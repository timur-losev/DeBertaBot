"""Round v68's timer rows for the decoder (TODO_v68.md item 1, 1a B and H step 5; the owner 2026-10-29: «добавляй строки и
стартуй обучение»).

The deployed decoder (v67s) loses or bends many numbers (1a B): «Подожди одну минуту» -> "wait", «Подожди пару секунд» ->
"Wait a sec.", «Подожди несколько секунд» -> "Wait a few more seconds.", «Прыгай 10 секунд» -> "jump down 10 seconds",
«Подожди ещё 5 секунд» -> "wait for me". These rows teach it to write the time in ONE English form that time_phrase.py reads
(the brain strips it before the classifier), and nothing that was not said:

  for N seconds        «подожди 5 секунд», «стой тут секунд десять» ("for about 10 seconds"), «присядь на 10 секунд»,
                       «беги 10 секунд вперёд», «полминуты» (30), «полторы секунды» (1.5), «одну минуту» (1 minute), «две
                       минуты» ("for 2 minutes": the brain cuts it to 60), «пару секунд» (2)
  for a few seconds    «несколько секунд», «unos segundos" (the game draws 3..7)
  for A to B seconds   «секунд 10-15», «от десяти до пятнадцати секунд», «entre diez y quince segundos»
  for N more seconds   only when ещё / más / otros / more / another was said
  in N seconds <order> «через 10 секунд иди к двери», «en diez segundos», «посчитай до десяти и ...» (after)
  no time              the idioms: «подожди минуту», «минутку», «секунду», «un momento», "hang on a sec" -> "wait a minute",
                       "hold on a sec" (time_phrase reads no time in them)

The orders: the intents a time lasts for (1a E: hold, follow, a move by a direction, repeat) with frames of their own here
(v67's frames of those intents hold idioms such as «погоди секунду»), and any order for "after" and as the next order of a
line (v67's frames, make_combos_v68). Every row is checked: time_phrase.find on each English line gives the time the row
means, and the rest is the order.

    python make_time_v68.py          counts, the check, samples
"""
import os, random, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..")))      # scripts/coop: time_phrase
import make_combos_v68 as M
import lexicon_v68 as L
import time_phrase as TP

MC = M.MC

# ---------------------------------------------------------------- numbers

RU_ONES_F = ["", "одну", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать",
             "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
RU_TENS = {2: "двадцать", 3: "тридцать", 4: "сорок", 5: "пятьдесят", 6: "шестьдесят", 7: "семьдесят", 8: "восемьдесят", 9: "девяносто"}
RU_GEN = {1: "одного", 2: "двух", 3: "трёх", 4: "четырёх", 5: "пяти", 6: "шести", 7: "семи", 8: "восьми", 9: "девяти", 10: "десяти",
          11: "одиннадцати", 12: "двенадцати", 13: "тринадцати", 14: "четырнадцати", 15: "пятнадцати", 16: "шестнадцати", 17: "семнадцати",
          18: "восемнадцати", 19: "девятнадцати", 20: "двадцати", 30: "тридцати", 40: "сорока"}
ES_ONES = ["", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
           "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiún", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
           "veintiséis", "veintisiete", "veintiocho", "veintinueve"]
ES_TENS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
EN_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
           "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
EN_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}


def ru_num(n):
    """A Russian numeral in the accusative of a feminine noun (секунду, минуту): одну, две, двадцать одну, сто двадцать."""
    if n >= 100:
        return "сто" + ("" if n == 100 else " " + ru_num(n - 100))
    if n < 20:
        return RU_ONES_F[n]
    t, o = divmod(n, 10)
    return RU_TENS[t] + ("" if o == 0 else " " + RU_ONES_F[o])


def ru_noun(n, forms):
    """секунду / секунды / секунд after n (forms: one, few, many)."""
    if 11 <= n % 100 <= 14:
        return forms[2]
    return forms[0] if n % 10 == 1 else forms[1] if 2 <= n % 10 <= 4 else forms[2]


SEC = ("секунду", "секунды", "секунд")
MIN = ("минуту", "минуты", "минут")


def es_num(n):
    if n >= 100:
        return "cien" if n == 100 else "ciento " + es_num(n - 100)
    if n < 30:
        return ES_ONES[n]
    t, o = divmod(n, 10)
    return ES_TENS[t] + ("" if o == 0 else " y " + ("un" if o == 1 else ES_ONES[o]))


