"""
v63: the bot fights hand to hand and puts its weapon away (the owner, 2026-10-24). Written BEFORE any v63 test line exists
(then hashed into frozen.txt).

The owner's words: "Надо добавить агрессивные интенты типа - отпизди его, дай ему пизды, наваляй ему и тд. а так же аналоги на
англ и тд. У бота должны появиться режим свободные руки, либо он нанесёт мили атаку в NPC. Вообще свободные руки и у персонажа
есть, но ему надо выкинуть все оружие. А хочется что бы можно было просто убрать всё в инвентарь". Their choices
(AskUserQuestion, 2026-10-24): the bot hits enemies and neutral NPCs, never the player or its team; it hits with what it holds
(fists with free hands, the butt of its gun otherwise: Lyra's GA_Melee); the player's key to put weapons away and back is H.

Two intents after KILL_YOURSELF, before NONE, each in a family of its own:
  MELEE    the bot goes to someone and beats them up hand to hand: punches, kicks, the butt of its gun (beat him up, punch him,
           kick his ass, smack him, rough him up, knock him out, «отпизди его», «наваляй ему» as the decoder writes them)
  HOLSTER  the bot puts its weapon away, hands free (put your gun away, holster it, hands free, stow your rifle)
Boundaries kept: shooting or attacking with no way said is ATTACK / OPEN_FIRE ("take him out", "kill him", "light him up");
"hit the deck / the dirt" PRONE, "hit the switch" HELP_INTERACTION, "hit them from behind" FLANK; taking a weapon out is
SWITCH_WEAPON ("draw your weapon", "take out your pistol", "gun up"); "lower your weapons" / "weapons down" stop the shooting
(HOLD_FIRE); "kill yourself" KILL_YOURSELF.

Writes:
  blind/spec_v63.json        the v62 spec with the two intents and the boundaries
  intents_v63.json           the model-side vocabulary (64 intents)
  seed_commands_v63.json     seed set v62 (ids unchanged) + the seeds below; _relabel_v63 = _relabel_v62
The places (locations_v62.json, vocabulary v9) and the item rules stay v62's.

    python make_spec_v63.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_INTENTS = {
    "MELEE": (
        "the bot fights someone hand to hand: goes up to them and beats them up with what it has in its hands, fists or the "
        "butt of its gun (beat him up, punch him, kick his ass, smack him, slap him, rough him up, knock him out, punch his "
        "lights out, melee him, give him a beating, beat the crap out of him, hit him with your fist, knife him). The target "
        "is the person the player points at or names (an enemy or a bystander). Attacking or shooting with no way said is "
        "ATTACK or OPEN_FIRE ('take him out', 'kill him', 'light him up', 'put rounds on him'); 'hit the deck' / 'hit the "
        "dirt' is PRONE, 'hit the switch' HELP_INTERACTION, 'hit them from behind' FLANK"),
    "HOLSTER": (
        "the bot puts its weapon away and has its hands free; the weapon stays in its inventory (put your gun away, holster "
        "your weapon, hands free, stow your rifle, put it away, no guns, go unarmed, sling your rifle). Taking a weapon out "
        "again is SWITCH_WEAPON ('draw your weapon', 'take out your pistol', 'gun up'); 'lower your weapons' / 'weapons "
        "down' / 'don't shoot' stop the shooting and are HOLD_FIRE"),
}
APPENDED = {
    "ATTACK": (". Fighting hand to hand ('beat him up', 'punch him', 'kick his ass') is MELEE"),
    "OPEN_FIRE": ". Hitting someone with fists or the butt of a gun is MELEE",
    "SWITCH_WEAPON": (". Putting the weapon away with nothing in its place ('put your gun away', 'holster it', 'hands free') "
                      "is HOLSTER; taking one out again ('draw your weapon', 'gun up') is this intent"),
    "HOLD_FIRE": ". Putting the weapon away ('put your gun away', 'holster it') is HOLSTER",
    "NONE": (". A fight the PLAYER is in ('I'm punching him', 'he hit me') is a callout, NONE; telling the bot to beat someone "
             "up is MELEE"),
}
NEW_MODEL = {
    "MELEE": {"label": "beat him up", "description": "fight someone hand to hand: fists or the butt of the gun"},
    "HOLSTER": {"label": "put the weapon away", "description": "put the weapon away, hands free"},
}
FAMILY_NOTE = ("v63 families: v62's; MELEE and HOLSTER each in a family of their own (melee, holster). They come after "
               "KILL_YOURSELF, before NONE")

NEW_SEEDS = {
    "MELEE": [
        "beat him up", "beat them up", "beat that guy up", "punch him", "punch that guy", "punch him in the face", "kick his ass",
        "kick their ass", "kick the shit out of him", "beat the shit out of him", "beat the crap out of him", "smack him",
        "slap him", "smack that guy", "rough him up", "knock him out", "knock him down", "punch his lights out",
        "give him a beating", "give him a good beating", "melee him", "melee that guy", "hit him with your fist",
        "hit him with your gun", "hit him with the butt", "butt stroke him", "pistol whip him", "knife him", "stab him",
        "fuck him up", "go fuck him up", "mess him up", "beat his ass", "whoop his ass", "kick him", "kick that guy",
        "kick him in the head", "punch the guard", "beat up the guard", "go punch him", "go beat him up", "smash his face in",
        "knock his teeth out", "teach him a lesson", "give him a punch", "give him a slap", "hit him hard with your fists",
        "use your fists", "fight him", "go fight that guy", "fist fight him", "box him", "headbutt him", "elbow him",
        "take him down with your fists", "beat him up but don't shoot", "punch him don't shoot", "melee attack",
        "do a melee attack", "melee", "hit him in the face", "beat that npc up", "punch the npc", "slap that dude",
        "kick his butt", "kick that guy's butt", "hit him hard"],
    "HOLSTER": [
        "put your gun away", "put your weapon away", "put the gun away", "put your rifle away", "put it away", "put away your gun",
        "holster your weapon", "holster your gun", "holster it", "holster", "holster your pistol", "hands free", "free your hands",
        "get your hands free", "stow your rifle", "stow your weapon", "stow it", "sling your rifle", "no guns", "go unarmed",
        "put the guns away", "put all your weapons away", "weapons in the bag", "put your gun in your bag", "pocket your pistol",
        "no weapons out", "unequip your weapon", "unequip", "empty hands", "keep your hands empty", "put down your gun but keep it",
        "guns away", "put the rifle on your back", "carry nothing in your hands", "holster up"],
    # boundaries: the words the new intents share with the old ones, under the old ones
    "ATTACK": ["take him out", "kill him", "take that guy out", "attack him", "engage him", "hit them"],
    "OPEN_FIRE": ["light him up", "put rounds on him", "shoot him", "open fire on him"],
    "SWITCH_WEAPON": ["draw your weapon", "take out your gun", "take out your pistol", "gun up", "get your gun out", "arm yourself",
                      "pull out your rifle", "weapons out"],
    "HOLD_FIRE": ["lower your weapons", "weapons down", "lower your gun", "don't shoot him"],
    "PRONE": ["hit the deck", "hit the dirt", "hit the floor"],
    "NONE": ["I'm punching him", "he hit me", "he punched me", "I beat him up", "nice punch", "I'll punch him"],
}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v62.json"), encoding="utf-8"))
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_INTENTS)
    spec["intents"]["NONE"] = none
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v63.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v62.json"), encoding="utf-8"))
    notes = {k: model.pop(k) for k in [k for k in model if k.startswith("_")]}
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model.update(notes)
    model["_note_v63"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v63.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]
    assert labels == list(spec["intents"]), (labels, list(spec["intents"]))

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v62.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v62"])
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
                seeds.setdefault(k, []).append(t)
                owner[t] = k
                added += 1
    seeds["_relabel_v63"] = relabel
    seeds["_note_v63"] = (f"v63 (make_spec_v63.py, before any v63 test line existed): seed set v62 + {added} seeds of MELEE, "
                          "HOLSTER and their boundaries (attack and shoot, take a weapon out, lower the weapons, hit the deck, "
                          "the player's own fight). _relabel_v63 = _relabel_v62")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v63.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v63: {len(spec['intents'])} intents; seeds v63: {n} (+{added}); already seeds: {had}")
    print({k: len(v) for k, v in NEW_SEEDS.items()})


if __name__ == "__main__":
    main()
