"""
v52: HELP, CHECK and SUPPRESS, after the owner's first test with a real voice. Written BEFORE any v52 test line
exists (then hashed into frozen.txt).

The owner talked to bot v51 through the C++ voice chat on 2026-10-09 (43 utterances, kept with the readings he
asked for in owner_voice_20261009.json) and asked for three things:
  - "REVIVE is used too broadly -- a label HELP is needed": "Help me here." was REVIVE_ME 1.00;
  - "'Check' something must be recognized as Check!": "Check that room." was asked again (ENTRY 0.43 / DRONE
    0.32), "Check the room in front of us." was DRONE;
  - "Suppressive fire and Suppress are frequent military jargon, they must be recognized": "Suppressive fire."
    was HOLD_FIRE 0.98 -- the opposite order -- and "Suppress them." was DEFUSE.
The same session showed weak refusals of things the bot has no order for ("Kiss me." 0.58 under a 0.62
threshold, "Be silent." acted on as HOLD_FIRE) and "Sneak into that room." acted on as VAULT_WINDOW.

Three intents are added:
  HELP       the player asks for help without saying with what; the planner works it out. Its own family:
             the point of the request is that it is not a revive.
  CHECK      the bot checks a place or thing itself. Its own family: mistaking it for DRONE or ENTRY is the
             complaint. The line between the looking intents is the verb again: check / inspect / make sure
             is CHECK, look / face is LOOK_AT, watch / hold / cover is HOLD_ANGLE, a drone or scouting is DRONE.
  SUPPRESS   suppressive or covering fire. In the family "fire" with OPEN_FIRE (the developer's choice: a
             planner that does not tell them apart treats both as firing; mistaking either for HOLD_FIRE stays
             a wrong-family error).
Nothing is removed or renamed. One seed changes its label and keeps its id ("help me": REVIVE_ME -> HELP,
"_relabel_v52"); every other earlier seed keeps id and label.

NOT blind, unlike the lines: the seeds below were written with the owner's 43 utterances on the table, and
some are near copies of them (as seed set v21 was written for his "cover from behind").

Writes:
  blind/spec_v52.json       what the v52 blind authors and annotators see
  intents_v52.json          the model-side vocabulary (32 intents)
  seed_commands_v52.json    seed set v51 (ids unchanged) + seeds for the three intents, their negations, orders
                            the bot has no intent for (NONE), and quiet moves (MOVE_TO)

    python make_spec_v52.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SPEC = {
    "HELP": "the player asks the bot for help and does not say with what (help me, help me here, I need a hand, I need "
            "backup here). The bot comes to the player and its planner works out what is needed. If the player says "
            "what they need, it is that intent: being revived or picked up when down is REVIVE_ME ('help me up', "
            "'help, I'm down'), being covered is COVER_ME, being followed is FOLLOW_ME",
    "CHECK": "the bot checks a place or a thing itself: goes and looks whether it is clear or what is there, and how is "
             "left to its planner (check that room, check the basement, check behind the sofa, check your six, see if "
             "it's clear, make sure nobody is in there). With a drone or another gadget it is DRONE; pushing in to "
             "clear the room by force is ENTRY; only turning to look is LOOK_AT; keeping it covered is HOLD_ANGLE",
    "SUPPRESS": "the bot lays down suppressive fire: keeps shooting at a place or at the enemy to pin them down, not to "
                "pick targets (suppress, suppressive fire, suppress them, covering fire, pin them down, keep their heads "
                "down). A plain order to start shooting is OPEN_FIRE; watching over the player without the order to "
                "shoot is COVER_ME",
}
CHANGED = {
    "REVIVE_ME": "the bot comes to revive the downed player (revive me, I'm down, pick me up, help me up). A plain 'help "
                 "me' that does not say the player is down is HELP",
    "DRONE": "the bot sends a drone or another gadget, or scouts ahead, to gather intel before anyone goes in. 'Check that "
             "room' with no drone and no scouting word is CHECK",
    "ENTRY": "the bot pushes into the room / site and clears it. A bare 'attack' that names no way is ATTACK; 'check the "
             "room' is CHECK",
}
# sentences of the v51 spec that the new intents make false
REWORDED = {
    "LOOK_AT": ("going somewhere to check it out is DRONE", "checking a place or a side ('check that room', 'check your six') is CHECK"),
}
APPENDED = {
    "OPEN_FIRE": ". Suppressive or covering fire is SUPPRESS",
    "COVER_ME": ". 'Covering fire' and 'suppressing fire' are SUPPRESS",
}
TARGET_ADD = (" For CHECK the target is what to check ('check the room in front of us' = direction forward, 'check your "
              "six' = direction back); for SUPPRESS where to fire; for HELP it is the player: all null.")
NEW_MODEL = {
    "HELP": {"label": "help you", "description": "come and help the player; the planner works out with what"},
    "CHECK": {"label": "check it", "description": "go and check a place or a thing: is it clear, what is there"},
    "SUPPRESS": {"label": "suppress", "description": "suppressive or covering fire: keep shooting to pin the enemy down"},
}
FAMILY_NOTE = "v52 families: v51 families + HELP in 'help', CHECK in 'check', SUPPRESS in 'fire' with OPEN_FIRE"
RELABEL = {"help me": ("REVIVE_ME", "HELP")}

NEW_SEEDS = {
    "HELP": ["help", "help me here", "i need help", "i need help here", "give me a hand", "need a hand here", "come help me",
             "help me out", "i need backup", "need backup here", "assist me", "i need assistance", "can you help me",
             "help me with this", "get over here and help", "somebody help me", "a little help here",
             "i could use some help", "help me out here", "come give me a hand"],
    "REVIVE_ME": ["help me up", "help me up i'm down", "get me up", "pick me up i'm down"],
    "CHECK": ["check", "check it", "check that", "check it out", "check that room", "check the room", "check this room",
              "go check it", "go check that", "check there", "check over there", "check if it's clear", "see if it's clear",
              "make sure it's clear", "check the area", "check that corner", "check the corners", "check inside",
              "go check inside", "inspect that room", "check behind that", "check that spot", "check around",
              "make sure nobody is in there", "go see if anyone is there", "check that for me"],
    "SUPPRESS": ["suppress", "suppress them", "suppressive fire", "suppressing fire", "suppress him", "lay down suppressive fire",
                 "lay down suppressing fire", "covering fire", "give me covering fire", "give me suppressive fire",
                 "pin them down", "keep them pinned", "keep their heads down", "lay down fire", "put fire on them",
                 "suppress the enemy", "suppress that position", "suppress that", "keep them suppressed", "suppress that guy",
                 "i need suppressing fire", "suppression"],
    # the bot has no order for these: it must say so, not pick the nearest one
    "NONE": ["kiss me", "you're stupid", "be quiet", "be silent", "shut up", "stay quiet", "keep quiet", "sing a song", "dance",
             "tell me a joke", "are you talking to me", "hey i'm talking to you", "can you hear me", "can you see me",
             "where are my shoes", "where is my gun", "what's your name", "how are you", "you're useless", "good job",
             "nice shot", "thank you", "sit down", "wave at me", "say something", "what are you doing", "i'm bored",
             "you idiot", "love you", "hello", "hi there", "who are you", "hi are you talking to me", "be nice"],
    "MOVE_TO": ["sneak into that room", "sneak in there", "sneak over there", "sneak to the door", "move quietly to the door",
                "quietly go to the stairs"],
}
NEW_NEGATED = {"NONE": ["don't help me", "i don't need help", "no need to help", "don't check it", "don't check that room",
                        "no need to check", "don't suppress", "no suppressive fire"],
               "WAIT": ["don't check yet", "don't suppress yet"],
               "HOLD_FIRE": ["stop suppressing", "cease suppressive fire"]}
ON_SIGNAL = {"CHECK": ["check the room on my go", "check it when i say"], "SUPPRESS": ["suppress on my go", "covering fire when i say"]}
DOOR = [f"the {q} door" for q in ("main", "north", "south", "west", "east")]
WINDOW = [f"the {q} window" for q in ("north", "south", "west", "east")]
STAIRS = [f"{c} stairs" for c in ("blue", "red", "yellow", "white", "brown")]
ZONE = ["the basement", "the first floor", "the top floor", "the roof"]
PLACED = {
    "CHECK": [("check {}", [DOOR[0], DOOR[1], WINDOW[2], STAIRS[0], STAIRS[3], ZONE[0], ZONE[2], ZONE[3], "the stairs", "that door", "that window"]),
              ("go check {}", [DOOR[3], WINDOW[0], STAIRS[1], ZONE[1]]),
              ("check behind {}", ["the sofa", "the table"]),
              ("check if {} is clear", [ZONE[0], ZONE[3], STAIRS[2]]),
              ("make sure {} is clear", [ZONE[2], DOOR[4]])],
    "SUPPRESS": [("suppress {}", [WINDOW[0], WINDOW[3], DOOR[0], STAIRS[4], ZONE[3]]),
                 ("suppressive fire on {}", [DOOR[2], WINDOW[1], STAIRS[1]]),
                 ("covering fire on {}", [DOOR[1], WINDOW[2]]),
                 ("pin them down at {}", [STAIRS[0], DOOR[4]])],
}
DIRECTED = {
    "CHECK": ["check left", "check right", "check your six", "check behind you", "check above", "check the left side",
              "check the room in front of you", "check the door on the left", "check up the stairs", "check behind us",
              "check your left", "check upstairs", "check downstairs", "check the room in front of us"],
    "SUPPRESS": ["suppress left", "suppress the right side", "suppressive fire on the left", "suppress the window on the right",
                 "covering fire to the right"],
}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v51.json"), encoding="utf-8"))
    for k, v in CHANGED.items():
        assert k in spec["intents"], k
        spec["intents"][k] = v
    for k, (old, new) in REWORDED.items():
        assert spec["intents"][k].count(old) == 1, k
        spec["intents"][k] = spec["intents"][k].replace(old, new)
    for k, v in APPENDED.items():
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_SPEC)
    spec["intents"]["NONE"] = none                      # NONE stays the last intent, as in every earlier spec
    spec["modifiers"]["target"] += TARGET_ADD
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v52.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v51.json"), encoding="utf-8"))
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model["_note_v52"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v52.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v51.json"), encoding="utf-8"))
    relabel = {}
    for text, (old, new) in RELABEL.items():
        relabel[f"seed_{old}_{seeds[old].index(text)}"] = new    # the seed stays where it is: its id and its audio stay valid
    extra = {}
    for src in (NEW_SEEDS, NEW_NEGATED, DIRECTED, ON_SIGNAL):
        for k, v in src.items():
            extra.setdefault(k, []).extend(v)
    for k, templates in PLACED.items():
        for tpl, places in templates:
            extra[k].extend(tpl.format(p) for p in places)
    owner = {t: k for k, v in seeds.items() if not k.startswith("_") for t in v}
    owner.update({t: new for t, (_, new) in RELABEL.items()})
    added = 0
    for k, v in extra.items():
        for t in v:
            assert owner.get(t, k) == k, f"{t!r} is already a {owner[t]} seed, cannot also be {k}"
            if t not in owner:
                seeds.setdefault(k, []).append(t)       # appended: every earlier seed keeps its id (seed_<INTENT>_<n>)
                owner[t] = k
                added += 1
    seeds["_relabel_v52"] = relabel
    seeds["_note_v52"] = ("v52 (make_spec_v52.py, before any v52 test line existed, but with the owner's 43 spoken lines of "
                          "2026-10-09 on the table): seed set v51 + commands for HELP, CHECK and SUPPRESS (plain, with places, "
                          "with directions, negated), things the bot has no order for under NONE, quiet moves under MOVE_TO: "
                          f"{added} new seeds over {len(extra)} intents. _relabel_v52: seeds that keep their id and position "
                          "but carry another label under COOP_TAG=v52 (coop_v2.seed_items)")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v52.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v52: {len(spec['intents'])} intents (last: {list(spec['intents'])[-4:]}); intents_v52: "
          f"{len([k for k in model if not k.startswith('_')])}; seeds v52: {n} (+{added}); relabelled {relabel}; "
          f"HELP {len(seeds['HELP'])}, CHECK {len(seeds['CHECK'])}, SUPPRESS {len(seeds['SUPPRESS'])}")


if __name__ == "__main__":
    main()
