"""Bot v5 for the Parakeet chain: build_v4.py's recipe on the v5 data (COOP_TAG=v5: 27 intents -- ATTACK, OPEN_FIRE and
HOLD_FIRE are new -- the older lines with their v5 truth, the v5 lines, seed_commands_v5.json).

  lines        all three authors (r6, cs, stt), typed: the 633 older lines and the v5 lines
  seeds        the seed commands of seed_commands_v5.json, typed
  transcripts  what Parakeet TDT 0.6B v2 heard when the r6 and cs lines and the seed commands were read by the
               training voices (Windows, Kokoro English, Kokoro other-language, VCTK pool A): v4's transcripts plus
               the ones of the v5 additions (out_*_v5.json); lowercased, final .!? stripped, inner punctuation kept;
               one copy of each (text, label). A transcript carries the label its line has under v5.
  epochs       12 (as v4)

    python build_v5.py oof SEED       five folds over lines + seeds; a held-out line is unseen typed and spoken
    python build_v5.py final SEED     one model on everything -> models/coop-deberta-v3-ens3-v5/seed<SEED>

VCTK pool B reads test lines only. Run from the jev environment (torch): see README.md.
"""
import io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v5"
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
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v5"))
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()
_heard = {}


def heard(cond):
    """line or seed id -> what Parakeet heard under this condition: v4's audio and the v5 additions."""
    if cond not in _heard:
        h = {}
        for tag in ("", "_v5"):
            d = json.load(io.open(os.path.join(HERE, f"out_{ENGINE}_{cond}{tag}.json"), encoding="utf-8"))
            h.update({r["id"]: norm(r["text"]) for r in d["rows"]})
        _heard[cond] = h
    return _heard[cond]


LINES = [i for i in V.load_items() if i["maj"]]
SPOKEN = {i["id"] for i in LINES if i["author"] in ("r6", "cs")}
SEEDS = V.seed_items()
for _c in LINE_TRAIN + LINE_TEST:
    assert SPOKEN <= set(heard(_c)), (_c, sorted(SPOKEN - set(heard(_c)))[:5])
for _c in SEED_TRAIN:
    assert {s["id"] for s in SEEDS} <= set(heard(_c)), _c


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


if __name__ == "__main__":
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
        json.dump({"seed": seed, "epochs": EPOCHS, "probs": out}, io.open(os.path.join(HERE, f"finaloof5_{seed}.json"), "w", encoding="utf-8"))
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
