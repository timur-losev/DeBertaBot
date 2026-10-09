"""The lines of the three critics of rule set v4 (directions) against a rule set: tuning material, never a test.

  critic_a.json   569 lines that DO give a direction (missed and mis-attached directions)
  critic_b.json   460 lines where a direction word is NOT a direction, or stands next to a place
  critic_c.txt    the code reviewer's probe lines (no expectations; printed with --show)
Each JSON row has the critic's "expect" for the primary target (null: no target) and what the FIRST DRAFT of the
rules gave ("got_ok"); critic A's rows also list other records the critic accepts ("also_accepted"); critic B's accepted alternatives are not in its file (with them 67 of its lines differ, not 87). The rules were then
changed with these lines, so the counts below say how much of the critique was taken, not how good the rules are.

    python rules/critic_v4/check.py            # the current rules
    python rules/critic_v4/check.py --rules v4 # an archived rule set
"""
import importlib.util, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, "..", ".."))
RULES = sys.argv[sys.argv.index("--rules") + 1] if "--rules" in sys.argv else None
path = os.path.join(COOP, "rules", RULES, "locations.py") if RULES else os.path.join(COOP, "locations.py")
spec = importlib.util.spec_from_file_location("loc_checked", path)
LOC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LOC)
K = ("object", "qualifier", "zone", "direction")


def same(exp, t):
    if exp is None:
        return t is None
    if isinstance(exp, list):                      # critic A's rows: [object, qualifier, zone, direction, role]
        exp = dict(zip(K + ("role",), exp))
    return t is not None and all(exp.get(k) == t.get(k) for k in K)


for name in ("critic_a.json", "critic_b.json"):
    rows = json.load(io.open(os.path.join(HERE, name), encoding="utf-8"))
    wrong = before = 0
    for r in rows:
        t = LOC.find(r["text"])["target"]
        ok = same(r["expect"], t) or any(same(a, t) for a in r.get("also_accepted") or [])
        wrong += not ok
        before += not r["got_ok"]
    print(f"{name}: {len(rows)} lines; the primary's place and direction differ from the critic's on {wrong} "
          f"(first draft of the rules: {before} by the critic's own count, which also looks at the role)")
if "--show" in sys.argv:
    for line in io.open(os.path.join(HERE, "critic_c.txt"), encoding="utf-8").read().splitlines():
        if line.strip():
            r = LOC.record(line)
            print(repr(line), "->", r["primary"], [tuple(t[k] for k in K + ("role", "flag")) for t in r["targets"]])
