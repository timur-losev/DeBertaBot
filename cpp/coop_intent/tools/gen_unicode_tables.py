"""
Generates ../src/unicode_tables.inc: every Unicode fact the C++ tokenizer and regex slots need, so
the engine carries no ICU / Windows NLS dependency and behaves the same on every platform (UE too).

The tables are taken from the libraries the Python bot actually runs, not from a Unicode version:
  kOnigSpace       what the normalizer's regex \s matches (HF tokenizers, Oniguruma), probed per
                   code point through normalizers.Replace
  kRustWhitespace  what Strip(right) removes (Rust char::is_whitespace), probed through normalizers.Strip
  kDecomp          the full canonical decomposition of each code point, from tokenizers' own NFD
  kCcc, kCompose   canonical combining classes and primary composites: unicodedata's, kept only
                   where tokenizers agrees, then checked against tokenizers' NFC on every single code
                   point and on 200k random mark sequences
tokenizers normalizes with an older Unicode table than Python 3.11's unicodedata (14.0): it does not
decompose U+11938 (Unicode 13) and gives U+07FD (Unicode 11) class 0. The model was trained on what
tokenizers produced, so its tables win.
  kPyWord          what Python's re \w matches (the bot's regexes are Python re patterns)
  kPyFold          non-ASCII code points that re.IGNORECASE matches to an ASCII letter (U+017F -> s, ...)
  kPySpace         what Python's str.isspace() accepts (coop_bot.py strips every typed line with it)

    python gen_unicode_tables.py      # jev environment (tokenizers); takes ~30 s
"""
import os, random, re, unicodedata

from tokenizers import Regex, normalizers

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "src", "unicode_tables.inc"))
CPS = [c for c in range(0x110000) if not 0xD800 <= c <= 0xDFFF]
HANGUL = range(0xAC00, 0xD7A4)


def ranges(pred):
    out, start = [], None
    for c in range(0x110001):
        on = c < 0x110000 and not 0xD800 <= c <= 0xDFFF and pred(c)
        if on and start is None:
            start = c
        elif not on and start is not None:
            out.append((start, c - 1))
            start = None
    return out


