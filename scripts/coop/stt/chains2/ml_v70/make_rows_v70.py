"""Round v70's decoder rows (2026-11-11, the owner: driving by voice and the body's commands; plan TODO_v70.md, the canon in its
section 10): Russian, English and Spanish lines -> the canonical English the classifier and the game read.

  drive_fwd     in the car («едь вперёд», «прямо», «поехали», «до перекрёстка») -> "drive forward"
  drive_turn    in the car («поверни налево», «на втором перекрёстке направо», «третий поворот налево») -> "take the next left" /
                "take the second right" / "take the third left" (no "junction", no "car": place words of vocabulary v16, which the
                planner would ground or ask about)
  drive_around  in the car («развернись», «разворот», «едь обратно») -> "make a u-turn"
  drive_to      anywhere («едь к банку», «отвези меня до аптеки», «едь к моей метке», «едь туда») -> "drive to the bank", "drive to
                my pin", "drive there" (on foot the game gets into the nearest free car)
  drive_park    in the car («припаркуйся», «прижмись к обочине») -> "pull over"
  drive_speed   in the car («быстрее», «газуй» / «помедленнее», «не гони») -> "drive faster" / "drive slower"
  drive_stop    in the car («тормози», «останови машину») -> "hit the brakes" (a bare «стой» / «стоп» stays "wait" / "stop")
  drive_chain   in the car, two orders («едь вперёд, потом налево», «садись в машину и едь к банку») -> both, a line each
  foot_same     contrast: the same words on foot, as the deployed decoder (v69s5) writes them («поверни налево» "turn left",
                «развернись» "turn around", «вперёд» "go", «тормози» "stop", «помедленнее» "slow down")
  body_move     a part raised, lowered, turned, tilted, by an angle, a deviation, a manner -> the body command line ("raise arm_r
                90 left 20 speed 2", "turn head left 45", "lower torso 40", "turn body right 90", "lower body 90", "relax all")
  body_strike   a strike in place («ударь ногой», «хук левой, сильно», «апперкот», «локтем») -> "kick", "hook left hard", ...
  strike_him    contrast: a strike at someone («ударь его ногой», «пни его») -> "kick him", "punch him" (MELEE, as before)
  body_combo    «запомни связку двойка: джеб, потом прямой» -> "teach двойка = jab ; punch"; «сделай двойку» -> "play двойка";
                «забудь связку двойка» -> "forget двойка"; «какие связки ты знаешь» -> "combos"

The scene: a drive row's is the game's own line for the bot at the wheel ("a car 0 m away"), or for «едь к X» any (no car near,
a car N m away); a body row's a neutral one (chains12_v68.with_neutral_scenes, by the wrapper).

    python make_rows_v70.py           counts and samples
"""
import io, os, random, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ml_v69"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import make_rows_v69 as R69  # noqa: E402  (dress, answer, row: the round before's)
import chains9_v65 as P9     # noqa: E402  (scene_text, with_scene)

dress, row = R69.dress, R69.row

# ---------------------------------------------------------------- the scene

def scene_in_car(rng):
    last = None
    if rng.random() < 0.3:
        last = (rng.choice(["car", "box", "door", "table", "crate"]), rng.choice([0, 1, 2, 3, 5]))
    return P9.scene_text(car=0, last=last)


def scene_any(rng):
    r = rng.random()
    car = 0 if r < 0.4 else (rng.choice([3, 5, 8, 12, 18, 24]) if r < 0.75 else None)
    return P9.scene_text(car=car)


def scene_on_foot(rng):
    return P9.scene_text(car=None if rng.random() < 0.6 else rng.choice([6, 10, 15, 20, 25]))


def with_scene(r, scene):
    r["text"] = P9.with_scene(r["text"], scene)
    return r

# ---------------------------------------------------------------- numbers

RU_NUM = {10: "десять", 15: "пятнадцать", 20: "двадцать", 30: "тридцать", 40: "сорок", 45: "сорок пять", 60: "шестьдесят",
          70: "семьдесят", 90: "девяносто", 120: "сто двадцать", 150: "сто пятьдесят", 180: "сто восемьдесят"}
ES_NUM = {10: "diez", 15: "quince", 20: "veinte", 30: "treinta", 40: "cuarenta", 45: "cuarenta y cinco", 60: "sesenta", 70: "setenta",
          90: "noventa", 120: "ciento veinte", 150: "ciento cincuenta", 180: "ciento ochenta"}
EN_NUM = {10: "ten", 15: "fifteen", 20: "twenty", 30: "thirty", 40: "forty", 45: "forty five", 60: "sixty", 70: "seventy", 90: "ninety",
          120: "a hundred and twenty", 150: "a hundred and fifty", 180: "a hundred and eighty"}


def num(lang, n, rng):
    """A number as said: digits half the time (the recognizer writes either), else in words."""
    if rng.random() < 0.5:
        return str(n)
    return {"ru": RU_NUM, "es": ES_NUM, "en": EN_NUM}[lang][n]


