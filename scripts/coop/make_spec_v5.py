"""
v5: fire control, a plain "attack", and directions. Written BEFORE any v5 test line exists (then hashed into
frozen.txt, with rule set v4 of the place matcher: locations.json / locations.py / locations_dev.json).

The owner's live test of the v4 bot (2026-10-09) and the decisions taken on it:
  - "open fire", "don't shoot", "stop shooting", "hold fire" had no intent: the bot answered "Noted" and went
    on as before. Two intents are added, OPEN_FIRE and HOLD_FIRE;
  - "attack" split between ENTRY and BREACH and was asked again. The owner wants it to be its own intent: the
    bot only hears "attack", and its planner (the owner's "tool AI") decides whether that is a breach, an
    entry or shooting. One intent is added, ATTACK;
  - "go down by stairs" and "go up by stairs" gave the same record (stairs). The owner wants the direction:
    up, down, left, right, forward, back. It is a fourth field of the target, found by the place matcher's
    rules, not by the classifier; "the left window" and "the door on the left" become object + direction
    instead of unknown_modifier.

Nothing is removed or renamed, so every earlier label stays valid. Each new intent gets its own family: mixing
OPEN_FIRE with HOLD_FIRE is the worst mistake there is, and ATTACK is the owner's "let the planner choose".
"don't shoot" is an order (HOLD_FIRE), not a retraction: the bot's leading-negation guard must let it through
(coop_bot.SAFE, intent_config.json "safe_intents").

Writes:
  blind/spec_v5.json        what the v5 blind authors and annotators see
  intents_v5.json           the model-side vocabulary (phrase label per intent, for the bot's replies)
  seed_commands_v5.json     seed set v31 + canonical commands for the new intents and for orders with a
                            direction; training only, never scored

    python make_spec_v5.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SPEC = {
    "ATTACK": "the bot attacks the enemy, and HOW is left to its planner (push in, breach, or shoot from where it "
              "is): the player only says to attack / engage / take them out and names no way. If the player names "
              "the way, it is that intent instead: pushing into a room is ENTRY, a charge is BREACH, a grenade is "
              "FRAG, opening fire is OPEN_FIRE",
    "OPEN_FIRE": "the bot starts shooting, or is told it is free to shoot (open fire, start shooting, weapons free, "
                 "fire at will, light them up); its planner picks the targets. A place or direction in the line is "
                 "where to shoot",
    "HOLD_FIRE": "the bot stops shooting or must not start (hold fire, cease fire, don't shoot, stop shooting), also "
                 "until something happens ('don't shoot until they come closer'). It is an order even though it is "
                 "phrased as a negation. The bot may keep moving and doing other things: pausing everything is WAIT",
}
CHANGED = {
    "ENTRY": "the bot pushes into the room / site and clears it. A bare 'attack' that names no way is ATTACK",
    "WAIT": "the bot pauses: stop what you are doing, hold up, do not act yet, cancel the last order. Only stopping "
            "the shooting is HOLD_FIRE",
    "NONE": "not an order to the bot: an information callout about enemies, chatter, a question, a complaint, an "
            "order the player explicitly takes back or negates, or an order the bot has no intent for. Exception: "
            "'don't shoot' / 'don't fire' is the order HOLD_FIRE",
}
NEW_MODEL = {
    "ATTACK": {"label": "attack", "description": "attack or engage the enemy; the planner picks how"},
    "OPEN_FIRE": {"label": "open fire", "description": "start shooting, weapons free, fire at will"},
    "HOLD_FIRE": {"label": "hold fire", "description": "stop shooting, cease fire, do not shoot"},
}
FAMILY_NOTE = ("v5 families: v2 families + ATTACK in its own family 'attack', OPEN_FIRE in 'fire' and HOLD_FIRE in "
               "'ceasefire'")

DIRECTIONS = {
    "up": "upwards: 'go up', 'up the stairs', 'look up', 'from above'",
    "down": "downwards: 'go down', 'down the stairs', 'drop down', 'from below'",
    "left": "to the bot's or player's left: 'go left', 'on your left', 'the left window', 'the door on the left', 'nine o'clock'",
    "right": "to the right: 'go right', 'to the right', 'the right door', 'three o'clock'",
    "forward": "ahead: 'move forward', 'push forward', 'straight ahead', 'in front of you', 'twelve o'clock'",
    "back": "behind, backwards: 'go back', 'behind you', 'check your six', 'to the rear'",
}
TARGET = ("the place on the map the BOT must act on for the order's first action -- go to, watch, open, throw at, "
          "shoot at, hide behind... -- as {object, qualifier, zone, direction, unknown_modifier}. object: one of the "
          "map's objects or null; qualifier: one of the map's qualifiers or null (also when the player named it "
          "without saying the object, e.g. 'push main' = door / main, 'take blue' = stairs / blue; a bare compass "
          "word with no object is qualifier only); zone: the floor the place is on, or the floor itself when the "
          "order is about the floor, else null. direction: up | down | left | right | forward | back when the line "
          "gives the bot's action a direction, with or without an object ('go left' = direction left only; 'go down "
          "the stairs' = stairs + down; 'the door on the left' = door + left; 'check behind you' = back), else "
          "null. A direction that describes the object is that object's: 'the door behind you' = door + back, "
          "'the window above you' = window + up. If the line gives both the side that tells WHICH object it is "
          "and a direction of movement, give the side: 'go up the stairs on the left' = stairs + left. A word that only belongs to a fixed phrase is NOT a direction: 'fall back' and 'back up' "
          "(retreat), 'hold up', 'move up' and 'push up' (advance), 'get down' (take cover), 'two left' (remaining), "
          "'right now', 'go ahead' (permission). 'upstairs' / 'downstairs' stay the zones up / down, with no "
          "direction. The target is NOT the player's own position, NOT where the enemy is and NOT the place to "
          "leave: 'I'll take the north door, you take the south window' -> window / south; 'I'll go left, you go "
          "right' -> direction right. unknown_modifier: true when the player singles out one particular object "
          "with a word that is neither a map name nor a direction ('the back door', 'the side door', 'the blue "
          "door', 'the second window', 'the stairs at the back': 'back', 'rear' and 'side' said of an object name "
          "a part of the building, not a direction); then give the object and leave the qualifier null. 'the left window' is "
          "NOT unknown_modifier any more: window + direction left. For a callout or chatter (intent NONE) give "
          "the place or direction the line is about, if it names one ('two on the left' = direction left). All "
          "are null / false when the line names no place of the map and no direction (a marker, 'here', 'there', "
          "'that wall').")

# canonical short commands for the new intents, written by the developer before any v5 test line existed
# (like the earlier seeds: training only, never scored)
NEW_SEEDS = {
    "ATTACK": ["attack", "attack them", "engage", "engage them", "take them out", "attack the enemy", "go get them",
               "take him out", "engage the enemy", "attack that guy", "kill them", "get them"],
    "OPEN_FIRE": ["open fire", "fire", "start shooting", "shoot", "shoot them", "weapons free", "fire at will",
                  "light them up", "start firing", "shoot him", "fire on them", "you can shoot"],
    "HOLD_FIRE": ["hold fire", "hold your fire", "cease fire", "stop shooting", "don't shoot", "do not shoot",
                  "stop firing", "don't fire", "no shooting", "weapons tight", "don't open fire", "quit shooting"],
}
NEW_NEGATED = {"NONE": ["don't attack", "do not attack", "don't engage", "never attack"],
               "WAIT": ["don't attack yet", "don't engage yet"]}

# orders with a place: the new intents meet the map's names (as make_seeds_v31.py does for the others)
DOOR = [f"the {q} door" for q in ("main", "north", "south", "west", "east")]
WINDOW = [f"the {q} window" for q in ("north", "south", "west", "east")]
STAIRS = [f"{c} stairs" for c in ("blue", "red", "yellow", "white", "brown")]
ZONE = ["the basement", "the first floor", "the top floor", "the roof"]
PLACED = {
    "ATTACK": [("attack {}", [DOOR[0], STAIRS[1], ZONE[0], ZONE[2]]), ("engage at {}", [WINDOW[1], STAIRS[0]])],
    "OPEN_FIRE": [("fire on {}", [DOOR[1], WINDOW[2], STAIRS[2]]), ("shoot at {}", [WINDOW[0], DOOR[3], ZONE[3]]),
                  ("open fire on {}", [STAIRS[3], DOOR[0]])],
    "HOLD_FIRE": [("don't shoot at {}", [DOOR[2], WINDOW[3]]), ("hold fire on {}", [STAIRS[4], ZONE[1]])],
}
# orders, callouts and negations with a direction: the classifier must keep its intent when a direction is said
DIRECTED = {
    "MOVE_TO": ["go left", "go right", "move left", "move right", "go up the stairs", "go down the stairs",
                "go up by stairs", "go down by stairs", "head up", "head down", "go back", "move forward",
                "go forward", "go to the left", "go to the right", "take the stairs up", "take the stairs down",
                "go through the door on the left", "go to the right window"],
    "HOLD_ANGLE": ["watch left", "watch right", "watch the left side", "cover the right side", "watch above",
                   "watch behind us", "hold the left window", "watch the door on the right", "eyes left",
                   "watch the stairs below"],
    "FLANK": ["flank left", "flank right", "go around the left", "flank from the right", "go around the back"],
    "OPEN": ["open the left window", "open the door on the right"],
    "SMOKE": ["smoke left", "smoke the right side", "smoke the door on the left"],
    "FLASH": ["flash left", "flash the right window"],
    "FRAG": ["frag left", "nade the right side"],
    "OPEN_FIRE": ["fire left", "shoot right", "open fire on the left", "shoot up", "fire on the right window",
                  "shoot behind you"],
    "ATTACK": ["attack left", "attack from the right", "attack the left side"],
    "HOLD_FIRE": ["don't shoot left", "hold fire on the right"],
    "NONE": ["two on the left", "one on the right", "he's behind you", "enemy above", "they're below us",
             "contact left", "contact right", "one more on your left", "he's on your right", "two left",
             "shots from the left", "don't go left", "don't go up", "don't shoot me"],
}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v3.json"), encoding="utf-8"))
    for k, v in CHANGED.items():
        assert k in spec["intents"], k
        spec["intents"][k] = v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_SPEC)
    spec["intents"]["NONE"] = none                      # NONE stays the last intent, as in every earlier spec
    spec["map"]["directions"] = DIRECTIONS
    spec["modifiers"]["target"] = TARGET
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v2.json"), encoding="utf-8"))
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model["_note_v5"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v31.json"), encoding="utf-8"))
    extra = {}
    for src in (NEW_SEEDS, NEW_NEGATED, DIRECTED):
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
                seeds.setdefault(k, []).append(t)
                owner[t] = k
                added += 1
    seeds["_note_v5"] = ("v5 (make_spec_v5.py, before any v5 test line existed): seed set v31 + canonical commands for "
                         "ATTACK, OPEN_FIRE and HOLD_FIRE, with places and negations, + orders and callouts with a "
                         f"direction: {added} new seeds over {len(extra)} intents")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v5: {len(spec['intents'])} intents (last: {list(spec['intents'])[-4:]}); intents_v5: "
          f"{len([k for k in model if not k.startswith('_')])}; seeds v5: {n} (+{added})")


if __name__ == "__main__":
    main()
