"""The Russian and Spanish translation batches for decoder v64 (chains2/ml_v64/in): every player line the v62 and v64 bots
added that the decoder has never seen, as singles: the v62 and v64 authored lines (blind/v62, blind/v64: 300) and the seed
commands seed_commands_v64.json has beyond v61's (the bot that talks and carries, melee and holster, the report, the body,
push, roll, drop: about 670). Translated under chains2/ml_v64/TRANSLATE.md, as round v62 was.

    python prep_ml_v64.py      -> chains2/ml_v64/in/{ru,es}_single_{00,01,02}.json"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v64"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import coop_v2 as V   # noqa: E402

OUT = os.path.join(HERE, "chains2", "ml_v64", "in")
os.makedirs(OUT, exist_ok=True)
v61 = json.load(io.open(os.path.join(HERE, "..", "seed_commands_v61.json"), encoding="utf-8"))
old = {t for k, v in v61.items() if not k.startswith("_") for t in v}
items = [{"id": i["id"], "en": i["text"], "intent": i["maj"]} for i in V.load_items() if i["version"] in ("v62", "v64") and i["maj"]]
items += [{"id": s["id"], "en": s["text"], "intent": s["maj"]} for s in V.seed_items() if s["text"] not in old]
seen, uniq = set(), []
for it in items:
    if it["en"] not in seen:
        seen.add(it["en"])
        uniq.append(it)
per = (len(uniq) + 2) // 3
for lang in ("ru", "es"):
    for b in range(3):
        part = uniq[b * per:(b + 1) * per]
        json.dump({"lang": lang, "kind": "single", "items": part},
                  io.open(os.path.join(OUT, f"{lang}_single_{b:02d}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(uniq), "singles in 3 batches per language")