def en_num(n):
    if n >= 100:
        return "a hundred" + ("" if n == 100 else " and " + en_num(n - 100))
    if n < 20:
        return EN_ONES[n]
    t, o = divmod(n, 10)
    return EN_TENS[t] + ("" if o == 0 else " " + EN_ONES[o])


def draw_n(rng):
    """Seconds as players say them: round numbers most, any from 1 to 60 at times."""
    if rng.random() < 0.7:
        return rng.choice([2, 3, 3, 4, 5, 5, 5, 6, 7, 8, 10, 10, 10, 12, 15, 15, 20, 20, 25, 30, 30, 40, 45, 50, 60])
    return rng.randint(1, 60)


# ---------------------------------------------------------------- a time, said

class Time:
    """A time to say: what each language says (forms for each place in the line) and the English the decoder writes.
    kind "for" | "after"; want: what time_phrase.find must read from the English (seconds or min/max, more)."""

    def __init__(self, kind, en, want, ru=None, es=None, en_said=None, ru_na=None, more=False):
        self.kind, self.en, self.want, self.more = kind, en, want, more
        self.ru = ru or []          # forms said alone: «5 секунд», «секунд десять»
        self.ru_na = ru_na or []    # forms after «на»: «на 5 секунд» (the accusative)
        self.es = es or []
        self.en_said = en_said or []


def ru_secs(n, rng, digits=None):
    digits = rng.random() < 0.3 if digits is None else digits
    return f"{n} {ru_noun(n, SEC)}" if digits else f"{ru_num(n)} {ru_noun(n, SEC)}"