def degrees(lang, n, rng):
    d = num(lang, n, rng)
    if lang == "ru":
        return rng.choice([f"на {d} градусов", f"на {d}", f"на {d} градусов"])
    if lang == "es":
        return rng.choice([f"{d} grados", f"unos {d} grados"])
    return rng.choice([f"{d} degrees", f"by {d} degrees", f"{d} degrees"])

# ---------------------------------------------------------------- driving

RU_FWD = ["едь вперёд", "езжай вперёд", "поезжай вперёд", "поехали вперёд", "вперёд", "прямо", "едь прямо", "езжай прямо", "давай прямо",
          "поехали", "трогай", "едь дальше", "езжай дальше", "двигай дальше", "едь до перекрёстка", "вперёд до перекрёстка",
          "давай до перекрёстка", "поехали прямо", "гони вперёд", "рули прямо"]
ES_FWD = ["adelante", "sigue recto", "todo recto", "conduce recto", "vamos", "arranca", "sigue", "hasta el cruce", "sigue adelante",
          "conduce hacia adelante"]
EN_FWD = ["go forward", "drive forward", "straight on", "keep going", "go straight", "drive on", "let's go", "go ahead", "drive",
          "keep driving", "to the next junction", "go straight ahead"]

RU_TURN = ["поверни {s}", "сверни {s}", "поворачивай {s}", "{s}", "на перекрёстке {s}", "на следующем перекрёстке {s}",
           "на ближайшем повороте {s}", "давай {s}", "уходи {s}", "сворачивай {s}", "поверни {s} на перекрёстке", "на повороте {s}"]
RU_TURN_N = {2: ["на втором перекрёстке {s}", "второй поворот {s}", "на втором повороте {s}", "через один перекрёсток {s}",
                 "второй {s}"],
             3: ["на третьем перекрёстке {s}", "третий поворот {s}", "на третьем повороте {s}"]}
RU_SIDE = {"left": "налево", "right": "направо"}
ES_TURN = ["gira a la {s}", "dobla a la {s}", "a la {s} en el cruce", "en el próximo cruce a la {s}", "a la {s}", "tuerce a la {s}"]
ES_TURN_N = {2: ["toma la segunda a la {s}", "en el segundo cruce a la {s}", "la segunda a la {s}"],
             3: ["toma la tercera a la {s}", "en el tercer cruce a la {s}"]}
ES_SIDE = {"left": "izquierda", "right": "derecha"}
EN_TURN = ["turn {s}", "take a {s}", "hang a {s}", "next {s}", "{s} at the junction", "turn {s} at the crossroads", "go {s} at the next junction",
           "make a {s}", "{s} here"]
EN_TURN_N = {2: ["take the second {s}", "second {s}", "{s} at the second junction"], 3: ["take the third {s}", "third {s}"]}
ORD = {2: "second", 3: "third"}

RU_AROUND = ["развернись", "разворачивайся", "разворот", "давай разворот", "развернись и едь обратно", "едь обратно", "поехали обратно",
             "разворачивай машину", "развернись тут", "сделай разворот"]
ES_AROUND = ["da la vuelta", "haz un cambio de sentido", "media vuelta", "gira en u", "vuelve atrás con el coche", "da la vuelta al coche"]
EN_AROUND = ["turn around", "make a u-turn", "u-turn", "go back the other way", "turn back", "flip it around", "do a u-turn"]

RU_PARK = ["припаркуйся", "паркуйся", "припаркуй машину", "встань у обочины", "прижмись к обочине", "остановись у тротуара",
           "тормозни у обочины", "паркуемся", "встань на парковку", "припаркуйся тут", "прижмись вправо и встань"]
ES_PARK = ["aparca", "estaciona", "aparca el coche", "para a un lado", "arrímate a la acera", "estaciona aquí"]
EN_PARK = ["park", "park the car", "pull over", "pull over here", "park here", "find a spot and park"]

RU_FAST = ["быстрее", "давай быстрее", "газуй", "газу", "прибавь", "прибавь газу", "поддай газу", "жми", "гони быстрее", "ускорься",
           "быстрей", "жми на газ"]
RU_SLOW = ["медленнее", "помедленнее", "потише", "не гони", "сбавь", "сбавь скорость", "тише едь", "полегче", "медленней", "не так быстро"]
ES_FAST = ["más rápido", "acelera", "dale gas", "más deprisa", "pisa el acelerador"]
ES_SLOW = ["más despacio", "despacio", "no corras", "frena un poco", "ve más lento"]
EN_FAST = ["faster", "speed up", "step on it", "floor it", "go faster", "hurry up"]
EN_SLOW = ["slower", "slow down", "easy", "not so fast", "take it easy", "go slower"]

