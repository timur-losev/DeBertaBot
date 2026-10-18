"""
v58: going on with a movement, after the owner's play with bot v57 in Lyra. The same 47 intents as v57; no line authored
before changes its reading; only seeds are added. Written BEFORE any v58 test line exists (then hashed into frozen.txt).

The owner played bots v56 and v57 on L_Expanse (2026-10-16..18, 689 lines in the game logs). The developer's audit of those
lines (the owner asked: "где гарантия, что фраза попадёт к LLM из-за планировщика?", then "ну попробуй") found that a
movement the owner wanted to go on with was not read: "Keep moving.", "Continue moving.", "And continue moving." (the bot
said 'Say again?'), "Further up." (MOVE_TO 0.41, under the gate), "More up." (REPEAT 0.67), "More down." (MOVE_TO 0.57),
"And up." (HELP 0.55). The decoder (chain v58) is being taught to write such a line back with the earlier order's way;
this round teaches the classifier the forms that carry a way, a side or a place themselves. The v57 classifier read
'keep moving forward' (MOVE_TO 0.38), 'keep going left' (REPEAT 0.30), 'continue forward' (MOVE_TO 0.49), 'further
forward' (0.26), 'advance' (ENTRY 0.68), 'keep coming back' (REPEAT 0.63) as no order, though 'move further forward',
'move up more', 'come back more' were read at 0.99 and over (checked 2026-10-18, stt/probe_v57.py).
The owner: "обучай заодно классификатор v58, свободно" (2026-10-18).

The developer's choices, told to the owner:
  - a going-on that names its way, side or place is MOVE_TO with that way ('keep moving forward', 'keep going up',
    'continue up the stairs', 'further up', 'more down', 'and up', 'a bit further forward'); 'advance' and 'keep
    advancing' are MOVE_TO forward (not ENTRY: no push into a room in the words). 'Push forward' / 'push up' stay ENTRY;
  - 'keep coming', 'keep coming back' are COME_BACK; 'keep coming closer' is FOLLOW_ME, as 'come closer';
  - a bare going-on ('keep moving', 'keep going', 'continue', 'continue moving') gets NO seed: what it goes on with is in
    the talk before it, so the bot must stay unsure of it and say 'Say again?' -- that is what sends it to the decoder's
    second look. A seed reading it NONE would make the bot ignore it, one reading it MOVE_TO would make it ask where.

NOT blind, unlike the lines: the seeds below were written with the owner's log on the table, and four of them are the
owner's own words ('further up', 'more up', 'more down', 'and up'). chains2/owner_ctx_v58.json (the decoder's test of
the owner's lines) is therefore not blind for the classifier on those four.

Writes:
  blind/spec_v58.json       spec_v57.json with MOVE_TO, COME_BACK and NONE saying how a going-on reads
  seed_commands_v58.json    seed set v57 (ids unchanged) + the seeds below; _relabel_v58 = _relabel_v57
The vocabulary is v57's (intents_v57.json: coop_v2.py loads it for v58 too), and so are the authored lines and their
readings (annot/v57/relabel_v57.json).

    python make_spec_v58.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

APPENDED = {
    "MOVE_TO": (". Going on with a movement that names its way, side or place is this intent with that way ('keep moving "
                "forward', 'keep going left', 'continue up the stairs', 'carry on forward', 'further up', 'more down', 'a "
                "bit further forward', 'and up'); 'advance' and 'keep advancing' are this intent forward. A going-on that "
                "names none ('keep moving', 'keep going', 'continue', 'continue moving') is NONE"),
    "COME_BACK": (". Going on coming back ('keep coming', 'keep coming back', 'keep coming this way') is this intent; 'keep "
                  "coming closer' is FOLLOW_ME, as 'come closer'"),
    "NONE": (". A going-on that names no way, side or place ('keep moving', 'keep going', 'continue', 'continue moving', 'keep "
             "it moving') is NONE: what the bot should go on with is in the talk before it; with a way named it is MOVE_TO"),
}

NEW_SEEDS = {
    "MOVE_TO": [
        # keep / continue / carry on + a way or a side
        "keep moving forward", "keep moving up", "keep moving down", "keep moving left", "keep moving right",
        "keep moving ahead", "keep moving up the stairs", "keep going forward", "keep going ahead", "keep going straight",
        "keep going left", "keep going right", "keep going up", "keep going down", "keep heading forward", "keep heading up",
        "keep walking forward", "keep running forward", "continue forward", "continue ahead", "continue moving forward",
        "continue moving up", "continue moving left", "continue moving right", "continue up", "continue down",
        "continue going up", "and continue forward", "carry on forward", "carry on up the stairs",
        # + a place
        "keep moving to the car", "keep going toward the car", "keep moving toward the stairs", "keep going to my pin",
        "continue to my pin",
        # advancing
        "advance", "advance forward", "keep advancing", "advance up", "advance up the stairs", "advance to my pin",
        # further / more + a way
        "further forward", "further up", "further down", "further left", "further right", "go further up",
        "move further up", "go further left", "a bit further forward", "a bit further up", "a little further forward",
        "a little further left", "more up", "more down", "more left", "more right", "up more", "down more",
        "a bit more forward", "a little more to the left", "a bit more up", "go up more", "go down more",
        "and up", "and down", "and forward"],
    "COME_BACK": ["keep coming", "keep coming back", "keep coming back to me", "keep coming back here", "keep coming this way"],
    "FOLLOW_ME": ["keep coming closer"],
}
ON_SIGNAL = {"MOVE_TO": ["keep moving forward on my go", "continue up the stairs when i say"]}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v57.json"), encoding="utf-8"))
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v58.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in json.load(io.open(os.path.join(HERE, "intents_v57.json"), encoding="utf-8")) if not k.startswith("_")]
    assert labels == list(spec["intents"]), (labels, list(spec["intents"]))

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v57.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v57"])               # the earlier relabelled seeds stay relabelled
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
    seeds["_relabel_v58"] = relabel
    seeds["_note_v58"] = ("v58 (make_spec_v58.py, before any v58 test line existed, but with the owner's log of 2026-10-16..18 "
                          f"on the table): seed set v57 + going on with a movement that names its way, side or place: {added} "
                          f"new seeds over {len(extra)} intents (MOVE_TO; COME_BACK 'keep coming'; FOLLOW_ME 'keep coming "
                          "closer'). A bare going-on ('keep moving') gets none. _relabel_v58 = _relabel_v57")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v58.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v58: {len(spec['intents'])} intents; seeds v58: {n} (+{added}); already seeds: {had}")
    print({k: sum(1 for kk, v in seeds.items() if not kk.startswith('_') for i, _ in enumerate(v)
                  if relabel.get(f'seed_{kk}_{i}', kk) == k) for k in ("MOVE_TO", "COME_BACK", "FOLLOW_ME", "ENTRY", "REPEAT", "NONE")})


if __name__ == "__main__":
    main()
