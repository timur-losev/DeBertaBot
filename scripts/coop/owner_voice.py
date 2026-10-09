"""A bot on the owner's spoken lines of 2026-10-09: what it picks for each transcript, as the voice chat would -- the
classifier reads the transcript lowercased and without its final .!? (build_v4.py norm).

  owner_voice_20261009.json    his first test, with bot v51: the lines seed set v52 was written from
  owner_voice_20261009b.json   his test of bot v52: the lines seed set v53 was written from

Not a blind test: the seed sets were written with these lines on the table. It shows whether the tuning took.

    python owner_voice.py ../../models/coop-deberta-v3-ens3-v52 [FILE.json]      # jev environment, CPU
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_bot  # noqa: E402

norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()  # noqa: E731
model = sys.argv[1]
source = sys.argv[2] if len(sys.argv) > 2 else "owner_voice_20261009.json"
lines = json.load(io.open(os.path.join(HERE, source), encoding="utf-8"))["lines"]
was = next(k for k in ("v52", "v51") if k in lines[0])      # the bot of the live test
bot = coop_bot.Bot(model_dir=model)
name = os.path.basename(os.path.normpath(model))
right = acted_wrong = was_right = 0
print(f"{name}: gate {bot.gate}, threshold {bot.threshold}; {source}")
for r in lines:
    bot.classify(norm(r["heard"]))
    intent, conf = bot.pick(bot.last_probs)
    acts = conf >= bot.threshold
    shown = intent if acts else "(say again)"
    ok = (acts and intent in r["want"]) or (not acts and "NONE" in r["want"])   # asking again about a non-order harms nothing
    right += ok
    acted_wrong += acts and intent not in r["want"]
    old_ok = (r[was][2] != "say_again" and r[was][0] in r["want"]) or (r[was][2] == "say_again" and "NONE" in r["want"])
    was_right += old_ok
    place = coop_bot.LOC.find(r["heard"])["target"]
    where = "" if not place else "  place: " + " ".join(str(place[k]) for k in ("qualifier", "object", "zone") if place[k]) + \
        (f" dir={place['direction']}" if place.get("direction") else "")
    print(f"  {'ok ' if ok else 'NO '} {r['heard']!r:42} {shown:<14} {conf:.2f}   want {'/'.join(r['want']):<22} {was}: {r[was][0]} {r[was][1]:.2f} {r[was][2]}{where}")
print(f"{name}: {right}/{len(lines)} as the owner wants (bot {was} in the live test: {was_right}/{len(lines)}); acted on a wrong order: {acted_wrong}")