RU_STOP = ["тормози", "затормози", "останови машину", "останавливайся", "жми на тормоз", "по тормозам", "стоп машина", "тормози давай"]
ES_STOP = ["frena", "para el coche", "detén el coche", "frena ya", "pisa el freno"]
EN_STOP = ["brake", "stop the car", "hit the brakes", "brake now", "stop driving"]

# places: (ru dative after «к», ru genitive after «до», es with article, en canonical)
PLACES = [("банку", "банка", "el banco", "the bank"), ("ресторану", "ресторана", "el restaurante", "the restaurant"),
          ("кафе", "кафе", "la cafetería", "the cafe"), ("магазину", "магазина", "la tienda", "the shop"),
          ("отелю", "отеля", "el hotel", "the hotel"), ("гостинице", "гостиницы", "el hotel", "the hotel"),
          ("аптеке", "аптеки", "la farmacia", "the pharmacy"), ("заправке", "заправки", "la gasolinera", "the gas station"),
          ("парковке", "парковки", "el aparcamiento", "the parking lot"), ("стоянке", "стоянки", "el aparcamiento", "the parking lot"),
          ("перекрёстку", "перекрёстка", "el cruce", "the junction"), ("светофору", "светофора", "el semáforo", "the traffic light"),
          ("главной двери", "главной двери", "la puerta principal", "the main door"), ("банкомату", "банкомата", "el cajero", "the ATM")]
RU_TO = ["едь к {d}", "поехали к {d}", "езжай к {d}", "гони к {d}", "рули к {d}", "отвези меня к {d}", "отвези нас к {d}",
         "подвези меня к {d}", "подбрось меня к {d}", "довези до {g}", "вези к {d}", "поезжай к {d}", "едь до {g}", "давай к {d}"]
RU_TO_PIN = [("едь к моей метке", "drive to my pin"), ("поехали к метке", "drive to my pin"), ("едь к метке", "drive to my pin"),
             ("отвези меня к метке", "drive to my pin"), ("едь туда", "drive there"), ("поехали туда", "drive there"),
             ("едь вон туда", "drive over there"), ("гони туда", "drive there"), ("рули туда", "drive there")]
ES_TO = ["ve a {e}", "conduce a {e}", "llévame a {e}", "vamos a {e}", "maneja hasta {e}", "llévanos a {e}"]
ES_TO_PIN = [("ve a mi marcador", "drive to my pin"), ("conduce hasta mi marca", "drive to my pin"), ("ve allí", "drive there"),
             ("conduce hacia allá", "drive over there")]
EN_TO = ["drive to {c}", "take me to {c}", "give me a ride to {c}", "drive me to {c}", "go to {c} by car", "head to {c} in the car",
         "drive us to {c}", "let's drive to {c}"]
EN_TO_PIN = [("drive to my pin", "drive to my pin"), ("drive to the pin", "drive to my pin"), ("drive there", "drive there"),
             ("drive over there", "drive over there")]


def es_a(e):
    """«a el banco» -> «al banco»."""
    return re.sub(r"\ba el\b", "al", e)


