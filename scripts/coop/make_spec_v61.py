"""
v61: the v6x line's first round after the owner's play (bot v60 in Lyra, L_Expanse, the session of 2026-10-20 21:16). The same
57 intents as v60, the same authored lines and their readings; only seeds are added. No new test lines: the v60 lines stay
the test, and the seeds below are written with the owner's log on the table (NOT blind for the owner's own lines).

The owner: "В логах последней сессии находится общение бота, посмотри лог и начни обучение системы v61 на непонятых
фразах" (2026-10-20). In that session bot v60 said 'Say again?' on 10 of 32 lines. The readings, from the log and from the
owner's answers (AskUserQuestion, 2026-10-20):
  - "Should there" (OPEN_FIRE 0.27): "Shoot there" -- the next line, "Shoot their", was read; "should" heard for "shoot"
    is the owner's known pattern (v57: "should that windows" OPEN_FIRE). The v58/v60 comparison on the owner's earlier
    730 lines (2026-10-16..18) showed the same words lost to v60: "Should this wall?" read REPAIR 0.72 (acting wrong),
    "Should that wall?", "Should this fall?", "Should this well", "Should this ball", "Should that we lose?" 'say again'
    where v58 read OPEN_FIRE. All OPEN_FIRE;
  - "Find the enemy." (4 times, ATTACK 0.60): ATTACK -- next came "Now kill the enemy."; the v60 classifier also reads
    "go find the enemy" MOVE_TO 0.99 (as "go find ammo"), which is not what the owner means;
  - "Give him" (DELIVER 0.25): ATTACK, "Get him" (the owner); "Gilken." (GO_BACK 0.22): ATTACK, "Kill him" (the owner);
  - "Uh throw the grenade there." / "Throw the grenade there." (FRAG 0.63, under the 0.66 gate; PLANT 0.37 beside it): FRAG;
  - "Let's colour the colour." (DRONE 0.31): COVER_ME, "Cover me" (the owner);
  - "Carl." (NONE 0.33): the owner does not remember -- no seed;
  - from the v58/v60 comparison: "Shotgun." (v58 SWITCH_WEAPON 0.95, v60 0.62): SWITCH_WEAPON, a named weapon (v57 rule).
Boundaries kept: "should" in a question or advice stays as it is read ("what should we do" NONE, "you should take cover"
TAKE_COVER: v60 reads both at 0.88 and 1.00); a few NONE seeds of that kind go in with the OPEN_FIRE ones.

Writes:
  seed_commands_v61.json    seed set v60 (ids unchanged) + the seeds below; _relabel_v61 = _relabel_v60
The spec (blind/spec_v60.json), the vocabulary (intents_v60.json), the places (locations_v60.json) and the item rules
(items_v60.json) are v60's: coop_v2.py loads them for v61.

    python make_spec_v61.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_SEEDS = {
    # "should" heard for "shoot": the owner's own words first, then the same with other places
    "OPEN_FIRE": ["should there", "should their", "should this wall", "should that wall", "should this fall", "should this well",
                  "should this ball", "should this same wall", "should that we lose", "should him", "should here",
                  "should over there", "should that window", "should the door", "should that car", "should at them",
                  "should at that wall", "should it", "should them all", "uh should there"],
    "ATTACK": ["find the enemy", "find the enemies", "find an enemy", "go find the enemy", "go find the enemies",
               "find the enemy and kill him", "find them and kill them", "hunt the enemy", "hunt them down", "give him",
               "gilken", "kill him kill him", "find enemy"],
    "FRAG": ["throw the grenade there", "uh throw the grenade there", "throw the grenade over there", "throw your grenade there",
             "throw the grenade at them", "throw the grenade here", "throw the nade there", "grenade there"],
    "COVER_ME": ["let's colour the colour", "let's colour", "colour the colour", "let's cover"],
    "SWITCH_WEAPON": ["shotgun", "the shotgun", "pistol", "rifle"],
    # "should" that is no order: a question, a thought
    "NONE": ["should we push", "should I go first", "what should I do", "should we wait for them", "I should reload"],
}


def main():
    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v60.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v60"])
    labels = [k for k in json.load(io.open(os.path.join(HERE, "intents_v60.json"), encoding="utf-8")) if not k.startswith("_")]
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    added, had = 0, []
    for k, v in NEW_SEEDS.items():
        assert k in labels, k
        assert len(v) == len(set(v)), (k, [t for t in v if v.count(t) > 1])
        for t in v:
            assert owner.get(t, k) == k, f"{t!r} is already a {owner[t]} seed, cannot also be {k}"
            if t in owner:
                had.append(t)
            else:
                seeds.setdefault(k, []).append(t)       # appended: every earlier seed keeps its id (seed_<INTENT>_<n>)
                owner[t] = k
                added += 1
    seeds["_relabel_v61"] = relabel
    seeds["_note_v61"] = (f"v61 (make_spec_v61.py, with the owner's log of 2026-10-20 21:16 on the table, not blind): seed set v60 + "
                          f"{added} seeds of the lines bot v60 did not understand, under the readings the log and the owner gave "
                          "('should ...' OPEN_FIRE, 'find the enemy' / 'give him' / 'gilken' ATTACK, 'throw the grenade there' "
                          "FRAG, 'let's colour the colour' COVER_ME, 'shotgun' SWITCH_WEAPON) and a few NONE questions with "
                          "'should'. _relabel_v61 = _relabel_v60")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v61.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"seeds v61: {n} (+{added}); already seeds: {had}")


if __name__ == "__main__":
    main()
