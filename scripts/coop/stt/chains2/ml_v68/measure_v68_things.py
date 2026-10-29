"""The held-out test of round v68's new things (test_v68_things.json: the bed to sleep on, the garden bed, the rock; written
blind 2026-10-29) read by a whole brain as the game reads lines: measure_v67_cli.py's brain, world and scores (intent,
+ target, + means), in a world that also has two beds (yellow, red), two garden beds (north, south) and two rocks (big,
small) in place of test67's one bed.

    python measure_v68_things.py TAG     TAG as measure_v67_cli.py: v67s15 (v67s on today's bot files), v68s, v68s2
-> measure_v68_things_<TAG>.log
"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, STT)
import measure_v67_cli as MC

MC.ENTITIES = [e for e in MC.ENTITIES if e[1] != "bed"] + [
    ("bed_y", "bed", "yellow", -110, 18), ("bed_r", "bed", "red", -125, 14),
    ("garden_bed_n", "garden_bed", "north", 105, 28), ("garden_bed_s", "garden_bed", "south", 115, 32),
    ("rock_big", "rock", "big", -50, 9), ("rock_small", "rock", "small", 35, 7)]
MC.BY_ID = {e[0]: e for e in MC.ENTITIES}
MC.BRAINS.setdefault("v68s2", (MC.BRAINS["v67"][0], os.path.join(MC.REPO, "models", "coop-chain-v68s2", "cpp")))


def orders_of(ev):
    """measure_v67_cli.orders_of, but a question's thing is read from its candidates when it has them: "harvest the bed"
    asks "Which garden bed?" (the garden rule), while the reply's "places" text still says the matcher's "* bed"."""
    out = MC.orders_of(ev)
    turns = [t for t in (ev.get("turns") or [ev])
             if t.get("action") in ("act", "queued", "ask", "resolved", "execute") and ((t.get("order") or {}).get("intent") or t.get("intent"))]
    for k, (turn, got) in enumerate(zip(turns, out)):
        cands = (turn.get("question") or {}).get("candidates") or []
        objs = {MC.BY_ID[c][1] for c in cands if c in MC.BY_ID}
        if turn.get("action") == "ask" and not turn.get("order") and len(objs) == 1:
            out[k] = (got[0], objs.pop(), None) + got[3:]
    return out


def main():
    tag = sys.argv[1]
    items = [{"id": it["id"], "lang": it["lang"], "before": it.get("before") or [], "scene": it.get("scene") or None,
              "text": it["line"], "want": it["want"], "cat": it.get("cat")}
             for it in json.load(io.open(os.path.join(HERE, "test_v68_things.json"), encoding="utf-8"))["items"]]
    rows = []
    for lang in ("en", "ru", "es"):
        todo = [it for it in items if it["lang"] == lang]
        if not todo:
            continue
        brain = MC.Brain(tag, lang)
        for k, it in enumerate(todo):
            brain.ask({"cmd": "reset"})
            t = 1000.0 + 100.0 * k
            for b in it["before"]:
                brain.ask({"cmd": "text", "text": b, "world": MC.world(t, None)})
                t += 3
            ev = brain.ask({"cmd": "text", "text": it["text"], "world": MC.world(t, it.get("scene"))})
            got = orders_of(ev)
            want = it["want"]
            per = [MC.matches(w, g) for w, g in zip(want, got)]
            n_ok = len(got) == len(want)
            rows.append((it, got, tuple(n_ok and all(p[i] for p in per) for i in range(3))))
        brain.close()
    log = io.StringIO()
    n = len(rows)
    print(f"brain {tag} on test68 things ({n} items): " + ", ".join(
        f"{name} {sum(r[2][i] for r in rows)}/{n} = {100 * sum(r[2][i] for r in rows) / n:.1f}%" for i, name in enumerate(("intent", "+ target", "+ means"))), file=log)
    for key, name in ((lambda r: r[0]["lang"], "language"), (lambda r: r[0].get("cat"), "category")):
        by = {}
        for r in rows:
            b = by.setdefault(key(r), [0, 0, 0, 0])
            for i in range(3):
                b[i] += r[2][i]
            b[3] += 1
        print(f"  by {name} (intent / + target / + means): " + ", ".join(f"{k}: {v[0]}/{v[1]}/{v[2]} of {v[3]}" for k, v in sorted(by.items(), key=lambda x: str(x[0]))), file=log)
    for it, got, score in rows:
        if not score[2]:
            w = "; ".join(f"{x['intent']} {(x.get('target') or {}).get('object')}/{(x.get('target') or {}).get('qualifier')} by "
                          f"{(x.get('means') or {}).get('object')}" for x in it["want"])
            g = "; ".join(f"{x[0]} {x[1]}/{x[2]} by {x[3]} ({x[4]})" for x in got) or "nothing"
            print(f"  NO  [{it.get('cat')}] {it['lang']} {it['text'][:50]:50s} -> {g}   want {w}   | {' / '.join(x[5] for x in got)[:80]}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v68_things_{tag}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    main()