def time_for(rng, wait=False):
    """A time an order lasts, drawn among the forms (wait: the order is WAIT, where «минуту» alone is the idiom)."""
    r = rng.random()
    if r < 0.46:
        n = draw_n(rng)
        while wait and n == 1:          # "wait one second", «espera un segundo»: the idiom "hold on", not 1 s
            n = draw_n(rng)
        d = rng.random() < 0.3
        ru = [ru_secs(n, rng, d)] + ([f"{n} сек"] if d and rng.random() < 0.3 else []) +             ([f"в течение {n} {'секунды' if n % 10 == 1 and n % 100 != 11 else 'секунд'}"] if d else [])
        es_n = "un" if n == 1 else (str(n) if d else es_num(n))
        es_u = "segundo" if n == 1 else "segundos"
        es = ([] if n == 1 else [f"{es_n} {es_u}"]) + [f"durante {es_n} {es_u}", f"por {es_n} {es_u}"]
        en_n = str(n) if d or rng.random() < 0.3 else en_num(n)
        en_u = "second" if n == 1 else rng.choice(["seconds", "seconds", "secs"])
        en_said = [f"{en_n} {en_u}", f"for {en_n} {en_u}", f"for like {en_n} {en_u}"]
        return Time("for", f"for {n} {'second' if n == 1 else 'seconds'}", {"seconds": float(n)}, ru, es, en_said, ru_na=ru[:1])
    if r < 0.55:
        # «секунд десять»: about (the noun first)
        n = rng.choice([5, 10, 10, 15, 20, 20, 30, 40])
        ru = [f"секунд {ru_num(n)}", f"где-то {ru_secs(n, rng, False)}", f"примерно {ru_secs(n, rng, False)}"]
        es = [f"unos {es_num(n)} segundos", f"como {es_num(n)} segundos"]
        en_said = [f"about {en_num(n)} seconds", f"like {n} seconds", f"around {n} seconds"]
        return Time("for", f"for about {n} seconds", {"seconds": float(n)}, ru, es, en_said)
    if r < 0.62:
        return Time("for", "for 2 seconds", {"seconds": 2.0}, ["пару секунд", "пару сек", "секунды две"], ["un par de segundos", "dos segunditos"],
                    ["a couple of seconds", "a couple seconds", "couple secs"], ru_na=["пару секунд"])
    if r < 0.70:
        return Time("for", "for a few seconds", {"min": 3.0, "max": 7.0}, ["несколько секунд", "пару-тройку секунд"],
                    ["unos segundos", "unos cuantos segundos", "algunos segundos"], ["a few seconds", "several seconds", "a few secs"],
                    ru_na=["несколько секунд"])
    if r < 0.76:
        lo, hi = rng.choice([(3, 5), (5, 7), (5, 10), (10, 15), (10, 20), (15, 20), (20, 30), (30, 40)])
        ru = [f"секунд {lo}-{hi}", f"{lo}-{hi} секунд", f"от {RU_GEN[lo]} до {RU_GEN[hi]} секунд", f"секунд {ru_num(lo)}-{ru_num(hi)}"]
        es = [f"entre {es_num(lo)} y {es_num(hi)} segundos", f"de {es_num(lo)} a {es_num(hi)} segundos"]
        en_said = [f"{lo} to {hi} seconds", f"{en_num(lo)} or {en_num(hi)} seconds", f"like {lo}-{hi} seconds"]
        return Time("for", f"for {lo} to {hi} seconds", {"min": float(lo), "max": float(hi)}, ru, es, en_said)
    if r < 0.82:
        return Time("for", "for 30 seconds", {"seconds": 30.0}, ["полминуты", "секунд тридцать"], ["medio minuto", "treinta segundos"],
                    ["half a minute", "thirty seconds"], ru_na=["полминуты"])
    if r < 0.86:
        return Time("for", "for 1.5 seconds", {"seconds": 1.5}, ["полторы секунды"], ["segundo y medio", "un segundo y medio"],
                    ["one and a half seconds", "1.5 seconds"], ru_na=["полторы секунды"])
    if r < 0.94:
        # minutes: «одну минуту» is 60 s (a numeral); «минуту» alone only for an order that is not a wait (the owner: «подожди
        # минуту» is the idiom); two or more minutes are said as said and cut to 60 by the brain
        m = rng.choice([1, 1, 1, 2, 3])
        if m == 1:
            ru = ["одну минуту", "1 минуту"] + ([] if wait else ["минуту", "минутку"])
            es = ["un minuto", "durante un minuto"] if not wait else ["durante un minuto", "por un minuto"]
            en_said = ["one minute", "for a minute", "1 minute"] if not wait else ["one minute", "for one minute", "for a minute"]
            return Time("for", "for 1 minute", {"seconds": 60.0}, ru, es, en_said, ru_na=["одну минуту"] + ([] if wait else ["минуту", "минутку"]))
        ru = [f"{ru_num(m)} {ru_noun(m, MIN)}", f"{m} {ru_noun(m, MIN)}"]
        es = [f"{es_num(m)} minutos", f"durante {es_num(m)} minutos"]
        return Time("for", f"for {m} minutes", {"seconds": 60.0}, ru, es, [f"{en_num(m)} minutes", f"for {m} minutes"], ru_na=ru[:1])
    # over the cap in seconds: said as said
    n = rng.choice([90, 90, 100, 120])
    ru = [ru_secs(n, rng)] + (["полторы минуты"] if n == 90 else [])
    es = [f"{es_num(n)} segundos"] + (["minuto y medio", "un minuto y medio"] if n == 90 else [])
    en_said = [f"{n} seconds"] + (["a minute and a half"] if n == 90 else [])
    return Time("for", f"for {n} seconds", {"seconds": 60.0}, ru, es, en_said, ru_na=ru[:1])


def time_more(rng):
    """«ещё 5 секунд»: more of a timed order (or 5 s when none runs)."""
    n = rng.choice([2, 3, 5, 5, 5, 10, 10, 15, 20, 30])
    d = rng.random() < 0.3
    ru = [f"ещё {ru_secs(n, rng, d)}", f"ещё {ru_secs(n, rng, d)}", f"ещё секунд {ru_num(n)}"]
    es_n = str(n) if d else es_num(n)
    es = [f"{es_n} segundos más", f"otros {es_n} segundos"]
    en_n = str(n) if d else en_num(n)
    en_said = [f"{en_n} more seconds", f"another {en_n} seconds"]
    return Time("for", f"for {n} more seconds", {"seconds": float(n), "more": True}, ru, es, en_said, more=True)


