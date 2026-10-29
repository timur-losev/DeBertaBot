"""The held-out v67 test (chains2/ml_v67/test_v67.json, 240 lines written blind) read by a whole brain as the game reads lines:
coop_cli --serve with the classifier, the chain (router and decoder, the decoder on the CPU) and the planner, one process per
language, the context reset before each item, its lines before said first, its scene (with "failed: ...") in the world.

Each item wants one or more orders in order, each an intent, a target and a means (an object and a qualifier). The brain's
orders are its turns that act, are queued or ask (a question about the target counts as the target when the item names no
qualifier). Scores:
  intent          every wanted order's intent, in order (the brain may not give more orders than wanted)
  + target        ... and its target's object (and qualifier when the item gives one)
  + means         ... and its means' object (rule set v9; a brain without it never has one)
The test's way of writing a few intents differs from the brain's, and is read so: PUSH and ROLL want the thing moved as the means
and where it goes as the target -- the brain's place is the thing moved, so it is compared with the wanted means and the
destination is not checked; DELIVER and DROP carry what the bot holds, so their means is not checked.

    python measure_v67_cli.py v66     the repo's coop_cli with bot v66 and chain v66 (the deployed brain's models)
    python measure_v67_cli.py v67     the repo's coop_cli with models/coop-deberta-v3-ens3-v67/cpp and models/coop-chain-v67/cpp
    python measure_v67_cli.py v67s    the same with the short system turn's chain, models/coop-chain-v67s/cpp
    python measure_v67_cli.py v68s    the same with round v68's chain, models/coop-chain-v68s/cpp (v67s15: v67s on today's bot files)
-> measure_v67_cli_<tag>.log"""
import io, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_v67 as M
from chains9_v65 import scene_parts

REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CLI = os.path.join(REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe")
BRAINS = {t: (os.path.join(REPO, "models", f"coop-deberta-v3-ens3-{t}", "cpp"), os.path.join(REPO, "models", f"coop-chain-{t}", "cpp"))
          for t in ("v66", "v67")}
# v67s: bot v67 with the decoder of the short system turn (chains11_v67.py ... short)
BRAINS["v67s"] = (BRAINS["v67"][0], os.path.join(REPO, "models", "coop-chain-v67s", "cpp"))
# round v68 (2026-10-29): bot v67 as re-exported with place vocabulary v15; v67s15 = v67s again on it (its own log), v68s the new decoder
BRAINS["v67s15"] = BRAINS["v67s"]
BRAINS["v68s"] = (BRAINS["v67"][0], os.path.join(REPO, "models", "coop-chain-v68s", "cpp"))
BRAINS["v68s2"] = (BRAINS["v67"][0], os.path.join(REPO, "models", "coop-chain-v68s2", "cpp"))
# one entity of every object, some with their qualifiers (several tables and crates, as the test range has)
ENTITIES = [("table_w", "table", "white", 0, 6), ("table_r", "table", "red", 30, 9), ("table_b", "table", "blue", -40, 8),
            ("table_y", "table", "yellow", 70, 12), ("crate_1", "crate", None, 10, 3), ("crate_big", "crate", "big", -15, 5),
            ("crate_small", "crate", "small", 25, 4), ("crate_card", "crate", "cardboard", -60, 7), ("spool_1", "spool", None, 50, 5),
            ("door_1", "door", None, 90, 10), ("door_n", "door", "north", -90, 14), ("window_1", "window", None, 120, 9),
            ("car_1", "car", None, 160, 15), ("fence_1", "fence", None, -130, 12), ("stairs_1", "stairs", None, 140, 11),
            ("chair_1", "chair", None, -20, 4), ("sofa_1", "sofa", None, -100, 7), ("tree_1", "tree", None, 179, 20),
            ("ammo_1", "ammo", None, 45, 6), ("weapon_1", "weapon", None, -45, 6), ("health_1", "health", None, 80, 6),
            ("teleport_1", "teleport", None, -170, 25), ("field_1", "field", None, 100, 30), ("bed_1", "bed", None, -110, 18),
            ("greenhouse_1", "greenhouse", None, 130, 35), ("barn_1", "barn", None, -150, 40), ("coop_1", "coop", None, 150, 30),
            ("beehive_1", "beehive", None, -75, 22), ("well_1", "well", None, 60, 24), ("foundation_1", "foundation", None, -30, 16)]
BY_ID = {e[0]: e for e in ENTITIES}


def scene_json(scene):
    parts = scene.split("; ")
    failed = next((p[len("failed: "):] for p in parts if p.startswith("failed: ")), None)
    out = scene_parts("; ".join(p for p in parts if not p.startswith("failed: ")))
    if failed:
        out["failed"] = failed
    return out


def world(t, scene):
    w = {"entities": [{"id": i, "object": o, "qualifier": q, "zone": None, "bearing": float(b), "distance": float(d), "elevation": 0.0,
                       "tags": []} for i, o, q, b, d in ENTITIES],
         "player_gaze": None, "bot": {"stance": "stand", "items": [], "busy": False}, "time": t}
    if scene:
        w["scene"] = scene_json(scene)
    return w


class Brain:
    def __init__(self, tag, lang):
        bot, chain = BRAINS[tag]
        args = [CLI, "--serve", "--model-dir", bot, "--threads", "2", "--no-spin", "--chain", chain, "--decoder-threads", "6", "--decoder-cpu"]
        if lang != "en":
            args += ["--language", lang]
        self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.n = 0
        while self.read().get("event") != "ready":
            pass

    def read(self):
        while True:
            s = self.p.stdout.readline()
            if not s:
                raise SystemExit("the brain ended")
            if s.lstrip().startswith("{"):
                return json.loads(s)

    def ask(self, q):
        self.n += 1
        q["id"] = self.n
        self.p.stdin.write(json.dumps(q, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        while True:
            ev = self.read()
            if ev.get("id") == self.n and ev.get("event") in ("reply", "error", "nothing", "reset"):
                return ev

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)


def orders_of(ev):
    """The brain's orders for one line: [(intent, target object, target qualifier, means object, action, English)]."""
    out = []
    for turn in ev.get("turns") or [ev]:
        action = turn.get("action")
        o = turn.get("order") or {}
        intent = o.get("intent") or turn.get("intent")
        if action not in ("act", "queued", "ask", "resolved", "execute") or not intent:
            continue
        ent = BY_ID.get(o.get("entity") or "")
        obj = ent[1] if ent else o.get("object")
        qual = ent[2] if ent else None
        means = o.get("means_object")
        if action == "ask" and not o:
            # "crate [means]; * table": the question is about the starred place; the means waits in the question (world.py
            # _ask) and goes on the order its answer settles, so it is read from its place here
            places = [p.strip() for p in (turn.get("places") or "").split(";") if p.strip()]
            star = next((p for p in places if p.startswith("*")), None)
            obj = star.lstrip("*").strip().split()[-1] if star else None
            m = next((p for p in places if p.endswith("[means]")), None)
            means = m[:-len("[means]")].strip().split()[-1] if m else None
        out.append((intent, obj, qual, means, action, turn.get("line") or ev.get("english") or ""))
    return out


def matches(want, got):
    """(intent, + target, + means) for one wanted order against one of the brain's."""
    intent, obj, qual, means, action, _ = got
    ok_i = intent == want["intent"]
    t, m = want.get("target"), want.get("means")
    if want["intent"] in ("PUSH", "ROLL"):          # the test's thing moved is the means; the brain's place is that thing
        ok_t = (m is None and t is None) or (m is not None and obj == m["object"]) or (m is None and t is not None and obj == t["object"])
        ok_m = True
    else:
        ok_t = t is None or (obj == t["object"] and (t.get("qualifier") is None or qual == t["qualifier"] or action == "ask"))
        ok_m = want["intent"] in ("DELIVER", "DROP") or m is None or means == m["object"]
    return ok_i, ok_i and ok_t, ok_i and ok_t and ok_m


def main():
    tag = sys.argv[1]
    items = M.sets()["test67"]
    rows = []
    for lang in ("en", "ru", "es"):
        todo = [it for it in items if it["lang"] == lang]
        brain = Brain(tag, lang)
        for k, it in enumerate(todo):
            brain.ask({"cmd": "reset"})
            t = 1000.0 + 100.0 * k
            for b in it["before"]:
                brain.ask({"cmd": "text", "text": b, "world": world(t, None)})
                t += 3
            ev = brain.ask({"cmd": "text", "text": it["text"], "world": world(t, it.get("scene"))})
            got = orders_of(ev)
            want = it["want"]
            per = [matches(w, g) for w, g in zip(want, got)]
            n_ok = len(got) == len(want)
            score = tuple(n_ok and all(p[i] for p in per) for i in range(3))
            rows.append((it, got, score))
        brain.close()
    log = io.StringIO()
    n = len(rows)
    print(f"brain {tag} on test67 ({n} items): " + ", ".join(f"{name} {sum(r[2][i] for r in rows)}/{n} = {100 * sum(r[2][i] for r in rows) / n:.1f}%"
                                                         for i, name in enumerate(("intent", "+ target", "+ means"))), file=log)
    for key, name in ((lambda r: r[0]["lang"], "language"), (lambda r: r[0].get("cat"), "category")):
        by = {}
        for r in rows:
            b = by.setdefault(key(r), [0, 0, 0, 0])
            for i in range(3):
                b[i] += r[2][i]
            b[3] += 1
        print(f"  by {name} (intent / + target / + means): " + ", ".join(f"{k}: {v[0]}/{v[1]}/{v[2]} of {v[3]}" for k, v in sorted(by.items(), key=lambda x: str(x[0]))), file=log)
    for it, got, score in rows:
        if not score[2]:
            w = "; ".join(f"{x['intent']} {(x.get('target') or {}).get('object')}/{(x.get('target') or {}).get('qualifier')} by "
                          f"{(x.get('means') or {}).get('object')}" for x in it["want"])
            g = "; ".join(f"{x[0]} {x[1]}/{x[2]} by {x[3]} ({x[4]})" for x in got) or "nothing"
            print(f"  NO  [{it.get('cat')}] {it['lang']} {it['text'][:50]:50s} -> {g}   want {w}   | {got[0][5][:60] if got else ''}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v67_cli_{tag}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    main()
