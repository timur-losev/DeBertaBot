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
CONFIG = os.path.join(REPO, "scripts", "coop", "intents_v66.json")   # bot v66's phrases ("label") and places (locations_v66.json)
PLACES = os.path.join(REPO, "scripts", "coop", "locations_v68.json")   # v14 (2026-10-28): bed is a bed, garden_bed, rock

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
    ("Point at it.", "world.cpp; coop_cli.cpp the long-term memory: a name or a colour with nothing under the crosshair"),
    # the long-term memory (coop_cli.cpp --memory, teach.h): what the player teaches the bot
    ("What did you mean?", "coop_cli.cpp memory: after 'not that'; the next line is the meaning"),
    ("Got it, I'll remember.", "coop_cli.cpp memory: a name, a colour or a meaning kept (before the order's own words)"),
    ("Forgotten.", "coop_cli.cpp memory: 'forget the name', 'forget <a line>'"),
    ("I don't remember that.", "coop_cli.cpp memory: 'forget ...' with nothing kept"),
    ("Then what is it?", "coop_cli.cpp memory: 'no' right after the bot answered 'what is that?'; the next line says what it is"),
    ("Shall I remember it as {thing}?", "coop_cli.cpp memory: 'no, it's a red lantern', 'this is the garage': the name as the "
                                        "player said it (in their language); 'yes' keeps it"),
    ("All right, I won't remember it.", "coop_cli.cpp memory: 'no' to 'Shall I remember it as ...?'"),
    ("I don't know what colour it is.", "coop_cli.cpp memory: 'what colour is it?' at a thing whose colour neither the game "
                                        "nor the player gave"),
    ("Shall I remember that {thing} is behind this door?", "coop_cli.cpp memory: 'this is the garage' at a door whose inside the "
                                                            "level marks: the room behind it; 'yes' keeps the name"),
    ("That's the door to {thing}.", "coop_cli.cpp memory: 'what is that?' at a door into a room the player named"),
    ('Shall I remember that "{said}" means "{meant}"?', "coop_cli.cpp memory (OfferMeaning): a line the bot read right after lines "
                                                         "about the same thing it could not read; 'yes' keeps them as its orders"),
    ('I don\'t understand "{meant}".', "coop_cli.cpp memory: 'when I say X, it means Y' with a Y the bot cannot read"),
    ('Like this: "{said}"?', "coop_cli.cpp memory: a word said the way the player taught ('the stress in zamok is on the first "
                             "syllable'); 'yes' keeps it"),
    ("I don't say \"{said}\".", "coop_cli.cpp memory: 'instead of X say Y' with an X the bot never says"),
    ("Shall I stop saying \"{said}\"?", "coop_cli.cpp memory: 'don't say X', 'don't say that' about the bot's own line; 'yes' keeps it"),
    ("Shall I say \"{meant}\" instead of \"{said}\"?", "coop_cli.cpp memory: 'instead of X say Y' about the bot's own line; 'yes' keeps it"),
    ("Shall I keep {n} m from you?", "coop_cli.cpp memory: 'stay 3 meters from me', 'stay closer': the follow distance; 'yes' keeps it"),
    ("Shall I open fire within {n} m?", "coop_cli.cpp memory: 'open fire within 20 meters': the range it shoots from; 'yes' keeps it"),
    ("Shall I shoot only on your command?", "coop_cli.cpp memory: 'only shoot on my command'; 'yes' keeps it"),
    ("Shall I shoot on my own?", "coop_cli.cpp memory: 'you can shoot on your own'; 'yes' keeps it"),
    ("Shall I speak faster?", "coop_cli.cpp memory: 'talk faster'; 'yes' keeps it"),
    ("Shall I speak slower?", "coop_cli.cpp memory: 'talk slower'; 'yes' keeps it"),
    ("Shall I speak at the usual speed?", "coop_cli.cpp memory: 'talk at normal speed'; 'yes' keeps it"),
    ("{Phrase}.", "world.cpp: the order said back, e.g. 'Move there.', 'Hold position.'"),
    ("{Phrase}, {where}.", "world.cpp: the order said back with where, e.g. 'Open fire, on your pin.'"),
    ("Ready to {phrase}.", "coop_cli.cpp / world.cpp: an order queued for the player's signal; followed by 'On your go.'"),
    ("On your go.", "coop_cli.cpp / world.cpp: the bot waits for the player's 'go'"),
    ("Copy, standing down.", "coop_cli.cpp: a negated order"),
    ("Now!", "coop_cli.cpp: the queued order is carried out on the signal; followed by the order's line"),
    ("Going!", "coop_cli.cpp: 'go' with nothing queued"),
    ("Taking the other one.", "coop_cli.cpp: 'the other one'"),
    ("Ready.", "coop_cli.cpp: the voice's warm-up line"),
    # round v68: the time said with an order, one sentence after the order's own words (coop_cli.cpp TimeWords)
    ("{n} seconds.", "coop_cli.cpp: the order lasts that long ('Holding up. 10 seconds.')"),
    ("1 second.", "coop_cli.cpp: the same, one second"),
    ("In {n} seconds.", "coop_cli.cpp: the order starts after that long ('Relocating. In 10 seconds.')"),
    ("In 1 second.", "coop_cli.cpp: the same, one second"),
    ("{n} more seconds.", "coop_cli.cpp: added to a timed order still running"),
    ("1 more second.", "coop_cli.cpp: the same, one second"),
    ("A few seconds.", "coop_cli.cpp: 'a few seconds', the game draws 3 to 7"),
    ("In a few seconds.", "coop_cli.cpp: starts after a few seconds"),
    ("About {n} seconds.", "coop_cli.cpp: a range said ('10 to 15 seconds'): its middle"),
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
    ("I don't see a way in.", "'go inside' with no door near"), ("I'm inside already.", "'go inside' in the room of every door near"), ("No free car around.", "GET_IN"),
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
    ("I can't get down from here.", "JUMP off what it stands on: no floor below its edges"),
    # bot v66 (2026-10-27): what the thing looked at is, out of the way, out of the room, a butt strike on glass
    ("That's {thing}.", "'what is that?': the thing under the player's crosshair (WHAT_THINGS)"), ("That's me.", "'what is that?' at the bot"),
    ("Nothing there, just the sky.", "'what is that?' with the crosshair on nothing"),
    ("No room to step aside.", "GIVE_WAY with no floor to either side"), ("I don't see a way out.", "'go outside' with no door near"),
    ("I'm outside already.", "'go outside' in no room of a door near"),
    ("Glass is broken.", "MELEE on glass: broken"), ("It won't break.", "MELEE on glass: four strikes and it holds"),
    ("I can't get to the glass.", "MELEE on glass: no way to its edge"),
    # 2026-10-27: doors (GOAP Phase 2: a shut door on the way, by hand or by its switch) and climbing (Phase 6: ledges, gaps, a crate as a step)
    ("There's a ledge.", "climb (Phase 6): the way up is a ledge within a jump; followed by 'I'll jump up.'"),
    ("I'll jump up.", "climb: the same"),
    ("A gap.", "climb: the way is over a gap between two floors; followed by 'I'll jump it.'"),
    ("I'll jump it.", "climb: the same"),
    ("Too high to jump.", "climb: the ledge needs a crate as a step; followed by 'I'll get a crate.'"),
    ("I'll get a crate.", "climb: the same"),
    ("I can't get up there.", "climb: the jump up did not land, or the place is up where no ledge or crate gets it"),
    ("I can't jump that.", "climb: the jump over the gap did not land"),
    ("I can't get to the crate.", "climb: no way to the crate it meant to carry"),
    ("The crate's gone.", "climb: the crate it meant to carry is no longer there"),
    ("Time's up.", "a timed order's time is over (round v68): the bot goes back to what it did before"),
    ("Didn't work.", "climb: the crate the order named was put down and tried, and the jump off it fell short; followed by 'Too high, even with the crate.'"),
    ("Too high, even with the crate.", "climb: the same"),
    ("Door's shut.", "doors (Phase 2): the way goes through a shut door; followed by 'Opening it.' or 'Getting the switch.'"),
    ("Getting the switch.", "doors: the door opens from a switch; also OPEN on a switch-only door"),
    ("Door's open.", "doors: it opened the door"),
    ("Open.", "doors: it used a switch that is not a door's"),
    ("It's open already.", "OPEN on a door that is open"),
    ("It won't open.", "doors: used by hand and still shut"),
    ("The switch did nothing.", "doors: the switch used and the door still shut"),
    ("I can't open that.", "OPEN on a thing that is no door and no switch"),
    ("I can't reach the door.", "doors: no way to the door's handle side"),
    ("I can't reach the switch.", "doors: no way to the switch"),
    ("I can't get to the switch.", "OPEN on a switch door whose switch has no way to it"),
    ("I can't get to it.", "OPEN on a door by hand with no way to it"),
    # 2026-10-28: the reasons after "I can't get there." (Planner/OVGateSubsystem.cpp Explain, the climb planner's why-not)
    ("No way there, not even through a door.", "after 'I can't get there.': the gates find no way, doors open or shut"),
    ("The door's shut; the switch is {n} m from it.", "after 'I can't get there.': a shut door on the way, opened by a switch (the planner then opens it)"),
    ("The door's shut; I can open it.", "after 'I can't get there.': a shut door it opens by hand"),
    ("The door's shut, and I see no switch.", "after 'I can't get there.': a shut door with no switch and no handle"),
    ("{n} doors are shut on the way.", "after 'I can't get there.': several shut doors; followed by 'The first's shut...'"),
    ("The first's shut; the switch is {n} m from it.", "the first of several shut doors, by a switch"),
    ("The first's shut; I can open it.", "the first of several shut doors, by hand"),
    ("The first's shut, and I see no switch.", "the first of several shut doors, no switch"),
    ("The ledge is too high, and there's nothing to stand on.", "after 'I can't get there.': the climb planner found a ledge beyond its jump and no crate to reach"),
]
# what the bot calls the thing under the crosshair (LyraStarterGame58 CoopBot OVCoop::ThingName and the client's BuildWorld):
# the slot "thing" lists them, so that the reply tables say them in the player's language
WHAT_THINGS = ["an enemy", "a teammate", "someone", "a switch", "the floor", "the ceiling", "a wall",
               "a door", "a window", "the stairs", "a chair", "a sofa", "a table", "a car", "some ammo", "a weapon", "a health pack",
               "a box", "a cable spool", "a teleport", "a field", "a garden bed", "a greenhouse", "a barn", "a chicken coop", "a beehive",
               "a well", "a fence", "a tree", "a foundation", "a bed", "a rock", "a big rock", "a small rock",
               "the blue bed", "the red bed", "the yellow bed", "the white bed", "the brown bed",
               "the main door", "the north door", "the south door", "the west door", "the east door",
               "the north window", "the south window", "the west window", "the east window",
               "the blue table", "the red table", "the yellow table", "the white table", "the brown table",
               "the blue stairs", "the red stairs", "the yellow stairs", "the white stairs", "the brown stairs",
               "a cardboard box", "a big box", "a small box", "a big spool", "a small spool"]
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
SLOTS_NOTE["said"] = ("the player's own words, a line the bot could not read, quoted in their language (lowercase, no stops); "
                      "open, no values: the line comes with it")
