"""Round v65 of the chains study (2026-10-25): decoder v65, given the scene. The owner: "держать в голове контекст субъекта
и объекта, с которым он сейчас имеет дело"; "если нет рядом машины, я говорю запрыгни, значит речь идёт не про машину";
"Хотелось бы решения на уровне нейросетей"; "запускай и померяем точность". Plan: chains2/ml_v65/PLAN_v65.md.

What changes against v64 (chains8_v64.py, its rows kept):
  - a "scene:" line may come before "now:" (after the older lines), made by the game:
        scene: holding a cardboard box; standing on a cable spool; no car near; last thing: cable spool, 0 m
    parts in that order, each but the car's optional; the car's is "no car near" or "a car N m away" (N up to 25; 0: the
    bot is in it). The same words under different scenes give different English:
        «запрыгни» / "jump in" / «súbete»   a car near: "get in the car" (English "jump in" as it is); none: "jump up on it"
        «слезь» / "get down" / «bájate»     standing on a thing: "climb down"; on the floor "get down" is cover
        «садись»                            a car near: "get in the car"; none: "sit down"
        «ещё раз» after jumping on a thing and getting off: "jump on it again"
    A pronoun stays a pronoun ("pick it up"): the game's memory (the thing in hand, the last thing) says which thing;
  - SCENE rows from the templates below (ru, en, es); the English answers are words bot v64 reads as meant (probed);
  - a scene that changes nothing is added to SCENE_SHARE of v64's rows (their answers stay), so that a scene alone is no
    reason to rewrite a line; the parts that could change a row's meaning are left out of its scene;
  - the hand rows (chains2/ml_v65/hand_v65.json), each HAND_COPIES times, half of them with a scene that fits;
  - rows whose line and scene are those of an item of the held-out scene test (chains2/ml_v65/scene_test.json, written
    blind) are dropped: that test is never trained on;
  - the system turn says what the scene is (SYSTEM_V65); plain Qwen3-1.7B with a new LoRA, v64's recipe (r16, 3 epochs).

    python chains9_v65.py data       the rows, counted, with samples
    python chains9_v65.py train      -> models/coop-qwen3-qlora-chains9-v65/pieces10v65_final_seed0; answers on every test set
    python chains9_v65.py gguf | export
"""
import io, json, os, random, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chains8_v64 as P8            # v64's rows (and through it v63's, v62's)
from chains8_v64 import P, C, C2, Q, torch

VARIANT = "pieces10v65_final"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = P.ROWS_OF
ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains9-v65")
_adapter64 = C2.adapter_dir
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}") if variant == VARIANT else _adapter64(variant, seed)
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains9_65_{variant}_s{seed}.json")
ML65 = os.path.join(C2.CH2, "ml_v65")
SYSTEM_V65 = P.SYSTEM_V62 + (" A line \"scene:\" may come before \"now\": what the bot is holding, what it is standing on, how far "
                             "the nearest car is (0 m: the bot is in it) and the last thing it dealt with. Read the player's words "
                             "in that scene; an English line is written back as it is unless the scene changes what it orders.")
SCENE_SHARE = 0.45           # of v64's rows, given a scene that changes nothing
HAND_COPIES = 8
PER_TEMPLATE = {"ru": 16, "es": 12, "en": 10}   # rows drawn per template and scene case

# things as the game names them in the scene, and how the player names them
THINGS = {
    "box": {"scene": ["box", "cardboard box", "big box", "small box", "cardboard box", "box"], "en": "box",
            "ru": ("коробку", "коробки", "f"), "es": ("la caja", "de la caja", "f")},
    "crate": {"scene": ["crate", "wooden crate", "crate"], "en": "crate", "ru": ("ящик", "ящика", "m"), "es": ("el cajón", "del cajón", "m")},
    "spool": {"scene": ["spool", "cable spool", "big spool", "small spool", "cable spool"], "en": "spool",
              "ru": ("катушку", "катушки", "f"), "es": ("la bobina", "de la bobina", "f")},
}
RU_IT = {"f": ("её", "неё", "эту"), "m": ("его", "него", "этот")}
ES_IT = {"f": "la", "m": "lo"}

