"""The bot for the Parakeet chain, built the project's way (train_v2.final: 15 out-of-fold trainings for the gate and
threshold, 3 final models), on the data the comparisons favoured:

  lines        all three authors (r6, cs, stt), typed: 633
  seeds        the 580 seed commands, typed
  transcripts  what Parakeet TDT 0.6B v2 heard when the r6 and cs lines and the seed commands were read by the
               training voices (Windows, Kokoro English, Kokoro other-language, VCTK pool A); lowercased, final .!?
               stripped, inner punctuation kept (dropping it cost 4-10 points); one copy of each (text, label)
  epochs       12 instead of 20 (EPOCHS): on this much data 12 lost nothing against 20, 8 did

    python build_v4.py oof SEED       five folds over lines + seeds; a held-out line is unseen typed and spoken
    python build_v4.py final SEED     one model on everything -> models/coop-deberta-v3-ens3-v4/seed<SEED>

VCTK pool B reads test lines only. Run from the jev environment (torch): see README.md.
"""
import io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
import coop_v2 as V
import train_v2 as T

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = "parakeet-0.6b-v2"
EPOCHS = 12
LINE_TRAIN = ["clean", "kokoro", "kokorox", "vctkA"]
SEED_TRAIN = ["seedclean", "seedkokoro", "seedkokorox", "seedvctkA"]
LINE_TEST = ["vctkB", "vctkA", "kokoro", "kokorox", "clean"]
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v4"))
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()
_heard = {}


def heard(cond):
    if cond not in _heard:
        d = json.load(io.open(os.path.join(HERE, f"out_{ENGINE}_{cond}.json"), encoding="utf-8"))
        _heard[cond] = {r["id"]: norm(r["text"]) for r in d["rows"]}
    return _heard[cond]


LINES = [i for i in V.load_items() if i["maj"]]
SPOKEN = {i["id"] for i in LINES if i["author"] in ("r6", "cs")}
SEEDS = V.seed_items()


def training_set(lines, seeds):
    out = [{"id": i["id"], "text": i["text"], "maj": i["maj"]} for i in lines + seeds]
    have = {(i["text"], i["maj"]) for i in out}
    for conds, src in ((LINE_TRAIN, [i for i in lines if i["id"] in SPOKEN]), (SEED_TRAIN, seeds)):
        for cond in conds:
            h = heard(cond)
            for i in src:
                t = h.get(i["id"], "")
                if t.strip() and (t, i["maj"]) not in have:
                    have.add((t, i["maj"]))
                    out.append({"id": f"{cond}|{i['id']}", "text": t, "maj": i["maj"]})
    return out


def steps(n):
    return (n + T.HP["batch"] - 1) // T.HP["batch"]


mode, seed = sys.argv[1], int(sys.argv[2])
t0 = time.time()
if mode == "oof":
    groups = LINES + SEEDS
    random.Random(1000 + seed).shuffle(groups)
    full = EPOCHS * steps(len(training_set(LINES, SEEDS)))
    out = {}
    for f in range(5):
        held = {g["id"] for g in groups[f::5]}
        train = training_set([i for i in LINES if i["id"] not in held], [s for s in SEEDS if s["id"] not in held])
        test = []
        for i in LINES:
            if i["id"] in held:
                test.append({"id": f"typed|{i['id']}", "text": i["text"]})
                if i["id"] in SPOKEN:
                    test += [{"id": f"{c}|{i['id']}", "text": heard(c)[i["id"]]} for c in LINE_TEST]
        ep = max(1, round(full / steps(len(train))))
        probs, model, _ = T.train_predict("base", train, test, seed, "cuda", epochs=ep)
        out.update(probs)
        del model
        torch.cuda.empty_cache()
        print(f"oof seed {seed} fold {f}: {len(train)} training lines, {ep} epochs, {len(test)} test lines, {time.time() - t0:.0f}s", flush=True)
    json.dump({"seed": seed, "epochs": EPOCHS, "probs": out}, io.open(os.path.join(HERE, f"finaloof_{seed}.json"), "w", encoding="utf-8"))
else:
    train = training_set(LINES, SEEDS)
    _, model, tok = T.train_predict("base", train, [{"id": "x", "text": "go"}], seed, "cuda", epochs=EPOCHS)
    d = os.path.join(OUT_DIR, f"seed{seed}")
    os.makedirs(d, exist_ok=True)
    model.to("cpu").save_pretrained(d, safe_serialization=True)
    tok.save_pretrained(d)
    json.dump({"training_lines": len(train), "typed_lines": len(LINES), "seeds": len(SEEDS), "epochs": EPOCHS},
              io.open(os.path.join(d, "trained_on.json"), "w"))
    print(f"final seed {seed}: {len(train)} training lines ({len(LINES)} lines + {len(SEEDS)} seeds typed, "
          f"{len(train) - len(LINES) - len(SEEDS)} heard by Parakeet), {EPOCHS} epochs, saved, {time.time() - t0:.0f}s", flush=True)
