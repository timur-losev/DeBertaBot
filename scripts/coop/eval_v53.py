"""
v53: the place matcher (rule set v4 with its two logged changes) on the v53 lines (blind/v53: jump orders, the
other angle, cease-fire wording, 3 authors, author + 2 annotators) -- a fourth batch the rules never saw.

The matcher's primary target against the readers' target: the place (object, qualifier, zone -- per field the
value two of three readers give) and the direction (the value two of three give, else none). "exact" = the
place and the direction both equal. Rule set v4 was frozen before any of these lines existed (frozen.txt), so
`--rules` is not needed for the blind number; an archived rule set can still be compared:

    python eval_v53.py                # the current rules
    python eval_v53.py --rules v3     # rule set v3: no directions (what the bot had before)
"""
import importlib.util, io, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["COOP_TAG"] = "v53"
import coop_v2 as V  # noqa: E402

RULES = sys.argv[sys.argv.index("--rules") + 1] if "--rules" in sys.argv else None
if RULES is None:
    import locations as LOC  # noqa: E402
else:
    _s = importlib.util.spec_from_file_location(f"locations_{RULES}", os.path.join(HERE, "rules", RULES, "locations.py"))
    LOC = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(LOC)
ITEMS = [i for i in V.load_items() if i["version"] == "v53"]
ORDER = lambda i: i["maj"] not in (None, "NONE", "WAIT")  # noqa: E731


def pct(a, b):
    return f"{100 * a / max(b, 1):5.1f}% ({a}/{b})"


rows = []
for it in ITEMS:
    r = LOC.find(it["text"])
    t = r["target"]
    place = (t["object"], t["qualifier"], t["zone"]) if t else (None, None, None)
    d = t.get("direction") if t else None
    alld = [x.get("direction") for x in r["targets"] if x.get("direction")]
    rows.append({"it": it, "place": place, "dir": d, "place_ok": place == it["target"], "dir_ok": d == it["direction"],
                 "exact": place == it["target"] and d == it["direction"], "t": t, "targets": r["targets"],
                 "dir_in_list": it["direction"] in alld if it["direction"] else not alld,
                 "usable": place == it["target"] and d == it["direction"] and not (t and (t["role"] or t["flag"] == "unsure"))})


def line(name, rs):
    n = len(rs)
    o = [r for r in rs if ORDER(r["it"])]
    return (f"  {name:<24} exact {pct(sum(r['exact'] for r in rs), n)}   place {pct(sum(r['place_ok'] for r in rs), n)}"
            f"   direction {pct(sum(r['dir_ok'] for r in rs), n)}   usable on orders {pct(sum(r['usable'] for r in o), len(o))}")


name = RULES or f"v{LOC.VOCAB['version']} (current)"
print(f"MATCHER, rule set {name}, on {len(ITEMS)} v53 lines (the readers agree on the place on "
      f"{sum(i['target_agreed'] for i in ITEMS)} and on the direction on {sum(i['direction_agreed'] for i in ITEMS)})")
print(line("all", rows))
for a in V.AUTHORS:
    print(line(f"author {a}", [r for r in rows if r["it"]["author"] == a]))
for k in sorted({r["it"]["kind"] for r in rows}):
    print(line(f"kind {k}", [r for r in rows if r["it"]["kind"] == k]))
has = [r for r in rows if r["it"]["direction"]]
no = [r for r in rows if not r["it"]["direction"]]
print(f"  lines where the readers give a direction: {len(has)}; the matcher's primary has that direction on "
      f"{sum(r['dir_ok'] for r in has)}, another direction on {sum(bool(r['dir']) and not r['dir_ok'] for r in has)}, none on "
      f"{sum(not r['dir'] for r in has)} (the direction is somewhere in its list on {sum(r['dir_in_list'] for r in has)})")
print(f"  lines where the readers give none: {len(no)}; the matcher's primary has a direction on {sum(bool(r['dir']) for r in no)}, "
      f"some target has one on {sum(not r['dir_in_list'] for r in no)}")
print("  readers' direction -> matcher's: " + ", ".join(f"{a}->{b} {n}" for (a, b), n in
                                                        sorted(Counter((r['it']['direction'], r['dir']) for r in rows).items(), key=str)))
um = [r for r in rows if r["it"]["unknown_modifier"]]
print(f"  unknown_modifier flag: raised on {sum(bool(r['t'] and r['t']['flag'] == 'unknown_modifier') for r in rows)} lines, the readers mark {len(um)}; "
      f"both {sum(bool(r['t'] and r['t']['flag'] == 'unknown_modifier') for r in um)}")
print("  mismatches (id kind | text | readers -> matcher):")
show = lambda p, d: "/".join(str(x) for x in p) + f" dir={d}"  # noqa: E731
for r in rows:
    if not r["exact"]:
        it = r["it"]
        print(f"    {it['id']:<10} {it['kind']:<14} {it['text']!r}\n{'':17}{show(it['target'], it['direction'])} -> {show(r['place'], r['dir'])}"
              + ("" if not r["t"] else f"  role={r['t']['role']} flag={r['t']['flag']}")
              + f"   all: {[(x['object'], x['qualifier'], x['zone'], x.get('direction'), x['role']) for x in r['targets']]}")
json.dump({"rules": name, "n": len(rows), "exact": sum(r["exact"] for r in rows) / max(1, len(rows)),
           "place": sum(r["place_ok"] for r in rows) / max(1, len(rows)), "direction": sum(r["dir_ok"] for r in rows) / max(1, len(rows)),
           "direction_lines": len(has), "direction_right": sum(r["dir_ok"] for r in has),
           "false_direction_on_primary": sum(bool(r["dir"]) for r in no)},
          io.open(os.path.join(HERE, f"results_v53_matcher{'_' + RULES if RULES else ''}.json"), "w", encoding="utf-8"), indent=1)
