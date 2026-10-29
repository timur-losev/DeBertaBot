"""
v2 classifiers (24 intents, coop_v2.py): the leave-one-author-out study and the model the bot ships.

The recipe is v1's fixed recipe (train_bert.HP: fp32, batch 16, 20 epochs, AdamW wd 0.01, 10% linear
warm-up, max 64 tokens, lr 5e-5 base / 2e-5 large), chosen before any v2 result. Every training set
includes the v2 seed commands. The owner allows up to 200 ms per line and +2 GB of RAM, so besides
deberta-v3-base (one model, 0.8 GB, ~25 ms on 4 CPU threads) the study measures:
  large   microsoft/deberta-v3-large, one model (~1.8 GB)
  ens3    three deberta-v3-base seeds, probabilities averaged (~2.3 GB, ~3x base latency); built in
          eval_v2.py from the base runs, no extra training

  cv      for each held-out author and seed: train on the other two authors + seeds, predict the
          held-out author's lines and the probes; and 5-fold out-of-fold predictions over the same
          training lines with the same number of optimizer steps (for the threshold)
  final   train on every line + seeds, with out-of-fold predictions over all lines for the threshold

    python train_v2.py cv base large       # jev environment, GPU
    python train_v2.py cv large --held r6,cs --results results_v2_probs_large_a.json   # a second process
    python train_v2.py final base|large|ens3
    python train_v2.py final ens3 --reuse-gate ../../models/coop-deberta-v3-ens3-v3/bot_config.json
                                           # skip the 15 out-of-fold trainings: keep that bot's gate and threshold
    python train_v2.py smoke               # one short training and a prediction: does this machine's device work

The device is cuda, else mps (Apple silicon), else cpu; COOP_DEVICE=cpu|mps|cuda overrides. The
cross-validation numbers in the write-ups are CUDA runs; the v3 final model was trained on mps.
"""
import io, json, os, random, sys, time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_v2 as V  # noqa: E402
import train_bert as T  # noqa: E402  (HP only: the v1 recipe)

MODELS = {"base": "microsoft/deberta-v3-base", "large": "microsoft/deberta-v3-large"}
LABELS = V.INTENTS
IDX = {k: i for i, k in enumerate(LABELS)}
SEEDS = [0, 1, 2]
HP = T.HP
RESULTS = os.path.join(HERE, f"results_{V.TAG}_probs.json")   # COOP_TAG=v21 -> results_v21_probs.json
MODELS_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "models"))


def pick_device():
    want = os.environ.get("COOP_DEVICE")
    if want:
        return want
    if torch.cuda.is_available():
        return "cuda"
    return "mps" if torch.backends.mps.is_available() else "cpu"


def free_cache(device):
    """Hand the freed model's memory back between trainings (cuda and mps keep it cached)."""
    if device == "cuda":
        torch.cuda.empty_cache()
    elif device == "mps":
        torch.mps.empty_cache()


def batcher(tok, items, device):
    """Each line is tokenized once and kept on the device; batch(idx) returns exactly the tensors
    tok([those lines], truncation=True, max_length=..., padding=True) would give (same ids, same
    padding to the longest line of the batch), without tokenizing and copying at every step."""
    ids = tok([i["text"] for i in items], truncation=True, max_length=HP["max_len"])["input_ids"]
    lens = [len(x) for x in ids]
    width = max(lens, default=1)
    X = torch.full((len(ids), width), tok.pad_token_id, dtype=torch.long)
    M = torch.zeros((len(ids), width), dtype=torch.long)
    for r, x in enumerate(ids):
        X[r, :len(x)] = torch.tensor(x)
        M[r, :len(x)] = 1
    X, M = X.to(device), M.to(device)

    def batch(idx):
        n = max(lens[j] for j in idx)
        rows = torch.tensor(idx, device=device)
        x = X[rows, :n]
        return {"input_ids": x, "token_type_ids": torch.zeros_like(x), "attention_mask": M[rows, :n]}
    return batch


SNAPSHOT_EVERY = 30 * 60   # seconds between snapshots of a training (the owner, 2026-10-27: every 30 minutes)


