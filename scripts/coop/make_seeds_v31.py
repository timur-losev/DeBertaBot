"""
Seed set v31 = the v3 seed set, corrected and extended after the v3 review (seed_commands_v3.json
itself stays as the v3 study used it). Every v3 seed is kept, two change their label, and new ones
are added. What was wrong in v3's seeds:

  1. make_spec_v3.py re-defined RAPPEL (the rope; just going to the roof is MOVE_TO) but only appended
     to the v21 seeds, so "get on the roof" and "go roof" stayed under RAPPEL and the bot trained on
     them answered RAPPEL to both. Here they move to MOVE_TO.
  2. Each order template was filled with 3 places sampled from its whole list, 150 of 486
     combinations; "take {}" drew only "... stairs" forms, so "take blue" was never taught and the
     bot read it as ENTRY. Here every template is also filled with PER_GROUP places from each KIND
     of place it allows (doors, windows, stairs, lone names, floors, furniture), so every template
     meets every kind. It is still a sample, not the full grid: a name is not seen in every order.
     The roof is not left to the draw: every MOVE_TO template that takes a floor gets it ("go to
     the roof", "get to the roof", ...), because that is the order the old RAPPEL seeds fought.

  3. (from the review run on the Mac, review_v3/ and probe_v3.log) The v3 bot carries out state
     callouts as orders: "<place> is smoked" -> SMOKE on 47 names of 47, "<place> clear" -> ENTRY on
     27 of 30. The training data had "smoked" only in two SMOKE orders and no "clear" callout without
     a copula. Here NONE gets templates for both, next to the orders they must not be confused with
     ("smoke {}", "clear {}"), and five plain callouts without a place.

Written after the first v3 lines and the review's probes had been seen: every number on those lines
for a model trained with this set is "after tuning". Never scored itself.

    python make_seeds_v31.py
"""
import io, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))

DOOR = [f"the {q} door" for q in ("main", "north", "south", "west", "east")]
WINDOW = [f"the {q} window" for q in ("north", "south", "west", "east")]
STAIRS = [f"{c} stairs" for c in ("blue", "red", "yellow", "white", "brown")]
COLOUR = ["blue", "red", "yellow", "white", "brown"]
LONE = ["main"] + COLOUR
FURN = ["the sofa", "the couch", "the table", "the chairs"]
ZONE = ["the basement", "the first floor", "the top floor", "the roof"]
FLOOR = ["the basement", "the first floor", "the top floor"]
UP = ["the top floor", "the roof"]
# as players call them out, no article
DOOR_B = [f"{q} door" for q in ("main", "north", "south", "west", "east")]
WINDOW_B = [f"{q} window" for q in ("north", "south", "west", "east")]
ZONE_B = ["basement", "first floor", "top floor", "roof"]
ROOF = ["the roof"]
ANY = [DOOR, WINDOW, STAIRS]
# intent -> [(template, [groups of places])]
TEMPLATES = {
    "MOVE_TO": [("go to {}", ANY + [ZONE, FURN, ROOF]), ("move to {}", ANY + [ZONE, ROOF]),
                ("get to {}", ANY + [ZONE, ROOF]), ("head to {}", [ZONE, STAIRS, ROOF]), ("take {}", [COLOUR, STAIRS]),
                ("go up to {}", [UP])],
    "HOLD_ANGLE": [("hold {}", ANY + [LONE]), ("watch {}", ANY + [LONE]), ("cover {}", [DOOR, WINDOW]),
                   ("eyes on {}", ANY), ("hold {}", [FLOOR]), ("lock down {}", [ZONE])],
    "OPEN": [("open {}", [DOOR, WINDOW])],
    "SMOKE": [("smoke {}", ANY + [LONE])],
    "FLASH": [("flash {}", ANY + [LONE])],
    "FRAG": [("frag {}", ANY), ("nade {}", [STAIRS, LONE])],
    "BREACH": [("breach {}", [DOOR, WINDOW]), ("blow {}", [DOOR])],
    "VAULT_WINDOW": [("vault {}", [WINDOW]), ("go through {}", [WINDOW]), ("hop in {}", [WINDOW])],
    "ENTRY": [("push {}", [LONE, DOOR]), ("push {}", [FLOOR]), ("clear {}", [ZONE]), ("rush {}", [LONE])],
    "FLANK": [("flank through {}", [DOOR, ["the basement"]]), ("go around through {}", [DOOR, WINDOW])],
    "TAKE_COVER": [("hide behind {}", [FURN]), ("take cover behind {}", [FURN]), ("get behind {}", [FURN])],
    "RAPPEL": [("rappel to {}", [WINDOW]), ("rope down to {}", [WINDOW]), ("rappel from {}", [ROOF])],
    "DRONE": [("drone {}", [ZONE, STAIRS, DOOR])],
    "FALL_BACK": [("fall back to {}", [ZONE, STAIRS, DOOR])],
    "PLANT": [("plant at {}", [STAIRS, DOOR]), ("plant behind {}", [FURN])],
    "FOLLOW_ME": [("follow me to {}", ANY + [ZONE])],
    "COVER_ME": [("cover me from {}", [WINDOW, STAIRS, FURN])],
    "NONE": [("one on {}", [STAIRS, COLOUR]), ("two at {}", [DOOR, WINDOW]), ("{} is clear", ANY + [ZONE]),
             ("he's behind {}", [FURN]), ("they're on {}", [["the first floor", "the top floor", "the roof"]]), ("they're in {}", [["the basement"]]), ("contact {}", [LONE, STAIRS]),
             ("don't open {}", [DOOR, WINDOW]), ("don't go to {}", [ZONE, STAIRS]), ("don't smoke {}", ANY),
             # state callouts (point 3 of the docstring)
             ("{} is smoked", ANY + [ZONE]), ("{} smoked", [DOOR_B, STAIRS, LONE]), ("i smoked {}", [DOOR, WINDOW]),
             ("they smoked {}", [STAIRS, ZONE]), ("{} clear", [DOOR_B, WINDOW_B, STAIRS, LONE, ZONE_B]),
             ("{} cleared", [DOOR_B, ZONE_B]), ("clear on {}", [STAIRS, LONE])],
    "WAIT": [("don't push {} yet", [LONE, DOOR]), ("don't open {} yet", [DOOR])],
}
PER_GROUP = 2
MOVED = {"RAPPEL": ["get on the roof", "go roof"]}      # -> MOVE_TO: no rope word
PLAIN = {"NONE": ["all clear", "room clear", "it's smoked", "already smoked", "that's smoked"]}


