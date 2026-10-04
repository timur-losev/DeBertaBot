"""
v3: orders that name a place on the map. Written BEFORE any v3 test line exists (then hashed into
frozen.txt, with locations.json / locations.py / locations_dev.json).

The owner's list: every map has a Main door; north, south, west, east doors and windows; blue, red,
yellow, white, brown stairs; chairs, sofas, tables; a basement, a 1st floor, a top floor, a roof.
The 24 intents do not change. What is new is a third modifier, the target: the place the bot must act
on, which the planner resolves on the map. One intent description is sharpened so the truth is
decidable: RAPPEL is using the rope; simply going to a named place, the roof included, is MOVE_TO
(spec_v2 listed "go up to the roof" under RAPPEL, and every "roof" line so far was a rope line).

Writes:
  blind/spec_v3.json       what the v3 blind authors and annotators see
  seed_commands_v3.json    seed set v21 + templated seed commands with map places, so that a model
                           trained with them (train_v2.py, COOP_TAG=v3) sees every place name in every
                           kind of order and learns the construction, not the word; never scored

    python make_spec_v3.py
"""
import io, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))

MAP = {
    "note": "Every map of the game has these named places, and players use the names in orders and callouts. "
            "Doors and windows are named by compass side, plus one Main door; stairs are named by colour; "
            "furniture and floors by what they are.",
    "objects": {
        "door": "a door: the Main door, or the north / south / west / east door",
        "window": "a window: the north / south / west / east window",
        "stairs": "a staircase: the blue / red / yellow / white / brown stairs",
        "chair": "chairs", "sofa": "a sofa", "table": "a table",
    },
    "qualifiers": ["main", "north", "south", "west", "east", "blue", "red", "yellow", "white", "brown"],
    "zones": {
        "basement": "the basement", "floor_1": "the 1st (ground) floor", "floor_2": "a second floor, if the player names one",
        "top_floor": "the top floor", "roof": "the roof",
        "up": "'upstairs': the floor above, relative", "down": "'downstairs': the floor below, relative",
    },
}
TARGET = ("the place on the map the BOT must act on for the order's first action -- go to, watch, open, throw at, "
          "hide behind... -- as {object, qualifier, zone, unknown_modifier}. object: one of the map's objects or "
          "null; qualifier: one of the map's qualifiers or null (also when the player named it without saying the "
          "object, e.g. 'push main' = door / main, 'take blue' = stairs / blue; a bare compass word with no object "
          "is qualifier only); zone: the floor the place is on, or the floor itself when the order is about the "
          "floor, else null. It is NOT the player's own position, NOT where the enemy is and NOT the place to "
          "leave: 'I'll take the north door, you take the south window' -> window / south. unknown_modifier: true "
          "when the player singles out one particular object with a word the map names cannot express ('the back "
          "door', 'the left window', 'the blue door'); then give the object and leave the qualifier null. For a "
          "callout or chatter (intent NONE) give the place the line is about, if it names one. All four are null "
          "/ false when the line names no place of the map (a marker, 'here', 'there', 'that wall').")
CHANGED = {
    "RAPPEL": "the bot uses a rappel rope on the outside of the building (rope up, drop down, hang at a window). "
              "Just going to a named place, the roof included, is MOVE_TO",
    "MOVE_TO": "the bot moves to a place: the marker, or a named or pointed-at location (a door, stairs, a floor, the roof)",
}

