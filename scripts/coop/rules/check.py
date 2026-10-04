"""
Tuning material for the place matcher, and one outside check. Nothing here is a blind test of rule
set v3 except the last block, and that one is weak.

  critic_v3/{ordinary,stt,adversarial}.json
      Lines three critic agents wrote against rule set v3 while it was being written (2026-10-04),
      each with the record a teammate would accept: {"text", "accept": [[object, qualifier, zone] or
      null], "role", "flag"}. "ordinary" is everyday orders and callouts (its first 213 lines were
      written before any result was seen: 4 of them failed then, all a missing role on a one-place
      line); "stt" is unpunctuated speech-to-text style, "adversarial" was aimed at each new rule.
      The rules were then changed using these lines, so the counts below are in-sample. The lines
      that still fail are the known limits of rule set v3.
  ../review_v3/fresh_author.json
      80 lines of the Mac review's fresh author (one AI author who is also the only labeller; short,
      seed-like lines). Rule set v3 was written on the work machine without these lines having been
      read there, so for the three rule sets side by side this is an outside check -- not a blind
      set in the project's sense (see review_v3/README.md).

    python rules/check.py            # from scripts/coop
"""
import importlib.util, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.dirname(HERE)
sys.path.insert(0, COOP)


def load(name):
    path = os.path.join(COOP, "locations.py") if name is None else os.path.join(HERE, name, "locations.py")
    spec = importlib.util.spec_from_file_location(f"loc_{name}", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def critic(L):
    for name in ("ordinary", "stt", "adversarial"):
        cases = json.load(io.open(os.path.join(HERE, "critic_v3", f"{name}.json"), encoding="utf-8"))
        place = role = flag = 0
        for c in cases:
            t = L.find(c["text"])["target"]
            got = None if t is None else [t["object"], t["qualifier"], t["zone"]]
            ok = got in [a if a is None else list(a) for a in c["accept"]]
            place += not ok
            role += ok and "role" in c and (t["role"] if t else None) != c["role"]
            flag += ok and "flag" in c and (t["flag"] if t else None) != c["flag"]
        print(f"  {name:<12} {len(cases):>3} lines: wrong primary place on {place}, right place but wrong role on {role}, "
              f"wrong flag on {flag}")


def fresh(rules):
    lines = json.load(io.open(os.path.join(COOP, "review_v3", "fresh_author.json"), encoding="utf-8"))["lines"]
    for name, L in rules:
        exact = usable = orders = named = named_ok = 0
        for x in lines:
            want = tuple((x.get("target") or {}).get(k) for k in ("object", "qualifier", "zone"))
            t = L.find(x["text"])["target"]
            got = (t["object"], t["qualifier"], t["zone"]) if t else (None, None, None)
            e = got == want
            exact += e
            if want != (None, None, None):
                named += 1
                named_ok += e
            if x["intent"] not in ("NONE", "WAIT"):
                orders += 1
                usable += e and not (t and (t["role"] or t["flag"] == "unsure"))
        print(f"  rule set {name:<3} exact {exact}/{len(lines)}; on lines that name a place {named_ok}/{named}; "
              f"usable on orders {usable}/{orders}")


def main():
    cur = load(None)
    print(f"critics' lines, rule set v{cur.VOCAB['version']} (in-sample: the rules were changed with these lines)")
    critic(cur)
    print("the Mac review's fresh author, 80 lines (an outside check, one author-labeller)")
    fresh([("v1", load("v1")), ("v2", load("v2")), (f"v{cur.VOCAB['version']}", cur)])


if __name__ == "__main__":
    main()
