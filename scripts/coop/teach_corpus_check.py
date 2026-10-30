"""False teaching lines: the rules of teach.h (coop_cli --teach-tests) on every order line the repository holds, and
the colour question ("what colour is it?", 2026-10-30), read by rule on every line as well.

A teaching line ("no, I meant ...", "not that", «назови это ...», "forget ...") is found by rule before any model reads
the line, so a rule that takes an ordinary order for one costs the player that order. This check reads thousands of
real and test lines in English, Russian and Spanish -- the owner's heard lines, the held-out tests of rounds v64..v68,
the decoder's blind lines and its v62 translations -- and expects none of them to be a teaching line, except the ones
listed in EXPECT below, each looked at by hand.

    python teach_corpus_check.py [--exe coop_cli.exe] [--show N]

Prints the counts per source and language, every line read otherwise than expected, and exits 1 on any.
Build-time tooling.
"""
import argparse, glob, io, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
CH = os.path.join(HERE, "stt", "chains2")

# lines of the corpus that ARE teaching lines (or read so on purpose), by their text as written: kind, and why
PLACE = "a new place for the order before (context lines): the brain reads the meaning and keeps nothing, the same order"
NEG = "a meaning that cancels itself: the brain reads it and keeps nothing (not understood)"
ANSWER = "an answer to the bot's question in its context; with no question open the bot asks what was meant"
EXPECT = {
    "i said kitchen": ("meant", PLACE),
    "I meant the window.": ("meant", PLACE),
    "dije cocina": ("meant", PLACE),
    "Quería decir la ventana.": ("meant", PLACE),
    "te dije la cocina": ("meant", PLACE),
    "dije sur, no norte": ("meant", PLACE),
    "я сказал к южному, не к северному": ("meant", PLACE),
    "я сказал на кухню": ("meant", PLACE),
    "Я имел в виду окно.": ("meant", PLACE),
    "я сказал кухню": ("meant", PLACE),
    "Я сказал, держи жёлтую лестницу.": ("meant", "a meaning said again: kept only when the line before was misread"),
    "я сказал южную, не северную": ("meant", PLACE),
    "i said open fire but no dont fire dont fire": ("meant", NEG),
    "dije abre fuego pero no, no dispares, no dispares": ("meant", NEG),
    "я сказал огонь, но нет, не стреляй, не стреляй": ("meant", NEG),
    "that's wrong": ("not_that", ANSWER),
    "not that": ("not_that", ANSWER),
    "eso no": ("not_that", ANSWER),
    "не то": ("not_that", ANSWER),
    "forget the smoke": ("forget", "a candidate: forgets only a name or a line kept as 'smoke', else a line like any other"),
}

# lines of the corpus that ARE questions about a colour (ColourQuestion), each looked at by hand
COLOUR_QUESTIONS = set()


def load(path):
    return json.load(io.open(path, encoding="utf-8"))


def rows(d):
    """The records of a file: a list, or a dict's "items" / "rows" / "lines"; strings are lines of their own."""
    if isinstance(d, dict):
        d = d.get("items") or d.get("rows") or d.get("lines") or []
    return [x if isinstance(x, dict) else {"text": x, "en": x} for x in d]


def corpus():
    """(source, lang, line) for every line, each (lang, line) once."""
    out, seen = [], set()

    def add(src, lang, text):
        if not isinstance(text, str) or not text.strip():
            return
        key = (lang, text)
        if key in seen:
            return
        seen.add(key)
        out.append((src, lang, text))

    for name in ("owner_lines_v61.json", "owner_lines_v64.json", "owner_lines_v65.json", "owner_lines_v66.json"):
        for it in load(os.path.join(HERE, name))["items"]:
            add(name, "en", it["text"])
    for it in load(os.path.join(HERE, "dev.json"))["cases"]:
        add("dev.json", "en", it["text"])
    for name in ("blind_lines.json", "held_lines.json", "ctx_blind_lines.json"):
        p = os.path.join(CH, name)
        if os.path.exists(p):
            d = load(p)
            for it in rows(d):
                add(name, "en", it.get("text"))
    for p in sorted(glob.glob(os.path.join(CH, "ml_v62", "in", "*.json"))):
        for it in rows(load(p)):
            add("ml_v62/in", "en", it.get("en"))
            for b in it.get("before", []):
                add("ml_v62/in", "en", b)
    for p in sorted(glob.glob(os.path.join(CH, "ml_v62", "out", "*.json"))):
        lang = os.path.basename(p)[:2]
        for it in rows(load(p)):
            add("ml_v62/out", lang, it.get("text"))
            for b in it.get("before", []):
                add("ml_v62/out", lang, b)
    pairs = load(os.path.join(CH, "ml_v62", "pairs_test.json"))
    for lang, recs in pairs.items():
        for it in recs:
            add("pairs_test", lang, it["text"])
    t64 = load(os.path.join(CH, "ml_v64", "test_v64.json"))
    for lang, recs in t64.items():
        for it in recs:
            add("test_v64", lang, it["text"])
    for rel in ("ml_v66/test_v66.json", "ml_v67/test_v67.json", "ml_v68/test_v68_things.json", "ml_v68/test_v68_time.json"):
        for it in load(os.path.join(CH, rel))["items"]:
            lang = it.get("lang", "en")
            add(rel, lang, it.get("line", it.get("text")))
            for b in it.get("before", []):
                add(rel, lang, b)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=os.path.join(REPO, "cpp", "coop_intent", "build", "Release", "coop_cli.exe"))
    ap.add_argument("--show", type=int, default=200)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    lines = corpus()
    cases = [{"line": t, "lang": lang, "kind": EXPECT.get(t, ("none", ""))[0]} for _, lang, t in lines]
    # "what colour is it?" is read by rule on every line too (2026-10-30): no order line is one
    cases += [{"colour_question": t, "expect": t in COLOUR_QUESTIONS} for _, lang, t in lines]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False)
        path = f.name
    try:
        p = subprocess.run([args.exe, "--teach-tests", path], capture_output=True, encoding="utf-8")
    finally:
        os.unlink(path)
    by = {}
    for src, lang, _ in lines:
        by.setdefault((src, lang), 0)
        by[(src, lang)] += 1
    print(f"teaching rules on {len(lines)} lines: " + ", ".join(f"{s} {l} {n}" for (s, l), n in sorted(by.items())))
    shown = [l for l in p.stdout.splitlines() if l.startswith("  ")]   # each case read otherwise, and what it got
    for l in shown[: 2 * args.show]:
        print(l)
    missing = [t for t in EXPECT if t not in {x[2] for x in lines}]
    for t in missing:
        print(f"  EXPECT names a line the corpus no longer has: {t!r}")
    print(p.stdout.splitlines()[-1] if p.stdout else p.stderr)
    return 1 if p.returncode or missing else 0


if __name__ == "__main__":
    sys.exit(main())
