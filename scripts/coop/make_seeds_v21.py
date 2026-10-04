"""
Seed set v21 = seed_commands_v2.json + COVER_ME commands with a bare "cover" (no object, or the player
as the object). Written AFTER the v2 study, because of what it showed: with "cover yourself" among the
TAKE_COVER seeds, the owner's own "cover from behid" went to TAKE_COVER (a wrong-family action: the bot
hides instead of covering the player) and "cover while moving" to "say again". In a shooter a bare
"cover" is an order to cover the player; the bot covering itself needs "yourself", "hide", "get down"...

The two owner lines are not added verbatim, but these seeds teach the same pattern, so after v21 they
are no longer a blind check. The blind test lines are untouched; train_v2.py cv with COOP_TAG=v21
measures the new seed set on them.

    python make_seeds_v21.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
COVER_ME = ["cover while I move", "cover me from behind", "cover me while I cross", "keep me covered",
            "cover my push", "cover me as I go", "cover from back there", "cover while I reload"]


def main():
    d = json.load(io.open(os.path.join(HERE, "seed_commands_v2.json"), encoding="utf-8"))
    d["_note_v21"] = ("v21: + " + str(len(COVER_ME)) + " COVER_ME seeds with a bare 'cover' (make_seeds_v21.py), "
                      "added after the v2 study showed 'cover from behid' -> TAKE_COVER")
    d["COVER_ME"] = d["COVER_ME"] + COVER_ME
    notes = {k: v for k, v in d.items() if k.startswith("_")}
    body = {k: v for k, v in d.items() if not k.startswith("_")}
    json.dump({**notes, **body}, io.open(os.path.join(HERE, "seed_commands_v21.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in body.items()})


if __name__ == "__main__":
    main()
