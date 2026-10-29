"""test66 (chains2/ml_v66/test_v66.json, the items measure_v66.py scores) read by a whole brain as the game reads lines:
measure_v67_cli.py's coop_cli (the classifier, the chain with the decoder as the game runs it, GGUF on the CPU, the planner),
one process per language, the context reset before each item, its lines before said first, its scene in the world.

measure_v66.py reads the decoder's answers made by the Python model (the LoRA on Qwen3 in transformers) and the classifier in
PyTorch; the game runs the GGUF. This scores the same items on the game's path, by measure_v66.py's rules: the first turn's
intent against the label, and its place (measure_v66.place_ok on the turn's English line, the matcher of vocabulary v15).

    python measure_v66_cli.py TAG     TAG as measure_v67_cli.py: v67s15, v68s, v68s2  -> measure_v66_cli_<TAG>.log
"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STT = os.path.normpath(os.path.join(HERE, "..", ".."))
COOP = os.path.normpath(os.path.join(STT, ".."))
sys.path.insert(0, STT)
sys.path.insert(0, COOP)
os.environ["COOP_TAG"] = "v67"
os.environ.setdefault("COOP_PLACES", "locations_v68.json")
import measure_v67_cli as MC
import measure_v66 as M6
import locations as L

MC.BRAINS.setdefault("v68s2", (MC.BRAINS["v67"][0], os.path.join(MC.REPO, "models", "coop-chain-v68s2", "cpp")))


def place_ok(it, text, got):
    """measure_v66.score's place_ok."""
    want = it.get("place")
    if not want or got in M6.NO_PLACE:
        return True
    r = L.record(text)
    t = r["targets"][r["primary"]] if r["primary"] >= 0 else None
    if t is None:
        return False
    if t["object"] == want or t["zone"] == want:
        return True
    return bool(it["before"]) and t["pointer"] in ("it", "this") and t["object"] is None


def main():
    tag = sys.argv[1]
    items = M6.sets()["test66"]
    rows = []
    for lang in ("en", "ru", "es"):
        todo = [it for it in items if it["lang"] == lang]
        brain = MC.Brain(tag, lang)
        for k, it in enumerate(todo):
            brain.ask({"cmd": "reset"})
            t = 1000.0 + 100.0 * k
            for b in it["before"]:
                brain.ask({"cmd": "text", "text": b, "world": MC.world(t, None)})
                t += 3
            ev = brain.ask({"cmd": "text", "text": it["text"], "world": MC.world(t, it.get("scene"))})
            turn = (ev.get("turns") or [ev])[0]
            got = turn.get("intent") or (turn.get("order") or {}).get("intent") or "NONE"
            line = (turn.get("line") or ev.get("english") or it["text"]).split("\n")[0]
            ok = got == it["label"]
            rows.append((ok, ok and place_ok(it, line, got), it, line, got))
        brain.close()
    log = io.StringIO()
    n = len(rows)
    by = {}
    for ok, okp, it, _, _ in rows:
        b = by.setdefault(it["lang"], [0, 0])
        b[0] += okp
        b[1] += 1
    print(f"brain {tag} on test66 ({n} items, the game's path): intent {sum(r[0] for r in rows)}/{n} = {100 * sum(r[0] for r in rows) / n:.1f}%, "
          f"intent and place {sum(r[1] for r in rows)}/{n} = {100 * sum(r[1] for r in rows) / n:.1f}%   ("
          + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items())) + ")", file=log)
    for ok, okp, it, line, got in rows:
        if not okp:
            why = f"read {got:14s} want {it['label']}" if not ok else f"place: want {it.get('place')}"
            print(f"  NO  {it['lang']} {it['text'][:44]:44s} -> {line[:44]:44s} {why}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v66_cli_{tag}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    main()
