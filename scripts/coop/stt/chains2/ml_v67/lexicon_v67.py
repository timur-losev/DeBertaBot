"""Round v67's lexicon: how the player names every object of vocabulary v12 in English, Russian and Spanish, with the forms
the frames' slots need (FRAMES.md), and every qualifier as an agreeing adjective. The English word is what the decoder
writes (the matcher knows it); a Russian or Spanish word maps to the English word it is said for (коробка -> "box",
ящик -> "crate": both the object crate).

    python lexicon_v67.py      prints every object's forms with a qualifier, for a look
"""
import random

# Russian nouns: (nom, acc, gen, dat, ins, prep, gender m/f/n/p, English word)
RU = {
    "door": [("дверь", "дверь", "двери", "двери", "дверью", "двери", "f", "door"), ("вход", "вход", "входа", "входу", "входом", "входе", "m", "entrance")],
    "window": [("окно", "окно", "окна", "окну", "окном", "окне", "n", "window"), ("стекло", "стекло", "стекла", "стеклу", "стеклом", "стекле", "n", "glass")],
    "stairs": [("лестница", "лестницу", "лестницы", "лестнице", "лестницей", "лестнице", "f", "stairs"),
               ("ступеньки", "ступеньки", "ступенек", "ступенькам", "ступеньками", "ступеньках", "p", "stairs")],
    "chair": [("стул", "стул", "стула", "стулу", "стулом", "стуле", "m", "chair"), ("кресло", "кресло", "кресла", "креслу", "креслом", "кресле", "n", "chair")],
    "sofa": [("диван", "диван", "дивана", "дивану", "диваном", "диване", "m", "sofa")],
    "table": [("стол", "стол", "стола", "столу", "столом", "столе", "m", "table"), ("столик", "столик", "столика", "столику", "столиком", "столике", "m", "table")],
    "car": [("машина", "машину", "машины", "машине", "машиной", "машине", "f", "car"), ("тачка", "тачку", "тачки", "тачке", "тачкой", "тачке", "f", "car"),
            ("джип", "джип", "джипа", "джипу", "джипом", "джипе", "m", "jeep"), ("грузовик", "грузовик", "грузовика", "грузовику", "грузовиком", "грузовике", "m", "truck")],
    "ammo": [("патроны", "патроны", "патронов", "патронам", "патронами", "патронах", "p", "ammo"),
             ("ящик с патронами", "ящик с патронами", "ящика с патронами", "ящику с патронами", "ящиком с патронами", "ящике с патронами", "m", "ammo box")],
    "weapon": [("оружие", "оружие", "оружия", "оружию", "оружием", "оружии", "n", "weapon")],
    "health": [("аптечка", "аптечку", "аптечки", "аптечке", "аптечкой", "аптечке", "f", "medkit")],
    "field": [("поле", "поле", "поля", "полю", "полем", "поле", "n", "field")],
    "bed": [("грядка", "грядку", "грядки", "грядке", "грядкой", "грядке", "f", "garden bed")],
    "greenhouse": [("теплица", "теплицу", "теплицы", "теплице", "теплицей", "теплице", "f", "greenhouse")],
    "barn": [("сарай", "сарай", "сарая", "сараю", "сараем", "сарае", "m", "barn"), ("амбар", "амбар", "амбара", "амбару", "амбаром", "амбаре", "m", "barn")],
    "coop": [("курятник", "курятник", "курятника", "курятнику", "курятником", "курятнике", "m", "chicken coop")],
    "beehive": [("улей", "улей", "улья", "улью", "ульем", "улье", "m", "beehive")],
    "well": [("колодец", "колодец", "колодца", "колодцу", "колодцем", "колодце", "m", "water well")],
    "fence": [("забор", "забор", "забора", "забору", "забором", "заборе", "m", "fence"), ("ограда", "ограду", "ограды", "ограде", "оградой", "ограде", "f", "fence")],
    "tree": [("дерево", "дерево", "дерева", "дереву", "деревом", "дереве", "n", "tree")],
    "crate": [("ящик", "ящик", "ящика", "ящику", "ящиком", "ящике", "m", "crate"), ("коробка", "коробку", "коробки", "коробке", "коробкой", "коробке", "f", "box"),
              ("контейнер", "контейнер", "контейнера", "контейнеру", "контейнером", "контейнере", "m", "container")],
    "foundation": [("фундамент", "фундамент", "фундамента", "фундаменту", "фундаментом", "фундаменте", "m", "foundation")],
    "teleport": [("телепорт", "телепорт", "телепорта", "телепорту", "телепортом", "телепорте", "m", "teleport"),
                 ("портал", "портал", "портала", "порталу", "порталом", "портале", "m", "portal")],
    "spool": [("катушка", "катушку", "катушки", "катушке", "катушкой", "катушке", "f", "spool"), ("бобина", "бобину", "бобины", "бобине", "бобиной", "бобине", "f", "spool")],
}
CASES = ("nom", "acc", "gen", "dat", "ins", "prep")

