"""What v57 adds to the voice chain, as lists for the synthesis scripts: the seed commands seed_commands_v57.json has on top
of v56 (seeds_v57.json; a seed relabelled under v57 keeps its id and its audio) and the v57 lines of the r6 and cs authors
(lines_v57.json; the stt author writes as the recognizer
hears, so its lines are not voiced). Everything voiced before keeps its audio and transcripts (lines.json, seeds.json: v4;
the _v5 to _v56 lists).

    python export_v57.py seeds      the new seeds (they exist before any v57 test line)
    python export_v57.py lines      the v57 lines, once the authors and the annotators are done
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v57"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
what = sys.argv[1] if len(sys.argv) > 1 else ""
assert what in ("seeds", "lines"), __doc__

if what == "seeds":
    old = {s["id"]: s["text"] for f in ("seeds.json", "seeds_v5.json", "seeds_v51.json", "seeds_v52.json", "seeds_v53.json",
                                       "seeds_v54.json", "seeds_v55.json", "seeds_v56.json") for s in json.load(io.open(os.path.join(HERE, f), encoding="utf-8"))}
    seeds = V.seed_items()
    assert all(old[s["id"]] == s["text"] for s in seeds if s["id"] in old), "an earlier seed changed its id"
    new = [s for s in seeds if s["id"] not in old]
    srows = [{"id": s["id"], "text": s["text"], "maj": s["maj"], "voice": voices[n % 3], "wav": f"s57_{n:04d}.wav"} for n, s in enumerate(new)]
    json.dump(srows, io.open(os.path.join(HERE, "seeds_v57.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(srows), "new seed commands")
else:
    items = [i for i in V.load_items() if i["version"] == "v57" and i["author"] in ("r6", "cs") and i["maj"]]
    rows = [{"id": i["id"], "author": i["author"], "version": i["version"], "text": i["text"], "maj": i["maj"],
             "voice": voices[n % 3], "wav": f"v57_{n:04d}.wav"} for n, i in enumerate(items)]
    json.dump(rows, io.open(os.path.join(HERE, "lines_v57.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(rows), "v57 lines of r6 and cs")
