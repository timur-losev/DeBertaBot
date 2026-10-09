"""
v53: JUMP, and three repairs, after the owner's first test of bot v52 with a real voice. Written BEFORE any v53
test line exists (then hashed into frozen.txt).

The owner talked to bot v52 through the C++ voice chat on 2026-10-09 and reported:
  - "Jump down." was VAULT_WINDOW 0.70 and acted on: "this is not the window label, it is just jumping down";
  - "Another angle." was asked again (FLANK 0.31 / HOLD_OTHER_ANGLE 0.30) and "Keep another angle." was a coin
    toss inside the family (HOLD_OTHER_ANGLE 0.51 / HOLD_ANGLE 0.48).
The developer's typed probes of v52 (probe_v52.log, and a second one before this spec) added:
  - "check fire" / "check your fire" -- radio wording for stop shooting -- had become CHECK (v51: HOLD_FIRE);
  - every jump / hop / drop / climb that is not a window or a rope was acted on as VAULT_WINDOW or RAPPEL
    ("drop down" RAPPEL 1.00, "jump over the sofa" VAULT_WINDOW 1.00, "climb up" RAPPEL 0.57): no line and no
    seed of the data has such a move, so the words were learnt from the window and rope lines alone;
  - "we're taking fire" was acted on as HOLD_FIRE 0.89;
  - "hold this angle i'll take the other one" was HOLD_OTHER_ANGLE 1.00: no HOLD_ANGLE line of the data has the
    word "other", so the word alone decides.

One intent is added:
  JUMP   the bot jumps, drops or climbs with its own body: down, up, over or onto something. In the family
         "move" with MOVE_TO (the developer's choice: a planner that does not know it treats it as a move with a
         direction). Climbing is included (the developer's choice: "climb up" and "jump up" ask for the same move).
         The line to RAPPEL follows the owner's earlier decision for the roof: no rope word, no RAPPEL.
Nothing is removed or renamed. One more seed changes its label and keeps its id ("drop down from the roof":
RAPPEL -> JUMP); "_relabel_v53" carries it together with v52's ("help me": REVIVE_ME -> HELP).

NOT blind, unlike the lines: the seeds below were written with the owner's lines and both probes on the table.

Writes:
  blind/spec_v53.json       what the v53 blind authors and annotators see
  intents_v53.json          the model-side vocabulary (33 intents)
  seed_commands_v53.json    seed set v52 (ids unchanged) + seeds for JUMP and its negations, for the orders it is
                            confused with, radio wording for HOLD_FIRE, both sides of "the other angle", and reports
                            of being under fire (NONE)

    python make_spec_v53.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SPEC = {
    "JUMP": "the bot jumps, drops or climbs with its own body -- no rope, and not through a window: down from where it "
            "is (off a ledge, a roof edge, a balcony, through an open hatch or a hole in the floor), up onto something, "
            "over an obstacle, across a gap (jump down, drop down, hop over that, jump on the table, climb up there, jump "
            "off the roof). Through a window it is VAULT_WINDOW; on a rope it is RAPPEL; walking down the stairs or just "
            "going to a place is MOVE_TO ('go down', 'head downstairs'); 'get down' in the sense of ducking or hiding is "
            "TAKE_COVER",
}
CHANGED = {
    "VAULT_WINDOW": "the bot goes in or out through a WINDOW (vault, climb, jump or hop through it; a bare 'vault' or "
                    "'vault in' means the window). Jumping, dropping or climbing that is not through a window ('jump "
                    "down', 'hop over the sofa') is JUMP",
    "RAPPEL": "the bot uses a rappel rope on the outside of the building (rappel, rope up, rope down, drop down on the "
              "rope, hang at a window). Just going to a named place, the roof included, is MOVE_TO; jumping or dropping "
              "down with no rope in the wording ('drop down', 'jump off the roof') is JUMP",
    "HOLD_OTHER_ANGLE": "the bot watches the OTHER angle than the one currently covered (by the player or by the bot), "
                        "e.g. the player takes one door and tells the bot to take the other ('you take the other one', "
                        "'the other angle', 'another angle', 'the opposite side'). What counts is which angle the BOT "
                        "gets: 'hold this angle, I'll take the other one' leaves the bot on its angle and is HOLD_ANGLE",
}
# sentences of the v52 spec that the changes make false or incomplete
REWORDED = {
    "HOLD_FIRE": ("(hold fire, cease fire, don't shoot, stop shooting)", "(hold fire, cease fire, check fire, don't shoot, stop shooting)"),
}
APPENDED = {
    "MOVE_TO": ". If the player says to jump, drop, hop or climb ('jump down', 'climb up on that') it is JUMP",
    "HOLD_ANGLE": ". It stays this intent when the player says they take the other one themselves ('hold this angle, I'll "
                  "take the other one')",
    "HOLD_FIRE": ". 'Check fire' / 'check your fire' is radio wording for stop shooting: this intent, not CHECK",
    "CHECK": ". 'Check fire' / 'check your fire' is the order to stop shooting: HOLD_FIRE",
    "NONE": ". A report that the player or the team is under fire ('we're taking fire', 'I'm pinned down', 'I'm "
            "suppressed') is a callout: NONE, not SUPPRESS, HOLD_FIRE or HELP. What the player says they do themselves "
            "('I'm jumping down') is not an order either",
}
TARGET_ADD = (" For JUMP the target is where to jump or what to get over or onto ('jump down' = direction down, 'climb "
              "up' = direction up, 'jump over the sofa' = sofa, 'climb on the table' = table); the place to jump off is "
              "the place to leave, so 'jump off the roof' has no target.")
NEW_MODEL = {
    "JUMP": {"label": "jump", "description": "jump, drop or climb without a rope or a window: down, up, over or onto something"},
}
FAMILY_NOTE = "v53 families: v52 families + JUMP in 'move' with MOVE_TO, FOLLOW_ME and FLANK"
RELABEL = {"drop down from the roof": ("RAPPEL", "JUMP")}

NEW_SEEDS = {
    "JUMP": ["jump", "jump down", "drop down", "hop down", "jump off", "jump down from there", "jump down here",
             "jump down to me", "drop down here", "drop down to me", "drop down there", "just jump down", "leap down",
             "jump over", "jump over that", "jump over it", "hop over that", "hop over it", "vault over that",
             "vault over it", "climb over that", "climb over it", "jump across", "jump across the gap", "jump the gap",
             "jump up", "jump up there", "climb up", "climb up there", "climb up here", "climb down",
             "climb down from there", "jump on that", "climb on that", "get up on that", "climb on top of that",
             "jump off the ledge", "drop off the ledge", "jump off the edge", "jump down the hatch",
             "drop down the hatch", "drop through the hatch", "jump down the hole", "drop down through the hole",
             "jump into the hole", "jump to the lower floor", "drop to the floor below", "jump down a level",
             "drop down a floor"],
    # the orders the new intent must not swallow
    "VAULT_WINDOW": ["jump in the window", "jump out the window", "jump through that window", "climb through the window",
                     "climb out the window"],
    "RAPPEL": ["drop down on the rope", "rope down", "rope down from the roof", "rappel down from the roof",
               "climb up the rope", "drop down the rope"],
    "MOVE_TO": ["go down", "go up", "go down there", "go up there", "go downstairs", "go upstairs",
                "head down to the basement", "walk down the stairs", "take the stairs down"],
    "TAKE_COVER": ["get down get down", "stay down", "duck", "get down now"],
    # radio wording: "check" here is not CHECK
    "HOLD_FIRE": ["check fire", "check your fire", "check firing", "check fire check fire",
                  "check your fire friendlies ahead"],
    # the other angle: the bot takes it ...
    "HOLD_OTHER_ANGLE": ["another angle", "the other angle", "other angle", "keep another angle", "hold another angle",
                         "take another angle", "watch another angle", "the opposite angle", "opposite angle",
                         "take the opposite side", "hold the opposite side", "watch another door", "cover another window",
                         "cover the other window", "watch the other window", "i've got this one you take the other",
                         "i'll hold this angle you take the other one", "i'm on this door you watch the other one",
                         "switch to the other angle", "cover the other angle", "keep the other angle"],
    # ... or the player does, and the bot keeps its own
    "HOLD_ANGLE": ["hold this angle i'll take the other one", "watch this door i've got the other one",
                   "you hold this side i'll take the other", "stay on this angle i'm taking the other one",
                   "keep watching that door i'll cover the other one", "hold that window i'll watch the other side"],
    # reports, not orders
    "NONE": ["we're taking fire", "taking fire", "i'm taking fire", "i'm under fire", "we're under fire", "i'm pinned down",
             "i'm pinned", "we're pinned down", "i'm suppressed", "we're suppressed", "they're suppressing us",
             "they've got me pinned", "i'm getting shot at", "taking fire from the left",
             "taking fire from the north window", "he jumped down", "they jumped out the window",
             "someone dropped down the hatch", "i'm jumping down", "i'll jump down first", "i'm going to drop down",
             "he's climbing up", "nice jump", "he's on the other angle", "they're on the other side", "nice angle",
             "that's a bad angle"],
}
NEW_NEGATED = {"NONE": ["don't jump", "don't jump down", "do not drop down", "no need to jump", "don't climb up there"],
               "WAIT": ["don't jump yet", "don't drop down yet"]}
ON_SIGNAL = {"JUMP": ["jump down on my go", "drop down when i say", "jump on my mark"]}
PLACED = {
    "JUMP": [("jump over {}", ["the sofa", "the table", "the chairs"]),
             ("hop over {}", ["the sofa", "the table"]),
             ("climb over {}", ["the sofa", "the table"]),
             ("vault over {}", ["the sofa", "the table"]),
             ("jump on {}", ["the table", "the sofa"]),
             ("climb on {}", ["the table", "the sofa"]),
             ("jump off {}", ["the roof", "the table"]),
             ("jump down from {}", ["the roof", "the top floor"]),
             ("drop down from {}", ["the top floor"]),
             ("jump down to {}", ["the first floor", "the basement"]),
             ("drop down to {}", ["the basement", "the first floor"])],
}
DIRECTED = {
    "JUMP": ["jump down on the left", "drop down on the right side", "climb up on the right"],
}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v52.json"), encoding="utf-8"))
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
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v53.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v52.json"), encoding="utf-8"))
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model["_note_v53"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v53.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v52.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v52"])               # v52's relabelled seed stays relabelled
    for text, (old, new) in RELABEL.items():
        relabel[f"seed_{old}_{seeds[old].index(text)}"] = new    # the seed stays where it is: its id and its audio stay valid
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    extra = {}
    for src in (NEW_SEEDS, NEW_NEGATED, DIRECTED, ON_SIGNAL):
        for k, v in src.items():
            extra.setdefault(k, []).extend(v)
    for k, templates in PLACED.items():
        for tpl, places in templates:
            extra[k].extend(tpl.format(p) for p in places)
    added, had = 0, []
    for k, v in extra.items():
        for t in v:
            assert owner.get(t, k) == k, f"{t!r} is already a {owner[t]} seed, cannot also be {k}"
            if t in owner:
                had.append(t)
            else:
                seeds.setdefault(k, []).append(t)       # appended: every earlier seed keeps its id (seed_<INTENT>_<n>)
                owner[t] = k
                added += 1
    seeds["_relabel_v53"] = relabel
    seeds["_note_v53"] = ("v53 (make_spec_v53.py, before any v53 test line existed, but with the owner's spoken lines of "
                          "2026-10-09 and the developer's probes of bot v52 on the table): seed set v52 + commands for JUMP "
                          "(plain, with places, with directions, negated), for the window, rope, move and cover orders next "
                          "to it, radio wording under HOLD_FIRE, both sides of 'the other angle', reports of being under fire "
                          f"under NONE: {added} new seeds over {len(extra)} intents. _relabel_v53: every seed that keeps its "
                          "id and position but carries another label under COOP_TAG=v53 (v52's one and 'drop down from the "
                          "roof')")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v53.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v53: {len(spec['intents'])} intents (last: {list(spec['intents'])[-3:]}); intents_v53: "
          f"{len([k for k in model if not k.startswith('_')])}; seeds v53: {n} (+{added}); relabelled {relabel}; "
          f"JUMP {len(seeds['JUMP'])}; already seeds: {had}")


if __name__ == "__main__":
    main()
