import io, json, os, sys
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V
out = sys.argv[1]
items = [i for i in V.load_items() if i["author"] in ("r6", "cs") and i["maj"]]
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
rows = [{"id": i["id"], "author": i["author"], "version": i["version"], "text": i["text"], "maj": i["maj"],
         "voice": voices[n % 3], "wav": f"{n:04d}.wav"} for n, i in enumerate(items)]
json.dump(rows, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(rows), "lines;", sum(r["maj"] == "NONE" for r in rows), "of them NONE; versions", sorted({r["version"] for r in rows}))
print("examples:", [r["text"] for r in rows[:4]])