# prefixes and suffixes as spoken, and what they leave in the English
PRE = {"ru": [("", ""), ("", ""), ("", ""), ("давай ", ""), ("ну ", ""), ("теперь ", "now "), ("а теперь ", "now "), ("так, ", ""),
              ("брат, ", ""), ("просто ", "just "), ("да ", "")],
       "es": [("", ""), ("", ""), ("", ""), ("venga, ", ""), ("ahora ", "now "), ("oye, ", ""), ("vale, ", ""), ("solo ", "just ")],
       "en": [("", ""), ("", ""), ("", ""), ("now ", "now "), ("okay ", "okay "), ("come on, ", "come on, "), ("just ", "just ")]}
SUF = {"ru": [("", ""), ("", ""), ("", ""), (", брат", " bro"), (" давай", ""), (" быстро", " quick"), (" пожалуйста", "")],
       "es": [("", ""), ("", ""), ("", ""), (", tío", " bro"), (" ya", ""), (" rápido", " quick"), (", por favor", "")],
       "en": [("", ""), ("", ""), ("", ""), (" bro", " bro"), (" now", " now"), (" quick", " quick")]}


def scene_text(holding=None, standing=None, car=None, last=None):
    """The game's scene line (without "scene: "): parts in order; car None = "no car near"."""
    parts = []
    if holding:
        parts.append(f"holding a {holding}")
    if standing:
        parts.append(f"standing on a {standing}")
    parts.append("no car near" if car is None else f"a car {car} m away")
    if last:
        parts.append(f"last thing: {last[0]}, {last[1]} m")
    return "; ".join(parts)


def scene_parts(scene):
    """The world's "scene" as the game sends it (coop_cli SceneFromJson) for a scene line: scene_text(**) of it is the line."""
    out = {"holding": None, "standing_on": None, "car_m": None, "last": None}
    for p in scene.split("; "):
        if p.startswith("holding a "):
            out["holding"] = p[len("holding a "):]
        elif p.startswith("standing on a "):
            out["standing_on"] = p[len("standing on a "):]
        elif p.startswith("a car "):
            out["car_m"] = int(p.split()[2])
        elif p.startswith("last thing: "):
            name, m = p[len("last thing: "):].rsplit(", ", 1)
            out["last"] = {"thing": name, "m": int(m.split()[0])}
    assert scene_text(out["holding"], out["standing_on"], out["car_m"], (out["last"]["thing"], out["last"]["m"]) if out["last"] else None) == scene
    return out


def turn(before, scene, line):
    return "\n".join([f"before: {b}" for b in before] + ([f"scene: {scene}"] if scene else []) + [f"now: {line}"])


def thing(rng, kind=None):
    k = kind or rng.choice(list(THINGS))
    return k, rng.choice(THINGS[k]["scene"])


def carried(rng):
    """A thing the bot can hold: boxes and crates (spools are pushed and rolled)."""
    return thing(rng, rng.choice(["box", "box", "crate"]))[1]


def car_near(rng):
    return rng.choice([2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 18, 20, 24])


def car_any(rng):
    return car_near(rng) if rng.random() < 0.35 else None


# The scene cases. Each case: a function (rng) -> (scene kwargs, the thing named in the scene or None), and templates per
# language: (spoken line with {acc} {gen} {it} {on_it} of the thing, English answer with {en}). A template list is drawn
# from with prefixes and suffixes.
def sc_no_car_last(rng):
    k, name = thing(rng)
    return dict(car=None, last=(name, rng.choice([0, 1, 1, 2, 2, 3, 4, 5, 6, 8]))), k


def sc_no_car_nothing(rng):
    return dict(car=None, last=(thing(rng)[1], rng.choice([12, 15, 20, 30])) if rng.random() < 0.3 else None), None


