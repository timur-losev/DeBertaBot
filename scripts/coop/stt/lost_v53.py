"""Where bot v53 lost against bot v52 on the lines both were checked on (out of fold, r6 and cs): is it the higher
threshold (the bot asks again) or new confusions (the bot acts on another order)? Truth: the v53 tag's (no line changed).

    python lost_v53.py > score_v53_lost.log
"""
import io, json, os, sys
from collections import Counter
os.environ["COOP_TAG"] = "v53"
COOP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, COOP)
import coop_v2 as V

items = {i["id"]: i for i in V.load_items() if i["maj"] and i["author"] in ("r6", "cs") and i["version"] != "v53"}
I53 = V.INTENTS
I52 = [k for k in json.load(io.open(os.path.join(COOP, "intents_v52.json"), encoding="utf-8")) if not k.startswith("_")]


def load(tag, labels):
    runs = [json.load(io.open(os.path.join(COOP, "stt", f"finaloof{tag}_{s}.json"), encoding="utf-8")) for s in (0, 1, 2)]
    out = {}
    for k in runs[0]["probs"]:
        p = [sum(r["probs"][k][j] for r in runs) / 3 for j in range(len(labels))]
        out[k] = [p[labels.index(x)] if x in labels else 0.0 for x in I53]      # in v53's label order
    return out


P52, P53 = load("52", I52), load("53", I53)
OLD = lambda i: i["version"].split("-")[0] not in ("v5", "v51", "v52")  # noqa: E731


def near(pick, it):
    return pick in it["accept"] or (pick != "NONE" and it["maj"] != "NONE" and V.FAMILY[pick] == V.FAMILY[it["maj"]]) or pick == it["maj"]


for title, keep in (("the 662 lines bot v52 was checked on", lambda i: True), ("the 422 older lines", OLD)):
    print(title)
    for c, label in (("typed", "typed"), ("clean", "Windows"), ("kokoro", "Kokoro EN"), ("kokorox", "Kokoro other"), ("vctkB", "VCTK unseen")):
        ids = [k for k, i in items.items() if keep(i) and f"{c}|{k}" in P52 and f"{c}|{k}" in P53]
        a = V.picks({k: P52[f"{c}|{k}"] for k in ids}, "family", 0.60)
        row = []
        for thr in (0.66, 0.60):
            b = V.picks({k: P53[f"{c}|{k}"] for k in ids}, "family", thr)
            lost = [k for k in ids if near(a[k], items[k]) and not near(b[k], items[k])]
            won = [k for k in ids if not near(a[k], items[k]) and near(b[k], items[k])]
            quiet = sum(b[k] == "NONE" for k in lost)
            to = Counter(b[k] for k in lost if b[k] != "NONE")
            row.append(f"v53 at {thr:.2f}: lost {len(lost)} (does nothing on {quiet}; acts on " + (", ".join(f"{x} {n}" for x, n in to.most_common(4)) or "-") + f"), won {len(won)}")
        print(f"  {label:<13} n={len(ids)}  " + " | ".join(row))
