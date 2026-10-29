"""Checks the frame files of round v67 against FRAMES.md: python check_frames.py [frames/X.json ...] (default: all)."""
import glob, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INTENTS = json.load(io.open(os.path.join(HERE, "..", "..", "..", "intents_v66.json"), encoding="utf-8"))
LABELS = [k for k in INTENTS if not k.startswith("_")]
SLOTS = {"en": {"T"}, "canon": {"T"}, "ru": {"T:nom", "T:acc", "T:gen", "T:dat", "T:ins", "T:prep"},
         "ru_inf": {"T:nom", "T:acc", "T:gen", "T:dat", "T:ins", "T:prep"}, "es": {"T", "T:a", "T:de"}, "es_inf": {"T", "T:a", "T:de"}}
SLOT = re.compile(r"\{([^{}]*)\}")


def check(path):
    bad = []
    data = json.load(io.open(path, encoding="utf-8"))
    for intent, f in data.items():
        where = f"{os.path.basename(path)} {intent}"
        if intent not in LABELS:
            bad.append(f"{where}: not an intent")
            continue
        if f.get("target") not in ("required", "optional", "none"):
            bad.append(f"{where}: target is {f.get('target')!r}")
            continue
        canon = f.get("canon") or []
        if not canon:
            bad.append(f"{where}: no canon")
        for key in ("canon", "en", "ru", "es", "ru_inf", "es_inf"):
            rows = f.get(key) or []
            if key in ("ru_inf", "es_inf") and len(rows) != len(canon):
                bad.append(f"{where}: {key} has {len(rows)} entries for {len(canon)} canon")
            if key in ("en", "ru", "es") and not rows:
                bad.append(f"{where}: no {key}")
            for row in rows:
                if key in ("en", "ru", "es"):
                    if not (isinstance(row, list) and len(row) == 2 and isinstance(row[0], str) and isinstance(row[1], int)):
                        bad.append(f"{where}: {key} row {row!r} is not [text, index]")
                        continue
                    text, k = row
                    if not 0 <= k < len(canon):
                        bad.append(f"{where}: {key} {text!r} points at canon {k}")
                        continue
                    want = "{T}" in canon[k]
                else:
                    text, want = row, None
                slots = SLOT.findall(text)
                for s in slots:
                    if s not in SLOTS[key]:
                        bad.append(f"{where}: {key} {text!r} has slot {{{s}}}")
                if f["target"] == "required" and not slots:
                    bad.append(f"{where}: {key} {text!r} has no target slot (target required)")
                if f["target"] == "none" and slots:
                    bad.append(f"{where}: {key} {text!r} has a slot (target none)")
                if want is not None and bool(slots) != want:
                    bad.append(f"{where}: {key} {text!r} and its canon {canon[k]!r} disagree on the target")
                if text != text.strip() or "  " in text:
                    bad.append(f"{where}: {key} {text!r} has extra spaces")
    return data, bad


def main():
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, "frames", "*.json")))
    seen, total = {}, 0
    for p in paths:
        data, bad = check(p)
        for intent in data:
            if intent in seen:
                print(f"{intent}: in {seen[intent]} and {os.path.basename(p)}")
            seen[intent] = os.path.basename(p)
        for b in bad:
            print(b)
        total += len(bad)
        n = {k: sum(len(f.get(k) or []) for f in data.values()) for k in ("canon", "en", "ru", "es")}
        print(f"{os.path.basename(p)}: {len(data)} intents, {n}, {len(bad)} problem(s)")
    missing = [k for k in LABELS if k not in seen and k != "NONE"]
    if len(paths) > 1 or not sys.argv[1:]:
        print(f"intents with no frames: {missing}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
