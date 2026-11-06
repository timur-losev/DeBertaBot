"""Classifier vNN on the owner's own lines from the game as the recognizer heard them (owner_lines_v61/v64/v65/v66.json), out of
fold: each line read by models that never saw it (finaloofNN_{0,1,2}.json of the build), three seeds averaged, gate family,
threshold 0.66, as the game reads. Per different line and per time said: right intent, said again, wrong family, and the
precision when the bot acts (README.md, "Measured results").

    python score_owner_oof.py v67
"""
import io, json, os, sys
TAG = sys.argv[1]
os.environ["COOP_TAG"] = TAG
COOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STT = os.path.join(COOP, "stt")
sys.path.insert(0, COOP)
import coop_v2 as V
runs = [json.load(io.open(os.path.join(STT, f"finaloof{TAG[1:]}_{s}.json"), encoding="utf-8"))["probs"] for s in (0, 1, 2)]
probs = {}
for r in runs:
    for k, v in r.items():
        if k.startswith("owner|"):
            probs.setdefault(k.split("|", 1)[1], []).append(v)
probs = {k: [sum(x[j] for x in v) / 3 for j in range(len(V.INTENTS))] for k, v in probs.items() if len(v) == 3}
files = ["owner_lines_v61.json", "owner_lines_v64.json", "owner_lines_v65.json"] + (["owner_lines_v66.json"] if TAG != "v65" else [])
owner = []
for f in files:
    owner += json.load(io.open(os.path.join(COOP, f), encoding="utf-8"))["items"]
rel = {}
for v in ("v62", "v64", "v65"):
    rel.update(json.load(io.open(os.path.join(COOP, "annot", v, f"relabel_{v}.json"), encoding="utf-8"))["owner"])
owner = [dict(o, maj=rel[o["id"]]["to"]) if o["id"] in rel else o for o in owner]
assert all(o["id"] in probs for o in owner), "missing owner probs"
out = {"tag": TAG, "intents": len(V.INTENTS), "sets": {}}
def stats(items, weight):
    n = right = again = wrongfam = wrongsame = acted = acted_right = 0
    per = {}
    for o in items:
        p = V.pick(probs[o["id"]], "family", 0.66)[0]
        w = weight(o)
        n += w
        ok = p == o["maj"]
        right += w * ok
        if p != "NONE":
            acted += w
            acted_right += w * ok
            d = per.setdefault(p, [0, 0]); d[0] += w; d[1] += w * ok
        if not ok:
            if p == "NONE":
                again += w
            elif V.FAMILY.get(p) != V.FAMILY.get(o["maj"]):
                wrongfam += w
            else:
                wrongsame += w
    macro = sum(c / t for t, c in per.values()) / len(per) if per else 0
    return {"n": n, "accuracy": 100 * right / n, "precision_when_acting": 100 * acted_right / acted if acted else 0,
            "macro_precision": 100 * macro, "say_again": 100 * again / n, "wrong_family": 100 * wrongfam / n,
            "wrong_same_family": 100 * wrongsame / n, "acted": 100 * acted / n}
common = [o for o in owner if not o["id"].startswith("owner66_")]
v66 = [o for o in owner if o["id"].startswith("owner66_")]
out["sets"]["common_per_line"] = stats(common, lambda o: 1)
out["sets"]["common_per_time_said"] = stats(common, lambda o: o["count"])
if v66:
    out["sets"]["v66_lines"] = stats(v66, lambda o: 1)
    out["sets"]["all_per_line"] = stats(owner, lambda o: 1)
print(json.dumps(out, ensure_ascii=False))