# Spanish nouns: (noun, gender m/f, plural?, English word)
ES = {
    "door": [("puerta", "f", False, "door")],
    "window": [("ventana", "f", False, "window"), ("cristal", "m", False, "glass")],
    "stairs": [("escalera", "f", False, "stairs"), ("escaleras", "f", True, "stairs")],
    "chair": [("silla", "f", False, "chair")],
    "sofa": [("sofá", "m", False, "sofa")],
    "table": [("mesa", "f", False, "table")],
    "car": [("coche", "m", False, "car"), ("carro", "m", False, "car"), ("camioneta", "f", False, "truck")],
    "ammo": [("munición", "f", False, "ammo")],
    "weapon": [("caja de armas", "f", False, "weapon crate")],
    "health": [("botiquín", "m", False, "medkit")],
    "field": [("campo", "m", False, "field")],
    "bed": [("huerto", "m", False, "garden bed"), ("bancal", "m", False, "garden bed")],
    "greenhouse": [("invernadero", "m", False, "greenhouse")],
    "barn": [("granero", "m", False, "barn"), ("cobertizo", "m", False, "shed")],
    "coop": [("gallinero", "m", False, "chicken coop")],
    "beehive": [("colmena", "f", False, "beehive")],
    "well": [("pozo", "m", False, "water well")],
    "fence": [("valla", "f", False, "fence"), ("cerca", "f", False, "fence")],
    "tree": [("árbol", "m", False, "tree")],
    "crate": [("caja", "f", False, "box"), ("cajón", "m", False, "crate")],
    "foundation": [("cimientos", "m", True, "foundation")],
    "teleport": [("teletransporte", "m", False, "teleport"), ("portal", "m", False, "portal")],
    "spool": [("bobina", "f", False, "spool"), ("carrete", "m", False, "spool")],
}

# qualifiers: English word, Russian adjective (stem, type), Spanish (m, f) after the noun
QUAL = {
    "blue": ("blue", ("син", "soft"), ("azul", "azul")),
    "red": ("red", ("красн", "hard"), ("rojo", "roja")),
    "yellow": ("yellow", ("жёлт", "hard"), ("amarillo", "amarilla")),
    "white": ("white", ("бел", "hard"), ("blanco", "blanca")),
    "brown": ("brown", ("коричнев", "hard"), ("marrón", "marrón")),
    "big": ("big", ("больш", "stressed"), ("grande", "grande")),
    "small": ("small", ("маленьк", "velar"), ("pequeño", "pequeña")),
    "cardboard": ("cardboard", ("картонн", "hard"), ("de cartón", "de cartón")),
    "north": ("north", ("северн", "hard"), ("del norte", "del norte")),
    "south": ("south", ("южн", "hard"), ("del sur", "del sur")),
    "west": ("west", ("западн", "hard"), ("del oeste", "del oeste")),
    "east": ("east", ("восточн", "hard"), ("del este", "del este")),
    "main": ("main", ("главн", "hard"), ("principal", "principal")),
}
# the qualifiers each object takes (vocabulary v12)
OBJ_QUALS = {"door": ["main", "north", "south", "west", "east"], "table": ["blue", "red", "yellow", "white", "brown"],
             "stairs": ["blue", "red", "yellow", "white", "brown"], "crate": ["big", "small", "cardboard"],
             "field": ["north", "south", "west", "east"], "greenhouse": ["north", "south", "west", "east"],
             "barn": ["north", "south", "west", "east"], "fence": ["north", "south", "west", "east"]}

# adjective endings: type -> gender -> case
_ADJ = {
    "hard": {"m": ("ый", "ый", "ого", "ому", "ым", "ом"), "f": ("ая", "ую", "ой", "ой", "ой", "ой"),
             "n": ("ое", "ое", "ого", "ому", "ым", "ом"), "p": ("ые", "ые", "ых", "ым", "ыми", "ых")},
    "stressed": {"m": ("ой", "ой", "ого", "ому", "им", "ом"), "f": ("ая", "ую", "ой", "ой", "ой", "ой"),
                 "n": ("ое", "ое", "ого", "ому", "им", "ом"), "p": ("ие", "ие", "их", "им", "ими", "их")},
    "velar": {"m": ("ий", "ий", "ого", "ому", "им", "ом"), "f": ("ая", "ую", "ой", "ой", "ой", "ой"),
              "n": ("ое", "ое", "ого", "ому", "им", "ом"), "p": ("ие", "ие", "их", "им", "ими", "их")},
    "soft": {"m": ("ий", "ий", "его", "ему", "им", "ем"), "f": ("яя", "юю", "ей", "ей", "ей", "ей"),
             "n": ("ее", "ее", "его", "ему", "им", "ем"), "p": ("ие", "ие", "их", "им", "ими", "их")},
}
# Russian pronouns for a thing named before: gender -> case -> (bare, after a preposition)
RU_PRON = {
    "m": {"nom": ("он", "он"), "acc": ("его", "него"), "gen": ("его", "него"), "dat": ("ему", "нему"), "ins": ("им", "ним"), "prep": ("нём", "нём")},
    "n": {"nom": ("оно", "оно"), "acc": ("его", "него"), "gen": ("его", "него"), "dat": ("ему", "нему"), "ins": ("им", "ним"), "prep": ("нём", "нём")},
    "f": {"nom": ("она", "она"), "acc": ("её", "неё"), "gen": ("её", "неё"), "dat": ("ей", "ней"), "ins": ("ей", "ней"), "prep": ("ней", "ней")},
    "p": {"nom": ("они", "они"), "acc": ("их", "них"), "gen": ("их", "них"), "dat": ("им", "ним"), "ins": ("ими", "ними"), "prep": ("них", "них")},
}
RU_PREPS = {"на", "в", "во", "к", "ко", "за", "через", "у", "с", "со", "по", "от", "до", "над", "под", "перед", "около", "возле", "мимо",
            "о", "об", "при", "из", "рядом", "вокруг", "между", "сквозь", "внутрь"}


