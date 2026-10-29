"""Round v68's lexicon: round v67's (lexicon_v67.py) with the place vocabulary v15 (locations_v68.json, make_places_v68.py).

The owner (2026-10-28): «почему он называет кровать грядкой» and «ко всем определителям добавить камень. Нужно будет на камень
залезть»; 2026-10-29, on adding the new things to the generator for the next training round: «ок я согласен с улучшением».

  bed         a bed to sleep on: кровать, койка / cama, litera ("bed", "bunk"); colours, as a table ("the yellow bed")
  garden_bed  the farm's garden bed, v67's "bed": грядка / bancal, huerto ("garden bed"); the sides
  rock        камень, валун, булыжник / roca, piedra, peñasco ("rock", "boulder", "stone"); big, small

Everything else is v67's (the objects, the qualifiers, the adjective endings, the pronouns, Thing, things, thing).

    python lexicon_v68.py      prints every object's forms with a qualifier, for a look
"""
import os, random, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml_v67"))
import lexicon_v67 as L67
from lexicon_v67 import CASES, QUAL, RU_PRON, RU_PREPS, Thing, ru_adj, es_plural, es_article  # noqa: F401  (the v67 parts kept)

RU = dict(L67.RU)
ES = dict(L67.ES)
OBJ_QUALS = dict(L67.OBJ_QUALS)

# v67's "bed" was the garden bed: it is "garden_bed" now, and "bed" a bed to sleep on
RU["garden_bed"] = RU.pop("bed")
ES["garden_bed"] = ES.pop("bed")
RU["bed"] = [("кровать", "кровать", "кровати", "кровати", "кроватью", "кровати", "f", "bed"),
             ("койка", "койку", "койки", "койке", "койкой", "койке", "f", "bunk")]
ES["bed"] = [("cama", "f", False, "bed"), ("litera", "f", False, "bunk")]
RU["rock"] = [("камень", "камень", "камня", "камню", "камнем", "камне", "m", "rock"),
              ("валун", "валун", "валуна", "валуну", "валуном", "валуне", "m", "boulder"),
              ("булыжник", "булыжник", "булыжника", "булыжнику", "булыжником", "булыжнике", "m", "stone")]
ES["rock"] = [("roca", "f", False, "rock"), ("piedra", "f", False, "stone"), ("peñasco", "m", False, "boulder")]
# the qualifiers each object takes (vocabulary v15)
OBJ_QUALS["bed"] = ["blue", "red", "yellow", "white", "brown"]
OBJ_QUALS["garden_bed"] = ["north", "south", "west", "east"]
OBJ_QUALS["rock"] = ["big", "small"]

OBJECTS = list(RU)
NEW = ("bed", "garden_bed", "rock")     # new or changed since v67 (the check reads these first)
assert set(RU) == set(ES), set(RU) ^ set(ES)


def things(obj, rng=None, qual="any"):
    """lexicon_v67.things on this lexicon."""
    out = []
    quals = OBJ_QUALS.get(obj, [])
    for ru in RU[obj]:
        for es in ES[obj]:
            q = qual
            if q == "any":
                q = (rng or random).choice(quals + [None, None]) if quals else None
            out.append(Thing(obj, q, ru, es, ru[7]))
    return out


def thing(obj, rng, qual="any"):
    """lexicon_v67.thing on this lexicon: one way to name obj, drawn; the English word of each language's noun."""
    ru = rng.choice(RU[obj])
    es = rng.choice(ES[obj])
    quals = OBJ_QUALS.get(obj, [])
    q = rng.choice(quals + [None, None]) if qual == "any" and quals else (None if qual == "any" else qual)
    return Thing(obj, q, ru, es, ru[7]), Thing(obj, q, ru, es, es[3])


if __name__ == "__main__":
    r = random.Random(1)
    for obj in NEW + tuple(o for o in OBJECTS if o not in NEW):
        for q in [None] + OBJ_QUALS.get(obj, [])[:1]:
            t_ru, t_es = thing(obj, r, q)
            print(f"{obj:10s} {str(q):6s} en {t_ru.en!r:28s} ru acc {t_ru.ru['acc']!r:28s} ins {t_ru.ru['ins']!r:30s} "
                  f"es {t_es.es['T']!r} / {t_es.es['T:a']!r} ({t_es.en!r})")
