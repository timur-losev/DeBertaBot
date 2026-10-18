"""The owner's lines that lean on the talk (chains2/owner_ctx_v58.json, a test set) through a brain end to end, as the
game runs it: coop_cli --serve with the router and the decoder (on the CPU), a reset before each item, the item's earlier
lines said first (each read and remembered as the game's brain would), then the line. Scored: the orders of the order
lines the brain made of it, against the expected ones.

    python owner_ctx_score.py <coop_cli.exe> <bot cpp dir> <chain cpp dir> [out.json]

The planner's own words before an item (its question) come from its world, which is not the game's: the items whose
reading hangs on the bot's question are marked. Spoken lines are given as the game's brain reads them (lowercase, no
final .!?: coop::SpeechTextForClassifier)."""
import io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SET = os.path.join(HERE, "chains2", "owner_ctx_v58.json")
WORLD = {"entities": [
    {"id": "car", "object": "car", "qualifier": None, "zone": "floor_1", "bearing": 10.0, "distance": 4.0, "elevation": 0.0, "tags": []},
    {"id": "win_a", "object": "window", "qualifier": None, "zone": "floor_1", "bearing": -20.0, "distance": 9.0, "elevation": 1.0, "tags": []},
    {"id": "win_b", "object": "window", "qualifier": None, "zone": "floor_1", "bearing": 25.0, "distance": 11.0, "elevation": 1.0, "tags": []},
    {"id": "door_a", "object": "door", "qualifier": None, "zone": "floor_1", "bearing": 50.0, "distance": 8.0, "elevation": 0.0, "tags": []},
    {"id": "stairs_a", "object": "stairs", "qualifier": "blue", "zone": "floor_1", "bearing": 40.0, "distance": 7.0, "elevation": 0.0, "tags": []}],
    "player_pin": {"id": "pin", "entity": None, "bearing": -10.0, "distance": 12.0, "elevation": 0.0},
    "bot_pin": None, "player_gaze": None, "player": {"downed": False}, "bot": {"stance": "stand", "items": [], "busy": False}}


def spoken(t):
    t = t.strip()
    while t and t[-1] in ".!?":
        t = t[:-1]
    return t.lower()


def main():
    exe, bot, chain = sys.argv[1:4]
    out = sys.argv[4] if len(sys.argv) > 4 else None
    items = json.load(io.open(SET, encoding="utf-8"))["items"]
    reqs, plan = [], []
    for it in items:
        reqs.append({"cmd": "reset"})
        for k, b in enumerate(it["before"]):
            reqs.append({"cmd": "text", "text": spoken(b), "world": dict(WORLD, time=100.0 + k)})
            plan.append(None)
        reqs.append({"cmd": "text", "text": spoken(it["line"]), "world": dict(WORLD, time=110.0)})
        plan.append(it)
    proc = subprocess.run([exe, "--serve", "--model-dir", bot, "--threads", "2", "--no-spin", "--no-stt", "--chain", chain,
                           "--decoder-threads", "4", "--decoder-cpu"], input="\n".join(json.dumps(r) for r in reqs) + "\n",
                          capture_output=True, text=True, encoding="utf-8", timeout=1800, cwd=os.path.dirname(exe))
    replies = [d for d in (json.loads(l) for l in proc.stdout.splitlines() if l.startswith("{")) if d.get("event") == "reply"]
    assert len(replies) == len(plan), (len(replies), len(plan), proc.stderr[-2000:])
    ok, rows = 0, []
    for it, d in zip(plan, replies):
        if it is None:
            continue
        turns = d.get("turns") or []
        got = [t.get("intent") for t in turns if t.get("action") in ("act", "resolved", "queued", "go", "execute", "wait", "negated")]
        good = got == it["orders"]
        ok += good
        c = d.get("chain", {})
        rows.append({"id": it["id"], "line": it["line"], "want": it["orders"], "got": got, "ok": good,
                     "lines": [t.get("line") for t in turns], "actions": [t.get("action") for t in turns],
                     "route": round(c.get("route", -1), 2), "decoded": c.get("decoded"), "rewritten": c.get("rewritten"),
                     "asked": it["bot"] is not None})
        print(f"{'ok ' if good else 'NO '} {it['id']}  \"{it['line']}\" -> {[t.get('line') for t in turns]} {[(t.get('action'), t.get('intent')) for t in turns]}"
              f"  route {c.get('route', -1):.2f}{' rewritten' if c.get('rewritten') else ' as it is' if c.get('decoded') else ''}")
    print(f"{ok}/{len(rows)} read as expected")
    if out:
        json.dump(rows, io.open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
