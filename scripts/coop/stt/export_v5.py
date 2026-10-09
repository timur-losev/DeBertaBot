"""What v5 adds to the voice chain, as lists for the synthesis scripts: the v5 lines of the r6 and cs authors
(lines_v5.json) and the seed commands seed_commands_v5.json has on top of v31 (seeds_v5.json). The 422 lines and 580
seed commands of v4 keep their audio and transcripts (lines.json, seeds.json).

    python export_v5.py
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v5"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
items = [i for i in V.load_items() if i["version"] == "v5" and i["author"] in ("r6", "cs") and i["maj"]]
rows = [{"id": i["id"], "author": i["author"], "version": i["version"], "text": i["text"], "maj": i["maj"],
         "voice": voices[n % 3], "wav": f"v5_{n:04d}.wav"} for n, i in enumerate(items)]
json.dump(rows, io.open(os.path.join(HERE, "lines_v5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
old = {s["id"]: s["text"] for s in json.load(io.open(os.path.join(HERE, "seeds.json"), encoding="utf-8"))}
seeds = V.seed_items()
assert all(old[s["id"]] == s["text"] for s in seeds if s["id"] in old), "a v31 seed changed its id"
new = [s for s in seeds if s["id"] not in old]
srows = [{"id": s["id"], "text": s["text"], "maj": s["maj"], "voice": voices[n % 3], "wav": f"s5_{n:04d}.wav"} for n, s in enumerate(new)]
json.dump(srows, io.open(os.path.join(HERE, "seeds_v5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(rows), "v5 lines of r6 and cs;", len(srows), "new seed commands")
