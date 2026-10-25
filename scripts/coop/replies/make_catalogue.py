"""Every sentence the bot says, in English, as templates: the source the Russian and Spanish reply tables are translated
from (catalogue_en.json). The brain says a line in the player's language by matching each of its English sentences to one
of these templates and writing the template's translation (cpp/coop_intent/src/localize.cpp, coop_cli --replies).

    python make_catalogue.py      -> catalogue_en.json

Sources:
  - the brain's chat lines (coop_cli.cpp kLines, kAck, kAgain), read from the code;
  - the planner's words (world.cpp) and the chat's own (coop_cli.cpp Think), listed here;
  - the game's lines (LyraStarterGame58 Source/LyraGame/CoopBot: the bot controller's Say and Refuse, the command
    component, OVCoop::UnsupportedLine), listed here.
A template is one sentence. {slot} stands for a word or phrase from the slot's list; {Slot} is the same, written with a
capital first letter; {n} is a number. A line of several sentences ("I see no door. Where?") is several templates.
"""
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CLI = os.path.join(REPO, "cpp", "coop_intent", "tools", "coop_cli.cpp")
CONFIG = os.path.join(REPO, "scripts", "coop", "intents_v64.json")   # bot v64's phrases ("label") and places (locations_v64.json)
PLACES = os.path.join(REPO, "scripts", "coop", "locations_v64.json")

