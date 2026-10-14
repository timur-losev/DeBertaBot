"""
v55: the car, items to fetch, saying it again, negated orders and "wait here", after the owner's play with bot v54 and the
chain in Lyra. Written BEFORE any v55 test line exists (then hashed into frozen.txt).

The owner played bot v54 with its language model in the game on 2026-10-13 and 14 and asked (2026-10-14, his words in quotes,
answers to the developer's questions in brackets):
  - "wait here не распознаётся, а stay here без проблем": waiting at a place is staying there (HOLD_POSITION);
  - "...on my go всегда STT в on my goal": "on my goal" is the signal (the timing rule takes "goal"; seeds teach it);
  - "надо научить его искать ammo и weapon, go find ammo. Пока что go find ammo SST в go find armor или go find amor":
    [MOVE_TO with places ammo / weapon / health: the bot goes to the nearest dispenser of it and picks up by walking through;
    "armor" / "amor" heard there is ammo];
  - "go into the car, get into the car - новый интент или MOVE_TO, place = car": [a new intent, GET_IN, with GET_OUT];
  - "try again - Должно повторить предыдущую команду или только невыполненную часть";
  - "бот не понимает don't, don't move, don't shoot и тд": ["don't" + an order is WAIT: the bot stops and waits; "don't shoot"
    stays HOLD_FIRE, "don't move" stays HOLD_POSITION].
The developer's choices, told to the owner, not confirmed: REPEAT is a new intent the game carries out (it knows what failed:
the refused order and the rest of its line, else the last order); "more" said after an order is REPEAT; GET_IN and GET_OUT are
two families, so the gate never adds getting in to getting out; REPEAT is a family of its own.

Not new intents: items and the car are places (locations.json version 6: objects car, ammo, weapon, health).

NOT blind, unlike the lines: the seeds below were written with the owner's log of 2026-10-14 on the table.

Writes:
  blind/spec_v55.json       what the v55 blind authors and annotators see
  intents_v55.json          the model-side vocabulary (44 intents)
  seed_commands_v55.json    seed set v54 (ids unchanged) + the seeds below; _relabel_v55 moves the negated seeds to WAIT
  annot/v55/relabel_v55.json   the authored lines (v1 to v54) that start with a negation and were NONE or NO: now WAIT

    python make_spec_v55.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SPEC = {
    "GET_IN": "the bot gets into a vehicle: a car, a truck (get in the car, get into the car, go into the car, hop in, jump in "
              "the car, get in the truck, get in the vehicle, take the car). It takes a free seat, the driver's when that is the "
              "only one. Going into a room, a box, a vent or a building is MOVE_TO; through a window is VAULT_WINDOW; going TO "
              "the car without getting in ('go to the car', 'run to the truck') is MOVE_TO",
    "GET_OUT": "the bot gets out of the vehicle it is in (get out of the car, hop out, jump out of the car, exit the vehicle, "
               "leave the car, out of the truck). A bare 'get out' or 'get out of there' with no vehicle is FALL_BACK",
    "REPEAT": "the bot does again what it was told last, or the part of it that it could not do (try again, again, do it again, "
              "one more time, once more, repeat that, same again, go again, more, give it another go). An order said again "
              "with its own words is that order ('shoot again' is OPEN_FIRE, 'frag it again' is FRAG); 'one more on your left' "
              "is a callout (NONE)",
}
APPENDED = {
    "WAIT": ". A negated order is this intent: the bot stops and waits ('don't breach', 'don't follow me', 'don't go there', "
            "'don't jump down', 'no need to check'). Only 'don't shoot' / 'don't fire' is HOLD_FIRE and 'don't move' is "
            "HOLD_POSITION. Waiting at a place ('wait here', 'wait there', 'wait at the door') is HOLD_POSITION",
    "HOLD_POSITION": ". Waiting at a place is staying there: 'wait here', 'wait there', 'wait right here', 'wait for me here', "
                     "'wait at the north door' are this intent; a bare 'wait' or 'wait for it' is WAIT. 'Don't move' is this "
                     "intent too",
    "MOVE_TO": ". Going to get an item is this intent, and the item is the place: 'go find ammo', 'get some ammo', 'grab a "
               "gun', 'find a weapon', 'pick up that rifle', 'go get health' (the nearest place that gives it). Going to a car is "
               "this intent ('go to the car'); getting into it is GET_IN",
    "FALL_BACK": ". Getting out of a vehicle ('get out of the car', 'hop out') is GET_OUT; a bare 'get out' is this intent",
    "VAULT_WINDOW": ". 'Hop in' / 'jump in' with no window named is GET_IN (a vehicle)",
    "JUMP": ". Jumping into a vehicle ('jump in the car') is GET_IN",
}
# whole phrases of the v54 text that change; each must be there exactly once
REPLACED = {
    "NO": ("a negated order is NONE ('don't breach')", "a negated order is WAIT ('don't breach')"),
    "NONE": ("an order the player explicitly takes back or negates, or an order the bot has no intent for. Exception: 'don't "
             "shoot' / 'don't fire' is the order HOLD_FIRE.",
             "or an order the bot has no intent for. A negated order is WAIT ('don't breach'); 'don't shoot' / 'don't fire' is "
             "the order HOLD_FIRE and 'don't move' is HOLD_POSITION."),
}
TIMING_ADD = (" 'On my goal' is 'on my go' misheard: a signal")
TARGET_ADD = (" For GET_IN / GET_OUT the target is the vehicle (object 'car') if the line names one; for REPEAT all null. An "
              "item to get is the target of MOVE_TO: object ammo, weapon or health ('go find ammo' = ammo; 'grab a rifle' = "
              "weapon; 'go get health' = health); 'armor' or 'amor' heard where ammo is meant is ammo.")
MAP_OBJECTS = {
    "car": "a car, a truck, a vehicle (a car can be driven; it is also cover)",
    "ammo": "ammunition: where the bot can pick some up",
    "weapon": "a weapon: a gun, a rifle, a pistol, a shotgun lying or spawning somewhere",
    "health": "health: a medkit, a health pack",
}
NEW_MODEL = {
    "GET_IN": {"label": "get in the vehicle", "description": "get into a car or another vehicle"},
    "GET_OUT": {"label": "get out of the vehicle", "description": "get out of the car the bot is in"},
    "REPEAT": {"label": "do it again", "description": "repeat the last order, or the part of it that was not done"},
}
FAMILY_NOTE = ("v55 families: v54 families + GET_IN in 'get_in', GET_OUT in 'get_out' (never summed), REPEAT in 'repeat'")

NEW_SEEDS = {
    "GET_IN": ["get in the car", "get into the car", "go into the car", "hop in", "hop in the car", "jump in the car",
               "get in the truck", "get into the truck", "get in the vehicle", "get into the vehicle", "take the car",
               "get in the driver's seat", "hop in the truck", "climb into the car", "get inside the car", "jump in",
               "get in that car", "go get in the car", "in the car now", "everybody in the car", "get in the jeep",
               "get in the car at my pin", "get in the car by the north door", "hop in that truck", "jump in the truck",
               "get in my car", "get back in the car", "get in the car quick", "into the car", "take that car"],
    "GET_OUT": ["get out of the car", "hop out", "hop out of the car", "jump out of the car", "exit the vehicle", "exit the car",
                "leave the car", "get out of the vehicle", "out of the car", "bail out of the car", "get out of the truck",
                "step out of the car", "hop out of the truck", "jump out", "get out of the car now", "out of the truck",
                "leave the vehicle", "hop out of the vehicle", "exit the truck", "climb out of the car"],
    "REPEAT": ["try again", "again", "do it again", "one more time", "once more", "repeat that", "repeat", "more",
               "same again", "go again", "do that again", "try that again", "try it again", "give it another go",
               "again please", "more more more", "do it one more time", "redo it", "try once more", "one more time please",
               "again again", "same thing again", "do the same again", "repeat the last order", "keep doing that",
               "more of that", "go on again", "try that one more time", "have another go", "try one more time"],
    # waiting at a place is staying there (the owner: "wait here" was not understood, "stay here" was)
    "HOLD_POSITION": ["wait here", "wait there", "wait right here", "wait right there", "wait over there", "wait for me here",
                      "wait me here", "wait here for me", "just wait here", "wait here a sec", "wait at the north door",
                      "wait by the stairs", "wait at my pin", "wait on the roof", "wait in this room", "you wait here",
                      "wait there for me", "stay and wait here", "wait at the car", "wait over by the table"],
    # an item to fetch: the item is the place; "armor" / "amor" are what the recognizer made of "ammo" for the owner
    "MOVE_TO": ["go find ammo", "find ammo", "find some ammo", "get some ammo", "grab some ammo", "go get ammo",
                "find some ammunition", "go grab ammo", "pick up ammo", "go find armor", "find some armor", "go find amor",
                "get some armor", "grab some amor", "find a weapon", "go find a gun", "grab a gun", "get a weapon",
                "pick up a rifle", "grab that rifle", "pick up that gun", "go get a shotgun", "find a better gun",
                "get a new weapon", "grab a pistol", "go find a weapon", "find a rifle", "go get health", "find a medkit",
                "grab a health pack", "go find health", "get some health", "pick up the medkit", "go heal up",
                "go to the car", "run to the car", "move to the truck", "go to that car", "get to the car"],
    # negated orders not yet among the seeds; the 72 negated NONE seeds move to WAIT by _relabel_v55
    "WAIT": ["don't", "don't do that", "don't do it", "don't go there", "don't go in there", "do not jump down",
             "don't throw it", "don't get in the car", "don't pick that up", "do not go upstairs", "don't come closer",
             "stop following me", "don't follow", "no don't", "don't open it yet", "never mind don't go", "don't run",
             "don't push yet", "don't drop down", "no need to go"],
    # "don't move" is HOLD_POSITION, "don't shoot" HOLD_FIRE (the owner: they must keep working)
    "HOLD_FIRE": ["don't shoot me", "don't fire at me", "don't shoot him", "do not shoot now"],
    "FOLLOW_ME": ["run to me", "come to me", "come closer to me", "come closer"],
}
ON_SIGNAL = {"BREACH": ["breach on my goal", "breach it on my goal"], "GO_NOW": ["go on my goal"],
             "SMOKE": ["smoke the door on my goal"], "FLASH": ["flash on my goal"], "MOVE_TO": ["go to the stairs on my goal"],
             "GET_IN": ["get in the car on my go", "get in the car when i say"], "GET_OUT": ["get out of the car on my go"],
             "REPEAT": ["try again on my go"]}
# AFTER TUNING (2026-10-14, after the v55 ensemble was trained and probed with the owner's own lines; logged in frozen.txt):
# a place with "to" in front and no verb is going there. v55 read the owner's "To this wall." as RAPPEL 0.70 and acted on
# it ("to that wall", "to the left wall" the same); v54 had read MOVE_TO 0.59 and asked again. With a context the router
# sends such a line to the decoder, which makes it the earlier order at that place (chains3_v55.py)
FRAGMENTS_TO = {"MOVE_TO": ["to this wall", "to that wall", "to the wall", "to the left wall", "to the back wall", "to the far wall",
                            "to this corner", "to that corner", "to the corner", "to this spot", "to that spot", "to the right wall"]}
# the negated seeds that are not WAIT under v55
NEGATED_TO = {"don't shoot me": "HOLD_FIRE"}


def main():
    sys.path.insert(0, HERE)
    os.environ["COOP_TAG"] = "v54"
    import coop_bot
    neg = coop_bot.NEGATION

    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v54.json"), encoding="utf-8"))
    for k, (old, new) in REPLACED.items():
        assert spec["intents"][k].count(old) == 1, (k, old)
        spec["intents"][k] = spec["intents"][k].replace(old, new)
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_SPEC)
    spec["intents"]["NONE"] = none                      # NONE stays the last intent, as in every earlier spec
    spec["modifiers"]["timing"] += TIMING_ADD
    spec["modifiers"]["target"] += TARGET_ADD
    spec["map"]["objects"].update(MAP_OBJECTS)
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v55.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v54.json"), encoding="utf-8"))
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model["_note_v55"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v55.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v54.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v54"])               # the earlier relabelled seeds stay relabelled
    moved = {}
    for k, v in seeds.items():
        if k.startswith("_"):
            continue
        for n, t in enumerate(v):
            sid = f"seed_{k}_{n}"
            if relabel.get(sid, k) == "NONE" and neg.search(t):
                relabel[sid] = NEGATED_TO.get(t, "WAIT")   # the seed stays where it is: its id and its audio stay valid
                moved[t] = relabel[sid]
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    extra = {}
    for src in (NEW_SEEDS, ON_SIGNAL, FRAGMENTS_TO):
        for k, v in src.items():
            extra.setdefault(k, []).extend(v)
    added, had = 0, []
    for k, v in extra.items():
        assert len(v) == len(set(v)), (k, [t for t in v if v.count(t) > 1])
        for t in v:
            assert owner.get(t, k) == k, f"{t!r} is already a {owner[t]} seed, cannot also be {k}"
            if t in owner:
                had.append(t)
            else:
                seeds.setdefault(k, []).append(t)       # appended: every earlier seed keeps its id (seed_<INTENT>_<n>)
                owner[t] = k
                added += 1
    seeds["_relabel_v55"] = relabel
    seeds["_note_v55"] = ("v55 (make_spec_v55.py, before any v55 test line existed, but with the owner's log of 2026-10-14 on "
                          "the table): seed set v54 + commands for GET_IN, GET_OUT and REPEAT; waiting at a place under "
                          "HOLD_POSITION; items to fetch and going to a car under MOVE_TO; negated orders under WAIT; 'on my "
                          f"goal' as the signal: {added} new seeds over {len(extra)} intents. _relabel_v55: _relabel_v54 + the "
                          f"{len(moved)} seeds that start with a negation and were NONE (WAIT; 'don't shoot me' HOLD_FIRE)")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v55.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # the authored lines: a line of v1 to v54 whose reading is NONE or NO and that starts with a negation is WAIT now
    import coop_v2
    items = coop_v2.load_items()
    lines = {it["id"]: {"from": it["maj"], "to": "WAIT", "text": it["text"]} for it in items
             if it["maj"] in ("NONE", "NO") and neg.search(it["text"])}
    os.makedirs(os.path.join(HERE, "annot", "v55"), exist_ok=True)
    json.dump({"_note": "make_spec_v55.py: the authored lines (v1 to v54) whose majority reading is NONE or NO and that start "
                        "with a negation (coop_bot.NEGATION): a negated order is WAIT under spec v55. A rule, not a re-reading: "
                        "the developer read the list before freezing it", "lines": lines},
              io.open(os.path.join(HERE, "annot", "v55", "relabel_v55.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v55: {len(spec['intents'])} intents (last: {list(spec['intents'])[-5:]}); intents_v55: "
          f"{len([k for k in model if not k.startswith('_')])}; seeds v55: {n} (+{added}); seeds moved: {len(moved)} "
          f"({sum(1 for v in moved.values() if v == 'WAIT')} to WAIT); already seeds: {had}")
    print({k: len(seeds[k]) for k in NEW_SPEC})
    print(f"authored lines relabelled: {len(lines)} ({sum(1 for v in lines.values() if v['from'] == 'NO')} from NO)")


if __name__ == "__main__":
    main()
