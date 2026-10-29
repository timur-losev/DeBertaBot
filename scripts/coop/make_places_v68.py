"""The place vocabulary v14 (round v68, the owner 2026-10-28): "почему он называет кровать грядкой" and "ко всем
определителям добавить камень. Нужно будет на камень залезть".

v13 (locations_v67.json) had one object "bed" for the farm's garden bed (bot v60): a marker set to "bed" on a bed was "a
garden bed", «грядка». v14:
  bed         a bed to sleep on: bed, bunk, cot (colours, as a table: "the yellow bed")
  garden_bed  the farm's garden bed: garden bed, flower bed, vegetable bed, raised bed, plot, planter (the sides, as v13's bed)
  rock        rock, stone, boulder (big, small): a thing to climb onto, hide behind, go to
The decoder already writes «кровать» "bed", «грядка» "garden bed", «камень» "stone"/"rock", «валун» "boulder", «cama» "bed",
«bancal» "garden bed", «roca» / «piedra» "rock" / "stone" (deployed chain v67s, 2026-10-28): no training. The classifier
does not learn place names. The longest phrase wins, so "garden bed" is garden_bed and a lone "bed" the bed.

v15 (2026-10-29): the farmer's words since bot v60 call the garden bed a bed, and the decoder learnt them so («посади морковку
на северной грядке» -> "plant carrots in the north bed", «вскопай грядки» -> "hoe the beds"): with v14 those went to the yellow
bed. A bed has no sides, so "the north bed" (each side's words, one bed or several) is a named phrase of the garden bed on
that side; a garden order on a bed is on the garden bed (world.garden_record, a rule of the planner).

The vocabulary goes into a bot's intent_config.json by `COOP_PLACES=locations_v68.json python export_cpp.py BOT --config-only`
(locations.vocab_file), and the place and world tests are made again with the same variable.

    python make_places_v68.py
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    loc = json.load(io.open(os.path.join(HERE, "locations_v67.json"), encoding="utf-8"))
    assert loc["version"] == 13, loc["version"]
    ids = [o["id"] for o in loc["objects"]]
    bed = loc["objects"][ids.index("bed")]
    garden_words = [w for w in bed["words"] if w not in ("bed", "beds")] + ["veggie bed", "veggie beds", "vegetable beds", "planting bed",
                                                                          "planting beds"]
    bed["words"] = ["bed", "beds", "bunk", "bunks", "bunk bed", "bunk beds", "cot", "cots"]
    garden = {"id": "garden_bed", "words": garden_words, "qualifiers": list(bed["qualifiers"])}
    bed["qualifiers"] = ["blue", "red", "yellow", "white", "brown"]
    rock = {"id": "rock", "words": ["rock", "rocks", "stone", "stones", "boulder", "boulders"], "qualifiers": ["big", "small"]}
    # appended: the objects keep their places in the list (the C++ indexes them)
    loc["objects"] += [garden, rock]
    # v15: "the north bed" is the garden bed on the north side (a bed to sleep on has no sides)
    sides = [q for q in loc["qualifiers"] if q["id"] in garden["qualifiers"]]
    named = [{"phrase": f"{w} {b}", "object": "garden_bed", "qualifier": q["id"]} for q in sides for w in q["words"] for b in ("bed", "beds")]
    loc["named"] += named
    loc["version"] = 15
    loc["_note"] += (" v14 (2026-10-28, make_places_v68.py): \"bed\" is a bed to sleep on (bed, bunk, cot; colours), the farm's garden "
                     "bed is \"garden_bed\" (garden bed, flower bed, plot, planter...; sides), and \"rock\" (rock, stone, boulder; big, "
                     "small) is new; v15 (2026-10-29): \"the north bed\" and the other sides are the garden bed there (named phrases); for the "
                     "v67 bots with COOP_PLACES=locations_v68.json.")
    path = os.path.join(HERE, "locations_v68.json")
    json.dump(loc, io.open(path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"{path}: version 15, {len(loc['objects'])} objects; bed {bed['words']}; garden_bed {garden['words']}; rock {rock['words']}; "
          f"{len(named)} named phrases of the garden bed: {', '.join(n['phrase'] for n in named[:4])}, ...")


if __name__ == "__main__":
    main()
