import io, json, os, sys
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
rows = [{"id": s["id"], "text": s["text"], "maj": s["maj"], "voice": voices[n % 3], "wav": f"s{n:04d}.wav"} for n, s in enumerate(V.seed_items())]
json.dump(rows, io.open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(rows), "seed commands;", len({r["text"] for r in rows}), "distinct texts")