PLANNER = [
    ("Copy, stopping.", "world.cpp: a negated order stops the bot"),
    ("I don't see a pin.", "world.cpp: the order names the pin and there is none; followed by 'Where?'"),
    ("I don't know where you mean.", "world.cpp: 'there', 'this' with nothing to point at"),
    ("I can't find {zone}.", "world.cpp: a zone of the map ('the way up') that the world has not"),
    ("I see no {object}.", "world.cpp: the object named is not in the world"),
    ("Where?", "world.cpp: the question after the three above"),
    ("Which {object}?", "world.cpp: several of the object; followed by 'The one ..., N m?'"),
    ("The one {sector}, {n} m?", "world.cpp: offering a candidate: where it is from the player and how far"),
    ("Got it.", "world.cpp: the player's answer settled the question"),
    ("Copy, never mind.", "world.cpp: the player dropped the question"),
    ("I'll take the one {sector}, {n} m.", "world.cpp: the bot picks a candidate itself"),
    ("Which one, then?", "world.cpp: the player said no to every candidate; followed by 'Point at it.'"),
    ("Point at it.", "world.cpp"),
    ("{Phrase}.", "world.cpp: the order said back, e.g. 'Move there.', 'Hold position.'"),
    ("{Phrase}, {where}.", "world.cpp: the order said back with where, e.g. 'Open fire, on your pin.'"),
    ("Ready to {phrase}.", "coop_cli.cpp / world.cpp: an order queued for the player's signal; followed by 'On your go.'"),
    ("On your go.", "coop_cli.cpp / world.cpp: the bot waits for the player's 'go'"),
    ("Copy, standing down.", "coop_cli.cpp: a negated order"),
    ("Now!", "coop_cli.cpp: the queued order is carried out on the signal; followed by the order's line"),
    ("Going!", "coop_cli.cpp: 'go' with nothing queued"),
    ("Taking the other one.", "coop_cli.cpp: 'the other one'"),
    ("Ready.", "coop_cli.cpp: the voice's warm-up line"),
]
REFUSE = [  # world.cpp kRefuse: the item the player named is not in the game's catalogue
    ("I can't build that: no {item} in my build menu.", "BUILD"), ("I can't plant that: I have no {item} to plant.", "PLANT_CROP"),
    ("I can't water that: I see no {item}.", "WATER"), ("I can't harvest that: I see no {item}.", "HARVEST"),
    ("I can't feed that: I see no {item}.", "FEED"), ("I can't collect that: I see no {item}.", "COLLECT"),
    ("I can't bring that: I have no {item}.", "DELIVER"), ("I can't repair that: I see no {item}.", "REPAIR"),
    ("I can't tear that down: I see no {item}.", "DEMOLISH"),
]
GAME = [  # the game's own lines (Source/LyraGame/CoopBot)
    ("Back in the fight.", "respawned"), ("I'm down!", "died"), ("I can't get in.", "car"), ("Someone's in it.", "car taken"),
    ("I can't get to the car.", "car"), ("Again what?", "REPEAT with nothing to repeat"),
    ("Taking fire, {side}!", "hit by an enemy out of view; side from the player"), ("Target down.", "killed its target"),
    ("Contact, {side}!", "saw a new enemy; side from the player"), ("Jumping down.", "drop"), ("I can't get down here.", "drop"),
    ("I'm here.", "HELP_INTERACTION arrived; followed by 'What do I do?'"), ("What do I do?", "HELP_INTERACTION"),
    ("I can't get there.", "no path"), ("In cover.", "TAKE_COVER arrived"), ("I'm with you.", "FOLLOW_ME arrived"),
    ("Closest I can get.", "walk ended short"), ("I'm back.", "COME_BACK / GO_BACK arrived"), ("Flank's set.", "FLANK arrived"),
    ("In position.", "MOVE_TO arrived"), ("Already on my {weapon}.", "SWITCH_WEAPON to the one in hand"),
    ("No {weapon} on me.", "SWITCH_WEAPON to one it has not"), ("Nothing else with ammo.", "SWITCH_WEAPON"),
    ("This is all I've got.", "SWITCH_WEAPON"), ("Switching to {weapon}.", "SWITCH_WEAPON ordered"),
    ("Out of ammo, switching to {weapon}!", "its own switch when the weapon is empty"), ("Nothing to reload.", "RELOAD"),
    ("No spare ammo.", "RELOAD"), ("Mag's full.", "RELOAD"), ("Can't reload right now.", "RELOAD"), ("Reloading.", "RELOAD"),
    ("Frag's coming back!", "its grenade bounced back"), ("Grenade by you, move!", "grenade near the player"),
    ("I'm in.", "in the car"), ("I can't get out.", "car"), ("Copy.", "dead and given an order; followed by the next"),
    ("I'm down, back in a moment.", "dead and given an order"), ("I'm down, give me a moment.", "dead and given an order"),
    ("I don't see a way in.", "'go inside' with no covered spot"), ("No free car around.", "GET_IN"),
    ("Back where?", "GO_BACK before any move; followed by 'I haven't moved.'"), ("I haven't moved.", "GO_BACK"),
    ("Where are you?", "FOLLOW_ME with the player out of reach"), ("Up where?", "'go up' with no way up; followed by 'Mark it.'"),
    ("Down where?", "'go down' with no way down"), ("Mark it.", "asks for a pin"), ("No cover here, staying low.", "TAKE_COVER"),
    ("Too close for a frag.", "FRAG"), ("Too far for a frag.", "FRAG"), ("You're in my way.", "FRAG: the player in the arc"),
    ("No clear throw from here.", "FRAG"), ("Nowhere to jump down here.", "JUMP down"), ("I can't reach you.", "FOLLOW_ME"),
    ("Contact here!", "CHECK found an enemy"), ("Clear.", "CHECK found none"), ("Frag's not ready.", "FRAG on cooldown"),
    ("I'm out of ammo!", "nothing left"), ("That's too far.", "order too far from the player"),
    ("I don't know how to do that.", "an intent the game does not know"), ("Moving.", "MOVE_TO to the player's pin"),
    ("Coming to you.", "MOVE_TO to the speaker"), ("No charges on me.", "BREACH; followed by 'Pushing in instead.'"),
    ("Pushing in instead.", "BREACH"), ("Can't go prone here.", "PRONE; followed by 'Staying low.'"), ("Staying low.", "PRONE"),
    ("Nothing to open there.", "OPEN; followed by 'Moving up to it.'"), ("Moving up to it.", "OPEN"),
    ("Didn't catch part of that.", "a line of several orders with one not understood"), ("Falling back.", "GET_OUT on foot"),
    ("Understood: {verb}.", "farm or build order on a map without those mechanics; followed by 'No farming or building on this map yet.'"),
    ("Understood: {verb} {item}.", "the same with the item the player named"),
    ("No farming or building on this map yet.", "farm or build order"), ("No rope on me.", "RAPPEL"),
    ("I don't have a drone.", "DRONE"), ("No flashbangs, only frags.", "FLASH"), ("No smoke, only frags.", "SMOKE"),
    ("Nothing to plant here.", "PLANT (bomb)"), ("Nothing to defuse here.", "DEFUSE"), ("I can't do that here.", "other"),
    # bot v62 (2026-10-24): the answers the game gives after checking the bot's line of sight, the teleport, carrying
    ("Yes, I see it.", "SEE_THING: the pointed or named thing is in sight"),
    ("No, I can't see it from here.", "SEE_THING: it is not"), ("Yes, I see him.", "SEE_THING: the enemy under the crosshair is in sight"),
    ("No, I don't see him.", "SEE_THING: that enemy is not in sight"), ("I see one of them.", "SEE_THING with nothing pointed: one enemy in sight"),
    ("I see {n} of them.", "SEE_THING with nothing pointed: several enemies in sight"), ("Nothing in sight.", "SEE_THING: no enemy in sight"),
    ("Yes, I see you.", "SEE_ME: the player is in sight"), ("No, I can't see you.", "SEE_ME: the player is not"),
    ("Through the portal.", "MOVE_TO a teleport: the bot went through"), ("Got it.", "DELIVER: picked the thing up"),
    ("Here you go.", "DELIVER: put it down by the player"), ("Dropped it off.", "DELIVER: put it down at the place"),
    ("Nothing to carry there.", "DELIVER: no carriable thing where the player points"), ("That's too heavy for me.", "DELIVER: not carriable"),
    # 2026-10-24, the owner: "what do you see?" / "how is it going?" answered from what the bot sees and senses (the things the
    # level designer labelled, the enemy) and from its body (health, heat, cold, gas, ammo). {thing} is the label, with its
    # article in English ("a spike trap"); its words in the player's language come with the line (the label's own names)
    ("I see {thing} {sector}, {n} m.", "'what do you see?': a labelled thing in sight, where it is from the player and how far"),
    ("And {thing} {sector}, {n} m.", "'what do you see?': the next labelled thing in sight"),
    ("I can feel {thing} {sector}.", "'what do you see?': a labelled heat, cold or gas source near the bot, out of sight"),
    ("Enemy {sector}, {n} m.", "'what do you see?': one enemy in sight"),
    ("{n} enemies in sight.", "'what do you see?': several enemies in sight; followed by 'The nearest ...'"),
    ("The nearest {sector}, {n} m.", "'what do you see?': the nearest of several enemies"),
    ("Nothing worth noting.", "'what do you see?': no labelled thing and no enemy"),
    ("Not a scratch.", "health above nine tenths"), ("Took a few hits, I'm fine.", "health 60 to 90 percent"),
    ("Hurt, but I can fight.", "health 30 to 60 percent"), ("Badly hurt, I need a break.", "health under 30 percent"),
    ("Not hot at all.", "'are you hot?' with no heat"), ("Getting warm here.", "a little heat"), ("It's hot, really hot!", "heat"),
    ("I'm burning up, get me out of here!", "much heat; also said by itself when it gets there"),
    ("Not cold.", "'are you cold?' with no cold"), ("A bit chilly.", "a little cold"), ("It's freezing here.", "cold"),
    ("I'm freezing to death!", "much cold; also said by itself"),
    ("Air's clean.", "'gas?' with no gas"), ("Something smells off.", "a little gas"), ("Gas! Hard to breathe.", "gas"),
    ("Choking on gas, need to get out!", "much gas; also said by itself"),
    ("{n} rounds left.", "'ammo?': the rounds in the weapon in hand and in reserve"), ("Plenty of ammo.", "'ammo?': over half"),
    ("Running low on ammo.", "'ammo?': under a quarter"), ("Nothing in my hands.", "'ammo?' with the weapon put away"),
    ("All quiet around me.", "'how is it going?' with nothing to report but health"),
    # bot v64 (2026-10-25): hand to hand, the weapon put away, things pushed, rolled and put down
    ("My hands are free already.", "HOLSTER with nothing in hand"), ("Weapon up.", "SWITCH_WEAPON with the weapon put away: drawn"),
    ("That's one of ours.", "MELEE with the crosshair on a teammate"), ("Who? I don't see anyone.", "MELEE with no one to strike"),
    ("He's down.", "MELEE: the one it fought is down"), ("I can't get to him.", "MELEE: no way to the one it fights"),
    ("Nothing to push there.", "PUSH: nothing that moves where the player points"),
    ("Nothing to roll there.", "ROLL: the same"), ("That won't move.", "PUSH / ROLL: a fixed part of the map"),
    ("I can't get behind it.", "PUSH / ROLL: no way to behind the thing"), ("There it is.", "PUSH / ROLL: the thing is at its place"),
    ("It won't budge.", "PUSH / ROLL: the thing does not move"), ("I'm not carrying anything.", "DROP with nothing in its hands"),
    # 2026-10-25: jumping over a thing or onto it
    ("Too high to jump on.", "JUMP onto a thing higher than the bot's jump"), ("Too high to jump over.", "JUMP over it: the same"),
    ("Nowhere to land over there.", "JUMP over a thing with no floor beyond it"), ("Didn't make it.", "JUMP over / onto: it landed short"),
]
# the brat habit (coop_cli.cpp kBroOff, kBroRelapse; bro.h): the bot agrees to stop calling the player "bro", and the brat
# persona slips 30 s later
BRO = [("Okay, I won't anymore.", "the player told it to stop saying 'bro'"), ("Got it, no more.", "the same"),
       ("Fine, I'll stop.", "the same"), ("Sorry, habit.", "the brat persona says 'bro' again 30 s after being told to stop; "
                                         "followed by its line")]

