"""What v62 adds to the voice chain, as lists for the synthesis scripts: the seed commands seed_commands_v62.json has on top
of v61 (seeds_v62.json: the bot that talks and carries, make_spec_v62.py) and the v62 lines of the r6 and cs authors
(lines_v62.json; the stt author writes as the recognizer hears, so its lines are not voiced). Everything voiced before keeps
its audio and transcripts (lines.json, seeds.json: v4; the _v5 to _v61 lists).

    python export_v62.py seeds      the new seeds (the second batch, carrying, came after the v62 test lines)
    python export_v62.py lines      the v62 lines, once the authors and the annotators are done
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v62"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
what = sys.argv[1] if len(sys.argv) > 1 else ""
assert what in ("seeds", "lines"), __doc__

if what == "seeds":
    old = {s["id"]: s["text"] for f in ("seeds.json", "seeds_v5.json", "seeds_v51.json", "seeds_v52.json", "seeds_v53.json",
                                       "seeds_v54.json", "seeds_v55.json", "seeds_v56.json", "seeds_v57.json",
                                       "seeds_v58.json", "seeds_v60.json", "seeds_v61.json") for s in json.load(io.open(os.path.join(HERE, f), encoding="utf-8"))}
    seeds = V.seed_items()
    assert all(old[s["id"]] == s["text"] for s in seeds if s["id"] in old), "an earlier seed changed its id"
    new = [s for s in seeds if s["id"] not in old]
    srows = [{"id": s["id"], "text": s["text"], "maj": s["maj"], "voice": voices[n % 3], "wav": f"s62_{n:04d}.wav"} for n, s in enumerate(new)]
    json.dump(srows, io.open(os.path.join(HERE, "seeds_v62.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(srows), "new seed commands")
else:
    items = [i for i in V.load_items() if i["version"] == "v62" and i["author"] in ("r6", "cs") and i["maj"]]
    rows = [{"id": i["id"], "author": i["author"], "version": i["version"], "text": i["text"], "maj": i["maj"],
             "voice": voices[n % 3], "wav": f"v62_{n:04d}.wav"} for n, i in enumerate(items)]
    json.dump(rows, io.open(os.path.join(HERE, "lines_v62.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(rows), "v62 lines of r6 and cs")
