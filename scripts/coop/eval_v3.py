"""
v3: orders that name a place on the map (blind/v3, 3 authors x 50 lines, author + 2 annotators).

A. The matcher: its primary target against the readers' target -- per field the value two of three
   readers give. "exact" = object, qualifier and zone all equal. "usable" (order lines only: intent
   not NONE / WAIT) = exact, and the primary carries no role and no "unsure" flag, i.e. the planner
   gets a destination it may act on. Also whether the readers' target is anywhere in the matcher's
   list (extraction right, choice of primary wrong) and how the "unknown_modifier" flag does.
   Only rule set v1 was frozen before these lines existed: `--rules v1` is the blind number. Rule
   sets v2 and v3 were written after reading them; their blind number is eval_v3b.py.
B. The classifier shipped before v3 (never saw a v3 line): intent on the v3 lines, reading the raw
   line or the line with attached qualifiers stripped (v3_shipped.py), at its gate and threshold.
C. Re-training with the v3 lines and the location seeds (train_v2.py cv under the tag: leave one
   author out, out-of-fold threshold per fold), three base seeds averaged; against B on the v3
   lines, per author too, and against the earlier studies on the old lines.

    COOP_TAG=v3 python eval_v3.py            # the v3 study as it was run
    COOP_TAG=v31 python eval_v3.py           # seed set v31, r6 re-read by an independent annotator
    python eval_v3.py --rules v1             # section A with an archived rule set (rules/v1, rules/v2)
"""
import importlib, importlib.util, io, json, os, random, statistics, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TAG = os.environ.get("COOP_TAG") if os.environ.get("COOP_TAG") in ("v3", "v31") else "v3"
os.environ["COOP_TAG"] = TAG
import coop_v2 as V  # noqa: E402

RULES = sys.argv[sys.argv.index("--rules") + 1] if "--rules" in sys.argv else None


