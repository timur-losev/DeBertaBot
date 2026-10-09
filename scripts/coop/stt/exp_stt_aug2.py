"""The retraining idea for the chosen engine (Parakeet 0.6B v2), in full: lines and seed commands.

    python exp_stt_aug2.py HELD ARM          HELD: r6 | cs      ARM: base | aug

One held-out author, the project's recipe (train_v2.train_predict), three seeds.
  base   the project's training set for that fold: the other authors' typed lines + the 580 typed seed commands
  aug    base + what Parakeet heard, each with its known label:
           the other spoken author's lines read by the Windows, Kokoro and VCTK-pool-A voices
           the seed commands read by the same kinds of voices
         (a transcript equal to a line already in the set is not added twice)
Tested on the held-out author's lines: typed, and as Parakeet heard them. "vctkB" is the honest one: speakers that
are in no training set. Probabilities go to aug2_<held>_<arm>.json; nothing is written to the repository.
"""
import io, json, os, re, sys, time
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
import coop_v2 as V
import train_v2 as T

HERE = os.path.dirname(os.path.abspath(__file__))
HELD, ARM = sys.argv[1], sys.argv[2]
ENGINE = "parakeet-0.6b-v2"
LINE_CONDS = ["clean", "kokoro", "kokorox", "vctkA"]
SEED_CONDS = ["seedclean", "seedkokoro", "seedkokorox", "seedvctkA"]
TEST = ["vctkB", "kokoro", "kokorox", "clean"]
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()


def heard(cond):
    d = json.load(io.open(os.path.join(HERE, f"out_{ENGINE}_{cond}.json"), encoding="utf-8"))
    return {r["id"]: norm(r["text"]) for r in d["rows"]}


items, seeds = V.load_items(), V.seed_items()
spoken = [a for a in ("r6", "cs") if a != HELD][0]
train = [i for i in items if i["author"] != HELD] + seeds
added = {"lines": 0, "seeds": 0}
if ARM == "aug":
    have = {(i["text"], i["maj"]) for i in train if i["maj"]}
    for kind, conds, src in (("lines", LINE_CONDS, [i for i in items if i["author"] == spoken and i["maj"]]), ("seeds", SEED_CONDS, seeds)):
        for cond in conds:
            h = heard(cond)
            for i in src:
                t = h.get(i["id"], "")
                if t.strip() and (t, i["maj"]) not in have:
                    have.add((t, i["maj"]))
                    train.append({"id": f"{cond}|{i['id']}", "text": t, "maj": i["maj"]})
                    added[kind] += 1
held_items = [i for i in items if i["author"] == HELD and i["maj"]]
test = [{"id": f"typed|{i['id']}", "text": i["text"]} for i in held_items]
for cond in TEST:
    h = heard(cond)
    test += [{"id": f"{cond}@parakeet|{i['id']}", "text": h[i["id"]]} for i in held_items]
print(f"held {HELD} arm {ARM}: {len([i for i in train if i['maj']])} training lines (added from speech: {added}), {len(test)} test lines", flush=True)
t0 = time.time()
out = {}
for seed in T.SEEDS:
    probs, model, _ = T.train_predict("base", train, test, seed, "cuda")
    out[str(seed)] = probs
    del model
    torch.cuda.empty_cache()
    print(f"  seed {seed} done, {time.time() - t0:.0f}s", flush=True)
json.dump({"held": HELD, "arm": ARM, "engine": ENGINE, "added": added, "probs": out},
          io.open(os.path.join(HERE, f"aug2_{HELD}_{ARM}.json"), "w", encoding="utf-8"))