def sc_car_near(rng):
    k, name = thing(rng)
    return dict(car=car_near(rng), last=(name, rng.choice([1, 2, 3, 5, 8])) if rng.random() < 0.6 else None), k


def sc_standing(rng):
    k, name = thing(rng)
    h = carried(rng) if rng.random() < 0.2 else None
    return dict(holding=h, standing=name, car=car_any(rng), last=(name, 0) if rng.random() < 0.85 else (thing(rng)[1], rng.choice([2, 4]))), k


def sc_floor(rng):
    k, name = thing(rng)
    return dict(car=car_any(rng), last=(name, rng.choice([0, 1, 2, 3, 6])) if rng.random() < 0.6 else None), k


def sc_in_car(rng):
    return dict(car=0, last=None), None


def sc_holding(rng):
    k, name = thing(rng, rng.choice(["box", "box", "crate"]))
    st = thing(rng)[1] if rng.random() < 0.15 else None
    return dict(holding=name, standing=st, car=car_any(rng), last=(name, 0)), k


def sc_last_not_holding(rng):
    k, name = thing(rng)
    return dict(car=car_any(rng), last=(name, rng.choice([1, 2, 2, 3, 4, 5, 7]))), k


CASES = [
    # jump-in words: a car near -> into the car
    ("jump_in_car", sc_car_near, {
        "ru": [("запрыгни", "get in the car"), ("запрыгивай", "get in the car"), ("залезай", "get in the car"),
               ("залезь", "get in the car"), ("прыгай внутрь", "get in the car"), ("садись", "get in the car"),
               ("запрыгни туда", "get in the car"), ("садись в машину", "get in the car"), ("запрыгни в машину", "get in the car")],
        "es": [("súbete", "get in the car"), ("sube", "get in the car"), ("monta", "get in the car"), ("súbete ahí", "get in the car"),
               ("métete", "get in the car"), ("sube al coche", "get in the car"), ("métete en el coche", "get in the car")],
        "en": [("jump in", "jump in"), ("hop in", "hop in"), ("get in", "get in the car"), ("climb in", "get in the car"),
               ("jump in there", "jump in there"), ("get in the car", "get in the car")]}),
    # jump-in words, no car: up on the thing it dealt with last
    ("jump_in_no_car", sc_no_car_last, {
        "ru": [("запрыгни", "jump up on it"), ("запрыгивай", "jump up on it"), ("залезай", "climb up on it"),
               ("залезь", "climb up on it"), ("запрыгни туда", "jump up on it"), ("прыгай наверх", "jump up on it"),
               ("запрыгни наверх", "jump up on it"), ("залезь наверх", "climb up on it"), ("садись", "sit down")],
        "es": [("súbete", "jump up on it"), ("sube", "climb up on it"), ("súbete ahí", "jump up on it"),
               ("súbete arriba", "jump up on it"), ("salta arriba", "jump up on it"), ("sube encima", "climb up on it")],
        "en": [("jump in", "jump up on it"), ("hop in", "jump up on it"), ("hop up", "jump up on it"), ("jump up", "jump up on it"),
               ("jump in there", "jump up on it")]}),
    ("jump_in_nothing", sc_no_car_nothing, {
        "ru": [("запрыгни", "jump up"), ("запрыгивай", "jump up"), ("залезай", "climb up"), ("прыгай наверх", "jump up"),
               ("запрыгни сюда", "jump up here"), ("садись", "sit down")],
        "es": [("súbete", "jump up"), ("sube", "climb up"), ("súbete aquí", "jump up here"), ("salta arriba", "jump up")],
        "en": [("jump in", "jump up"), ("hop in", "jump up"), ("hop up", "hop up"), ("jump in here", "jump up here")]}),
    # a thing named: a car near or not, it is that thing
    ("jump_on_named", lambda rng: (dict(car=car_any(rng) if rng.random() < 0.5 else car_near(rng),
                                        last=(thing(rng)[1], rng.choice([1, 3, 5])) if rng.random() < 0.5 else None), None), {
        "ru": [("запрыгни на {acc}", "jump on the {en}"), ("залезь на {acc}", "climb on the {en}"), ("на {acc} запрыгни", "jump on the {en}"),
               ("запрыгни на {acc} сверху", "jump on top of the {en}"), ("перепрыгни {acc}", "jump over the {en}"),
               ("запрыгни на {this} {acc}", "jump on this {en}")],
        "es": [("súbete a {acc}", "jump on the {en}"), ("sube a {acc}", "climb on the {en}"), ("salta encima de {acc}", "jump on top of the {en}"),
               ("salta por encima de {acc}", "jump over the {en}")],
        "en": [("jump on the {en}", "jump on the {en}"), ("hop on the {en}", "hop on the {en}"), ("climb on the {en}", "climb on the {en}"),
               ("jump over the {en}", "jump over the {en}")]}),
    # the car named: it is the car, near or not (the game says when there is none)
    ("car_named", lambda rng: (dict(car=car_any(rng), last=(thing(rng)[1], 2) if rng.random() < 0.4 else None), None), {
        "ru": [("садись в машину", "get in the car"), ("запрыгни в машину", "get in the car"), ("залезай в машину", "get in the car")],
        "es": [("sube al coche", "get in the car"), ("súbete al coche", "get in the car"), ("métete en el coche", "get in the car")],
        "en": [("get in the car", "get in the car"), ("jump in the car", "jump in the car"), ("hop in the car", "hop in the car")]}),
    # getting down standing on a thing: off it
    ("down_standing", sc_standing, {
        "ru": [("слезь", "climb down"), ("слезай", "climb down"), ("слезь оттуда", "climb down from there"), ("спрыгни", "jump down"),
               ("спрыгивай", "jump down"), ("спускайся", "climb down"), ("давай вниз", "jump down"), ("вниз", "jump down"),
               ("спрыгни вниз", "jump down"), ("слезь с {gen}", "climb down off the {en}"), ("спрыгни с {gen}", "jump off the {en}"),
               ("слезь с {on_it}", "climb down off it"), ("спрыгни с {on_it}", "jump off it"), ("спрыгни ко мне", "jump down to me"),
               ("спрыгни сюда", "jump down here"), ("слезь сюда", "climb down here"), ("сойди", "climb down")],
        "es": [("bájate", "climb down"), ("baja", "climb down"), ("bájate de ahí", "climb down from there"), ("salta abajo", "jump down"),
               ("bájate {gen}", "climb down off the {en}"), ("salta {gen}", "jump off the {en}"), ("baja aquí", "jump down here"),
               ("salta hacia mí", "jump down to me")],
        "en": [("get down", "climb down"), ("come down", "climb down"), ("get off", "climb down"), ("get off it", "jump off it"),
               ("get down from there", "get down from there"), ("come on down", "climb down"), ("hop down", "jump down"),
               ("get off the {en}", "get off the {en}"), ("jump down", "jump down"), ("climb down", "climb down")]}),
    # the same words on the floor: getting off words stay a jump down (the game says it is on the ground); cover words cover
    ("down_floor", sc_floor, {
        "ru": [("слезь", "climb down"), ("спрыгни", "jump down"), ("ложись", "get down"), ("пригнись", "crouch"),
               ("в укрытие", "take cover")],
        "es": [("bájate", "get down"), ("agáchate", "crouch"), ("a cubierto", "take cover"), ("cúbrete", "take cover")],
        "en": [("get down", "get down"), ("take cover", "take cover"), ("crouch", "crouch"), ("jump down", "jump down")]}),
    # in the car (0 m): out of it
    ("out_of_car", sc_in_car, {
        "ru": [("вылезай", "get out of the car"), ("выходи", "get out of the car"), ("вылезай из машины", "get out of the car"),
               ("выпрыгивай", "get out of the car")],
        "es": [("bájate", "get out of the car"), ("sal", "get out of the car"), ("sal del coche", "get out of the car"),
               ("bájate del coche", "get out of the car")],
        "en": [("get out", "get out"), ("hop out", "hop out"), ("get out of the car", "get out of the car")]}),
    # holding a thing
    ("holding", sc_holding, {
        "ru": [("брось {it}", "drop it"), ("брось", "drop it"), ("бросай", "drop it"), ("выбрось {it}", "throw it away"),
               ("поставь", "put it down"), ("поставь {it}", "put it down"), ("положи {it}", "put it down"),
               ("поставь {it} туда", "put it there"), ("поставь туда", "put it there"), ("неси {it}", "carry it"),
               ("неси дальше", "keep carrying it"), ("держи {it}", "keep holding it"), ("не бросай", "keep holding it"),
               ("отдай мне", "give it to me"), ("дай {it} мне", "give it to me"), ("подними {it}", "pick it up"),
               ("подними {it} над собой", "lift it up and hold it")],
        "es": [("suéltala", "drop it"), ("tírala", "throw it away"), ("déjala", "put it down"), ("déjala ahí", "put it there"),
               ("llévala", "carry it"), ("sigue llevándola", "keep carrying it"), ("no la sueltes", "keep holding it"),
               ("dámela", "give it to me"), ("levántala", "pick it up")],
        "en": [("drop it", "drop it"), ("put it down", "put it down"), ("put it there", "put it there"), ("throw it away", "throw it away"),
               ("give it to me", "give it to me"), ("keep holding it", "keep holding it"), ("carry it", "carry it")]}),
    # not holding: the last thing
    ("last_thing", sc_last_not_holding, {
        "ru": [("подними {it}", "pick it up"), ("возьми {it}", "pick it up"), ("бери {it}", "pick it up"), ("подбери {it}", "pick it up"),
               ("принеси {it}", "bring it to me"), ("принеси мне {it}", "bring it to me"), ("кати {it}", "roll it"),
               ("кати {it} обратно", "roll it back"), ("толкай {it}", "push it"), ("толкни {it}", "push it"),
               ("запрыгни на {on_it}", "jump on it"), ("перепрыгни {it}", "jump over it"), ("подними {it} снова", "pick it up again")],
        "es": [("recógela", "pick it up"), ("cógela", "pick it up"), ("levántala", "pick it up"), ("tráemela", "bring it to me"),
               ("hazla rodar", "roll it"), ("empújala", "push it"), ("súbete encima", "jump on it"), ("sáltala", "jump over it")],
        "en": [("pick it up", "pick it up"), ("bring it to me", "bring it to me"), ("roll it", "roll it"), ("push it", "push it"),
               ("jump on it", "jump on it"), ("jump over it", "jump over it")]}),
    # take vs bring, the thing named
    ("take_bring", lambda rng: (dict(holding=None, car=car_any(rng), last=(thing(rng)[1], rng.choice([1, 3, 6])) if rng.random() < 0.5 else None), None), {
        "ru": [("возьми {acc}", "pick up the {en}"), ("подними {acc}", "pick up the {en}"), ("бери {acc}", "pick up the {en}"),
               ("принеси {acc}", "bring me the {en}"), ("принеси мне {acc}", "bring me the {en}"), ("отнеси {acc} туда", "take the {en} over there"),
               ("неси {acc} сюда", "bring the {en} here"), ("возьми {acc} с собой", "bring the {en} with you")],
        "es": [("coge {acc}", "pick up the {en}"), ("recoge {acc}", "pick up the {en}"), ("tráeme {acc}", "bring me the {en}"),
               ("lleva {acc} allí", "take the {en} over there"), ("llévate {acc} contigo", "bring the {en} with you")],
        "en": [("pick up the {en}", "pick up the {en}"), ("take the {en}", "take the {en}"), ("bring me the {en}", "bring me the {en}"),
               ("take the {en} over there", "take the {en} over there")]}),
]
# "again" after jumping on a thing and getting off, after rolling or pushing it: the order once more, on it
AGAIN = {
    "ru": ([("Запрыгни на {acc}.", "Слезь."), ("Запрыгни на {acc}.", "Спрыгни."), ("Залезь на {acc}.", "Слезай.")],
           [("Кати {acc}.",), ("Толкни {acc}.",), ("Перепрыгни {acc}.",)],
           ["ещё раз", "давай ещё раз", "и снова", "снова"], ["ещё раз запрыгни", "снова запрыгни", "залезь обратно"]),
    "es": ([("Súbete a {acc}.", "Bájate."), ("Sube a {acc}.", "Baja.")],
           [("Haz rodar {acc}.",), ("Empuja {acc}.",), ("Salta por encima de {acc}.",)],
           ["otra vez", "de nuevo", "venga, otra vez"], ["otra vez súbete", "vuelve a subir"]),
}
AGAIN_EN = {"Кати": "roll it again", "Толкни": "push it again", "Перепрыгни": "jump over it again", "Haz rodar": "roll it again",
            "Empuja": "push it again", "Salta por encima": "jump over it again"}


