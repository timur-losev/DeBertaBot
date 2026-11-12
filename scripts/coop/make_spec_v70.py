"""v70 (the owner, 2026-11-08 and 2026-11-11): the body's commands and driving by voice. Plan:
stt/chains2/ml_v70/TODO_v70.md (the owner's words, his choices, the canon in its section 10).

Three intents after WHAT_IS_IT, before NONE:
  DRIVE        a car's order: on to the next junction, a turn at a junction (the Nth of a side), turning round, to a place by the
               roads, pulling over, faster, slower, stopping the car. Said on foot, the game gets into the nearest free car first.
               What the line asks the game reads from the canonical line itself (OVCoop::DriveFromWords); the place is grounded
               as any order's. A family of its own (drive): never a walk ("move") nor getting in.
  BODY_MOVE    a body part moved, or a strike in place with no one to hit; the canonical line IS the game's body command
               ("raise arm_r 90 left 20 speed 2", "hook left hard"). A family of its own (body_move; "body" is BODY_STATE's).
  BODY_COMBO   a combo of body moves taught, played, forgotten, listed ("teach двойка = jab ; punch", "play двойка", "forget
               двойка", "combos"). Its own family (body_combo).
The boundaries kept: a strike at someone ("punch him") stays MELEE; "kneel" / "take a knee" stay CROUCH; "turn around" on foot
stays LOOK_AT ("turn the car around" is DRIVE); a bare "stop" stays WAIT; "lower your weapons" stays HOLD_FIRE.

Writes:
  intents_v70.json           the model-side vocabulary (74 intents)
  seed_commands_v70.json     seed set v67 (ids unchanged) + NEW_SEEDS; _relabel_v70 = _relabel_v67
(the place vocabulary v16 is make_places_v70.py's)

    python make_spec_v70.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_MODEL = {
    "DRIVE": {"label": "drive the car", "description": "drive a car along the roads: on to the next junction, turn left or right at "
              "a junction, turn round, drive to a place, pull over, faster, slower, stop the car"},
    "BODY_MOVE": {"label": "move a body part", "description": "raise, lower, turn or tilt an arm, a leg, the head, the torso or the whole "
                  "body by an angle, or strike in place (punch, hook, uppercut, elbow, kick, knee, headbutt) with no one to hit"},
    "BODY_COMBO": {"label": "teach or play a combo", "description": "teach a named combo of body moves, play it, forget it, or list the "
                   "combos taught"},
}
FAMILY_NOTE = ("v70 families: v66's; DRIVE in a family of its own (drive), BODY_MOVE (body_move) and BODY_COMBO (body_combo) each "
               "their own ('body' is BODY_STATE's). They come after WHAT_IS_IT, before NONE")

NEW_SEEDS = {
    "DRIVE": [
        # on to the next junction
        "drive forward", "drive straight", "drive straight on", "drive on", "keep driving", "carry on driving", "just drive",
        "start driving", "let's drive", "drive ahead", "drive to the next junction", "drive to the next crossroads",
        "drive on to the intersection", "drive straight ahead", "go straight on in the car", "drive straight through the junction",
        "drive forward to the junction", "keep going straight, drive", "drive, keep going", "drive",
        # turns
        "turn left at the next junction", "turn right at the next junction", "turn left at the crossroads",
        "turn right at the crossroads", "turn left at the intersection", "turn right at the intersection", "take the next left",
        "take the next right", "take the first left", "take the first right", "take the second left", "take the second right",
        "take the third left", "take the third right", "turn left at the second junction", "turn right at the second junction",
        "turn left at the third crossroads", "left at the junction", "right at the junction", "left at the next crossroads",
        "right at the next intersection", "hang a left at the junction", "hang a right at the next junction",
        "make a left at the crossroads", "make a right at the intersection", "next left", "next right", "second left",
        "second right", "turn left at the next junction and drive on", "at the junction turn left", "at the crossroads go right",
        # turning round
        "turn the car around", "turn the car round", "make a u-turn", "do a u-turn", "u-turn", "u-turn here", "flip a u-turn",
        "turn around and drive back", "drive back the other way", "turn the car around and drive back",
        # to a place
        "drive to the bank", "drive to the restaurant", "drive me to the bank", "drive us to the hotel", "drive me to the restaurant",
        "give me a ride to the bank", "give us a ride to the cafe", "take me to the bank by car", "drive to my pin", "drive to the pin",
        "drive there", "drive over there", "drive to that building", "drive to the cafe", "drive to the shop", "drive to the pharmacy",
        "drive to the gas station", "drive to the parking", "drive to the end of the road", "drive to the main door",
        "drive to the junction", "drive to the crossroads", "drive to the traffic light", "drive to that place", "drive us there",
        "drive me home to the hotel", "drive to the store", "drive up to the bank",
        # pulling over
        "park the car", "park here", "park over there", "pull over", "pull over here", "park at the curb", "pull up at the curb",
        "park by the sidewalk", "find a parking spot", "park it", "park somewhere", "pull over to the side",
        # faster, slower
        "drive faster", "speed up", "step on it", "floor it", "go faster", "put your foot down", "hurry up and drive", "faster, drive faster",
        "drive slower", "slow down", "slow the car down", "ease off", "don't drive so fast", "take it easy on the gas", "drive slowly",
        "slow down a bit", "not so fast",
        # stopping the car
        "stop the car", "brake", "hit the brakes", "brake now", "stop driving", "stop the car here", "brake hard"],
    "BODY_MOVE": [
        # the console's lines (the canon)
        "raise arm_r", "raise arm_l", "raise arm_r 90", "raise arm_l 45", "raise arms", "raise arms 180", "raise arms 90 out 90",
        "raise arm_r 90 left 20", "raise arm_r 90 left 20 speed 2", "raise arms 170 sharp 1", "lower arms", "lower arm_r",
        "lower arm_l", "raise leg_r", "raise leg_l", "raise leg_r 60 bend 40", "lower legs", "turn head left", "turn head right",
        "turn head left 45", "turn head right 30 up 20", "turn head left up 20", "tilt head right", "tilt head left 20",
        "lower head", "raise head", "lower torso", "lower torso 40", "lower torso 40 right 20", "raise torso", "turn torso left",
        "turn torso right 30", "tilt torso right 20", "turn body left 90", "turn body right 90", "turn body left 45 speed 2",
        "lower body 90", "lower body 60", "raise body", "bow", "relax all", "relax arms", "relax head", "relax", "relax legs",
        "speed 2", "speed 0.5", "sharp 1", "sharp 0",
        "punch", "punch hard", "punch left", "jab", "hook left", "hook right", "hook left high", "hook left hard speed 1.5",
        "uppercut", "uppercut left", "elbow", "elbow left", "kick", "kick high", "kick left", "kick force 1.5", "sidekick",
        "sidekick left", "knee", "knee left", "headbutt", "butt", "punch soft", "kick hard",
        # the same in plain words
        "raise your right arm", "raise your left arm", "raise both arms", "put your arms up", "arms up", "hands up high",
        "spread your arms", "arms out to the sides", "lower your arms", "put your arm down", "raise your right leg",
        "lift your left leg", "turn your head to the left", "turn your head right", "tilt your head", "nod your head down",
        "bend forward", "lean forward", "lean to the left", "lean right", "squat down ninety degrees", "turn your whole body left",
        "turn your body ninety degrees right", "throw a punch", "do a left hook", "do an uppercut", "punch the air", "kick the air",
        "show me a kick", "do a front kick", "do a side kick", "knee strike", "elbow strike", "headbutt the air",
        "strike with your rifle butt in the air", "raise your arm fast", "raise your arm slowly", "punch hard and fast",
        "relax your body", "stand normally", "loosen up", "at ease with your arms"],
    "BODY_COMBO": [
        "teach one_two = jab ; punch", "teach combo double = jab ; punch hard", "teach boxer = jab ; hook left ; uppercut",
        "teach salute = raise arm_r 150 ; wait 1 ; lower arm_r", "teach двойка = jab ; punch", "teach тройка = jab ; punch ; hook left",
        "play one_two", "play combo double", "play boxer", "play двойка", "play the combo salute", "forget one_two",
        "forget combo double", "forget the combo boxer", "forget двойка", "combos", "list the combos", "what combos do you know",
        "which combos do you know", "show me your combos", "remember this combo: jab, then a punch", "learn a combo called double: jab, punch",
        "make a combo named boxer: jab, hook, uppercut", "do the combo one_two", "do your combo двойка", "show me the combo boxer",
        "perform the combo salute", "run the combo double", "delete the combo boxer", "drop the combo one_two",
        "erase the combo salute", "new combo kicker: kick ; knee ; kick high", "teach combo kicker = kick ; knee",
        "save this combo as wave: raise arm_r 160 ; lower arm_r", "how many combos do you know", "play combo тройка",
        "forget combo тройка", "teach combo guard = raise arms 70 in 20 bend 110"],
}
# The canon's turns (TODO_v70.md section 10), added 2026-11-11 after bot v70's first build: a plain turn to a side is LOOK_AT
# (the v6x bots' reading of «повернись налево» / "turn left"; bot v70 without these read it BODY_MOVE, which the game's body
# refused for want of a part), a turn with an angle and no part named is the whole body's (BODY_MOVE). Appended at the end of
# each intent's list: the ids and the audio of the seeds before them stay. None of them is a test line.
NEW_SEEDS["LOOK_AT"] = [
    "turn to the left", "turn to the right", "turn to your left", "turn to your right", "turn left a bit", "turn right a little",
    "turn a bit to the left", "turn left and look", "turn right and look there", "face to the left", "face to the right",
    "turn leftwards", "turn rightwards", "turn left, look over there", "turn right, check it out"]
NEW_SEEDS["BODY_MOVE"] += [
    "turn left 90", "turn right 45", "turn left 180", "turn right ninety degrees", "turn left by 30 degrees", "turn right 120 speed 2",
    "turn left 60 degrees", "turn right by 90"]
# bot v70c: the decoder's own words for a plain turn («повернись налево» -> "turn left", the canon), which bot v70b, with only the
# longer ways of saying it, still could not tell from "turn left 90" ("Say again?"). "turn left" is the blind test's d_en_016
# (test_v70_new.json): that item is no longer blind.
NEW_SEEDS["LOOK_AT"] += ["turn left", "turn right", "now turn left", "now turn right", "turn left please", "turn right please"]


def main():
    model = json.load(io.open(os.path.join(HERE, "intents_v66.json"), encoding="utf-8"))
    notes = {k: model.pop(k) for k in [k for k in model if k.startswith("_")]}
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model.update(notes)
    model["_note_v70"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v70.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v67.json"), encoding="utf-8"))
    have = {}
    for intent, lines in seeds.items():
        if not intent.startswith("_"):
            for t in lines:
                have.setdefault(t.strip().lower(), intent)
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
    ordered = {k: seeds[k] for k in labels if k in seeds}
    ordered.update({k: v for k, v in seeds.items() if k not in ordered})
    ordered["_relabel_v70"] = dict(seeds["_relabel_v67"])
    ordered["_note_v70"] = ("v70 (make_spec_v70.py, 2026-11-11): seed set v67 with its ids, + DRIVE, BODY_MOVE (the body command lines "
                            "and plain words), BODY_COMBO (teach / play / forget / list).")
    json.dump(ordered, io.open(os.path.join(HERE, "seed_commands_v70.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in ordered.items() if not k.startswith("_"))
    print(f"intents_v70.json: {len(labels)} intents; seed_commands_v70.json: {n} seeds (+{added})")


if __name__ == "__main__":
    main()
