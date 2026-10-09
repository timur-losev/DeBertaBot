"""How many epochs does the classifier need? Same data (r6, cs, stt + seeds + Parakeet transcripts), same seed and folds,
only the length of training differs. Each variant gets its own fitted gate and threshold, as in r6_score.py."""
import io, json, os, sys
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V
HERE = os.path.dirname(os.path.abspath(__file__))
items = {i["id"]: i for i in V.load_items() if i["author"] == "r6" and i["maj"]}
FIT = ["clean", "kokoro", "kokorox", "vctkA"]
CONDS = ["typed", "clean", "kokoro", "kokorox", "vctkA", "vctkB"]
by = lambda probs, c: {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == c}
def fit(probs):
    best = None
    for gate in ("top", "family"):
        for t in range(0, 100, 2):
            near = cross = 0
            for c in FIT:
                p = by(probs, c); s = V.score(V.picks(p, gate, t / 100), [items[k] for k in p])
                near += s["near_count"]; cross += s["cross_count"]
            v = near - 2 * cross
            if best is None or v > best[0] or (v == best[0] and gate == "top" and best[1] != "top"):
                best = (v, gate, t / 100)
    return best[1], best[2]
print(f"{'epochs':>8s} {'gate/thr':>12s} | " + " | ".join(f"{c:>8s}" for c in CONDS) + " |  wrong family on vctkB, acts on non-orders on vctkB")
for name, label in (("csstt-e5", "~5"), ("csstt-e8", "~8"), ("csstt-e12", "~12"), ("csstt", "20")):
    p = os.path.join(HERE, f"r6oof_{name}_0.json")
    if not os.path.exists(p): continue
    probs = json.load(io.open(p, encoding="utf-8"))["probs"]
    g, t = fit(probs)
    row = []
    for c in CONDS:
        q = by(probs, c); s = V.score(V.picks(q, g, t), [items[k] for k in q])
        row.append(100 * (s["near"] - 2 * s["cross"]))
        last = s
    print(f"{label:>8s} {g + ' ' + format(t, '.2f'):>12s} | " + " | ".join(f"{x:8.1f}" for x in row) + f" |  {100 * last['cross']:.1f}%, {100 * last['fired_on_nonorder']:.1f}%")
