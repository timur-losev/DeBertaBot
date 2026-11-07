"""The owner's English lines from the game (owner_lines_v61/v64/v65/v66.json: 649 different lines as the recognizer heard them,
each with its intent as labelled) read by a whole brain on the game's path (measure_v67_cli.py's coop_cli: bot v67, chain v69s5,
the decoder on the CPU, the planner), English mode, the context reset before each line: with the router as before (tag v69s5now)
and with every line through the decoder (v69s5all: coop_cli --decoder-every-line, 2026-11-06, the owner: «пусть LLM работает
даже в английской версии на каждой фразе»).

A line is right when the brain's first turn that acts, is queued or asks has the labelled intent (a line labelled NONE: when no
turn acts). Per different line and per time said (the line's count). The lines read differently by the two are listed.

    python measure_en_every_line.py            -> measure_en_every_line.log next to this file
"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STT = os.path.normpath(os.path.join(HERE, "..", ".."))
COOP = os.path.normpath(os.path.join(STT, ".."))
sys.path.insert(0, STT)
import measure_v67_cli as MC  # noqa: E402

FILES = ["owner_lines_v61.json", "owner_lines_v64.json", "owner_lines_v65.json", "owner_lines_v66.json"]


def first_intent(ev):
    for t in ev.get("turns") or [ev]:
        if t.get("action") in ("act", "queued", "ask", "resolved"):
            return t.get("intent"), t.get("line") or ""
    t = (ev.get("turns") or [ev])[0]
    return ("NONE" if t.get("action") in ("ignore", "say_again", "say") else t.get("intent")), t.get("line") or ""


def run(tag, items):
    brain = MC.Brain(tag, "en")
    out = []
    for k, it in enumerate(items):
        brain.ask({"cmd": "reset"})
        ev = brain.ask({"cmd": "text", "text": it["text"], "world": MC.world(1000.0 + 100.0 * k, None)})
        out.append(first_intent(ev) + ((ev.get("turns") or [ev])[0].get("action"),))
    brain.close()
    return out


def main():
    items = []
    for f in FILES:
        items += json.load(io.open(os.path.join(COOP, f), encoding="utf-8"))["items"]
    log = io.StringIO()
    res = {tag: run(tag, items) for tag in ("v69s5now", "v69s5all")}
    for tag, got in res.items():
        right = [g[0] == it["maj"] for g, it in zip(got, items)]
        again = [g[2] == "say_again" for g in got]
        n, w = len(items), sum(it.get("count", 1) for it in items)
        print(f"{tag}: per line {sum(right)}/{n} = {100 * sum(right) / n:.1f}%, per time said "
              f"{100 * sum(r * it.get('count', 1) for r, it in zip(right, items)) / w:.1f}%, said again {sum(again)}", file=log)
    a, b = res["v69s5now"], res["v69s5all"]
    better = [(it, x, y) for it, x, y in zip(items, a, b) if x[0] != it["maj"] and y[0] == it["maj"]]
    worse = [(it, x, y) for it, x, y in zip(items, a, b) if x[0] == it["maj"] and y[0] != it["maj"]]
    print(f"\nright only with every line through the decoder: {len(better)}; right only with the router: {len(worse)}", file=log)
    for name, rows in (("BETTER with --decoder-every-line", better), ("WORSE with --decoder-every-line", worse)):
        print(f"\n{name}:", file=log)
        for it, x, y in rows:
            print(f"  {it['text']!r} (x{it.get('count', 1)}) want {it['maj']}: router {x[0]} | every line {y[0]} {y[1]!r}", file=log)
    io.open(os.path.join(HERE, "measure_en_every_line.log"), "w", encoding="utf-8").write(log.getvalue())
    print(log.getvalue())


if __name__ == "__main__":
    main()
