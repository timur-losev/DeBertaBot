"""The Piper training set from a rendered corpus: the lines Parakeet heard right enough (score_wavs.py corpus), at a
sane speed, as metadata.csv (wav|text) next to the wavs. A heavy model now and then drops or repeats words, or
babbles past the end; such a line would teach the voice to do the same.

    python make_dataset.py <scores.jsonl> <wav dir> <out metadata.csv>"""
import json
import sys


def keep(row):
    words, errors, secs = row["words"], row["errors"], row["seconds"]
    chars = len(row["text"])
    if secs < 0.4 or secs > 15:
        return False
    per_char = secs / max(chars, 1)
    if not 0.035 <= per_char <= 0.16:   # too fast: words dropped; too slow: long pauses or babble
        return False
    if words <= 2:
        return errors == 0 or (words == 2 and errors <= 1 and chars >= 10)
    return errors / words <= 0.25


def main():
    scores, wav_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = [json.loads(line) for line in open(scores, encoding="utf-8")]
    kept = [r for r in rows if keep(r)]
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for r in kept:
            f.write(f"{r['id']}.wav|{r['text']}\n")
    hours = sum(r["seconds"] for r in kept) / 3600
    bot = sum(1 for r in kept if r["id"].startswith("bot_"))
    print(f"kept {len(kept)} of {len(rows)} lines ({bot} of the bot's), {hours:.2f} h -> {out}")


if __name__ == "__main__":
    main()
