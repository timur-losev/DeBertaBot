"""The bot's long-term memory end to end (cpp/coop_intent: bot_memory.h, teach.h, coop_cli --serve --memory FILE).

Talks to `coop_cli --serve --no-stt --memory FILE` as the game does, one typed line at a time with a world, and checks the
replies: "I meant ...", "not that" and its question, a kept line read again (the same words and one word more), names and
colours of things the planner then picks, "forget ...", the doubt after a "no", and the file read again by a new process.
The English scenario runs the classifier alone; the Russian one (--ru) needs the chain (the decoder runs on the CPU).

    python memory_tests.py [--exe coop_cli.exe] [--bot DIR] [--chain DIR] [--ru] [--keep]

Exit 1 on any step that reads otherwise. Build-time tooling: nothing in the game runs it.
"""
import argparse, io, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
GAME_BRAIN = r"J:\UE4\Projects\LyraStarterGame58\Binaries\CoopBrainV6"

ENTITIES = [
    {"id": "T_White", "object": "table", "qualifier": "white", "bearing": -30.0, "distance": 6.0, "elevation": 0.0},
    {"id": "T_Red", "object": "table", "qualifier": "red", "bearing": 30.0, "distance": 7.0, "elevation": 0.0},
    {"id": "C_1", "object": "crate", "qualifier": None, "bearing": -60.0, "distance": 4.0, "elevation": 0.0},
    {"id": "C_2", "object": "crate", "qualifier": None, "bearing": 60.0, "distance": 4.5, "elevation": 0.0},
    {"id": "D_1", "object": "door", "qualifier": None, "bearing": 0.0, "distance": 10.0, "elevation": 0.0},
]


def world(t, gaze=None):
    return {"entities": ENTITIES, "player_gaze": gaze, "player": {"downed": False}, "bot": {"stance": "stand", "items": []},
            "time": t, "map": "/Game/Maps/L_MemoryTest"}


