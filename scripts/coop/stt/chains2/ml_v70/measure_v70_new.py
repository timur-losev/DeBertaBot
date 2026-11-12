"""Round v70's blind test (test_v70_new.json: driving, the body's commands, combos, and their contrasts) read by a whole brain as the
game reads lines: the repo's coop_cli --serve with a bot (default: bot v70) and a chain (router and decoder on the CPU), one process
per language, the context reset before each item, the scene the game sends (the bot at the wheel: "car 0 m"; on foot: no car).

An item passes when the brain's orders (turns that act, are queued, ask or settle) begin with the wanted ones in order:
  - the intent;
  - DRIVE: what the game reads from the turn's line (drive_from_words, the twin of OVCoop::DriveFromWords): the kind, a turn's side
    and count; "to": the order's place is the wanted thing (a pin or "there" are not checked);
  - BODY_MOVE, BODY_COMBO: the turn's line is the wanted console line (or one of "alt"), lower case, its sentence's end and a "bro"
    / "please" at the end left out (as UOVBodyStateComponent::RunCommand reads it).

    python measure_v70_new.py CHAIN [BOT]     CHAIN: a models/coop-chain-<CHAIN>/cpp tag (v69s5, v70); BOT: a models/<BOT>/cpp dir name
                                               (default coop-deberta-v3-ens3-v70) -> measure_v70_new_<CHAIN>.log
"""
import io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
CLI = os.path.join(REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe")
NO_ORDER = {"SMALL_TALK", "PRAISE", "NONE", "YES", "NO", "MAYBE", "DONT_KNOW", None}
# the v16 objects the test names, by the test's place word (make_places_v70.py's ids)
PLACE_IDS = {"bank": "bank", "restaurant": "restaurant", "cafe": "cafe", "shop": "shop", "hotel": "hotel", "pharmacy": "pharmacy",
             "gas station": "gas_station", "parking lot": "parking", "junction": "junction", "traffic light": "traffic_light"}


def E(id, obj, qual=None, b=0.0, d=40.0, el=0.0):
    return {"id": id, "object": obj, "qualifier": qual, "zone": None, "bearing": b, "distance": d, "elevation": el, "tags": []}


WORLD = [E(f"{v}_1", v, None, 20.0 * k - 90.0, 30.0 + 10 * k) for k, v in enumerate(sorted(set(PLACE_IDS.values())))] + \
        [E("main_door_1", "door", "main", 10, 12), E("car_1", "car", None, 40, 4)]
BY_ID = {e["id"]: e for e in WORLD}


class Brain:
    def __init__(self, bot, chain, lang):
        args = [CLI, "--serve", "--no-stt", "--model-dir", bot, "--threads", "2", "--no-spin"]
        if chain:
            args += ["--chain", chain, "--decoder-cpu", "--decoder-threads", "6", "--decoder-every-line"]
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


def world(t, in_car):
    return {"entities": WORLD, "player_gaze": None, "player": {"downed": False}, "bot": {"stance": "stand", "items": [], "busy": False},
            "time": t, "map": "/Game/Maps/L_OVModernCity",
            "scene": {"holding": None, "standing_on": None, "car_m": 0 if in_car else None, "last": None}}


def drive_from_words(words):
    """OVCoop::DriveFromWords (OVCoopBotTypes.cpp): the kind, a turn's side and count."""
    w = " " + re.sub(r"[,.!?;:]", " ", words.lower()) + " "
    has = lambda *a: any(x in w for x in a)  # noqa: E731
    if has(" u-turn ", " u turn ", " uturn ", " car around ", " car round ", " turn around ", " turn round ", " the other way ", " turn it around "):
        return "around", None, 0
    if has(" park ", " pull over ", " pull up ", " parking ", " park it "):
        return "park", None, 0
    if has(" stop the car ", " brake ", " brakes ", " stop driving ", " stop the car here "):
        return "stop", None, 0
    if has(" faster ", " speed up ", " step on it ", " floor it ", " foot down ", " hurry "):
        return "faster", None, 0
    if has(" slower ", " slow down ", " slow the car ", " ease off ", " so fast ", " easy on the gas ", " slowly "):
        return "slower", None, 0
    left, right = " left " in w, " right " in w
    if left != right and has(" turn ", " take ", " hang ", " make a ", " next ", " first ", " second ", " third ", " junction ", " crossroads ",
                             " intersection "):
        return "turn", ("left" if left else "right"), (3 if " third " in w else 2 if " second " in w else 1)
    if has(" forward ", " straight ", " ahead ", " keep driving ", " drive on ", " carry on ", " next junction ", " next crossroads ",
           " next intersection ", " just drive ", " start driving ", " keep going "):
        return "forward", None, 0
    return "to", None, 0


def body_line(line):
    s = (line or "").strip().lower()
    while True:
        s2 = re.sub(r"[.!?]+$", "", s).strip()
        s2 = re.sub(r"\s+(bro|please|now)$", "", s2).strip()
        if s2 == s:
            return s
        s = s2


def orders(ev):
    out = []
    for turn in ev.get("turns") or [ev]:
        if turn.get("action") not in ("act", "queued", "ask", "resolved", "wait"):
            continue
        o = turn.get("order") or {}
        out.append((turn, o.get("intent") or turn.get("intent"), o))
    return out


def fits(want, got):
    turn, intent, o = got
    if intent != want["intent"] and intent not in (want.get("alt_intent") or []):
        return False
    if intent != want["intent"]:
        return True                     # an acceptable other reading (the test's "alt_intent")
    if intent == "DRIVE" and want.get("alt"):
        return any(fits1(w, got) for w in [want] + [dict(want, **a) for a in want["alt"]])
    return fits1(want, got)


def fits1(want, got):
    turn, intent, o = got
    line = turn.get("line") or ""
    if intent == "DRIVE" and "drive" in want:
        kind, side, count = drive_from_words(line)
        if kind != want["drive"]:
            return False
        if kind == "turn" and (side != want.get("side") or count != want.get("count", 1)):
            return False
        if kind == "to" and want.get("place") in PLACE_IDS:
            ent = BY_ID.get(o.get("entity") or turn.get("pending_entity") or "")
            objs = {ent["object"]} if ent else set()
            objs |= {o.get("object")} if o.get("object") else set()
            if PLACE_IDS[want["place"]] not in objs and not (turn.get("action") == "ask" and want["place"] in (turn.get("places") or "")):
                return False
    if intent in ("BODY_MOVE", "BODY_COMBO") and "body" in want:
        if body_line(line) not in [body_line(x) for x in [want["body"]] + list(want.get("alt") or [])]:
            return False
    return True


def main():
    tag, _, chain_tag = sys.argv[1].partition("=")   # NAME=CHAIN: the log under NAME (bot v70b with decoder v70: v70b=v70)
    bot = os.path.join(REPO, "models", sys.argv[2] if len(sys.argv) > 2 else "coop-deberta-v3-ens3-v70", "cpp")
    chain = os.path.join(REPO, "models", f"coop-chain-{chain_tag or tag}", "cpp")
    items = json.load(io.open(os.path.join(HERE, "test_v70_new.json"), encoding="utf-8"))["items"]
    rows = []
    for lang in ("ru", "en", "es"):
        todo = [it for it in items if it["lang"] == lang]
        if not todo:
            continue
        brain = Brain(bot, chain, lang)
        for k, it in enumerate(todo):
            brain.ask({"cmd": "reset"})
            ev = brain.ask({"cmd": "text", "text": it["text"], "world": world(1000.0 + 100.0 * k, it.get("scene") == "car")})
            got = orders(ev)
            ok = len(got) >= len(it["want"]) and all(fits(w, x) for w, x in zip(it["want"], got))
            lines = " | ".join((tu.get("line") or "") for tu in ev.get("turns") or [])
            said = " / ".join(f"{g[0].get('action')} {g[1]}" for g in got) or f"{ev.get('action')} {ev.get('intent')}"
            rows.append((ok, it, lines, said))
        brain.close()
    n, k = len(rows), sum(r[0] for r in rows)
    log = io.StringIO()
    print(f"chain {tag}, bot {os.path.basename(os.path.dirname(bot))}, on test_v70_new ({n} lines, the game's path): {k}/{n} = {100 * k / n:.1f}%", file=log)
    by = {}
    for ok, it, _, _ in rows:
        key = it["want"][0]["intent"] if it["want"] else "-"
        a, b = by.get(key, (0, 0))
        by[key] = (a + ok, b + 1)
    for key, (a, b) in sorted(by.items()):
        print(f"  {key:12s} {a}/{b}", file=log)
    for ok, it, lines, said in rows:
        print(f"  {'ok' if ok else 'NO':3s} {it['id']:12s} {it.get('scene', ''):4s} {it['text'][:50]:50s} -> {lines[:80]:80s} [{said[:60]}]", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v70_new_{tag}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    main()
