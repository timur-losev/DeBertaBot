"""The timer test (test_v68_time.json, written blind 2026-10-29) through the whole C++ brain: coop_cli --serve with a bot and
a chain (the router, the decoder, the time cut from each English line, the classifier, the planner), the line's language
as the game sets it (ru / es: every line to the decoder; en: the router decides).

Per item: right when the brain gives as many orders as wanted and each has the wanted intent and time (kind, seconds or
min/max, more; null when none was said). Also the time alone (the intents not compared) and the intents alone.

The world has no things, so an order with a place asks ("Which door?") and the brain holds the rest of the line until the
answer (the reply's chain.held: the decoder's English lines). Two scores: "at once", the turns of the reply alone (the
first numbers of 2026-10-29), and "with held", each held line also read by a brain without the chain (the classifier and
the time cut, as a held line is read after the answer).

    python measure_v68_time.py CHAIN_DIR [TAG]      e.g. ...\\models\\coop-chain-v67s\\cpp v67s (answers: measure_v68_time_<TAG>.json)
"""
import io, json, os, subprocess, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.environ.get("COOP_CLI", r"G:\Proj\ollaya\DeBertaBot\cpp\coop_intent\build\Release\coop_cli.exe")
BOT = os.environ.get("COOP_BOT", r"G:\Proj\ollaya\DeBertaBot\models\coop-deberta-v3-ens3-v67\cpp")


def brain(chain, lang):
    args = [EXE, "--serve", "--model-dir", BOT, "--threads", "2", "--no-spin"]
    if chain:
        args += ["--chain", chain, "--decoder-cpu", "--decoder-threads", "4"]
    if lang != "en":
        args += ["--language", lang]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    return p


def read(p):
    while True:
        s = p.stdout.readline()
        if not s:
            raise SystemExit("the brain ended")
        if s.lstrip().startswith("{"):
            return json.loads(s)


def same_time(got, want):
    if want is None or got is None:
        return want is None and got is None
    if got.get("kind") != want.get("kind") or bool(got.get("more")) != bool(want.get("more")):
        return False
    for k in ("seconds", "min", "max"):
        if (k in want) != (got.get(k) is not None):
            return False
        if k in want and abs(float(got[k]) - min(float(want[k]), 60.0)) > 0.05:
            return False
    return True


def main():
    chain = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(os.path.dirname(chain.rstrip("\\/")))
    items = json.load(io.open(os.path.join(HERE, "test_v68_time.json"), encoding="utf-8"))["items"]
    out, n = [], 0
    plain = brain(None, "en")      # the held lines: the classifier and the time cut, no chain
    while read(plain).get("event") != "ready":
        pass
    for lang in ("ru", "es", "en"):
        mine = [it for it in items if it["lang"] == lang]
        if not mine:
            continue
        p = brain(chain, lang)
        while read(p).get("event") != "ready":
            pass
        for it in mine:
            n += 1
            p.stdin.write(json.dumps({"cmd": "reset", "id": 2 * n - 1}) + "\n")
            world = {"entities": [], "player_gaze": None, "bot": {"stance": "stand", "items": [], "busy": False}, "time": 100.0 + n}
            p.stdin.write(json.dumps({"cmd": "text", "text": it["line"], "world": world, "id": 2 * n}, ensure_ascii=False) + "\n")
            p.stdin.flush()
            while True:
                ev = read(p)
                if ev.get("id") == 2 * n and ev.get("event") in ("reply", "error", "nothing"):
                    break
            turns = ev.get("turns") or [ev]
            got = [{"intent": t.get("intent"), "time": t.get("time"), "line": t.get("line"), "action": t.get("action")} for t in turns]
            held = []
            for h, line in enumerate((ev.get("chain") or {}).get("held") or []):
                q = 100000 + 10 * n + h
                plain.stdin.write(json.dumps({"cmd": "reset", "id": q}) + "\n")
                plain.stdin.write(json.dumps({"cmd": "text", "text": line, "world": world, "id": q + 1}, ensure_ascii=False) + "\n")
                plain.stdin.flush()
                while True:
                    hv = read(plain)
                    if hv.get("id") == q + 1 and hv.get("event") in ("reply", "error", "nothing"):
                        break
                held += [{"intent": t.get("intent"), "time": t.get("time"), "line": t.get("line"), "action": t.get("action"), "held": True}
                         for t in (hv.get("turns") or [hv])]
            want = it["want"]
            wt = [dict(w["time"], more=w.get("more", False)) if w.get("time") else None for w in want]

            def scored(g):
                count_ok = len(g) == len(want)
                time_ok = count_ok and all(same_time(x["time"], w) for x, w in zip(g, wt))
                intent_ok = count_ok and all(x["intent"] == w["intent"] for x, w in zip(g, want))
                return time_ok, intent_ok
            time_ok, intent_ok = scored(got)
            h_time, h_intent = scored(got + held)
            out.append({**it, "got": got, "held": held, "time_ok": time_ok, "intent_ok": intent_ok, "ok": time_ok and intent_ok,
                        "h_time_ok": h_time, "h_intent_ok": h_intent, "h_ok": h_time and h_intent})
        p.stdin.close()
        p.wait(timeout=60)
    plain.stdin.close()
    plain.wait(timeout=60)
    path = os.path.join(HERE, f"measure_v68_time_{tag}.json")
    json.dump({"chain": chain, "bot": BOT, "items": out}, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    by = defaultdict(Counter)
    for r in out:
        for key in ("all", r["lang"]):
            by[key]["n"] += 1
            by[key]["ok"] += r["ok"]
            by[key]["time"] += r["time_ok"]
            by[key]["intent"] += r["intent_ok"]
            by[key]["h_ok"] += r["h_ok"]
            by[key]["h_time"] += r["h_time_ok"]
            by[key]["h_intent"] += r["h_intent_ok"]
    print(f"{tag}: timer test, {len(out)} items (answers in {path})")
    for key in ("all", "ru", "es", "en"):
        c = by[key]
        if c["n"]:
            pc = lambda k: 100 * c[k] / c["n"]   # noqa: E731
            print(f"  {key:4s} {c['n']:4d}  at once: whole {pc('ok'):5.1f}%  time {pc('time'):5.1f}%  intents {pc('intent'):5.1f}%"
                  f"   with held: whole {pc('h_ok'):5.1f}%  time {pc('h_time'):5.1f}%  intents {pc('h_intent'):5.1f}%")
    for r in [r for r in out if not r["h_ok"]][:40]:
        print("   NO:", r["id"], r["lang"], r["line"], "| want", [(w["intent"], w.get("time")) for w in r["want"]], "| got",
              [(g["intent"], g["line"], g["time"] and {k: g["time"].get(k) for k in ("kind", "seconds", "min", "max", "more") if g["time"].get(k) is not None}) for g in r["got"] + r["held"]])


if __name__ == "__main__":
    main()