def ru_adj(qual, gender, case):
    stem, kind = QUAL[qual][1]
    return stem + _ADJ[kind][gender][CASES.index(case)]


def es_plural(adj, plural):
    """A Spanish adjective after a plural noun: rojas, azules, marrones; «de cartón», «del norte» stay."""
    if not plural or adj.startswith("de"):
        return adj
    if adj[-1] in "aeiou":
        return adj + "s"
    return {"marrón": "marrones"}.get(adj, adj + "es")


def es_article(gender, plural):
    return {("m", False): "el", ("f", False): "la", ("m", True): "los", ("f", True): "las"}[(gender, plural)]


class Thing:
    """One way to name one object: its forms in the three languages (filled for one qualifier or none)."""

    def __init__(self, obj, qual, ru, es, en_word):
        self.obj, self.qual = obj, qual
        q_en = QUAL[qual][0] + " " if qual else ""
        self.en_word = en_word
        self.en = f"the {q_en}{en_word}"
        nom, acc, gen, dat, ins, prep, g, ru_en = ru
        self.ru_gender = g
        forms = dict(zip(CASES, (nom, acc, gen, dat, ins, prep)))
        # a qualifier agrees with the head noun (the first word of «ящик с патронами»)
        self.ru = {c: (ru_adj(qual, g, c) + " " if qual else "") + forms[c] for c in CASES}
        noun, eg, plural, es_en = es
        art = es_article(eg, plural)
        adj = (" " + es_plural(QUAL[qual][2][0] if eg == "m" else QUAL[qual][2][1], plural)) if qual else ""
        base = f"{noun}{adj}"
        self.es = {"T": f"{art} {base}",
                   "T:a": ("al " + base) if art == "el" else f"a {art} {base}",
                   "T:de": ("del " + base) if art == "el" else f"de {art} {base}"}
        self.es_gender, self.es_plural = eg, plural

    def ru_slot(self, case, pronoun=False, after_prep=False):
        if pronoun:
            return RU_PRON[self.ru_gender][case][1 if after_prep else 0]
        return self.ru[case]

    def es_slot(self, form, pronoun=False):
        if not pronoun:
            return self.es[form]
        p = {("m", False): "él", ("f", False): "ella", ("m", True): "ellos", ("f", True): "ellas"}[(self.es_gender, self.es_plural)]
        return {"T": None, "T:a": f"a {p}", "T:de": f"de {p}"}[form]


def things(obj, rng=None, qual="any"):
    """Every way to name obj (each Russian and Spanish noun, the English word each stands for), for one qualifier: qual
    "any" draws one of the object's qualifiers or none, None gives none, a qualifier id gives that one."""
    out = []
    quals = OBJ_QUALS.get(obj, [])
    for ru in RU[obj]:
        for es in ES[obj]:
            q = qual
            if q == "any":
                q = (rng or random).choice(quals + [None, None]) if quals else None
            # the English word: the Russian noun's (коробка -> box, ящик -> crate), or the Spanish one's when the
            # Russian is the object's first word
            out.append(Thing(obj, q, ru, es, ru[7]))
    return out


def thing(obj, rng, qual="any"):
    """One way to name obj, drawn; the English word follows the Russian noun drawn (the Spanish noun drawn on its own)."""
    ru = rng.choice(RU[obj])
    es = rng.choice(ES[obj])
    quals = OBJ_QUALS.get(obj, [])
    q = rng.choice(quals + [None, None]) if qual == "any" and quals else (None if qual == "any" else qual)
    return Thing(obj, q, ru, es, ru[7]), Thing(obj, q, ru, es, es[3])


OBJECTS = list(RU)
assert set(RU) == set(ES), set(RU) ^ set(ES)


if __name__ == "__main__":
    r = random.Random(1)
    for obj in OBJECTS:
        for q in [None] + OBJ_QUALS.get(obj, [])[:1]:
            t = thing(obj, r, q)[0]
            print(f"{obj:10s} {str(q):6s} en {t.en!r:28s} ru acc {t.ru['acc']!r:28s} ins {t.ru['ins']!r:30s} "
                  f"es {t.es['T']!r} / {t.es['T:a']!r}")
