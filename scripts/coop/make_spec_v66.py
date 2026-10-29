"""v66 (the owner, 2026-10-26/27): his notes after playing bots v64/v65 (stt/chains2/ml_v66/TODO_v66.md), the plan in
stt/chains2/ml_v66/PLAN_v66.md; the owner: «стартуй v66».

The owner's words and choices (2026-10-26/27):
  - "Move away, Go away, step away - бот бывает мешает пройти": a new intent; after stepping aside the bot keeps following
    ("должен идти за мной");
  - "Take it/this/that - не понимал. Throw it away не понимает. what is that/this/it - не понимает. не понимает как выйти";
  - "окно и стекло не одинаково боту, но ты должен сделать одинаково": glass is a window; «разбей стекло» is a rifle-butt
    strike (MELEE, «удар прикладом»), shooting it is OPEN_FIRE.

Two intents after DROP, before NONE:
  GIVE_WAY    step out of the player's way (and keep following): a family of its own
  WHAT_IS_IT  say what the thing the player looks at is: the family 'see' with SEE_THING and SEE_ME
The places: vocabulary v12 = v11 (locations_v65.json) + the window's words glass, pane, glass panel, window pane; the zone
outside (relative, like inside: the game finds the nearest point under open sky); the weapon a strike or a shot is made with is
no place ("with the butt of your rifle", "with your gun": "ignore").

Writes:
  intents_v66.json           the model-side vocabulary (71 intents)
  seed_commands_v66.json     seed set v65 (ids unchanged) + NEW_SEEDS; _relabel_v66 = _relabel_v65
  locations_v66.json         the place vocabulary v12

    python make_spec_v66.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_MODEL = {
    "GIVE_WAY": {"label": "get out of the way", "description": "step aside out of the player's way, then keep following"},
    "WHAT_IS_IT": {"label": "say what that is", "description": "name the thing the player is looking at"},
}
# seeds of v65 under another intent from v66 on (seed_<intent>_<index in seed_commands_v65.json>): the owner's «дай пройти»
# went to HELP_INTERACTION, and the bot walked up to him asking what to do
RELABEL_SEEDS = {"seed_HELP_INTERACTION_16": "GIVE_WAY"}
RELABEL_TEXT = {"seed_HELP_INTERACTION_16": "let me through"}
FAMILY_NOTE = ("v66 families: v64's; GIVE_WAY in a family of its own (give_way), WHAT_IS_IT in 'see' with SEE_THING and SEE_ME. "
               "They come after DROP, before NONE")

NEW_SEEDS = {
    "GIVE_WAY": [
        "move away", "go away", "step away", "move aside", "step aside", "get out of the way", "get out of my way", "you're in my way",
        "you are in my way", "you're in the way", "out of the way", "out of my way", "let me through", "let me pass", "let me by",
        "let me get by", "move over", "scoot over", "make way", "make room", "clear the way", "clear the path", "you're blocking me",
        "you're blocking the way", "you're blocking the door", "stop blocking me", "don't block me", "don't stand in my way",
        "quit standing in the way", "step to the side", "move to the side", "get to the side", "move out of the way",
        "move out of my way", "step out of the way", "step out of my way", "get out the way", "outta the way", "outta my way",
        "move, you're in the way", "make some room", "give me some room", "give me some space", "shift over", "budge up",
        "move, you're blocking", "excuse me, coming through", "coming through", "get away from me", "go away, i'm busy",
        "go away bro", "move bro, you're in my way", "step aside bro", "you're right in my way", "stop getting in my way",
        "don't get in my way", "move away from me", "step back, you're in my way", "let me through bro", "can you move",
        "could you move out of the way", "move out the way", "get out of the doorway", "you're standing in the doorway",
        "move, let me pass"],
    "WHAT_IS_IT": [
        "what is that", "what's that", "what is this", "what's this", "what is it", "what's that thing", "what is that thing",
        "what's this thing", "what is this thing", "what am i looking at", "what am i aiming at", "what's that over there",
        "what is that over there", "what's that right there", "what's this here", "what kind of thing is that",
        "what kind of object is that", "what the hell is that", "what the heck is this", "what's that object", "identify that",
        "identify this", "what is this object", "do you know what that is", "tell me what that is", "what's that supposed to be",
        "what's this stuff", "what's that stuff", "what's that thing on the floor", "what's that there", "what are those",
        "what are these", "what's this one", "what's that one", "what is that one", "what do you call that", "what's that called",
        "what's this called", "hey what is that", "bro what's that", "what is that thing over there", "what's that in front of me"],
    # take with a pronoun: keep it (the owner, 2026-10-25: take = keep); the way words stay a move
    "COLLECT": ["take it", "take this", "take that", "take this one", "take that one", "grab it", "grab this", "grab that",
                "take it with you", "pick this up", "pick that up", "take it and hold it", "you take it", "grab this one",
                "take the books", "grab the chair"],
    "MOVE_TO": ["take this way", "take that road", "take that path", "take the left path", "take this route", "take the stairs up",
                "go outside", "get outside", "head outside", "step outside", "get out of the room", "leave the room", "exit the room",
                "get out of the building", "leave the building", "go outdoors", "move outside", "get out of this room",
                "go out of the room", "let's go outside", "go outside and wait", "go up on this platform", "go on top of this platform"],
    "DROP": ["toss it away", "chuck it away", "throw it out", "throw that", "throw this away", "chuck that", "toss that", "bin it",
             "ditch it", "ditch the box", "get rid of that", "throw the box", "just throw it", "throw it away now"],
    # glass is a window: shooting it is firing, breaking it is a butt strike (the owner's choice, 2026-10-27)
    "OPEN_FIRE": ["shoot the glass", "shoot that glass", "shoot this glass", "shoot through the glass", "shoot through that glass",
                  "shoot the pane", "shoot the glass panel", "fire at the glass", "shoot out the glass", "blast the glass",
                  "put a round in the glass", "shoot the window", "shoot that window", "shoot out the window", "fire at the window",
                  "just shoot it", "shoot it", "no, shoot it", "no, use your gun, shoot it", "shoot the glass with your rifle"],
    "MELEE": ["break the glass", "break that glass", "smash the glass", "smash the window", "break the window", "break that window",
              "smash that window", "knock out the glass", "bust the glass", "bust the window", "hit the glass with your rifle butt",
              "hit the window with the butt of your rifle", "butt stroke the glass", "smash the glass with your gun", "crack the glass",
              "hit the glass", "smash it with the butt", "hit it with the butt of your rifle", "no, hit it with the butt",
              "break the glass with the butt of your gun", "smash the glass panel", "break the pane"],
    "BREACH": ["breach the door", "blow the door", "breach that wall"],
    "SMALL_TALK": ["you're my brother", "you are my brother", "you're my bro", "you're my brother man", "we're brothers",
                   "brothers for life", "what was that", "what was that noise", "what was that sound"],
    "STATUS_REPORT": ["how we doing bro", "how we doing", "how you doing homie", "how are we doing", "how's it looking bro"],
    "PUSH": ["press it forward", "press it ahead", "press the box forward"],
    "GET_OUT": ["get out of the car", "get out of the truck"],
    "FALL_BACK": ["get out of here", "get the hell out of here"],
    "SEE_THING": ["can you see this wall", "can you see the white table", "can you see the red table", "do you see that thing"],
    "YES": ["yeah the one right in front of you", "yes that one", "right in front of you, yes"],
}

# vocabulary v12 (on v11, locations_v65.json)
WINDOW_WORDS = ["glass", "pane", "panes", "glass panel", "glass panels", "window pane", "window panes", "glass pane", "glass panes",
                "windowpane", "windowpanes"]
OUTSIDE = {"id": "outside", "words": ["outside", "outdoors", "out of the room", "out of the building", "out of this room",
                                       "out of the house", "out of this building", "out of the rooms",
                                       # the verb with its room: "leave the room" names no place otherwise ("the room" is none)
                                       "leave the room", "leave this room", "leave the building", "exit the room", "exit the building"]}
IGNORE = ["butt of your rifle", "butt of the rifle", "butt of your gun", "butt of the gun", "rifle butt", "gun butt",
          "with your rifle", "with the rifle", "with your gun", "with the gun", "with your weapon", "with the weapon"]


def main():
    model = json.load(io.open(os.path.join(HERE, "intents_v64.json"), encoding="utf-8"))
    notes = {k: model.pop(k) for k in [k for k in model if k.startswith("_")]}
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model.update(notes)
    model["_note_v66"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v66.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v65.json"), encoding="utf-8"))
    for sid, text in RELABEL_TEXT.items():   # the index still names the line it was written for
        intent, idx = sid[len("seed_"):].rsplit("_", 1)
        assert seeds[intent][int(idx)] == text, (sid, seeds[intent][int(idx)])
    have = {}
    for intent, lines in seeds.items():
        if not intent.startswith("_"):
            for n, t in enumerate(lines):
                have.setdefault(t.strip().lower(), RELABEL_SEEDS.get(f"seed_{intent}_{n}", intent))
    added, clash = 0, []
    for intent in NEW_SEEDS:
        seeds.setdefault(intent, [])
    for intent, lines in NEW_SEEDS.items():
        assert intent in labels, intent
        for t in lines:
            was = have.get(t.strip().lower())
            if was is not None:
                if was != intent:
                    clash.append((t, was, intent))
                continue
            seeds[intent].append(t)
            have[t.strip().lower()] = intent
            added += 1
    assert not clash, "seeds of another intent already: " + "; ".join(f"{t!r} {a}->{b}" for t, a, b in clash)
    # keep the label order of the model file for the intents (json order is what loaders iterate)
    ordered = {k: seeds[k] for k in labels if k in seeds}
    ordered.update({k: v for k, v in seeds.items() if k not in ordered})
    ordered["_relabel_v66"] = dict(seeds["_relabel_v65"], **RELABEL_SEEDS)
    ordered["_note_v66"] = ("v66 (make_spec_v66.py, 2026-10-27): seed set v65 with its ids, + GIVE_WAY and WHAT_IS_IT, take it / this / "
                            "that (COLLECT), throw it (DROP), glass is a window (shooting it OPEN_FIRE, breaking it MELEE), going "
                            "outside (MOVE_TO), and the boundaries.")
    json.dump(ordered, io.open(os.path.join(HERE, "seed_commands_v66.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    loc = json.load(io.open(os.path.join(HERE, "locations_v65.json"), encoding="utf-8"))
    assert loc["version"] == 11, loc["version"]
    for o in loc["objects"]:
        if o["id"] == "window":
            o["words"] += [w for w in WINDOW_WORDS if w not in o["words"]]
    assert all(z["id"] != "outside" for z in loc["zones"])
    loc["zones"].append(OUTSIDE)
    loc["ignore"] += [p for p in IGNORE if p not in loc["ignore"]]
    loc["version"] = 12
    loc["_note"] += (" v12 (2026-10-27, make_spec_v66.py): glass is a window (glass, pane, glass panel, window pane), the zone outside "
                     "(the game finds the nearest point under open sky), the weapon a strike or a shot is made with is no place; for the "
                     "v66 bots.")
    json.dump(loc, io.open(os.path.join(HERE, "locations_v66.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in ordered.items() if not k.startswith("_"))
    print(f"intents_v66.json: {len(labels)} intents; seed_commands_v66.json: {n} seeds (+{added}); locations_v66.json: version 12")


if __name__ == "__main__":
    main()
