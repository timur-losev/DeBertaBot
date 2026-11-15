"""Round talk-2 (2026-11-13): the training rows of the round, put together in one folder (talk_train.py's TALK_ROWS).

The rows of round talk-1 (rows/*.jsonl) and the new ones (rows2/w*.jsonl), with the checkers' changes applied (rows2/fix_*.jsonl:
{"file", "line" (1-based), "where": "answer" | "before.N", "old", "new", "why"} or {"file", "line", "drop": true, "why"}). A change
whose "old" is not the text at its place is refused and reported, and the row stays as it was.

    python apply_fixes.py OUT_DIR    -> OUT_DIR/<the same file names>, and the counts
"""
import collections, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# a person's gender where a row has none (round talk-1's invented people): the brain tells the model the forms a person uses of
# themselves in Russian and Spanish ("gender" of the game's role request), so their rows are trained with it too
WOMEN = {"teller_anna", "granny", "pharmacist", "soda_bartender"}


def main(out_dir):
    sources = {os.path.basename(p): p for p in sorted(glob.glob(os.path.join(HERE, "rows", "*.jsonl")))}
    sources.update({os.path.basename(p): p for p in sorted(glob.glob(os.path.join(HERE, "rows2", "w*.jsonl")))})
    fixes = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(HERE, "rows2", "fix_*.jsonl"))):
        with open(p, encoding="utf-8-sig") as f:
            for raw in f:
                if raw.strip():
                    fx = json.loads(raw)
                    fx["_from"] = os.path.basename(p)
                    fixes[fx["file"]].append(fx)
    os.makedirs(out_dir, exist_ok=True)
    counts = collections.Counter()
    why = collections.Counter()
    refused = []
    for name, path in sources.items():
        with open(path, encoding="utf-8-sig") as f:
            lines = [l.rstrip("\n") for l in f]
        rows = {n: json.loads(l) for n, l in enumerate(lines, 1) if l.strip()}
        drop = set()
        for fx in fixes.get(name, []):
            n = int(fx["line"])
            if n not in rows:
                refused.append((name, n, "no such line"))
                continue
            if fx.get("drop"):
                drop.add(n)
                counts["dropped"] += 1
                why["drop: " + str(fx.get("why", ""))[:40]] += 1
                continue
            r = rows[n]
            if fx.get("clear_before"):   # an earlier exchange that has nothing to do with the line: the row without it
                r["before"] = []
                counts["before cleared"] += 1
                why["before cleared"] += 1
                continue
            where = fx.get("where", "answer")
            if where == "answer":
                ok = r["answer"] == fx["old"]
                if ok:
                    r["answer"] = fx["new"]
            elif where.startswith("before."):
                i = int(where.split(".")[1])
                b = r.get("before") or []
                ok = i < len(b) and b[i][1] == fx["old"]
                if ok:
                    b[i][1] = fx["new"]
            else:
                ok = False
            if ok:
                counts["fixed"] += 1
                why[str(fx.get("why", ""))[:40]] += 1
            else:
                refused.append((name, n, f"{where}: the old text is not there ({fx['_from']})"))
        for r in rows.values():
            if r.get("role") == "other" and r.get("gender") not in ("man", "woman"):
                r["gender"] = "woman" if r.get("role_name") in WOMEN else "man"
                counts["gender set"] += 1
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as f:
            for n, r in sorted(rows.items()):
                if n not in drop:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    counts["rows"] += 1
    print(f"{counts['rows']} rows in {len(sources)} files -> {out_dir}; {counts['fixed']} fixed, {counts['dropped']} dropped, "
          f"{counts['before cleared']} with their earlier exchanges cleared, {counts['gender set']} people given their gender, {len(refused)} refused")
    for w, c in why.most_common(25):
        print(f"  {c:4} {w}")
    for r in refused[:30]:
        print("  refused", r)


if __name__ == "__main__":
    main(sys.argv[1])
