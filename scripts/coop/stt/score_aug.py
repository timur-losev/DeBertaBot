"""exp_stt_aug.py results: the three seeds averaged (as the bot does), the bot's gate, strict project scoring.
base = today's training set, aug = + speech-to-text output with known labels. Both held-out authors pooled (422 lines)."""
import io, json, os, random, sys
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
items = {i["id"]: i for i in V.load_items()}
GATE, THR = "family", 0.62
PREFIX = sys.argv[1] if len(sys.argv) > 1 else "aug"
runs = {}
for held in ("r6", "cs"):
    for arm in ("base", "aug"):
        p = os.path.join(HERE, f"{PREFIX}_{held}_{arm}.json")
        if os.path.exists(p):
            d = json.load(io.open(p, encoding="utf-8"))["probs"]
            seeds = list(d)
            runs[held, arm] = {k: [sum(d[s][k][j] for s in seeds) / len(seeds) for j in range(len(V.INTENTS))] for k in d[seeds[0]]}
sets = sorted({k.split("|")[0] for r in runs.values() for k in r}, key=lambda s: (s != "typed", "vctk" not in s, s))


def lines(arm, name, thr):
    """per line: (near, wrong family, is a non-order, acted) for both held-out authors"""
    out = {}
    for held in ("r6", "cs"):
        for k, row in runs.get((held, arm), {}).items():
            s, lid = k.split("|", 1)
            if s != name:
                continue
            it = items[lid]
            p = V.pick(row, GATE, thr)[0]
            good = p in it["accept"] or V.FAMILY[p] == V.FAMILY[it["maj"]]
            out[lid] = (good, (not good) and p != "NONE", it["maj"] == "NONE", p != "NONE")
    return out


def summary(L):
    n = len(L)
    near = sum(v[0] for v in L.values()); wf = sum(v[1] for v in L.values())
    non = [v for v in L.values() if v[2]]
    return 100 * near / n, 100 * wf / n, 100 * sum(v[3] for v in non) / max(1, len(non)), 100 * (near - 2 * wf) / n


def best(arm, name):
    return max(summary(lines(arm, name, t / 100))[3] for t in range(0, 100, 2))


print(f"gate {GATE}, threshold {THR} (the shipped bot's, not re-fitted to these models); n = lines of both held-out authors")
print(f"{'what the classifier is given':34s} {'arm':5s} {'near':>6s} {'wrong fam':>10s} {'acts on non-order':>18s} {'criterion':>10s} {'best thr crit':>14s}")
rng = random.Random(0)
for name in sets:
    B, A = lines("base", name, THR), lines("aug", name, THR)
    for arm, L in (("base", B), ("aug", A)):
        if L:
            s = summary(L)
            print(f"{name:34s} {arm:5s} {s[0]:6.1f} {s[1]:9.1f}% {s[2]:17.1f}% {s[3]:10.1f} {best(arm, name):14.1f}   n={len(L)}")
    if A and B and set(A) == set(B):
        ids = list(A)
        d = [(A[k][0] - 2 * A[k][1]) - (B[k][0] - 2 * B[k][1]) for k in ids]
        boots = sorted(100 * sum(rng.choice(d) for _ in ids) / len(ids) for _ in range(2000))
        print(f"{'':34s} aug - base criterion: {100 * sum(d) / len(d):+.1f} [{boots[49]:+.1f}, {boots[1949]:+.1f}]"
              f"   lines fixed {sum(x > 0 for x in d)}, broken {sum(x < 0 for x in d)}")
