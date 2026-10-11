"""Distilling the v54 ensemble into one small model, to buy CPU time for the rest of the brain (HANDOFF.md, "brains").

The three DeBERTa-v3-base members cost ~40 ms on 3 cores. A deberta-v3-xsmall (22M in the backbone, hidden 384) or
deberta-v3-small (44M, 6 layers) student trained on the same lines with the ensemble's soft probabilities as a second
target should keep most of the accuracy at a fraction of the cost. Same tokenizer as base, so the C++ engine runs the
student as it runs a one-member bot.

Honest numbers need teachers that never saw the held-out lines, so the fold split here is ONE fixed split (shuffle
seed 1000) shared by the three teacher seeds, unlike build_v54.py's per-seed splits; per fold the student is distilled
from the three fold teachers' average, and the teachers' own out-of-fold average is the baseline on the same lines.

    python distill_v54.py teachers SEED            5 folds: a base teacher per fold -> kd54_teacher_s<SEED>.json
                                                   (its probabilities on the fold's training lines and on its test lines)
    python distill_v54.py student SIZE SEED [TAG]  5 folds: a SIZE student (xsmall | small | base) per fold, distilled from the
                                                   fold's teachers -> kd54_student_<SIZE>_<TAG>_s<SEED>.json. TAG: kd (default:
                                                   T=2, alpha=0.5), hard (no distillation, the same recipe), kd24 (24 epochs)
    python distill_v54.py final SIZE SEED [TAG]    one student on everything, distilled from the final v54 members
                                                   -> models/coop-deberta-v3-<SIZE>-kd-v54/seed<SEED>
    python distill_v54.py score                    the tables: teacher ensemble vs every student file present
"""
import io, json, os, random, sys, time
from collections import Counter
os.environ["COOP_TAG"] = "v54"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
sys.path.insert(0, HERE)
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
import coop_v2 as V
import train_v2 as T
import build_v54 as B

MODELS = {"xsmall": "microsoft/deberta-v3-xsmall", "small": "microsoft/deberta-v3-small", "base": "microsoft/deberta-v3-base"}
LR = {"xsmall": 1e-4, "small": 5e-5, "base": 5e-5}     # fixed before any result: the usual rates for the sizes
TAGS = {"kd": dict(T=2.0, alpha=0.5, epochs=12), "hard": dict(T=1.0, alpha=1.0, epochs=12), "kd24": dict(T=2.0, alpha=0.5, epochs=24)}
DEVICE = T.pick_device()
LABELS, IDX = V.INTENTS, {k: i for i, k in enumerate(V.INTENTS)}
SPLIT_SEED = 1000
FINAL_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v54"))


def folds():
    groups = B.LINES + B.SEEDS
    random.Random(SPLIT_SEED).shuffle(groups)
    out = []
    for f in range(5):
        held = {g["id"] for g in groups[f::5]}
        train = B.training_set([i for i in B.LINES if i["id"] not in held], [s for s in B.SEEDS if s["id"] not in held])
        test = []
        for i in B.LINES:
            if i["id"] in held:
                test.append({"id": f"typed|{i['id']}", "text": i["text"]})
                if i["id"] in B.SPOKEN:
                    test += [{"id": f"{c}|{i['id']}", "text": B.heard(c)[i["id"]]} for c in B.LINE_TEST]
        out.append((train, test))
    return out


def predict(model, tok, items, device):
    batch = T.batcher(tok, items, device)
    out = {}
    model.eval()
    with torch.no_grad():
        for b in range(0, len(items), 64):
            chunk = items[b:b + 64]
            p = torch.softmax(model(**batch(list(range(b, b + len(chunk))))).logits.float(), -1).cpu().tolist()
            out.update({i["id"]: row for i, row in zip(chunk, p)})
    return out


