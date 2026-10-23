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
CONFIG = os.path.join(REPO, "models", "coop-deberta-v3-ens3-v61", "cpp", "intent_config.json")

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
]

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
}


def chat_lines():
    src = io.open(CLI, encoding="utf-8").read()
    body = src[src.index("const std::unordered_map<std::string, std::vector<std::string>> kLines = {"):src.index("// a label the demo has no lines")]
    out = []
    for m in re.finditer(r'\{"([A-Z_]+)",\s*\{([^}]*)\}\}', body):
        for line in re.findall(r'"([^"]+)"', m.group(2)):
            out.append((line, f"coop_cli.cpp kLines {m.group(1)}"))
    for name in ("kAck", "kAgain"):
        m = re.search(name + r' = \{([^}]*)\}', src)
        out += [(line, f"coop_cli.cpp {name}") for line in re.findall(r'"([^"]+)"', m.group(1))]
    return out


def sentences(line):
    """A line as the localizer splits it: after . ! ? followed by a space."""
    return [s for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s]


def main():
    cfg = json.load(io.open(CONFIG, encoding="utf-8"))
    phrases = sorted(set(cfg["phrases"].values()))
    objects = list(cfg["locations"]["objects"]) + ["place"]
    seen, out = {}, []
    for line, src in chat_lines() + PLANNER + [(t, "world.cpp kRefuse " + i) for t, i in REFUSE] + [(t, "game: " + n) for t, n in GAME]:
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