def fill(tpl, kind, lang, rng):
    t = THINGS[kind or rng.choice(list(THINGS))]
    if lang == "ru":
        acc, gen, g = t["ru"]
        return tpl.format(acc=acc, gen=gen, it=RU_IT[g][0], on_it=RU_IT[g][1], this=RU_IT[g][2], en=t["en"]), t
    if lang == "es":
        acc, gen, g = t["es"]
        line = tpl.format(acc=acc, gen=gen, en=t["en"]).replace("de el ", "del ").replace("a el ", "al ")
        if g == "m":   # the pronoun stuck to the verb is masculine for el cajón
            line = re.sub(r"(\w)la\b", r"\1lo", line).replace("no la ", "no lo ")
        return line, t
    return tpl.format(en=t["en"]), t


def spoken_line(core, answer, lang, rng):
    """(the line as the decoder gets it, the English answer). English as v64's rows: the line as written, and written back
    as it is when the scene does not change it (answer None)."""
    (p, pe), (s, se) = rng.choice(PRE[lang]), rng.choice(SUF[lang])
    line = p + core + s
    if lang == "en":
        return line, line if answer is None else (pe + answer + se).strip()
    if rng.random() < 0.5:
        line = line[0].upper() + line[1:] + "."
    return P.spoken(line, rng), (pe + answer + se).strip()


