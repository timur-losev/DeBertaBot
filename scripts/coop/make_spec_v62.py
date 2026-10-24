"""
v62: the v6x line learns to talk (the owner, 2026-10-24). Written BEFORE any v62 test line exists (then hashed into frozen.txt).

The owner's words: "обучи мозг фразам 'Видишь [что-то игрок покажет]?' А так же 'Видишь меня?' Ещё попросы: 'как дела?' и
другие смолл токи бот должен уметь отвечать, пусть даже коротко. 'Похвала бота' должна реагироваться им. Потом приказы
'Убейся', 'Суициднись' и тд должны с юмором реагироваться. 'Иди в портал/телепорт' MOVE_TO с новым дирекшеном".

The developer's reading, told to the owner:
  - five intents after DEMOLISH, before NONE:
      SEE_THING      "do you see that?", "can you see him?", "do you see the blue stairs?", "see anything?": the bot answers
                     whether it sees what the player points at or names (the game checks its line of sight); with nothing
                     pointed at or named it says what it sees of the enemy;
      SEE_ME         "do you see me?": the same for the player;
      SMALL_TALK     "how are you?", "hello", "thanks", "who are you?", "tell me a joke": a short answer, no action;
      PRAISE         "nice shot", "good job", "you're the best": the bot takes the praise, no action;
      KILL_YOURSELF  "kill yourself", "suicide", "go die": refused with a joke, no action;
  - SEE_THING and SEE_ME share a family ("see"); the other three each have their own;
  - "go into the portal / the teleport": MOVE_TO, and the teleport is a new kind of place (locations_v62.json, vocabulary
    version 9: the object "teleport"); the game gives the brain its teleports as places, and the order is carried out when
    the bot has gone through.
Boundaries kept: turning to look is LOOK_AT / LOOK_AT_ME ('look at that', 'look at me'); going to look is CHECK ('see if it's
clear', 'check if they're there'); a callout of what the PLAYER sees is NONE ('I see him', 'I see two on the roof'); 'kill
him / them' is ATTACK; a bare 'good', 'great', 'perfect', 'okay' answers the bot (YES) and is not praise; praise or small talk
with an order in the same line is that order ('nice shot, now follow me' FOLLOW_ME, 'hey, cover me' COVER_ME); 'hi there'
stays TAKE_COVER (the owner's misheard 'hide there', v57) and a bare 'hi' is left out of the seeds for the same reason.

Writes:
  blind/spec_v62.json        what the v62 blind authors and annotators see: the v60 spec, the five intents, the boundaries,
                             the teleport place
  intents_v62.json           the model-side vocabulary (62 intents)
  seed_commands_v62.json     seed set v61 (ids unchanged) + the seeds below; _relabel_v62 = _relabel_v60
  locations_v62.json         the place vocabulary v9: v8 + the teleport

    python make_spec_v62.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

NEW_INTENTS = {
    "SEE_THING": (
        "the player asks the bot whether it SEES something: the thing the player points at, looks at or names, or anything "
        "at all (do you see that?, can you see him?, see that guy?, do you have eyes on the door?, do you see the blue "
        "stairs?, can you spot him?, you got a visual on that?, are you seeing this?, do you see anything?, do you see any "
        "enemies?). It is a question, and the bot only answers it: it does not turn, move or shoot. Turning to look is "
        "LOOK_AT ('look at that'); going to look whether a place is clear is CHECK ('see if it's clear', 'go see what's "
        "there'); telling the bot what the PLAYER sees is a callout, NONE ('I see him', 'I see two on the roof'); asking "
        "whether the bot sees the player is SEE_ME"),
    "SEE_ME": (
        "the player asks the bot whether it sees the PLAYER (do you see me?, can you see me?, see me?, am I in your view?, "
        "do you have eyes on me?, can you see me from there?). The bot answers; it does not turn to the player (LOOK_AT_ME) "
        "or come (FOLLOW_ME)"),
    "SMALL_TALK": (
        "social talk to the bot that asks for no action: greetings and goodbyes (hello, hey buddy, good morning, see you), "
        "how it is (how are you?, how's it going?, what's up?, are you okay?, you still there?), thanks and apologies "
        "(thanks, thank you, cheers, sorry, my bad), questions about the bot itself (who are you?, what's your name?, are "
        "you a bot?, do you like this game?), and banter (tell me a joke, I'm bored, talk to me). The bot answers briefly. "
        "A question about the fight or the map is not small talk ('where are they?', 'how many are left?' are NONE); praise "
        "of what the bot did is PRAISE; with an order in the same line it is that order ('hey, cover me' is COVER_ME). A bare "
        "'hi' or 'hi there' is not seeded here: speech-to-text hears the player's 'hide there' that way (TAKE_COVER)"),
    "PRAISE": (
        "the player praises the bot or what it just did (nice shot, good job, well done, great work, nice one, nice kill, "
        "you're the best, you're awesome, good bot, that was amazing, great teamwork). The bot takes it, briefly; nothing "
        "else happens. A bare 'good', 'great', 'perfect', 'nice' or 'okay' that answers the bot is YES; praise with an order "
        "in the same line is that order ('nice shot, now follow me' is FOLLOW_ME); thanks are SMALL_TALK"),
    "KILL_YOURSELF": (
        "the player tells the bot to kill itself or to die, as a joke or an insult (kill yourself, go kill yourself, shoot "
        "yourself, commit suicide, suicide, go die, just die, drop dead, end yourself, off yourself, kys, self destruct, "
        "blow yourself up, frag yourself). The bot refuses with a joke and does nothing. Killing an enemy is ATTACK ('kill "
        "him', 'kill them all'); 'don't die' / 'stay alive' / 'you'll die there' are NONE"),
}
APPENDED = {
    "LOOK_AT": (". Asking whether the bot sees something ('do you see that?', 'can you see him?') is SEE_THING: a question, "
                "not a turn"),
    "LOOK_AT_ME": ". Asking whether the bot sees the player ('do you see me?') is SEE_ME",
    "CHECK": (". 'Do you see anything there?' asked of the bot where it is, is SEE_THING; going to see is this intent "
              "('go see if it's clear')"),
    "ATTACK": ". Telling the bot to kill ITSELF ('kill yourself', 'go die') is KILL_YOURSELF",
    "YES": (". Praise of what the bot did ('nice shot', 'good job', 'well done') is PRAISE; the bare word that answers the "
            "bot ('good', 'great', 'perfect') stays this intent"),
    "MOVE_TO": (". Going into or through a teleport or a portal ('go into the portal', 'take the teleport', 'go through the "
                "teleporter') is this intent: the teleport is the place"),
    "NONE": (". Social talk to the bot ('how are you?', 'hello', 'thanks', 'who are you?') is SMALL_TALK, praise ('nice "
             "shot') PRAISE, asking whether the bot sees something SEE_THING or SEE_ME, and telling it to kill itself "
             "KILL_YOURSELF; a callout of what the PLAYER sees ('I see him') and questions about the fight ('where are they?') "
             "stay NONE"),
}
TELEPORT = {"id": "teleport", "words": ["teleport", "teleports", "teleporter", "teleporters", "portal", "portals", "the tp",
                                        "warp", "warp gate", "warp pad", "jump pad"], "qualifiers": []}
TELEPORT_SPEC = "a teleport, a portal, a teleporter: walking into it takes you to another part of the map"
NEW_MODEL = {
    "SEE_THING": {"label": "say if you see it", "description": "answer whether the bot sees what the player points at or names"},
    "SEE_ME": {"label": "say if you see me", "description": "answer whether the bot sees the player"},
    "SMALL_TALK": {"label": "talk", "description": "social talk that asks for no action: greetings, how are you, thanks"},
    "PRAISE": {"label": "take the praise", "description": "the player praises the bot"},
    "KILL_YOURSELF": {"label": "refuse that", "description": "the player tells the bot to kill itself: refused with a joke"},
}
FAMILY_NOTE = ("v62 families: v60's; SEE_THING and SEE_ME share the family 'see', SMALL_TALK, PRAISE and KILL_YOURSELF have "
               "one each (small_talk, praise, kill_yourself). They come after DEMOLISH, before NONE")
FAMILIES = {"SEE_THING": "see", "SEE_ME": "see", "SMALL_TALK": "small_talk", "PRAISE": "praise", "KILL_YOURSELF": "kill_yourself"}

NEW_SEEDS = {
    "SEE_THING": [
        "do you see that", "do you see it", "can you see that", "can you see it", "can you see him", "do you see him",
        "do you see them", "can you see them", "you see that", "see that", "see that guy", "do you see the enemy",
        "can you see the enemy", "do you see any enemies", "do you see anything", "see anything", "can you see anything there",
        "do you see the window", "can you see the north window", "do you see the blue stairs", "do you see the car",
        "can you see the door from there", "do you see my pin", "can you see my pin", "can you see my mark",
        "do you have eyes on that", "do you have eyes on him", "you got eyes on that guy", "have you got eyes on the door",
        "eyes on my pin", "can you spot him", "can you spot that", "did you spot him", "you seeing this", "are you seeing that",
        "do you see this", "do you see what I'm pointing at", "can you see where I'm aiming", "do you see what I'm looking at",
        "do you see the guy on the roof", "can you see the sniper", "do you see the target", "is he in your view",
        "is that in your sight", "do you have a line of sight on that", "you got a visual on that", "do you have visual",
        "visual on the target", "can you see over there", "do you see the teleport", "can you see the portal",
        "do you see the barn", "can you see the crate", "do you still see him", "do you see him now", "see them over there",
        "can you see the enemy at my pin", "do you see the guy behind the car"],
    "SEE_ME": [
        "do you see me", "can you see me", "you see me", "see me", "do you have eyes on me", "can you spot me",
        "am I visible to you", "am I in your view", "do you see where I am", "can you see me from there", "are you seeing me",
        "you got eyes on me", "do you see me up here", "can you see me down here", "I'm here do you see me",
        "can you still see me", "do you see me now", "hey can you see me", "do you see me waving", "do you see me on the roof",
        "can you see me through the window", "am I in your line of sight", "do you have a visual on me", "can you see me or not",
        "tell me if you see me", "do you see me over here", "can you see me behind the car", "do you see me at the door"],
    "SMALL_TALK": [
        "how are you", "how are you doing", "how's it going", "how is it going", "what's up", "sup", "hello", "hello there",
        "hey buddy", "hey man", "yo buddy", "good morning", "good evening", "good night", "bye", "see you later",
        "see you", "are you okay", "you okay", "are you alright", "you still there", "are you there", "thanks", "thank you",
        "thanks buddy", "thank you so much", "cheers", "cheers mate", "sorry", "my bad", "sorry about that", "who are you",
        "what's your name", "what is your name", "what are you", "are you a bot", "are you human", "are you real",
        "do you like this game", "how old are you", "where are you from", "tell me a joke", "tell me something", "talk to me",
        "say something", "I'm bored", "are you tired", "how was your day", "how do you feel", "how are things",
        "how's your day", "nice to meet you", "glad you're here", "what do you think of me", "do you like me",
        "are you happy", "having fun", "are you having fun", "what's new"],
    "PRAISE": [
        "good job", "nice job", "great job", "well done", "nice shot", "good shot", "great shot", "nice one", "good one",
        "nice work", "good work", "great work", "excellent work", "awesome job", "you're awesome", "you're the best",
        "you're amazing", "good bot", "nice kill", "great kill", "nice moves", "that was amazing", "that was awesome",
        "you're doing great", "you did great", "perfect shot", "beautiful shot", "impressive", "that was impressive",
        "nice throw", "nice grenade", "great teamwork", "good teamwork", "good boy", "nice going", "way to go",
        "you nailed it", "you killed it", "you're a legend", "legend", "that's my boy", "nice save", "great save",
        "nice cover", "good cover", "you saved me", "you saved my life", "best teammate ever", "you rock", "bravo",
        "nice flank", "nice breach", "clean shot", "what a shot"],
    "KILL_YOURSELF": [
        "kill yourself", "go kill yourself", "just kill yourself", "shoot yourself", "shoot yourself in the head",
        "commit suicide", "suicide", "do a suicide", "go die", "just die", "die", "drop dead", "go drop dead", "end yourself",
        "end it", "off yourself", "unalive yourself", "kys", "kill urself", "self destruct", "self-destruct", "blow yourself up",
        "frag yourself", "throw a grenade at your feet", "eat a grenade", "go jump in the lava", "delete yourself",
        "uninstall yourself", "shut yourself down", "turn yourself off", "kill yourself now", "please die",
        "jump to your death", "walk into the fire", "blow your brains out"],
    # boundaries: the words the new intents share with the old ones, under the old ones
    "LOOK_AT": ["look at that", "look at him", "look at the window", "look over there", "take a look at that"],
    "LOOK_AT_ME": ["look at me", "turn to me", "face me"],
    "CHECK": ["see if it's clear", "go see what's there", "see what's behind the door", "check if they're there",
              "go see if anyone is there"],
    "ATTACK": ["kill him", "kill them", "kill them all", "kill that guy", "kill the enemy", "kill everyone"],
    "FOLLOW_ME": ["nice shot now follow me", "good job follow me", "thanks now follow me", "hey follow me"],
    "COVER_ME": ["hey cover me", "nice one cover me now", "thanks cover me"],
    "YES": ["good", "great", "perfect", "okay good"],
    "NONE": ["I see him", "I see two on the roof", "I see them", "I can see the enemy", "where are they", "how many are left",
             "don't die", "stay alive", "you'll die there", "I'm dying", "he's dead", "I killed him", "nice try",
             "watch yourself"],
    "MOVE_TO": ["go to the teleport", "go into the portal", "walk into the teleporter", "take the teleport", "use the teleport",
                "go through the portal", "enter the portal", "jump into the portal", "step into the teleporter",
                "go in the portal", "take the portal", "go through the teleport", "use the portal", "go to the portal",
                "head to the teleporter", "get in the teleport", "go through the teleporter to the warehouse",
                "teleport", "take the warp gate"],
    # carrying (the owner, 2026-10-24, mid-round: "бот строитель фермер должен уметь: 'Неси это', 'Бери это и неси туда',
    # 'Перенеси, отнеси, принеси мне коробку'"): DELIVER as spec_v60 has it; bot v61 read the pointed ones as MOVE_TO
    "DELIVER": ["carry this", "carry it", "carry that", "carry this there", "carry it over there", "carry this to me",
                "take this there", "take this over there", "take that over there", "take it over there", "take this to my pin",
                "take this and carry it there", "pick this up and carry it there", "grab this and take it over there",
                "grab that and bring it here", "pick it up and bring it to me", "take this and bring it here",
                "move the box", "move the box over there", "move this box", "move that crate over there", "move the crate to my pin",
                "move this over there", "move it over there", "relocate the crate", "shift the box over there",
                "take the box over there", "take the crate there", "bring me the box", "bring me that box", "bring me that",
                "bring me this", "bring that here", "bring this over here", "bring that to me", "fetch the box",
                "fetch me that crate", "get me that box", "get me the crate", "haul the box over there", "carry the box",
                "carry the crate to the barn", "carry the box to me", "carry that crate over here", "lug the box over there",
                "deliver the box to my pin", "drop this over there", "put this over there", "put that box over there"],
    # not "take this": the owner says it for MOVE_TO (owner_lines_v61.json, four times), as bot v62's first build showed
    "COLLECT": ["pick this up", "pick that up", "pick up the box", "grab this", "grab that crate"],
}

# earlier NONE seeds that the new intents now take (their ids and audio stay): _relabel_v62
RELABEL_SEEDS = {
    "seed_NONE_15": "PRAISE", "seed_NONE_189": "PRAISE",
    "seed_NONE_183": "SEE_ME",
    "seed_NONE_179": "SMALL_TALK", "seed_NONE_180": "SMALL_TALK", "seed_NONE_181": "SMALL_TALK", "seed_NONE_186": "SMALL_TALK",
    "seed_NONE_187": "SMALL_TALK", "seed_NONE_190": "SMALL_TALK", "seed_NONE_193": "SMALL_TALK", "seed_NONE_194": "SMALL_TALK",
    "seed_NONE_195": "SMALL_TALK", "seed_NONE_198": "SMALL_TALK", "seed_NONE_200": "SMALL_TALK", "seed_NONE_201": "SMALL_TALK",
}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v60.json"), encoding="utf-8"))
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_INTENTS)
    spec["intents"]["NONE"] = none
    spec["map"]["objects"]["teleport"] = TELEPORT_SPEC
    spec["map"]["note"] += " Some maps also have teleports (portals): walking into one takes you to another part of the map."
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v62.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v60.json"), encoding="utf-8"))
    notes = {k: model.pop(k) for k in [k for k in model if k.startswith("_")]}
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model.update(notes)
    model["_note_v62"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v62.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]
    assert labels == list(spec["intents"]), (labels, list(spec["intents"]))

    loc = json.load(io.open(os.path.join(HERE, "locations_v60.json"), encoding="utf-8"))
    assert all(o["id"] != "teleport" for o in loc["objects"])
    loc["objects"].append(TELEPORT)
    loc["version"] = 9
    loc["_note"] += " v9 (2026-10-24, make_spec_v62.py): the object teleport (portal, teleporter), for the v62 bots."
    json.dump(loc, io.open(os.path.join(HERE, "locations_v62.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v61.json"), encoding="utf-8"))
    relabel = dict(seeds.get("_relabel_v61", seeds["_relabel_v60"]))
    for sid, to in RELABEL_SEEDS.items():
        intent, n = sid[len("seed_"):].rsplit("_", 1)
        assert relabel.get(sid, intent) == "NONE", (sid, relabel.get(sid, intent))
        relabel[sid] = to
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
    seeds["_relabel_v62"] = relabel
    seeds["_note_v62"] = (f"v62 (make_spec_v62.py, before any v62 test line existed): seed set v61 + {added} seeds of the five "
                          "talking intents (SEE_THING, SEE_ME, SMALL_TALK, PRAISE, KILL_YOURSELF), the teleport as a MOVE_TO "
                          "place, and the boundaries (look, check, kill him, praise or talk with an order, bare yes words, the "
                          f"player's own callouts). _relabel_v62 = _relabel_v61 + {len(RELABEL_SEEDS)} earlier NONE seeds that "
                          "the new intents take (RELABEL_SEEDS)")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v62.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v62: {len(spec['intents'])} intents (last: {list(spec['intents'])[-6:]}); intents_v62: {len(labels)}; "
          f"seeds v62: {n} (+{added}); already seeds: {had}")
    print({k: len(v) for k, v in NEW_SEEDS.items()})


if __name__ == "__main__":
    main()