def time_after(rng):
    """«через 10 секунд»: the order starts after the time (English "in N seconds" before the order)."""
    r = rng.random()
    if r < 0.6:
        n = draw_n(rng)
        d = rng.random() < 0.3
        es_n = "un" if n == 1 else (str(n) if d else es_num(n))
        es_u = "segundo" if n == 1 else "segundos"
        en_n = str(n) if d or rng.random() < 0.3 else en_num(n)
        en_u = "second" if n == 1 else "seconds"
        ru = [f"через {ru_secs(n, rng, d)}"] + ([f"посчитай до {RU_GEN[n]} и"] if 3 <= n <= 20 else [])
        es = [f"en {es_n} {es_u}", f"dentro de {es_n} {es_u}"] + ([f"cuenta hasta {es_num(n)} y"] if 3 <= n <= 20 else [])
        en_said = [f"in {en_n} {en_u}", f"after {en_n} {en_u}"] + ([f"count to {en_num(n)} and"] if 3 <= n <= 20 else [])
        return Time("after", f"in {n} {'second' if n == 1 else 'seconds'}", {"seconds": float(n)}, ru, es, en_said)
    if r < 0.75:
        return Time("after", "in 2 seconds", {"seconds": 2.0}, ["через пару секунд"], ["en un par de segundos", "dentro de un par de segundos"],
                    ["in a couple of seconds", "in a couple seconds"])
    if r < 0.88:
        return Time("after", "in a few seconds", {"min": 3.0, "max": 7.0}, ["через несколько секунд"], ["en unos segundos", "dentro de unos segundos"],
                    ["in a few seconds", "in a few secs"])
    return Time("after", "in 30 seconds", {"seconds": 30.0}, ["через полминуты"], ["en medio minuto", "dentro de medio minuto"],
                ["in half a minute", "in thirty seconds"])


# ---------------------------------------------------------------- orders a time lasts for

