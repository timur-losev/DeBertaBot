"""Does training the classifier on speech-to-text output (with the line's known label) repair what the STT breaks?

    python exp_stt_aug.py HELD ARM [ENGINE]        HELD: r6 | cs      ARM: base | aug

One held-out author, the project's recipe (train_v2.train_predict), three seeds.
  base   the project's training set for that fold: the other authors' typed lines + the seed commands
  aug    base + what ENGINE heard when the OTHER spoken author's lines were read by the Windows and Kokoro voices
         (clean, noisy, kokoro, kokorox), each with its line's label
Tested on the held-out author's lines: typed, and as ENGINE heard them. The VCTK voices are in no training set
(another synthesizer, other speakers), so "vctk" is the test of whether the repair carries over to unheard voices.
Nothing is written to the repository; probabilities go to aug_<held>_<arm>.json next to this file.
"""
import io, json, os, re, sys, time
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
import coop_v2 as V
import train_v2 as T

HERE = os.path.dirname(os.path.abspath(__file__))
HELD, ARM = sys.argv[1], sys.argv[2]
ENGINE = sys.argv[3] if len(sys.argv) > 3 else "zipformer-kroko25"
TRAIN_CONDS = ["clean", "noisy", "kokoro", "kokorox"]
TEST = [("vctk", ENGINE), ("kokoro", ENGINE), ("kokorox", ENGINE), ("clean", ENGINE), ("noisy", ENGINE), ("vctk", "parakeet-0.6b-v2")]
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()


def heard(engine, cond):
    d = json.load(io.open(os.path.join(HERE, f"out_{engine}_{cond}.json"), encoding="utf-8"))
    return {r["id"]: norm(r["text"]) for r in d["rows"]}


items, seeds = V.load_items(), V.seed_items()
spoken = [a for a in ("r6", "cs") if a != HELD][0]          # the other author that has audio
train = [i for i in items if i["author"] != HELD] + seeds
if ARM == "aug":
    for cond in TRAIN_CONDS:
        h = heard(ENGINE, cond)
        train += [{"id": f"{cond}|{i['id']}", "text": h[i["id"]], "maj": i["maj"]}
                  for i in items if i["author"] == spoken and i["maj"] and h.get(i["id"], "").strip()]
held_items = [i for i in items if i["author"] == HELD and i["maj"]]
test = [{"id": f"typed|{i['id']}", "text": i["text"]} for i in held_items]
for cond, engine in TEST:
    h = heard(engine, cond)
    test += [{"id": f"{cond}@{engine}|{i['id']}", "text": h[i["id"]]} for i in held_items]
print(f"held {HELD} arm {ARM}: {len([i for i in train if i['maj']])} training lines, {len(test)} test lines", flush=True)
t0 = time.time()
out = {}
for seed in T.SEEDS:
    probs, model, _ = T.train_predict("base", train, test, seed, "cuda")
    out[str(seed)] = probs
    del model
    torch.cuda.empty_cache()
    print(f"  seed {seed} done, {time.time() - t0:.0f}s", flush=True)
json.dump({"held": HELD, "arm": ARM, "engine": ENGINE, "probs": out},
          io.open(os.path.join(HERE, f"aug_{HELD}_{ARM}.json"), "w", encoding="utf-8"))