def scene_rows(rng):
    rows, counts = [], {}
    for name, case, tpls in CASES:
        for lang, items in tpls.items():
            for tpl, ans in items:
                for _ in range(PER_TEMPLATE[lang]):
                    kw, kind = case(rng)
                    core, t = fill(tpl, kind, lang, rng)
                    line, answer = spoken_line(core, None if lang == "en" and ans == tpl else ans.format(en=t["en"]), lang, rng)
                    rows.append({"text": turn([], scene_text(**kw), line), "answer": answer, "case": name, "lang": lang})
                    counts[f"{name}/{lang}"] = counts.get(f"{name}/{lang}", 0) + 1
    for lang, (pairs, singles, nows, jump_nows) in AGAIN.items():
        for _ in range(PER_TEMPLATE[lang] * 6):
            kind = rng.choice(list(THINGS))
            if rng.random() < 0.6:
                before = [fill(b, kind, lang, rng)[0] for b in rng.choice(pairs)]
                answer = "jump on it again"
                kw = dict(car=None, last=(rng.choice(THINGS[kind]["scene"]), rng.choice([0, 1, 1, 2])))
                now = rng.choice(nows + jump_nows)
            else:
                b = rng.choice(singles)[0]
                before = [fill(b, kind, lang, rng)[0]]
                answer = next(v for k, v in AGAIN_EN.items() if b.startswith(k))
                kw = dict(car=car_any(rng), last=(rng.choice(THINGS[kind]["scene"]), rng.choice([0, 1, 2, 3])))
                now = rng.choice(nows)
            line = P.spoken(now[0].upper() + now[1:] + "." if rng.random() < 0.5 else now, rng)
            rows.append({"text": turn([P.spoken(b, rng) for b in before], scene_text(**kw), line), "answer": answer, "case": "again", "lang": lang})
            counts[f"again/{lang}"] = counts.get(f"again/{lang}", 0) + 1
    return rows, counts


