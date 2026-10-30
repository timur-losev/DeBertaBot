"""The owner's real play replayed through the brain with the long-term memory: what corrections fix and what they harm, with
the C++ rules as the game runs them (memory_sim.py of 2026-10-29 measured the same in Python: 18 fixed, none harmed).

The owner's 916 labelled heard lines of 2026-10-16..21 (owner_lines_v61.json), in the order he said them, go to two brains
(coop_cli --serve, the classifier alone): one without a memory, one with. The bot is v58 by default, the live bot of those
days: the bots from v61 on were trained on these very lines (v67 reads 98.9% of them right, and a memory has nothing to fix).
A line whose label the bot does not have is left out. When the one with a memory reads a line otherwise
than its label, the owner is taken to correct it at once: the line is taught the label's own words (the bot's phrase for it,
"follow me", one the classifier reads as that label). A line the memory reads is "fixed" when it is right and the brain
without a memory is wrong, "harmed" the other way round.

    python memory_replay.py [--min-fixed N] [--exe ...] [--bot DIR]

Exit 1 when a line is harmed or fewer than N (default 10) are fixed. Build-time tooling.
"""
import argparse, io, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import memory_tests as mt  # noqa: E402


def occurrences():
    occ = []
    for it in json.load(io.open(os.path.join(HERE, "owner_lines_v61.json"), encoding="utf-8"))["items"]:
        for sid in it["said"]:
            occ.append(((sid[0], int(sid[1:])), it["text"], it["maj"]))
    return [(t, m) for _, t, m in sorted(occ)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=os.path.join(mt.REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe"))
    ap.add_argument("--bot", default=os.path.join(mt.REPO, "models", "coop-deberta-v3-ens3-v58", "cpp"))
    ap.add_argument("--min-fixed", type=int, default=10)
    args = ap.parse_args()
    args.chain = None
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    folder = tempfile.mkdtemp(prefix="coop_memory_replay_")
    cfg = json.load(io.open(os.path.join(args.bot, "intent_config.json"), encoding="utf-8"))
    sc = {"lang": "en"}
    # the label's own words, kept only when the classifier reads them as that label
    check = mt.Brain(args, sc, None, os.path.join(folder, "phrases.stderr.txt"))
    words = {}
    for label, phrase in cfg["phrases"].items():
        r = check.send({"cmd": "text", "text": phrase})
        if r.get("intent") == label and r.get("action") not in ("say_again", "ignore"):
            words[label] = phrase
        check.send({"cmd": "reset"})
    check.close()
    plain = mt.Brain(args, sc, None, os.path.join(folder, "plain.stderr.txt"))
    kept = mt.Brain(args, sc, os.path.join(folder, "owner.mv2s"), os.path.join(folder, "memory.stderr.txt"))
    if not kept.ready.get("memory"):
        print("the brain has no memory:", kept.ready.get("memory_note"))
        return 1
    n = right_plain = right_kept = hits = fixed = harmed = taught = no_words = 0
    harms, fixes = [], {}
    t = 100.0
    skipped = 0
    for text, label in occurrences():
        if label not in cfg["labels"]:
            skipped += 1
            continue
        t += 10.0
        # tables and a door: the words every bot knows (v58 refuses a whole world with a crate in it)
        q = {"cmd": "text", "text": text, "world": mt.world(t, {"drop": ["C_1", "C_2"]})}
        a, b = plain.send(q), kept.send(q)
        n += 1
        a_ok, b_ok = a.get("intent") == label, b.get("intent") == label
        right_plain += a_ok
        right_kept += b_ok
        used = (b.get("memory") or {}).get("did") == "used_line"
        if used:
            hits += 1
            if b_ok and not a_ok:
                fixed += 1
                fixes[f"{text} -> {label}"] = fixes.get(f"{text} -> {label}", 0) + 1
            if a_ok and not b_ok:
                harmed += 1
                harms.append(f"{text!r}: the brain alone {a.get('intent')}, the memory gave {b.get('intent')} ({label})")
        if not b_ok:   # the owner corrects it at once
            if label in words:
                kept.send({"cmd": "teach", "heard": text, "lines": [words[label]], "intent": label, "source": "replay"})
                taught += 1
            else:
                no_words += 1
    plain.close()
    kept.close()
    import shutil
    shutil.rmtree(folder, ignore_errors=True)
    bot_name = os.path.basename(os.path.dirname(os.path.normpath(args.bot)))
    print(f"bot {bot_name}; {skipped} lines with a label it does not have left out")
    print(f"memory replay: {n} heard lines of the owner; right {right_plain} -> {right_kept} ({100 * right_plain / n:.1f}% -> "
          f"{100 * right_kept / n:.1f}%); memory read {hits}, fixed {fixed}, harmed {harmed}; taught {taught} times "
          f"({no_words} misread lines had a label without words of its own)")
    print("  fixed most: " + "; ".join(f"{k} x{v}" for k, v in sorted(fixes.items(), key=lambda kv: -kv[1])[:10]))
    for h in harms[:20]:
        print("  HARM " + h)
    ok = harmed == 0 and fixed >= args.min_fixed
    print("memory replay:", "pass" if ok else f"FAIL (harmed {harmed}, fixed {fixed} < {args.min_fixed})" if fixed < args.min_fixed else f"FAIL (harmed {harmed})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
