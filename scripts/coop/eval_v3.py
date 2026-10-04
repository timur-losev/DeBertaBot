"""
v3: orders that name a place on the map (blind/v3, 3 authors x 50 lines, author + 2 annotators).

A. The matcher (locations.py, rules frozen before the lines existed): its primary target against the
   readers' target -- per field the value two of three readers give. "exact" = object, qualifier and
   zone all equal. Also whether the readers' target is anywhere in the matcher's list (extraction
   right, choice of primary wrong) and how the "unknown_modifier" flag does.
B. The classifier the game ships (never saw a v3 line): intent on the v3 lines, reading the raw line
   or the line with attached qualifiers stripped (v3_shipped.py), at the shipped gate and threshold.
C. Re-training with the v3 lines and the location seeds (train_v2.py cv under COOP_TAG=v3: leave one
   author out, out-of-fold threshold per fold), three base seeds averaged; against B on the v3
   lines, and against the v21 study on the old lines (does adding places cost anything there).

    COOP_TAG=v3 python eval_v3.py        # base anaconda python
"""
import importlib, io, json, os, random, statistics, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["COOP_TAG"] = "v3"
import coop_v2 as V  # noqa: E402
import locations as LOC  # noqa: E402

ITEMS = V.load_items()
V3 = [i for i in ITEMS if i["version"] == "v3"]


def pct(a, b):
    return f"{100 * a / max(b, 1):5.1f}% ({a}/{b})"


def matcher():
    print(f"A. MATCHER on {len(V3)} v3 lines (readers agree on the whole target on "
          f"{sum(i['target_agreed'] for i in V3)}, unanimously on {sum(i['target_unanimous'] for i in V3)})")
    rows = []
    for it in V3:
        r = LOC.find(it["text"])
        t = r["target"]
        got = (t["object"], t["qualifier"], t["zone"]) if t else (None, None, None)
        allt = [(x["object"], x["qualifier"], x["zone"]) for x in r["targets"]]
        rows.append({"it": it, "got": got, "exact": got == it["target"], "in_list": it["target"] in allt or
                     it["target"] == (None, None, None) and not allt,
                     "flag": bool(t and t["flag"] == "unknown_modifier"), "t": t,
                     "fields": [got[k] == it["target"][k] for k in range(3)]})

    def line(name, rs):
        n = len(rs)
        return (f"  {name:<22} exact {pct(sum(r['exact'] for r in rs), n)}   object {pct(sum(r['fields'][0] for r in rs), n)}"
                f"   qualifier {pct(sum(r['fields'][1] for r in rs), n)}   zone {pct(sum(r['fields'][2] for r in rs), n)}"
                f"   truth in list {pct(sum(r['in_list'] for r in rs), n)}")

    print(line("all", rows))
    for a in V.AUTHORS:
        print(line(f"author {a}", [r for r in rows if r["it"]["author"] == a]))
    for k in sorted({r["it"]["kind"] for r in rows}):
        print(line(f"kind {k}", [r for r in rows if r["it"]["kind"] == k]))
    print(line("readers agreed", [r for r in rows if r["it"]["target_agreed"]]))
    tp = sum(r["flag"] and r["it"]["unknown_modifier"] for r in rows)
    print(f"  unknown_modifier flag: raised on {sum(r['flag'] for r in rows)} lines, the readers mark "
          f"{sum(r['it']['unknown_modifier'] for r in rows)}; both {tp}")
    print("  mismatches (author kind | text | readers -> matcher):")
    for r in rows:
        if not r["exact"]:
            it = r["it"]
            print(f"    {it['id']:<10} {it['kind']:<11} {it['text']!r}\n{'':17}{it['target']} -> {r['got']}"
                  f"{'' if not r['t'] else '  role=' + str(r['t']['role']) + ' flag=' + str(r['t']['flag'])}"
                  f"{'  [truth is in the list]' if r['in_list'] else ''}")
    old = [i for i in ITEMS if i["version"] != "v3"]
    print(f"  on the {len(old)} older lines the matcher finds a target in {sum(LOC.find(i['text'])['target'] is not None for i in old)}")
    return {"exact": sum(r["exact"] for r in rows) / len(rows), "n": len(rows),
            "per_author": {a: sum(r["exact"] for r in rows if r["it"]["author"] == a) /
                           max(1, sum(r["it"]["author"] == a for r in rows)) for a in V.AUTHORS},
            "in_list": sum(r["in_list"] for r in rows) / len(rows)}


def per_item(preds, sl):
    out = {}
    for i in sl:
        x = preds[i["id"]]
        good = x in i["accept"] or bool(i["maj"] and V.FAMILY[x] == V.FAMILY[i["maj"]])
        out[i["id"]] = int(good) - 2 * int(not good and x != "NONE")
    return out


def bootstrap(a, b, sl, reps=4000, seed=0):
    d = [a[i["id"]] - b[i["id"]] for i in sl]
    rng = random.Random(seed)
    boots = sorted(statistics.fmean(d[rng.randrange(len(d))] for _ in d) for _ in range(reps))
    return 100 * statistics.fmean(d), 100 * boots[int(0.025 * reps)], 100 * boots[int(0.975 * reps)]


