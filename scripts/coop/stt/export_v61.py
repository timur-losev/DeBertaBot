"""What v61 adds to the voice chain, as a list for the synthesis scripts: the seed commands seed_commands_v61.json has on top
of v60 (seeds_v61.json; make_spec_v61.py). v61 has no lines of its own: every authored line keeps its v60 audio and
transcripts. Everything voiced before keeps its audio and transcripts (lines.json, seeds.json: v4; the _v5 to _v60 lists).

    python export_v61.py seeds
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v61"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
assert sys.argv[1:] == ["seeds"], __doc__

old = {s["id"]: s["text"] for f in ("seeds.json", "seeds_v5.json", "seeds_v51.json", "seeds_v52.json", "seeds_v53.json",
                                   "seeds_v54.json", "seeds_v55.json", "seeds_v56.json", "seeds_v57.json",
                                   "seeds_v58.json", "seeds_v60.json")
       for s in json.load(io.open(os.path.join(HERE, f), encoding="utf-8"))}
seeds = V.seed_items()
assert all(old[s["id"]] == s["text"] for s in seeds if s["id"] in old), "an earlier seed changed its id"
new = [s for s in seeds if s["id"] not in old]
srows = [{"id": s["id"], "text": s["text"], "maj": s["maj"], "voice": voices[n % 3], "wav": f"s61_{n:04d}.wav"} for n, s in enumerate(new)]
json.dump(srows, io.open(os.path.join(HERE, "seeds_v61.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(srows), "new seed commands")
