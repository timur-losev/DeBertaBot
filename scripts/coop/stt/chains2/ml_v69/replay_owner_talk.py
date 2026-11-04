"""The owner's real lines (scripts/coop/owner_talk_v69_candidates.json: 495 lines of his voice tests of 2026-10-31 .. 11-01, as the
recognizer wrote them) said again, in order, through a whole brain on the game's path: the repo's coop_cli --serve with bot v67 and
a chain, Russian mode, the decoder on the CPU. A session is the lines of one game log with no gap over 60 s between them; the
brain is reset before each, and each line is sent at its own time, so the decoder's memory (5 lines, 30 s) holds what it held
in the game. The world is the test range's things (measure_v69_owner.py) with the crosshair on nothing: places the owner looked
at are not known, so the English lines and the intents are what to compare, not the places.

    python replay_owner_talk.py TAG [TAG ...]     -> replay_owner_talk_<TAG>.jsonl (one row a line: the decoder's English per turn,
                                                     the action and intent)
    python replay_owner_talk.py --diff A B        the lines whose English or intents differ between two tags
"""
import io, json, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_v69_owner as M  # noqa: E402

TALK = os.path.normpath(os.path.join(HERE, "..", "..", "..", "owner_talk_v69_candidates.json"))


def sessions(items):
    out, last_log, last_t = [], None, None
    for it in items:
        t = datetime.strptime(it["time"], "%Y.%m.%d-%H.%M.%S").timestamp()
        if it.get("log") != last_log or last_t is None or t - last_t > 60:
            out.append([])
        out[-1].append((t, it))
        last_log, last_t = it.get("log"), t
    return out


def replay(tag):
    items = json.load(io.open(TALK, encoding="utf-8"))["items"]
    b = M.Brain(os.path.join(M.REPO, "models", f"coop-chain-{tag}", "cpp"), "ru")
    rows = []
    for k, sess in enumerate(sessions(items)):
        b.ask({"cmd": "reset"})
        t0 = sess[0][0]
        for t, it in sess:
            ev = b.ask({"cmd": "text", "text": it["text"], "world": M.world(1000.0 * (k + 1) + (t - t0), None)})
            turns = ev.get("turns") or [ev]
            rows.append({"id": it["id"], "text": it["text"], "session": k,
                         "lines": [x.get("line") for x in turns], "acts": [f"{x.get('action')} {x.get('intent')}" for x in turns],
                         "held": (ev.get("chain") or {}).get("held") or []})
    b.close()
    path = os.path.join(HERE, f"replay_owner_talk_{tag}.jsonl")
    with io.open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{tag}: {len(rows)} lines -> {path}")


def diff(a, b):
    load = lambda t: [json.loads(l) for l in io.open(os.path.join(HERE, f"replay_owner_talk_{t}.jsonl"), encoding="utf-8")]
    ra, rb = load(a), load(b)
    n = 0
    for x, y in zip(ra, rb):
        if [s.split()[1] for s in x["acts"]] != [s.split()[1] for s in y["acts"]]:
            n += 1
            print(f"{x['id']}  {x['text'][:60]}")
            print(f"    {a}: {' | '.join(x['acts'])}  {' | '.join(str(l) for l in x['lines'])}  {x['held'] or ''}")
            print(f"    {b}: {' | '.join(y['acts'])}  {' | '.join(str(l) for l in y['lines'])}  {y['held'] or ''}")
    print(f"{n} of {len(ra)} lines read with other intents")


if __name__ == "__main__":
    if sys.argv[1] == "--diff":
        diff(sys.argv[2], sys.argv[3])
    else:
        for tag in sys.argv[1:]:
            replay(tag)
