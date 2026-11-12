"""Checks the place vocabulary v16 (locations_v70.json, make_places_v70.py) with the matcher of today (locations.py), no model.

  1. the grounding of the new words: the primary target of each line of CASES ("drive to the bank" -> bank, "go to the ATM" ->
     atm, ...), and the lines whose record must be v15's byte for byte ("bank left", "take the second left", "store the tools in
     the shed", "go gather some clay at the at the river bank", ...);
  2. a regression pass: every line of the place tests and of the human line sets below is matched with v15 (locations_v68.json)
     and with v16, and the two records compared. A difference on a line with none of v16's new phrases (object words, ignore
     phrases) is a failure; the others are listed by the new phrase they hold.
     Lines: the v67 bot's location_tests.jsonl (made with v15: its stored records must equal v15's of today first), the
     developer's regression lines (locations_dev.json), the seed sets v67 and v70, the owner's lines (owner_lines_v66.json, the
     recogniser's and the decoder's lines of owner_talk_v69_candidates.json, test_v69_owner.json).

    python check_places_v70.py [--out FILE]     # FILE: every difference, one JSON line each
Exit status 1 when a case or the regression pass fails.
"""
import argparse, collections, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import locations as LOC            # noqa: E402
import make_places_v70 as MP       # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
V15 = LOC.load_vocab(os.path.join(HERE, "locations_v68.json"))
V16 = LOC.load_vocab(os.path.join(HERE, "locations_v70.json"))
assert (V15["version"], V16["version"]) == (15, 16), (V15["version"], V16["version"])
SAME = "same"                      # the record of v16 is v15's

