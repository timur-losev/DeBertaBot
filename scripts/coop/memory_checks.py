"""Every check of the bot's long-term memory, one after another, with a summary (2026-10-29).

  1. rules       coop_cli --teach-tests tools/teach_tests.json: the teaching lines and the text rules (teach.h), by hand
  2. corpus      teach_corpus_check.py: the rules on 16 000+ order lines in three languages take none for teaching
  3. store       coop_cli --memory-store-tests: the file -- kept and read back, the matching rule, doubts, a file held
                 twice, compaction, a cut-short compaction, unreadable files, a folder named in Cyrillic
  4. scenarios   memory_tests.py: the whole brain through --serve (memory_scenarios.json; Russian and Spanish through the
                 chain, the decoder on the CPU)
  5. invariance  memory_invariance.py: an empty memory changes no reply (English; with --full also Russian and Spanish)
  6. replay      memory_replay.py: the owner's 913 real lines through bot v58 with a memory: fixed, harmed (none)
  7. game        with --game: the game's automation test Project.OV.CoopBot.Memory and the E2E Tests/E2E/memory.txt on
                 the test range (a dedicated server and a client, no graphics; the editor must be closed), its client log
                 checked line by line

    python memory_checks.py [--quick] [--full] [--game | --game-only] [--exe coop_cli.exe]

--quick leaves out the chain (4) and the replay (6). Exit 1 when any check fails. Build-time tooling.
"""
import argparse, io, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
CPP = os.path.join(REPO, "cpp", "coop_intent")
GAME = r"J:\UE4\Projects\LyraStarterGame58"
ENGINE = r"J:\UE5.7SRC\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

# the E2E's client log: after each mark, what must be in it before the next one
E2E_EXPECT = {
    "name_it": [r"the brain's memory kept_name: .*\"key\":\"OVCoopPlaceMarker_", r"Buddy: Got it, I'll remember\."],
    "go_by_name": [r"order MOVE_TO @ white table", r"the brain's memory named: .*\"read_as\":\"go to the table\""],
    "what_named": [r"Buddy: That's the workbench\."],
    "meant": [r"the brain's memory kept_line: .*\"heard\":\[\"banana\"\]", r"Buddy: Got it, I'll remember\."],
    "banana_2": [r"the brain's memory used_line"],
    "banana_after_restart": [r"the brain's memory used_line"],
    "go_after_restart": [r"order MOVE_TO @ white table"],
    "colour": [r"the brain's memory kept_colour: .*\"colour\":\"green\""],
    "go_green": [r"the brain's memory named"],
    "not_that": [r"the brain's memory asked_meaning", r"Buddy: What did you mean\?"],
    "meaning": [r"the brain's memory kept_line"],
    "zorbl_2": [r"the brain's memory used_line"],
    "nazovi": [r"the brain's memory kept_name: .*верстак", r"Buddy: Понял, запомню\."],
    "idi_k_verstaku": [r"order MOVE_TO @ white table"],
    "chto_eto": [r"Buddy: Это верстак\."],
    "zabud": [r"the brain's memory forgot", r"Buddy: Всё, забыл\."],
    # the owner's lines of 2026-10-30
    "chto_eto_3": [r"Buddy: That's the white table\."],
    "net_zheltyi": [r"the brain's memory kept_colour: .*\"colour\":\"yellow\"", r"Buddy: Понял, запомню\."],
    "chto_eto_zheltyi": [r"the brain's memory coloured_thing", r"Buddy: Это жёлтый стол\."],
    "kakogo_tsveta_stol": [r"the brain's memory colour_of", r"Buddy: Это жёлтый стол\."],
    "idi_k_zheltomu": [r"order MOVE_TO @ white table"],
    "net_fonar": [r"the brain's memory offered_name", r"Buddy: Запомнить, что это красный фонарь\?"],
    "da_fonar": [r"the brain's memory kept_name: .*красный фонарь", r"Buddy: Понял, запомню\."],
    "chto_eto_fonar": [r"the brain's memory named_thing", r"Buddy: Это красный фонарь\."],
    "kakogo_tsveta_stul": [r"the brain's memory no_colour", r"Buddy: Не знаю, какого это цвета\."],
}
E2E_NEVER = [r"lease already held", r"TIMED OUT", r"coop_cli ended", r"brain: .*exited"]


def run(cmd, cwd=None, timeout=None):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or ""), time.time() - t0


def last_line(out, pattern):
    lines = [l for l in out.splitlines() if re.search(pattern, l)]
    return lines[-1].strip() if lines else out.strip().splitlines()[-1] if out.strip() else "(no output)"