def train_student(size, train, soft, seed, device, T_=2.0, alpha=0.5, epochs=12):
    """build_v54's recipe (batch 16, AdamW, 10% warm-up, linear decay) with the loss
    alpha * CE(hard label) + (1 - alpha) * T^2 * KL(teacher_T || student_T); soft: id -> teacher probabilities."""
    random.seed(seed)
    torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(MODELS[size])
    model = AutoModelForSequenceClassification.from_pretrained(MODELS[size], num_labels=len(LABELS), dtype=torch.float32).to(device)
    batch = T.batcher(tok, train, device)
    y = torch.tensor([IDX[i["maj"]] for i in train], device=device)
    soft_t = torch.tensor([soft[i["id"]] if soft else [0.0] * len(LABELS) for i in train], device=device)
    order = list(range(len(train)))
    steps = epochs * ((len(train) + T.HP["batch"] - 1) // T.HP["batch"])
    opt = torch.optim.AdamW(model.parameters(), lr=LR[size], weight_decay=T.HP["weight_decay"], fused=device == "cuda")
    sched = get_linear_schedule_with_warmup(opt, int(T.HP["warmup"] * steps), steps)
    model.train()
    for _ in range(epochs):
        random.shuffle(order)
        for b in range(0, len(order), T.HP["batch"]):
            idx = order[b:b + T.HP["batch"]]
            rows = torch.tensor(idx, device=device)
            logits = model(**batch(idx)).logits.float()
            loss = alpha * F.cross_entropy(logits, y[rows])
            if alpha < 1.0:
                # the teacher's probabilities re-tempered: p_T = softmax(log p / T)
                pt = torch.softmax(torch.log(soft_t[rows].clamp_min(1e-9)) / T_, -1)
                loss = loss + (1 - alpha) * T_ * T_ * F.kl_div(torch.log_softmax(logits / T_, -1), pt, reduction="batchmean")
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
    return model, tok


def teachers(seed):
    t0 = time.time()
    path = os.path.join(HERE, f"kd54_teacher_s{seed}.json")
    done = json.load(io.open(path, encoding="utf-8")) if os.path.exists(path) else {}
    for f, (train, test) in enumerate(folds()):
        if str(f) in done:
            print(f"teacher seed {seed} fold {f}: kept", flush=True)
            continue
        ep = max(1, round(B.EPOCHS * B.steps(len(B.training_set(B.LINES, B.SEEDS))) / B.steps(len(train))))
        test_probs, model, tok = T.train_predict("base", train, test, seed, DEVICE, epochs=ep)
        done[str(f)] = {"epochs": ep, "train": predict(model, tok, train, DEVICE), "test": test_probs}
        del model
        T.free_cache(DEVICE)
        json.dump(done, io.open(path, "w", encoding="utf-8"))
        print(f"teacher seed {seed} fold {f}: {len(train)} training lines, {ep} epochs, {len(test)} test lines, {time.time() - t0:.0f}s", flush=True)


def soft_labels(fold, items):
    """The fold teachers' average on the items (every kd54_teacher_s*.json present); None if there are none."""
    files = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2)
             if os.path.exists(os.path.join(HERE, f"kd54_teacher_s{s}.json"))]
    runs = [r[str(fold)]["train"] for r in files if str(fold) in r]
    if not runs:
        return None, 0
    return {i["id"]: [sum(r[i["id"]][j] for r in runs) / len(runs) for j in range(len(LABELS))] for i in items}, len(runs)


def embed(model, tok, items, device):
    """The pooled vector the classifier head reads (DeBERTa's ContextPooler on the first token), per id: what a
    nearest-neighbour memory of commands would index (knn_v54.py)."""
    batch = T.batcher(tok, items, device)
    out = {}
    model.eval()
    with torch.no_grad():
        for b in range(0, len(items), 64):
            chunk = items[b:b + 64]
            x = batch(list(range(b, b + len(chunk))))
            h = model.deberta(input_ids=x["input_ids"], attention_mask=x["attention_mask"]).last_hidden_state
            v = model.pooler(h).float().cpu()
            out.update({i["id"]: v[j].numpy().astype("float16") for j, i in enumerate(chunk)})
    return out


