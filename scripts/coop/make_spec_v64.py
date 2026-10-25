"""
v64 (the owner, 2026-10-25): what the bot sees and how it is, pushing and rolling things, putting down what it carries; on top of
v63 (MELEE, HOLSTER), which was specified and never trained. Written BEFORE any v64 test line exists (then hashed into
frozen.txt).

The owner's words and choices (2026-10-24/25):
  - "Что видишь? ... бот будет смотреть только лейблы обнаруженных интерактивных объектов"; "как дела / how are you" go to the
    report, not small talk ("«как дела / how are you» в «обстановку»"); the questions about the body as intents, not word rules;
  - "Толкать, катить и «поставь» включаем в v64 вместе с игровым кодом";
  - in play he tried to make the bot take "именно картонную коробку", and it did not understand: «Подними (эту) коробку» became
    "Lift up the crate" -> DEMOLISH 0.62; «Возьми эту картонную коробку» -> DELIVER 0.61 / COLLECT 0.37, asked again; «Двигай
    эту коробку» -> DELIVER; «Убери оружие» -> SWITCH_WEAPON; «Голые руки» -> nothing;
  - taking the weapon out again stays SWITCH_WEAPON (the owner left it to me): on a bot with its hands free it draws.

Five intents after HOLSTER, before NONE, each in a family of its own:
  STATUS_REPORT  tell what it sees and senses now and how it is (what do you see, how are you, how is it going, sitrep)
  BODY_STATE     a question about its body (are you hurt, are you hot / cold, do you smell gas, got any ammo)
  PUSH           push, shove or slide a thing (a box, a crate) somewhere
  ROLL           roll a round thing (a cable spool, a barrel, a reel) somewhere
  DROP           put down or let go of what it carries, where it is
COLLECT and DELIVER become one family, carry: the game carries the thing for both, and a line between them is no question.
Relabelled seeds: SMALL_TALK's how-are-you (how are you doing, how's it going, how is it going, how are things) are
STATUS_REPORT; SMALL_TALK's are-you-okay (are you okay, you okay, are you alright, how do you feel) BODY_STATE; SEE_THING's
"do you see anything", "see anything" STATUS_REPORT.
The places: vocabulary v10 = v9 + the object spool (cable spool, reel) and the qualifiers big, small, cardboard.

Writes:
  blind/spec_v64.json        the v63 spec with the five intents and the boundaries
  intents_v64.json           the model-side vocabulary (69 intents)
  seed_commands_v64.json     seed set v63 (ids unchanged) + the seeds below; _relabel_v64 = _relabel_v63 + RELABEL_SEEDS
  locations_v64.json         the place vocabulary v10

    python make_spec_v64.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_INTENTS = {
    "STATUS_REPORT": (
        "the bot tells what it sees and senses around it right now and how it is doing: the marked things in sight, a heat or "
        "gas it feels, the enemy, its health (what do you see, what can you see from there, how are you, how are you doing, "
        "how is it going, how are things over there, sitrep, status report, report, what's the situation, anything to "
        "report, what's around you, talk to me, what have you got). A yes/no question about one thing ('do you see that', "
        "'do you see the enemy', 'can you see me') is SEE_THING / SEE_ME; a greeting, thanks or chat ('hello', 'what's up', "
        "'thanks', 'who are you') is SMALL_TALK; a question about one part of its body ('are you hurt', 'are you hot') is "
        "BODY_STATE"),
    "BODY_STATE": (
        "a question about the bot's body or kit: is it hurt, hot, cold, short of breath from gas, out of ammo (are you hurt, "
        "are you okay, are you alright, are you wounded, how's your health, are you hot, is it hot there, are you cold, "
        "are you freezing, do you smell gas, can you breathe, are you low on ammo, got any ammo, how many rounds do you have, "
        "how do you feel). Asking for a report of everything ('how are you', 'what do you see', 'sitrep') is STATUS_REPORT; "
        "sending the bot to get ammo or health ('get some ammo', 'go find health') is MOVE_TO"),
    "PUSH": (
        "the bot pushes, shoves or slides a thing (a box, a crate, a cart, a barrel standing up) somewhere, without lifting it "
        "(push the box, push that crate over there, shove the box to the door, slide the crate, move this box out of the way, "
        "push it aside, push the big box against the wall). Carrying a thing ('bring me the box', 'pick up the crate', "
        "'carry it there') is DELIVER / COLLECT; 'push forward' / 'push up' / 'push the line' is moving the bot (MOVE_TO), "
        "'push in' ENTRY, 'push them back' SUPPRESS"),
    "ROLL": (
        "the bot rolls a round thing on the ground (a cable spool, a reel, a barrel on its side, a tire) somewhere (roll the "
        "spool over there, roll the cable reel to the door, roll that barrel, roll it out of the way). 'Roll out' / "
        "'let's roll' is going now (GO_NOW / MOVE_TO); pushing a box is PUSH"),
    "DROP": (
        "the bot puts down or lets go of what it is carrying, where it stands (put it down, drop it, drop the box, set it "
        "down, put the crate down here, leave it here, let go of it, drop that, put that box down). Bringing the thing to a "
        "place ('put it over there', 'put the box by the door', 'bring it here') is DELIVER; 'drop down' / 'drop into the pit' "
        "is JUMP; 'drop him' ATTACK; putting the weapon away is HOLSTER"),
}
APPENDED = {
    "SMALL_TALK": (". How the bot is ('how are you', 'how is it going', 'how are things') and what it sees ('what do you see') "
                   "ask for a report: STATUS_REPORT; 'are you okay' / 'are you hurt' is BODY_STATE"),
    "SEE_THING": (". An open question with nothing named ('what do you see', 'do you see anything', 'what's around') asks for "
                  "a report: STATUS_REPORT"),
    "COLLECT": (". Lifting a thing up to carry it ('lift up the box', 'pick that crate up', 'grab the cardboard box', 'get that "
                "box up') is this intent or DELIVER, never DEMOLISH"),
    "DELIVER": (". Pushing or rolling a thing along the ground is PUSH / ROLL; putting down what it carries where it stands "
                "is DROP"),
    "DEMOLISH": ". Lifting up a box or a crate ('lift up the crate') is carrying it (COLLECT), not tearing it down",
    "MOVE_TO": (". Moving a thing (a box, a crate, a spool) is PUSH / ROLL / DELIVER: the thing is moved, not the bot"),
    "JUMP": ". Dropping what it carries ('drop it', 'drop the box') is DROP",
    "HOLSTER": " (also: bare hands, fists only, empty-handed, no weapon in your hands)",
    "NONE": (". The player saying how he is ('I'm hurt', 'I'm cold') or what he sees ('I see a box') is a callout, NONE"),
}
NEW_MODEL = {
    "STATUS_REPORT": {"label": "report", "description": "tell what it sees and senses and how it is"},
    "BODY_STATE": {"label": "say how you are", "description": "answer a question about its body: hurt, hot, cold, gas, ammo"},
    "PUSH": {"label": "push it", "description": "push or slide a thing somewhere"},
    "ROLL": {"label": "roll it", "description": "roll a round thing somewhere"},
    "DROP": {"label": "put it down", "description": "put down what it carries"},
}
FAMILY_NOTE = ("v64 families: v63's, with COLLECT and DELIVER in one family (carry); STATUS_REPORT, BODY_STATE, PUSH, ROLL "
               "and DROP each in a family of their own. They come after HOLSTER, before NONE")

# seeds of v63 under another intent from v64 on (seed_<intent>_<index in seed_commands_v63.json>)
RELABEL_SEEDS = {
    "seed_SMALL_TALK_0": "STATUS_REPORT", "seed_SMALL_TALK_1": "STATUS_REPORT", "seed_SMALL_TALK_2": "STATUS_REPORT",
    "seed_SMALL_TALK_42": "STATUS_REPORT",
    "seed_SMALL_TALK_15": "BODY_STATE", "seed_SMALL_TALK_16": "BODY_STATE", "seed_SMALL_TALK_17": "BODY_STATE",
    "seed_SMALL_TALK_41": "BODY_STATE",
    "seed_SEE_THING_14": "STATUS_REPORT", "seed_SEE_THING_15": "STATUS_REPORT",
}
RELABEL_TEXT = {"seed_SMALL_TALK_0": "how are you doing", "seed_SMALL_TALK_1": "how's it going", "seed_SMALL_TALK_2": "how is it going",
                "seed_SMALL_TALK_42": "how are things", "seed_SMALL_TALK_15": "are you okay", "seed_SMALL_TALK_16": "you okay",
                "seed_SMALL_TALK_17": "are you alright", "seed_SMALL_TALK_41": "how do you feel",
                "seed_SEE_THING_14": "do you see anything", "seed_SEE_THING_15": "see anything"}

NEW_SEEDS = {
    "STATUS_REPORT": [
        "what do you see", "what can you see", "what can you see from there", "what are you looking at", "what are you seeing",
        "tell me what you see", "how are you", "how are you holding up", "how's it going over there", "how are things over there",
        "how's everything", "sitrep", "give me a sitrep", "status report", "status", "report", "report in", "give me a report",
        "what's the situation", "what's the situation over there", "anything to report", "what's around you", "what's around",
        "what's out there", "what's over there", "what have you got", "what you got", "talk to me what do you see",
        "how does it look", "how does it look over there", "what's going on over there", "anything going on", "anything new",
        "describe what you see", "look around and tell me", "what's ahead", "what's in front of you", "you see anything interesting",
        "anything interesting", "what's your status", "check in", "how's your side", "how's the situation",
        "what's the word", "how goes it", "what's happening over there"],
    "BODY_STATE": [
        "are you hurt", "are you wounded", "are you injured", "are you hit", "did you get hit", "how's your health", "what's your health",
        "how much health do you have", "are you bleeding", "do you need healing", "you need a medkit", "are you hot", "is it hot there",
        "are you burning", "are you on fire", "too hot for you", "are you cold", "are you freezing", "is it cold there", "you cold",
        "do you smell gas", "can you breathe", "is there gas", "are you choking", "is the air okay", "are you low on ammo",
        "got any ammo", "do you have ammo", "how much ammo do you have", "how many rounds do you have", "how's your ammo",
        "are you out of ammo", "ammo check", "how many mags do you have", "are you okay there", "you alright there",
        "are you in one piece", "still alive", "are you still alive", "how bad is it", "how are you feeling"],
    "PUSH": [
        "push the box", "push that box", "push this box", "push the crate", "push that crate over there", "push the box over there",
        "shove the box", "shove that crate", "shove the box to the door", "slide the crate", "slide the box over there",
        "push the box out of the way", "push it aside", "push it out of the way",
        "push the big box", "push the big box against the wall", "push the cardboard box", "push it there", "push it to me",
        "push the box toward me", "nudge the box", "shove it over there", "push that thing", "push the cart", "shove the big box",
        "slide it over", "push the crate to the wall", "push the barrel", "push this crate there", "push the box along"],
    "ROLL": [
        "roll the spool", "roll that spool", "roll the spool over there", "roll the cable spool", "roll the cable reel",
        "roll the reel to the door", "roll the reel", "roll that barrel", "roll the barrel over there", "roll it over there",
        "roll it to me", "roll it out of the way", "roll the spool to the wall", "roll that thing", "roll the drum",
        "roll the cable drum over there", "roll the tire", "roll it here", "roll the spool toward me", "roll the big spool"],
    "DROP": [
        "put it down", "drop it", "drop the box", "set it down", "put the crate down", "put the box down", "put the box down here",
        "leave it here", "let go of it", "drop that", "put that box down", "drop the crate", "set the box down", "put it down here",
        "let it go", "drop what you're carrying", "put down the box", "set that down", "leave the box here", "unload it",
        "put it on the floor", "drop it here", "release it", "let go of the box", "you can put it down"],
    # what the owner said in play and the bot misread (via the decoder's English), and the carry words around them
    "COLLECT": ["lift up the box", "lift up the crate", "lift up this crate", "lift that box", "pick up the cardboard box",
                "pick up this cardboard crate", "get that crate up", "grab the cardboard box", "pick that box up", "lift the box up",
                "raise the box", "pick up the small box", "grab that box", "take the cardboard box"],
    "DELIVER": ["take this cardboard crate", "take the cardboard box to me", "bring me the cardboard box", "carry the cardboard box over there",
                "take that box and bring it here", "pick up the box and bring it to me", "lift the crate and carry it over there"],
    "HOLSTER": ["bare hands", "go bare handed", "fists only", "empty handed", "no weapon in your hands", "use your bare hands",
                "put your weapon in your inventory"],
    # boundaries: the words the new intents share with the old ones, under the old ones
    "MOVE_TO": ["push forward", "push up", "push up the left side", "go get some ammo", "go find health", "go to the spool",
                "move to the box", "go to the crate"],
    "ENTRY": ["push in", "push into the room"],
    "SUPPRESS": ["push them back"],
    "GO_NOW": ["roll out", "let's roll", "we roll now"],
    "JUMP": ["drop down", "drop down there", "drop into the pit", "drop down the hole"],
    "ATTACK": ["drop him", "drop that guy"],
    "SEE_THING": ["do you see the box", "can you see the spool", "do you see the cardboard box"],
    "SMALL_TALK": ["hey", "how was your day", "what do you think of this place"],
    "NONE": ["I'm hurt", "I'm cold", "I'm low on ammo", "I see a box", "I'm pushing the box", "I dropped it", "it's hot here"],
}

SPOOL = {"id": "spool", "words": ["spool", "spools", "cable spool", "cable spools", "reel", "reels", "cable reel", "cable reels",
                                  "cable drum", "cable drums", "bobbin"]}
SPOOL_SPEC = "a big cable spool (a reel, a cable drum) on the ground: it can be rolled"
QUALIFIERS = [{"id": "big", "words": ["big", "large", "huge", "bigger", "the big", "biggest"]},
              {"id": "small", "words": ["small", "little", "tiny", "smaller", "smallest"]},
              {"id": "cardboard", "words": ["cardboard", "carton", "paper"]}]


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v63.json"), encoding="utf-8"))
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_INTENTS)
    spec["intents"]["NONE"] = none
    spec["map"]["objects"]["spool"] = SPOOL_SPEC
    spec["map"]["qualifiers"] += [q["id"] for q in QUALIFIERS]   # "the big box", "the cardboard box", "the small crate"
    spec["map"]["note"] += (" Some maps have loose things too: boxes and crates (a cardboard box, a big box) one can carry or push, "
                            "and cable spools one can roll.")
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v64.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v63.json"), encoding="utf-8"))
    notes = {k: model.pop(k) for k in [k for k in model if k.startswith("_")]}
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model.update(notes)
    model["_note_v64"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v64.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]
    assert labels == list(spec["intents"]), (labels, list(spec["intents"]))

    loc = json.load(io.open(os.path.join(HERE, "locations_v62.json"), encoding="utf-8"))
    assert all(o["id"] != "spool" for o in loc["objects"])
    loc["objects"].append(dict(SPOOL, qualifiers=["big", "small"]))
    have = {q["id"] for q in loc["qualifiers"]}
    for q in QUALIFIERS:
        assert q["id"] not in have, q
        loc["qualifiers"].append(q)
    # the objects that take them (2026-10-25 fix: the vocabulary was refused, "qualifier 'big' is allowed by no object"):
    # a box of any of the three, a spool big or small; a lone "cardboard" is a box ("the cardboard one"), a lone size nothing
    for o in loc["objects"]:
        if o["id"] == "crate":
            o["qualifiers"] = o.get("qualifiers", []) + ["big", "small", "cardboard"]
    for q in loc["qualifiers"]:
        if q["id"] in ("big", "small", "cardboard"):
            q["lone"] = "crate" if q["id"] == "cardboard" else None
    loc["version"] = 10
    loc["_note"] += (" v10 (2026-10-25, make_spec_v64.py): the object spool (cable spool, reel) and the qualifiers big, small, "
                     "cardboard (the warehouse's boxes), for the v64 bots.")
    json.dump(loc, io.open(os.path.join(HERE, "locations_v64.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v63.json"), encoding="utf-8"))
    for sid, text in RELABEL_TEXT.items():   # the index still names the line it was written for
        intent, idx = sid[len("seed_"):].rsplit("_", 1)
        assert seeds[intent][int(idx)] == text, (sid, seeds[intent][int(idx)], text)
    relabel = dict(seeds["_relabel_v63"])
    relabel.update(RELABEL_SEEDS)
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    ids = {}
    for k, v in seeds.items():
        if not k.startswith("_"):
            for n, t in enumerate(v):
                ids.setdefault(t, []).append(f"seed_{k}_{n}")
    # a seed that moves with the owner's choice (a how-are-you of small talk to the report, an are-you-okay to the body):
    # relabelled where it is, not written twice
    moves = {("SMALL_TALK", "STATUS_REPORT"), ("SMALL_TALK", "BODY_STATE"), ("SEE_THING", "STATUS_REPORT")}
    moved = []
    for k, v in NEW_SEEDS.items():
        for t in v:
            if t in owner and owner[t] != k and (owner[t], k) in moves:
                for sid in ids[t]:
                    relabel[sid] = k
                owner[t] = k
                moved.append(t)
    added, had = 0, []
    for k, v in NEW_SEEDS.items():
        assert k in labels, k
        assert len(v) == len(set(v)), (k, [t for t in v if v.count(t) > 1])
        for t in v:
            assert owner.get(t, k) == k, f"{t!r} is already a {owner[t]} seed, cannot also be {k}"
            if t in owner:
                had.append(t)
            else:
                seeds.setdefault(k, []).append(t)
                owner[t] = k
                added += 1
    seeds["_relabel_v64"] = relabel
    seeds["_note_v64"] = (f"v64 (make_spec_v64.py, before any v64 test line existed): seed set v63 + {added} seeds of "
                          "STATUS_REPORT, BODY_STATE, PUSH, ROLL, DROP, the carry words the owner's play missed (lift up, "
                          "cardboard), bare hands, and their boundaries. _relabel_v64 = _relabel_v63 + RELABEL_SEEDS "
                          "(how-are-you to STATUS_REPORT, are-you-okay to BODY_STATE, see-anything to STATUS_REPORT)")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v64.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v64: {len(spec['intents'])} intents; seeds v64: {n} (+{added}); already seeds: {had}; relabelled where they are: {moved}")
    print({k: len(v) for k, v in NEW_SEEDS.items()})


if __name__ == "__main__":
    main()
