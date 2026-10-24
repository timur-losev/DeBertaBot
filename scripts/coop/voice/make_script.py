"""The lines the owner reads for his own bot voice, in the order that pays off soonest: the bot's lines (each
template of the persona table once, slots filled) alternating with short ordinary sentences picked for the Russian
sounds the bot's lines miss (greedy over phoneme pairs, espeak through Piper's phonemizer). Stopping anywhere leaves
a balanced set. Run with the Piper training Python (venv_piper):

    python make_script.py --out work/owner_rec/lines.json"""
import argparse
import json
import random
import re
from pathlib import Path

from piper.phonemize_espeak import EspeakPhonemizer

from make_corpus import REPLIES, CYRILLIC_ONLY, fill

HERE = Path(__file__).resolve().parent


def pairs(phonemizer, text):
    out = set()
    for sentence in phonemizer.phonemize("ru", text):
        ph = [p for p in sentence if p not in "ˈˌ"]
        out.update(zip(ph, ph[1:]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="brat")
    ap.add_argument("--common-voice", default=str(HERE / "work" / "cv_ru_sentences.txt"))
    ap.add_argument("--extra", type=int, default=400)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261024)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    ph = EspeakPhonemizer()

    table = json.loads((REPLIES / f"replies_ru_{args.persona}.json").read_text(encoding="utf-8"))
    slots = {k.lower(): v for k, v in table.get("slots", {}).items()}
    bot, seen = [], set()
    for template in table["sentences"].values():
        text = fill(template, slots, rng) if "{" in template else template
        if text and "{" not in text and text not in seen:
            seen.add(text)
            bot.append(text)

    covered = set()
    for text in bot:
        covered |= pairs(ph, text)

    pool = []
    for line in Path(args.common_voice).read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("-– ").strip()
        if (20 <= len(line) <= 80 and CYRILLIC_ONLY.match(line) and line not in seen and not re.search(r"\d", line)
                and not re.search(r"[А-ЯЁ]{2,}", line)):   # no numbers or abbreviations: they are read many ways
            seen.add(line)
            pool.append(line)
    rng.shuffle(pool)
    pool = pool[:6000]
    cached = {t: pairs(ph, t) for t in pool}
    extra = []
    while len(extra) < args.extra and cached:
        # new sounds per length, so short spoken sentences win over long official ones
        best = max(cached, key=lambda t: len(cached[t] - covered) / len(t) ** 0.8)
        if not cached[best] - covered:   # every pair is in: the rest by length, short ones first
            rest = sorted(cached, key=len)[: args.extra - len(extra)]
            extra += rest
            break
        covered |= cached.pop(best)
        extra.append(best)

    lines = []
    b = e = 0
    while b < len(bot) or e < len(extra):
        if b < len(bot):
            lines.append({"id": f"bot_{b:04d}", "text": bot[b], "kind": "bot"})
            b += 1
        if e < len(extra):
            lines.append({"id": f"gen_{e:04d}", "text": extra[e], "kind": "general"})
            e += 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"persona": args.persona, "lines": lines}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(bot)} bot lines + {len(extra)} sentences = {len(lines)} -> {out}; {len(covered)} phoneme pairs covered")


if __name__ == "__main__":
    main()