def drive_rows(rng):
    out = []
    langs = ["ru"] * 6 + ["en"] * 2 + ["es"] * 2

    def car(case, lang, line, parts, scene=None):
        out.append(with_scene(row(case, lang, line, parts, rng, before=R69.maybe_before(lang, rng, 0.15)), scene or scene_in_car(rng)))

    for _ in range(260):
        lang = rng.choice(langs)
        line = rng.choice({"ru": RU_FWD, "es": ES_FWD, "en": EN_FWD}[lang])
        car("drive_fwd", lang, line, ["drive forward"])
    for _ in range(420):
        lang = rng.choice(langs)
        side = rng.choice(["left", "right"])
        n = rng.choice([1, 1, 1, 1, 2, 2, 3])
        if n == 1:
            tpl = rng.choice({"ru": RU_TURN, "es": ES_TURN, "en": EN_TURN}[lang])
            ans = f"take the next {side}"
        else:
            tpl = rng.choice({"ru": RU_TURN_N, "es": ES_TURN_N, "en": EN_TURN_N}[lang][n])
            ans = f"take the {ORD[n]} {side}"
        s = {"ru": RU_SIDE, "es": ES_SIDE, "en": {"left": "left", "right": "right"}}[lang][side]
        car("drive_turn", lang, tpl.format(s=s), [ans])
    for _ in range(160):
        lang = rng.choice(langs)
        car("drive_around", lang, rng.choice({"ru": RU_AROUND, "es": ES_AROUND, "en": EN_AROUND}[lang]), ["make a u-turn"])
    for _ in range(420):
        lang = rng.choice(langs)
        if rng.random() < 0.2:
            line, ans = rng.choice({"ru": RU_TO_PIN, "es": ES_TO_PIN, "en": EN_TO_PIN}[lang])
        else:
            d, g, e, c = rng.choice(PLACES)
            if lang == "ru":
                line = rng.choice(RU_TO).format(d=d, g=g)
            elif lang == "es":
                line = es_a(rng.choice(ES_TO).format(e=e))
            else:
                line = rng.choice(EN_TO).format(c=c)
            ans = f"drive to {c}"
        out.append(with_scene(row("drive_to", lang, line, [ans], rng, before=R69.maybe_before(lang, rng, 0.15)), scene_any(rng)))
    for _ in range(160):
        lang = rng.choice(langs)
        car("drive_park", lang, rng.choice({"ru": RU_PARK, "es": ES_PARK, "en": EN_PARK}[lang]), ["pull over"])
    for _ in range(220):
        lang = rng.choice(langs)
        fast = rng.random() < 0.5
        pool = {"ru": (RU_FAST, RU_SLOW), "es": (ES_FAST, ES_SLOW), "en": (EN_FAST, EN_SLOW)}[lang][0 if fast else 1]
        car("drive_speed", lang, rng.choice(pool), ["drive faster" if fast else "drive slower"])
    for _ in range(140):
        lang = rng.choice(langs)
        car("drive_stop", lang, rng.choice({"ru": RU_STOP, "es": ES_STOP, "en": EN_STOP}[lang]), ["hit the brakes"])
    # two orders in a line
    for _ in range(220):
        lang = rng.choice(langs)
        side = rng.choice(["left", "right"])
        kind = rng.random()
        if lang == "ru":
            s = RU_SIDE[side]
            if kind < 0.45:
                line = rng.choice([f"едь вперёд, потом {s}", f"прямо, а потом {s}", f"вперёд и на перекрёстке {s}",
                                   f"едь вперёд, поверни {s}", f"поехали вперёд и сверни {s}", f"едь прямо и {s}"])
                parts = ["drive forward", f"take the next {side}"]
            elif kind < 0.7:
                o = "right" if side == "left" else "left"
                line = f"поверни {s}, потом {RU_SIDE[o]}"
                parts = [f"take the next {side}", f"take the next {o}"]
            else:
                d, g, e, c = rng.choice(PLACES)
                line = rng.choice([f"садись в машину и едь к {d}", f"садись за руль и вези меня к {d}", f"залезай в машину, едь к {d}"])
                parts = ["get in the car", f"drive to {c}"]
                out.append(with_scene(row("drive_chain", lang, line, parts, rng), P9.scene_text(car=rng.choice([3, 5, 8, 12]))))
                continue
        elif lang == "es":
            s = ES_SIDE[side]
            if kind < 0.6:
                line = rng.choice([f"sigue recto y luego a la {s}", f"adelante y gira a la {s}"])
                parts = ["drive forward", f"take the next {side}"]
            else:
                d, g, e, c = rng.choice(PLACES)
                line = es_a(f"sube al coche y ve a {e}")
                parts = ["get in the car", f"drive to {c}"]
                out.append(with_scene(row("drive_chain", lang, line, parts, rng), P9.scene_text(car=rng.choice([3, 5, 8, 12]))))
                continue
        else:
            if kind < 0.6:
                line = rng.choice([f"go forward then turn {side}", f"drive straight and take a {side}", f"keep going and turn {side}"])
                parts = ["drive forward", f"take the next {side}"]
            else:
                d, g, e, c = rng.choice(PLACES)
                line = f"get in the car and drive to {c}"
                parts = ["get in the car", f"drive to {c}"]
                out.append(with_scene(row("drive_chain", lang, line, parts, rng), P9.scene_text(car=rng.choice([3, 5, 8, 12]))))
                continue
        car("drive_chain", lang, line, parts)
    # the same words on foot: as the deployed decoder writes them (probe 2026-11-11)
    foot = [("поверни налево", "turn left"), ("поверни направо", "turn right"), ("развернись", "turn around"), ("вперёд", "go"),
            ("тормози", "stop"), ("помедленнее", "slow down"), ("стой", "wait"), ("стоп", "stop"), ("иди вперёд", "go forward"),
            ("повернись налево", "turn left"), ("turn left", "turn left"), ("turn around", "turn around"), ("stop", "stop"),
            ("gira a la izquierda", "turn left"), ("date la vuelta", "turn around")]
    for _ in range(160):
        line, ans = rng.choice(foot)
        lang = "ru" if re.search("[а-яё]", line) else ("es" if re.search("[áéíóúñ]|gira|date", line) else "en")
        out.append(with_scene(row("foot_same", lang, line, [ans], rng), scene_on_foot(rng)))
    # in the car a bare «стой» / «стоп» is still a wait / a stop (WAIT brakes the car)
    for _ in range(40):
        line, ans = rng.choice([("стой", "wait"), ("стоп", "stop"), ("stop", "stop"), ("wait", "wait")])
        lang = "ru" if re.search("[а-яё]", line) else "en"
        car("drive_wait", lang, line, [ans])
    return out

