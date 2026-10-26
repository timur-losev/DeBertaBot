"""v65 (the owner, 2026-10-25): no new intent; what the v64 bot and decoder got wrong in his play, and the context the decoder
will be given (chains9_v65.py). "Hide Weapon - Didn't catch that. Добавь в план обучения. ... Хотелось бы решения на уровне
нейросетей"; "запускай и померяем точность". Plan: stt/chains2/ml_v65/PLAN_v65.md.

The owner's words and choices (2026-10-25):
  - taking a thing with no place to take it to and no word of giving it is keeping it: "take that box", «возьми / неси / держи
    коробку» are COLLECT ("я говорю возьми эту коробку, он берёт, кидает её"); "bring me the box", «принеси», «отдай» stay
    DELIVER; "put it there" is DELIVER (the bot holds it: it goes there), not DROP;
  - "hide weapon" is HOLSTER; "throw it away" DROP; "don't call me bro" small talk (the bro habit); a bare "bro" nothing;
  - jumping has three kinds, and getting down off a thing ("get off the box", "climb down", «слезь») is a jump, not getting
    out of a car (ЗАпрыгнуть, Спрыгнуть, Перепрыгнуть).

Relabelled seeds (ids and audio kept, _relabel_v65 = _relabel_v64 + RELABEL_SEEDS): DELIVER's "carry this", "carry it", "carry
that", "carry the box", "take this cardboard crate" are COLLECT. The owner's v64 lines "take the that box", "just take that box",
"take that box" are COLLECT too (annot/v65/relabel_v65.json "owner").
The intents (intents_v64.json) and the places (locations_v64.json) are v64's.

Writes:
  seed_commands_v65.json     seed set v64 (ids unchanged) + NEW_SEEDS; _relabel_v65
  annot/v65/relabel_v65.json the owner's v64 lines read again

    python make_spec_v65.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
RELABEL_SEEDS = {"seed_DELIVER_40": "COLLECT", "seed_DELIVER_41": "COLLECT", "seed_DELIVER_42": "COLLECT",
                 "seed_DELIVER_80": "COLLECT", "seed_DELIVER_89": "COLLECT"}
RELABEL_TEXT = {"seed_DELIVER_40": "carry this", "seed_DELIVER_41": "carry it", "seed_DELIVER_42": "carry that",
                "seed_DELIVER_80": "carry the box", "seed_DELIVER_89": "take this cardboard crate"}
OWNER_RELABEL = {"owner64_0011": ("take the that box", "COLLECT"), "owner64_0013": ("just take that box", "COLLECT"),
                 "owner64_0023": ("take that box", "COLLECT")}
NEW_SEEDS = {
    "HOLSTER": ["hide weapon", "hide your weapon", "hide your gun", "hide the gun", "hide your rifle", "weapon away", "gun away",
                "put your piece away", "stash your weapon", "tuck your gun away", "hide it, put the gun away"],
    "COLLECT": ["take that box", "take the box", "take this box", "take that crate", "take the crate", "carry this box",
                "carry that crate", "hold the box", "keep it", "keep holding it", "hold on to the box",
                "pick it up and keep it", "grab it and hold it", "carry it with you", "bring the box with you",
                "just pick it up, don't give it to me", "don't give it to me, just carry it", "no, don't drop it, just hold it up",
                "just this box, hold it", "take that box again", "pick it up again", "lift it up and hold it", "keep the box"],
    "DELIVER": ["put it there", "put it over there", "put the box there", "put in there that box", "put it right there",
                "put it on the spool", "put the box on the spool", "carry it over to the wall", "take it over there",
                "drop it off over there", "put that box over there", "put it in the corner", "carry it to the wall"],
    "DROP": ["throw it away", "toss it", "throw it", "throw the box away", "chuck it", "get rid of it", "dump it",
             "toss the box", "throw that away"],
    "JUMP": ["get off the box", "get off the spool", "get off the crate", "jump off the box", "jump off it", "jump off the spool",
             "climb down", "climb down from there", "come down from there", "get down from there", "get down off the box",
             "step off the box", "hop off", "hop off the box", "jump down off the box", "jump up on it", "jump on top of the box",
             "get on top of the box", "hop on the box", "jump on it again", "jump up here", "climb on the box", "climb on the spool",
             "climb up on it", "jump on the spool", "jump on top of the spool", "hop over to me", "jump over to me",
             "jump on this trash box", "jump on the trash can", "now jump up higher", "climb over here", "jump forward over the box",
             "jump over onto the other spool", "jump back on it"],
    "PUSH": ["push it forward", "keep pushing it", "push it more", "push it further", "push it again"],
    "ROLL": ["roll it the other way", "roll the spool the other way", "roll it back", "roll it backwards", "roll it again",
             "now roll this one"],
    "SMALL_TALK": ["don't call me bro", "stop calling me bro", "quit calling me bro", "don't call me brother", "stop saying bro",
                   "hey brother", "hey bro"],
    "NONE": ["bro", "brother", "dude", "yo bro"],
}


def main():
    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v64.json"), encoding="utf-8"))
    for sid, text in RELABEL_TEXT.items():   # the index still names the line it was written for
        intent, idx = sid[len("seed_"):].rsplit("_", 1)
        assert seeds[intent][int(idx)] == text, (sid, seeds[intent][int(idx)])
    have = {}
    for intent, lines in seeds.items():
        if not intent.startswith("_"):
            for t in lines:
                have.setdefault(t.strip().lower(), intent)
    added = 0
    for intent, lines in NEW_SEEDS.items():
        for t in lines:
            was = have.get(t.strip().lower())
            if was is not None:
                assert was == intent, f"{t!r} is a {was} seed already"   # a seed of the same intent: left as it is
                continue
            seeds[intent].append(t)
            have[t.strip().lower()] = intent
            added += 1
    seeds["_relabel_v65"] = dict(seeds["_relabel_v64"], **RELABEL_SEEDS)
    seeds["_note_v65"] = ("v65 (make_spec_v65.py, 2026-10-25): seed set v64 with its ids, + seeds of what the v64 bot got wrong in "
                          "the owner's play (hide weapon; take = keep, put it there = deliver; throw it away; getting off a thing "
                          "and jumping on or over it; don't call me bro); DELIVER's carry/take-only seeds read as COLLECT.")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v65.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(HERE, "annot", "v65"), exist_ok=True)
    owner64 = {o["id"]: o for o in json.load(io.open(os.path.join(HERE, "owner_lines_v64.json"), encoding="utf-8"))["items"]}
    rel = {}
    for oid, (text, to) in OWNER_RELABEL.items():
        assert owner64[oid]["text"] == text, (oid, owner64[oid]["text"])
        rel[oid] = {"text": text, "from": owner64[oid]["maj"], "to": to}
    json.dump({"_note": "The owner's v64 lines read again under his choice of 2026-10-25 (take = keep).", "owner": rel, "lines": []},
              io.open(os.path.join(HERE, "annot", "v65", "relabel_v65.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"seed_commands_v65.json: {n} seeds (+{added}), {len(seeds['_relabel_v65'])} relabelled; relabel_v65.json: {len(rel)} owner lines")


if __name__ == "__main__":
    main()