# a step: a line (with the crosshair on `gaze`) or a command, and what the reply must say. A check is a dotted path in the
# reply and its value; {"starts": s} a string that starts so; {"not": v} anything else; {"absent": True} no such field
EN = [
    ("text", "banana", None, {}),
    ("text", "No, I meant follow me.", None, {"intent": "FOLLOW_ME", "memory.did": "kept_line", "say": {"starts": "Got it, I'll remember."}}),
    ("text", "banana", None, {"intent": "FOLLOW_ME", "memory.did": "used_line"}),
    ("text", "mango smoothie now", None, {}),
    ("text", "Not that.", None, {"memory.did": "asked_meaning", "say": "What did you mean?", "order.intent": "SMALL_TALK"}),
    ("text", "hold position", None, {"intent": "HOLD_POSITION", "memory.did": "kept_line"}),
    ("text", "mango smoothie now please", None, {"intent": "HOLD_POSITION", "memory.did": "used_line", "memory.used_line.heard": "mango smoothie now"}),
    ("text", "mango", None, {"memory.did": {"absent": True}}),
    # names: the crosshair on the white table
    ("text", "Call this the workbench.", "T_White", {"memory.did": "kept_name", "memory.kept_name.entity": "T_White", "say": "Got it, I'll remember."}),
    ("text", "go to the workbench", None, {"intent": "MOVE_TO", "order.entity": "T_White", "order.via": "name", "memory.read_as": "go to the table"}),
    ("text", "go to the workbench", "T_Red", {"order.entity": "T_White"}),
    ("text", "Call this the workbench.", None, {"memory.did": "no_thing", "say": "Point at it."}),
    # a plain "this is X" with no order in it
    ("text", "This is the garage", "D_1", {"memory.did": "kept_name", "memory.kept_name.entity": "D_1"}),
    ("text", "open the garage", None, {"intent": "OPEN", "order.entity": "D_1"}),
    # colours
    ("text", "This box is green.", "C_2", {"memory.did": "kept_colour", "memory.kept_colour.colour": "green"}),
    ("text", "go to the green box", None, {"order.entity": "C_2", "order.via": "name"}),
    ("text", "go to the green box", "C_1", {"order.entity": "C_2"}),
    # forget
    ("text", "Forget the name.", "T_White", {"memory.did": "forgot", "say": "Forgotten."}),
    ("text", "go to the workbench", None, {"order.entity": {"not": "T_White"}, "memory.named": {"absent": True}}),
    ("text", "Forget the name.", "T_White", {"memory.did": "not_kept", "say": "I don't remember that."}),
    ("text", "forget banana", None, {"memory.did": "forgot", "memory.forgot_line": "banana"}),
    ("text", "banana", None, {"memory.did": {"absent": True}}),
    ("text", "Forget it.", None, {"memory.teach": "none"}),
    # a kept line doubted twice by "no" right after it
    ("cmd", {"cmd": "teach", "heard": "kiwi", "lines": ["follow me"]}, None, {"event": "taught"}),
    ("text", "kiwi", None, {"intent": "FOLLOW_ME", "memory.did": "used_line"}),
    ("text", "no", None, {"memory.doubted_line": "kiwi"}),
    ("text", "kiwi", None, {"intent": "FOLLOW_ME", "memory.did": "used_line"}),
    ("text", "no", None, {"memory.forgot_line": "kiwi"}),
    ("text", "kiwi", None, {"memory.did": {"absent": True}}),
    # by hand, and the whole memory
    ("cmd", {"cmd": "forget", "heard": "nothing like it"}, None, {"event": "forgot", "none": True}),
    ("cmd", {"cmd": "recall"}, None, {"event": "memory", "memory.lines.#": 1, "memory.names.#": 1, "memory.colours.#": 1}),
]
# a new process on the same file
EN_AGAIN = [
    ("text", "mango smoothie now", None, {"intent": "HOLD_POSITION", "memory.did": "used_line"}),
    ("text", "go to the garage", None, {"order.entity": "D_1"}),
    ("text", "go to the green box", None, {"order.entity": "C_2"}),
]

RU = [
    ("text", "Назови это верстак.", "T_White", {"memory.did": "kept_name", "memory.kept_name.name": "верстак", "say_en": "Got it, I'll remember."}),
    ("text", "Иди к верстаку.", None, {"intent": "MOVE_TO", "order.entity": "T_White", "memory.read_as": "Иди к table."}),
    ("text", "Залезь на верстак", "T_Red", {"order.entity": "T_White"}),
    ("text", "Этот ящик зелёный.", "C_1", {"memory.did": "kept_colour", "memory.kept_colour.colour": "green"}),
    ("text", "Иди к зелёному ящику", None, {"order.entity": "C_1"}),
    ("text", "банан", None, {}),
    ("text", "Нет, я имел в виду иди за мной.", None, {"intent": "FOLLOW_ME", "memory.did": "kept_line", "say_en": {"starts": "Got it, I'll remember."}}),
    ("text", "банан", None, {"intent": "FOLLOW_ME", "memory.did": "used_line"}),
    ("text", "киви апельсин манго", None, {}),
    ("text", "Не то.", None, {"memory.did": "asked_meaning", "say_en": "What did you mean?"}),
    ("text", "стой на месте", None, {"memory.did": "kept_line", "intent": "HOLD_POSITION"}),
    ("text", "киви апельсин манго", None, {"intent": "HOLD_POSITION", "memory.did": "used_line"}),
    ("text", "Забудь верстак", None, {"memory.did": "forgot", "memory.forgot_thing": "T_White"}),
    ("text", "Иди к верстаку", None, {"memory.named": {"absent": True}}),
]


def get(j, path):
    cur = j
    for part in path.split("."):
        if part == "#":
            return len(cur) if isinstance(cur, list) else None
        if not isinstance(cur, dict) or part not in cur:
            return KeyError
        cur = cur[part]
    return cur