# ---------------------------------------------------------------- the body

# (ru accusative, es, en, part)
LIMBS = [("правую руку", "el brazo derecho", "your right arm", "arm_r"), ("левую руку", "el brazo izquierdo", "your left arm", "arm_l"),
         ("руки", "los brazos", "your arms", "arms"), ("обе руки", "los dos brazos", "both arms", "arms"),
         ("правую ногу", "la pierna derecha", "your right leg", "leg_r"), ("левую ногу", "la pierna izquierda", "your left leg", "leg_l")]
RU_RAISE = ["подними", "подыми", "поднимай", "вскинь", "подними-ка"]
RU_LOWER = ["опусти", "опускай", "опусти-ка"]
RU_DEV = [("и чуть влево", "left 20"), ("и чуть вправо", "right 20"), ("и влево на тридцать", "left 30"), ("и вправо на 30", "right 30"),
          ("и в сторону", "out 90"), ("и немного вверх", "up 20")]
RU_MANNER = [("быстро", "speed 2"), ("медленно", "speed 0.5"), ("резко", "sharp 1"), ("плавно", "sharp 0"), ("очень быстро", "speed 3")]
ES_MANNER = [("rápido", "speed 2"), ("despacio", "speed 0.5"), ("de golpe", "sharp 1"), ("suavemente", "sharp 0")]
EN_MANNER = [("fast", "speed 2"), ("slowly", "speed 0.5"), ("sharply", "sharp 1"), ("smoothly", "sharp 0")]
ANGLES = [20, 30, 45, 60, 90, 120, 150, 180]
TURN_ANGLES = [20, 30, 45, 60, 90]


def canon(*bits):
    return " ".join(b for b in bits if b)


