"""The bot's long-term memory end to end (cpp/coop_intent: bot_memory.h, teach.h, coop_cli --serve --memory FILE).

Runs the scenarios of memory_scenarios.json: each starts `coop_cli --serve --no-stt` as the game does (its own memory file,
an earlier scenario's, none, or a file of garbage; the player's language, the chain with the decoder on the CPU, the reply
tables, the habit), says its lines one at a time with a world and checks the replies. The world is the game's: its ids
change on every line ("T_White_12"), its keys do not; a step names a thing by its key.

    python memory_tests.py [--only NAME ...] [--no-chain] [--exe coop_cli.exe] [--bot DIR] [--chain DIR] [--keep]

Exit 1 on any step that reads otherwise. Build-time tooling: nothing in the game runs it.
"""
import argparse, io, json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
REPLIES = os.path.join(HERE, "replies")
GAME_BRAIN = r"J:\UE4\Projects\LyraStarterGame58\Binaries\CoopBrainV6"

# the world: two tables, two crates, a door (the keys); ids get the line's count
ENTITIES = [
    {"id": "T_White", "object": "table", "qualifier": "white", "bearing": -30.0, "distance": 6.0, "elevation": 0.0},
    {"id": "T_Red", "object": "table", "qualifier": "red", "bearing": 30.0, "distance": 7.0, "elevation": 0.0},
    {"id": "C_1", "object": "crate", "qualifier": None, "bearing": -60.0, "distance": 4.0, "elevation": 0.0},
    {"id": "C_2", "object": "crate", "qualifier": None, "bearing": 60.0, "distance": 4.5, "elevation": 0.0},
    {"id": "D_1", "object": "door", "qualifier": None, "bearing": 0.0, "distance": 10.0, "elevation": 0.0},
]
KEYS = {e["id"] for e in ENTITIES}
MAP = "/Game/Maps/L_MemoryTest"


def world(t, step, tags=None):
    n = int(t) // 10
    drop = set(step.get("drop", []))
    tags = tags or {}
    entities = [dict(e, id=f"{e['id']}_{n}", key=e["id"], tags=tags.get(e["id"], [])) for e in ENTITIES if e["id"] not in drop] +         step.get("add", [])
    gaze = step.get("gaze")
    if gaze in KEYS:
        gaze = f"{gaze}_{n}"
    return {"entities": entities, "player_gaze": gaze, "player": {"downed": False}, "bot": {"stance": "stand", "items": []},
            "time": t, "map": step.get("map", MAP)}


def strip_count(v):
    """An entity id as the scenarios name it: without the line's count."""
    if isinstance(v, str):
        return re.sub(r"_\d+$", "", v) if re.sub(r"_\d+$", "", v) in KEYS else v
    if isinstance(v, list):
        return [strip_count(x) for x in v]
    return v


def get(j, path):
    cur = j
    for part in path.split("."):
        if part == "#":
            return len(cur) if isinstance(cur, (list, dict)) else KeyError
        if isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)] if int(part) < len(cur) else KeyError
            if cur is KeyError:
                return KeyError
            continue
        if not isinstance(cur, dict) or part not in cur:
            return KeyError
        cur = cur[part]
    return cur


def check(reply, expect):
    bad = []
    for path, want in expect.items():
        got = get(reply, path)
        if path.endswith("entity") or path.endswith("named") or path.endswith("forgot_thing"):
            got = strip_count(got)
        if isinstance(want, dict) and "absent" in want:
            ok = got is KeyError or got is None
        elif isinstance(want, dict) and "contains" in want:
            ok = isinstance(got, str) and want["contains"] in got
        elif isinstance(want, dict) and "starts" in want:
            ok = isinstance(got, str) and got.startswith(want["starts"])
        elif isinstance(want, dict) and "not" in want:
            ok = got != want["not"]
        elif isinstance(want, dict) and "in" in want:
            ok = got in want["in"]
        elif isinstance(want, dict) and "has" in want:
            ok = isinstance(got, list) and want["has"] in got
        else:
            ok = got == want
        if not ok:
            bad.append(f"{path}: want {want!r}, got {'(none)' if got is KeyError else repr(got)}")
    return bad