# own frames: (said, canonical English); {T...} as make_combos_v67 (a thing of the lexicon). "mid": the time may stand after
# the first word («беги 10 секунд вперёд», «стой 10 секунд тут»)
TIMED = {
    "WAIT": {"ru": [("подожди", "wait"), ("погоди", "wait"), ("жди", "wait"), ("подожди меня", "wait"), ("подожди-ка", "wait"), ("обожди", "wait")],
             "es": [("espera", "wait"), ("espérate", "wait"), ("aguanta", "wait"), ("espera ahí", "wait"), ("espérame", "wait")],
             "en": [("wait", "wait"), ("hold on", "wait"), ("hang on", "wait"), ("give me", "wait"), ("gimme", "wait")]},
    "HOLD_POSITION": {"ru": [("стой здесь", "hold position", "mid"), ("стой тут", "hold position", "mid"), ("стой на месте", "hold position", "mid"),
                             ("держи позицию", "hold position"), ("оставайся тут", "hold position", "mid"), ("не двигайся", "hold position"),
                             ("постой тут", "hold position", "mid"), ("стой у {T:gen}", "hold position at {T}"), ("подожди у {T:gen}", "hold position at {T}")],
                      "es": [("quédate aquí", "hold position"), ("no te muevas", "hold position"), ("mantén la posición", "hold position"),
                             ("quédate quieto", "hold position"), ("quédate junto {T:a}", "hold position at {T}")],
                      "en": [("stay here", "hold position"), ("hold here", "hold position"), ("hold this spot", "hold position"),
                             ("don't move", "hold position"), ("stay by {T}", "hold position at {T}")]},
    "HOLD_ANGLE": {"ru": [("держи угол", "hold that angle"), ("следи за {T:ins}", "keep an eye on {T}"), ("паси {T:acc}", "keep an eye on {T}"),
                          ("держи {T:acc}", "keep an eye on {T}")],
                   "es": [("vigila ese ángulo", "hold that angle"), ("vigila {T}", "keep an eye on {T}"), ("cubre ese ángulo", "hold that angle")],
                   "en": [("hold that angle", "hold that angle"), ("watch {T}", "keep an eye on {T}"), ("keep eyes on {T}", "keep an eye on {T}")]},
    "LOOK_AT": {"ru": [("посмотри туда", "look there"), ("смотри туда", "look there"), ("смотри на {T:acc}", "look at {T}"), ("глянь на {T:acc}", "look at {T}")],
                "es": [("mira allí", "look there"), ("mira hacia allá", "look there"), ("mira {T}", "look at {T}")],
                "en": [("look over there", "look there"), ("look at {T}", "look at {T}")]},
    "LOOK_AT_ME": {"ru": [("посмотри на меня", "look at me"), ("смотри на меня", "look at me")], "es": [("mírame", "look at me")],
                   "en": [("look at me", "look at me")]},
    "CROUCH": {"ru": [("присядь", "crouch"), ("пригнись", "crouch"), ("сядь", "crouch"), ("посиди на корточках", "crouch")],
               "es": [("agáchate", "crouch"), ("quédate agachado", "crouch")], "en": [("crouch", "crouch"), ("get low", "crouch")]},
    "PRONE": {"ru": [("ложись", "go prone"), ("ляг", "go prone"), ("заляг", "go prone"), ("полежи", "go prone")],
              "es": [("túmbate", "go prone"), ("al suelo", "go prone"), ("échate al suelo", "go prone")], "en": [("go prone", "go prone"), ("lie down", "go prone")]},
    "COVER_ME": {"ru": [("прикрой меня", "cover me"), ("прикрывай", "cover me"), ("прикрывай меня", "cover me")],
                 "es": [("cúbreme", "cover me"), ("dame cobertura", "cover me")], "en": [("cover me", "cover me"), ("watch my back", "watch my back")]},
    "TAKE_COVER": {"ru": [("спрячься", "take cover"), ("прячься", "take cover"), ("посиди в укрытии", "take cover"), ("спрячься за {T:ins}", "hide behind {T}")],
                   "es": [("escóndete", "take cover"), ("ponte a cubierto", "take cover"), ("escóndete detrás {T:de}", "hide behind {T}")],
                   "en": [("take cover", "take cover"), ("hide behind {T}", "hide behind {T}")]},
    "HOLD_FIRE": {"ru": [("не стреляй", "hold fire"), ("не пали", "hold fire"), ("прекрати огонь", "hold fire")],
                  "es": [("no dispares", "hold fire"), ("alto el fuego", "hold fire")], "en": [("hold fire", "hold fire"), ("don't shoot", "hold fire")]},
    "FOLLOW_ME": {"ru": [("иди за мной", "follow me", "mid"), ("следуй за мной", "follow me", "mid"), ("за мной", "follow me"), ("держись рядом", "follow me")],
                  "es": [("sígueme", "follow me"), ("ven conmigo", "follow me"), ("pégate a mí", "follow me")],
                  "en": [("follow me", "follow me"), ("stick with me", "follow me")]},
    "MOVE_TO": {"ru": [("беги вперёд", "run forward", "mid"), ("иди вперёд", "go forward", "mid"), ("двигайся вперёд", "move forward", "mid"),
                       ("топай вперёд", "go forward", "mid"), ("беги влево", "run left", "mid"), ("иди налево", "go left", "mid"),
                       ("беги направо", "run right", "mid"), ("иди вправо", "go right", "mid"), ("беги прямо", "run forward", "mid")],
                "es": [("corre hacia adelante", "run forward"), ("avanza", "move forward"), ("sigue adelante", "go forward"),
                       ("corre a la izquierda", "run left"), ("ve a la derecha", "go right"), ("muévete a la izquierda", "move left")],
                "en": [("run forward", "run forward"), ("keep running forward", "run forward"), ("go left", "go left"), ("move right", "move right")]},
    "FALL_BACK": {"ru": [("отступай", "fall back"), ("отходи", "fall back"), ("отходи назад", "fall back")],
                  "es": [("retrocede", "fall back"), ("repliégate", "fall back")], "en": [("fall back", "fall back"), ("back off", "fall back")]},
    "JUMP": {"ru": [("прыгай", "jump"), ("попрыгай", "jump"), ("прыгай на месте", "jump"), ("скачи", "jump"), ("попрыгай на месте", "jump")],
             "es": [("salta", "jump"), ("brinca", "jump"), ("salta en el sitio", "jump"), ("ponte a saltar", "jump")],
             "en": [("jump", "jump"), ("keep jumping", "jump"), ("jump in place", "jump")]},
    "OPEN_FIRE": {"ru": [("стреляй", "open fire"), ("стреляй туда", "open fire"), ("пали", "open fire"), ("стреляй по {T:dat}", "shoot {T}")],
                  "es": [("dispara", "open fire"), ("abre fuego", "open fire"), ("dispárale {T:a}", "shoot {T}")],
                  "en": [("shoot", "open fire"), ("open fire", "open fire"), ("shoot {T}", "shoot {T}")]},
    "SUPPRESS": {"ru": [("подави их", "lay down suppressive fire"), ("прижми их огнём", "lay down suppressive fire"), ("подави {T:acc}", "lay down suppressive fire on {T}")],
                 "es": [("suprímelos", "lay down suppressive fire"), ("fuego de supresión", "lay down suppressive fire")],
                 "en": [("suppress", "lay down suppressive fire"), ("pin them down", "lay down suppressive fire")]},
}
# "give me 5 seconds" is a wait said by the time alone
GIVE = {"give me", "gimme"}
PER_INTENT = {"ru": 70, "es": 40, "en": 16}
AFTER_ROWS = {"ru": 600, "es": 360, "en": 150}
MORE_ROWS = {"ru": 260, "es": 150, "en": 60}
IDIOM_ROWS = {"ru": 220, "es": 120, "en": 50}
MULTI_ROWS = {"ru": 450, "es": 270, "en": 120}
# orders "after" a time and as the next order of a line: every intent with frames but the answers, talk and questions
NOT_AFTER = {"YES", "NO", "MAYBE", "DONT_KNOW", "SMALL_TALK", "PRAISE", "KILL_YOURSELF", "NONE", "WAIT", "GO_NOW", "REPEAT", "SEE_ME",
             "SEE_THING", "STATUS_REPORT", "WHAT_IS_IT", "BODY_STATE"}