def student(size, seed, tag):
    import numpy as np
    hp = TAGS[tag]
    t0 = time.time()
    path = os.path.join(HERE, f"kd54_student_{size}_{tag}_s{seed}.json")
    done = json.load(io.open(path, encoding="utf-8")) if os.path.exists(path) else {"size": size, "tag": tag, "seed": seed, "folds": {}, "probs": {}}
    for f, (train, test) in enumerate(folds()):
        if str(f) in done["folds"]:
            continue
        soft, n_t = (None, 0) if hp["alpha"] >= 1.0 else soft_labels(f, train)
        assert hp["alpha"] >= 1.0 or n_t == 3, f"fold {f}: {n_t} teachers, need 3 (run `teachers 0|1|2` first)"
        model, tok = train_student(size, train, soft, seed, DEVICE, hp["T"], hp["alpha"], hp["epochs"])
        done["probs"].update(predict(model, tok, test, DEVICE))
        # the pooled vectors of the fold's training and test lines, for the nearest-neighbour study (knn_v54.py)
        emb = embed(model, tok, train + test, DEVICE)
        np.savez_compressed(os.path.join(HERE, f"kd54_emb_{size}_{tag}_s{seed}_f{f}.npz"), ids=np.array(list(emb)), x=np.stack(list(emb.values())),
                            train=np.array([i["id"] for i in train]), test=np.array([i["id"] for i in test]))
        done["folds"][str(f)] = {"teachers": n_t, "train": len(train), "test": len(test)}
        del model
        T.free_cache(DEVICE)
        json.dump(done, io.open(path, "w", encoding="utf-8"))
        print(f"student {size} {tag} seed {seed} fold {f}: {len(train)} lines, {n_t} teachers, {time.time() - t0:.0f}s", flush=True)


def final(size, seed, tag):
    hp = TAGS[tag]
    t0 = time.time()
    train = B.training_set(B.LINES, B.SEEDS)
    soft = None
    if hp["alpha"] < 1.0:
        runs = []
        for s in (0, 1, 2):
            d = os.path.join(FINAL_DIR, f"seed{s}")
            tok = AutoTokenizer.from_pretrained(d)
            m = AutoModelForSequenceClassification.from_pretrained(d, dtype=torch.float32).to(DEVICE)
            runs.append(predict(m, tok, train, DEVICE))
            del m
            T.free_cache(DEVICE)
        soft = {i["id"]: [sum(r[i["id"]][j] for r in runs) / 3 for j in range(len(LABELS))] for i in train}
        print(f"soft labels from the 3 final members on {len(train)} lines, {time.time() - t0:.0f}s", flush=True)
    model, tok = train_student(size, train, soft, seed, DEVICE, hp["T"], hp["alpha"], hp["epochs"])
    out = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", f"coop-deberta-v3-{size}-{tag}-v54"))
    d = os.path.join(out, f"seed{seed}")
    os.makedirs(d, exist_ok=True)
    model.to("cpu").save_pretrained(d, safe_serialization=True)
    tok.save_pretrained(d)
    json.dump({"training_lines": len(train), "student": MODELS[size], "lr": LR[size], **hp, "teachers": FINAL_DIR if soft else None, "device": DEVICE},
              io.open(os.path.join(d, "trained_on.json"), "w"), indent=1)
    print(f"final student {size} {tag} seed {seed}: {len(train)} lines, {hp['epochs']} epochs, saved to {d}, {time.time() - t0:.0f}s", flush=True)