def main():
    replace = normalizers.Replace(Regex(r"\s{2,}"), " ")
    strip = normalizers.Strip(left=False, right=True)
    nfd, nfc = normalizers.NFD(), normalizers.NFC()
    word = re.compile(r"\w")

    onig_space = ranges(lambda c: replace.normalize_str(chr(c) * 2) == " ")
    rust_ws = ranges(lambda c: strip.normalize_str("a" + chr(c)) == "a")
    py_word = ranges(lambda c: word.match(chr(c)) is not None)
    py_space = ranges(lambda c: chr(c).isspace())   # what str.strip() removes (the bot strips each line)
    fold = []
    for c in CPS:
        if c >= 0x80 and re.fullmatch("[a-z]", chr(c), re.I):
            fold.append((c, next(l for l in "abcdefghijklmnopqrstuvwxyz" if re.fullmatch(l, chr(c), re.I))))

    decomp = {}
    for c in CPS:
        if c in HANGUL:
            continue
        d = nfd.normalize_str(chr(c))
        if d != chr(c):
            decomp[c] = [ord(x) for x in d]
    # a mark tokenizers knows moves in front of U+0345 (class 240, the highest) when NFD reorders;
    # one it does not know has class 0 there and stays put (classes never change once assigned)
    knows = lambda c: c == 0x345 or nfd.normalize_str("a\u0345" + chr(c)) != "a\u0345" + nfd.normalize_str(chr(c))
    ccc = {c: unicodedata.combining(chr(c)) for c in CPS if unicodedata.combining(chr(c)) and knows(c)}
    ccc_ranges = []
    for c in sorted(ccc):
        if ccc_ranges and ccc_ranges[-1][1] == c - 1 and ccc_ranges[-1][2] == ccc[c]:
            ccc_ranges[-1][1] = c
        else:
            ccc_ranges.append([c, c, ccc[c]])
    pairs = []
    for c in CPS:
        if c in HANGUL:
            continue
        d = unicodedata.decomposition(chr(c))
        if d and not d.startswith("<"):
            parts = [int(x, 16) for x in d.split()]
            if len(parts) == 2 and nfc.normalize_str(chr(c)) == chr(c) and nfc.normalize_str(chr(parts[0]) + chr(parts[1])) == chr(c):
                pairs.append((parts[0], parts[1], c))
    pairs.sort()

    # ---- check the tables with a Python copy of the C++ algorithm against tokenizers' NFC
    get_ccc = lambda c: ccc.get(c, 0)
    comp = {(a, b): c for a, b, c in pairs}

    def compose(a, b):
        if 0x1100 <= a < 0x1113 and 0x1161 <= b < 0x1176:
            return 0xAC00 + ((a - 0x1100) * 21 + (b - 0x1161)) * 28
        if 0xAC00 <= a < 0xD7A4 and (a - 0xAC00) % 28 == 0 and 0x11A7 < b < 0x11C3:
            return a + (b - 0x11A7)
        return comp.get((a, b))

    def my_nfc(s):
        d = []
        for ch in map(ord, s):
            if ch in HANGUL:
                i = ch - 0xAC00
                d += [0x1100 + i // 588, 0x1161 + i % 588 // 28] + ([0x11A7 + i % 28] if i % 28 else [])
            else:
                d += decomp.get(ch, [ch])
        for i in range(1, len(d)):           # canonical ordering: insertion sort of marks by ccc
            j = i
            while j > 0 and get_ccc(d[j]) and get_ccc(d[j - 1]) > get_ccc(d[j]):
                d[j - 1], d[j] = d[j], d[j - 1]
                j -= 1
        out, starter = [], None
        for ch in d:
            k = get_ccc(ch)
            if starter is not None:
                blocked = len(out) - 1 > starter and (get_ccc(out[-1]) == 0 or get_ccc(out[-1]) >= k)
                if not blocked:
                    x = compose(out[starter], ch)
                    if x is not None:
                        out[starter] = x
                        continue
            if k == 0:
                starter = len(out)
            out.append(ch)
        return "".join(map(chr, out))

    rng = random.Random(0)
    marks = sorted(c for c in CPS if unicodedata.combining(chr(c)))   # Python's marks: includes the ones tokenizers does not know
    tests = [chr(c) for c in CPS]
    tests += ["a" + chr(m) + chr(x) for m in marks for x in (0x0334, 0x05B0, 0x0316, 0x0301, 0x0345, 0x093C, 0x094D)]
    bases = [c for c in CPS if c < 0x3000 and unicodedata.category(chr(c))[0] == "L"] + list(range(0x1100, 0x1200)) + list(HANGUL)[:500]
    for _ in range(200000):
        tests.append("".join(chr(rng.choice(bases) if rng.random() < 0.4 else rng.choice(marks)) for _ in range(rng.randint(1, 6))))
    bad = [t for t in tests if my_nfc(t) != nfc.normalize_str(t)]
    assert not bad, f"{len(bad)} NFC mismatches, e.g. {[[hex(ord(x)) for x in t] for t in bad[:5]]}"
    print(f"NFC tables reproduce tokenizers on {len(tests)} strings")

    # ---- write
    data, index = [], []
    for c in sorted(decomp):
        index.append((c, len(data), len(decomp[c])))
        data += decomp[c]

    def rows(items, per):
        return "\n".join("    " + " ".join(items[i:i + per]) for i in range(0, len(items), per))

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("// Generated by tools/gen_unicode_tables.py -- do not edit.\n"
                f"// tokenizers normalizers + Python {unicodedata.unidata_version} unicodedata / re; see the script.\n\n")
        for name, rs in (("kOnigSpace", onig_space), ("kRustWhitespace", rust_ws), ("kPyWord", py_word),
                         ("kPySpace", py_space)):
            f.write(f"static const CpRange {name}[] = {{\n{rows([f'{{0x{a:X},0x{b:X}}},' for a, b in rs], 8)}\n}};\n\n")
        f.write(f"static const CpFold kPyFold[] = {{\n{rows([f'{{0x{c:X},{l!r}}},' for c, l in fold], 8)}\n}};\n\n")
        f.write(f"static const CccRange kCcc[] = {{\n{rows([f'{{0x{a:X},0x{b:X},{k}}},' for a, b, k in ccc_ranges], 6)}\n}};\n\n")
        f.write(f"static const char32_t kDecompData[] = {{\n{rows([f'0x{x:X},' for x in data], 12)}\n}};\n\n")
        f.write(f"static const DecompEntry kDecomp[] = {{\n{rows([f'{{0x{c:X},{o},{n}}},' for c, o, n in index], 6)}\n}};\n\n")
        f.write(f"static const ComposePair kCompose[] = {{\n{rows([f'{{0x{a:X},0x{b:X},0x{c:X}}},' for a, b, c in pairs], 5)}\n}};\n")
    print(f"wrote {OUT}: space {len(onig_space)} ranges, whitespace {len(rust_ws)}, word {len(py_word)}, fold {fold}, "
          f"ccc {len(ccc_ranges)} ranges, decompositions {len(index)}, compositions {len(pairs)}")


if __name__ == "__main__":
    main()
