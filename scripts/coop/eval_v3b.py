"""
The second batch of place lines (blind/v3b: the same three author personas, 50 lines each, author +
2 annotators), written after rule set v3 and seed set v31 were fixed and logged. No rule and no
model was fitted to these lines, so for all of them this is a blind test:

A. The matcher, rule sets v1, v2 and v3 side by side ("exact" and "usable on orders" as in eval_v3.py).
B. Every bot that v3b_shipped.py has run (results_v3b_<bot>.json), each at its own gate and
   threshold: near-correct, wrong family, score = near - 2 x wrong family; paired differences
   between bots, bootstrap over lines.
C. Both together, the question the planner cares about: on order lines, the bot acted in the right
   family AND the matcher handed it a usable destination.

Caveats that do not go away: the authors and annotators are the same model family as the developer,
and the same three personas wrote the first batch, which rule set v3 and seed set v31 were written
after reading.

    python eval_v3b.py        # base anaconda python (after v3b_shipped.py for section B)
"""
import glob, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eval_v3 as E  # noqa: E402  (its loaders and tables; it sets COOP_TAG)

V = E.V
ITEMS = V.load_v3b()


def matcher():
    out = {}
    for name in ("v1", "v2", None):
        loc = E.load_rules(name)
        label = name or f"v{loc.VOCAB['version']}"
        rows = E.match_rows(ITEMS, loc)
        print(f"\nA. MATCHER, rule set {label}, on {len(ITEMS)} v3b lines (readers agree on the whole target on "
              f"{sum(i['target_agreed'] for i in ITEMS)}, unanimously on {sum(i['target_unanimous'] for i in ITEMS)})")
        E.matcher_table(rows, V.AUTHORS, mismatches=name is None)
        out[label] = E.summary(rows, V.AUTHORS)
        out[label]["rows"] = {r["it"]["id"]: {"exact": r["exact"], "usable": r["usable"]} for r in rows}
    return out


def bots():
    res = {}
    for p in sorted(glob.glob(os.path.join(HERE, "results_v3b_*.json"))):
        R = json.load(io.open(p, encoding="utf-8"))
        if "probs" in R and set(R["probs"]) == {i["id"] for i in ITEMS}:
            res[R["model"]] = R
    if not res:
        print("\nB. (run v3b_shipped.py first)")
        return {}
    print(f"\nB. BOTS on the {len(ITEMS)} v3b lines, each at its own gate and threshold (score = near - 2 x wrong family)")
    preds = {}
    for name, R in res.items():
        preds[name] = {k: V.pick(row, R["gate"], R["threshold"])[0] for k, row in R["probs"].items()}
        E.show(f"{name} ({R['gate']} {R['threshold']})", preds[name], ITEMS)
        for a in V.AUTHORS:
            sl = [i for i in ITEMS if i["author"] == a]
            s = V.score(preds[name], sl)
            print(f"      author {a:<3} n={len(sl)}: near {100 * s['near']:5.1f}  wrong family {100 * s['cross']:4.1f}")
    names = list(res)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            d = E.bootstrap(E.per_item(preds[names[b]], ITEMS), E.per_item(preds[names[a]], ITEMS), ITEMS)
            print(f"  {names[b]} - {names[a]}, score: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]; answers that differ: "
                  f"{sum(preds[names[a]][i['id']] != preds[names[b]][i['id']] for i in ITEMS)}")
    for name in names:
        print(f"  {name}, not near-correct (truth -> pick):")
        for i in ITEMS:
            x = preds[name][i["id"]]
            if not (x in i["accept"] or (i["maj"] and V.FAMILY[x] == V.FAMILY[i["maj"]])):
                print(f"    {i['id']:<10} {i['kind']:<11} {i['maj']} -> {x:<14} {i['text']!r}")
    return preds


def together(m, preds):
    if not preds:
        return
    orders = [i for i in ITEMS if E.ORDER(i)]
    print(f"\nC. ORDER LINES ({len(orders)}): the bot acts in the right family AND the matcher (rule set v3) gives a usable destination")
    rows = m[[k for k in m if k not in ("v1", "v2")][0]]["rows"]
    for name, p in preds.items():
        good = [i for i in orders if p[i["id"]] in i["accept"] or V.FAMILY[p[i["id"]]] == V.FAMILY[i["maj"]]]
        both = [i for i in good if rows[i["id"]]["usable"]]
        print(f"  {name:<34} intent near {E.pct(len(good), len(orders))}   and a usable place {E.pct(len(both), len(orders))}")


def main():
    if not ITEMS:
        sys.exit("no blind/v3b lines yet")
    from collections import Counter
    print(f"v3b lines: {len(ITEMS)}; majority intent on {sum(bool(i['maj']) for i in ITEMS)}, unanimous on "
          f"{sum(i['unanimous'] for i in ITEMS)}; intents {dict(Counter(i['maj'] for i in ITEMS).most_common())}")
    m = matcher()
    preds = bots()
    together(m, preds)
    for v in m.values():
        v.pop("rows", None)
    json.dump({"matcher": m}, io.open(os.path.join(HERE, "results_v3b_matcher.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
