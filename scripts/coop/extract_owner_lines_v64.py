"""The owner's spoken English lines since owner_lines_v61.json (game logs of 2026-10-22..25, LyraStarterGame58/Saved/Logs),
with what the bot made of them and what was said around them, for labelling: owner_lines_v64_candidates.json. Only lines
heard by the speech key (not typed, not the E2E scripts), in English (the Russian and Spanish lines go through the decoder:
they are the decoder's data, not the classifier's).

    python extract_owner_lines_v64.py"""
import glob, io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = r"J:\UE4\Projects\LyraStarterGame58\Saved\Logs"
HEARD = re.compile(r"\[(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d):\d+\].*client: heard \"(.*?)\" -> (.*?) \[speech (\d+) ms")
SAID = re.compile(r"client: latency: \"(.*?)\" -> \"(.*?)\": ")
old = {o["text"] for o in json.load(io.open(os.path.join(HERE, "owner_lines_v61.json"), encoding="utf-8"))["items"]}
rows = []
for path in sorted(glob.glob(os.path.join(LOGS, "*.log"))):
    lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    for n, line in enumerate(lines):
        m = HEARD.search(line)
        if not m:
            continue
        stamp, heard, read, speech_ms = m.groups()
        if stamp < "2026.10.22" or int(speech_ms) == 0 or re.search(r"[А-Яа-яЁёñáéíóú¿¡]", heard):
            continue   # older than the v61 set, typed (no speech), or not English
        bot = ""
        for k in range(n + 1, min(n + 40, len(lines))):
            s = SAID.search(lines[k])
            if s and s.group(1) == heard:
                bot = s.group(2)
                break
        rows.append({"time": stamp, "text": heard, "brain": read, "bot": bot, "log": os.path.basename(path)})
seen, out = set(), []
for r in sorted(rows, key=lambda r: r["time"]):
    key = (r["time"], r["text"])
    if key not in seen:
        seen.add(key)
        r["in_v61"] = r["text"].strip().rstrip(".!?").lower() in old
        out.append(r)
json.dump(out, io.open(os.path.join(HERE, "owner_lines_v64_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "spoken English lines since 2026-10-22")
