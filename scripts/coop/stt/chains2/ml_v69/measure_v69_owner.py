"""Round v69's owner test (test_v69_owner.json) read by a whole brain as the game reads lines: the repo's coop_cli --serve with bot v67
(place vocabulary v15), a chain (router and decoder, the decoder on the CPU) and the planner, one process per language, the context
reset before each item, its lines before said first (with their crosshair), on the test range's things.

An item passes when the brain's orders (its turns that act, are queued, ask or settle) begin with the wanted ones in order: each
intent, and when given the place's object, qualifier, zone or the close flag. A remark passes when no turn gives an order (an
answer, small talk, praise, "say again" are all no order). Two scores: "at once", the reply's turns alone (the first numbers of
2026-11-04), and "with held", each line the chain held (after an "on my go" order or a question) then read by a brain without the
chain, as the game reads a held line later (measure_v68_time.py's way).

    python measure_v69_owner.py TAG     TAG: v68s2 (models/coop-chain-v68s2/cpp), v69, v69s2 (models/coop-chain-<TAG>/cpp) -> measure_v69_owner_<TAG>.log
"""
import io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
CLI = os.path.join(REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe")
BOT = os.path.join(REPO, "models", "coop-deberta-v3-ens3-v67", "cpp")
NO_ORDER = {"SMALL_TALK", "PRAISE", "NONE", "YES", "NO", "MAYBE", "DONT_KNOW", None}


def E(id, obj, qual=None, b=0.0, d=5.0, el=0.0, tags=None):
    return {"id": id, "object": obj, "qualifier": qual, "zone": None, "bearing": b, "distance": d, "elevation": el, "tags": tags or []}


WORLD = [E("yellow_bed_2", "bed", "yellow", -20, 6), E("white_table_3", "table", "white", 160, 8), E("red_chair_1", "chair", "red", 120, 5),
         E("blue_table_4", "table", "blue", 140, 6), E("rock_10", "rock", None, 40, 7), E("blue_stairs_5", "stairs", "blue", 70, 9),
         E("sofa_6", "sofa", None, -70, 7), E("main_door_7", "door", "main", 10, 12, tags=["inside"]), E("north_door_8", "door", "north", -40, 14),
         E("crate_9", "crate", None, -60, 3)]
BY_ID = {e["id"]: e for e in WORLD}


class Brain:
    def __init__(self, chain, lang):
        args = [CLI, "--serve", "--no-stt", "--model-dir", BOT, "--threads", "2", "--no-spin"]
        if chain:
            args += ["--chain", chain, "--decoder-cpu", "--decoder-threads", "6"]
        if lang != "en":
            args += ["--language", lang]
        self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", bufsize=1)
        self.n = 0
        self.wait(lambda j: j.get("event") in ("ready", "error"))

    def wait(self, done):
        for line in self.p.stdout:
            if line.startswith("{"):
                j = json.loads(line)
                if done(j):
                    return j
        raise RuntimeError("coop_cli ended")

    def ask(self, q):
        self.n += 1
        q = dict(q, id=self.n)
        self.p.stdin.write(json.dumps(q, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        return self.wait(lambda j: j.get("id") == self.n)

    def close(self):
        self.p.stdin.write('{"cmd":"quit"}\n')
        self.p.stdin.flush()
        self.p.wait(timeout=30)


def world(t, gaze):
    return {"entities": WORLD, "player_gaze": gaze, "player": {"downed": False}, "bot": {"stance": "stand", "items": [], "busy": False},
            "time": t, "map": "/Game/Maps/L_OVTestRange"}


def orders(ev):
    out = []
    for turn in ev.get("turns") or [ev]:
        if turn.get("action") not in ("act", "queued", "ask", "resolved", "wait"):
            continue
        o = turn.get("order") or {}
        intent = o.get("intent") or turn.get("intent")
        out.append((turn, intent, o))
    return out


def fits(want, got):
    turn, intent, o = got
    if intent != want["intent"]:
        return False
    ent = BY_ID.get(o.get("entity") or turn.get("pending_entity") or "")      # a queued order keeps its place as pending_entity
    cands = [BY_ID[c] for c in (o.get("candidates") or (turn.get("question") or {}).get("candidates") or []) if c in BY_ID]
    if "object" in want:
        objs = {e["object"] for e in ([ent] if ent else cands)} | ({o.get("object")} if o.get("object") else set())
        if turn.get("action") == "ask" and want["object"] in (turn.get("places") or ""):
            objs.add(want["object"])
        if want["object"] not in objs:
            return False
    if "qual" in want and ent is not None and ent.get("qualifier") != want["qual"]:
        return False
    if "zone" in want and want["zone"] not in (o.get("zone"), o.get("via")):
        return False
    if want.get("close") and not o.get("close"):
        return False
    return True


def main():
    tag = sys.argv[1]
    chain = os.path.join(REPO, "models", f"coop-chain-{tag}", "cpp")
    items = json.load(io.open(os.path.join(HERE, "test_v69_owner.json"), encoding="utf-8"))["items"]
    rows = []
    plain = Brain(None, "en")      # the held lines: no chain
    for lang in ("ru", "en", "es"):
        todo = [it for it in items if it["lang"] == lang]
        if not todo:
            continue
        brain = Brain(chain, lang)
        for k, it in enumerate(todo):
            brain.ask({"cmd": "reset"})
            t = 1000.0 + 100.0 * k
            for b in it.get("before", []):
                brain.ask({"cmd": "text", "text": b, "world": world(t, it.get("gaze_before"))})
                t += 3
            ev = brain.ask({"cmd": "text", "text": it["text"], "world": world(t, it.get("gaze"))})
            got = orders(ev)
            held_lines = (ev.get("chain") or {}).get("held") or []
            held = []
            for line in held_lines:
                plain.ask({"cmd": "reset"})
                held += orders(plain.ask({"cmd": "text", "text": line, "world": world(t, it.get("gaze"))}))

            def passes(g):
                if it.get("remark"):
                    return not any(x[1] not in NO_ORDER for x in g if x[0].get("action") in ("act", "queued"))
                return len(g) >= len(it["want"]) and all(fits(w, x) for w, x in zip(it["want"], g))
            ok, h_ok = passes(got), passes(got + held)
            lines = " | ".join((tu.get("line") or "") for tu in ev.get("turns") or []) + "".join(f" | held: {h}" for h in held_lines)
            said = " / ".join(f"{g[0].get('action')} {g[1]} {(g[2].get('entity') or '')}" for g in got + held) or f"{ev.get('action')} {ev.get('intent')}"
            rows.append((ok, h_ok, it, lines, said))
        brain.close()
    plain.close()
    n, k, kh = len(rows), sum(r[0] for r in rows), sum(r[1] for r in rows)
    log = io.StringIO()
    print(f"chain {tag} on the owner test ({n} lines, the game's path): with held {kh}/{n} = {100 * kh / n:.1f}%, at once {k}/{n} = {100 * k / n:.1f}%", file=log)
    for ok, h_ok, it, lines, said in rows:
        mark = "ok" if ok else ("ok+held" if h_ok else "NO")
        print(f"  {mark:7s} {it['id']:16s} {it['text'][:52]:52s} -> {lines[:84]:84s} [{said[:90]}]", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v69_owner_{tag}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    main()
