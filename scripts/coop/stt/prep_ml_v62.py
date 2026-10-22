"""Round v62 of the decoder (the v6x line's chain, three languages in, English orders out): what is to be translated into Russian
and Spanish, cut into batches for the AI translators (chains2/ml_v62/TRANSLATE.md), and the blind test sets for the test
translators (chains2/ml_v62/TEST.md). The English answers never change: only the player's words are translated.

  training (chains2/ml_v62/in/<lang>_<kind>_<n>.json):
    single    the authored lines of v61 (load_items, every author) and up to 12 seed commands per intent: one order or none
    chain     round two's kept teacher items (several orders in one line)
    ctx       round six's kept context items: the earlier lines and the line (the bot's line stays English: the brain's own words)
  tests (chains2/ml_v62/test_in/<lang>_<set>.json): round three's blind chains (blind2, 150) and blind context items (ctx, 150)

    python prep_ml_v62.py
"""
import io, json, os, random, sys
from collections import defaultdict
os.environ["COOP_TAG"] = "v61"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import coop_v2 as V
import build_v61
sys.modules["build_v54"] = build_v61   # the chain modules import build_v54 by name; they get v61's lines and seeds
import chains2_v54 as C2

OUT = os.path.join(C2.CH2, "ml_v62")
LANGS = ("ru", "es")
BATCH = {"single": 600, "chain": 450, "ctx": 300}
SEEDS_PER_INTENT = 12


def batches(rows, n):
    return [rows[i:i + n] for i in range(0, len(rows), n)]


def main():
    os.makedirs(os.path.join(OUT, "in"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "test_in"), exist_ok=True)
    singles = [{"id": i["id"], "en": i["text"], "intent": i["maj"]} for i in V.load_items() if i["maj"]]
    by = defaultdict(list)
    for s in V.seed_items():
        by[s["maj"]].append(s)
    rng = random.Random(62)
    for k in sorted(by):
        for s in rng.sample(by[k], min(SEEDS_PER_INTENT, len(by[k]))):
            singles.append({"id": s["id"], "en": s["text"], "intent": s["maj"]})
    kept, _ = C2.teacher()
    chains = [{"id": t["id"], "en": t["text"], "orders": t["orders"], "pieces": t["pieces"]} for t in kept]
    ctx = [{"id": x["id"], "before": x["before"], "bot": x["bot"], "en": x["line"], "pieces": x["pieces"], "orders": x["orders"]}
           for x in C2.jload(C2.CH2, "ctx_checked_v59.json") if x["kept"]]
    counts = {}
    for kind, rows in (("single", singles), ("chain", chains), ("ctx", ctx)):
        rng.shuffle(rows)
        for lang in LANGS:
            for n, b in enumerate(batches(rows, BATCH[kind])):
                p = os.path.join(OUT, "in", f"{lang}_{kind}_{n:02d}.json")
                json.dump({"lang": lang, "kind": kind, "items": b}, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        counts[kind] = (len(rows), len(batches(rows, BATCH[kind])))
    ts = C2.tests()
    for lang in LANGS:
        json.dump({"lang": lang, "set": "blind2", "items": [{"id": t["id"], "en": t["text"]} for t in ts["blind2"]]},
                  io.open(os.path.join(OUT, "test_in", f"{lang}_blind2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        json.dump({"lang": lang, "set": "ctx", "items": [{"id": t["id"], "before": t["before"], "bot": t["bot"], "en": t["text"]}
                                                          for t in ts["ctx"]]},
                  io.open(os.path.join(OUT, "test_in", f"{lang}_ctx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    strings = sum(len(r["before"]) + 1 if "before" in r else 1 for r in ctx) + len(singles) + len(chains)
    print(f"training: {counts} (items, batches per language); {strings} strings per language")
    print(f"tests: blind2 {len(ts['blind2'])}, ctx {len(ts['ctx'])} per language")


if __name__ == "__main__":
    main()