SLOTS_NOTE["meant"] = "the player's own words of the line the bot then read, quoted as 'said' is"
SLOT_VALUES = {
    "said": [],
    "meant": [],
    "where": ["on your pin", "here", "there", "to the left", "to the right", "forward", "back", "up", "down"],
    "sector": ["above", "below", "ahead", "behind you", "on the left", "on the right"],
    "zone": ["the basement", "the first floor", "the second floor", "the top floor", "the roof", "the way up", "the way down", "the way out",
             "the way in", "that place"],
    "side": [s + h for s in ("ahead", "on us", "behind us", "right", "left") for h in ("", ", high", ", low")],
    "weapon": ["pistol", "rifle", "shotgun", "weapon"],
    "verb": ["plant", "water", "harvest", "work the ground", "feed", "collect", "bring", "build", "repair", "tear down", "do that"],
    "item": ["wall", "floor", "ramp", "roof", "door", "window", "stairs", "fence", "pillar", "foundation", "corn", "wheat",
             "carrots", "potatoes", "tomatoes", "seeds", "plants", "crops", "chickens", "cows", "pigs", "animals", "eggs", "milk",
             "wood", "planks", "stone", "metal", "ammo", "water", "field", "barn", "well"],
    "thing": WHAT_THINGS,   # open: a label the level designer gave is said as it is
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
    # as the planner says them (world.py object_word: "garden_bed" is "garden bed")
    objects = [o["id"].replace("_", " ") for o in json.load(io.open(PLACES, encoding="utf-8"))["objects"]] + ["place"]
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