def _fingerprint(size, train, test, seed, epochs):
    """What a snapshot was taken of: the model size, the seed, the epochs, the training items in order, the test ids."""
    import hashlib
    h = hashlib.sha1(json.dumps([size, seed, epochs], sort_keys=True).encode("utf-8"))
    for i in train:
        h.update(json.dumps([i.get("id"), i.get("text"), i.get("maj")], ensure_ascii=False).encode("utf-8"))
    for i in test:
        h.update(str(i.get("id")).encode("utf-8"))
    return h.hexdigest()


def _save_snapshot(path, model, opt, sched, epoch, b, order, n, fp):
    tmp = path + ".tmp"
    torch.save({"fingerprint": fp, "model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "epoch": epoch,
                "b": b, "order": order, "py_random": random.getstate(), "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
                "saved": time.strftime("%Y-%m-%d %H:%M:%S")}, tmp)
    os.replace(tmp, path)       # a crash while writing leaves the snapshot before it whole
    print(f"snapshot {time.strftime('%H:%M:%S')}: epoch {epoch + 1}, row {min(b, n)} of {n} -> {path}", flush=True)


def train_predict(size, train, test, seed, device, epochs=None, snapshot_dir=None, snapshot_every=SNAPSHOT_EVERY):
    """snapshot_dir: every snapshot_every seconds the model, the optimizer, the schedule, the random states and the place in
    the epoch go to <snapshot_dir>/snapshot.pt; a call with the same data, seed and epochs goes on from there. A file
    <snapshot_dir>/STOP (stt/stop_training.ps1) makes it take a snapshot at the next step and exit with code 3."""
    name = MODELS[size]
    random.seed(seed)
    torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(name)
    # fp32 explicitly: deberta-v3 checkpoints are saved in fp16, where AdamW's eps rounds to zero
    model = AutoModelForSequenceClassification.from_pretrained(
        name, num_labels=len(LABELS), dtype=torch.float32).to(device)
    tr = [i for i in train if i["maj"]]
    train_batch, test_batch = batcher(tok, tr, device), batcher(tok, test, device)
    labels = torch.tensor([IDX[i["maj"]] for i in tr], device=device)
    order = list(range(len(tr)))
    epochs = epochs or HP["epochs"]
    steps = epochs * ((len(tr) + HP["batch"] - 1) // HP["batch"])
    # fused: one pass over the weights per step instead of about ten (same algorithm; CUDA only)
    opt = torch.optim.AdamW(model.parameters(), lr=HP["lr"][size], weight_decay=HP["weight_decay"],
                            fused=device == "cuda")
    sched = get_linear_schedule_with_warmup(opt, int(HP["warmup"] * steps), steps)
    snap = os.path.join(snapshot_dir, "snapshot.pt") if snapshot_dir else None
    stop = os.path.join(snapshot_dir, "STOP") if snapshot_dir else None
    fp = _fingerprint(size, train, test, seed, epochs) if snap else None
    start_epoch, start_b, resumed = 0, 0, False
    if snap:
        os.makedirs(snapshot_dir, exist_ok=True)
        if os.path.exists(stop):
            os.remove(stop)             # a stop asked of an earlier run, not of this one
        if os.path.exists(snap):
            s = torch.load(snap, map_location="cpu", weights_only=False)
            if s.get("fingerprint") == fp:
                model.load_state_dict(s["model"])
                opt.load_state_dict(s["opt"])
                sched.load_state_dict(s["sched"])
                random.setstate(s["py_random"])
                torch.set_rng_state(s["torch_rng"])
                if s["cuda_rng"] is not None and torch.cuda.is_available():
                    torch.cuda.set_rng_state_all(s["cuda_rng"])
                start_epoch, start_b, order, resumed = s["epoch"], s["b"], s["order"], True
                print(f"resumed from the snapshot of {s['saved']}: epoch {start_epoch + 1} of {epochs}, row {min(start_b, len(order))} of {len(order)}", flush=True)
            else:
                print(f"{snap}: a snapshot of other data, not used (it is replaced)", flush=True)
            del s
    last = time.time()
    model.train()
    for epoch in range(start_epoch, epochs):
        if not (resumed and epoch == start_epoch):
            random.shuffle(order)       # a resumed epoch keeps the order it was shuffled into
        for b in range(start_b if resumed and epoch == start_epoch else 0, len(order), HP["batch"]):
            idx = order[b:b + HP["batch"]]
            loss = model(**train_batch(idx), labels=labels[torch.tensor(idx, device=device)]).loss
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
            if snap and time.time() - last >= snapshot_every:
                _save_snapshot(snap, model, opt, sched, epoch, b + HP["batch"], order, len(order), fp)
                last = time.time()
            if stop and os.path.exists(stop):
                _save_snapshot(snap, model, opt, sched, epoch, b + HP["batch"], order, len(order), fp)
                os.remove(stop)
                print("stopped on request; run the same command again to go on", flush=True)
                sys.exit(3)
    model.eval()
    out = {}
    with torch.no_grad():
        for b in range(0, len(test), 64):
            batch = test[b:b + 64]
            x = test_batch(list(range(b, b + len(batch))))
            p = torch.softmax(model(**x).logits.float(), -1).cpu().tolist()
            out.update({i["id"]: row for i, row in zip(batch, p)})
    return out, model, tok


def oof(size, train, seed, device, k=5):
    """Out-of-fold predictions over the training lines; each fold trains for the same number of
    optimizer steps as a model on all of them (train_bert.oof)."""
    lines = [i for i in train if i["maj"]]
    random.Random(1000 + seed).shuffle(lines)
    full_steps = HP["epochs"] * ((len(lines) + HP["batch"] - 1) // HP["batch"])
    out = {}
    for f in range(k):
        te = lines[f::k]
        tr = [i for j, i in enumerate(lines) if j % k != f]
        ep = round(full_steps / ((len(tr) + HP["batch"] - 1) // HP["batch"]))
        out.update(train_predict(size, tr, te, seed, device, epochs=ep)[0])
        free_cache(device)
    return out


def cv(sizes, device, held_only=None, path=RESULTS):
    """held_only / path: run some held-out authors in a separate process with its own results file
    (several processes share the GPU); eval_v2.py reads every results_v2_probs*.json."""
    items, seeds, probes = V.load_items(), V.seed_items(), V.probe_items()
    try:
        res = json.load(io.open(path, encoding="utf-8"))
    except FileNotFoundError:
        res = {}
    res["_meta"] = {"labels": LABELS, "hp": HP, "models": MODELS, "n_items": len(items), "n_seeds": len(seeds)}
    for size in sizes:
        t0 = time.time()
        for held in held_only or V.AUTHORS:
            train = [i for i in items if i["author"] != held] + seeds
            test = [i for i in items if i["author"] == held] + probes
            for seed in SEEDS:
                key = f"{held}/{seed}"
                if key in res.get(size, {}):
                    continue
                full, model, _ = train_predict(size, train, test, seed, device)
                del model
                free_cache(device)
                res.setdefault(size, {})[key] = {"test": full, "oof": oof(size, train, seed, device)}
                json.dump(res, io.open(path, "w", encoding="utf-8"))
                print(f"{size} held={held} seed={seed} done, {time.time() - t0:.0f}s", flush=True)


def final(kind, device, reuse_gate=None):
    """kind: base | large (one model, seed 0) or ens3 (three base seeds). The threshold and the gate
    come from out-of-fold predictions over all study lines (seeds excluded from fitting).
    reuse_gate: another bot's bot_config.json; its gate and threshold are kept and the out-of-fold
    trainings are skipped (5 per member). The threshold then was not fitted to this training set."""
    items, seeds = V.load_items(), V.seed_items()
    size, members = ("base", SEEDS) if kind == "ens3" else (kind, [0])
    out_dir = os.path.join(MODELS_DIR, f"coop-deberta-v3-{kind}-{V.TAG if V.PLACES else 'v2'}")
    t0 = time.time()
    if reuse_gate:
        prev = json.load(io.open(reuse_gate, encoding="utf-8"))
        gate, thr, fits = prev["gate"], prev["threshold"], {}
        print(f"gate and threshold kept from {reuse_gate}: {gate} {thr}", flush=True)
    else:
        oofs = []
        for s in members:
            oofs.append(oof(size, items + seeds, s, device))
            print(f"oof seed {s} done, {time.time() - t0:.0f}s", flush=True)
        avg = {k: [sum(o[k][j] for o in oofs) / len(oofs) for j in range(len(LABELS))]
               for k in oofs[0] if not k.startswith("seed_")}
        fits = {g: V.fit_threshold(avg, items, g) for g in ("top", "family")}
        gate = max(fits, key=lambda g: (fits[g][1], g == "top"))   # ties keep the simpler top gate
        thr = fits[gate][0]
        print(f"out-of-fold over {len(avg)} lines: " + ", ".join(
            f"{g} gate thr {t:.2f} (near-2*wf {v})" for g, (t, v) in fits.items()) + f" -> {gate}", flush=True)
        # kept per member, as cv() keeps its own: without them the threshold and the gate in bot_config.json
        # can be checked against the log line above but not re-derived
        json.dump({"_meta": {"labels": LABELS, "kind": kind, "n_items": len(items), "n_seeds": len(seeds), "device": device},
                   "oof": {str(s): o for s, o in zip(members, oofs)}},
                  io.open(os.path.join(HERE, f"results_{V.TAG}_final_oof.json"), "w", encoding="utf-8"))
    os.makedirs(out_dir, exist_ok=True)
    member_dirs = []
    for s in members:
        _, model, tok = train_predict(size, items + seeds, items[:1], s, device)
        d = out_dir if len(members) == 1 else os.path.join(out_dir, f"seed{s}")
        model.to("cpu").save_pretrained(d, safe_serialization=True)
        tok.save_pretrained(d)
        member_dirs.append(os.path.relpath(d, out_dir).replace(os.sep, "/"))
        del model
        free_cache(device)
        print(f"member seed {s} saved, {time.time() - t0:.0f}s", flush=True)
    cfg = {
        "labels": LABELS, "threshold": thr, "gate": gate, "families": V.FAMILY,
        "phrases": {k: v["label"] for k, v in V.I.items()},
        "base_model": MODELS[size], "members": member_dirs,
        "recipe": {**HP, "lr": HP["lr"][size], "dtype": "float32", "seeds": members, "device": device,
                   "torch": torch.__version__},
        "trained_on": f"{len(items)} lines from 3 AI-written authors (v1 blind lines + v2 lines for "
                      f"TAKE_COVER/OPEN{' + v3 lines that name map places' if V.PLACES else ''}), "
                      f"majority of author + 2 AI annotators, plus {len(seeds)} "
                      f"developer-written canonical commands ({V.SEED_FILE})",
        "threshold_from": f"kept from {os.path.basename(os.path.dirname(os.path.abspath(reuse_gate)))} (not re-fitted to this training set)"
                          if reuse_gate else
                          f"5-fold out-of-fold predictions ({'averaged over the members' if len(members) > 1 else 'one model'}), "
                          "criterion near - 2*wrong-family, strict; gate chosen the same way",
        "oof_fits": {g: {"threshold": t, "criterion": v} for g, (t, v) in fits.items()},
    }
    json.dump(cfg, io.open(os.path.join(out_dir, "bot_config.json"), "w", encoding="utf-8"), indent=1)
    print(f"saved to {out_dir} in {time.time() - t0:.0f}s", flush=True)


def smoke(device):
    """A short training on this device: 64 lines, 2 epochs, then predictions on 32 others."""
    items = [i for i in V.load_items() if i["maj"]]
    t0 = time.time()
    out, model, _ = train_predict("base", items[:64], items[64:96], 0, device, epochs=2)
    ok = all(len(r) == len(LABELS) and abs(sum(r) - 1) < 1e-3 for r in out.values())
    print(f"device {device}, torch {torch.__version__}: 8 optimizer steps and {len(out)} predictions in "
          f"{time.time() - t0:.0f}s; probabilities {'sum to 1' if ok else 'ARE BROKEN'}")
    sys.exit(0 if ok else 1)


def main():
    device = pick_device()
    print(f"device: {device}", flush=True)
    if sys.argv[1] == "smoke":
        smoke(device)
    elif sys.argv[1] == "cv":
        args = sys.argv[2:]
        held = args[args.index("--held") + 1].split(",") if "--held" in args else None
        path = os.path.join(HERE, args[args.index("--results") + 1]) if "--results" in args else RESULTS
        sizes = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
        cv(sizes, device, held, path)
    elif sys.argv[1] == "final":
        args = sys.argv[3:]
        final(sys.argv[2], device, args[args.index("--reuse-gate") + 1] if "--reuse-gate" in args else None)


if __name__ == "__main__":
    main()
