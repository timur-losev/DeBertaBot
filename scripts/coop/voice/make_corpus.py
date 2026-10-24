"""The Russian lines a bot voice is trained on: the bot's own lines (the plain and the persona reply tables, every
template filled with a few slot values) and ordinary sentences from the Common Voice ru sentence collection (CC0), for
the sounds the bot's lines do not have.

    python make_corpus.py --persona brat --common-voice work/cv_ru_sentences.txt --out work/brat/corpus.txt

One line per sentence: id|text. Seeded: the same inputs give the same file."""
import argparse
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPLIES = HERE.parent / "replies"
SLOT = re.compile(r"\{([A-Za-z_]+)(?:\.([a-z_]+))?(?::([^}]*))?\}")
CYRILLIC_ONLY = re.compile(r"^[А-Яа-яЁё0-9 ,.!?;:—–\-«»\"'()]+$")


def plural(n, forms):
    one, few, many = forms.split("|")
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def fill(template, slots, rng):
    """One reading of a template: a random value for each slot, the number words agreeing with {n}."""
    chosen = {}
    n = rng.choice([1, 2, 3, 4, 5, 7, 12, 15, 21, 23, 30, 45])

    def value(match):
        name, form, forms = match.group(1), match.group(2), match.group(3)
        if name == "n":
            return plural(n, forms) if forms else str(n)
        key = name.lower()
        table = slots.get(key)
        if not table:
            return None
        if key not in chosen:
            chosen[key] = rng.choice([v for k, v in table.items() if k != "_other"] or list(table.values()))
        text = chosen[key].get(form or "text") or chosen[key].get("text", "")
        return text[:1].upper() + text[1:] if name[0].isupper() else text

    out = []
    pos = 0
    for match in SLOT.finditer(template):
        got = value(match)
        if got is None:
            return None
        out.append(template[pos:match.start()])
        out.append(got)
        pos = match.end()
    out.append(template[pos:])
    text = "".join(out).strip()
    return text[:1].upper() + text[1:] if text else None


def bot_lines(table_path, rng, fills):
    table = json.loads(table_path.read_text(encoding="utf-8"))
    slots = {k.lower(): v for k, v in table.get("slots", {}).items()}
    lines = []
    for template in table["sentences"].values():
        if "{" not in template:
            lines.append(template)
            continue
        for _ in range(fills):
            text = fill(template, slots, rng)
            if text and "{" not in text:
                lines.append(text)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="brat")
    ap.add_argument("--common-voice", required=True)
    ap.add_argument("--common-voice-count", type=int, default=1800)
    ap.add_argument("--fills", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261024)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    lines = bot_lines(REPLIES / f"replies_ru_{args.persona}.json", rng, args.fills)
    lines += bot_lines(REPLIES / "replies_ru.json", rng, 1)
    seen, bot = set(), []
    for line in lines:
        if line not in seen:
            seen.add(line)
            bot.append(line)

    common = []
    for line in Path(args.common_voice).read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("-– ").strip()
        if 25 <= len(line) <= 130 and CYRILLIC_ONLY.match(line) and line not in seen:
            seen.add(line)
            common.append(line)
    rng.shuffle(common)
    common = common[: args.common_voice_count]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for i, line in enumerate(bot):
            f.write(f"bot_{i:04d}|{line}\n")
        for i, line in enumerate(common):
            f.write(f"cv_{i:04d}|{line}\n")
    print(f"{len(bot)} bot lines, {len(common)} Common Voice sentences -> {out}")


if __name__ == "__main__":
    main()
