"""
v56: going back, letting the player out, standing at a place, and ways up, down and inside, after the owner's play with bot
v55 in Lyra. Written BEFORE any v56 test line exists (then hashed into frozen.txt).

The owner played bot v55 on L_Expanse and asked (2026-10-15, their words in quotes, answers to the developer's questions in
brackets):
  - "фраза Go up + by stairs, + by steps должна заставить бота подняться куда-то выше. Если рядом есть лестница, то по
    лестнице ли по рампе, а не приводить к непониманию" ("Go up by the stairs." got "Which stairs? The one above, 5 m?";
    "Stairs on my pin." got "Come again?"): the classifier already reads the ways as MOVE_TO; the question is the planner's
    (world.py: a way up or down with no particular stairs is not asked about). The ramp was RAPPEL ("go down the ramp");
  - "go down - игрок видит какой-то спуск, бот должен понять. И go inside": [inside = the nearest covered spot where the
    player looks, through a door if they look at one]; a new zone "inside" (locations.json version 7);
  - "Stand here, Stand on my pin должны иметь интент": staying at a place is HOLD_POSITION, as "stay here" and "wait here"
    are (v55 read "Stand on my pin." HOLD_POSITION 0.49, under the gate);
  - "REVIVE_ME вообще больше не нужен, этот лейбл можно освободить": its place in the label list goes to HELP_INTERACTION,
    and being revived is HELP (the bot comes to the player);
  - "Let me out должен генерировать новый интент HELP_INTERACTION, мы будем на него опираться": [the bot walks to the
    speaker and the game raises an event the owner's code takes up];
  - "GO back должен возвращать бота на его предыдущую позицию до команды, не должен быть интент COME_BACK. COME_BACK
    получается, когда я говорю get back to me, come back TO ME": a new intent GO_BACK [the game remembers where the bot
    stood before each order that moved it]; COME_BACK is coming back to the player.
The developer's choices, told to the owner: HELP_INTERACTION takes REVIVE_ME's index (the labels before and after it keep
theirs), GO_BACK comes after REPEAT; families: HELP_INTERACTION in 'help' with HELP, GO_BACK in 'move'. "Return" with nothing
after it is GO_BACK (the owner's "come back TO ME" is what makes COME_BACK). "Go stand by the window", with a verb of going,
stays MOVE_TO, as the authored lines have it; "stand here" is HOLD_POSITION.

NOT blind, unlike the lines: the seeds below were written with the owner's log of 2026-10-15 on the table.

Writes:
  blind/spec_v56.json       what the v56 blind authors and annotators see
  intents_v56.json          the model-side vocabulary (45 intents)
  seed_commands_v56.json    seed set v55 (ids unchanged) + the seeds below; _relabel_v56 = _relabel_v55 + the REVIVE_ME
                            seeds (HELP) and the going-back seeds of COME_BACK and MOVE_TO (GO_BACK)
  annot/v56/relabel_v56.json   the authored lines (v1 to v55) that change: every reading of REVIVE_ME is HELP (a rule);
                            three COME_BACK lines that send the bot to its own earlier place are GO_BACK (read one by one)

    python make_spec_v56.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

HELP_INTERACTION = (
    "the player is stuck, trapped, or locked in or out, and asks the bot to get them out or let them through (let me out, "
    "let me in, get me out of here, I'm stuck in here, I'm locked in, help me get out, I can't get out), or asks the bot to "
    "work something for them that they cannot reach or use themselves (press the button for me, pull the lever, hit the "
    "switch for me). The bot comes to the player and does it. Opening a door or a window as an order of its own ('open the "
    "door', 'open it for me') is OPEN; help with nothing named is HELP")
GO_BACK = (
    "the bot goes back to where IT was before the last order that moved it (go back, go back there, go back to where you "
    "were, return, head back, return to your position, back to your post, get back to your spot). The planner knows that "
    "place; the line names none. Coming back to the PLAYER is COME_BACK ('come back', 'come back to me', 'get back to me', "
    "'get back here'); going back to a place the line names is MOVE_TO ('go back to the stairs', 'head back to the first "
    "floor'); retreating from a fight is FALL_BACK ('fall back', 'pull back')")
REWRITTEN = {
    "COME_BACK": (
        "the bot comes back to the PLAYER (come back, come back here, come back to me, get back here, get back to me, back "
        "to me, return to me, regroup, rejoin me). Going back to where the bot itself was is GO_BACK ('go back', 'return', "
        "'return to your position', 'head back'); retreating from a fight is FALL_BACK ('fall back', 'pull back', 'get "
        "back'); coming to the player or staying with them is FOLLOW_ME ('come here', 'on me', 'come with me'); going back "
        "to a place the line names is MOVE_TO ('go back to the stairs')"),
    "HELP": (
        "the player asks the bot for help and does not say with what (help me, help me here, I need a hand, I need backup "
        "here), or asks to be revived or picked up when down (revive me, I'm down, pick me up, help me up). The bot comes to "
        "the player and its planner works out what is needed. If the player says what they need, it is that intent: being "
        "let out, let in or freed, or having a control worked for them, is HELP_INTERACTION ('let me out', 'get me out of "
        "here', 'press the button for me'); being covered is COVER_ME, being followed is FOLLOW_ME"),
}
# whole phrases of the v55 text that change; each must be there exactly once
REPLACED = {
    "FOLLOW_ME": ("'Come back' / 'return' is COME_BACK", "'Come back' / 'come back to me' is COME_BACK; 'go back' / 'return' "
                  "is GO_BACK"),
    "MOVE_TO": ("Coming back with no place named ('come back', 'return') is COME_BACK.",
                "Coming back to the player ('come back', 'come back to me') is COME_BACK; going back to where the bot was "
                "('go back', 'return') is GO_BACK."),
    "FALL_BACK": ("'Come back' / 'return' with no retreat in the wording is COME_BACK.",
                  "'Come back' with no retreat in the wording is COME_BACK; 'go back' and 'return' are GO_BACK."),
    "STAND_UP": ("'Get me up' / 'help me up' is REVIVE_ME;", "'Get me up' / 'help me up' is HELP;"),
}
APPENDED = {
    "MOVE_TO": (". Going up or down with no particular place, or by a way the line names without singling one out ('go up', "
                "'go up by the stairs', 'take the steps up', 'go down the ramp', 'head down', 'find a way up'), is this "
                "intent: the planner takes the nearest way that way, the one the player looks at first. Going inside with no "
                "place named ('go inside', 'get indoors', 'get in the building') is this intent with the zone 'inside'"),
    "HOLD_POSITION": (". Standing at a place is staying there: 'stand here', 'stand there', 'stand right here', 'stand on my "
                      "pin', 'stand at the north door' are this intent ('go stand by the window', with a verb of going, is "
                      "MOVE_TO; 'stand up' is STAND_UP)"),
    "STAND_UP": " 'Stand on my pin', 'stand by the door' are HOLD_POSITION too",
    "OPEN": (". 'Let me out', 'let me in', 'get me out of here' is HELP_INTERACTION: the player is stuck and the bot frees "
             "them"),
    "RAPPEL": ". A ramp is walked, not roped: 'go down the ramp', 'take the ramp up' are MOVE_TO",
}
TARGET_ADD = (" For GO_BACK and HELP_INTERACTION all null: the place is the bot's own earlier one, or the player ('go back' "
              "gives no direction). Zone 'inside': a line that sends the bot indoors with no place named has zone 'inside' "
              "('go inside', 'get indoors', 'get in the building'); a named place keeps its own ('get inside the car' = "
              "car). A ramp is not a map object: 'go down the ramp' = direction down.")
ZONE_INSIDE = "'inside': indoors, under a roof, relative: the planner takes the nearest way in where the player looks"
DIRECTION_BACK = ("'go back', ", "'step back', ")      # map.directions.back: "go back" is GO_BACK now
NEW_MODEL = {
    "HELP_INTERACTION": {"label": "help me get out", "description": "let the player out or through, or work a control for "
                                                                    "them"},
    "GO_BACK": {"label": "go back", "description": "go back to where the bot was before the last order"},
}
FAMILY_NOTE = ("v56 families: v55 families without REVIVE_ME ('revive'); HELP_INTERACTION in 'help' with HELP, GO_BACK in "
               "'move'. HELP_INTERACTION is at REVIVE_ME's index")

# seeds that keep their id (and their audio) under another label
RELABEL_SEEDS = {
    # going back to the bot's own earlier place (the owner: COME_BACK is coming back TO ME)
    "seed_MOVE_TO_68": ("go back", "GO_BACK"),
    "seed_COME_BACK_3": ("return", "GO_BACK"), "seed_COME_BACK_4": ("return back", "GO_BACK"),
    "seed_COME_BACK_12": ("return to your position", "GO_BACK"), "seed_COME_BACK_13": ("go back to your position", "GO_BACK"),
    "seed_COME_BACK_14": ("get back to your spot", "GO_BACK"), "seed_COME_BACK_15": ("go back where you were", "GO_BACK"),
    "seed_COME_BACK_16": ("back to your post", "GO_BACK"), "seed_COME_BACK_19": ("return to position", "GO_BACK"),
    "seed_COME_BACK_20": ("head back", "GO_BACK"),
}
REVIVE_TO = "HELP"     # every REVIVE_ME seed and reading

NEW_SEEDS = {
    "GO_BACK": ["go back there", "go back to where you were", "go back to your spot", "go back to your post",
                "back to your spot", "back to your position", "return to your spot", "return to your post", "head back there",
                "go back to where you came from", "go back to your old spot", "go back to where you started",
                "back where you were", "return to where you were", "get back to your post", "go back to your last position",
                "go back to where you just were", "go back now", "just go back", "ok go back", "go on back",
                "go back to the spot you were at", "you can go back now", "go back to holding", "head back to your spot",
                "return to your last spot", "back to where you were", "move back to your spot", "go back to your old position",
                "go back where you came from"],
    "COME_BACK": ["get back to me", "come back over to me", "come back to my side", "get back over to me", "back to my side",
                  "return to my side", "come back to where i am", "come back to me now", "get back to me now",
                  "come on back to me"],
    "HELP_INTERACTION": ["let me out", "let me in", "get me out", "get me out of here", "let me out of here",
                         "i'm stuck let me out", "i'm stuck in here", "i'm locked in", "i'm locked out", "i'm trapped in here",
                         "help me get out", "help me get out of here", "i can't get out", "i can't get in",
                         "get me out of this room", "come let me out", "let me through", "open up and let me in",
                         "i'm stuck help me out of here", "free me", "get me out of this", "press the button for me",
                         "hit the switch for me", "pull the lever", "pull that lever for me", "press that button",
                         "flip the switch for me", "use the panel for me", "unlock it so i can get out",
                         "i'm stuck behind this door"],
    "HELP": ["rez me", "come get me up", "i'm down help", "get me back up"],
    # standing at a place is staying there (the owner: "Stand here, Stand on my pin должны иметь интент")
    "HOLD_POSITION": ["stand here", "stand there", "stand right here", "stand right there", "stand over there",
                      "stand on my pin", "stand at my pin", "stand by my pin", "stand on my mark", "stand on the pin",
                      "stand by the door", "stand at the north door", "stand on the roof", "stand by the stairs",
                      "stand in the corner", "stand on that spot", "stand here and wait", "stand here and hold",
                      "you stand here", "just stand here", "stand there for now", "stand guard here", "stand here until i say",
                      "stand by the window", "stand at the top of the stairs"],
    # ways up and down, by stairs, steps or a ramp, with no particular one; going indoors; the stairs as an answer
    "MOVE_TO": ["go down the ramp", "go up the ramp", "take the ramp", "take the ramp up", "take the ramp down",
                "walk down the ramp", "run up the ramp", "head down the ramp", "go down by the ramp", "go up by the ramp",
                "use the ramp", "go up the steps", "go down the steps", "go up by steps", "go down by steps", "take the steps",
                "take the steps down", "take the steps up", "climb the stairs", "climb the steps", "go up a level",
                "go down a level", "go up one floor", "go down one floor", "head up", "head down", "go higher", "get higher",
                "get up higher", "find a way up", "find a way down", "go up somewhere", "go up by the stairs",
                "go down by the stairs", "take the stairs down", "go down these stairs", "go up these stairs",
                "go up those stairs", "stairs on my pin", "the stairs on my pin", "stairs at my pin", "the stairs by my pin",
                "go indoors", "get indoors", "head indoors", "go in the building", "get in the building", "go inside the house",
                "get in the house", "move inside", "get inside now", "everyone inside", "inside now", "go inside quick",
                "find a way inside", "get inside somewhere"],
    "WAIT": ["don't go back", "don't go back there", "don't let me out yet"],
}
ON_SIGNAL = {"GO_BACK": ["go back on my go", "go back when i say"], "HELP_INTERACTION": ["let me out on my go"]}

# the authored lines (v1 to v55) read one by one: they send the bot to its own earlier place
LINES_TO_GO_BACK = {
    "r6v54_011": "Return to where you were anchoring, I'll finish the roam clear myself.",
    "csv54_011": "return to your post, nobody told you to peek",
    "sttv54_008": "okay so uh you can return now return to where you was before i sent you",
}


def main():
    sys.path.insert(0, HERE)

    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v55.json"), encoding="utf-8"))
    for k, (old, new) in REPLACED.items():
        assert spec["intents"][k].count(old) == 1, (k, old)
        spec["intents"][k] = spec["intents"][k].replace(old, new)
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    spec["intents"].update(REWRITTEN)
    # HELP_INTERACTION takes REVIVE_ME's place; GO_BACK comes after REPEAT; NONE stays the last intent
    spec["intents"] = {("HELP_INTERACTION" if k == "REVIVE_ME" else k): (HELP_INTERACTION if k == "REVIVE_ME" else v)
                       for k, v in spec["intents"].items()}
    none = spec["intents"].pop("NONE")
    spec["intents"]["GO_BACK"] = GO_BACK
    spec["intents"]["NONE"] = none
    for k, v in spec["intents"].items():
        assert "REVIVE_ME" not in v, k
    spec["modifiers"]["target"] += TARGET_ADD
    spec["map"]["zones"]["inside"] = ZONE_INSIDE
    old, new = DIRECTION_BACK
    assert spec["map"]["directions"]["back"].count(old) == 1
    spec["map"]["directions"]["back"] = spec["map"]["directions"]["back"].replace(old, new)
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v56.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v55.json"), encoding="utf-8"))
    model = {("HELP_INTERACTION" if k == "REVIVE_ME" else k): (NEW_MODEL["HELP_INTERACTION"] if k == "REVIVE_ME" else v)
             for k, v in model.items()}
    none = model.pop("NONE")
    note55 = model.pop("_note_v55")
    model["GO_BACK"] = NEW_MODEL["GO_BACK"]
    model["NONE"] = none
    model["_note_v55"] = note55
    model["_note_v56"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v56.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]
    assert labels == [k for k in spec["intents"]], (labels, list(spec["intents"]))

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v55.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v55"])               # the earlier relabelled seeds stay relabelled
    for sid, (text, to) in RELABEL_SEEDS.items():
        k, n = sid[len("seed_"):].rsplit("_", 1)
        assert seeds[k][int(n)] == text and relabel.get(sid, k) == k, (sid, seeds[k][int(n)], relabel.get(sid))
        relabel[sid] = to
    for n, t in enumerate(seeds["REVIVE_ME"]):
        sid = f"seed_REVIVE_ME_{n}"
        assert relabel.get(sid, "REVIVE_ME") in ("REVIVE_ME", REVIVE_TO), (sid, relabel.get(sid))
        relabel[sid] = REVIVE_TO
    assert "REVIVE_ME" not in relabel.values()
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    extra = {}
    for src in (NEW_SEEDS, ON_SIGNAL):
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
    seeds["_relabel_v56"] = relabel
    seeds["_note_v56"] = ("v56 (make_spec_v56.py, before any v56 test line existed, but with the owner's log of 2026-10-15 on "
                          "the table): seed set v55 + commands for GO_BACK and HELP_INTERACTION; standing at a place under "
                          "HOLD_POSITION; ways up and down by stairs, steps or a ramp, going indoors, and 'stairs on my pin' "
                          f"under MOVE_TO: {added} new seeds over {len(extra)} intents. _relabel_v56: _relabel_v55 + the "
                          f"{len(seeds['REVIVE_ME'])} REVIVE_ME seeds (HELP) + {len(RELABEL_SEEDS)} going-back seeds "
                          "(GO_BACK). The key REVIVE_ME stays for the ids; no seed carries that label any more")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v56.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # the authored lines
    os.environ["COOP_TAG"] = "v55"
    import coop_v2
    items = {it["id"]: it for it in coop_v2.load_items()}
    for k, t in LINES_TO_GO_BACK.items():
        assert items[k]["text"] == t and items[k]["maj"] == "COME_BACK", (k, items[k]["text"], items[k]["maj"])
    revived = sorted(k for k, it in items.items() if any("REVIVE_ME" in r["set"] or r["intent"] == "REVIVE_ME"
                                                         for r in it["reads"]))
    os.makedirs(os.path.join(HERE, "annot", "v56"), exist_ok=True)
    json.dump({"_note": "make_spec_v56.py: the authored lines (v1 to v55) whose reading changes under spec v56. 'revive': "
                        "every reading of REVIVE_ME is HELP (a rule: the label is gone and being revived is HELP); the "
                        "lines are listed for the record. 'lines': three COME_BACK lines that send the bot to its own "
                        "earlier place are GO_BACK (read one by one by the developer before freezing)",
               "revive": {"from": "REVIVE_ME", "to": REVIVE_TO, "ids": revived},
               "lines": {k: {"from": "COME_BACK", "to": "GO_BACK", "text": t} for k, t in LINES_TO_GO_BACK.items()}},
              io.open(os.path.join(HERE, "annot", "v56", "relabel_v56.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v56: {len(spec['intents'])} intents (index of HELP_INTERACTION {list(spec['intents']).index('HELP_INTERACTION')}"
          f", last: {list(spec['intents'])[-4:]}); intents_v56: {len(labels)}; seeds v56: {n} (+{added}); already seeds: {had}")
    print({k: sum(1 for kk, v in seeds.items() if not kk.startswith('_') for i, _ in enumerate(v)
                  if relabel.get(f'seed_{kk}_{i}', kk) == k) for k in ("GO_BACK", "HELP_INTERACTION", "HELP", "COME_BACK",
                                                                       "HOLD_POSITION", "MOVE_TO")})
    print(f"authored lines: {len(revived)} with a REVIVE_ME reading -> HELP; {len(LINES_TO_GO_BACK)} COME_BACK -> GO_BACK")


if __name__ == "__main__":
    main()