# a scene that changes nothing, for v64's rows: parts left out where they could change the row
_GETIN = re.compile(r"\b(in|into|inside|aboard|board|mount|car|vehicle|ride|drive|seat|sit|hop|jump|climb|enter|get|out)\b", re.I)
_DOWN = re.compile(r"\b(down|off|out|get|come|climb|jump|hop|step|fall|leave|descend|lower|duck|cover|crouch|prone)\b", re.I)
_DOWN_SRC = re.compile(r"слез|спрыг|спуск|вниз|сойд|сойти|ложи|пригн|baj|abajo|suelo|agach|down|off", re.I)
_AGAIN = re.compile(r"\b(again|more|once)\b|ещё|еще|снова|опять|otra vez|de nuevo", re.I)


def neutral_scene(text, answer, rng):
    if _AGAIN.search(answer) or _AGAIN.search(text):
        return None
    now = text.rsplit("now: ", 1)[-1]
    car = car_near(rng) if (_GETIN.search(answer) or rng.random() < 0.3) else None
    holding = carried(rng) if rng.random() < 0.25 else None
    standing = thing(rng)[1] if rng.random() < 0.12 and not _DOWN.search(answer) and not _DOWN_SRC.search(now) else None
    if holding:
        last = (holding, 0)
    elif standing:
        last = (standing, 0)
    else:
        last = (thing(rng)[1], rng.choice([0, 1, 2, 3, 5, 8, 12])) if rng.random() < 0.55 else None
    return scene_text(holding=holding, standing=standing, car=car, last=last)


