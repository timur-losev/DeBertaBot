"""The place vocabulary v11 (locations_v65.json) = v10 (locations_v64.json) + two things from the owner's play on the test
range (L_OVTestRange, 2026-10-27):

  colours on tables   "Can you see the white table?" was "Which table? The one ahead?": the colours blue, red, yellow,
                      white and brown were the stairs' only (L_Expanse), so "white" before "table" was an unknown
                      modifier. A table takes them now; a lone colour ("the blue one") is still the stairs.
  the "it" pointer    the it_* word lists of rule set v8 (locations.py): "Jump over it." after talking about the
                      table is the table, not where the crosshair is.

Read by the v65 bot (locations.vocab_file), exported again with it on 2026-10-27. Round v66 builds v12 on it (make_spec_v66.py). No training: the classifier reads the line, not its places.
    python make_locations_v65.py
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
COLOURS = ["blue", "red", "yellow", "white", "brown"]
IT_LISTS = {
    # the pronoun
    "it_word": ["it"],
    # "jump over it", "get on it", "hide behind it", "go to it", "look at it", "get in it", "climb down it"; not "with it",
    # "for it" ("go for it"), "of it" (only after an it_of_lead word), "from it"
    "it_prep": ["over", "on", "onto", "upon", "to", "toward", "towards", "at", "behind", "through", "into", "in", "inside",
                "near", "by", "beside", "under", "underneath", "below", "beneath", "above", "around", "across", "along",
                "past", "off", "up", "down", "outside", "beyond"],
    # the verbs whose "it" is the place or the thing acted on: "open it", "shoot it", "pick it up", "push it". Not "do it",
    # "take it", "get it", "hit it", "hold it", "watch it", "use it", "put it", "drop it", "throw it", "give it"
    "it_verb": ["jump", "climb", "vault", "hop", "cross", "enter", "open", "close", "shut", "breach", "blow", "check",
                "clear", "search", "guard", "defend", "secure", "shoot", "smash", "break", "kick", "bust", "push", "roll",
                "grab", "carry", "pick", "fetch", "repair", "fix", "mend", "demolish", "dismantle"],
    # "on top of it", "in front of it", "on the other side of it"
    "it_of_lead": ["top", "front", "side"],
    # "it" as the subject of what follows: "on it's way", "by it will"
    "it_not_next": ["s", "is", "was", "will", "ll", "d", "would"],
}


def main():
    loc = json.load(io.open(os.path.join(HERE, "locations_v64.json"), encoding="utf-8"))
    assert loc["version"] == 10, loc["version"]
    for o in loc["objects"]:
        if o["id"] == "table":
            assert not o["qualifiers"], o
            o["qualifiers"] = list(COLOURS)
    assert not any(k in loc["words"] for k in IT_LISTS)
    loc["words"].update(IT_LISTS)
    loc["version"] = 11
    loc["_note"] += (" v11 (2026-10-27, make_locations_v65.py): a table takes the colours (the test range's blue, red, "
                     "yellow and white tables), and the it_* lists of rule set v8 (\"jump over it\" is the thing the talk "
                     "was about), for the v65 bot.")
    out = os.path.join(HERE, "locations_v65.json")
    json.dump(loc, io.open(out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