def show(name, preds, sl):
    s = V.score(preds, sl)
    print(f"  {name:<34} near {100 * s['near']:5.1f}  exact ok {100 * s['ok']:5.1f}  wrong family {100 * s['cross']:4.1f}"
          f"  acts on non-order {100 * s['fired_on_nonorder']:5.1f}  score {100 * (s['near'] - 2 * s['cross']):5.1f}")
    return s


def shipped():
    p = os.path.join(HERE, "results_v3_shipped.json")
    if not os.path.exists(p):
        print("\nB. (run v3_shipped.py first)")
        return None
    R = json.load(io.open(p, encoding="utf-8"))
    print(f"\nB. SHIPPED BOT ({R['model']}, {R['gate']} gate, threshold {R['threshold']}) on the {len(V3)} v3 lines it never saw")
    preds = {}
    for mode in ("raw", "strip"):
        preds[mode] = {k: V.pick(row, R["gate"], R["threshold"])[0] for k, row in R[mode].items()}
        show(f"input: {mode}", preds[mode], V3)
    d = bootstrap(per_item(preds["strip"], V3), per_item(preds["raw"], V3), V3)
    print(f"  strip - raw, score: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]; answers that differ: "
          f"{sum(preds['raw'][i['id']] != preds['strip'][i['id']] for i in V3)}")
    for k in sorted({i["kind"] for i in V3}):
        sl = [i for i in V3 if i["kind"] == k]
        s = V.score(preds["raw"], sl)
        print(f"    raw, kind {k:<12} n={len(sl):>3}  near {100 * s['near']:5.1f}  wrong family {100 * s['cross']:4.1f}")
    print("  raw input, not near-correct (truth -> pick):")
    for i in V3:
        x = preds["raw"][i["id"]]
        if not (x in i["accept"] or (i["maj"] and V.FAMILY[x] == V.FAMILY[i["maj"]])):
            print(f"    {i['id']:<10} {i['kind']:<11} {i['maj']} -> {x:<14} {i['text']!r}")
    return preds


def ens_preds(tag):
    """Deployable ens3 predictions of a study (leave one author out, OOF threshold), per gate."""
    os.environ["COOP_TAG"] = tag
    for m in ("coop_v2", "eval_v2"):
        sys.modules.pop(m, None)
    E = importlib.import_module("eval_v2")
    if "base" not in E.R or len(E.R["base"]) != 9:
        return None
    run = E.average(E.load_runs("base"))
    out = {g: E.deploy(run, g)[0] for g in ("top", "family")}
    singles = [E.deploy(r, "top")[0] for r in E.load_runs("base")]
    return out, singles, E.ITEMS


def retrained(ship):
    got = ens_preds("v3")
    if got is None:
        print("\nC. (train_v2.py cv base under COOP_TAG=v3 has not finished)")
        return
    ens, singles, items = got
    v3 = [i for i in items if i["version"] == "v3"]
    old = [i for i in items if i["version"] != "v3"]
    print(f"\nC. RE-TRAINED with the v3 lines and location seeds (leave one author out), {len(items)} lines")
    for g in ("top", "family"):
        show(f"ens3, {g} gate: all lines", ens[g], items)
        show(f"ens3, {g} gate: v3 lines", ens[g], v3)
        show(f"ens3, {g} gate: older lines", ens[g], old)
    for n, p in enumerate(singles):
        show(f"one base model (seed {n}), top: v3", p, v3)
    if ship:
        for g in ("top", "family"):
            d = bootstrap(per_item(ens[g], v3), per_item(ship["raw"], v3), v3)
            print(f"  on v3 lines, re-trained ens3/{g} - shipped (raw input), score: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]")
    prev = ens_preds("v21")
    if prev:
        pens, _, pitems = prev
        ids = {i["id"] for i in pitems}
        sl = [i for i in old if i["id"] in ids]
        for g in ("top", "family"):
            d = bootstrap(per_item(ens[g], sl), per_item(pens[g], sl), sl)
            print(f"  on the {len(sl)} older lines, v3 study - v21 study, ens3/{g}, score: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]")
    print("  re-trained ens3 (family gate), v3 lines not near-correct (truth -> pick):")
    for i in v3:
        x = ens["family"][i["id"]]
        if not (x in i["accept"] or (i["maj"] and V.FAMILY[x] == V.FAMILY[i["maj"]])):
            print(f"    {i['id']:<10} {i['kind']:<11} {i['maj']} -> {x:<14} {i['text']!r}")


def main():
    print(f"v3 lines: {len(V3)}; majority intent on {sum(bool(i['maj']) for i in V3)}, unanimous on "
          f"{sum(i['unanimous'] for i in V3)}; intents {dict(Counter(i['maj'] for i in V3).most_common())}\n")
    m = matcher()
    ship = shipped()
    retrained(ship)
    json.dump({"matcher": m}, io.open(os.path.join(HERE, "results_v3.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