SLOTS_NOTE = {
    "phrase": "the order, as the bot says it back (intent_config.json 'phrases'); lowercase, an imperative ('move there')",
    "where": "where the order goes, after a comma: 'Open fire, on your pin.'",
    "sector": "where a candidate is, seen from the player: 'The one on the right, 23 m?'",
    "object": "a kind of place on the map: 'Which window?', 'I see no car.'",
    "zone": "a part of the map, with its article: 'I can't find the way up.'",
    "side": "where an enemy is, seen from the player: 'Contact, ahead, high!'",
    "weapon": "a weapon's name: 'Switching to pistol.'",
    "verb": "a farm or build action: 'Understood: tear down.'",
    "item": "what a farm or build order acts on, as the player named it ('wall', 'corn'); open: any word may come, "
            "and the table gives the words it knows and a form for any other",
    "thing": "a thing the level designer labelled, with its English article ('a spike trap'); open, and it has no values: "
             "its words in the player's language come with the line from the label itself (the forms text, acc, gen...). "
             "The table's _other is said only when a label has no words of that language: a neutral word ('что-то', 'algo')",
}
SLOT_VALUES = {
    "where": ["on your pin", "here", "there", "to the left", "to the right", "forward", "back", "up", "down"],
    "sector": ["above", "below", "ahead", "behind you", "on the left", "on the right"],
    "zone": ["the basement", "the first floor", "the second floor", "the top floor", "the roof", "the way up", "the way down",
             "the way in", "that place"],
    "side": [s + h for s in ("ahead", "on us", "behind us", "right", "left") for h in ("", ", high", ", low")],
    "weapon": ["pistol", "rifle", "shotgun", "weapon"],
    "verb": ["plant", "water", "harvest", "work the ground", "feed", "collect", "bring", "build", "repair", "tear down", "do that"],
    "item": ["wall", "floor", "ramp", "roof", "door", "window", "stairs", "fence", "pillar", "foundation", "corn", "wheat",
             "carrots", "potatoes", "tomatoes", "seeds", "plants", "crops", "chickens", "cows", "pigs", "animals", "eggs", "milk",
             "wood", "planks", "stone", "metal", "ammo", "water", "field", "barn", "well"],
    "thing": [],
}


