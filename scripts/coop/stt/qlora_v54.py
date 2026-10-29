"""A taught decoder next to the classifier (HANDOFF.md, "brains"). decoder_v54.py asked an untuned small instruct model
and it lost to asking again; this is the same model class after training: a ~2B decoder with its weights in 4 bits and
LoRA adapters on every projection (QLoRA), trained on exactly what a fold teacher of distill_v54.py trains on and
scored on the same held-out rows with the same criterion, so its table reads next to kd54_score.log.

The line goes in as the user turn; the answer is the intent's name and the end-of-turn token, nothing else. A test row
gets a probability per intent: the model's probability of each of the 41 names as the whole answer, renormalized over
the 41 (constrained choice: nothing is generated, nothing is parsed), so the gates and the threshold fit as they do
for a classifier.

    python qlora_v54.py folds MODEL SEED [TAG]    5 folds: an adapter per fold -> qlora54_<MODEL>_<TAG>_s<SEED>.json
    python qlora_v54.py final MODEL SEED [TAG]    one adapter on everything -> models/coop-<MODEL>-qlora-v54/seed<SEED>
    python qlora_v54.py score                     the tables: the teacher ensemble, every decoder file present, the two together
    python qlora_v54.py timing MODEL SEED [TAG]   the final adapter merged into the bf16 base: ms per line on this GPU

MODEL is a key of MODELS. The base weights are downloaded once into models/hf next to this file (COOP_LLM_CACHE
overrides), not into the user's Hugging Face cache. Needs peft and bitsandbytes on top of the training environment
(pip install --no-deps peft bitsandbytes) and a CUDA GPU.
"""
import copy, io, json, os, random, sys, time
os.environ["COOP_TAG"] = "v54"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
sys.path.insert(0, HERE)
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, get_linear_schedule_with_warmup
import coop_v2 as V
import train_v2 as T
import build_v54 as B
import distill_v54 as D

# both Apache-2.0 and not gated. The article's Mistral-NeMo-Minitron-2B has no public weights (NVIDIA ACE Early Access).
# qwen3 is a plain transformer (2.03B with its embeddings). qwen35's text model mixes in gated-delta-rule layers whose
# fast kernels (causal_conv1d, flash-linear-attention) are not built for Windows: with transformers' reference code a
# training step took 5.0 s against qwen3's 0.44 s on the RTX 4090, so its folds were not run here
# qwen3_4b: the same family twice the size (4.02B, Apache-2.0), for one question of chains2_v54.py: is what the decoder
# loses on heard lines a matter of the model's size
MODELS = {"qwen3": "Qwen/Qwen3-1.7B", "qwen35": "Qwen/Qwen3.5-2B", "qwen3_4b": "Qwen/Qwen3-4B"}
# fixed before any result: the usual QLoRA recipe (rank 16 on the attention and MLP projections, 2e-4, 3 epochs),
# with build_v54's batch, warm-up and decay
TAGS = {"r16": dict(r=16, alpha=32, dropout=0.05, lr=2e-4, epochs=3)}
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
CACHE = os.environ.get("COOP_LLM_CACHE", os.path.join(HERE, "models", "hf"))
SYSTEM = ("You are the AI teammate in a tactical co-op shooter. The player's line is a speech-to-text transcript and "
          "may be garbled. Answer with the name of the order it gives, or NONE.")
SEP = " > "
LABELS, IDX = V.INTENTS, {k: i for i, k in enumerate(V.INTENTS)}
DEVICE = "cuda"


def load(name, four_bit=True):
    tok = AutoTokenizer.from_pretrained(MODELS[name], cache_dir=CACHE)
    q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                           bnb_4bit_compute_dtype=torch.bfloat16) if four_bit else None
    model = AutoModelForCausalLM.from_pretrained(MODELS[name], cache_dir=CACHE, quantization_config=q, dtype=torch.bfloat16, device_map={"": 0})
    return model, tok


