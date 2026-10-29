"""The held-out v66 test (chains2/ml_v66/test_v66.json, written blind) read by a whole brain as the game reads lines: coop_cli
--serve with the classifier, the chain (router and decoder) and the planner, one process per language, the context reset before
each item, the item's lines before said first, its scene in the world. A line is right when the order's intent is the label's,
and right in place when the label names none, or the order's place is it: the entity of that object (the planner's memory of the
line before counts: "it", "that"), or the zone.

    python measure_v66_cli.py v65     the deployed brain (LyraStarterGame58/Binaries/CoopBrainV6)
    python measure_v66_cli.py v66     the repo's coop_cli with models/coop-deberta-v3-ens3-v66/cpp and models/coop-chain-v66/cpp
-> measure_v66_cli_<tag>.log"""
import io, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_v66 as M
from chains9_v65 import scene_parts

REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
GAME = "J:/UE4/Projects/LyraStarterGame58/Binaries/CoopBrainV6"
BRAINS = {"v65": (f"{GAME}/coop_cli.exe", f"{GAME}/bot", f"{GAME}/chain"),
          "v66": (os.path.join(REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe"),
                  os.path.join(REPO, "models", "coop-deberta-v3-ens3-v66", "cpp"), os.path.join(REPO, "models", "coop-chain-v66", "cpp"))}
ENTITIES = [("window_1", "window", None, 0, 4, -1.0), ("door_1", "door", None, 60, 8, 0.0), ("table_1", "table", "white", -30, 6, 0.0),
            ("crate_1", "crate", None, 10, 3, 0.0)]
OBJECT_OF = {e[0]: e[1] for e in ENTITIES}


def world(t, scene):
    w = {"entities": [{"id": i, "object": o, "qualifier": q, "zone": None, "bearing": b, "distance": d, "elevation": e, "tags": []}
                      for i, o, q, b, d, e in ENTITIES],
         "player_gaze": None, "bot": {"stance": "stand", "items": [], "busy": False}, "time": t}
    if scene:
        w["scene"] = scene_parts(scene)
    return w


class Brain:
    def __init__(self, tag, lang):
        exe, bot, chain = BRAINS[tag]
        args = [exe, "--serve", "--model-dir", bot, "--threads", "2", "--no-spin", "--chain", chain, "--decoder-threads", "6"]
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


def read_line(brain, it, t0):
    brain.ask({"cmd": "reset"})
    t = t0
    for b in it["before"]:
        brain.ask({"cmd": "text", "text": b, "world": world(t, None)})
        t += 3
    ev = brain.ask({"cmd": "text", "text": it["text"], "world": world(t, it.get("scene"))})
    turns = ev.get("turns") or [ev]
    first = turns[0]
    order = first.get("order") or {}
    intent = first.get("intent") or (order.get("intent"))
    if order.get("intent"):
        intent = order["intent"]
    return intent, order, first.get("line") or ev.get("english") or "", first.get("action")


def main():
    tag = sys.argv[1]
    items = M.sets()["test66"]
    rows = []
    for lang in ("en", "ru", "es"):
        todo = [it for it in items if it["lang"] == lang]
        brain = Brain(tag, lang)
        for k, it in enumerate(todo):
            intent, order, line, action = read_line(brain, it, 1000.0 + 100.0 * k)
            want = it.get("place")
            placed = not want or intent in M.NO_PLACE or order.get("zone") == want or order.get("object") == want or \
                OBJECT_OF.get(order.get("entity") or "") == want
            rows.append((it, intent, intent == it["label"], intent == it["label"] and placed, line, action, order))
        brain.close()
    log = io.StringIO()
    n = len(rows)
    right = sum(r[2] for r in rows)
    placed = sum(r[3] for r in rows)
    print(f"brain {tag} on test66 ({n} items; left out as the owner's own trained lines: {M.sets.left_out}): intent {right}/{n} = "
          f"{100 * right / n:.1f}%, intent and place {placed}/{n} = {100 * placed / n:.1f}%", file=log)
    for key, name in ((lambda r: r[0]["lang"], "language"), (lambda r: r[0]["rule"], "rule")):
        by = {}
        for r in rows:
            b = by.setdefault(key(r), [0, 0])
            b[0] += r[3]
            b[1] += 1
        print(f"  by {name}: " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in sorted(by.items())), file=log)
    for it, intent, ok, okp, line, action, order in rows:
        if not okp:
            why = f"read {intent} ({action})" if not ok else f"place {order.get('entity') or order.get('zone')}"
            print(f"  NO  [{it['rule']}] {it['lang']} {it['text'][:44]:44s} -> {line[:46]:46s} {why}; want {it['label']} {it.get('place') or ''}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v66_cli_{tag}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    main()
