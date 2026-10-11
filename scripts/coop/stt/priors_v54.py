"""What the world priors (scripts/coop/world.py PRIORS) do to the classifier's picks, simulated: for every held-out line
of the teacher ensemble's out-of-fold run a world state is drawn that is consistent with the line's truth (a player who
says "revive me" is down; a bot told to go prone is not prone already; an answer comes when the bot asked; a window
order has a window in sight), and otherwise random. The priors are applied to the out-of-fold probabilities and the
picks compared, before and after, under the bot's own gate and threshold (fitted without priors, as the bot ships).
Also the hostile case: a world drawn with NO regard to the truth, to see what the priors cost when the game's state
is wrong or stale.

    python priors_v54.py [--scale X]     # --scale: every multiplier replaced by X (how strong the priors should be)
"""
import io, json, os, random, sys
os.environ["COOP_TAG"] = "v54"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import coop_v2 as V
import world as W

items = {i["id"]: i for i in V.load_items() if i["maj"]}
spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731
runs = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2)
        if os.path.exists(os.path.join(HERE, f"kd54_teacher_s{s}.json"))]
probs = {}
for r in runs:
    for f in r.values():
        for k, v in f["test"].items():
            probs.setdefault(k, []).append(v)
n_seeds = max(len(v) for v in probs.values())
probs = {k: [sum(x[j] for x in v) / len(v) for j in range(len(V.INTENTS))] for k, v in probs.items() if len(v) == n_seeds}


def by(c):
    return {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == c and spoken(items[k.split("|", 1)[1]])}


best = None
for gate in ("top", "family"):
    for t in range(0, 100, 2):
        near = cross = 0
        for c in ("clean", "kokoro", "kokorox", "vctkA"):
            p = by(c)
            s = V.score(V.picks(p, gate, t / 100), [items[k] for k in p])
            near += s["near_count"]; cross += s["cross_count"]
        v = near - 2 * cross
        if best is None or v > best[0] or (v == best[0] and gate == "top"):
            best = (v, gate, t / 100)
_, gate, thr = best
PRIORS = W.PRIORS
if "--scale" in sys.argv:
    x = float(sys.argv[sys.argv.index("--scale") + 1])
    PRIORS = {k: [(c, x) for c, _ in v] for k, v in W.PRIORS.items()}
    print(f"every multiplier set to {x}")
print(f"teacher ensemble out-of-fold ({n_seeds} seeds): gate {gate}, threshold {thr:.2f}")

STANCE_OF = {"CROUCH": "crouch", "PRONE": "prone", "STAND_UP": "stand"}


def world_for(truth, rng, consistent):
    w = W.empty_world()
    objs = ["door", "window", "stairs", "table"]
    n = rng.choice([0, 1, 2, 3, 4])
    kinds = rng.sample(objs, min(n, len(objs)))
    if consistent and truth == "VAULT_WINDOW" and "window" not in kinds:
        kinds.append("window")
    if consistent and truth == "OPEN" and "door" not in kinds:
        kinds.append("door")
    for i, o in enumerate(kinds):
        w["entities"].append({"id": f"{o}_{i}", "object": o, "qualifier": None, "zone": None, "bearing": 0.0, "distance": 5.0, "elevation": 0.0,
                              "tags": ["bomb"] if (consistent and truth == "DEFUSE" and i == 0) or (rng.random() < 0.3) else []})
    w["bot"]["stance"] = rng.choice(W.STANCES)
    if consistent and truth in STANCE_OF and w["bot"]["stance"] == STANCE_OF[truth]:
        w["bot"]["stance"] = rng.choice([s for s in W.STANCES if s != STANCE_OF[truth]])
    w["bot"]["items"] = ["bomb"] if (consistent and truth == "PLANT") or rng.random() < 0.5 else []
    w["player"]["downed"] = True if (consistent and truth == "REVIVE_ME") else rng.random() < 0.1
    memory = {"question": {"kind": "which"} if (consistent and truth in ("YES", "NO", "MAYBE", "DONT_KNOW")) or rng.random() < 0.15 else None}
    return w, memory


for cond, label in (("typed", "typed"), ("vctkB", "VCTK pool B, unseen speakers"), ("clean", "Windows voices")):
    p = by(cond)
    rows = [items[k] for k in p]
    base = V.score(V.picks(p, gate, thr), rows)
    print(f"\n{label}: {len(p)} lines")
    print(f"  {'':34s} {'near':>6s} {'wrong fam':>10s} {'acts on non-order':>18s} {'criterion':>10s} {'changed picks':>14s}")
    print(f"  {'no priors (the bot today)':34s} {100 * base['near']:6.1f} {100 * base['cross']:9.1f}% {100 * base['fired_on_nonorder']:17.1f}% {100 * (base['near'] - 2 * base['cross']):10.1f}")
    for consistent, name in ((True, "priors, world consistent with truth"), (False, "priors, world drawn blind")):
        rng = random.Random(7)
        adj = {}
        for k, row in p.items():
            w, mem = world_for(items[k]["maj"], rng, consistent)
            adj[k] = W.apply_priors(row, V.INTENTS, w, mem, PRIORS)[0]
        pk0, pk1 = V.picks(p, gate, thr), V.picks(adj, gate, thr)
        s = V.score(pk1, rows)
        changed = sum(pk0[k] != pk1[k] for k in p)
        print(f"  {name:34s} {100 * s['near']:6.1f} {100 * s['cross']:9.1f}% {100 * s['fired_on_nonorder']:17.1f}% {100 * (s['near'] - 2 * s['cross']):10.1f} {changed:14d}")
        if consistent:
            won = [k for k in p if pk1[k] in items[k]["accept"] and pk0[k] not in items[k]["accept"]]
            lost = [k for k in p if pk0[k] in items[k]["accept"] and pk1[k] not in items[k]["accept"]]
            print(f"    won {len(won)}, lost {len(lost)}" + (": " + "; ".join(f"{items[k]['text'][:40]!r} {pk0[k]}->{pk1[k]} (truth {items[k]['maj']})" for k in lost[:4]) if lost else ""))