def check(reply, expect):
    bad = []
    for path, want in expect.items():
        got = get(reply, path)
        if isinstance(want, dict) and "absent" in want:
            ok = got is KeyError or got is None
        elif isinstance(want, dict) and "starts" in want:
            ok = isinstance(got, str) and got.startswith(want["starts"])
        elif isinstance(want, dict) and "not" in want:
            ok = got != want["not"]
        else:
            ok = got == want
        if not ok:
            bad.append(f"{path}: want {want!r}, got {'(none)' if got is KeyError else repr(got)}")
    return bad


class Brain:
    def __init__(self, args, memory, ru):
        cmd = [args.exe, "--serve", "--no-stt", "--model-dir", args.bot, "--threads", "2", "--no-spin", "--memory", memory]
        if ru:
            cmd += ["--chain", args.chain, "--decoder-cpu", "--decoder-threads", "4", "--language", "ru",
                    "--replies", os.path.join(REPO, "scripts", "coop", "replies", "replies_ru.json")]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  encoding="utf-8", bufsize=1)
        self.ready = self.wait(lambda j: j.get("event") == "ready")
        self.id = 0

    def wait(self, done):
        for line in self.p.stdout:
            if not line.startswith("{"):
                continue
            j = json.loads(line)
            if j.get("event") == "error":
                return j
            if done(j):
                return j
        raise RuntimeError("coop_cli ended")

    def send(self, q):
        self.id += 1
        q = dict(q, id=self.id)
        self.p.stdin.write(json.dumps(q, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        return self.wait(lambda j: j.get("id") == self.id)

    def close(self):
        try:
            self.p.stdin.write('{"cmd":"quit"}\n')
            self.p.stdin.flush()
        except OSError:
            pass
        self.p.wait(timeout=60)


def run(args, memory, steps, ru, name):
    b = Brain(args, memory, ru)
    if b.ready.get("event") != "ready" or not b.ready.get("memory"):
        print(f"{name}: no memory in the brain: {b.ready.get('memory_note') or b.ready}")
        b.close()
        return 1
    bad = 0
    t = 100.0
    for kind, what, gaze, expect in steps:
        t += 10.0
        q = {"cmd": "text", "text": what, "world": world(t, gaze)} if kind == "text" else what
        r = b.send(q)
        problems = check(r, expect)
        shown = what if kind == "text" else json.dumps(what, ensure_ascii=False)
        turn = (r.get("turns") or [r])[0]
        said = turn.get("say_en", turn.get("say", ""))
        line = f"  {'ok ' if not problems else 'BAD'} {shown!s:44} -> {r.get('intent', r.get('event'))} {r.get('action', '')}" \
               f" {((r.get('order') or {}).get('entity'))} | {said} | memory {json.dumps(r.get('memory'), ensure_ascii=False)}"
        print(line)
        for p in problems:
            print("        " + p)
        bad += bool(problems)
    b.close()
    print(f"{name}: {len(steps)} steps, {bad} wrong")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=os.path.join(REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe"))
    ap.add_argument("--bot", default=os.path.join(GAME_BRAIN, "bot"))
    ap.add_argument("--chain", default=os.path.join(GAME_BRAIN, "chain"))
    ap.add_argument("--ru", action="store_true", help="also the Russian scenario (the decoder on the CPU)")
    ap.add_argument("--keep", action="store_true", help="keep the memory files")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    folder = tempfile.mkdtemp(prefix="coop_memory_")
    bad = 0
    en = os.path.join(folder, "en.mv2s")
    bad += run(args, en, EN, False, "en")
    bad += run(args, en, EN_AGAIN, False, "en, the same file in a new process")
    if args.ru:
        bad += run(args, os.path.join(folder, "ru.mv2s"), RU, True, "ru")
    print(f"memory files in {folder}" if args.keep else "")
    if not args.keep:
        import shutil
        shutil.rmtree(folder, ignore_errors=True)
    print("memory tests:", "all pass" if not bad else f"{bad} wrong")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
