"""What the v57 ensemble (the calculator of chains4_v58.py) reads in some lines: python probe_v57.py "line" "line" ... (or a file
with one line a row via @file). Prints the pick and its probability for each."""
import io, sys
import chains4_v58 as X          # COOP_TAG=v57, the v57 calculator

lines = []
for a in sys.argv[1:]:
    if a.startswith("@"):
        lines += [l.strip() for l in io.open(a[1:], encoding="utf-8") if l.strip()]
    else:
        lines.append(a)
picks, cfg = X.C.bot_picks([{"id": str(n), "text": t} for n, t in enumerate(lines)])
for n, t in enumerate(lines):
    p = picks[str(n)]
    print(f"{str(p[0]):16s} {str(p[1:])[:40]:<42} {t}")
