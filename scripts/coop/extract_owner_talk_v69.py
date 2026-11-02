"""The owner's spoken lines (every language) from the game logs of 2026-10-31 13:00 .. 2026-11-01 23:32 (log time, the test
range: lying down, the wall hop, doors, stairs, boxes), with what the bot made of them, for the next decoder round:
owner_talk_v69_candidates.json. The game keeps only its last 10 logs (BaseEngine.ini [LogFiles] MaxLogFilesOnDisk=10,
PurgeLogsDays=5), so this file is the record once they are gone.

Per line: the log time, the text as Parakeet heard it, the decoder's English order lines where the client logged them
("client: order line N"), the brain's result, the bot's replies in the player's language until the next line, the log.
Lines said to someone in the room (not to the bot) are left out (ROOM). The misreads, what was wanted and what the
2026-11-02 brain does with each: stt/chains2/ml_v68/TODO_v68.md, section 5.

    python extract_owner_talk_v69.py"""
import glob, io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = r"J:\UE4\Projects\LyraStarterGame58\Saved\Logs"
FROM, TO = "2026.10.31-13.00", "2026.11.02-12.00"
STAMP = re.compile(r"^\[(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d):\d+\]")
HEARD = re.compile(r"client: heard \"(.*?)\" -> (.*?) \[speech (\d+) ms")
LINE = re.compile(r"client: order line \d+ \"(.*?)\" at ")
SAID_AS = re.compile(r"client: \S+ said \".*?\" as \"(.*?)\"")
REPLY = re.compile(r"client: (?:Buddy|Бади|Тимур|Michael|Нео|Эмти|Лох|Bra|[A-ZА-Я][a-zа-я]+): ([А-Яа-яЁё].*)$")
# said to someone in the room, not to the bot (2026-11-01 evening, the open microphone)
ROOM = {"2026.11.01-19.57.28", "2026.11.01-19.57.31", "2026.11.01-19.57.43", "2026.11.01-19.57.44", "2026.11.01-19.57.56",
        "2026.11.01-21.57.25"}

items, seen = [], set()
for path in sorted(glob.glob(os.path.join(LOGS, "LyraStarterGame*.log")), key=os.path.getmtime):
    pending, cur = [], None
    for raw in io.open(path, encoding="utf-8", errors="replace"):
        if "LogOVCoopBot" not in raw:
            continue
        m = STAMP.match(raw)
        stamp = m.group(1) if m else ""
        body = raw.split("LogOVCoopBot: ", 1)[-1].rstrip()
        m = LINE.search(body)
        if m:
            pending.append(m.group(1))
            continue
        m = HEARD.search(body)
        if m:
            text, result, speech = m.groups()
            cur = None
            if FROM <= stamp < TO and int(speech) > 0 and (stamp, text) not in seen:
                seen.add((stamp, text))
                if not (stamp in ROOM and len(text.split()) > 1) or text == "Вот привет.":
                    cur = {"time": stamp, "text": text, "decoder": pending, "brain": result, "bot": [], "log": os.path.basename(path)}
                    items.append(cur)
            pending = []
            continue
        if cur is None:
            continue
        m = SAID_AS.search(body) or REPLY.search(body)
        if m and m.group(1) not in cur["bot"]:
            cur["bot"].append(m.group(1))
items.sort(key=lambda r: r["time"])
for i, r in enumerate(items):
    r["id"] = "talk69_%04d" % (i + 1)
note = ("The owner's spoken lines in the game, " + FROM + " .. " + TO + " (log time; the test range), " +
        "made by extract_owner_talk_v69.py; the room talk on the open microphone left out. decoder: the English order lines "
        "where the client logged them; brain: the result; bot: its replies in the player's language.")
json.dump({"_note": note, "items": [dict(id=r.pop("id"), **r) for r in items]},
          io.open(os.path.join(HERE, "owner_talk_v69_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(items), "spoken lines", FROM, "..", TO)