def body_rows(rng):
    out = []
    langs = ["ru"] * 6 + ["en"] * 2 + ["es"] * 2

    def add(case, lang, line, ans):
        out.append(row(case, lang, line, [ans], rng, before=R69.maybe_before(lang, rng, 0.15)))

    for _ in range(700):
        lang = rng.choice(langs)
        k = rng.random()
        manner = rng.choice([None, None, None] + list(range(4)))
        if k < 0.42:       # a limb raised: the angle, a deviation, a manner
            ru, es, en, part = rng.choice(LIMBS)
            n = rng.choice([None, None] + (ANGLES if part.startswith("arm") or part == "arms" else [30, 45, 60, 90]))
            dev = rng.choice([None, None, None] + list(range(len(RU_DEV)))) if part.startswith("arm") else None
            ma = None
            if lang == "ru":
                bits = [rng.choice(RU_RAISE), ru]
                if n:
                    bits.append(degrees("ru", n, rng))
                if dev is not None:
                    bits.append(RU_DEV[dev][0])
                if manner is not None:
                    m = RU_MANNER[manner % len(RU_MANNER)]
                    bits.insert(0 if rng.random() < 0.5 else len(bits), m[0])
                    ma = m[1]
                line = " ".join(bits)
            elif lang == "es":
                line = "levanta " + es + (" " + degrees("es", n, rng) if n else "")
                if manner is not None:
                    m = ES_MANNER[manner % len(ES_MANNER)]
                    line += " " + m[0]
                    ma = m[1]
                dev = None
            else:
                line = "raise " + en + (" " + degrees("en", n, rng) if n else "")
                if manner is not None:
                    m = EN_MANNER[manner % len(EN_MANNER)]
                    line += " " + m[0]
                    ma = m[1]
                dev = None
            ans = canon("raise", part, str(n) if n else "", RU_DEV[dev][1] if dev is not None else "", ma)
            add("body_move", lang, line, ans)
        elif k < 0.52:     # lowered
            ru, es, en, part = rng.choice(LIMBS)
            line = {"ru": f"{rng.choice(RU_LOWER)} {ru}", "es": f"baja {es}", "en": f"lower {en}"}[lang]
            add("body_move", lang, line, canon("lower", part))
        elif k < 0.6:      # arms out, hands up
            if lang == "ru":
                line, ans = rng.choice([("разведи руки в стороны", "raise arms 90 out 90"), ("разведи руки", "raise arms 90 out 90"),
                                        ("руки в стороны", "raise arms 90 out 90"), ("руки вверх", "raise arms 180"),
                                        ("подними руки вверх", "raise arms 180"), ("вытяни руки вперёд", "raise arms 90")])
            elif lang == "es":
                line, ans = rng.choice([("abre los brazos", "raise arms 90 out 90"), ("brazos arriba", "raise arms 180"),
                                        ("estira los brazos hacia adelante", "raise arms 90")])
            else:
                line, ans = rng.choice([("spread your arms", "raise arms 90 out 90"), ("arms out to the sides", "raise arms 90 out 90"),
                                        ("hands up high", "raise arms 180"), ("put your arms up", "raise arms 180"),
                                        ("stretch your arms forward", "raise arms 90")])
            add("body_move", lang, line, ans)
        elif k < 0.72:     # the head
            side = rng.choice(["left", "right"])
            n = rng.choice([None, None, 20, 30, 45, 60])
            kind = rng.random()
            if kind < 0.55:
                ru_side = {"left": "налево", "right": "направо"}[side]
                line = {"ru": f"поверни голову {ru_side}" + (" " + degrees("ru", n, rng) if n else ""),
                        "es": f"gira la cabeza a la {ES_SIDE[side]}" + (" " + degrees("es", n, rng) if n else ""),
                        "en": f"turn your head {side}" + (" " + degrees("en", n, rng) if n else "")}[lang]
                ans = canon("turn head", side, str(n) if n else "")
            elif kind < 0.75:
                line = {"ru": f"наклони голову {'влево' if side == 'left' else 'вправо'}", "es": f"inclina la cabeza a la {ES_SIDE[side]}",
                        "en": f"tilt your head {side}"}[lang]
                ans = canon("tilt head", side)
            else:
                up = rng.random() < 0.5
                line = {"ru": "подними голову" if up else "опусти голову", "es": "levanta la cabeza" if up else "baja la cabeza",
                        "en": "head up" if up else "lower your head"}[lang]
                ans = "raise head" if up else "lower head"
            add("body_move", lang, line, ans)
        elif k < 0.84:     # the torso
            n = rng.choice([None, None, 20, 30, 40, 60])
            kind = rng.random()
            if kind < 0.5:
                line = {"ru": rng.choice(["наклонись вперёд", "нагнись", "наклонись", "согнись вперёд"]) + (" " + degrees("ru", n, rng) if n else ""),
                        "es": "inclínate hacia adelante" + (" " + degrees("es", n, rng) if n else ""),
                        "en": rng.choice(["bend forward", "lean forward"]) + (" " + degrees("en", n, rng) if n else "")}[lang]
                ans = canon("lower torso", str(n) if n else "")
            elif kind < 0.8:
                side = rng.choice(["left", "right"])
                line = {"ru": f"наклонись {'влево' if side == 'left' else 'вправо'}", "es": f"inclínate a la {ES_SIDE[side]}",
                        "en": f"lean {side}"}[lang]
                ans = canon("tilt torso", side)
            else:
                line = {"ru": rng.choice(["прогнись назад", "откинься назад"]), "es": "échate hacia atrás", "en": "lean back"}[lang]
                ans = "raise torso"
            add("body_move", lang, line, ans)
        elif k < 0.93:     # the whole body
            if rng.random() < 0.3:
                # a turn with an angle and no part named is the whole body's (a plain «повернись налево» stays a look)
                side = rng.choice(["left", "right"])
                n = rng.choice([45, 90, 90, 180])
                line = {"ru": f"{rng.choice(['повернись', 'развернись', 'поворачивайся'])} {'налево' if side == 'left' else 'направо'} {degrees('ru', n, rng)}",
                        "es": f"gira a la {ES_SIDE[side]} {degrees('es', n, rng)}",
                        "en": f"turn {side} {degrees('en', n, rng)}"}[lang]
                ans = f"turn body {side} {n}"
            elif rng.random() < 0.6:
                side = rng.choice(["left", "right"])
                n = rng.choice([None, 45, 90, 90, 180])
                line = {"ru": rng.choice([f"повернись всем телом {'налево' if side == 'left' else 'направо'}",
                                          f"развернись корпусом {'налево' if side == 'left' else 'направо'}",
                                          f"повернись всем телом {'влево' if side == 'left' else 'вправо'}"]) + (" " + degrees("ru", n, rng) if n else ""),
                        "es": f"gira todo el cuerpo a la {ES_SIDE[side]}" + (" " + degrees("es", n, rng) if n else ""),
                        "en": f"turn your whole body {side}" + (" " + degrees("en", n, rng) if n else "")}[lang]
                ans = canon("turn body", side, str(n) if n else "")
            else:
                n = rng.choice([45, 60, 90])
                line = {"ru": f"присядь {degrees('ru', n, rng)}", "es": f"agáchate {degrees('es', n, rng)}",
                        "en": f"squat {degrees('en', n, rng)}"}[lang]
                ans = f"lower body {n}"
            add("body_move", lang, line, ans)
        else:              # rest
            line, ans = {"ru": rng.choice([("расслабься", "relax all"), ("вольно", "relax all"), ("стой спокойно", "relax all"),
                                           ("верни всё как было", "relax all"), ("расслабь руки", "relax arms"), ("поклонись", "bow"),
                                           ("опусти всё", "relax all")]),
                         "es": rng.choice([("relájate", "relax all"), ("descansa", "relax all"), ("haz una reverencia", "bow")]),
                         "en": rng.choice([("relax", "relax all"), ("at ease", "relax all"), ("loosen up", "relax all"),
                                           ("relax your arms", "relax arms"), ("bow", "bow")])}[lang]
            add("body_move", lang, line, ans)
    return out