def location_seeds():
    rng = random.Random(31)
    out, grid = {}, 0
    for intent, templates in TEMPLATES.items():
        for tpl, groups in templates:
            for places in groups:
                grid += len(places)
                for place in rng.sample(places, min(PER_GROUP, len(places))):
                    out.setdefault(intent, []).append(tpl.format(place))
    return out, grid


def main():
    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v3.json"), encoding="utf-8"))
    kept = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    for intent, lines in MOVED.items():
        for x in lines:
            seeds[intent].remove(x)
            seeds["MOVE_TO"].append(x)
    for intent, lines in PLAIN.items():
        seeds[intent] += [x for x in lines if x not in seeds[intent]]
    extra, grid = location_seeds()
    n = 0
    for k, v in extra.items():
        new = [x for x in dict.fromkeys(v) if x not in seeds[k]]
        seeds[k] = seeds[k] + new
        n += len(new)
    seeds["_note_v31"] = (
        f"v31 (make_seeds_v31.py, after the v3 review): the {kept} seeds of the v3 set, with 'get on the roof' and 'go roof' moved from RAPPEL to "
        f"MOVE_TO (spec_v3: going to the roof without a rope word is MOVE_TO); + {sum(map(len, PLAIN.values()))} plain "
        f"NONE callouts ('it's smoked', 'all clear'); + {n} new templated seed commands with map places "
        f"({PER_GROUP} per kind of place per template, drawn from {grid} template x place combinations; the roof in "
        f"every MOVE_TO template; state callouts under NONE)")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v31.json"), "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    total = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"{total} seeds: {kept} of the v3 set, {sum(map(len, PLAIN.values()))} plain callouts, {n} new templated ones "
          f"(drawn from {grid} template x place combinations)")
    clash = {}
    for k, v in seeds.items():
        if not k.startswith("_"):
            for x in v:
                clash.setdefault(x, []).append(k)
    print("the same line under two intents:", {x: ks for x, ks in clash.items() if len(ks) > 1})
    for k, v in extra.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