def with_scene(text, scene):
    head, sep, now = text.rpartition("now: ")
    assert sep, text[:80]
    return f"{head}scene: {scene}\n{sep}{now}"


def hand_scene(it, rng):
    en = " ".join(it["en"]).lower()
    k, name = thing(rng, "spool" if "spool" in en or "катушк" in it["text"].lower() else ("crate" if "crate" in en else "box"))
    if it["label"] == "JUMP" and re.search(r"\b(down|off)\b", en):
        return scene_text(standing=name, car=car_any(rng), last=(name, 0))
    if it["label"] == "JUMP":
        return scene_text(car=None, last=(name, rng.choice([1, 2, 3])))
    if it["label"] in ("ROLL", "PUSH"):
        return scene_text(car=car_any(rng), last=(name, rng.choice([1, 2])))
    if it["label"] == "DELIVER" and not it["before"]:
        return scene_text(holding=name if "carry" in en else None, car=car_any(rng), last=(name, 0 if "carry" in en else 3))
    if it["label"] == "COLLECT":
        held = bool(re.search(r"hold|carry|don't give", en))
        return scene_text(holding=name if held else None, car=car_any(rng), last=(name, 0 if held else 2))
    return scene_text(car=car_any(rng))


def test_keys():
    """(line, scene) of every held-out scene test item, normalised: those rows are dropped."""
    p = os.path.join(ML65, "scene_test.json")
    if not os.path.exists(p):
        return set()
    norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()   # noqa: E731
    return {(norm(it["text"]), it["scene"].strip().lower()) for it in P.jl(p)["items"]}


