"""
Label set v2 of the co-op bot, written BEFORE any v2 test line exists (then hashed into frozen.txt).

The owner asked for three distinctions the 22-intent set cannot make ("cover me" vs the bot covering
itself, the bot hiding while its planner picks the spot, opening a door or window without going
through). Two intents are added; nothing is removed or renamed, so every v1 label stays valid:

  TAKE_COVER  the bot protects ITSELF: hide, get into cover, get down, get out of sight; the planner
              picks the spot. (COVER_ME stays: the bot protects the PLAYER.)
  OPEN        the bot opens a door / window / hatch / gate the normal way and does not go through it.
              (VAULT_WINDOW = through a window, ENTRY = into the room, BREACH = forced with a charge.)

Each gets its own family, so a mix-up with COVER_ME / HOLD_* or with BREACH / VAULT_WINDOW counts as a
wrong-family action: that mix-up is exactly what the owner wants fixed. NONE also covers an order the
bot has no intent for (it did in practice; now it is written down for the annotators).

Writes:
  blind/spec_v2.json        what the v2 blind authors and annotators see
  intents_v2.json           the model-side vocabulary (phrase label per intent, for the bot's replies)
  seed_commands_v2.json     v1 seed commands + canonical short commands for the two new intents

    python make_spec_v2.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SPEC = {
    "TAKE_COVER": "the bot gets ITSELF into cover or out of sight to protect itself (hide, get behind "
                  "something solid, get down); its planner picks the spot: the nearest cover, or the "
                  "marker if the player points at one. Protecting the player is COVER_ME, not this",
    "OPEN": "the bot opens a door, window, hatch, gate or shutter the normal way (by hand, quietly) and "
            "does NOT go through it; its planner picks which one. Going through a window is "
            "VAULT_WINDOW, pushing into the room is ENTRY, forcing it open with a charge or tool is BREACH",
}
CHANGED = {
    "COVER_ME": "the bot covers the PLAYER (watches over them, ready to shoot) while the player moves or "
                "does something",
    "NONE": "not an order to the bot: an information callout about enemies, chatter, a question, a "
            "complaint, an order the player explicitly takes back or negates, or an order the bot has no "
            "intent for",
}
NEW_MODEL = {
    "TAKE_COVER": {"label": "take cover", "description": "hide, get into cover, get down, get out of sight"},
    "OPEN": {"label": "open it", "description": "open the door, window or hatch without going through"},
}
FAMILY_NOTE = ("v2 families: v1 families + TAKE_COVER in its own family 'cover' and OPEN in its own "
               "family 'open'")

# canonical short commands for the new intents, written by the developer before any v2 test line
# existed (like the v1 seeds: training only, never scored)
NEW_SEEDS = {
    "TAKE_COVER": ["take cover", "hide", "get to cover", "find cover", "get down", "cover yourself",
                   "get behind something", "hide somewhere"],
    "OPEN": ["open the door", "open it", "open the window", "open that door", "open this door",
             "get the door", "open the gate", "open that window"],
}
NEW_NEGATED = {"NONE": ["don't open the door", "don't open it", "don't hide", "do not take cover"],
               "WAIT": ["don't open it yet"]}


def insert_before_none(d, new):
    out = {k: v for k, v in d.items() if k != "NONE"}
    out.update(new)
    out["NONE"] = d["NONE"]
    return out


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec.json"), encoding="utf-8"))
    intents = dict(spec["intents"])
    intents.update(CHANGED)
    spec["intents"] = insert_before_none(intents, NEW_SPEC)
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents.json"), encoding="utf-8"))
    note = {k: v for k, v in model.items() if k.startswith("_")}
    body = insert_before_none({k: v for k, v in model.items() if not k.startswith("_")}, NEW_MODEL)
    note["_note_v2"] = "v2 = v1 + TAKE_COVER + OPEN (make_spec_v2.py). " + FAMILY_NOTE
    json.dump({**note, **body}, io.open(os.path.join(HERE, "intents_v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands.json"), encoding="utf-8"))
    out = {k: list(v) if isinstance(v, list) else v for k, v in seeds.items()}
    out["_note_v2"] = ("v2: seed lines for TAKE_COVER and OPEN and their negations, written before any v2 "
                       "test line existed. The owner's own live-test lines ('go find cover', 'hide there', "
                       "'open window', ...) are kept out, to test on.")
    for k, v in NEW_NEGATED.items():
        out[k] = out[k] + v
    body = insert_before_none({k: v for k, v in out.items() if not k.startswith("_")}, NEW_SEEDS)
    json.dump({**{k: v for k, v in out.items() if k.startswith("_")}, **body},
              io.open(os.path.join(HERE, "seed_commands_v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("intents:", list(spec["intents"]))
    print("seeds:", {k: len(v) for k, v in body.items()})


if __name__ == "__main__":
    main()