def check_e2e_log(path):
    if not os.path.exists(path):
        return False, f"no client log at {path}"
    text = io.open(path, encoding="utf-8", errors="replace").read()
    parts = re.split(r"LogOVCoopBot: script: mark (\S+)", text)
    seen = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    problems = []
    for mark, patterns in E2E_EXPECT.items():
        if mark not in seen:
            problems.append(f"mark {mark} never reached")
            continue
        for pat in patterns:
            if not re.search(pat, seen[mark]):
                problems.append(f"after mark {mark}: no /{pat}/")
    for pat in E2E_NEVER:
        m = re.search(pat, text)
        if m:
            problems.append(f"the log has /{pat}/: ...{text[max(0, m.start() - 80):m.end() + 40]!r}")
    return not problems, "; ".join(problems) if problems else f"{len(E2E_EXPECT)} marks, every line there"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=os.path.join(CPP, "build", "Release", "coop_cli.exe"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--full", action="store_true", help="the invariance check also in Russian and Spanish")
    ap.add_argument("--game", action="store_true")
    ap.add_argument("--game-only", action="store_true", help="the game's checks alone")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    py = sys.executable
    results = []

    def step(name, cmd, ok_pattern, cwd=None, timeout=3600):
        print(f"-- {name}: {' '.join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd))}")
        code, out, secs = run(cmd, cwd, timeout)
        summary = last_line(out, ok_pattern)
        ok = code == 0
        if not ok:
            print("\n".join(out.strip().splitlines()[-25:]))
        results.append((name, ok, summary, secs))
        print(f"   {'PASS' if ok else 'FAIL'} ({secs:.0f} s): {summary}")

    if args.game_only:
        args.game = True
    else:
        brain_checks(args, step, py)
    game_checks(args, step, results)

    print("\nmemory checks:")
    for name, ok, summary, secs in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:22} {secs:6.0f} s  {summary[:150]}")
    bad = sum(not ok for _, ok, _, _ in results)
    print("all pass" if not bad else f"{bad} failed")
    return 1 if bad else 0


def brain_checks(args, step, py):
    step("rules", [args.exe, "--teach-tests", os.path.join(CPP, "tools", "teach_tests.json")], r"teach tests")
    step("corpus", [py, os.path.join(HERE, "teach_corpus_check.py"), "--exe", args.exe], r"teach tests")
    store_dir = os.path.join(tempfile.gettempdir(), f"coop_memory_store_{os.getpid()}")
    step("store", [args.exe, "--memory-store-tests", store_dir], r"memory store tests")
    step("scenarios", [py, os.path.join(HERE, "memory_tests.py"), "--exe", args.exe] + (["--no-chain"] if args.quick else []), r"memory tests:")
    step("invariance", [py, os.path.join(HERE, "memory_invariance.py"), "--exe", args.exe] + (["--chain"] if args.full else []),
         r"memory invariance")
    if not args.quick:
        step("replay", [py, os.path.join(HERE, "memory_replay.py"), "--exe", args.exe], r"memory replay: \d+ heard")


def game_checks(args, step, results):
    if args.game:
        busy = subprocess.run(["tasklist"], capture_output=True, encoding="utf-8", errors="replace").stdout
        if re.search(r"UnrealEditor\.exe|LyraGame\.exe", busy):
            results.append(("game", False, "the editor or the game is running: close it first", 0))
        else:
            uproject = os.path.join(GAME, "LyraStarterGame.uproject")
            log = os.path.join(tempfile.gettempdir(), "coop_memory_automation.log")
            step("game: automation", [ENGINE, uproject, "-ExecCmds=Automation RunTests Project.OV.CoopBot.Memory; Quit", "-nullrhi",
                                      "-unattended", "-nosplash", "-nosound", f"-abslog={log}"], r".")
            text = io.open(log, encoding="utf-8", errors="replace").read() if os.path.exists(log) else ""
            ok = "Result={Success} Name={Memory}" in text and "EXIT CODE: 0" in text
            results[-1] = ("game: automation", ok, "Project.OV.CoopBot.Memory " + ("passed" if ok else "did not pass (see " + log + ")"), results[-1][3])
            e2e = os.path.join(GAME, "Source", "LyraGame", "CoopBot", "Tests", "E2E")
            t0 = time.time()
            subprocess.run(["pwsh", "-NoProfile", "-File", os.path.join(e2e, "run_server_client.ps1"), "-Tag", "memory", "-Script", "memory.txt",
                            "-Map", "/Game/Maps/L_OVTestRange"], cwd=e2e, capture_output=True, encoding="utf-8", errors="replace")
            ok, summary = check_e2e_log(os.path.join(GAME, "Saved", "CoopBotE2E", "e2e_memory_client.log"))
            results.append(("game: E2E memory.txt", ok, summary, time.time() - t0))
            print(f"   {'PASS' if ok else 'FAIL'}: {summary}")


if __name__ == "__main__":
    sys.exit(main())
