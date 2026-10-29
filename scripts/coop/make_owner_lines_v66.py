"""The owner's spoken English lines heard since owner_lines_v65.json (2026-10-25 22:04 .. 2026-10-27 01:20; the warehouse yard
and the test range L_OVTestRange), labelled by hand from the talk around each line (owner_lines_v66_candidates.json, written by
extract_owner_lines_v66.py) -> owner_lines_v66.json.

Left out: lines of the Russian sessions that the multilingual recognizer wrote in Latin letters ("Zaprygnę się na prapę.",
"Idzi ka mnie soda.": the decoder's data, chains2/ml_v66/hand_v66.json), fragments and words that say nothing ("King.",
"Good air.", "Filled it up."), answers that are only a place ("Blue Table", "Here."), and lines already in the earlier owner
files. The owner's choices applied: take it / this / that is COLLECT (2026-10-25: take = keep); move away / go away is GIVE_WAY
(2026-10-26); going up onto the test range's 3 m platform is a walk there (MOVE_TO), not a jump. 'sure': false where a word was
misheard ("Mood here." for "move here", "Put the dare." for "put it there", "Hard weapon." for "hide weapon").

    python make_owner_lines_v66.py"""
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
# heard text (as the candidates file has it) -> (label, sure)
LABELS = {
    "Roll it.": ("ROLL", True), "You stay there.": ("HOLD_POSITION", True), "Go there.": ("MOVE_TO", True),
    "Jump on it.": ("JUMP", True), "Take it.": ("COLLECT", True), "Take that box.": ("COLLECT", True),
    "Throw it away.": ("DROP", True), "Take this.": ("COLLECT", True), "Go inside that room.": ("MOVE_TO", True),
    "Take the books.": ("COLLECT", False), "Move away.": ("GIVE_WAY", True), "Fallback.": ("FALL_BACK", True),
    "Go away.": ("GIVE_WAY", True), "Go up by by there.": ("MOVE_TO", True), "Find the way there.": ("MOVE_TO", True),
    "Find a way there.": ("MOVE_TO", True), "find a way there.": ("MOVE_TO", True), "Jump down from from there.": ("JUMP", True),
    "Find a way here.": ("MOVE_TO", True), "Find a way, dear.": ("MOVE_TO", False),
    "Take that box and move it out there.": ("DELIVER", True), "Take this box.": ("COLLECT", True), "Move down there.": ("MOVE_TO", True),
    "Drop it.": ("DROP", True), "Jump on this.": ("JUMP", True), "Come back.": ("COME_BACK", True), "Jump down from there.": ("JUMP", True),
    "Go here.": ("MOVE_TO", True), "Go to that window.": ("MOVE_TO", True),
    "Don't call me bro.": ("SMALL_TALK", True), "Go up by the stairs.": ("MOVE_TO", True), "Further up": ("MOVE_TO", True),
    "No move here now.": ("MOVE_TO", False), "Move here now.": ("MOVE_TO", True), "Come here.": ("FOLLOW_ME", True),
    "Open the door.": ("OPEN", True), "Come inside.": ("MOVE_TO", True), "Follow me.": ("FOLLOW_ME", True),
    "Jump on the blue table.": ("JUMP", True), "Jump, come come to me.": ("JUMP", True), "Jump to me.": ("JUMP", True),
    "Go go to me.": ("FOLLOW_ME", True), "Come to me.": ("FOLLOW_ME", True), "Come closer to me.": ("FOLLOW_ME", True),
    "Stay there.": ("HOLD_POSITION", True), "Thank you.": ("SMALL_TALK", True), "Grab that box.": ("COLLECT", True),
    "Hide weapon.": ("HOLSTER", True), "Hide the weapon.": ("HOLSTER", True), "Hard weapon.": ("HOLSTER", False),
    "Hide weapon": ("HOLSTER", True), "Grab the box.": ("COLLECT", True), "Mood here.": ("MOVE_TO", False),
    "Kill yourself.": ("KILL_YOURSELF", True), "Put the dare.": ("DELIVER", False), "Put it there.": ("DELIVER", True),
    "Jump onto it.": ("JUMP", True), "Drop that box.": ("DROP", True), "And take this box.": ("COLLECT", True),
    "Uh follow me.": ("FOLLOW_ME", True), "Stop.": ("WAIT", True), "Open that room.": ("OPEN", True),
    "Clear the trump.": ("ENTRY", False), "Clear that room.": ("ENTRY", True), "Grab the chair.": ("COLLECT", True),
    "Don't call me bra.": ("SMALL_TALK", False), "Don't call me a bra.": ("SMALL_TALK", False),
    "Go up on this platform.": ("MOVE_TO", True), "Go on top of this platform.": ("MOVE_TO", True),
    "Go uh go up by blue stairs.": ("MOVE_TO", True), "Go to the roof.": ("MOVE_TO", True), "What is your name?": ("SMALL_TALK", True),
    "Can you see this wall?": ("SEE_THING", True), "What can we see inside?": ("STATUS_REPORT", False),
    "What can you see in round?": ("STATUS_REPORT", False), "Come back to me.": ("COME_BACK", True), "Go inside.": ("MOVE_TO", True),
    "Can you see the floor?": ("SEE_THING", True), "Can you see the screen?": ("SEE_THING", True),
    "Can you see the stable?": ("SEE_THING", False), "Can you see this red table?": ("SEE_THING", True),
    "Can you see white table?": ("SEE_THING", True), "Turn around.": ("LOOK_AT", True), "Can you see the white table?": ("SEE_THING", True),
    "No, no.": ("NO", True), "Yes.": ("YES", True), "No.": ("NO", True), "So go to there.": ("MOVE_TO", True),
    "Can you see the red table?": ("SEE_THING", True), "Uh can you see the white table?": ("SEE_THING", True),
    "So jump over it.": ("JUMP", True), "Come back to me closer.": ("COME_BACK", True), "Jump down to me.": ("JUMP", True),
    "Come come back to me": ("COME_BACK", True), "Can you see the yellow table?": ("SEE_THING", True),
    "Come over it.": ("JUMP", False), "So come over it.": ("JUMP", False), "Jump over it.": ("JUMP", True),
}
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()   # noqa: E731