IDIOM_WORDS = re.compile(r"секунд|минут|момент|segund|minut|moment|\bsec\b|\bsecond|\bminute", re.I)


def fill(text, lang, t):
    return MC.fill(text, lang, t) if t is not None else text


def timed_order(intent, lang, rng):
    """(said order, English, has a "mid" place) of an intent a time lasts for."""
    f = rng.choice(TIMED[intent][lang])
    said, canon = f[0], f[1]
    t = MC.draw_thing(rng, lang) if MC.SLOT.search(said) else None
    return fill(said, lang, t), fill(canon, "en", t), len(f) > 2


def say_with_time(line, lang, tm, rng, mid=False, give=False):
    """The order said with its time: at the end mostly, before it or after the first word at times (Russian)."""
    if lang == "ru":
        r = rng.random()
        if tm.ru_na and r < 0.18:
            return f"{line} на {rng.choice(tm.ru_na)}"
        phrase = rng.choice(tm.ru)
        if mid and " " in line and r < 0.5:
            first, rest = line.split(" ", 1)
            return f"{first} {phrase} {rest}"
        if r < 0.32:
            return f"{phrase} {line}"
        return f"{line} {phrase}"
    if lang == "es":
        phrase = rng.choice(tm.es)
        if rng.random() < 0.15 and not phrase.startswith(("durante", "por")):
            return f"{phrase}, {line}"
        return f"{line} {phrase}"
    phrase = rng.choice(tm.en_said)
    if give:
        return f"{line} {phrase.replace('for ', '').replace('like ', '')}"
    if rng.random() < 0.15 and phrase.startswith("for "):
        return f"{phrase} {line}"
    return f"{line} {phrase}"


def check_row(answer, wants):
    """time_phrase.find on each English line: the time each line must carry (None: no time) and a non-empty rest."""
    lines = answer.split("\n")
    if len(lines) != len(wants):
        return f"{len(lines)} lines for {len(wants)} times"
    for ln, (kind, want) in zip(lines, wants):
        got, rest = TP.find(ln)
        if want is None:
            if got is not None:
                return f"{ln!r}: a time {got} where none was said"
            continue
        if got is None:
            return f"{ln!r}: no time read"
        if got["kind"] != kind or got["more"] != bool(want.get("more")):
            return f"{ln!r}: {got} for {kind} {want}"
        for k in ("seconds", "min", "max"):
            if k in want and abs(got.get(k, -1) - min(want[k], TP.MAX_SECONDS)) > 1e-6:
                return f"{ln!r}: {got} for {want}"
        if not rest.strip():
            return f"{ln!r}: nothing left of the order"
    return None


