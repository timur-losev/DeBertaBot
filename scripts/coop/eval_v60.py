"""
The v60 test lines (blind/v60, three AI authors x 60, two AI annotators each): how the three readings agree, and what
the item rules (items.py) and the place matcher (locations.py with locations_v60.json) give against the majority. No
model: the intent the rules are given is the lines' majority intent (the classifier's own number comes from the
v60 training, build_v60.py).

  item     the majority item of three readings (2 of 3 the same, lowercase, articles dropped), null included; a line
           with no majority item is not counted
  place    the majority (object, qualifier, zone) of three readings (coop_v2._target_truth); "matcher" is the primary
           target of locations.find, "with item" the same after the planner's rule for BUILD, COLLECT and DELIVER: a
           place that is the item itself is not where the order goes ("carry the crate to the barn" = barn)

    python eval_v60.py [--lines]
"""
import glob, io, json, os, sys
from collections import Counter

os.environ["COOP_TAG"] = "v60"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_v2 as V  # noqa: E402
import items as I  # noqa: E402
import locations as LOC  # noqa: E402

ARTICLES = {"the", "a", "an", "some"}


def norm_item(x):
    if not x:
        return None
    w = [t for t, *_ in LOC.tokenize(x) if t not in ARTICLES]
    return " ".join(w) or None


def load():
    out = []
    for key in V.AUTHORS:
        auth = json.load(io.open(os.path.join(HERE, "blind", "v60", f"author_{key}.json"), encoding="utf-8"))
        anns = [json.load(io.open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(HERE, "annot", "v60", f"author_{key}_ann*.json")))]
        assert len(anns) == 2, (key, len(anns))
        for a in auth:
            raw = [a] + [an[a["id"]] for an in anns]
            reads = [V._read(r) for r in raw]
            it = V._item(a, key, reads, "v60")
            iv = Counter(norm_item(r.get("item")) for r in raw).most_common(1)[0]
            it["item"], it["item_agreed"] = (iv[0] if iv[1] >= 2 else None), iv[1] >= 2
            it["item_unanimous"] = iv[1] == 3
            it["items"] = [norm_item(r.get("item")) for r in raw]
            out.append(it)
    return out


def place_of(text, intent, item_res):
    r = LOC.find(text)
    ts = r["targets"]
    if r["primary"] < 0:
        return (None, None, None), (None, None, None)
    p = ts[r["primary"]]
    plain = (p["object"], p["qualifier"], p["zone"])
    if intent in I.ITEMS["keeps_object"] and item_res["item"]:
        last = tuple(item_res["item"].split(" "))
        obj = None
        for n in range(len(last), 0, -1):
            q = LOC.VOCAB["phrases"].get(last[len(last) - n:])
            if q is not None and q[0] == "object":
                obj = q[1]
                break
        if obj is not None and p["object"] == obj:
            rest = [t for t in ts if t is not p and t["role"] not in ("mine", "them", "not", "from")]
            p2 = rest[0] if rest else None
            return plain, ((p2["object"], p2["qualifier"], p2["zone"]) if p2 else (None, None, None))
    return plain, plain


def main():
    lines = load()
    n = len(lines)
    maj = sum(1 for x in lines if x["maj"])
    una = sum(1 for x in lines if x["unanimous"])
    print(f"v60 lines: {n}; intent majority {maj}, unanimous {una}")
    print("  intents (majority):", dict(Counter(x["maj"] for x in lines).most_common()))
    print(f"  item: majority {sum(x['item_agreed'] for x in lines)}, unanimous {sum(x['item_unanimous'] for x in lines)}")
    print(f"  place: majority {sum(x['target_agreed'] for x in lines)}, unanimous {sum(x['target_unanimous'] for x in lines)}")
    ok_i = tot_i = ok_p = ok_p2 = tot_p = 0
    miss_i, miss_p = [], []
    for x in lines:
        intent = x["maj"]
        if not intent:
            continue
        r = I.find(x["text"], intent)
        if x["item_agreed"]:
            tot_i += 1
            if r["item"] == x["item"]:
                ok_i += 1
            else:
                miss_i.append((x["id"], intent, x["text"], r["item"], x["items"]))
        if x["target_agreed"]:
            tot_p += 1
            plain, withitem = place_of(x["text"], intent, r)
            truth = tuple(x["target"])
            ok_p += plain == truth
            ok_p2 += withitem == truth
            if withitem != truth:
                miss_p.append((x["id"], intent, x["text"], withitem, truth))
    print(f"items.py {I.RULESET}: {ok_i}/{tot_i} lines with a majority item")
    print(f"places: matcher {ok_p}/{tot_p}, with the item rule {ok_p2}/{tot_p}")
    if "--lines" in sys.argv:
        print("\nitem misses (id, intent, line, rules, three readings):")
        for m in miss_i:
            print("  ", m)
        print("\nplace misses (id, intent, line, rules, truth):")
        for m in miss_p:
            print("  ", m)
        print("\nno intent majority / not unanimous:")
        for x in lines:
            if not x["unanimous"]:
                print("  ", x["id"], x["text"], [r["intent"] for r in x["reads"]], sorted(x["accept"]))


if __name__ == "__main__":
    main()
