"""
The place vocabulary of the v60 bots (the farmer and the builder beside the shooter, make_spec_v60.py): locations.json
(version 7, the v5x bots' file, left as it is) + the farm's and the building site's places = locations_v60.json, version 8.
Written BEFORE any v60 test line was read (then hashed into frozen.txt). Rule set v7 (locations.py) reads it unchanged:
a new place is a new entry, not new code.

  objects     field, bed, greenhouse, barn, coop, beehive, well, fence, tree, crate, foundation (spec_v60 "map"); a field,
              bed, barn, greenhouse, coop or fence is named by compass side. "well" only with "the" or "water" in front
              ("well, go there" is no place); "patch" and "row" are no bed ("patch the hole", "two in a row")
  ammo, weapon "ammo crate", "ammo box", "weapon crate"... stay ammo and weapon (the longest phrase wins): a crate that
              gives ammo is where the bot gets ammo, as before
  unknown_modifier  the crop words: "the wheat field", "the carrot bed" single out one field or bed by what grows there
  order_verb  the farmer's and the builder's verbs: such a verb starts the bot's own order, like "breach" or "plant"

    python make_locations_v60.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

COMPASS = ["north", "south", "west", "east"]
OBJECTS = [
    {"id": "field", "words": ["field", "fields", "farmland", "paddock", "paddocks", "meadow", "meadows"], "qualifiers": COMPASS},
    {"id": "bed", "words": ["bed", "beds", "garden bed", "garden beds", "flower bed", "flower beds", "vegetable bed",
                            "plot", "plots", "planter", "planters", "raised bed", "raised beds"], "qualifiers": COMPASS},
    {"id": "greenhouse", "words": ["greenhouse", "greenhouses", "green house", "hothouse", "glasshouse"], "qualifiers": COMPASS},
    {"id": "barn", "words": ["barn", "barns", "shed", "sheds", "storehouse", "storehouses", "silo", "silos", "granary",
                             "warehouse", "tool shed", "toolshed"], "qualifiers": COMPASS},
    {"id": "coop", "words": ["coop", "coops", "chicken coop", "hen house", "henhouse", "chicken house", "pen", "pens",
                             "stable", "stables", "sty", "pigsty", "pig pen", "corral"], "qualifiers": COMPASS},
    {"id": "beehive", "words": ["beehive", "beehives", "hive", "hives", "bee hive", "bee hives", "apiary"], "qualifiers": []},
    {"id": "well", "words": ["the well", "water well", "wells", "water tank", "water tanks", "water pump", "pump", "pumps"],
     "qualifiers": []},
    {"id": "fence", "words": ["fence", "fences", "fencing", "fence line"], "qualifiers": COMPASS},
    {"id": "tree", "words": ["tree", "trees", "woods", "forest", "treeline", "tree line"], "qualifiers": []},
    {"id": "crate", "words": ["crate", "crates", "box", "boxes", "chest", "chests", "container", "containers"], "qualifiers": []},
    {"id": "foundation", "words": ["foundation", "foundations", "building spot", "build spot", "building site",
                                   "construction site"], "qualifiers": []},
]
MORE_WORDS = {
    "ammo": ["ammo crate", "ammo crates", "ammo box", "ammo boxes", "ammunition crate", "ammunition box"],
    "weapon": ["weapon crate", "weapons crate", "gun crate", "weapon box", "weapons box"],
    "health": ["health box", "medical box", "medical crate"],
}
CROP_WORDS = ["wheat", "corn", "carrot", "carrots", "tomato", "tomatoes", "potato", "potatoes", "cabbage", "lettuce",
              "onion", "onions", "pumpkin", "pumpkins", "strawberry", "strawberries", "bean", "beans", "pea", "peas",
              "beet", "beets", "rice", "cotton", "sunflower", "sunflowers", "berry", "berries", "grape", "grapes",
              "herb", "herbs", "flower", "flowers", "vegetable", "veggie", "veg", "potatoe", "melon", "watermelon",
              "cucumber", "pepper", "garlic", "spinach", "turnip", "zucchini", "sugarcane", "tea", "coffee", "lavender",
              "hay", "crop", "orchard", "apple", "vineyard", "chicken", "pig", "cow", "sheep", "goat", "horse", "bee"]
ORDER_VERBS = ["build", "repair", "fix", "mend", "demolish", "dismantle", "harvest", "sow", "till", "plow", "plough", "hoe",
               "rake", "weed", "feed", "collect", "gather", "carry", "deliver", "chop", "fetch", "dig", "fertilize",
               "construct", "rebuild", "tear", "knock", "water", "irrigate", "reap", "patch"]


def main():
    v = json.load(io.open(os.path.join(HERE, "locations.json"), encoding="utf-8"))
    assert v["version"] == 7, v["version"]
    v["version"] = 8
    v["_note"] += (" Version 8 (the v60 bots, 2026-10-19, make_locations_v60.py; locations.json stays version 7 for the v5x "
                   "bots): the farm's and the building site's places (field, bed, greenhouse, barn, coop, beehive, well, "
                   "fence, tree, crate, foundation); 'ammo crate' and its like stay ammo / weapon / health; crop words single "
                   "out a field or bed (unknown_modifier); the farmer's and the builder's verbs are order verbs.")
    have = {o["id"] for o in v["objects"]}
    assert not have & {o["id"] for o in OBJECTS}
    for o in v["objects"]:
        o["words"] += [w for w in MORE_WORDS.get(o["id"], []) if w not in o["words"]]
    v["objects"] += OBJECTS
    W = v["words"]
    W["unknown_modifier"] += [w for w in CROP_WORDS if w not in W["unknown_modifier"]]
    W["order_verb"] += [w for w in ORDER_VERBS if w not in W["order_verb"]]
    path = os.path.join(HERE, "locations_v60.json")
    json.dump(v, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import locations
    voc = locations.load_vocab(path)          # validates: refuses a malformed file
    words = [w for o in v["objects"] for w in o["words"]]
    assert len(words) == len(set(words)), sorted({w for w in words if words.count(w) > 1})
    print(f"locations_v60.json: version {voc['version']}, {len(v['objects'])} objects, {len(voc['phrases'])} phrases")


if __name__ == "__main__":
    main()