class Turns:
    """Token ids of a line's prompt and of the 41 answers. The prompt and the answer are tokenized apart and joined as
    ids, in training and in scoring alike, so no merge across the boundary can make the two disagree."""

    def __init__(self, tok, system=SYSTEM):
        self.tok, self.system = tok, system
        self.end = tok.convert_tokens_to_ids("<|im_end|>")
        assert isinstance(self.end, int) and self.end != tok.unk_token_id, "this tokenizer has no <|im_end|>"
        self.pad = tok.pad_token_id if tok.pad_token_id is not None else self.end
        self.answers = [self.answer([k]) for k in LABELS]
        assert len({tuple(a) for a in self.answers}) == len(LABELS)

    def answer(self, orders):
        """One intent's name, or several joined by SEP (chains_v54.py), and the end-of-turn token: without it NO would
        be a prefix of NONE."""
        return self.ids(SEP.join(orders))

    def ids(self, text):
        """Any answer as written (chains2_v54.py: the orders as lines of their own) and the end-of-turn token."""
        return self.tok(text, add_special_tokens=False)["input_ids"] + [self.end]

    def text(self, line):
        return self.tok.apply_chat_template([{"role": "system", "content": self.system}, {"role": "user", "content": line}],
                                            add_generation_prompt=True, tokenize=False, enable_thinking=False)

    def prompt(self, line):
        return self.tok(self.text(line), add_special_tokens=False)["input_ids"]


def padded(seqs, pad):
    n = max(map(len, seqs))
    x = torch.full((len(seqs), n), pad, dtype=torch.long)
    m = torch.zeros((len(seqs), n), dtype=torch.long)
    for r, s in enumerate(seqs):
        x[r, :len(s)] = torch.tensor(s)
        m[r, :len(s)] = 1
    return x.to(DEVICE), m.to(DEVICE)


SNAPSHOT_EVERY = 30 * 60   # seconds between snapshots of a training (the owner, 2026-10-27: every 30 minutes)