# ---- seed commands with places: template x place, so every name meets every kind of order
DOOR = [f"the {q} door" for q in ("main", "north", "south", "west", "east")]
WINDOW = [f"the {q} window" for q in ("north", "south", "west", "east")]
STAIRS = [f"{c} stairs" for c in ("blue", "red", "yellow", "white", "brown")]
LONE = ["main", "blue", "red", "yellow", "white", "brown"]
FURN = ["the sofa", "the couch", "the table", "the chairs"]
ZONE = ["the basement", "the first floor", "the top floor", "the roof"]
ANY = DOOR + WINDOW + STAIRS
TEMPLATES = {
    "MOVE_TO": [("go to {}", ANY + ZONE + FURN), ("move to {}", ANY + ZONE), ("get to {}", ANY + ZONE),
                ("head to {}", ZONE + STAIRS), ("take {}", LONE[1:] + STAIRS), ("go up to {}", ["the top floor", "the roof"])],
    "HOLD_ANGLE": [("hold {}", ANY + LONE), ("watch {}", ANY + LONE), ("cover {}", DOOR + WINDOW), ("eyes on {}", ANY),
                   ("hold {}", ["the basement", "the first floor", "the top floor"]), ("lock down {}", ZONE)],
    "OPEN": [("open {}", DOOR + WINDOW)],
    "SMOKE": [("smoke {}", ANY + LONE)],
    "FLASH": [("flash {}", ANY + LONE)],
    "FRAG": [("frag {}", ANY), ("nade {}", STAIRS + LONE)],
    "BREACH": [("breach {}", DOOR + WINDOW), ("blow {}", DOOR)],
    "VAULT_WINDOW": [("vault {}", WINDOW), ("go through {}", WINDOW), ("hop in {}", WINDOW)],
    "ENTRY": [("push {}", LONE + DOOR), ("push {}", ["the basement", "the first floor", "the top floor"]),
              ("clear {}", ZONE), ("rush {}", LONE)],
    "FLANK": [("flank through {}", DOOR + ["the basement"]), ("go around through {}", DOOR + WINDOW)],
    "TAKE_COVER": [("hide behind {}", FURN), ("take cover behind {}", FURN), ("get behind {}", FURN)],
    "RAPPEL": [("rappel to {}", WINDOW), ("rope down to {}", WINDOW), ("rappel from {}", ["the roof"])],
    "DRONE": [("drone {}", ZONE + STAIRS + DOOR)],
    "FALL_BACK": [("fall back to {}", ZONE + STAIRS + DOOR)],
    "PLANT": [("plant at {}", STAIRS + DOOR), ("plant behind {}", FURN)],
    "FOLLOW_ME": [("follow me to {}", ANY + ZONE)],
    "COVER_ME": [("cover me from {}", WINDOW + STAIRS + FURN)],
    "NONE": [("one on {}", STAIRS + LONE[1:]), ("two at {}", DOOR + WINDOW), ("{} is clear", ANY + ZONE),
             ("he's behind {}", FURN), ("they're on {}", ZONE), ("contact {}", LONE + STAIRS),
             ("don't open {}", DOOR + WINDOW), ("don't go to {}", ZONE + STAIRS), ("don't smoke {}", ANY)],
    "WAIT": [("don't push {} yet", LONE + DOOR), ("don't open {} yet", DOOR)],
}
PER_TEMPLATE = 3


def location_seeds():
    rng = random.Random(3)
    out = {}
    for intent, templates in TEMPLATES.items():
        for tpl, places in templates:
            for place in rng.sample(places, min(PER_TEMPLATE, len(places))):
                out.setdefault(intent, []).append(tpl.format(place))
    return out


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v2.json"), encoding="utf-8"))
    spec["intents"].update(CHANGED)
    spec["map"] = MAP
    spec["modifiers"]["target"] = TARGET
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v3.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v21.json"), encoding="utf-8"))
    extra = location_seeds()
    seeds["_note_v3"] = ("v3: + templated seed commands with map places (make_spec_v3.py), written before any "
                         "v3 test line existed: " + ", ".join(f"{k} {len(v)}" for k, v in extra.items()))
    for k, v in extra.items():
        new = [x for x in v if x not in seeds[k]]
        seeds[k] = seeds[k] + new
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v3.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    n = sum(len(v) for v in extra.values())
    print(f"spec_v3: {len(spec['intents'])} intents; {n} location seeds over {len(extra)} intents")
    for k, v in extra.items():
        print(f"  {k}: {v[:5]}")


if __name__ == "__main__":
    main()
