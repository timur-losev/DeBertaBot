"""An empty long-term memory changes nothing: the brain with `--memory` and nothing taught hears every line as the brain
without it does (coop_cli --serve).

Two brains get the same lines in the same worlds, one after the other: the owner's heard lines in the order he said them,
the dev lines and the held-out tests of rounds v66 and v67 in English (the classifier alone); with --chain also their Russian
and Spanish lines (the decoder on the CPU). Every few lines the crosshair is on a thing, and the world's ids change on every
line as the game's do. Teaching lines (teach.h: "I meant ...", "not that", a name) are left out: those are the memory's to
answer. Every field of the two replies must be equal but the words chosen among a reply's variants and the "memory" note.

    python memory_invariance.py [--chain] [--limit N] [--exe ...] [--bot DIR]

Exit 1 on any difference. Build-time tooling.
"""
import argparse, io, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import memory_tests as mt  # noqa: E402

CH = os.path.join(HERE, "stt", "chains2")
SKIP = {"say", "say_en", "say_untranslated", "ms", "memory", "id", "audio_s", "stt_ms", "route_ms", "rewrite_ms", "bro_active"}


def owner_lines():
    """The owner's heard lines in the order he said them (session a, then b; the said ids are their places)."""
    occ = []
    for it in json.load(io.open(os.path.join(HERE, "owner_lines_v61.json"), encoding="utf-8"))["items"]:
        for sid in it["said"]:
            occ.append(((sid[0], int(sid[1:])), it["text"]))
    return [t for _, t in sorted(occ)]


def corpus(lang, limit):
    lines = []
    if lang == "en":
        lines += owner_lines()
        lines += [c["text"] for c in json.load(io.open(os.path.join(HERE, "dev.json"), encoding="utf-8"))["cases"]]
    for rel in ("ml_v66/test_v66.json", "ml_v67/test_v67.json", "ml_v68/test_v68_things.json"):
        for it in json.load(io.open(os.path.join(CH, rel), encoding="utf-8"))["items"]:
            if it.get("lang", "en") == lang:
                lines += it.get("before", []) + [it.get("line", it.get("text"))]
    return lines[:limit] if limit else lines


def teaching(exe, lines, lang):
    """The lines the teaching rules take (teach.h), by coop_cli --teach-tests."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([{"line": l, "lang": lang, "kind": "none"} for l in lines], f, ensure_ascii=False)
        path = f.name
    out = subprocess.run([exe, "--teach-tests", path], capture_output=True, encoding="utf-8").stdout
    os.unlink(path)
    taken = set()
    for l in out.splitlines():
        if l.startswith("  {"):
            taken.add(json.loads(l.strip())["line"])
    return taken


def strip(j):
    if isinstance(j, dict):
        return {k: strip(v) for k, v in j.items() if k not in SKIP}
    if isinstance(j, list):
        return [strip(x) for x in j]
    if isinstance(j, float):
        return round(j, 5)
    return j


def diff(a, b, path=""):
    if type(a) != type(b):
        return [f"{path}: {a!r} vs {b!r}"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: {len(a)} items vs {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {a!r} vs {b!r}"]


def run(args, lang, chain, folder):
    lines = corpus(lang, args.limit)
    taken = teaching(args.exe, lines, lang)
    lines = [l for l in lines if l not in taken]
    sc = {"lang": lang, "chain": chain}
    a = mt.Brain(args, sc, None, os.path.join(folder, f"{lang}_without.stderr.txt"))
    b = mt.Brain(args, sc, os.path.join(folder, f"{lang}.mv2s"), os.path.join(folder, f"{lang}_with.stderr.txt"))
    if not b.ready.get("memory"):
        print(f"{lang}: the brain has no memory: {b.ready.get('memory_note')}")
        return 1
    keys = [e["id"] for e in mt.ENTITIES]
    bad = 0
    t = 100.0
    for k, line in enumerate(lines):
        t += 10.0
        step = {"gaze": keys[k % len(keys)]} if k % 3 == 0 else {}
        q = {"cmd": "text", "text": line, "world": mt.world(t, step)}
        ra, rb = a.send(q), b.send(q)
        d = diff(strip(ra), strip(rb))
        if d:
            bad += 1
            if bad <= 15:
                print(f"  DIFF {line!r}: " + "; ".join(d[:4]))
    a.close()
    b.close()
    print(f"{lang}{' (chain)' if chain else ''}: {len(lines)} lines ({len(taken)} teaching lines left out), {bad} differ")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=os.path.join(mt.REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe"))
    ap.add_argument("--bot", default=os.path.join(mt.GAME_BRAIN, "bot"))
    ap.add_argument("--chain", nargs="?", const=os.path.join(mt.GAME_BRAIN, "chain"), default=None,
                    help="also Russian and Spanish through the chain (the decoder on the CPU)")
    ap.add_argument("--limit", type=int, default=0, help="at most this many lines a language (0: all)")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    folder = tempfile.mkdtemp(prefix="coop_memory_inv_")
    bad = run(args, "en", False, folder)
    if args.chain:
        for lang in ("ru", "es"):
            bad += run(args, lang, True, folder)
    import shutil
    shutil.rmtree(folder, ignore_errors=True)
    print("memory invariance:", "no difference" if not bad else f"{bad} lines differ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
