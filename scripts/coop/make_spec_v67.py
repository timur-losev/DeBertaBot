"""v67 (the owner, 2026-10-27): any thing with any order. «Подготовь обучение языковой модели версии 67, но я хочу, чтобы не
было никаких ограничений, что можно сделать с чем. Предмет есть предмет, и можно комбинировать»; the combinations come from
the data generator (stt/chains2/ml_v67/make_combos_v67.py; plan: stt/chains2/ml_v67/PLAN_v67.md).

No new intent (v66's 71, intents_v66.json). The means of an order ("climb onto the white table using the crate") is a
place target of role "means" (rule set v9, locations.py); the classifier learns that it never changes the intent.

Writes:
  seed_commands_v67.json     seed set v66 (ids unchanged) + the generator's English seeds of every intent (a means half the
                             time); a generated line that is already a seed of another intent is left out (counted)
  locations_v67.json         the place vocabulary v13 = v12 + the means_* lists of rule set v9, and "using" / "with" as
                             it_prep words ("climb onto the table using it")

    python make_spec_v67.py
"""
import io, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stt", "chains2", "ml_v67"))

MEANS_WORDS = {
    "means_lead": ["using", "with"],
    # "help me with the door", "deal with the window": the thing is the order's own, not a means
    "means_not_prev": ["help", "me", "us", "deal", "dealing", "done", "careful", "finished", "busy", "wrong"],
    "means_on_lead": ["standing", "stepping"],
    "means_use": ["use"],
    # "use the crate to the left", "use the box to me": a place after "to", not an order
    "means_use_not_next": ["the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her", "our", "their",
                           "me", "you", "him", "us", "them", "there", "here", "it"],
}
IT_PREP_MORE = ["using", "with"]
SEEDS_PER_INTENT = 36


def main():
    import make_combos_v67 as MC
    labels = [k for k in json.load(io.open(os.path.join(HERE, "intents_v66.json"), encoding="utf-8")) if not k.startswith("_")]
    assert MC.INTENTS, "no frames (stt/chains2/ml_v67/frames)"
    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v66.json"), encoding="utf-8"))
    have = {}
    for intent, lines in seeds.items():
        if not intent.startswith("_"):
            for t in lines:
                have.setdefault(t.strip().lower(), intent)
    added, clash, dup = 0, 0, 0
    for s in MC.classifier_seeds(random.Random(6702), SEEDS_PER_INTENT):
        assert s["intent"] in labels, s
        t = s["text"].strip()
        was = have.get(t.lower())
        if was is not None:
            clash += was != s["intent"]
            dup += was == s["intent"]
            continue
        seeds.setdefault(s["intent"], []).append(t)
        have[t.lower()] = s["intent"]
        added += 1
    ordered = {k: seeds[k] for k in labels if k in seeds}
    ordered.update({k: v for k, v in seeds.items() if k not in ordered})
    ordered["_relabel_v67"] = dict(seeds["_relabel_v66"])
    ordered["_note_v67"] = ("v67 (make_spec_v67.py, 2026-10-27): seed set v66 with its ids, + the generator's English lines of every "
                            "intent with any object and, half the time, any means (make_combos_v67.classifier_seeds).")
    json.dump(ordered, io.open(os.path.join(HERE, "seed_commands_v67.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    loc = json.load(io.open(os.path.join(HERE, "locations_v66.json"), encoding="utf-8"))
    assert loc["version"] == 12, loc["version"]
    loc["words"].update(MEANS_WORDS)
    loc["words"]["it_prep"] += [w for w in IT_PREP_MORE if w not in loc["words"]["it_prep"]]
    loc["version"] = 13
    loc["_note"] += (" v13 (2026-10-27, make_spec_v67.py): the means_* lists of rule set v9 (the thing an order is done with: "
                     "\"using the crate\", \"with this box\", \"standing on the spool\", \"use the chair to ...\"), \"using\" and \"with\" "
                     "as it_prep words; for the v67 bots.")
    json.dump(loc, io.open(os.path.join(HERE, "locations_v67.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in ordered.items() if not k.startswith("_"))
    print(f"seed_commands_v67.json: {n} seeds (+{added}; {dup} already seeds of the intent, {clash} of another intent left out); "
          f"locations_v67.json: version 13")


if __name__ == "__main__":
    main()