# (line, what the primary target of v16 must have, or SAME)
CASES = [
    # the owner's words and the new places
    ("drive to the bank", {"object": "bank"}),
    ("Drive to the bank.", {"object": "bank"}),
    ("drive me to the bank", {"object": "bank"}),
    ("give me a ride to the bank", {"object": "bank"}),
    ("take me to the bank by car", {"object": "bank"}),
    ("drive up to the bank", {"object": "bank"}),
    ("go to the restaurant", {"object": "restaurant"}),
    ("drive to the restaurant", {"object": "restaurant"}),
    ("get in the car and drive to the restaurant", {"object": "car"}),
    ("go to the burger place", {"object": "restaurant"}),
    ("drive to the diner", {"object": "restaurant"}),
    ("drive to the cafe", {"object": "cafe"}),
    ("go to the café", {"object": "cafe"}),
    ("meet me at the coffee shop", {"object": "cafe"}),
    ("drive to the shop", {"object": "shop"}),
    ("drive to the store", {"object": "shop"}),
    ("drive to a store", {"object": "shop"}),
    ("drive to the nearest store", {"object": "shop"}),
    ("go to the supermarket", {"object": "shop"}),
    ("drive us to the hotel", {"object": "hotel"}),
    ("drive to the pharmacy", {"object": "pharmacy"}),
    ("drive to the gas station", {"object": "gas_station"}),
    ("go to the gas pump", {"object": "gas_station"}),
    ("drive to the parking", {"object": "parking"}),
    ("park in the parking lot", {"object": "parking"}),
    ("find a parking spot", {"object": "parking"}),
    ("drive to the junction", {"object": "junction"}),
    ("drive to the crossroads", {"object": "junction"}),
    ("stop at the intersection", {"object": "junction"}),
    ("drive to the traffic light", {"object": "traffic_light"}),
    ("stop at the traffic lights", {"object": "traffic_light"}),
    ("wait at the crosswalk", {"object": "crosswalk"}),
    ("cross at the zebra crossing", {"object": "crosswalk"}),
    ("go to the counter", {"object": "counter"}),
    ("hide behind the counter", {"object": "counter"}),
    ("go to the kitchen counter", {"object": "counter"}),
    ("go to the kiosk", {"object": "kiosk"}),
    ("go to the ordering kiosk", {"object": "kiosk", "flag": None}),
    ("sit on the bench", {"object": "bench"}),
    ("sit on the red bench", {"object": "bench", "qualifier": "red"}),
    ("throw it in the bin", {"object": "bin"}),
    ("throw it in the trash can", {"object": "bin"}),
    ("go to the ATM", {"object": "atm"}),
    ("find a cash machine", {"object": "atm"}),
    ("stand under the parasol", {"object": "parasol"}),
    ("stand under the umbrella", {"object": "parasol"}),
    ("look at the menu", {"object": "menu"}),
    ("go to the menu board", {"object": "menu"}),
    ("go to the kitchen", {"object": "kitchen"}),
    ("go to the drinks machine", {"object": "drinks_machine"}),
    ("get me a soda from the soda fountain", {"object": "drinks_machine"}),
    ("go to the vending machine", {"object": "drinks_machine"}),
    # qualifiers, pointers, directions on the new places
    ("drive to the north bank", {"object": "bank", "qualifier": "north"}),
    ("go to the bank on the east side", {"object": "bank", "qualifier": "east"}),
    ("go to that bank", {"object": "bank", "pointer": "this"}),
    ("drive to the bank right next to the hotel", {"object": "bank"}),
    ("drive to the bank to the left", {"object": "bank", "direction": "left"}),
    ("drive to the bank on the right", {"object": "bank", "direction": "right"}),
    ("go to the big hotel", {"object": "hotel", "flag": "unknown_modifier"}),
    ("drive to the next junction", {"object": "junction", "flag": "unknown_modifier"}),
    ("turn left at the next junction", {"object": "junction", "direction": "left", "flag": "unknown_modifier"}),
    ("turn right at the crossroads", {"object": "junction", "direction": "right"}),
    # v15's readings kept
    ("bank left", SAME), ("bank right", SAME), ("Bank left!", SAME), ("bank hard left", SAME), ("bank hard right", SAME),
    ("bank to the left", SAME), ("bank to the right", SAME), ("bank a left", SAME), ("bank a right", SAME),
    ("bank left and hold the north door", SAME), ("bank right at the stairs", SAME), ("veer left", SAME),
    ("take the second left", SAME), ("take the next right", SAME), ("take the first left", SAME), ("hang a left", SAME),
    ("turn left", SAME), ("go left", SAME), ("drive forward", SAME), ("turn the car around", SAME), ("park here", SAME),
    ("park the car", SAME), ("get in the car", SAME), ("get out of the car", SAME), ("go to the water pump", SAME),
    ("store the tools in the shed", SAME), ("store wheat in the barn", SAME), ("store the crates in the warehouse", SAME),
    ("go gather some clay at the at the river bank", SAME), ("open the main menu", SAME), ("go back to the main menu", SAME),
    ("counter attack now", SAME), ("take it easy on the gas", SAME), ("light em up", SAME), ("this map is trash", SAME),
    ("two hostiles on the stairs", SAME), ("plant coffee in the north field", SAME), ("wait till my mark", SAME),
    ("go to the front door", SAME), ("hold the main door", SAME), ("put the box on the red table", SAME),
    # real lines the first draft of v16 broke (the recogniser's "marker", "bang"; a chain's newline; the bot's own line)
    ("Go to my market,", SAME), ("Stay at my market.", SAME), ("before you go to my market look left then stay low when you get there", SAME),
    ("hop outta the car\npark at the pin", SAME), ("Bank the door with an entry with me", SAME),
    ("You Banks the doorway then entry with me.", SAME), ("open the build menu", SAME),
    ("try again at my bin", SAME), ("Throw a smoke on my bin", SAME), ("Check my bin.", SAME), ("nice shop", SAME),
    ("drive to the bank the one on the left", {"object": "bank"}),
]


def tokens(text, vocab):
    """The words find() reads: the line's tokens without the recogniser's fillers."""
    return [w for w, a, b, br in LOC.tokenize(text) if w not in vocab["w"]["filler"]]


NEW_PHRASES = sorted({tuple(w.split(" ")) for o in MP.NEW_OBJECTS for w in o["words"]} | {tuple(p.split(" ")) for p in MP.NEW_IGNORE},
                     key=lambda p: (-len(p), p))


def new_phrases_in(text):
    ws = tokens(text, V16)
    return sorted({" ".join(p) for p in NEW_PHRASES for i in range(len(ws) - len(p) + 1) if tuple(ws[i:i + len(p)]) == p})


def run_cases():
    fails = 0
    for text, want in CASES:
        r15, r16 = LOC.record(text, V15), LOC.record(text, V16)
        p16 = r16["targets"][r16["primary"]] if r16["primary"] >= 0 else None
        if want == SAME:
            ok = r15 == r16
        else:
            ok = p16 is not None and all(p16.get(k) == v for k, v in want.items())
        fails += not ok
        brief = lambda r: [{k: v for k, v in t.items() if v not in (None, False)} | ({"PRIMARY": True} if i == r["primary"] else {})  # noqa: E731
                           for i, t in enumerate(r["targets"])]
        print(f"  {'ok  ' if ok else 'FAIL'} {text!r}: v16 {brief(r16)}" + ("" if r15 == r16 else f"   (v15 {brief(r15)})")
              + ("" if ok else f"   WANT {want}"))
    return fails


