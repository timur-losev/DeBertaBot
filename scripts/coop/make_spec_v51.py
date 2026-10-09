"""
v51: "look at ...". Written BEFORE any v51 test line exists and before any v5 model was trained (then hashed
into frozen.txt).

The owner, 2026-10-09, while the v5 training waited for the GPU: "I also want the command look at ...: look at
me, look at sofa, look at that window". The 27 intents of v5 have nothing for it: "watch the window" is
HOLD_ANGLE (keep it covered), "come here" is FOLLOW_ME.

Two intents are added, in one family ("look"):
  LOOK_AT      the bot turns and looks at a place, an object, the marked thing or a direction. The place is in
               the bot's place record, as for every other order ("look at sofa" -> sofa, "look at that window"
               -> window, "look left" -> direction left); with no place it is the marker.
  LOOK_AT_ME   the bot turns and looks at the player. The player is not a place of the map, so the place record
               cannot say it; the bot's other player-directed orders carry the player in the intent too
               (FOLLOW_ME, COVER_ME, REVIVE_ME). The developer's choice, not the owner's wording: a planner that
               wants one command treats both as "look" (same family) and reads the top intent as the target.

Nothing is removed or renamed. The line between one look and a watch is the verb: look / face / turn to is
LOOK_AT; watch / hold / cover / eyes on (keep it covered, ready to shoot) stays HOLD_ANGLE. The place matcher
(rule set v4) is not touched: "look left", "look up", "look behind you" already give a direction.

Writes:
  blind/spec_v51.json       what the v51 blind authors and annotators see
  intents_v51.json          the model-side vocabulary (29 intents)
  seed_commands_v51.json    seed set v5 (ids unchanged) + canonical commands for the two intents; training only

    python make_spec_v51.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SPEC = {
    "LOOK_AT": "the bot turns and looks at something: a named place or object, the thing the player points at, or a "
               "direction (look at the sofa, look at that window, look left, look up, look behind you, face the door, "
               "turn around). It is one look, not a watch: keeping an angle covered, ready to shoot, is HOLD_ANGLE "
               "('watch the window', 'eyes on the door', 'cover the stairs'); going to a place is MOVE_TO, going "
               "somewhere to check it out is DRONE. A 'look' that is not about turning to see is not this intent: a "
               "warning or an exclamation ('look out', 'look at that shot'), a filler ('look, we need to move'), "
               "searching ('look for the defuser') are NONE",
    "LOOK_AT_ME": "the bot turns and looks at the PLAYER (look at me, face me, turn to me, look over here). The bot "
                  "does not come to the player -- that is FOLLOW_ME -- and does not start covering them (COVER_ME)",
}
CHANGED = {
    "HOLD_ANGLE": "the bot watches a specific angle / door / window / corridor / stairs, ready to shoot, and keeps "
                  "watching it. Only turning to look at something is LOOK_AT",
    "FOLLOW_ME": "the bot follows the player and stays with them. 'Look at me' is LOOK_AT_ME: the bot turns, it does "
                 "not come",
}
TARGET_ADD = (" For LOOK_AT the target is what the bot must look at ('look at the sofa' = sofa, 'look at that window' "
              "= window, 'look left' = direction left); for LOOK_AT_ME it is the player, who is not a place of the "
              "map: all null.")
NEW_MODEL = {
    "LOOK_AT": {"label": "look there", "description": "turn and look at a place, an object, a marked thing or a direction"},
    "LOOK_AT_ME": {"label": "look at you", "description": "turn and look at the player"},
}
FAMILY_NOTE = "v51 families: v5 families + LOOK_AT and LOOK_AT_ME in one family 'look'"

# canonical short commands, written by the developer before any v51 test line existed (training only, never scored)
NEW_SEEDS = {
    "LOOK_AT": ["look at that", "look at this", "look there", "look over there", "look at it", "take a look at that",
                "look that way", "face that way", "look where i'm pointing", "look at my marker", "look at the ping",
                "turn around", "turn and look", "look at that thing", "have a look at that", "look right there"],
    "LOOK_AT_ME": ["look at me", "face me", "turn to me", "look over here", "look at me bot", "hey look at me",
                   "turn and look at me", "look my way", "turn towards me", "face me now", "look here at me",
                   "look at me when i talk", "can you look at me", "turn around and look at me"],
}
NEW_NEGATED = {"NONE": ["don't look at me", "don't look", "do not look at that", "don't look there", "never mind don't look"],
               "WAIT": ["don't look yet"]}
# "look" in another sense: the classifier must not turn the bot's head for these
OTHER_SENSE = {"NONE": ["look out", "look at that shot", "look at this guy", "look we need to go", "looks clear",
                        "looking good", "look alive", "i'm looking for the defuser", "look who's back"]}
DOOR = [f"the {q} door" for q in ("main", "north", "south", "west", "east")]
WINDOW = [f"the {q} window" for q in ("north", "south", "west", "east")]
STAIRS = [f"{c} stairs" for c in ("blue", "red", "yellow", "white", "brown")]
ZONE = ["the basement", "the first floor", "the top floor", "the roof"]
THINGS = ["the sofa", "sofa", "the table", "the chairs", "that window", "that door", "the stairs", "that sofa", "the window"]
PLACED = {
    "LOOK_AT": [("look at {}", THINGS + [DOOR[0], DOOR[1], WINDOW[2], WINDOW[3], STAIRS[0], STAIRS[2], ZONE[3]]),
                ("face {}", [DOOR[2], WINDOW[0], THINGS[0], STAIRS[4]]),
                ("turn to {}", [DOOR[4], WINDOW[1], THINGS[2]]),
                ("take a look at {}", [STAIRS[1], DOOR[3], THINGS[4]]),
                ("look up at {}", [ZONE[3], WINDOW[0]]),
                ("look down at {}", [ZONE[0], STAIRS[3]])],
}
DIRECTED = {
    "LOOK_AT": ["look left", "look right", "look up", "look down", "look behind you", "look back", "look to the left",
                "look to your right", "look straight ahead", "look at the left window", "look at the door on the right",
                "look up the stairs", "face left", "face right", "look above you", "look at your six", "look forward",
                "look at the window above you"],
}
ON_SIGNAL = {"LOOK_AT": ["look left when i say", "on my go look at the door"], "LOOK_AT_ME": ["look at me on my mark"]}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v5.json"), encoding="utf-8"))
    for k, v in CHANGED.items():
        assert k in spec["intents"], k
        spec["intents"][k] = v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_SPEC)
    spec["intents"]["NONE"] = none                      # NONE stays the last intent, as in every earlier spec
    spec["modifiers"]["target"] += TARGET_ADD
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v51.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v5.json"), encoding="utf-8"))
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model["_note_v51"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v51.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v5.json"), encoding="utf-8"))
    extra = {}
    for src in (NEW_SEEDS, NEW_NEGATED, OTHER_SENSE, DIRECTED, ON_SIGNAL):
        for k, v in src.items():
            extra.setdefault(k, []).extend(v)
    for k, templates in PLACED.items():
        for tpl, places in templates:
            extra[k].extend(tpl.format(p) for p in places)
    owner = {t: k for k, v in seeds.items() if not k.startswith("_") for t in v}
    added = 0
    for k, v in extra.items():
        for t in v:
            assert owner.get(t, k) == k, f"{t!r} is already a {owner[t]} seed, cannot also be {k}"
            if t not in owner:
                seeds.setdefault(k, []).append(t)       # appended: every v5 seed keeps its id (seed_<INTENT>_<n>)
                owner[t] = k
                added += 1
    # no v5 seed changes its label: none has "look" / "face" / "turn"; "eyes on <place>" and "eyes left" stay HOLD_ANGLE
    seeds["_note_v51"] = ("v51 (make_spec_v51.py, before any v51 test line existed): seed set v5 + canonical commands for "
                          "LOOK_AT (plain, with places, with directions) and LOOK_AT_ME, their negations, and 'look' in "
                          f"another sense under NONE: {added} new seeds over {len(extra)} intents")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v51.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v51: {len(spec['intents'])} intents (last: {list(spec['intents'])[-3:]}); intents_v51: "
          f"{len([k for k in model if not k.startswith('_')])}; seeds v51: {n} (+{added}); "
          f"LOOK_AT {len(seeds['LOOK_AT'])}, LOOK_AT_ME {len(seeds['LOOK_AT_ME'])}")


if __name__ == "__main__":
    main()