def score():
    items = {i["id"]: i for i in B.LINES}
    spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731
    FIT = ["clean", "kokoro", "kokorox", "vctkA"]
    SHOW = [("typed", "typed text"), ("clean", "Windows voices"), ("kokoro", "Kokoro, English voices"), ("kokorox", "Kokoro, other-language voices"),
            ("vctkA", "VCTK, speakers used in training"), ("vctkB", "VCTK, speakers never in training")]

    def by(probs, c, keep):
        return {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == c and keep(items[k.split("|", 1)[1]])}

    def fit(probs):
        best = None
        for gate in ("top", "family"):
            for t in range(0, 100, 2):
                near = cross = 0
                for c in FIT:
                    p = by(probs, c, spoken)
                    s = V.score(V.picks(p, gate, t / 100), [items[k] for k in p])
                    near += s["near_count"]; cross += s["cross_count"]
                v = near - 2 * cross
                if best is None or v > best[0] or (v == best[0] and gate == "top" and best[1] != "top"):
                    best = (v, gate, t / 100)
        return best[1], best[2]

    def avg(runs):
        keys = set.intersection(*[set(r) for r in runs])
        return {k: [sum(r[k][j] for r in runs) / len(runs) for j in range(len(LABELS))] for k in keys}

    systems = []
    tfiles = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2)
              if os.path.exists(os.path.join(HERE, f"kd54_teacher_s{s}.json"))]
    tfiles = [r for r in tfiles if len(r) == 5]
    if tfiles:
        per_seed = [{k: v for f in r.values() for k, v in f["test"].items()} for r in tfiles]
        systems.append((f"teacher ensemble, {len(tfiles)} base members (the v54 bot's shape)", avg(per_seed)))
        systems.append(("one base teacher (seed 0)", per_seed[0]))
    studs = {}
    for fn in sorted(os.listdir(HERE)):
        if fn.startswith("kd54_student_") and fn.endswith(".json"):
            r = json.load(io.open(os.path.join(HERE, fn), encoding="utf-8"))
            if len(r["folds"]) == 5:
                studs.setdefault((r["size"], r["tag"]), []).append(r["probs"])
    for (size, tag), runs in sorted(studs.items()):
        systems.append((f"student {size} {tag}, seed {0} alone", runs[0]))
        if len(runs) > 1:
            systems.append((f"student {size} {tag}, {len(runs)} seeds averaged", avg(runs)))
    print(f"{len(items)} lines; gate and threshold fitted per system on the training voices (criterion near - 2 * wrong family)")
    for name, probs in systems:
        gate, thr = fit(probs)
        print(f"\n{name}: gate {gate}, threshold {thr:.2f}")
        print(f"  {'what the classifier is given':38s} {'near':>6s} {'wrong fam':>10s} {'acts on non-order':>18s} {'criterion':>10s}")
        for c, label in SHOW:
            p = by(probs, c, spoken)
            if not p:
                continue
            s = V.score(V.picks(p, gate, thr), [items[k] for k in p])
            print(f"  {label:38s} {100 * s['near']:6.1f} {100 * s['cross']:9.1f}% {100 * s['fired_on_nonorder']:17.1f}% {100 * (s['near'] - 2 * s['cross']):10.1f}   n={s['n']}")
        p = by(probs, "typed", lambda i: True)
        s = V.score(V.picks(p, gate, thr), [items[k] for k in p])
        print(f"  {'every line typed (all authors)':38s} {100 * s['near']:6.1f} {100 * s['cross']:9.1f}% {100 * s['fired_on_nonorder']:17.1f}% {100 * (s['near'] - 2 * s['cross']):10.1f}   n={s['n']}")
    if len(systems) > 1:
        print("\nlines (VCTK B) the teacher ensemble has near and a system loses, by true intent:")
        tg, tt = fit(systems[0][1])
        tp = by(systems[0][1], "vctkB", spoken)
        tpk = V.picks(tp, tg, tt)
        for name, probs in systems[1:]:
            g, t = fit(probs)
            pk = V.picks(by(probs, "vctkB", spoken), g, t)
            lost = Counter(items[k]["maj"] for k in pk if pk[k] not in items[k]["accept"] and V.FAMILY[pk[k]] != V.FAMILY[items[k]["maj"]]
                           and (tpk[k] in items[k]["accept"] or V.FAMILY[tpk[k]] == V.FAMILY[items[k]["maj"]]))
            print(f"  {name}: {sum(lost.values())} lost -- " + ", ".join(f"{a} {n}" for a, n in lost.most_common(8)))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "teachers":
        teachers(int(sys.argv[2]))
    elif mode == "student":
        student(sys.argv[2], int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "kd")
    elif mode == "final":
        final(sys.argv[2], int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "kd")
    elif mode == "score":
        score()
    else:
        sys.exit(__doc__)
