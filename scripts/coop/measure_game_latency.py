"""In-game latency of the owner's spoken lines from the game's logs (Saved/Logs/LyraStarterGame*.log, the client's "latency:" lines):
from the end of the speech to the bot's voice or order, and the brain's parts, by the decoder the game had when the brain
started (version() below: deploy times in the logs' clock, UTC). README.md, "Measured results".

    python measure_game_latency.py

Prints numbers only; the lines themselves (the owner's words) stay in the logs.
"""
import glob, io, json, re, sys
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
LOGS = sorted(glob.glob(r"J:\UE4\Projects\LyraStarterGame58\Saved\Logs\LyraStarterGame*.log"))
TS = re.compile(r"^\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):")
def when(line):
    m = TS.match(line)
    return datetime(*map(int, m.groups())) if m else None
def version(t):   # the decoders deployed, UTC: v69s2 07:18-08:05, v69s3 13:15, v69s5 20:50 on 2026-11-04
    if t < datetime(2026, 11, 4, 7, 18): return "v68s2"
    if t < datetime(2026, 11, 4, 8, 5): return "v69s2"
    if t < datetime(2026, 11, 4, 13, 15): return "v68s2"
    if t < datetime(2026, 11, 4, 20, 50): return "v69s3"
    return "v69s5"
LAT = re.compile(r'client: latency: "(.*)" -> "(.*)": (\d+) ms from the (end of the clip|end of the line|typed line)[^=]*= the reply (\d+) ms \(([^)]*)\)(?: \+ its voice (\d+))?')
rows = []
for path in LOGS:
    start = None; lang = "en"
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if "LogOVCoopBot: brain: started" in line:
            start = when(line); lang = "en"
        m = re.search(r"brain: language:? (\w\w)\b", line)
        if m: lang = m.group(1)
        m = LAT.search(line)
        if not m or start is None: continue
        parts = dict((k.strip(), float(v)) for v, k in [(p.split()[-1], " ".join(p.split()[:-1])) for p in m.group(6).split(",") if p.strip() and p.split()[-1].replace(".", "").isdigit()])
        rows.append({"v": version(start), "lang": lang, "src": m.group(4), "total": float(m.group(3)), "reply": float(m.group(5)),
                     "speech": parts.get("speech"), "intent": parts.get("intent"), "router": parts.get("router"), "lm": parts.get("language model"),
                     "voice": float(m.group(7)) if m.group(7) else None, "text": m.group(1)})
def pct(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * q
    f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
def line(name, xs):
    xs = [x for x in xs if x is not None]
    if not xs: return f"  {name:28} n=0"
    return f"  {name:28} n={len(xs):4}  P50 {pct(xs,.5):6.0f}  P95 {pct(xs,.95):6.0f}  P99 {pct(xs,.99):6.0f}  max {max(xs):6.0f}"
voice = [r for r in rows if r["src"] != "typed line"]
out = {}
for v in ("v68s2", "v69s3", "v69s5"):
    for lang in ("all", "ru", "en"):
        rs = [r for r in voice if r["v"] == v and (lang == "all" or r["lang"] == lang)]
        if not rs: continue
        print(f"{v} {lang}: {len(rs)} spoken lines")
        print(line("end to end (to voice/order)", [r["total"] for r in rs]))
        print(line("brain reply", [r["reply"] for r in rs]))
        print(line("speech to text", [r["speech"] for r in rs]))
        print(line("classifier", [r["intent"] for r in rs]))
        print(line("router", [r["router"] for r in rs]))
        print(line("decoder (lines it read)", [r["lm"] for r in rs]))
        print(f"  share of lines through the decoder: {100*sum(r['lm'] is not None for r in rs)/len(rs):.0f}%")
print("typed lines left out:", len(rows) - len(voice), "| v69s2 lines:", sum(r["v"] == "v69s2" for r in voice))