def load_rules(name):
    """locations.py of an archived rule set (rules/<name>/), or the current one."""
    if name is None:
        import locations
        return locations
    spec = importlib.util.spec_from_file_location(f"locations_{name}", os.path.join(HERE, "rules", name, "locations.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


LOC = load_rules(RULES)
ITEMS = V.load_items()
V3 = [i for i in ITEMS if i["version"] == "v3"]
ORDER = lambda i: i["maj"] not in (None, "NONE", "WAIT")  # noqa: E731


def pct(a, b):
    return f"{100 * a / max(b, 1):5.1f}% ({a}/{b})"


def match_rows(items, loc):
    rows = []
    for it in items:
        r = loc.find(it["text"])
        t = r["target"]
        got = (t["object"], t["qualifier"], t["zone"]) if t else (None, None, None)
        allt = [(x["object"], x["qualifier"], x["zone"]) for x in r["targets"]]
        exact = got == it["target"]
        rows.append({"it": it, "got": got, "exact": exact, "in_list": it["target"] in allt or
                     it["target"] == (None, None, None) and not allt,
                     "flag": bool(t and t["flag"] == "unknown_modifier"), "t": t, "targets": r["targets"],
                     "role": bool(t and t["role"]), "unsure": bool(t and t["flag"] == "unsure"),
                     "usable": exact and not (t and (t["role"] or t["flag"] == "unsure")),
                     "fields": [got[k] == it["target"][k] for k in range(3)]})
    return rows


def matcher_table(rows, authors, mismatches=True):
    def line(name, rs):
        n = len(rs)
        o = [r for r in rs if ORDER(r["it"])]
        return (f"  {name:<22} exact {pct(sum(r['exact'] for r in rs), n)}   usable on orders {pct(sum(r['usable'] for r in o), len(o))}"
                f"   object {pct(sum(r['fields'][0] for r in rs), n)}   qualifier {pct(sum(r['fields'][1] for r in rs), n)}"
                f"   zone {pct(sum(r['fields'][2] for r in rs), n)}   truth in list {pct(sum(r['in_list'] for r in rs), n)}")

    print(line("all", rows))
    for a in authors:
        print(line(f"author {a}", [r for r in rows if r["it"]["author"] == a]))
    for k in sorted({r["it"]["kind"] for r in rows}):
        print(line(f"kind {k}", [r for r in rows if r["it"]["kind"] == k]))
    print(line("readers agreed", [r for r in rows if r["it"]["target_agreed"]]))
    o = [r for r in rows if ORDER(r["it"])]
    print(f"  order lines: {len(o)}; exact {sum(r['exact'] for r in o)}; of the exact ones the primary carries a role on "
          f"{sum(r['exact'] and r['role'] for r in o)} and 'unsure' on {sum(r['exact'] and r['unsure'] and not r['role'] for r in o)}")
    um = [r for r in rows if r["it"]["unknown_modifier"]]
    print(f"  unknown_modifier flag: raised on {sum(r['flag'] for r in rows)} lines, the readers mark {len(um)}; "
          f"both {sum(r['flag'] for r in um)}; raised where the readers do not mark it {sum(r['flag'] and not r['it']['unknown_modifier'] for r in rows)}")
    print(f"  'unsure' flags: on {sum(any(x['flag'] == 'unsure' for x in r['targets']) for r in rows)} lines")
    if mismatches:
        print("  mismatches (author kind | text | readers -> matcher):")
        for r in rows:
            if not r["exact"]:
                it = r["it"]
                print(f"    {it['id']:<10} {it['kind']:<11} {it['text']!r}\n{'':17}{it['target']} -> {r['got']}"
                      f"{'' if not r['t'] else '  role=' + str(r['t']['role']) + ' flag=' + str(r['t']['flag'])}"
                      f"{'  [truth is in the list]' if r['in_list'] else ''}")
        print("  exact, but not usable (order lines whose primary has a role or 'unsure'):")
        for r in o:
            if r["exact"] and not r["usable"]:
                print(f"    {r['it']['id']:<10} role={r['t']['role']} flag={r['t']['flag']}  {r['it']['text']!r}")


def summary(rows, authors):
    o = [r for r in rows if ORDER(r["it"])]
    return {"n": len(rows), "exact": sum(r["exact"] for r in rows) / max(1, len(rows)),
            "orders": len(o), "usable_on_orders": sum(r["usable"] for r in o) / max(1, len(o)),
            "per_author": {a: sum(r["exact"] for r in rows if r["it"]["author"] == a) /
                           max(1, sum(r["it"]["author"] == a for r in rows)) for a in authors},
            "in_list": sum(r["in_list"] for r in rows) / max(1, len(rows))}


def matcher():
    name = RULES or f"v{LOC.VOCAB['version']} (current)"
    print(f"A. MATCHER, rule set {name}, on {len(V3)} v3 lines (readers agree on the whole target on "
          f"{sum(i['target_agreed'] for i in V3)}, unanimously on {sum(i['target_unanimous'] for i in V3)})")
    if RULES != "v1":
        print("  NOT a blind number: this rule set was written after these lines had been read (blind: --rules v1, and eval_v3b.py)")
    rows = match_rows(V3, LOC)
    matcher_table(rows, V.AUTHORS)
    old = [i for i in ITEMS if i["version"] != "v3"]
    found = [LOC.find(i["text"]) for i in old]
    print(f"  on the {len(old)} older lines the matcher finds a target in {sum(f['target'] is not None for f in found)}; "
          f"unknown_modifier on {sum(any(t['flag'] == 'unknown_modifier' for t in f['targets']) for f in found)}, "
          f"a role on the primary of {sum(bool(f['target'] and f['target']['role']) for f in found)}, "
          f"'unsure' on {sum(any(t['flag'] == 'unsure' for t in f['targets']) for f in found)}")
    return summary(rows, V.AUTHORS)


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
    print("  (score = near - 2 x wrong family)")
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
    try:
        E = importlib.import_module("eval_v2")
        if "base" not in E.R or len(E.R["base"]) != 9:
            return None
        run = E.average(E.load_runs("base"))
        out = {g: E.deploy(run, g)[0] for g in ("top", "family")}
        singles = [E.deploy(r, "top")[0] for r in E.load_runs("base")]
        return out, singles, E.ITEMS
    finally:
        os.environ["COOP_TAG"] = TAG


def retrained(ship):
    got = ens_preds(TAG)
    if got is None:
        print(f"\nC. (train_v2.py cv base under COOP_TAG={TAG} has not finished: no results_{TAG}_probs*.json with 9 runs)")
        return
    ens, singles, items = got
    v3 = [i for i in items if i["version"] == "v3"]
    old = [i for i in items if i["version"] != "v3"]
    print(f"\nC. RE-TRAINED under {TAG} with the v3 lines and location seeds (leave one author out), {len(items)} lines")
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
            for a in V.AUTHORS:      # the lines are not exchangeable across authors: show where the gain is
                sl = [i for i in v3 if i["author"] == a]
                d = bootstrap(per_item(ens[g], sl), per_item(ship["raw"], sl), sl)
                s0, s1 = V.score(ship["raw"], sl), V.score(ens[g], sl)
                print(f"      author {a:<3} n={len(sl)}: near {100 * s0['near']:.0f} -> {100 * s1['near']:.0f}, wrong family "
                      f"{100 * s0['cross']:.0f} -> {100 * s1['cross']:.0f}, score {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]")
    for other in [t for t in ("v21", "v3") if t != TAG]:
        prev = ens_preds(other)
        if prev:
            pens, _, pitems = prev
            ids = {i["id"] for i in pitems}
            for name, sl in (("older lines", [i for i in old if i["id"] in ids]), ("v3 lines", [i for i in v3 if i["id"] in ids])):
                if sl:
                    for g in ("top", "family"):
                        d = bootstrap(per_item(ens[g], sl), per_item(pens[g], sl), sl)
                        print(f"  on the {len(sl)} {name}, {TAG} study - {other} study, ens3/{g}, score: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]")
    print("  re-trained ens3 (family gate), v3 lines not near-correct (truth -> pick):")
    for i in v3:
        x = ens["family"][i["id"]]
        if not (x in i["accept"] or (i["maj"] and V.FAMILY[x] == V.FAMILY[i["maj"]])):
            print(f"    {i['id']:<10} {i['kind']:<11} {i['maj']} -> {x:<14} {i['text']!r}")


def main():
    print(f"study {TAG}; v3 lines: {len(V3)}; majority intent on {sum(bool(i['maj']) for i in V3)}, unanimous on "
          f"{sum(i['unanimous'] for i in V3)}; intents {dict(Counter(i['maj'] for i in V3).most_common())}\n")
    m = matcher()
    if RULES:
        return
    ship = shipped()
    retrained(ship)
    json.dump({"matcher": m}, io.open(os.path.join(HERE, f"results_{TAG}_matcher.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
