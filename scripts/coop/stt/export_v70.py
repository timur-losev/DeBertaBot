"""v70 (2026-11-11): the seeds seed_commands_v70.json adds on top of v67 (make_spec_v70.py: DRIVE, BODY_MOVE, BODY_COMBO) -> seeds_v70.json
(s70_*.wav); no new lines. export_v67.py's docstring follows.

What v67 adds to the voice chain, as lists for the synthesis scripts: the seed commands seed_commands_v67.json has on top
of v65 (seeds_v67.json: the owner's notes of 2026-10-26/27, make_spec_v67.py; GIVE_WAY and WHAT_IS_IT) and the v67 lines of the r6 and cs authors
(lines_v67.json; the stt author writes as the recognizer hears, so its lines are not voiced). Everything voiced before keeps
its audio and transcripts (lines.json, seeds.json: v4; the _v5 to _v65 lists).

    python export_v67.py seeds      the new seeds
    python export_v67.py lines      the v67 lines, once the authors and the annotators are done
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v70"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
voices = ["Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark"]
what = sys.argv[1] if len(sys.argv) > 1 else ""
assert what in ("seeds", "lines"), __doc__

if what == "seeds":
    old = {s["id"]: s["text"] for f in ("seeds.json", "seeds_v5.json", "seeds_v51.json", "seeds_v52.json", "seeds_v53.json",
                                       "seeds_v54.json", "seeds_v55.json", "seeds_v56.json", "seeds_v57.json",
                                       "seeds_v58.json", "seeds_v60.json", "seeds_v61.json", "seeds_v62.json", "seeds_v64.json", "seeds_v65.json", "seeds_v66.json", "seeds_v67.json") for s in json.load(io.open(os.path.join(HERE, f), encoding="utf-8"))}
    seeds = V.seed_items()
    # an id voiced before for another text (seed_COLLECT_50: "take this", taken out of the v62 seeds, now "lift up the box"):
    # voiced again; its _v67 transcripts come after the older ones in build_v67.py heard(), so they win
    reused = [s["id"] for s in seeds if s["id"] in old and old[s["id"]] != s["text"]]
    print("ids voiced before for another text, voiced again:", reused)
    new = [s for s in seeds if s["id"] not in old or old[s["id"]] != s["text"]]
    # a seed voiced in an earlier export of this list keeps its row (its wav, its voice); a new one gets the next free number
    # (2026-11-11: the canon's turns appended after the first build; numbering them in order would have given the earlier
    # seeds' audio to other texts)
    p = os.path.join(HERE, "seeds_v70.json")
    prev = {r["id"]: r for r in json.load(io.open(p, encoding="utf-8"))} if os.path.exists(p) else {}
    free = 1 + max([int(r["wav"][4:8]) for r in prev.values()], default=-1)
    srows = []
    for s in new:
        r = prev.get(s["id"])
        if r is not None and r["text"] == s["text"] and r["maj"] == s["maj"]:
            srows.append(r)
            continue
        srows.append({"id": s["id"], "text": s["text"], "maj": s["maj"], "voice": voices[free % 3], "wav": f"s70_{free:04d}.wav"})
        free += 1
    # in wav order: the synthesis voices every row again and picks some voices by the row's place, so the earlier rows keep
    # their places (and their audio) and the new ones come after them
    srows.sort(key=lambda r: r["wav"])
    json.dump(srows, io.open(os.path.join(HERE, "seeds_v70.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(srows), "new seed commands")
else:
    items = [i for i in V.load_items() if i["version"] == "v70" and i["author"] in ("r6", "cs") and i["maj"]]
    rows = [{"id": i["id"], "author": i["author"], "version": i["version"], "text": i["text"], "maj": i["maj"],
             "voice": voices[n % 3], "wav": f"v70_{n:04d}.wav"} for n, i in enumerate(items)]
    json.dump(rows, io.open(os.path.join(HERE, "lines_v70.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(rows), "v70 lines of r6 and cs")
