"""
v57: changing weapons and reloading, and the owner's words the recognizer got wrong, after the owner's play with bot v56 in
Lyra. Written BEFORE any v57 test line exists (then hashed into frozen.txt).

The owner played bot v56 on L_Expanse and asked (2026-10-17, their words in quotes, answers to the developer's questions in
brackets):
  - "Bot почему-то не переключает оружие когда закончатся патроны, и нет интента для SWITCH WEAPON": a new intent
    SWITCH_WEAPON ("Switch weapons." got MOVE_TO @ weapon 0.36 and sent the bot to a weapon spawner) [a weapon named takes
    that one if the bot carries it; no name: the next weapon it carries that has ammo; the game switches by itself when the
    one in hand is empty]; and a new intent RELOAD ("Reload." got nothing) [asked by the developer, chosen by the owner];
  - "найди такой текст, который STT не правильно распознало и добавь его в обучение на нём": the transcripts of the log that
    the recognizer got wrong are seeds below, under the reading the owner confirmed ["Height." = "Hide.", "Hi there." =
    "Hide there.", "Jammed out." = "Jump down.", "Down here." = "Jump down here."] or that is plain from the log ("Jam down."
    jump down, "You doubt." get out (said in the car), "Sim dub." stand up, "Should that windows?" shoot that windows);
    "You have already have it." stays out (no reading);
  - [a bare "get out" is GET_OUT: the owner said it to the bot in the car, and v56 read it FALL_BACK, so the bot got out and
    ran off; the game carries GET_OUT out as falling back when the bot is in no vehicle]. "Get out of there" and "get out of
    the fight" stay FALL_BACK.
The developer's choices, told to the owner: SWITCH_WEAPON and RELOAD after GO_BACK, each in a family of its own ('switch',
'reload'); a weapon named in the line is not a place (target all null; the game reads the kind from the line's words).
"Go find them all." (go find ammo) stays out of the place rules: "them all" as ammo would also catch "kill them all".

NOT blind, unlike the lines: the seeds below were written with the owner's log of 2026-10-17 on the table.

Writes:
  blind/spec_v57.json       what the v57 blind authors and annotators see
  intents_v57.json          the model-side vocabulary (47 intents)
  seed_commands_v57.json    seed set v56 (ids unchanged) + the seeds below; _relabel_v57 = _relabel_v56 + the bare
                            'get out' seed (GET_OUT)
  annot/v57/relabel_v57.json   the authored lines (v1 to v56) that change: one line of two weapon orders, NONE so far, is
                            RELOAD with SWITCH_WEAPON accepted (read one by one)

    python make_spec_v57.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

SWITCH_WEAPON = (
    "the bot changes the weapon in its hands for another one it carries (switch weapons, change weapon, swap guns, next "
    "weapon, switch to your pistol, pull out your sidearm, use your rifle, go to your shotgun, switch to primary). A weapon "
    "named is the one to take, if the bot has it; with none named the bot takes the next one it carries that has ammo. "
    "Picking up or going to get a weapon lying in the world is MOVE_TO ('grab that rifle', 'go get a shotgun', 'find a "
    "weapon', 'pick up the pistol by my pin'); putting a fresh magazine in the same weapon is RELOAD; shooting is OPEN_FIRE")
RELOAD = (
    "the bot reloads the weapon in its hands (reload, reload now, change mags, swap mags, new mag, top off, get a fresh mag "
    "in). The player saying THEY are reloading ('cover me, I'm reloading') is COVER_ME or whatever they ask for; going to "
    "find or pick up ammo is MOVE_TO ('go find ammo', 'grab some ammo'); taking another weapon is SWITCH_WEAPON")
# whole phrases of the v56 text that change; each must be there exactly once
REPLACED = {
    "GET_OUT": ("A bare 'get out' or 'get out of there' with no vehicle is FALL_BACK",
                "A bare 'get out' (said to the bot in a car) is this intent too; with the bot in no vehicle the game takes it "
                "as falling back. 'Get out of there', 'get out of the fight', 'get out of his line' (leaving a place or a "
                "fight) is FALL_BACK"),
    "FALL_BACK": ("a bare 'get out' is this intent",
                  "'get out of there' / 'get out of the fight' is this intent; a bare 'get out' is GET_OUT"),
}
APPENDED = {
    "MOVE_TO": (". Taking out a weapon the bot already carries ('switch to your pistol', 'use your rifle', 'pull out your "
                "sidearm') is SWITCH_WEAPON; reloading is RELOAD"),
    "COVER_ME": ". The player reloading is no order to reload: 'cover me, I'm reloading' is this intent",
}
TARGET_ADD = (" For SWITCH_WEAPON and RELOAD all null: a weapon named is one the bot carries, not a place ('switch to your "
              "pistol' names no place; 'pick up the pistol by my pin', MOVE_TO, does).")
NEW_MODEL = {
    "SWITCH_WEAPON": {"label": "switch weapons", "description": "take out another weapon the bot carries"},
    "RELOAD": {"label": "reload", "description": "reload the weapon in hand"},
}
FAMILY_NOTE = ("v57 families: v56 families; SWITCH_WEAPON ('switch') and RELOAD ('reload') each in a family of its own. "
               "They come after GO_BACK, before NONE")

# seeds that keep their id (and their audio) under another label
RELABEL_SEEDS = {"seed_FALL_BACK_5": ("get out", "GET_OUT"),
                 # the owner's "Hide there." was heard "Hi there." (confirmed): the greeting seed goes, a greeting to the
                 # bot is rarer in play than an order to hide (told to the owner)
                 "seed_NONE_199": ("hi there", "TAKE_COVER")}

NEW_SEEDS = {
    "SWITCH_WEAPON": [
        "switch weapons", "switch weapon", "switch your weapon", "change weapon", "change weapons", "change your weapon",
        "swap weapons", "swap guns", "switch guns", "change guns", "next weapon", "other weapon", "use your other gun",
        "switch to your other gun", "switch to your pistol", "switch to pistol", "switch to the pistol", "switch to your rifle",
        "switch to the rifle", "switch to your shotgun", "switch to the shotgun", "swap to the rifle", "swap to your pistol",
        "swap to your shotgun", "change to the shotgun", "change to your rifle", "pull out your pistol", "pull out your sidearm",
        "go to your sidearm", "go to your pistol", "use your pistol", "use the rifle", "use your shotgun", "use your rifle",
        "take out your pistol", "get your rifle out", "get your shotgun out", "equip your pistol", "equip the rifle",
        "draw your pistol", "switch to secondary", "switch to primary", "go primary", "go secondary", "switch weapons now",
        "you're out of ammo switch weapons", "out of ammo switch guns", "switch to something with ammo",
        "use a gun with ammo", "switch weapons quick"],
    "RELOAD": [
        "reload", "reload now", "reload your weapon", "reload your gun", "reload your rifle", "reload your pistol",
        "reload quick", "go reload", "reload it", "quick reload", "reload up", "you need to reload", "reload while you can",
        "reload before they push", "reload real quick", "change mags", "swap mags", "change magazine", "change your mag",
        "new mag", "get a new mag in", "get a fresh mag in", "top off", "top off your mag", "top up your mag", "reload buddy",
        "ok reload", "reload reload", "reload your weapon now", "time to reload"],
    "GET_OUT": ["get out now", "ok get out", "you can get out", "get out quick", "just get out", "get out bro",
                "step out", "exit the car", "out of the car", "you doubt"],
    # the owner's words the recognizer got wrong on 2026-10-17, under the readings the owner confirmed or the log makes plain
    "TAKE_COVER": ["height", "hide there", "hide over there", "hide right there", "fine colour", "find colour"],
    "JUMP": ["jammed out", "jam down", "jammed down", "down here", "jump down over here"],
    "STAND_UP": ["sim dub"],
    "OPEN_FIRE": ["should that windows", "should that window", "shoot that windows", "shoot that window"],
    "WAIT": ["don't reload", "don't reload yet", "don't switch weapons", "don't switch guns"],
}
ON_SIGNAL = {"SWITCH_WEAPON": ["switch weapons on my go", "switch to your pistol when i say"],
             "RELOAD": ["reload on my go"]}

# the authored lines (v1 to v56) read one by one: two weapon orders in one line, NONE so far
LINES = {
    "r6v5_059": {"from": "NONE", "to": "RELOAD", "also": ["SWITCH_WEAPON"],
                 "text": "Reload and swap to your shotgun before the next push."},
}


def main():
    sys.path.insert(0, HERE)

    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v56.json"), encoding="utf-8"))
    for k, (old, new) in REPLACED.items():
        assert spec["intents"][k].count(old) == 1, (k, old)
        spec["intents"][k] = spec["intents"][k].replace(old, new)
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"]["SWITCH_WEAPON"] = SWITCH_WEAPON
    spec["intents"]["RELOAD"] = RELOAD
    spec["intents"]["NONE"] = none
    spec["modifiers"]["target"] += TARGET_ADD
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v57.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v56.json"), encoding="utf-8"))
    notes = {k: model.pop(k) for k in [k for k in model if k.startswith("_")]}
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model.update(notes)
    model["_note_v57"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v57.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]
    assert labels == [k for k in spec["intents"]], (labels, list(spec["intents"]))

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v56.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v56"])               # the earlier relabelled seeds stay relabelled
    for sid, (text, to) in RELABEL_SEEDS.items():
        k, n = sid[len("seed_"):].rsplit("_", 1)
        assert seeds[k][int(n)] == text and relabel.get(sid, k) == k, (sid, seeds[k][int(n)], relabel.get(sid))
        relabel[sid] = to
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    extra = {}
    for src in (NEW_SEEDS, ON_SIGNAL):
        for k, v in src.items():
            extra.setdefault(k, []).extend(v)
    added, had = 0, []
    for k, v in extra.items():
        assert len(v) == len(set(v)), (k, [t for t in v if v.count(t) > 1])
        for t in v:
            assert owner.get(t, k) == k, f"{t!r} is already a {owner[t]} seed, cannot also be {k}"
            if t in owner:
                had.append(t)
            else:
                seeds.setdefault(k, []).append(t)       # appended: every earlier seed keeps its id (seed_<INTENT>_<n>)
                owner[t] = k
                added += 1
    seeds["_relabel_v57"] = relabel
    seeds["_note_v57"] = ("v57 (make_spec_v57.py, before any v57 test line existed, but with the owner's log of 2026-10-17 on "
                          "the table): seed set v56 + commands for SWITCH_WEAPON and RELOAD, more bare GET_OUT, and the "
                          f"owner's misheard words under their readings: {added} new seeds over {len(extra)} intents. "
                          "_relabel_v57: _relabel_v56 + the bare 'get out' seed (FALL_BACK -> GET_OUT) and 'hi there' "
                          "(NONE -> TAKE_COVER: the owner's 'hide there' as the recognizer hears it)")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v57.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # the authored lines
    os.environ["COOP_TAG"] = "v56"
    import coop_v2
    items = {it["id"]: it for it in coop_v2.load_items()}
    for k, r in LINES.items():
        assert items[k]["text"] == r["text"] and items[k]["maj"] == r["from"], (k, items[k]["text"], items[k]["maj"])
    os.makedirs(os.path.join(HERE, "annot", "v57"), exist_ok=True)
    json.dump({"_note": "make_spec_v57.py: the authored lines (v1 to v56) whose reading changes under spec v57, read one by "
                        "one by the developer before freezing. 'also': readings accepted besides the new one (a line of two "
                        "orders: the classifier is right on either; the chain splits it)",
               "lines": LINES},
              io.open(os.path.join(HERE, "annot", "v57", "relabel_v57.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v57: {len(spec['intents'])} intents (last: {list(spec['intents'])[-4:]}); intents_v57: {len(labels)}; "
          f"seeds v57: {n} (+{added}); already seeds: {had}")
    print({k: sum(1 for kk, v in seeds.items() if not kk.startswith('_') for i, _ in enumerate(v)
                  if relabel.get(f'seed_{kk}_{i}', kk) == k) for k in ("SWITCH_WEAPON", "RELOAD", "GET_OUT", "FALL_BACK",
                                                                       "TAKE_COVER", "JUMP", "STAND_UP", "OPEN_FIRE", "WAIT")})
    print(f"authored lines: {len(LINES)} relabelled")


if __name__ == "__main__":
    main()
