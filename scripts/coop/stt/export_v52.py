"""What v52 adds to the voice chain, as lists for the synthesis scripts: the v52 lines of the r6 and cs authors
(lines_v52.json) and the seed commands seed_commands_v52.json has on top of v51 (seeds_v52.json). Everything voiced
before keeps its audio and transcripts (lines.json, seeds.json: v4; the _v5 and _v51 lists).

    python export_v52.py
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v52"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
items = [i for i in V.load_items() if i["version"] == "v52" and i["author"] in ("r6", "cs") and i["maj"]]
rows = [{"id": i["id"], "author": i["author"], "version": i["version"], "text": i["text"], "maj": i["maj"],
         "voice": voices[n % 3], "wav": f"v52_{n:04d}.wav"} for n, i in enumerate(items)]
json.dump(rows, io.open(os.path.join(HERE, "lines_v52.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
old = {s["id"]: s["text"] for f in ("seeds.json", "seeds_v5.json", "seeds_v51.json") for s in json.load(io.open(os.path.join(HERE, f), encoding="utf-8"))}
seeds = V.seed_items()
assert all(old[s["id"]] == s["text"] for s in seeds if s["id"] in old), "an earlier seed changed its id"
new = [s for s in seeds if s["id"] not in old]
srows = [{"id": s["id"], "text": s["text"], "maj": s["maj"], "voice": voices[n % 3], "wav": f"s52_{n:04d}.wav"} for n, s in enumerate(new)]
json.dump(srows, io.open(os.path.join(HERE, "seeds_v52.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(rows), "v52 lines of r6 and cs;", len(srows), "new seed commands")
