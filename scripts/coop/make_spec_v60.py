"""
v60: the bot as a farmer and a builder too, in the same game as the shooter (the owner, 2026-10-19). Written BEFORE any v60
test line exists (then hashed into frozen.txt). The v5x line (shooter only, bot v58 and chain v59 today) goes on beside it:
the game switches between the two brains.

The owner's words (2026-10-19): "чего нам будет стоить встроить дополнительно Интенты фермера и строителя?", then:
  - "Режимы смешанные": farming, building and fighting happen on one map, so a line is read with every intent available
    (no hard mode switch); the boundaries below decide the words both sides use ("plant", "clear", "cover", "wall");
  - "Строитель может построить что-то из арсенала строительной механики ... Построй стену, стена есть в меню, а построй
    столб - нет такого. Так же и с COLLECT и тд.": the intent is the VERB; what to build, plant, collect, feed or carry is
    an ITEM the line names (any noun, also one the game does not have), which the planner checks against the catalogue
    the game sends (its build menu, the seeds the bot carries, what lies around): "build a pillar" is BUILD with the item
    "pillar", and the game answers that it has none;
  - "Сначала понимание приказов": this round is the brain (data, classifier, item and place words, planner); the game's
    farming and building mechanics come later;
  - "Сразу создай версию v60. мы будем переключаться между v5x и v6x".
The developer's choices, told to the owner: ten intents after RELOAD, each in a family of its own (PLANT_CROP, WATER,
HARVEST, TILL, FEED, COLLECT, DELIVER, BUILD, REPAIR, DEMOLISH); a bare "plant" with no crop named stays PLANT (the bomb),
and the planner turns it into planting when the bot carries seeds and no bomb; picking up a weapon, ammo or health stays
MOVE_TO; "clear the room" stays ENTRY, "clear the weeds" is TILL; "breach the wall" stays BREACH, "tear down the wall" is
DEMOLISH; "reinforce the wall" is REPAIR. The farm's crops are the UltimateFarming pack's (in the project, models only).

Writes:
  blind/spec_v60.json        what the v60 blind authors and annotators see: the v58 spec, the setting widened, the ten
                             intents, the boundaries, the modifier "item", the farm's and the builder's places and items
  intents_v60.json           the model-side vocabulary (57 intents)
  seed_commands_v60.json     seed set v58 (ids unchanged) + the seeds below; _relabel_v60 = _relabel_v58

    python make_spec_v60.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

SETTING_ADD = (" The same game also has farming and building, on the same map and at the same time as the fighting: the "
               "bot can be told to plant, water and harvest crops, prepare the ground, feed animals, collect produce and "
               "materials, carry things somewhere, and build, repair or take down pieces from its build menu. A line is "
               "read with every intent available; nothing tells the bot which kind of work the player has in mind except "
               "the line itself.")

NEW_INTENTS = {
    "PLANT_CROP": (
        "the bot plants or sows a crop: seeds, seedlings, bulbs, saplings, or a crop by name (plant carrots, sow the wheat, "
        "put the tomato seedlings in, plant some potatoes in that bed, seed the north field, put a sunflower here). What it "
        "plants is the item; where is the target (a field, a bed, a plot, a planter, the greenhouse, here, my pin). Planting "
        "the bomb or the defuser is PLANT; a bare 'plant it' / 'plant here' with no crop or seed named is PLANT too (the "
        "planner looks at what the bot carries)"),
    "WATER": (
        "the bot waters plants or ground (water the carrots, water the north field, give the tomatoes some water, sprinkle "
        "the beds, water everything in the greenhouse). Fetching water or filling a can is COLLECT"),
    "HARVEST": (
        "the bot harvests crops that grow in the ground or on plants (harvest the wheat, pick the tomatoes, dig up the "
        "potatoes, cut the corn, gather the strawberries, reap the field, pick the grapes). Taking eggs, honey, milk, wood "
        "or stone is COLLECT"),
    "TILL": (
        "the bot prepares the ground for planting or keeps it clean: till, plow, hoe, rake, dig a bed, loosen the soil, "
        "weed, pull the weeds, clear the field of rocks or weeds, fertilize, spread manure. 'Clear the room' / 'clear the "
        "basement' (of enemies) stays ENTRY; 'dig in' (stay and hold) stays HOLD_POSITION"),
    "FEED": (
        "the bot feeds animals (feed the chickens, give the cows some hay, fill the troughs, throw grain to the hens, feed "
        "the pigs). The item is the food, the target the animals or their pen"),
    "COLLECT": (
        "the bot gathers produce or materials that are not crops in the ground and keeps them: collect the eggs, get the "
        "honey from the hives, milk the cow, shear the sheep, chop some wood, cut down that tree, mine stone, pick up the "
        "planks, grab the seeds from the shed, fill the watering can. Picking up a weapon, ammo or health is MOVE_TO, as "
        "before; harvesting crops is HARVEST; bringing something to a place or a person is DELIVER"),
    "DELIVER": (
        "the bot carries something to a place or to a person: bring me the wood, take the wheat to the barn, put the eggs "
        "in the crate, carry the planks over here, give me the seeds, store the tools in the shed, drop the logs by the "
        "wall. Fetching the thing first is part of the order. A plain 'come here' is FOLLOW_ME"),
    "BUILD": (
        "the bot builds or places a piece from its build menu: build a wall, put up a fence, place a barricade here, build "
        "a ramp up to the roof, set up a watchtower, lay a foundation, put in a door, make a crate, build cover. The item "
        "is what to build, as the player names it, also a piece the menu may not have ('build a pillar': the game answers "
        "that it has none). Taking cover behind something is TAKE_COVER; 'build cover' / 'put up some cover' is BUILD"),
    "REPAIR": (
        "the bot repairs or strengthens something built or damaged: fix the wall, patch that hole, repair the fence, mend "
        "the gate, reinforce the barricade, fill the hole in the wall, seal the breach, reinforce that wall (as defenders "
        "do before a fight). Repairing the car is REPAIR too"),
    "DEMOLISH": (
        "the bot takes down a structure: tear down the fence, demolish that wall, dismantle the watchtower, remove the "
        "barricade, knock down the shed, take apart the ramp. Blowing a way into a room through a wall is BREACH ('breach "
        "the wall', 'open the wall'); shooting at a wall is OPEN_FIRE"),
}
# whole sentences appended to existing intents: the boundaries the new intents draw
APPENDED = {
    "PLANT": ". Planting a crop, seeds or seedlings is PLANT_CROP ('plant the carrots', 'sow the field'); a bare 'plant' "
             "with nothing named stays this intent",
    "ENTRY": ". Clearing a field of weeds or rocks is TILL",
    "BREACH": ". Taking down a structure without going through it ('tear down the fence', 'demolish the shed') is DEMOLISH",
    "MOVE_TO": (". Gathering produce or materials ('collect the eggs', 'chop some wood') is COLLECT and carrying something "
                "somewhere ('bring the wood here') is DELIVER; going to the field, the barn or the greenhouse is this intent"),
    "TAKE_COVER": ". Building cover ('build some cover here', 'put up a barricade') is BUILD",
    "HELP": (". Help with a named job is that job ('help me harvest the wheat' is HARVEST, 'help me build the wall' is "
             "BUILD)"),
    "COVER_ME": ". 'Cover me while I build / plant / harvest' is this intent: the player does the work",
    "NONE": (". What the player says THEY do on the farm or the building ('I'm planting the carrots', 'I'll build the wall') "
             "and reports ('the wheat is ready', 'the fence is broken', 'we're out of wood') are NONE"),
    "HOLD_POSITION": ". 'Dig in' (stay put) is this intent; digging the ground is TILL",
}
ITEM_MODIFIER = (
    "the thing the order acts on, for the farmer's and the builder's ten intents (PLANT_CROP to DEMOLISH), as the player "
    "names it: lowercase, the noun with the words that name its kind ('wooden wall', 'tomato seedlings', 'scrap metal'), "
    "without articles, numbers, possessives and amounts ('some', 'a few', 'two rows of', 'a bunch of'); null when the "
    "line names nothing the order acts on, or only a general word ('build here', 'water them', 'harvest everything', "
    "'water the plants', 'harvest the crops', 'collect materials'). It is what was SAID, also a thing the game may not "
    "have ('build a pillar' = 'pillar'). Per intent: PLANT_CROP the crop or seeds planted; WATER and HARVEST the crop; "
    "TILL null; FEED the animals fed, not the food ('give the cows some hay' = 'cows'); COLLECT what is gathered or "
    "taken ('collect the eggs' = 'eggs', 'chop some wood' = 'wood', 'milk the cow' = 'cow'); DELIVER what is carried "
    "('bring me the planks' = 'planks'); BUILD what is built; REPAIR and DEMOLISH the structure ('fix the wall' = "
    "'wall'). One of the map's objects is never the item but the target ('water the north field' = target field / "
    "north, item null; 'fix the door' = target door, item null), except for BUILD, COLLECT and DELIVER, where what is "
    "built, gathered or carried is the item even when the map has the word ('build a fence' = item 'fence', target "
    "null; 'carry the crate to the barn' = item 'crate', target barn). For every other intent null")
# appended to the target modifier: where the new intents act
TARGET_ADD = (
    " For the farmer's and the builder's ten the target is the place where the work is done: the field or bed to plant, "
    "water, harvest or till ('plant carrots in the north bed' = bed / north), the animals' pen to feed in, the place to "
    "gather from (COLLECT: 'get the honey from the hives' = beehive), the place to build at (BUILD: 'build a wall at the "
    "east door' = door / east), the structure to repair or tear down when it is one of the map's objects (REPAIR / "
    "DEMOLISH: 'fix the fence' = fence), and for DELIVER the place the thing goes to ('take the wheat to the barn' = "
    "barn; to the player: all null). The thing itself is the item (see item). A crop word that singles out a field or "
    "bed ('the wheat field', 'the carrot bed') is unknown_modifier.")
NEW_PLACES = {
    "field": "a field: crops grow on it (the north field; fields and beds are named by compass side)",
    "bed": "a garden bed, a plot, a row, a planter",
    "greenhouse": "the greenhouse",
    "barn": "a barn, a shed, a storehouse",
    "coop": "a chicken coop, a hen house, a pen, a stable, a sty",
    "beehive": "beehives",
    "well": "a well, a water tank, a pump",
    "fence": "a fence",
    "tree": "a tree, trees, the woods",
    "crate": "a crate, a box, a chest, a container",
    "foundation": "a building spot, a foundation, a frame the builder works on",
}
ITEMS = {
    "crops (the farm's)": ["arugula", "beans", "beets", "berries", "blueberries", "broccoli", "cabbage", "cacao", "carrots",
                           "cauliflower", "coffee", "corn", "cotton", "cucumbers", "eggplant", "flax", "garlic", "grapes",
                           "hazelnuts", "hemp", "lavender", "lettuce", "mint", "mushrooms", "onions", "parsley", "peas",
                           "peppers", "potatoes", "pumpkins", "rice", "roses", "spinach", "strawberries", "sugarcane",
                           "sunflowers", "tea", "tobacco", "tomatoes", "turnips", "watermelons", "wheat", "zucchini"],
    "produce and materials": ["eggs", "honey", "milk", "wool", "hay", "grain", "seeds", "seedlings", "fertilizer", "manure",
                              "water", "wood", "logs", "planks", "stone", "bricks", "metal", "nails", "sandbags", "tools"],
    "animals": ["chickens", "hens", "cows", "pigs", "sheep", "goats", "horses", "bees"],
    "build pieces (a build menu has some of them, not all)": [
        "wall", "wooden wall", "stone wall", "fence", "gate", "door", "window", "floor", "foundation", "roof", "ramp",
        "stairs", "ladder", "barricade", "sandbag wall", "watchtower", "crate", "shed", "bridge", "pillar", "turret",
        "trench", "bench", "table"],
}
NEW_MODEL = {
    "PLANT_CROP": {"label": "plant a crop", "description": "plant or sow a crop: seeds, seedlings, a crop by name"},
    "WATER": {"label": "water the plants", "description": "water plants or ground"},
    "HARVEST": {"label": "harvest", "description": "harvest crops from the ground or the plants"},
    "TILL": {"label": "till the ground", "description": "prepare or clean the ground: till, plow, weed, fertilize"},
    "FEED": {"label": "feed the animals", "description": "feed animals"},
    "COLLECT": {"label": "collect", "description": "gather produce or materials: eggs, honey, wood, stone"},
    "DELIVER": {"label": "bring it", "description": "carry something to a place or a person"},
    "BUILD": {"label": "build", "description": "build or place a piece from the build menu"},
    "REPAIR": {"label": "repair", "description": "repair or strengthen something built or damaged"},
    "DEMOLISH": {"label": "tear it down", "description": "take down a structure"},
}
FAMILY_NOTE = ("v60 families: v57's (v58 kept them); the ten new intents each in a family of its own (plant_crop, water, "
               "harvest, till, feed, collect, deliver, build, repair, demolish). They come after RELOAD, before NONE")

CROPS = ITEMS["crops (the farm's)"]
NEW_SEEDS = {
    "PLANT_CROP": [
        "plant the carrots", "plant some carrots here", "plant carrots in that bed", "sow the wheat", "sow the north field",
        "seed the field", "plant the tomato seedlings", "put the tomatoes in the ground", "plant some potatoes",
        "plant potatoes over there", "plant the seeds", "plant these seeds", "put the seeds in", "sow some seeds here",
        "plant corn in the east field", "plant a row of lettuce", "plant sunflowers along the fence", "plant the onions",
        "plant garlic in the greenhouse", "plant some strawberries", "put a pumpkin here", "plant the beans by the wall",
        "sow the peas", "plant rice in the wet field", "plant some mint in the planter", "plant the cabbage",
        "plant the seedlings at my pin", "sow it with wheat", "fill that bed with carrots", "plant the whole field with corn",
        "get the seeds in the ground", "plant two rows of beets", "plant cucumbers in the greenhouse", "plant a tree here",
        "plant the grapes on the south side", "plant some flowers", "put some roses by the door", "go plant the carrots",
        "start planting", "start sowing", "sow the beds", "plant lavender over there", "plant the zucchini",
        "plant some peppers", "put in the onion sets", "plant the sugarcane", "plant cotton in the big field",
        "replant the tomatoes", "plant the turnips in the north bed", "plant spinach next to the lettuce"],
    "WATER": [
        "water the plants", "water the carrots", "water the field", "water the north field", "water the beds",
        "water the greenhouse", "water everything", "water them", "water it", "give the tomatoes some water",
        "give the plants a drink", "sprinkle the beds", "water the seedlings", "water the crops", "go water the garden",
        "water the corn", "water the strawberries", "water what we planted", "water the lettuce", "water the potatoes",
        "water the east field", "water the pumpkins", "water the flowers", "water the planter by the door",
        "water the rows by the fence", "the plants need water, water them", "keep the beds watered",
        "water the trees", "water the sunflowers", "water the beans", "water the whole garden", "give the field some water",
        "irrigate the field", "water those over there", "water the plot at my pin", "start watering",
        "go water the plants", "water the cucumbers in the greenhouse", "water the herbs", "soak the beds"],
    "HARVEST": [
        "harvest the wheat", "harvest the field", "harvest the carrots", "harvest everything that's ready",
        "pick the tomatoes", "pick the strawberries", "pick the berries", "pick the grapes", "dig up the potatoes",
        "dig up the carrots", "cut the corn", "cut the wheat", "reap the field", "gather the strawberries",
        "harvest the north field", "harvest the greenhouse", "pull up the onions", "pull the beets", "pick the apples",
        "pick the cucumbers", "harvest the pumpkins", "cut the lettuce", "harvest the crops", "bring in the harvest",
        "pick the peppers", "harvest the beans", "pick the peas", "harvest the sunflowers", "cut the sugarcane",
        "pick the cotton", "harvest the rice", "pick the ripe ones", "harvest what's ready", "go harvest the wheat",
        "start harvesting", "pick the tomatoes in the greenhouse", "harvest the east field", "cut the hay",
        "pick the blueberries", "harvest the garlic", "pick the mushrooms", "harvest the turnips", "pick the zucchini",
        "harvest the tea", "pick the lavender"],
    "TILL": [
        "till the field", "till the soil", "plow the field", "plow the north field", "hoe the beds", "rake the beds",
        "dig a bed here", "dig a new bed", "loosen the soil", "weed the beds", "pull the weeds", "pull the weeds in the greenhouse",
        "clear the weeds", "clear the field", "clear the rocks off the field", "clear the field of rocks",
        "fertilize the field", "fertilize the beds", "spread the manure", "spread fertilizer on the north field",
        "prepare the soil", "get the field ready for planting", "turn the soil", "dig over the garden", "plow the east field",
        "hoe the rows", "till the ground at my pin", "weed the carrots", "get rid of the weeds", "clean up the beds",
        "till it", "plow it", "dig up the ground here", "prepare the beds", "till the greenhouse beds", "go till the field",
        "start plowing", "rake the field", "weed around the tomatoes", "clear the stones from the garden"],
    "FEED": [
        "feed the chickens", "feed the hens", "feed the cows", "feed the pigs", "feed the animals", "feed the sheep",
        "feed the goats", "feed the horses", "give the cows some hay", "throw some grain to the chickens",
        "fill the troughs", "fill the trough", "feed them", "give the pigs their food", "feed the chickens in the coop",
        "give the horses some oats", "feed the animals in the barn", "put hay in the pen", "feed the bees",
        "give the goats some hay", "go feed the chickens", "feed the cows in the stable", "feed everybody",
        "the animals are hungry, feed them", "put out some feed", "fill the feeder", "feed the pigs some scraps",
        "give the sheep some grain", "give them some water and feed", "top up the troughs", "feed the cattle",
        "feed the livestock", "feed the hens at the coop", "start feeding the animals", "give the chickens some corn"],
    "COLLECT": [
        "collect the eggs", "get the eggs", "grab the eggs from the coop", "collect the honey", "get the honey from the hives",
        "milk the cow", "milk the cows", "milk the goats", "shear the sheep", "chop some wood", "chop wood",
        "cut down that tree", "cut down the tree by the barn", "chop down the trees over there", "mine some stone",
        "get some stone", "collect some stone", "gather some wood", "get some wood", "pick up the planks",
        "grab the planks", "collect the logs", "gather the logs", "pick up the bricks", "grab some nails",
        "get the seeds from the shed", "grab the seeds", "fill the watering can", "get some water from the well",
        "collect the wool", "gather some hay", "collect the hay", "get some fertilizer", "go collect the eggs",
        "gather materials", "collect materials", "get the tools from the shed", "grab some sandbags", "pick up the sandbags",
        "gather firewood", "collect the scrap metal", "get some metal", "go chop some wood", "start collecting the eggs",
        "pick up that crate of seeds"],
    "DELIVER": [
        "bring me the wood", "bring me some planks", "bring the planks over here", "bring the logs here",
        "take the wheat to the barn", "take the eggs to the house", "put the eggs in the crate", "put the eggs in the basket",
        "carry the planks to the wall", "carry the logs to the north wall", "give me the seeds", "hand me the seeds",
        "give me some stone", "store the tools in the shed", "put the tools in the barn", "drop the logs by the wall",
        "drop the wood here", "bring the hay to the barn", "take the honey to the storehouse", "bring me the hammer",
        "take the carrots to the crate", "put the potatoes in the barn", "bring me some water", "bring the bricks to my pin",
        "take the sandbags to the window", "bring the sandbags here", "carry the crate over there", "bring it here",
        "bring it to me", "take it to the barn", "put it in the crate", "bring me what you collected",
        "bring the harvest to the barn", "load the wheat into the truck", "put the logs in the truck",
        "unload the truck in the barn", "bring the materials to the building spot", "take the seeds to the greenhouse",
        "deliver the eggs to the house", "drop the planks at the foundation"],
    "BUILD": [
        "build a wall", "build a wall here", "build a wooden wall", "build a stone wall over there", "put up a fence",
        "put up a fence around the field", "build a fence", "place a barricade here", "build a barricade",
        "put up a barricade at the door", "build a ramp", "build a ramp up to the roof", "set up a watchtower",
        "build a watchtower", "lay a foundation", "lay the foundation here", "put in a door", "build a door",
        "make a crate", "build a crate", "build cover", "build some cover here", "put up some cover",
        "build a sandbag wall", "stack some sandbags here", "build a ladder", "put a ladder here", "build stairs to the roof",
        "build a bridge", "build a bridge over the river", "build a shed", "build a pillar", "build a roof",
        "put a roof on it", "build a floor", "build a gate", "put a gate in the fence", "build a trench", "dig a trench",
        "build a turret", "place a turret here", "build a bench", "build a table", "build a wall at my pin",
        "build a wall from here to there", "build a wall on the north side", "build a window", "put a window in",
        "build it", "build one here", "build another one", "start building", "go build the wall", "make a wall",
        "construct a wall", "raise a wall here"],
    "REPAIR": [
        "fix the wall", "repair the wall", "patch that hole", "patch the hole in the wall", "fill the hole",
        "fill the hole in the wall", "repair the fence", "fix the fence", "mend the fence", "mend the gate",
        "fix the gate", "repair the barricade", "reinforce the barricade", "reinforce the wall", "reinforce that wall",
        "reinforce the north wall", "seal the breach", "seal that hole", "fix the door", "repair the door",
        "fix the roof", "repair the roof", "fix the ramp", "repair the watchtower", "fix it", "repair it",
        "patch it up", "fix the window", "board up the window", "board up that window", "fix the car", "repair the car",
        "repair the truck", "fix the bridge", "repair the shed", "restore the wall", "rebuild the wall", "rebuild the fence",
        "fix the holes in the wall", "repair the damage", "go fix the wall", "start repairing", "patch the floor",
        "fix the floor"],
    "DEMOLISH": [
        "tear down the fence", "tear down that wall", "tear it down", "demolish the wall", "demolish that wall",
        "demolish the shed", "dismantle the watchtower", "dismantle the barricade", "remove the barricade",
        "take down the barricade", "take down the fence", "knock down the shed", "knock down that wall",
        "take apart the ramp", "take the ramp apart", "remove the ramp", "remove that wall", "destroy the barricade",
        "break down the fence", "pull down the fence", "dismantle it", "take it down", "remove it",
        "tear down the roof", "remove the ladder", "take down the ladder", "remove the sandbags", "clear away the barricade",
        "get rid of that wall", "get rid of the fence", "demolish the tower", "tear down the old barn",
        "dismantle the bridge", "remove the gate", "take the door off", "deconstruct the wall", "scrap the turret",
        "remove the turret", "pull down the shed", "level the shed"],
    # boundaries: the words the new intents share with the old ones, under the old ones
    "PLANT": ["plant the bomb on site", "plant the defuser here", "plant the charge", "go plant the bomb"],
    "ENTRY": ["clear the room", "clear the building", "clear the barn", "clear the house"],
    "BREACH": ["breach the barn wall", "blow the wall", "breach the shed"],
    "TAKE_COVER": ["take cover behind the fence", "get behind the barricade", "hide behind the crate",
                   "take cover by the barn", "get behind the wall"],
    "MOVE_TO": ["go to the field", "go to the barn", "go to the greenhouse", "go to the coop", "go to the well",
                "move to the fence", "go to the north field", "go to the shed", "head to the beehives",
                "go to the building spot", "go to the crate"],
    "COVER_ME": ["cover me while I build", "cover me while I plant", "watch my back while I harvest",
                 "cover me, I'm fixing the wall"],
    "HOLD_POSITION": ["dig in", "dig in here", "dig in and hold"],
    "CHECK": ["check the crops", "check the field", "check the barn", "check the coop", "check the greenhouse",
              "check if the wheat is ready", "check the fence"],
    "NONE": ["I'm planting the carrots", "I'll build the wall", "the wheat is ready", "the fence is broken",
             "we're out of wood", "the chickens are hungry", "nice harvest", "I'm fixing the wall", "the wall is done",
             "that's a lot of carrots", "the barn is full", "I'll water the plants", "we need more planks"],
    "WAIT": ["don't harvest yet", "don't water the tomatoes", "don't build here", "don't tear it down",
             "don't plant there", "don't feed them yet", "don't chop that tree", "don't fix it yet"],
}
ON_SIGNAL = {"HARVEST": ["harvest the wheat on my go", "pick the tomatoes when I say"],
             "BUILD": ["build the wall on my go", "put up the barricade when I say"],
             "DEMOLISH": ["tear down the fence on my go"],
             "REPAIR": ["fix the wall when I say"]}


def main():
    spec = json.load(io.open(os.path.join(HERE, "blind", "spec_v58.json"), encoding="utf-8"))
    spec["setting"] += SETTING_ADD
    for k, v in APPENDED.items():
        assert k in spec["intents"], k
        spec["intents"][k] += v
    none = spec["intents"].pop("NONE")
    spec["intents"].update(NEW_INTENTS)
    spec["intents"]["NONE"] = none
    spec["modifiers"]["target"] += TARGET_ADD
    spec["modifiers"]["item"] = ITEM_MODIFIER
    spec["map"]["objects"].update(NEW_PLACES)
    spec["map"]["note"] += (" The farm and the building site add their places: fields and beds, the greenhouse, the barn, "
                            "the coop, the beehives, the well, fences, trees, crates, building spots.")
    spec["items"] = {"note": "what a line names as the item: examples by kind, not a closed list (the game has its own "
                             "catalogue; a line may name anything)", **ITEMS}
    json.dump(spec, io.open(os.path.join(HERE, "blind", "spec_v60.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    model = json.load(io.open(os.path.join(HERE, "intents_v57.json"), encoding="utf-8"))
    notes = {k: model.pop(k) for k in [k for k in model if k.startswith("_")]}
    none = model.pop("NONE")
    model.update(NEW_MODEL)
    model["NONE"] = none
    model.update(notes)
    model["_note_v60"] = FAMILY_NOTE
    json.dump(model, io.open(os.path.join(HERE, "intents_v60.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    labels = [k for k in model if not k.startswith("_")]
    assert labels == list(spec["intents"]), (labels, list(spec["intents"]))

    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v58.json"), encoding="utf-8"))
    relabel = dict(seeds["_relabel_v58"])
    owner = {t: relabel.get(f"seed_{k}_{n}", k) for k, v in seeds.items() if not k.startswith("_") for n, t in enumerate(v)}
    extra = {}
    for src in (NEW_SEEDS, ON_SIGNAL):
        for k, v in src.items():
            assert k in labels, k
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
    seeds["_relabel_v60"] = relabel
    seeds["_note_v60"] = (f"v60 (make_spec_v60.py, before any v60 test line existed): seed set v58 + {added} seeds of the "
                          "farmer's and the builder's ten intents and of the boundaries they share with the shooter's "
                          "(plant, clear, breach, cover, dig in, check, what the player says they do). _relabel_v60 = "
                          "_relabel_v58")
    json.dump(seeds, io.open(os.path.join(HERE, "seed_commands_v60.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n = sum(len(v) for k, v in seeds.items() if not k.startswith("_"))
    print(f"spec_v60: {len(spec['intents'])} intents (last: {list(spec['intents'])[-11:]}); intents_v60: {len(labels)}; "
          f"seeds v60: {n} (+{added}); already seeds: {had}")
    print({k: len(v) for k, v in NEW_SEEDS.items()})


if __name__ == "__main__":
    main()