def row(case, lang, intent, line, en, wants, rng, before=None):
    line, en = MC.affix(line, en, lang, rng)
    return {"case": case, "lang": lang, "intent": intent, "text": MC.turn(before or [], None, MC.surface(line, lang, rng)), "answer": en,
            "wants": wants}


def for_rows(rng):
    out = []
    for intent in TIMED:
        for lang, n in PER_INTENT.items():
            for _ in range(n):
                line, en, mid = timed_order(intent, lang, rng)
                give = lang == "en" and line in GIVE
                tm = time_for(rng, wait=intent == "WAIT")
                said = say_with_time(line, lang, tm, rng, mid, give)
                out.append(row("time_for", lang, intent, said, f"{en} {tm.en}", [("for", tm.want)], rng))
    return out


def any_order(lang, rng, avoid=()):
    """An order of any intent but the answers and talk, as v67's generator says it (no means)."""
    intents = [i for i in INTENTS_AFTER if i not in avoid]
    for _ in range(20):
        intent = rng.choice(intents)
        line, en, _t = MC.order(intent, lang, rng)
        if not IDIOM_WORDS.search(line) and not IDIOM_WORDS.search(en):
            return intent, line, en
    raise RuntimeError("no order")


def after_rows(rng):
    out = []
    for lang, n in AFTER_ROWS.items():
        for _ in range(n):
            intent, line, en = any_order(lang, rng)
            tm = time_after(rng)
            phrase = rng.choice(tm.ru if lang == "ru" else tm.es if lang == "es" else tm.en_said)
            counted = phrase.endswith((" и", " y", " and"))
            if counted or rng.random() < 0.75:
                said = f"{phrase} {line}"
            else:
                said = f"{line} {phrase}"
            out.append(row("time_after", lang, intent, said, f"{tm.en} {en}", [("after", tm.want)], rng))
    return out


def more_rows(rng):
    """«ещё 5 секунд» alone, or with the order it adds to; a timed order said before it at times."""
    out = []
    for lang, n in MORE_ROWS.items():
        for _ in range(n):
            tm = time_more(rng)
            phrase = rng.choice(tm.ru if lang == "ru" else tm.es if lang == "es" else tm.en_said)
            before = None
            if rng.random() < 0.5:
                intent = rng.choice(list(TIMED))
                line, en, _ = timed_order(intent, lang, rng)
                if lang == "en" and line in GIVE:
                    line, en = "wait", "wait"
                said = f"{line} {phrase}" if rng.random() < 0.7 or lang != "ru" else f"{phrase} {line}"
                answer = f"{en} {tm.en}"
            else:
                intent = "WAIT"
                said = phrase if rng.random() < 0.6 else ({"ru": "давай ", "es": "dame ", "en": "give me "}[lang] + phrase)
                answer = f"wait {tm.en}"
                if rng.random() < 0.6:
                    b_int = rng.choice(list(TIMED))
                    b_line, _e, _m = timed_order(b_int, lang, rng)
                    b_tm = time_for(rng, wait=b_int == "WAIT")
                    before = [MC.surface(say_with_time(b_line, lang, b_tm, rng), lang, rng)]
            out.append(row("time_more", lang, intent, said, answer, [("for", tm.want)], rng, before))
    return out


IDIOMS = {"ru": [("подожди минуту", "wait a minute"), ("подожди минутку", "wait a minute"), ("погоди минутку", "wait a minute"), ("минутку", "wait a minute"),
                 ("секунду", "hold on a sec"), ("секундочку", "hold on a sec"), ("погоди секунду", "hold on a sec"), ("подожди секундочку", "hold on a sec"),
                 ("одну минутку", "wait a minute"), ("сек", "hold on a sec"), ("щас, секунду", "hold on a sec"), ("момент", "wait a moment"),
                 ("погоди-ка минутку", "wait a minute"), ("стой, минутку", "wait a minute")],
          "es": [("espera un momento", "wait a moment"), ("un momento", "wait a moment"), ("un segundo", "hold on a sec"), ("espera un segundito", "hold on a sec"),
                 ("un momentito", "wait a moment"), ("aguanta un segundo", "hold on a sec"), ("espérate un momento", "wait a moment")],
          "en": [("wait a minute", "wait a minute"), ("hang on a sec", "hold on a sec"), ("just a moment", "wait a moment"), ("one sec", "hold on a sec"),
                 ("hold on a second", "hold on a sec"), ("wait a sec", "hold on a sec")]}


