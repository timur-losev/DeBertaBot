"""The simplified plan: only the r6 author's lines and the seed commands, voiced, heard by Parakeet 0.6B v2, and the
classifier trained on what Parakeet heard (the typed lines stay in too). No "stt" author anywhere.

    python r6_build.py oof SEED ARM      five folds: every r6 line is predicted by a model that never saw it,
                                         typed or spoken. Writes r6oof_<arm>_<seed>.json
    python r6_build.py final SEED        one model on everything, saved under models_out/

ARM
  main   r6 lines + seed commands, typed and as Parakeet heard them from the training voices
  base   the same lines typed only (what training on speech adds)
  cs     main + the cs author's lines, typed and heard (what leaving cs out costs); cs lines are never held out

Voices: Windows, Kokoro (English and other-language voices) and VCTK pool A are training voices; VCTK pool B reads
only test lines. The recipe is the project's (train_v2.train_predict); a fold trains for as many optimizer steps as
a model on the whole set, as train_v2.oof does. Nothing is written to the repository.
"""
import io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
import coop_v2 as V
import train_v2 as T

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = "parakeet-0.6b-v2"
LINE_TRAIN = ["clean", "kokoro", "kokorox", "vctkA"]
SEED_TRAIN = ["seedclean", "seedkokoro", "seedkokorox", "seedvctkA"]
LINE_TEST = ["vctkB", "vctkA", "kokoro", "kokorox", "clean"]
OUT_DIR = os.path.join(HERE, "models_out", "coop-deberta-v3-ens3-r6stt")
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()
fnorm = lambda t: " ".join(re.sub(r"[^a-z0-9' ]+", " ", t.lower().replace("\u2019", "'")).split())
FULL = len(sys.argv) > 3 and sys.argv[3].endswith("norm")
tx = fnorm if FULL else (lambda t: t)
_heard = {}


def heard(cond):
    if cond not in _heard:
        d = json.load(io.open(os.path.join(HERE, f"out_{ENGINE}_{cond}.json"), encoding="utf-8"))
        _heard[cond] = {r["id"]: norm(r["text"]) for r in d["rows"]}
    return _heard[cond]


items = [i for i in V.load_items() if i["maj"]]
R6 = [i for i in items if i["author"] == "r6"]
CS = [i for i in items if i["author"] == "cs"]
STT = [i for i in items if i["author"] == "stt"]
EXTRA = {"main": [], "base": [], "cs": CS, "csstt": CS + STT, "csnorm": CS}
SEEDS = V.seed_items()


def training_set(arm, lines, seeds):
    """typed lines, plus (not for 'base') what Parakeet heard of them; one copy of each (text, label)"""
    out = [{"id": i["id"], "text": tx(i["text"]), "maj": i["maj"]} for i in lines + seeds]
    if FULL:   # normalized lines can coincide; the other arms keep the set exactly as before
        out = list({(o["text"], o["maj"]): o for o in out}.values())
    if arm == "base":
        return out
    have = {(i["text"], i["maj"]) for i in out}
    for conds, src in ((LINE_TRAIN, lines), (SEED_TRAIN, seeds)):
        for cond in conds:
            h = heard(cond)
            for i in src:
                t = tx(h.get(i["id"], ""))
                if t.strip() and (t, i["maj"]) not in have:
                    have.add((t, i["maj"]))
                    out.append({"id": f"{cond}|{i['id']}", "text": t, "maj": i["maj"]})
    return out


def steps(n):
    return (n + T.HP["batch"] - 1) // T.HP["batch"]


if sys.argv[1] == "sizes":
    for arm, extra in (("base", []), ("main", []), ("cs", CS)):
        tr = training_set(arm, R6 + extra, SEEDS)
        print(f"{arm}: {len(tr)} training lines = {len(R6 + extra)} lines + {len(SEEDS)} seeds typed + {len(tr) - len(R6 + extra) - len(SEEDS)} heard by Parakeet; "
              f"{T.HP['epochs'] * steps(len(tr))} optimizer steps")
    for c in LINE_TRAIN + ["vctkB"]:
        h = heard(c)
        print(f"   {c}: {sum(h[i['id']] != norm(i['text']) for i in R6)} of {len(R6)} r6 lines heard differently from the typed text")
    for c in SEED_TRAIN:
        h = heard(c)
        print(f"   {c}: {sum(h[s['id']] != norm(s['text']) for s in SEEDS)} of {len(SEEDS)} seed commands heard differently")
    sys.exit(0)
mode, seed = sys.argv[1], int(sys.argv[2])
t0 = time.time()
if mode == "oof":
    arm = sys.argv[3]
    extra = EXTRA[arm]
    groups = R6 + SEEDS
    random.Random(1000 + seed).shuffle(groups)
    full = T.HP["epochs"] * steps(len(training_set(arm, R6 + extra, SEEDS)))
    out = {}
    for f in range(5):
        held = {g["id"] for g in groups[f::5]}
        train = training_set(arm, [i for i in R6 if i["id"] not in held] + extra, [s for s in SEEDS if s["id"] not in held])
        test = []
        for i in R6:
            if i["id"] in held:
                test.append({"id": f"typed|{i['id']}", "text": tx(i["text"])})
                test += [{"id": f"{c}|{i['id']}", "text": tx(heard(c)[i["id"]])} for c in LINE_TEST]
        ep = max(1, round(float(os.environ.get("EPOCH_SCALE", "1")) * full / steps(len(train))))
        probs, model, _ = T.train_predict("base", train, test, seed, "cuda", epochs=ep)
        out.update(probs)
        del model
        torch.cuda.empty_cache()
        print(f"oof {arm} seed {seed} fold {f}: {len(train)} training lines, {ep} epochs, {len(test)} test lines, {time.time() - t0:.0f}s", flush=True)
    json.dump({"arm": arm, "seed": seed, "probs": out}, io.open(os.path.join(HERE, f"r6oof_{arm}{os.environ.get('ARM_SUFFIX', '')}_{seed}.json"), "w", encoding="utf-8"))
else:
    arm = sys.argv[3] if len(sys.argv) > 3 else "main"
    OUT_DIR = OUT_DIR if arm == "main" else os.path.join(HERE, "models_out", f"coop-deberta-v3-ens3-r6{arm}-stt")
    train = training_set(arm, R6 + EXTRA[arm], SEEDS)
    _, model, tok = T.train_predict("base", train, [{"id": "x", "text": "go"}], seed, "cuda")
    d = os.path.join(OUT_DIR, f"seed{seed}")
    os.makedirs(d, exist_ok=True)
    model.to("cpu").save_pretrained(d, safe_serialization=True)
    tok.save_pretrained(d)
    json.dump({"arm": arm, "training_lines": len(train), "typed": len(R6 + EXTRA[arm]) + len(SEEDS)}, io.open(os.path.join(d, "trained_on.json"), "w"))
    print(f"final {arm} seed {seed}: {len(train)} training lines ({len(R6 + EXTRA[arm])} lines + {len(SEEDS)} seeds typed, the rest heard by Parakeet), saved, {time.time() - t0:.0f}s", flush=True)