class Brain:
    def __init__(self, args, sc, memory, log):
        cmd = [args.exe, "--serve", "--no-stt", "--model-dir", args.bot, "--threads", "2", "--no-spin"]
        if memory:
            cmd += ["--memory", memory]
        lang = sc.get("lang", "en")
        if sc.get("chain"):
            cmd += ["--chain", args.chain, "--decoder-cpu", "--decoder-threads", "4"]
        if lang != "en":
            cmd += ["--language", lang]
        if sc.get("replies"):
            cmd += ["--replies", os.path.join(REPLIES, f"replies_{sc['replies']}.json")]
        if sc.get("bro"):
            cmd += ["--replies-bro", os.path.join(REPLIES, f"replies_{lang}_brat.json"), "--bro", sc["bro"]]
        self.log = log
        self.err = open(log, "w", encoding="utf-8", errors="replace")
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err,
                                  encoding="utf-8", bufsize=1)
        self.ready = self.wait(lambda j: j.get("event") in ("ready", "error"))
        self.id = 0

    def wait(self, done):
        for line in self.p.stdout:
            if not line.startswith("{"):
                continue
            j = json.loads(line)
            if done(j):
                return j
        self.p.wait(timeout=10)
        self.err.flush()
        tail = io.open(self.log, encoding="utf-8", errors="replace").read().strip().splitlines()[-8:]
        raise RuntimeError(f"coop_cli ended (exit {self.p.returncode}); its stderr ends:\n    " + "\n    ".join(tail))

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
        self.err.close()


def run(args, sc, folder):
    mem = sc.get("memory", "new")
    if mem == "none":
        memory = None
    elif mem.startswith("reuse:"):
        memory = os.path.join(folder, mem[6:] + ".mv2s")
    else:
        memory = os.path.join(folder, sc["name"] + ".mv2s")
        if mem == "garbage":
            with open(memory, "wb") as f:
                f.write(b"\x5a" * 4096)
    b = Brain(args, sc, memory, os.path.join(folder, sc["name"] + ".stderr.txt"))
    bad = 0
    problems = check(b.ready, sc.get("ready", {})) if b.ready.get("event") == "ready" else [f"no ready: {b.ready}"]
    if memory and mem != "garbage" and b.ready.get("event") == "ready" and not b.ready.get("memory"):
        problems.append(f"no memory in the brain: {b.ready.get('memory_note')}")
    if problems:
        bad += 1
        print(f"  BAD (ready) {'; '.join(problems)}")
    t = 100.0
    for step in sc["steps"]:
        t += 10.0
        if "pause" in step:
            time.sleep(step["pause"])
            print(f"  ok  (a pause of {step['pause']} s)")
            continue
        if "say" in step:
            r = b.send({"cmd": "text", "text": step["say"], "world": world(t, step, sc.get("tags"))})
            shown = step["say"] + (f" @{step['gaze']}" if step.get("gaze") else "")
        else:
            r = b.send(step["cmd"])
            shown = json.dumps(step["cmd"], ensure_ascii=False)
        problems = check(r, step.get("expect", {}))
        turn = (r.get("turns") or [r])[0]
        said = turn.get("say", "")
        entity = strip_count((turn.get("order") or {}).get("entity"))
        mem_info = r.get("memory")
        mem_text = json.dumps({k: v for k, v in mem_info.items() if k != "teach"} if isinstance(mem_info, dict) and "lines" not in mem_info else
                              ("(all)" if mem_info else None), ensure_ascii=False)
        print(f"  {'ok ' if not problems else 'BAD'} {shown[:46]:46} -> {r.get('intent', r.get('event'))} {r.get('action', '')} {entity} | "
              f"{said} | {mem_text}"[:330])
        for p in problems:
            print("        " + p)
        bad += bool(problems)
    b.close()
    print(f"{sc['name']}: {len(sc['steps'])} steps, {bad} wrong")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=os.path.join(REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe"))
    ap.add_argument("--bot", default=os.path.join(GAME_BRAIN, "bot"))
    ap.add_argument("--chain", default=os.path.join(GAME_BRAIN, "chain"))
    ap.add_argument("--scenarios", default=os.path.join(HERE, "memory_scenarios.json"))
    ap.add_argument("--only", action="append", help="this scenario (and the ones it reuses the file of)")
    ap.add_argument("--no-chain", action="store_true", help="leave out the scenarios that need the decoder")
    ap.add_argument("--keep", action="store_true", help="keep the memory files")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    scenarios = json.load(io.open(args.scenarios, encoding="utf-8"))["scenarios"]
    want = set(args.only or [s["name"] for s in scenarios])
    for s in scenarios:   # a scenario that reuses a file needs the one that made it
        if s["name"] in want and s.get("memory", "").startswith("reuse:"):
            want.add(s["memory"][6:])
    folder = tempfile.mkdtemp(prefix="coop_memory_")
    bad, ran = 0, 0
    for sc in scenarios:
        if sc["name"] not in want or (args.no_chain and sc.get("chain")):
            continue
        print(f"-- {sc['name']} ({sc.get('lang', 'en')}{', chain' if sc.get('chain') else ''}{', memory ' + sc['memory'] if 'memory' in sc else ''})")
        bad += run(args, sc, folder)
        ran += 1
    if args.keep:
        print(f"memory files in {folder}")
    else:
        import shutil
        shutil.rmtree(folder, ignore_errors=True)
    print(f"memory tests: {ran} scenarios, " + ("all pass" if not bad else f"{bad} wrong"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