def chat_lines():
    src = io.open(CLI, encoding="utf-8").read()
    body = src[src.index("const std::unordered_map<std::string, std::vector<std::string>> kLines = {"):src.index("// a label the demo has no lines")]
    out = []
    for m in re.finditer(r'\{"([A-Z_]+)",\s*\{([^}]*)\}\}', body):
        for line in re.findall(r'"([^"]+)"', m.group(2)):
            out.append((line, f"coop_cli.cpp kLines {m.group(1)}"))
    m = re.search(r"kTalk = \{(.*?)\n\};", src, re.S)       # bot v62: the small talk answers, by kind
    for k in re.finditer(r'\{"([a-z]+)",\s*\{([^}]*)\}\}', m.group(1)):
        out += [(line, f"coop_cli.cpp kTalk {k.group(1)} (SMALL_TALK)") for line in re.findall(r'"([^"]+)"', k.group(2))]
    for name in ("kAck", "kAgain"):
        m = re.search(name + r' = \{([^}]*)\}', src)
        out += [(line, f"coop_cli.cpp {name}") for line in re.findall(r'"([^"]+)"', m.group(1))]
    return out


def sentences(line):
    """A line as the localizer splits it: after . ! ? followed by a space."""
    return [s for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s]


def main():
    cfg = json.load(io.open(CONFIG, encoding="utf-8"))
    phrases = sorted({v["label"] for k, v in cfg.items() if not k.startswith("_") and isinstance(v, dict) and "label" in v})
    objects = [o["id"] for o in json.load(io.open(PLACES, encoding="utf-8"))["objects"]] + ["place"]
    seen, out = {}, []
    for line, src in (chat_lines() + PLANNER + [(t, "world.cpp kRefuse " + i) for t, i in REFUSE] + [(t, "game: " + n) for t, n in GAME] +
                      [(t, "coop_cli.cpp bro habit: " + n) for t, n in BRO]):
        for s in sentences(line):
            if s in seen:
                seen[s]["source"] += "; " + src
                continue
            seen[s] = {"en": s, "source": src}
            out.append(seen[s])
    values = dict(SLOT_VALUES, phrase=phrases, object=objects)
    cat = {"note": __doc__.strip().splitlines()[0], "sentences": out,
           "slots": {k: {"note": SLOTS_NOTE[k], "values": v} for k, v in values.items()}}
    json.dump(cat, io.open(os.path.join(HERE, "catalogue_en.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(out)} sentences; slots: " + ", ".join(f"{k} {len(v)}" for k, v in values.items()))


if __name__ == "__main__":
    main()