STRIKES_RU = [("ударь кулаком", "punch"), ("бей кулаком", "punch"), ("ударь рукой", "punch"), ("прямой удар", "punch"),
              ("прямой правой", "punch"), ("джеб", "jab"), ("прямой левой", "jab"), ("хук", "hook"), ("сделай хук", "hook"),
              ("боковой удар рукой", "hook"), ("апперкот", "uppercut"), ("удар снизу", "uppercut"), ("ударь локтем", "elbow"),
              ("локтем", "elbow"), ("ударь ногой", "kick"), ("пни", "kick"), ("пинок", "kick"), ("удар ногой вперёд", "kick"),
              ("боковой удар ногой", "sidekick"), ("удар ногой в сторону", "sidekick"), ("ударь коленом", "knee"), ("коленом", "knee"),
              ("ударь головой", "headbutt"), ("удар головой", "headbutt"), ("ударь прикладом", "butt"), ("прикладом", "butt")]
STRIKES_ES = [("da un puñetazo", "punch"), ("golpea con el puño", "punch"), ("jab", "jab"), ("gancho", "hook"), ("uppercut", "uppercut"),
              ("codazo", "elbow"), ("da una patada", "kick"), ("patada lateral", "sidekick"), ("rodillazo", "knee"), ("cabezazo", "headbutt"),
              ("culatazo", "butt")]
STRIKES_EN = [("punch", "punch"), ("throw a punch", "punch"), ("jab", "jab"), ("hook", "hook"), ("throw a hook", "hook"),
              ("uppercut", "uppercut"), ("elbow strike", "elbow"), ("kick", "kick"), ("front kick", "kick"), ("side kick", "sidekick"),
              ("knee strike", "knee"), ("headbutt", "headbutt"), ("rifle butt strike", "butt")]


def strike_rows(rng):
    out = []
    langs = ["ru"] * 6 + ["en"] * 2 + ["es"] * 2
    for _ in range(520):
        lang = rng.choice(langs)
        said, base = rng.choice({"ru": STRIKES_RU, "es": STRIKES_ES, "en": STRIKES_EN}[lang])
        bits = [said]
        side = high = force = manner = None
        if base in ("hook", "uppercut", "punch", "elbow", "kick", "sidekick", "knee") and rng.random() < 0.4:
            side = rng.choice(["left", "right"])
            bits.append({"ru": {"left": "левой", "right": "правой"}, "es": {"left": "con la izquierda", "right": "con la derecha"},
                         "en": {"left": "with your left", "right": "with your right"}}[lang][side])
        if base in ("hook", "kick", "punch") and rng.random() < 0.2:
            high = rng.choice(["high", "low"])
            bits.append({"ru": {"high": "высоко", "low": "низко"}, "es": {"high": "alto", "low": "bajo"}, "en": {"high": "high", "low": "low"}}[lang][high])
        if rng.random() < 0.3:
            force = rng.choice(["hard", "soft"])
            w = {"ru": {"hard": rng.choice(["сильно", "со всей силы", "мощно"]), "soft": rng.choice(["слабо", "легонько"])},
                 "es": {"hard": "fuerte", "soft": "suave"}, "en": {"hard": "hard", "soft": "softly"}}[lang][force]
            bits.insert(0 if rng.random() < 0.5 else len(bits), w)
        if rng.random() < 0.15:
            m = {"ru": RU_MANNER, "es": ES_MANNER, "en": EN_MANNER}[lang][rng.randrange(4)]
            bits.append(m[0])
            manner = m[1]
        # the side's word for the strike: a jab is the left punch; a right is each strike's own side, unsaid
        name = base
        side_c = "left" if side == "left" else ""
        if base == "punch" and side == "left":
            name, side_c = "jab", ""
        ans = canon(name, side_c, high or "", manner or "", force or "")
        out.append(row("body_strike", lang, " ".join(bits), [ans], rng, before=R69.maybe_before(lang, rng, 0.15)))
    # a strike at someone: as before (MELEE)
    him = [("ударь его ногой", "kick him"), ("пни его", "kick him"), ("ударь его кулаком", "punch him"), ("врежь ему", "punch him"),
           ("ударь его локтем", "elbow him"), ("ударь его головой", "headbutt him"), ("dale una patada", "kick him"),
           ("pégale un puñetazo", "punch him"), ("kick him", "kick him"), ("punch that guy", "punch that guy")]
    for _ in range(120):
        line, ans = rng.choice(him)
        lang = "ru" if re.search("[а-яё]", line) else ("es" if re.search("dale|pégale", line) else "en")
        out.append(row("strike_him", lang, line, [ans], rng))
    return out