# Every English form above (bare and with "bro", "now", "quick", "hey", "okay") is read as WAIT by bot v67 (coop_cli, checked
# 2026-10-29). Decoder v68s was trained with "just a moment" here: the classifier reads that as GO_BACK / LOOK_AT_ME and the bot
# said "say again" to «момент», «un momento», «espera un momento»; v68s2 writes "wait a moment".


def idiom_rows(rng):
    """The idioms of waiting: no time (the owner: «подожди минуту» is "погоди"); now and then the order after them."""
    out = []
    for lang, n in IDIOM_ROWS.items():
        for _ in range(n):
            said, en = rng.choice(IDIOMS[lang])
            if rng.random() < 0.3:
                intent, line, en2 = any_order(lang, rng)
                said, en = said + rng.choice(MC.JOIN[lang]) + line, f"{en}\n{en2}"
                wants = [("for", None), ("for", None)]
            else:
                wants = [("for", None)]
            out.append(row("time_idiom", lang, "WAIT", said, en, wants, rng))
    return out


def multi_rows(rng):
    """A timed order and another one in one line («подожди 10 секунд, потом иди к двери»), either first, or both timed."""
    out = []
    for lang, n in MULTI_ROWS.items():
        for _ in range(n):
            intent = rng.choice(list(TIMED))
            line, en, mid = timed_order(intent, lang, rng)
            if lang == "en" and line in GIVE:
                line, en = "wait", "wait"
            tm = time_for(rng, wait=intent == "WAIT")
            a_said, a_en, a_want = say_with_time(line, lang, tm, rng, mid), f"{en} {tm.en}", ("for", tm.want)
            r = rng.random()
            if r < 0.25:
                i2 = rng.choice(list(TIMED))
                l2, e2, m2 = timed_order(i2, lang, rng)
                if lang == "en" and l2 in GIVE:
                    l2, e2 = "wait", "wait"
                t2 = time_for(rng, wait=i2 == "WAIT")
                b_said, b_en, b_want = say_with_time(l2, lang, t2, rng, m2), f"{e2} {t2.en}", ("for", t2.want)
            elif r < 0.4:
                i2, l2, e2 = any_order(lang, rng)
                t2 = time_after(rng)
                b_said = f"{rng.choice(t2.ru if lang == 'ru' else t2.es if lang == 'es' else t2.en_said).rstrip(' иyand').rstrip()} {l2}"
                if b_said.split()[0] in ("посчитай", "cuenta", "count"):
                    b_said = f"{rng.choice([p for p in (t2.ru if lang == 'ru' else t2.es if lang == 'es' else t2.en_said) if not p.endswith((' и', ' y', ' and'))])} {l2}"
                b_en, b_want = f"{t2.en} {e2}", ("after", t2.want)
            else:
                i2, b_said, b_en = any_order(lang, rng)
                b_want = ("for", None)
            first, second = [(a_said, a_en, a_want), (b_said, b_en, b_want)][::(1 if rng.random() < 0.7 else -1)]
            said = first[0].rstrip("?") + rng.choice(MC.JOIN[lang]) + second[0]
            out.append(row("time_multi", lang, f"{intent}+{i2}", said, f"{first[1]}\n{second[1]}", [first[2], second[2]], rng))
    return out


INTENTS_AFTER = [i for i in MC.INTENTS if i not in NOT_AFTER]


def time_rows(rng):
    """Every timer row, checked (a row whose English time_phrase reads otherwise is a bug here: it raises)."""
    rows = for_rows(rng) + after_rows(rng) + more_rows(rng) + idiom_rows(rng) + multi_rows(rng)
    bad = [(r["text"], r["answer"], check_row(r["answer"], r["wants"])) for r in rows if check_row(r["answer"], r["wants"])]
    if bad:
        for b in bad[:30]:
            print("BAD", b)
        raise SystemExit(f"{len(bad)} timer rows whose English does not say their time")
    return rows


if __name__ == "__main__":
    rows = time_rows(random.Random(6811))
    print(Counter((r["case"], r["lang"]) for r in rows))
    print(len(rows), "timer rows, every one checked by time_phrase.find")
    for r in random.Random(5).sample(rows, 40):
        print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