def main():
    cands = json.load(io.open(os.path.join(HERE, "owner_lines_v66_candidates.json"), encoding="utf-8"))
    old = {norm(o["text"]) for f in ("owner_lines_v61.json", "owner_lines_v64.json", "owner_lines_v65.json")
           for o in json.load(io.open(os.path.join(HERE, f), encoding="utf-8"))["items"]}
    by = {}
    for c in cands:
        if c["text"] not in LABELS:
            continue
        label, sure = LABELS[c["text"]]
        key = norm(c["text"])
        if key in old:
            continue
        it = by.setdefault(key, {"text": key, "maj": label, "count": 0, "said": [], "multi": False, "sure": sure})
        assert it["maj"] == label, (key, it["maj"], label)
        it["count"] += 1
        it["said"].append(c["time"][:16])
    missing = sorted(set(LABELS) - {c["text"] for c in cands})
    assert not missing, missing
    items = [dict(id=f"owner66_{n + 1:04d}", **it) for n, it in enumerate(sorted(by.values(), key=lambda i: i["said"][0]))]
    note = ("The owner's own spoken English lines as Parakeet heard them in the game, 2026-10-25 22:04 .. 2026-10-27 01:20 (the "
            "warehouse yard; the test range), after owner_lines_v65.json (extract_owner_lines_v66.py -> owner_lines_v66_candidates.json, "
            "labelled by hand from the talk around each line: make_owner_lines_v66.py). Choices applied: take it / this / that = "
            "COLLECT; move away / go away = GIVE_WAY; going up onto the 3 m platform = MOVE_TO. 'sure': false where a word was misheard.")
    json.dump({"_note": note, "items": items}, io.open(os.path.join(HERE, "owner_lines_v66.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"owner_lines_v66.json: {len(items)} lines ({sum(i['count'] for i in items)} times said), {sum(not i['sure'] for i in items)} not sure;",
          dict(Counter(i["maj"] for i in items)))


if __name__ == "__main__":
    main()