# ---------------------------------------------------------------- combos

NAMES_RU = [("двойка", "двойку"), ("тройка", "тройку"), ("приветствие", "приветствие"), ("атака", "атаку"), ("защита", "защиту"),
            ("мельница", "мельницу"), ("финт", "финт"), ("танец", "танец"), ("разминка", "разминку")]
NAMES_ES = ["doble", "triple", "saludo", "ataque", "baile"]
NAMES_EN = ["double", "triple", "salute", "boxer", "dance", "warmup"]
STEPS = [("джеб", "un jab", "a jab", "jab"), ("прямой правой", "un directo", "a punch", "punch"), ("хук левой", "un gancho de izquierda", "a left hook", "hook left"),
         ("хук правой", "un gancho de derecha", "a right hook", "hook right"), ("апперкот", "un uppercut", "an uppercut", "uppercut"),
         ("удар ногой", "una patada", "a kick", "kick"), ("коленом", "un rodillazo", "a knee", "knee"), ("локтем", "un codazo", "an elbow", "elbow"),
         ("подними правую руку", "levanta el brazo derecho", "raise your right arm", "raise arm_r"),
         ("опусти руку", "baja el brazo", "lower your arm", "lower arm_r"), ("подожди секунду", "espera un segundo", "wait a second", "wait 1"),
         ("подожди две секунды", "espera dos segundos", "wait two seconds", "wait 2"), ("расслабься", "relájate", "relax", "relax all")]


def combo_rows(rng):
    out = []
    langs = ["ru"] * 6 + ["en"] * 2 + ["es"] * 2
    for _ in range(420):
        lang = rng.choice(langs)
        k = rng.random()
        if lang == "ru":
            nom, acc = rng.choice(NAMES_RU)
        elif lang == "es":
            nom = acc = rng.choice(NAMES_ES)
        else:
            nom = acc = rng.choice(NAMES_EN)
        if k < 0.45:       # teach
            steps = rng.sample(STEPS, rng.choice([2, 2, 3, 3, 4]))
            if lang == "ru":
                said = (", потом " if rng.random() < 0.5 else ", ").join(s[0] for s in steps)
                line = rng.choice([f"запомни связку {nom}: {said}", f"новая связка {nom}: {said}", f"выучи связку {nom}: {said}",
                                   f"запомни связку {nom} — {said}"])
            elif lang == "es":
                said = ", luego ".join(s[1] for s in steps)
                line = rng.choice([f"aprende el combo {nom}: {said}", f"recuerda el combo {nom}: {said}"])
            else:
                said = ", then ".join(s[2] for s in steps)
                line = rng.choice([f"remember the combo {nom}: {said}", f"learn a combo called {nom}: {said}", f"new combo {nom}: {said}"])
            ans = f"teach {nom} = " + " ; ".join(s[3] for s in steps)
        elif k < 0.75:     # play
            line = {"ru": rng.choice([f"сделай связку {nom}", f"покажи связку {nom}", f"сделай {acc}", f"покажи {acc}", f"давай {acc}",
                                      f"выполни связку {nom}"]),
                    "es": rng.choice([f"haz el combo {nom}", f"muestra el combo {nom}"]),
                    "en": rng.choice([f"do the combo {nom}", f"play the combo {nom}", f"show me the combo {nom}", f"run combo {nom}"])}[lang]
            ans = f"play {nom}"
        elif k < 0.9:      # forget
            line = {"ru": rng.choice([f"забудь связку {nom}", f"удали связку {nom}", f"сотри связку {nom}"]),
                    "es": rng.choice([f"olvida el combo {nom}", f"borra el combo {nom}"]),
                    "en": rng.choice([f"forget the combo {nom}", f"delete the combo {nom}"])}[lang]
            ans = f"forget {nom}"
        else:              # list
            line = {"ru": rng.choice(["какие связки ты знаешь", "какие у тебя связки", "покажи список связок", "перечисли связки"]),
                    "es": rng.choice(["qué combos sabes", "dime tus combos"]),
                    "en": rng.choice(["what combos do you know", "list your combos", "which combos do you know"])}[lang]
            ans = "combos"
        out.append(row("body_combo", lang, line, [ans], rng, before=R69.maybe_before(lang, rng, 0.1)))
    return out


def decoder_rows(rng):
    """Round v70's rows: driving (with its scenes), the body, strikes, combos (with no scene: the wrapper gives a third of them a
    neutral one)."""
    return drive_rows(rng) + body_rows(rng) + strike_rows(rng) + combo_rows(rng)


if __name__ == "__main__":
    rows = decoder_rows(random.Random(7001))
    c = Counter(f"{r['case']}/{r['lang']}" for r in rows)
    print(len(rows), "rows")
    for k, v in sorted(c.items()):
        print(f"  {k:24} {v}")
    rng = random.Random(4)
    for r in rng.sample(rows, 30):
        print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