def training():
    rows, counts, split = P8.training()
    rng = random.Random(6501)
    n_scene = 0
    for r in rows:
        if rng.random() < SCENE_SHARE:
            s = neutral_scene(r["text"], r["answer"], rng)
            if s:
                r["text"] = with_scene(r["text"], s)
                n_scene += 1
    new, scounts = scene_rows(rng)
    hand = P.jl(ML65, "hand_v65.json")["items"]
    for it in hand:
        for copy in range(HAND_COPIES):
            text = P.spoken(it["text"], rng)
            scene = hand_scene(it, rng) if copy % 2 == 0 else None
            new.append({"text": turn([P.spoken(b, rng) for b in it["before"]], scene, text), "answer": "\n".join(it["en"]),
                        "case": "hand", "lang": it["lang"]})
    keys = test_keys()
    norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()   # noqa: E731
    def key(text):
        sc = re.search(r"^scene: (.*)$", text, re.M)
        return (norm(text.rsplit("now: ", 1)[-1]), sc.group(1).strip().lower() if sc else "")
    kept = [r for r in new if key(r["text"]) not in keys]
    counts.update({"v65": {"scene_rows": scounts, "hand": {"items": len(hand), "rows": len(hand) * HAND_COPIES},
                           "dropped_as_test": len(new) - len(kept), "v64_rows_given_a_scene": n_scene},
                   "v64_rows": len(rows), "v65_rows": len(kept)})
    return rows + [{"text": r["text"], "answer": r["answer"]} for r in kept], counts, split


def scene_answers(model, turns, path):
    """hand_v65 (trained on) and the held-out scene test, with their scenes: measure_v65.py scores them."""
    sys.path.insert(0, HERE)
    import measure_v65 as M
    out = {}
    for name, items in M.sets().items():
        todo = [it for it in items if it["lang"] != "en" or name != "owner65"]
        if todo:
            out[name] = dict(zip([it["id"] for it in todo], C.generate(model, turns, [M.turn_text(it) for it in todo], max_new=C2.MAX_NEW["pieces"])))
    json.dump({"decoder": "v65", "adapter": C2.adapter_dir(VARIANT, 0), "pred": out}, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("scene answers ->", path, flush=True)


def train(seed=0):
    t0 = time.time()
    rows, counts, split = training()
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=SYSTEM_V65, checkpoint=True)
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": SYSTEM_V65, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"chains9 {VARIANT} seed {seed}: {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    model.eval()
    scene_answers(model, turns, os.path.join(HERE, "measure_v65_answers_v65.json"))
    P8.test_answers(model, turns, os.path.join(HERE, f"chains9_65_test64_{VARIANT}_s{seed}.json"))
    C2.answers(model, turns, VARIANT, seed, extra)
    P.ml_answers(model, turns, os.path.join(HERE, f"chains9_65_ml_{VARIANT}_s{seed}.json"), extra)
    P8.P7.pairs_answers(model, turns, os.path.join(HERE, f"chains9_65_pairs_{VARIANT}_s{seed}.json"))


def gguf(seed=0):
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    sys.argv = [sys.argv[0], VARIANT, str(seed)]
    C2.SYSTEM["pieces"] = SYSTEM_V65
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v65", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS9_ROUTER", "coop-router-deberta-v3-small-v63"))
    base = E.test_rows

    def rows():
        """v64's test lines, and 40 lines with a scene (made as the scene rows are, another draw): the C++ turn with its
        scene line against the one the server was given."""
        out = base()
        made, _ = scene_rows(random.Random(6577))
        for x in random.Random(6578).sample(made, 40):
            lines = x["text"].split("\n")
            scene = next(t[len("scene: "):] for t in lines if t.startswith("scene: "))
            out.append({"before": [t[len("before: "):] for t in lines if t.startswith("before: ")], "bot": None,
                        "scene": scene, "scene_parts": scene_parts(scene), "line": lines[-1][len("now: "):]})
        return out
    E.test_rows = rows
    E.main()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts["v65"], ensure_ascii=False, indent=1), counts["v64_rows"], "+", counts["v65_rows"], "=", len(rows), "rows")
        rng = random.Random(2)
        for r in rng.sample(rows[-counts["v65_rows"]:], 24) + rng.sample([r for r in rows[:counts["v64_rows"]] if "scene: " in r["text"]], 6):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        train(seed)
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    else:
        print(__doc__)