def _fingerprint(name, rows, seed, hp, system):
    """What a snapshot was taken of: the model, the rows in order, the seed, the recipe and the system turn."""
    import hashlib
    h = hashlib.sha1(json.dumps([name, seed, hp, system], sort_keys=True).encode("utf-8"))
    for r in rows:
        h.update(json.dumps(r, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def _save_snapshot(path, model, opt, sched, epoch, b, order, step, fp):
    from peft import get_peft_model_state_dict
    tmp = path + ".tmp"
    torch.save({"fingerprint": fp, "adapter": get_peft_model_state_dict(model), "opt": opt.state_dict(), "sched": sched.state_dict(),
                "epoch": epoch, "b": b, "order": order, "step": step, "py_random": random.getstate(), "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all(), "saved": time.strftime("%Y-%m-%d %H:%M:%S")}, tmp)
    os.replace(tmp, path)       # a crash while writing leaves the snapshot before it whole
    print(f"snapshot {time.strftime('%H:%M:%S')}: epoch {epoch + 1}, row {min(b, len(order))} of {len(order)}, step {step} -> {path}", flush=True)


def train(name, rows, seed, hp, system=SYSTEM, checkpoint=False, snapshot_dir=None, snapshot_every=SNAPSHOT_EVERY):
    """rows: [{"text", "maj"}], or "orders" (a list of intents) or "answer" (the answer as written) in place of "maj".
    The loss is on the answer's tokens only.
    checkpoint: gradient checkpointing, for long lines. A batch of 16 single lines (about 75 tokens with the prompt)
    peaks at 11 GB; the joined lines of chains_v54.py are twice as long and went past 24 GB without it.
    snapshot_dir: every snapshot_every seconds the adapter, the optimizer, the schedule, the random states and the place in
    the epoch go to <snapshot_dir>/snapshot.pt (and once more at the end); a training started again with the same rows,
    seed and recipe goes on from there (the same command after a crash or a stop). A snapshot of other rows is not used.
    A file <snapshot_dir>/STOP (stop_training.ps1) makes it take a snapshot at the next step and exit with code 3."""
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, set_peft_model_state_dict
    random.seed(seed)
    torch.manual_seed(seed)
    model, tok = load(name)
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=checkpoint)
    model = get_peft_model(model, LoraConfig(r=hp["r"], lora_alpha=hp["alpha"], lora_dropout=hp["dropout"], target_modules=TARGETS, task_type="CAUSAL_LM"))
    turns = Turns(tok, system)
    data = [(turns.prompt(r["text"]), turns.ids(r["answer"]) if "answer" in r else turns.answer(r.get("orders") or [r["maj"]])) for r in rows]
    order = list(range(len(data)))
    steps = hp["epochs"] * B.steps(len(data))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=hp["lr"], weight_decay=T.HP["weight_decay"])
    sched = get_linear_schedule_with_warmup(opt, int(T.HP["warmup"] * steps), steps)
    snap = os.path.join(snapshot_dir, "snapshot.pt") if snapshot_dir else None
    fp = _fingerprint(name, rows, seed, hp, system) if snap else None
    start_epoch, start_b, step, resumed = 0, 0, 0, False
    if snap and os.path.exists(snap):
        s = torch.load(snap, map_location="cpu", weights_only=False)
        if s.get("fingerprint") == fp:
            set_peft_model_state_dict(model, s["adapter"])
            opt.load_state_dict(s["opt"])
            sched.load_state_dict(s["sched"])
            random.setstate(s["py_random"])
            torch.set_rng_state(s["torch_rng"])
            torch.cuda.set_rng_state_all(s["cuda_rng"])
            start_epoch, start_b, step, order, resumed = s["epoch"], s["b"], s["step"], s["order"], True
            print(f"resumed from the snapshot of {s['saved']}: epoch {start_epoch + 1} of {hp['epochs']}, row {min(start_b, len(order))} of "
                  f"{len(order)}, step {step} of {steps}", flush=True)
        else:
            print(f"{snap}: a snapshot of other rows or another recipe, not used (it is replaced)", flush=True)
        del s
    if snap:
        os.makedirs(snapshot_dir, exist_ok=True)
        if os.path.exists(os.path.join(snapshot_dir, "STOP")):
            os.remove(os.path.join(snapshot_dir, "STOP"))   # a stop asked of an earlier run, not of this one
    last = time.time()
    lm = model.get_base_model()
    model.train()
    for epoch in range(start_epoch, hp["epochs"]):
        if not (resumed and epoch == start_epoch):
            random.shuffle(order)       # a resumed epoch keeps the order it was shuffled into
        for b in range(start_b if resumed and epoch == start_epoch else 0, len(order), T.HP["batch"]):
            idx = order[b:b + T.HP["batch"]]
            x, m = padded([data[j][0] + data[j][1] for j in idx], turns.pad)
            y = torch.full_like(x, -100)
            for r, j in enumerate(idx):
                p, a = data[j]
                y[r, len(p):len(p) + len(a)] = torch.tensor(a)
            if checkpoint:
                # the same loss from the answer's positions alone. Projecting every position of 16 long lines on the
                # vocabulary is gigabytes per step, and the allocator's leftovers of it filled the card (22.6 GB and
                # 2.4 GB spilled over) on the rows of chains2_v54.py
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    h = lm.model(input_ids=x, attention_mask=m, use_cache=False).last_hidden_state
                    keep = y[:, 1:] != -100                 # position j predicts token j + 1
                    logits = lm.lm_head(h[:, :-1][keep])
                loss = torch.nn.functional.cross_entropy(logits.float(), y[:, 1:][keep])
            else:
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    loss = model(input_ids=x, attention_mask=m, labels=y, use_cache=False).loss
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
            step += 1
            if snap and time.time() - last >= snapshot_every:
                _save_snapshot(snap, model, opt, sched, epoch, b + T.HP["batch"], order, step, fp)
                last = time.time()
            if snap and os.path.exists(os.path.join(snapshot_dir, "STOP")):
                # stop_training.ps1: a snapshot now, and out (exit code 3); the same command later goes on from here
                _save_snapshot(snap, model, opt, sched, epoch, b + T.HP["batch"], order, step, fp)
                os.remove(os.path.join(snapshot_dir, "STOP"))
                print(f"stopped on request at step {step} of {steps}; run the same command again to go on", flush=True)
                sys.exit(3)
    if snap:   # the end too: started again, the same command goes straight to what follows the training
        _save_snapshot(snap, model, opt, sched, hp["epochs"] - 1, len(order), order, step, fp)
    del opt, sched
    T.free_cache(DEVICE)
    return model, turns


@torch.no_grad()
def predict(model, turns, items, rows=6):
    """id -> the 41 probabilities. The prompts of `rows` lines are run once, padded on the left so each ends where its
    answer starts; their keys and values are repeated 41 times and the 41 answers are run on top of them (decoder_v54.py's
    way, batched). Two forwards per `rows` lines: a 4-bit layer unpacks its weights on every call (0.15 s a forward for
    the whole model), and a 2B model reads about 16,000 tokens a second on the RTX 4090, so neither a forward per line
    nor 41 whole prompts per line is cheap. `rows` is small because the repeated keys and values are: at 16 lines they
    and the logits overflow 24 GB, and Windows then swaps video memory instead of failing."""
    model.eval()
    n = len(LABELS)
    A, AM = padded(turns.answers, turns.pad)
    out = {}
    for b in range(0, len(items), rows):
        chunk = items[b:b + rows]
        prompts = [turns.prompt(it["text"]) for it in chunk]
        w = max(map(len, prompts))
        x = torch.full((len(chunk), w), turns.pad, dtype=torch.long)
        m = torch.zeros((len(chunk), w), dtype=torch.long)
        for r, p in enumerate(prompts):
            x[r, w - len(p):] = torch.tensor(p)
            m[r, w - len(p):] = 1
        x, m = x.to(DEVICE), m.to(DEVICE)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            o = model(input_ids=x, attention_mask=m, use_cache=True)
            first = torch.log_softmax(o.logits[:, -1].float(), -1)          # [rows, vocabulary]: the answer's first token
            cache = o.past_key_values
            cache.batch_repeat_interleave(n)                                # row 0 forty-one times, then row 1, ...
            ids, mask = A.repeat(len(chunk), 1), torch.cat([m.repeat_interleave(n, 0), AM.repeat(len(chunk), 1)], 1)
            # [rows * 41, width, vocabulary]: position j predicts the answer's token j + 1
            lp = torch.log_softmax(model(input_ids=ids, attention_mask=mask, past_key_values=cache, use_cache=False).logits.float(), -1)
        rest = (lp[:, :-1].gather(2, ids[:, 1:, None]).squeeze(2) * AM.repeat(len(chunk), 1)[:, 1:]).sum(1)
        score = first[:, A[:, 0]] + rest.view(len(chunk), n)
        out.update({it["id"]: row for it, row in zip(chunk, torch.softmax(score, -1).cpu().tolist())})
    return out


def path_of(name, tag, seed):
    return os.path.join(HERE, f"qlora54_{name}_{tag}_s{seed}.json")


def folds(name, seed, tag):
    hp = TAGS[tag]
    t0 = time.time()
    path = path_of(name, tag, seed)
    done = json.load(io.open(path, encoding="utf-8")) if os.path.exists(path) else {"model": MODELS[name], "tag": tag, "seed": seed, "folds": {}, "probs": {}}
    for f, (rows, test) in enumerate(D.folds()):
        if str(f) in done["folds"]:
            continue
        t1 = time.time()
        model, turns = train(name, rows, seed, hp)
        t2 = time.time()
        done["probs"].update(predict(model, turns, test))
        done["folds"][str(f)] = {"train": len(rows), "test": len(test), "train_s": round(t2 - t1), "predict_s": round(time.time() - t2),
                                 "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
        del model
        T.free_cache(DEVICE)
        json.dump(done, io.open(path, "w", encoding="utf-8"))
        print(f"decoder {name} {tag} seed {seed} fold {f}: {len(rows)} lines, {len(test)} test rows, training {t2 - t1:.0f}s, "
              f"scoring {time.time() - t2:.0f}s, peak {done['folds'][str(f)]['gpu_gb']} GB, {time.time() - t0:.0f}s", flush=True)


def final_dir(name, seed):
    return os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", f"coop-{name}-qlora-v54", f"seed{seed}"))


def final(name, seed, tag):
    hp = TAGS[tag]
    t0 = time.time()
    rows = B.training_set(B.LINES, B.SEEDS)
    model, _ = train(name, rows, seed, hp)
    d = final_dir(name, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)     # the adapter only; the base stays with its author
    json.dump({"training_lines": len(rows), "base": MODELS[name], "base_revision": model.get_base_model().config._commit_hash, **hp,
               "targets": TARGETS, "four_bit": "nf4, double quantization, bf16 compute", "system": SYSTEM, "labels": LABELS},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1)
    print(f"final decoder {name} {tag} seed {seed}: {len(rows)} lines, {hp['epochs']} epochs, adapter saved to {d}, {time.time() - t0:.0f}s", flush=True)


def timing(name, seed, n=200):
    """What a game would do: the system turn's KV cache is computed once; a line costs its own tokens and the answer's,
    generated greedily until the end-of-turn token. The adapter is merged into the bf16 base (4-bit layers in PyTorch
    are slower than bf16; a game would run a 4-bit GGUF in another runtime, so this is this GPU's number, not a player's)."""
    from peft import PeftModel
    model, tok = load(name, four_bit=False)
    model = PeftModel.from_pretrained(model, final_dir(name, seed)).merge_and_unload().eval()
    turns = Turns(tok)
    head = turns.text("X")
    head = tok(head[:head.index("X")], add_special_tokens=False)["input_ids"]
    lines = [i["text"] for i in B.LINES][:n]
    lat, picks = [], []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        sys_cache = model(input_ids=torch.tensor([head], device=DEVICE), use_cache=True).past_key_values
        for line in lines[:5] + lines:                    # the first five warm the GPU up and are not counted
            ids = turns.prompt(line)
            assert ids[:len(head)] == head, "the system turn is not a token prefix of the prompt"
            torch.cuda.synchronize()
            t1 = time.perf_counter()
            out = model(input_ids=torch.tensor([ids[len(head):]], device=DEVICE), past_key_values=copy.deepcopy(sys_cache), use_cache=True)
            said = []
            for _ in range(12):
                nxt = int(out.logits[0, -1].argmax())
                if nxt == turns.end:
                    break
                said.append(nxt)
                out = model(input_ids=torch.tensor([[nxt]], device=DEVICE), past_key_values=out.past_key_values, use_cache=True)
            torch.cuda.synchronize()
            lat.append(time.perf_counter() - t1)
            picks.append(tok.decode(said))
    lat = sorted(lat[5:])
    bad = sum(p not in IDX for p in picks)
    print(f"{MODELS[name]} merged, bf16, {torch.cuda.get_device_name(0)}: {len(head)} system tokens cached, {len(lat)} lines, "
          f"{1000 * sum(lat) / len(lat):.0f} ms per line (median {1000 * lat[len(lat) // 2]:.0f}, p95 {1000 * lat[int(0.95 * (len(lat) - 1))]:.0f}), "
          f"peak {torch.cuda.max_memory_allocated() / 2 ** 30:.1f} GB; {bad} free-running answers were not an intent name")


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

    def table(pick_of):
        print(f"  {'what the model is given':38s} {'near':>6s} {'wrong fam':>10s} {'acts on non-order':>18s} {'criterion':>10s}")
        for c, label in SHOW + [("typed", "every line typed (all authors)")]:
            keep = spoken if label != "every line typed (all authors)" else (lambda i: True)
            p = pick_of(c, keep)
            s = V.score(p, [items[k] for k in p])
            print(f"  {label:38s} {100 * s['near']:6.1f} {100 * s['cross']:9.1f}% {100 * s['fired_on_nonorder']:17.1f}% {100 * (s['near'] - 2 * s['cross']):10.1f}   n={s['n']}")

    tfiles = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2)
              if os.path.exists(os.path.join(HERE, f"kd54_teacher_s{s}.json"))]
    tfiles = [r for r in tfiles if len(r) == 5]
    ens = avg([{k: v for f in r.values() for k, v in f["test"].items()} for r in tfiles]) if tfiles else None
    print(f"{len(items)} lines; gate and threshold fitted per system on the training voices (criterion near - 2 * wrong family)")
    if ens:
        eg, et = fit(ens)
        print(f"\nteacher ensemble, {len(tfiles)} base members (the v54 bot's shape): gate {eg}, threshold {et:.2f}")
        table(lambda c, keep: V.picks(by(ens, c, keep), eg, et))
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("qlora54_") and fn.endswith(".json")):
            continue
        r = json.load(io.open(os.path.join(HERE, fn), encoding="utf-8"))
        if len(r["folds"]) != 5:
            continue
        dec = r["probs"]
        gate, thr = fit(dec)
        secs = sum(f["train_s"] for f in r["folds"].values()) / 5
        print(f"\ndecoder {r['model']} {r['tag']}, seed {r['seed']} alone ({secs:.0f} s of training per fold): gate {gate}, threshold {thr:.2f}")
        table(lambda c, keep: V.picks(by(dec, c, keep), gate, thr))
        if not ens:
            continue

        def slow_path(c, keep):
            """The bot as it would be built: the ensemble answers; a line under its threshold goes to the decoder."""
            pe, pd = by(ens, c, keep), by(dec, c, keep)
            return {k: V.pick(pe[k], eg, et)[0] if V.pick(pe[k], eg, 0.0)[1] >= et else V.pick(pd[k], gate, thr)[0] for k in pe}

        asked = sum(V.pick(v, eg, 0.0)[1] < et for v in by(ens, "vctkB", spoken).values())
        print(f"the ensemble, and the decoder on the lines under the ensemble's threshold ({asked} of {len(by(ens, 'vctkB', spoken))} on unseen voices):")
        table(slow_path)
        both = avg([ens, dec])
        bg, bt = fit(both)
        print(f"the ensemble's and the decoder's probabilities averaged: gate {bg}, threshold {bt:.2f}")
        table(lambda c, keep: V.picks(by(both, c, keep), bg, bt))


if __name__ == "__main__":
    mode = sys.argv[1]
    tag = sys.argv[4] if len(sys.argv) > 4 else "r16"
    if mode == "folds":
        folds(sys.argv[2], int(sys.argv[3]), tag)
    elif mode == "final":
        final(sys.argv[2], int(sys.argv[3]), tag)
    elif mode == "timing":
        timing(sys.argv[2], int(sys.argv[3]))
    elif mode == "score":
        score()
    else:
        sys.exit(__doc__)
