"""Bot v57 against bot v58 on going on with a movement: blind/v58/test_cont_r6.json (one AI author who read spec_v58.json only,
not the seeds and not the owner's lines; a test set, never trained on), typed as the bot gets it (lowercased, final .!?
stripped). Per kind of line:
  goon_way, goon_back, boundary   right when the bot acts on an accepted intent: the author's, the 'alt' of a line the author
                                  marked unsure, and the developer's second reading (SECOND_READER)
  goon_bare                       right when the bot does not act: 'say again' (under the gate: the decoder gets a second
                                  look) is counted apart from 'ignore' (read as NONE: no second look) and from REPEAT (the
                                  game does the last order again: a move goes on, anything else is done again)
Lines that are a seed word for word (SEEN) are shown but not counted: they test nothing the training did not see.

    python score_cont_v58.py          -> score_cont_v58.json and the table
"""
import io, json, os, sys
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chains4_v58 as X               # the v57 vocabulary and chains_v54.bot_picks; v58 has the same 47 intents in the same order

MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
TEST = os.path.join(HERE, "..", "blind", "v58", "test_cont_r6.json")
lines = json.load(io.open(TEST, encoding="utf-8"))
assert {t["intent"] for t in lines} <= set(X.V.INTENTS), {t["intent"] for t in lines} - set(X.V.INTENTS)
# the developer read the author's 64 lines and agreed with every intent; besides the author's own 'alt's it accepts:
SECOND_READER = {"t58_011": {"ENTRY"}}    # "Push on forward, slowly.": 'push forward' stays ENTRY (make_spec_v58.py)
SEEN = {"t58_001", "t58_003", "t58_063"}  # "further left", "and down" (v58 seeds), "Yeah, go ahead." (a GO_NOW seed since v2)
for t in lines:
    t["accept"] = {t["intent"]} | ({t["alt"]} if t.get("unsure") and t.get("alt") else set()) | SECOND_READER.get(t["id"], set())
rows = [{"id": t["id"], "text": t["text"]} for t in lines]
out = {}
for bot in ("coop-deberta-v3-ens3-v57", "coop-deberta-v3-ens3-v58"):
    X.C.BOT = os.path.join(MODELS, bot)
    cfg = json.load(io.open(os.path.join(X.C.BOT, "bot_config.json"), encoding="utf-8"))
    assert cfg["labels"] == X.V.INTENTS, bot
    picks, _ = X.C.bot_picks(rows)
    out[bot] = {k: {"pick": p, "top": c[0], "p": c[1]} for k, (p, c) in picks.items()}


def outcome(t, r):
    if t["kind"] == "goon_bare":
        return "right (say again)" if r["pick"] == "NONE" and r["top"] != "NONE" else \
               "right (ignore)" if r["pick"] == "NONE" else "REPEAT" if r["pick"] == "REPEAT" else \
               f"right ({r['pick']}, accepted)" if r["pick"] in t["accept"] else "acts"
    return "right" if r["pick"] in t["accept"] else "say again" if r["pick"] == "NONE" else "wrong"


table = defaultdict(Counter)
for bot, res in out.items():
    for t in lines:
        if t["id"] not in SEEN:
            table[(bot, t["kind"])][outcome(t, res[t["id"]])] += 1
for kind in ("goon_way", "goon_back", "goon_bare", "boundary"):
    n = sum(1 for t in lines if t["kind"] == kind and t["id"] not in SEEN)
    for bot in out:
        print(f"{kind:10} n={n:2}  {bot[-3:]}: " + ", ".join(f"{k} {v}" for k, v in sorted(table[(bot, kind)].items())))
print()
for t in lines:
    a, b = (out[bot][t["id"]] for bot in out)
    if outcome(t, a) != outcome(t, b) or not outcome(t, b).startswith("right"):
        print(f"{'(seen) ' if t['id'] in SEEN else ''}{t['kind']:9} {t['intent']:13} v57 {a['pick']:13} ({a['top']} {a['p']:.2f})  v58 {b['pick']:13} ({b['top']} {b['p']:.2f})  "
              f"{'unsure ' + t.get('alt', '') if t.get('unsure') else ''}  {t['text']}")
json.dump({"test": "blind/v58/test_cont_r6.json", "lines": [dict(t, accept=sorted(t["accept"])) for t in lines], "picks": out}, io.open(os.path.join(HERE, "score_cont_v58.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
