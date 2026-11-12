"""The place vocabulary v16 (round v70, the owner 2026-11-11): «Едь к банку», «там есть ресторан, банк и так далее» -- the city
(L_OVModernCity, ollaya-c1's map) and its "Best Burger" restaurant. Built from v15 (locations_v68.json, make_places_v68.py).

Twenty objects, appended after v15's 25 (the objects keep their places in the list: the C++ indexes them):
  city places   bank, restaurant, cafe, shop, hotel, pharmacy, gas_station, parking, junction, traffic_light, crosswalk
  the restaurant and the street (ollaya-c1's offer): counter, kiosk, bench, bin, atm, parasol, menu, kitchen, drinks_machine
The decoder writes these English words for the Russian ones (ollaya-c1, 2026-11-11): стойка / касса -> counter, терминал ->
kiosk, скамейка -> bench, урна -> bin, банкомат -> ATM, зонт -> parasol, меню -> menu, кухня -> kitchen, автомат с напитками ->
drinks machine. The classifier does not learn place names; the longest phrase wins.

Qualifiers (only v15's ids; no new qualifier): the buildings, the parking, the junction, the traffic light and the crosswalk take
the sides (north, south, west, east), as the barn and the greenhouse; the bench, the bin and the parasol take the colours, as
the table; the rest none (a qualifier they cannot carry flags the target unknown_modifier, as "the blue door").

The words chosen against the rule words (every new phrase was checked against v15's phrases and word lists: conflicts(), printed
by this script; check_places_v70.py compares v15 and v16 line by line):
  bank     "bank" is a verb of the direction rules (words.dir_lead_lateral, words.dir_turn: "bank left" = veer). The place is the
           bare "bank"; the verb is kept by ignore phrases that start with it ("bank left", "bank right", "bank hard", "bank a
           left", "bank to the left", ...): they hide "bank" from the place words and leave every rule word as v15 read it. A
           determiner makes it a noun: "the bank", "a bank", "the banks" are place words too, so "the bank right next to the
           hotel" and "drive to the bank to the left" stay the bank (the longest phrase at "the" is matched before the ignore
           phrase at "bank" can be). "bank the" / "banks the" are ignored too: the recogniser's "bang the door" ("Bank the door
           with an entry with me", r6 lines) stays the door. "river bank" is ignored: "go gather some clay at the river bank"
           (a real line) is no bank. "bank machine" is not an ATM word: "the bank machine" would be read "the bank" + "machine".
  store    a farm verb (items: DELIVER "store the tools in the shed", "store wheat in the barn"): no bare "store". The shop is
           "the store", "a store", "stores", "the stores", "nearest store", "closest store" and the compounds ("grocery store",
           ...); "that store" / "this store" are left to the pointer ("this" + a word the vocabulary does not know).
  bin      "my bin" is ignored: the recogniser's "my pin" (Parakeet: "Check my bin.", "Throw a smoke on my bin", "try again at
           my bin"); "nice shop" and "good shop" too ("nice shot"). "should came on the bin" (an owner line) stays a bin.
  market   not a shop word: the recogniser's "marker" (owner-era lines "go to my market", "stay at my market", "look at my
           market"); "supermarket", "marketplace", "minimarket" are.
  menu     "main menu", "pause menu", "game menu", "start menu", "options menu", "settings menu", "build menu", "buy menu" are
           the game's screens: ignored.
  counter  "counter attack", "counter attacks", "counter attacking", "counter push", "counter strafe" are moves: ignored.
           Not "till" (an order verb, "till the field", and words.pin_wait_prep "wait till my mark"), not "register" alone,
           not "desk" or "bar" alone ("health bar"), not "reception" alone (radio).
  others   not "hostel" (a recogniser's "hostile"), "inn" (a recogniser's "in"), "canteen" (a flask), "booth" (the map's
           booths are sofas), "stall" (a verb: "stall them"), "crossing" (a verb), "park" (a verb: "park here"), "gas" / "petrol"
           alone ("take it easy on the gas"), "car park" (a newline is no punctuation to the matcher: "hop outta the car\npark
           at the pin", a real chain line, would be a parking; and "stop the car park here"), "station" alone, "signal" alone
           ("on my signal"), "light" / "lights" alone ("light em up"), "trash" alone ("this map is trash"; nor "the trash":
           "pick up the trash" is litter, and "the trash" would cut "the trash can" short), "coffee" alone (a crop word,
           words.unknown_modifier), "pub" (a recogniser's "pop"). "café" is the token "caf" (the matcher reads ASCII letters
           only), so "caf" is a cafe word.
  longest  "gas pump", "fuel pump", "petrol pump" (gas station) win over the well's "pump"; "kitchen counter" (counter) over
           "kitchen"; "coffee shop" (cafe), "burger shop", "pizza shop" (restaurant) over "shop".

    python make_places_v70.py

The vocabulary goes into a bot's intent_config.json by `COOP_PLACES=locations_v70.json python export_cpp.py BOT --config-only`
(or COOP_TAG v70: locations.vocab_file), and the place and world tests are made again with the same vocabulary.
check_places_v70.py checks the grounding of the new words and compares v15 and v16 on every line the place tests hold.
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIDES = ["north", "south", "west", "east"]
COLOURS = ["blue", "red", "yellow", "white", "brown"]

# appended after v15's objects, in this order (the C++ indexes the objects by their place in the list)
NEW_OBJECTS = [
    {"id": "bank", "words": ["bank", "banks", "the bank", "a bank", "the banks"], "qualifiers": SIDES},
    {"id": "restaurant", "words": ["restaurant", "restaurants", "diner", "diners", "burger place", "burger places", "burger joint",
                                   "burger bar", "burger shop", "burger restaurant", "fast food", "fast food place",
                                   "fast food restaurant", "fast food joint", "pizzeria", "pizza place", "pizza shop",
                                   "pizza restaurant", "eatery", "bistro", "cafeteria"], "qualifiers": SIDES},
    {"id": "cafe", "words": ["cafe", "cafes", "caf", "coffee shop", "coffee shops", "coffee house", "coffeehouse", "coffee bar",
                             "coffee place"], "qualifiers": SIDES},
    {"id": "shop", "words": ["shop", "shops", "the store", "a store", "stores", "the stores", "nearest store", "closest store",
                             "grocery store", "grocery shop", "grocery", "general store", "convenience store", "corner store",
                             "corner shop", "department store", "toy store", "shoe store", "clothing store", "clothes store",
                             "book store", "bookstore", "supermarket", "supermarkets", "marketplace", "mall", "malls", "shopping mall", "shopping center", "shopping centre", "minimarket", "mini market",
                             "boutique"], "qualifiers": SIDES},
    {"id": "hotel", "words": ["hotel", "hotels", "motel", "motels"], "qualifiers": SIDES},
    {"id": "pharmacy", "words": ["pharmacy", "pharmacies", "drugstore", "drugstores", "drug store", "drug stores", "chemist",
                                 "chemists"], "qualifiers": SIDES},
    {"id": "gas_station", "words": ["gas station", "gas stations", "petrol station", "petrol stations", "filling station",
                                    "filling stations", "fuel station", "fuel stations", "service station", "service stations",
                                    "gas pump", "gas pumps", "petrol pump", "petrol pumps", "fuel pump", "fuel pumps"],
     "qualifiers": SIDES},
    {"id": "parking", "words": ["parking", "parking lot", "parking lots", "parking space", "parking spaces", "parking spot",
                                "parking spots", "parking place", "parking area", "parking garage", "parking garages"],
     "qualifiers": SIDES},
    {"id": "junction", "words": ["junction", "junctions", "crossroads", "crossroad", "intersection", "intersections", "roundabout",
                                 "roundabouts"], "qualifiers": SIDES},
    {"id": "traffic_light", "words": ["traffic light", "traffic lights", "stoplight", "stoplights", "stop light", "stop lights",
                                      "traffic signal", "traffic signals"], "qualifiers": SIDES},
    {"id": "crosswalk", "words": ["crosswalk", "crosswalks", "zebra crossing", "zebra crossings", "pedestrian crossing",
                                  "pedestrian crossings"], "qualifiers": SIDES},
    {"id": "counter", "words": ["counter", "counters", "checkout", "checkouts", "checkout counter", "cash register", "cash registers",
                                "cash desk", "cashier", "cashier desk", "service counter", "bar counter", "front desk",
                                "reception desk", "kitchen counter"], "qualifiers": []},
    {"id": "kiosk", "words": ["kiosk", "kiosks", "terminal", "terminals", "self order kiosk", "ordering kiosk", "ordering kiosks",
                              "order kiosk", "newsstand", "news stand"], "qualifiers": []},
    {"id": "bench", "words": ["bench", "benches", "park bench", "park benches"], "qualifiers": COLOURS},
    {"id": "bin", "words": ["bin", "bins", "trash can", "trash cans", "trashcan", "trashcans", "trash bin", "trash bins",
                            "garbage can", "garbage cans", "garbage bin", "garbage bins", "rubbish bin", "rubbish bins", "waste bin",
                            "waste bins", "litter bin", "litter bins", "dustbin", "dustbins", "wastebasket", "dumpster",
                            "dumpsters"], "qualifiers": COLOURS},
    {"id": "atm", "words": ["atm", "atms", "cash machine", "cash machines", "cashpoint", "cashpoints", "cash point",
                            "cash dispenser"], "qualifiers": []},
    {"id": "parasol", "words": ["parasol", "parasols", "umbrella", "umbrellas", "sunshade", "sunshades", "sun umbrella",
                                "patio umbrella", "beach umbrella"], "qualifiers": COLOURS},
    {"id": "menu", "words": ["menu", "menus", "menu board", "menu boards"], "qualifiers": []},
    {"id": "kitchen", "words": ["kitchen", "kitchens"], "qualifiers": []},
    {"id": "drinks_machine", "words": ["drinks machine", "drinks machines", "drink machine", "drink machines", "drinks dispenser",
                                       "drinks dispensers", "drink dispenser", "soda machine", "soda machines", "soda fountain",
                                       "soda fountains", "drinks fountain", "vending machine", "vending machines"], "qualifiers": []},
]

# phrases that hide a new place word where it is no place (see the docstring)
NEW_IGNORE = [
    # "bank" the verb: v15 reads the direction after it (words.dir_lead_lateral, words.dir_turn)
    "bank left", "bank right", "bank hard", "bank a left", "bank a right", "bank to the left", "bank to the right",
    # the recogniser's "bang the door" (r6 lines: "Bank the door with an entry with me", "You Banks the doorway then entry with me")
    "bank the", "banks the",
    "river bank", "river banks",
    # the game's screens (the bot's own line: "no {item} in my build menu")
    "main menu", "pause menu", "game menu", "start menu", "options menu", "settings menu", "build menu", "buy menu",
    # moves, not the counter
    "counter attack", "counter attacks", "counter attacking", "counter push", "counter strafe",
    # the recogniser's "my pin" ("Check my bin.", "Throw a smoke on my bin", "try again at my bin") and "nice shot"
    "my bin", "nice shop", "good shop",
]


def conflicts(old, new_objects, new_ignore):
    """What the new phrases meet in v15: the rule word lists their tokens are in, the direction / qualifier / zone words, and the
    v15 phrases they overlap (the longest phrase wins). Lines of text, for the record (validate() refuses real clashes)."""
    owner = {}
    for o in old["objects"]:
        for w in o["words"]:
            owner[w] = "object " + o["id"]
    for q in old["qualifiers"]:
        for w in q["words"]:
            owner[w] = "qualifier " + q["id"]
    for t in old["named"]:
        owner[t["phrase"]] = "named " + t["object"] + "/" + t["qualifier"]
    for z in old["zones"]:
        for w in z["words"] + z.get("words_end", []):
            owner[w] = "zone " + z["id"]
    for p in old["ignore"]:
        owner[p] = "ignore"
    dirs = {w: d["id"] for d in old["directions"] for w in d["words"]}
    lists = {}
    for k, ws in old["words"].items():
        for w in ws:
            lists.setdefault(w, []).append(k)
    out = []
    mine = [(w, "object " + o["id"]) for o in new_objects for w in o["words"]] + [(p, "ignore") for p in new_ignore]
    for phrase, who in mine:
        toks = phrase.split(" ")
        notes = []
        for t in toks:
            if t in dirs:
                notes.append(f"{t!r} is a direction word ({dirs[t]})")
            if t in owner and t != phrase:
                notes.append(f"{t!r} is v15's {owner[t]}")
            if t in lists:
                notes.append(f"{t!r} in words.{', words.'.join(lists[t])}")
        for p, o in owner.items():      # a v15 phrase of several tokens that can run into this one (the longest wins)
            pt = p.split(" ")
            if len(pt) > 1 and (pt[0] == toks[-1] or pt[-1] == toks[0]):
                notes.append(f"runs into v15 phrase {p!r} ({o})")
        if notes:
            out.append(f"  {phrase!r} ({who}): " + "; ".join(dict.fromkeys(notes)))
    return out


def main():
    sys.path.insert(0, HERE)
    import locations as LOC
    loc = json.load(io.open(os.path.join(HERE, "locations_v68.json"), encoding="utf-8"))
    assert loc["version"] == 15, loc["version"]
    old = json.loads(json.dumps(loc))
    ids = [o["id"] for o in loc["objects"]]
    assert not any(o["id"] in ids for o in NEW_OBJECTS)
    # appended: the objects keep their places in the list (the C++ indexes them)
    loc["objects"] += [dict(o, words=list(o["words"]), qualifiers=list(o["qualifiers"])) for o in NEW_OBJECTS]
    loc["ignore"] += NEW_IGNORE
    loc["version"] = 16
    loc["_note"] += (" v16 (2026-11-11, round v70, make_places_v70.py): the city and its restaurant, twenty objects appended -- bank, "
                     "restaurant, cafe, shop, hotel, pharmacy, gas_station, parking, junction, traffic_light, crosswalk (the sides), "
                     "counter, kiosk, bench, bin, atm, parasol, menu, kitchen, drinks_machine (the bench, the bin and the parasol take "
                     "the colours); \"bank left\" and the verb's other phrases, \"bank the\" (the recogniser's \"bang the door\"), "
                     "\"river bank\", the game's menus and \"counter attack\" are ignore phrases; no bare \"store\" (a farm verb), no "
                     "\"market\" (the recogniser's \"marker\"), no \"car park\" (\"the car\\npark at the pin\"); for the v70 bots "
                     "(COOP_TAG v70) or COOP_PLACES=locations_v70.json.")
    errs = LOC.validate(loc)
    if errs:
        sys.exit("v16 refused:\n  " + "\n  ".join(errs))
    path = os.path.join(HERE, "locations_v70.json")
    json.dump(loc, io.open(path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    LOC.load_vocab(path)                 # loads as the bot loads it
    n_words = sum(len(o["words"]) for o in NEW_OBJECTS)
    print(f"{path}: version 16, {len(loc['objects'])} objects ({len(NEW_OBJECTS)} new, {n_words} phrases), "
          f"{len(loc['ignore'])} ignore phrases ({len(NEW_IGNORE)} new), {len(loc['named'])} named phrases (unchanged)")
    for o in NEW_OBJECTS:
        print(f"  {o['id']:<15} {o['qualifiers'] and '/'.join(o['qualifiers']) or '-':<29} {', '.join(o['words'])}")
    print("what the new phrases meet in v15 (validate() found no clash):")
    print("\n".join(conflicts(old, NEW_OBJECTS, NEW_IGNORE)))


if __name__ == "__main__":
    main()