def regression_lines():
    """[(source, text)] in a fixed order, each text once."""
    out, seen = [], set()

    def add(src, t):
        if isinstance(t, str) and t.strip() and t not in seen:
            seen.add(t)
            out.append((src, t))
    stored = {}
    p = os.path.join(ROOT, "models", "coop-deberta-v3-ens3-v67", "cpp", "location_tests.jsonl")
    for line in io.open(p, encoding="utf-8"):
        r = json.loads(line)
        if "places" in r:
            stored[r["text"]] = r["places"]
        add("location_tests_v67", r["text"])
    for c in json.load(io.open(os.path.join(HERE, "locations_dev.json"), encoding="utf-8"))["cases"]:
        add("locations_dev", c["text"])
    for name in ("seed_commands_v67.json", "seed_commands_v70.json"):
        f = os.path.join(HERE, name)
        if os.path.exists(f):
            for k, v in json.load(io.open(f, encoding="utf-8")).items():
                if isinstance(v, list):
                    for t in v:
                        add(name, t)
    for name in ("owner_lines_v66.json", "owner_talk_v69_candidates.json", os.path.join("stt", "chains2", "ml_v69", "test_v69_owner.json")):
        for it in json.load(io.open(os.path.join(HERE, name), encoding="utf-8"))["items"]:
            add(os.path.basename(name), it.get("text"))
            for t in it.get("decoder") or []:
                add(os.path.basename(name) + " (decoder)", t)
    return out, stored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="every difference, one JSON line each")
    a = ap.parse_args()
    print(f"v15 {len(V15['phrases'])} phrases, v16 {len(V16['phrases'])}; {len(NEW_PHRASES)} new phrases")
    print(f"1. the cases ({len(CASES)}):")
    case_fails = run_cases()
    print(f"   {len(CASES) - case_fails}/{len(CASES)} as wanted")

    lines, stored = regression_lines()
    print(f"2. the regression pass: {len(lines)} lines")
    stale = 0
    diffs, by_src, by_phrase, bad = [], collections.Counter(), collections.Counter(), []
    for src, text in lines:
        try:
            r15 = LOC.record(text, V15)
        except Exception as e:             # the place tests hold lines the matcher raises on (python_error): both must raise
            r15 = f"error {type(e).__name__}"
        try:
            r16 = LOC.record(text, V16)
        except Exception as e:
            r16 = f"error {type(e).__name__}"
        if text in stored and stored[text] != r15:
            stale += 1
        if r15 == r16:
            continue
        found = new_phrases_in(text)
        row = {"source": src, "text": text, "new": found, "v15": r15, "v16": r16}
        diffs.append(row)
        by_src[src] += 1
        for f in found or ["(none)"]:
            by_phrase[f] += 1
        if not found:
            bad.append(row)
    print(f"   location_tests_v67 records equal to v15's of today: {len(stored) - stale}/{len(stored)}"
          + ("" if not stale else "  (STALE: the place tests were made with other rules or another vocabulary)"))
    print(f"   lines whose v16 record differs from v15's: {len(diffs)} ({', '.join(f'{k} {v}' for k, v in by_src.most_common())})")
    print(f"   of them with none of v16's new phrases (a failure): {len(bad)}")
    for row in bad:
        print(f"     {row['text']!r}\n       v15 {row['v15']}\n       v16 {row['v16']}")
    print("   the differences by the new phrase the line holds:")
    for f, c in by_phrase.most_common():
        print(f"     {c:6d}  {f}")
    human = [d for d in diffs if d["source"] != "location_tests_v67"]
    print(f"   the differences on the human line sets ({len(human)}):")
    for d in human:
        p15 = d["v15"]["targets"][d["v15"]["primary"]] if isinstance(d["v15"], dict) and d["v15"]["primary"] >= 0 else None
        p16 = d["v16"]["targets"][d["v16"]["primary"]] if isinstance(d["v16"], dict) and d["v16"]["primary"] >= 0 else None
        short = lambda p: None if p is None else {k: v for k, v in p.items() if v not in (None, False)}   # noqa: E731
        print(f"     [{d['source']}] {d['text']!r}: primary {short(p15)} -> {short(p16)}  ({', '.join(d['new'])})")
    if a.out:
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as f:
            for d in diffs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        print(f"   every difference: {a.out}")
    ok = case_fails == 0 and not bad and stale == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
