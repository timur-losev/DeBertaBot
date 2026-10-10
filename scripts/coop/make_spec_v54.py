"""
v54: the player's pin, answers to the bot's questions, COME_BACK and stance, after the owner's test of bot v53 with a real
voice. Written BEFORE any v54 test line exists (then hashed into frozen.txt).

The owner talked to bot v53 on 2026-10-09 and decided the following (2026-10-09 and 10; his words in quotes):
  - the game will point at places with a 3D pin a lot, and the bot must understand that the player points at a place:
    "Stay at my pin." was HOLD_POSITION with no place at all (the bot stayed where it stood), "Stay on my mark." and
    "check at my mark" were read as "wait for my go". "Mark - пин": "mark" is the pin, not the signal;
  - "there must be a classification Yes, No, Maybe, I don't know", so that the planner can ask back and understand
    the reply; "affirmative" and "negative" are yes and no;
  - "Come back" is a label of its own, "Return back" goes there too;
  - stance orders ("lie down", "crouch") are needed;
  - "Go inside", "get inside" is just walking or climbing in -- into a box, a vent -- with no clearing.
The developer's analysis of that log (not the owner's words): "Jump left." got no direction, "Come back." was asked
again and "Return back." was FALL_BACK 0.99, "go inside" split between MOVE_TO and ENTRY and was asked again.

Eight intents are added:
  COME_BACK                 the bot comes back -- to the player or to where it was, the planner decides. Family "move".
  CROUCH, PRONE, STAND_UP   posture on the spot; one family "stance" (the developer's choice: three labels, because
                            the posture is the whole order). "sit down" is CROUCH: a seed changes its label.
  YES, NO                   the player's answer to the bot's question; a family each, so that the family gate never
                            adds a yes to a no.
  MAYBE, DONT_KNOW          the two unsure answers, one family "unsure" (the developer's choice).
Not new intents: the pin is not an intent but a reference -- the place matcher reports it (rule set v5, "pointer"),
and the spec's `reference` gets the value "pin"; "go inside" is MOVE_TO (the seed "go in" moves there from ENTRY).
The developer's choices, to be confirmed: "roger" / "copy" only acknowledge (NONE); "up to you" is MAYBE; "okay" as a
bare answer is YES; "stay at my pin" is HOLD_POSITION with the pin as its place.
Also here: the three faults of bot v53 found by probe_v53_new.log ("check the fire escape", the reversed "i'll watch
the other door you stay on this one", "drop in through the hatch").

NOT blind, unlike the lines: the seeds below were written with the owner's lines and the probes on the table.

Writes:
  blind/spec_v54.json       what the v54 blind authors and annotators see
  intents_v54.json          the model-side vocabulary (41 intents)
  seed_commands_v54.json    seed set v53 (ids unchanged) + the seeds below

    python make_spec_v54.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SPEC = {
    "COME_BACK": "the bot comes back: returns to the player or to where it was before, and which of the two is left to its "
                 "planner (come back, come back here, return, return back, get back here, return to your position, regroup). "
                 "Retreating from a fight is FALL_BACK ('fall back', 'pull back', 'get back'); coming to the player or staying "
                 "with them is FOLLOW_ME ('come here', 'on me', 'come with me'); going back to a place the line names is "
                 "MOVE_TO ('go back to the stairs')",
    "CROUCH": "the bot crouches or stays low where it is: a change of posture on the spot (crouch, crouch down, get low, stay "
              "low, squat, take a knee, sit down). Getting into cover is TAKE_COVER ('get down', 'duck', 'hide')",
    "PRONE": "the bot lies down flat where it is (lie down, lay down, go prone, get on the ground, on your belly, hit the "
             "deck). 'Lay down fire' is SUPPRESS; getting into cover is TAKE_COVER",
    "STAND_UP": "the bot stands up from crouching or lying (stand up, get up, on your feet, get back up). 'Get me up' / 'help "
                "me up' is REVIVE_ME; 'get up on that' and 'get up there' are JUMP or MOVE_TO; 'stand still', 'stand here' "
                "are HOLD_POSITION",
    "YES": "the player answers yes to something the bot asked, or confirms what the bot said (yes, yeah, yep, affirmative, "
           "correct, that's right, exactly, sure, okay as a bare answer). It is not an order: the bot's planner uses it only "
           "if it asked something. If the line also gives an order, it is that order ('yes, breach it' = BREACH; 'yes, go' "
           "= GO_NOW). 'Roger' / 'copy' / 'got it' only acknowledge and are NONE",
    "NO": "the player answers no, or rejects what the bot said or proposed (no, nope, nah, negative, wrong, not that one, "
          "that's not it). If the line also gives an order, it is that order ('no, hold fire' = HOLD_FIRE; 'no, wait' = "
          "WAIT). Pausing or cancelling an order is WAIT ('stop', 'hold on', 'cancel that', 'never mind'); a negated order "
          "is NONE ('don't breach')",
    "MAYBE": "the player's answer is neither yes nor no: it may be so, or the bot may decide (maybe, perhaps, possibly, could "
             "be, probably, I guess so, up to you, your call)",
    "DONT_KNOW": "the player answers that they do not know (I don't know, no idea, not sure, dunno, can't tell, who knows). "
                 "It is an answer even though it is phrased as a negation",
}
APPENDED = {
    "FOLLOW_ME": ". 'Come back' / 'return' is COME_BACK",
    "MOVE_TO": ". Going or getting inside something with no word about clearing it ('go inside', 'get in there', 'get inside "
               "the box', 'crawl into the vent') is this intent too: the bot just goes in. Coming back with no place named "
               "('come back', 'return') is COME_BACK",
    "HOLD_POSITION": ". With a place or the player's marker the bot goes there and stays: 'stay at my pin', 'stay on my mark', "
                     "'stay over there' are this intent, and the target or the reference says where. Only changing posture is "
                     "CROUCH / PRONE / STAND_UP",
    "FALL_BACK": ". 'Come back' / 'return' with no retreat in the wording is COME_BACK",
    "WAIT": ". A bare 'no' that answers the bot is NO",
    "GO_NOW": ". A bare 'yes' that answers the bot is YES",
    "TAKE_COVER": ". Only changing posture where the bot stands ('crouch', 'lie down', 'go prone') is CROUCH / PRONE",
    "ENTRY": ". Just going or getting inside, with no pushing or clearing in the wording ('go inside', 'get in there'), is "
             "MOVE_TO",
    "JUMP": ". Going, getting or climbing INSIDE something ('get inside the vent', 'climb into the box') is MOVE_TO; jumping "
            "or dropping in is still this intent ('jump into the hole', 'drop in through the hatch')",
    "CHECK": ", but checking a place whose name has the word is this intent ('check the fire escape', 'check the fire exit')",
    "NONE": ". 'Roger' / 'copy' / 'got it' only acknowledge: NONE. What the player answers to the bot's question is YES / NO / "
            "MAYBE / DONT_KNOW",
}
SETTING = ("The human player places markers (pings) on the map", "The human player places markers on the map (a pin, a ping, a mark)")
MODIFIERS = {
    "timing": "now | on_signal -- 'on_signal' when the player says to do it on their call / when they say go / on three; "
              "otherwise 'now'. 'On my mark' / 'at my mark' is NOT a signal: 'mark' is the player's marker on the map (see "
              "reference 'pin'), so 'check at my mark' is 'now'. 'Wait for my mark' is a signal",
    "reference": "pin | this | other | none -- how the line points at the place the BOT must act on. 'pin': the line names the "
                 "player's marker ('my pin', 'the ping', 'my marker', 'on my mark', 'where I marked'). 'this': it points with "
                 "this / that / these / those / here / there ('this wall', 'that window', 'over there', 'check that room'). "
                 "'other': the order is about the OTHER one of two things (the other door, the other window, the other "
                 "angle). 'none': everything else -- a place that is only named ('the east window', 'the stairs') is 'none'. "
                 "If two apply: pin, then other, then this. A pointing word that is about the player's own place or the "
                 "enemy's does not count: 'I'll hold here, you take the north door' is 'none'",
}
TARGET_ADD = (" The player's marker is not a place of the map: 'stay at my pin' has all nulls and reference 'pin'; 'the window "
              "by my ping' = window, reference 'pin'. For COME_BACK the target is the place to come back to, if the line names "
              "one. For CROUCH / PRONE / STAND_UP and for the four answers all null.")
NEW_MODEL = {
    "COME_BACK": {"label": "come back", "description": "come back: to the player or to where the bot was before"},
    "CROUCH": {"label": "crouch", "description": "crouch or stay low on the spot"},
    "PRONE": {"label": "go prone", "description": "lie down flat on the spot"},
    "STAND_UP": {"label": "stand up", "description": "stand up from crouching or lying"},
    "YES": {"label": "say yes", "description": "the player's answer to the bot: yes, affirmative, correct"},
    "NO": {"label": "say no", "description": "the player's answer to the bot: no, negative, not that"},
    "MAYBE": {"label": "say maybe", "description": "the player's answer to the bot: maybe, could be, up to you"},
    "DONT_KNOW": {"label": "say they don't know", "description": "the player's answer to the bot: I don't know, not sure"},
}
FAMILY_NOTE = ("v54 families: v53 families + COME_BACK in 'move'; CROUCH, PRONE and STAND_UP in one family 'stance'; YES in "
               "'yes', NO in 'no' (never summed); MAYBE and DONT_KNOW in one family 'unsure'")
RELABEL = {"sit down": ("NONE", "CROUCH"), "go in": ("ENTRY", "MOVE_TO")}

PINS = ["my pin", "my mark", "the pin", "my marker"]
NEW_SEEDS = {
    "COME_BACK": ["come back", "come back here", "come back to me", "return", "return back", "return to me", "return here",
                  "get back here", "get back over here", "come on back", "back to me", "back here", "return to your position",
                  "go back to your position", "get back to your spot", "go back where you were", "back to your post",
                  "come back now", "come back quick", "return to position", "head back", "head back to me", "regroup",
                  "regroup on me", "rejoin me"],
    "CROUCH": ["crouch", "crouch down", "get low", "stay low", "squat", "squat down", "take a knee", "kneel", "kneel down", "sit",
               "crouch here", "stay crouched", "keep low", "go low", "on one knee", "crouch right there"],
    "PRONE": ["lie down", "lay down", "go prone", "prone", "get prone", "get on the ground", "get on your belly", "on your belly",
              "hit the deck", "hit the dirt", "lie flat", "lay flat", "drop prone", "lie down here", "lay down here",
              "go prone here", "stay prone", "flat on the ground", "get flat"],
    "STAND_UP": ["stand up", "get up", "on your feet", "get on your feet", "stand back up", "get back up", "up on your feet",
                 "stand up now", "you can stand up", "get up now", "stand up straight", "rise"],
    "YES": ["yes", "yeah", "yep", "yup", "yes sir", "affirmative", "that's affirmative", "correct", "that's correct",
            "that's right", "exactly", "sure", "of course", "definitely", "absolutely", "okay", "ok", "yes please",
            "yeah that one", "uh huh", "indeed", "positive", "aye", "yes exactly", "yes that's it", "confirmed", "confirm",
            "that's the one"],
    "NO": ["no", "nope", "nah", "no sir", "negative", "that's a negative", "that's negative", "no way", "not that",
           "not that one", "wrong", "that's wrong", "incorrect", "that's not it", "no not that", "no no", "no no no",
           "not what i meant", "that's not what i said", "nope not that", "not really", "no thanks"],
    "MAYBE": ["maybe", "perhaps", "possibly", "could be", "might be", "probably", "i guess", "i guess so", "i think so",
              "maybe yes", "maybe not", "probably not", "it's possible", "up to you", "your call", "you decide", "either way",
              "whatever you think", "kind of", "sort of"],
    "DONT_KNOW": ["i don't know", "don't know", "i dont know", "dunno", "i dunno", "no idea", "i have no idea", "not sure",
                  "i'm not sure", "im not sure", "who knows", "can't tell", "i can't tell", "hard to say", "no clue",
                  "i have no clue", "beats me", "how should i know", "i couldn't say", "i'm not certain", "not certain"],
    # acknowledgements are not answers; reports of someone's posture or return are not orders
    "NONE": ["roger", "roger that", "copy", "copy that", "got it", "understood", "ten four", "acknowledged", "wilco", "noted",
             "solid copy", "alright then", "he's crouching", "i'm prone", "i'm crouched behind the sofa", "he's lying down",
             "he stood up", "i'll come back", "i'm coming back", "they came back"],
    # going inside, with no clearing: the owner's "just walk or climb in"
    "MOVE_TO": ["go inside", "get inside", "get in", "get in there", "go in there", "go inside there", "get inside there",
                "go into the room", "get into the room", "go inside the room", "get inside the box", "get in the box",
                "climb into the box", "get inside the vent", "get in the vent", "climb into the vent", "crawl into the vent",
                "crawl inside", "get inside that", "go in that room", "walk in", "walk inside", "step inside", "head inside",
                "come inside", "squeeze in there", "get inside the building", "go inside the building",
                # the pin as the place to go
                "go to my pin", "go to my mark", "go to the pin", "go to the mark", "move to my pin", "move to my mark",
                "move to the marker", "get to my pin", "head to my mark", "go where i marked", "go to where i pinged",
                "run to my pin", "move to that pin", "go to my waypoint", "get over to my mark", "yes go there"],
    "ENTRY": ["go in and clear it", "go inside and clear the room", "get in there and clear it", "push inside",
              "push into the room", "enter and clear", "make entry", "storm the room", "push in at my pin", "enter at my mark"],
    # staying at a pointed place: the bot goes there and stays
    "HOLD_POSITION": ["stay at my pin", "stay on my mark", "stay at my mark", "stay at my marker", "stay at the pin",
                      "stay on my pin", "stay at my ping", "hold position at my pin", "hold position at my mark",
                      "post up at my pin", "stay over there", "stay right there", "stay at that spot", "stay where i marked",
                      "hold at my pin"],
    # the pin under the other orders: the order is the verb's, the pin only says where
    "CHECK": ["check my pin", "check at my mark", "check the pin", "check at my pin", "check the fire escape",
              "check the fire exit", "check by the fire escape"],
    "LOOK_AT": ["look at my pin", "look at my mark"],
    "SMOKE": ["smoke my pin", "smoke at my mark", "throw a smoke on my pin", "yeah smoke it"],
    "FLASH": ["flash my pin", "flash at my mark"],
    "FRAG": ["frag my pin", "throw a frag at my mark"],
    "BREACH": ["breach at my pin", "breach at my mark", "yes breach it"],
    "PLANT": ["plant at my pin", "plant on my mark"],
    "TAKE_COVER": ["take cover at my pin", "hide at my mark", "keep your head down", "heads down"],
    "SUPPRESS": ["suppress my pin", "suppressive fire on my mark"],
    "OPEN_FIRE": ["open fire at my pin", "fire at my mark", "shoot at my pin"],
    "ATTACK": ["attack at my pin", "attack my mark"],
    "DRONE": ["drone my pin", "send the drone to my mark"],
    "FLANK": ["flank through my pin", "go around through my mark"],
    "JUMP": ["jump down at my mark", "jump to my pin", "drop in through the hatch", "drop in", "drop in there",
             "jump in through the hatch", "drop in through the hole", "jump left", "jump right", "jump back", "jump forward",
             "hop left", "hop back", "jump to the left", "jump backwards"],
    # the other angle with the clauses the other way round (probe_v53_new.log)
    "HOLD_ANGLE": ["watch my pin", "hold the angle at my mark", "i'll watch the other door you stay on this one",
                   "i'll take the other angle you hold this one", "i've got the other side you keep this one",
                   "i'm taking the other window you watch this one"],
    "HOLD_OTHER_ANGLE": ["i'll stay on this one you watch the other door", "i'll keep this angle you take the other"],
    # an answer word in front of an order does not make it an answer
    "GO_NOW": ["yes go", "yes do it", "okay go", "yeah go ahead"],
    "WAIT": ["no wait", "no stop", "no hold on"],
    "HOLD_FIRE": ["no hold your fire"],
}
NEW_NEGATED = {"NONE": ["don't come back", "no need to come back", "don't crouch", "don't lie down", "don't stand up",
                        "don't get up", "don't go inside", "don't get in there", "no don't breach"],
               "WAIT": ["don't come back yet", "don't stand up yet"]}
ON_SIGNAL = {"COME_BACK": ["come back on my go"], "STAND_UP": ["stand up when i say"], "CROUCH": ["crouch on my go"],
             "PRONE": ["go prone when i say"], "MOVE_TO": ["go inside on my go"]}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v53.json"), encoding="utf-8"))
    assert spec["setting"].count(SETTING[0]) == 1
    spec["setting"] = spec["setting"].replace(*SETTING)
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_SPEC)
    spec["intents"]["NONE"] = none                      # NONE stays the last intent, as in every earlier spec
    for k, v in MODIFIERS.items():
        assert k in spec["modifiers"], k
        spec["modifiers"][k] = v
    spec["modifiers"]["target"] += TARGET_ADD
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v54.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v53.json"), encoding="utf-8"))
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model["_note_v54"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v54.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v53.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v53"])               # the earlier relabelled seeds stay relabelled
    for text, (old, new) in RELABEL.items():
        relabel[f"seed_{old}_{seeds[old].index(text)}"] = new    # the seed stays where it is: its id and its audio stay valid
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    extra = {}
    for src in (NEW_SEEDS, NEW_NEGATED, ON_SIGNAL):
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
    seeds["_relabel_v54"] = relabel
    seeds["_note_v54"] = ("v54 (make_spec_v54.py, before any v54 test line existed, but with the owner's spoken lines of "
                          "2026-10-09 and the probes of bot v53 on the table): seed set v53 + commands for COME_BACK, CROUCH, "
                          "PRONE, STAND_UP, YES, NO, MAYBE and DONT_KNOW; acknowledgements and reports under NONE; going inside "
                          "under MOVE_TO; staying at a pointed place under HOLD_POSITION; the player's pin under seventeen "
                          f"orders; the three faults of bot v53: {added} new seeds over {len(extra)} intents. _relabel_v54: every "
                          "seed that keeps its id and position but carries another label under COOP_TAG=v54 (the two of v53, "
                          "'sit down': NONE -> CROUCH, 'go in': ENTRY -> MOVE_TO)")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v54.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v54: {len(spec['intents'])} intents (last: {list(spec['intents'])[-9:]}); intents_v54: "
          f"{len([k for k in model if not k.startswith('_')])}; seeds v54: {n} (+{added}); relabelled {relabel}; already seeds: {had}")
    print({k: len(seeds[k]) for k in NEW_SPEC})


if __name__ == "__main__":
    main()
