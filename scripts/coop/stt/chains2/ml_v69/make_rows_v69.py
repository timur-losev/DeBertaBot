"""Round v69's decoder rows (2026-11-04, the owner: «начинай обучение»): what the owner's voice tests of 2026-10-31 .. 11-04 showed the
decoder writing wrong (chains2/ml_v68/TODO_v68.md section 5), as rows that teach the right English, in the frames he used and
in others, on the test range's things (lexicon_v68, with «софа» for the sofa).

Every answer was read by the deployed brain (bot v67, place vocabulary v15) before it went in: the intent and the place it
gives are the ones wanted (scratchpad check_answers.py, 2026-11-04). The kinds:

  door_in      «зайди / заходи / войди / пройди в X / через X» -> "go in through X" (was "flank through X"); «зайди с фланга через X»
               stays "flank through X"
  door_out     «выйди / вылези через X» -> "leave through X"; «вылези отсюда», «выйди из комнаты» -> "get out of the room"
  door_close   «закрой / закрывай / захлопни X», «закрой за собой X» -> "close X" (was "open" / "cover"); «заходи в комнату и
               закрой за собой X» -> "go inside | close X"
  lie_on       «ляг / ляж / ляш / лях / ляс / ложись / приляг на X» -> "lie down on X"; «ляжный диван» -> "lie down on the sofa";
               bare «ляж», «ляш», «прыляж» -> "lie down" (the recognizer's forms of «ляг», TODO 5b, 5k)
  sit_on       «сядь / садись / присядь на X» -> "sit down on X" (a faithful sit, not "take cover"; what it means is the owner's
               own lesson)
  get_off      «слезь / встань / спрыгни / сойди с X», «слей со стула» -> "climb down off X"
  off_then     «встань с X, сядь на Y» -> "climb down off X | sit down on Y"; «слезь ко мне» -> "jump down | come to me"
  jump_crouch  «запрыгни на X и присядь» -> "jump onto X | crouch"
  carry_dat    «отнеси его камню» (a dative with no «к») -> "carry it to the rock"
  take_carry   «возьми ящик и отнеси его камню», «подождёшь пять секунд, потом возьмёшь ящик и доставишь его камню»
  put_climb    «поставь ящик и залезь на X» -> "put the crate down | climb onto X"
  up_onto      «залезь на X наверх», «поднимись на X», after "That's X." «залезь на неё наверх» -> "climb up onto X" (was
               "... upstairs")
  back         «вернись», «вернись обратно», «возвращайся», «vuelve» -> "go back"; «вернись ко мне» -> "come back to me"
  here_stay    «иди вот сюда, встань» -> "go here | stay here"; «вот сюда встань» after another order -> "stay here"
  wall_cont    after «перепрыгни эту стену»: «через стену прям» -> "jump over this wall"
  queued_two   «когда я скажу иди к камню, ты подойдёшь к нему и запрыгнешь» -> "on my go move to the rock | jump onto the rock"
  retry        «найди путь, попробуй ещё раз» -> "try again"
  remark       «у меня получилось» -> "i made it"; «нифига себе» -> "seriously?" (no order)
  jump_follow  «перепрыгни через эту стену и беги за мной» -> "jump over this wall | follow me"
  means_from   run 2 only: «со стула залезь на X», «подставь ящик к X и залезай», «pon la silla junto a X y súbete» -> "climb onto X
               using Y" (contrast rows: run 1's get_off and put_climb lost these on test67); run 2 has no put_climb
  run 3 only (v69s2 failed 27 steps of the memory scenarios, and the owner's real lines showed more):
  statement    «этот ящик зелёный», «это верстак», «этот стол называется верстак», «нет, это камень» -> "this crate is green", "this is
               a workbench", ... (words that teach, no order)
  on_go_davai  «(запомни,) когда я скажу давай, (ты) возьмёшь ящик, потом отнеси его к X» -> "on my go pick up the crate | carry it to X"
  back_after   «вернись обратно» after «сядь на стул» -> "go back"
  here_bare    «иди сюда» -> "come here"
  remark_fail  «не получилось» -> "it didn't work"
  use_climb    «используй эту коробку, залезь на X» -> "climb onto X using this box"
  forget_thing «забудь про ящик» -> "never mind the crate" (as v68s2)
  short_after  «да», «yeah», «стой» after an order to lie or sit -> "yes", "yeah", "hold position"

Not here (the owner's call, or not the decoder's): a new intent for «иди впереди меня», «без коробки», «не бери ящик и ...», the
recognizer's junk (5f, 5g), «иди на красный стул» after a failure (the means rule), the bot's name alone.

    python make_rows_v69.py [RUN]      counts and samples (RUN 1: v69, 2: v69s2)
    fix_old_rows(rows)                 the old rows' bare «вернись» / «возвращайся» / «vuelve» written "come back" -> "go back"
"""
import io, os, random, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ml_v68"))
import lexicon_v68 as L  # noqa: E402

RU = dict(L.RU)
RU["sofa"] = RU["sofa"] + [("софа", "софу", "софы", "софе", "софой", "софе", "f", "sofa")]
L.RU = RU

# ---------------------------------------------------------------- the words around a line

RU_LEAD = ["", "", "", "брат, ", "так, ", "давай, ", "ну ", "слушай, ", "бади, ", "в общем, ", "теперь "]
RU_TAIL = ["", "", "", " брат", " быстро", " пожалуйста", " давай"]
ES_LEAD = ["", "", "tío, ", "venga, ", "oye, "]
ES_TAIL = ["", "", " tío", " por favor", " ya"]
EN_LEAD = ["", "", "hey ", "okay ", "bro ", "uh "]
EN_TAIL = ["", "", " bro", " please", " now"]
BRO = re.compile(r"\b(брат|tío|bro)\b", re.I)
# orders said before, that the line has nothing to do with (the decoder's memory carries them: TODO 5k)
BEFORE_RU = ["иди ко мне", "стой тут", "проверь стол", "возьми коробку", "открой дверь", "перепрыгни стену", "смотри налево",
             "держи угол", "покатай катушку", "встань", "иди за мной", "залезь на синий стол", "что это"]
BEFORE_ES = ["ven aquí", "quédate ahí", "abre la puerta", "sígueme", "coge la caja"]
BEFORE_EN = ["come here", "hold here", "open the door", "follow me", "pick up the box"]


def dress(line, lang, rng, lead=True, tail=True):
    """A line as said: a word to the bot before it or after it, its case and its full stop as the recognizer writes them."""
    if lang == "ru":
        a, b = (rng.choice(RU_LEAD) if lead else ""), (rng.choice(RU_TAIL) if tail else "")
    elif lang == "es":
        a, b = (rng.choice(ES_LEAD) if lead else ""), (rng.choice(ES_TAIL) if tail else "")
    else:
        a, b = (rng.choice(EN_LEAD) if lead else ""), (rng.choice(EN_TAIL) if tail else "")
    s = a + line + b
    if rng.random() < 0.6:
        s = s[0].upper() + s[1:] + rng.choice([".", ".", "!", ""])
    return s


def answer(parts, said):
    """The answer's lines; "bro" at the end of the last when the line calls the bot so."""
    out = list(parts)
    if BRO.search(said):
        out[-1] += " bro"
    return "\n".join(out)


def row(case, lang, line, parts, rng, before=None, bot=None, dressed=True, lead=True, tail=True):
    said = dress(line, lang, rng, lead, tail) if dressed else line
    text = []
    for b in before or []:
        text.append(f"before: {b}")
    if bot:
        text.append(f"bot: {bot}")
    text.append(f"now: {said}")
    return {"case": case, "lang": lang, "text": "\n".join(text), "answer": answer(parts, said)}


def maybe_before(lang, rng, p=0.25):
    if rng.random() >= p:
        return None
    pool = {"ru": BEFORE_RU, "es": BEFORE_ES, "en": BEFORE_EN}[lang]
    return rng.sample(pool, rng.choice([1, 1, 2]))


def ru_with(word):
    """«с» or «со» before a Russian word («со стула», «с дивана»)."""
    return "со" if re.match(r"(с[тпкмвлн]|з[вл]|вс|щ)", word) else "с"


def thing(obj, rng, qual="any"):
    return L.thing(obj, rng, qual)


DOOR_QUALS = ["main", "main", "main", "north", "south", "east", "west", None]
SIT_ON = ["sofa", "sofa", "sofa", "chair", "chair", "bed", "bed", "table"]       # the crate reads as a jump, not a sit
LIE_ON = ["sofa", "sofa", "sofa", "bed", "bed", "table", "chair", "rock", "crate"]
OFF = ["sofa", "sofa", "chair", "chair", "bed", "table", "crate", "rock", "spool"]
ONTO = ["bed", "bed", "table", "table", "chair", "sofa", "rock", "crate", "spool"]
TO = ["rock", "rock", "table", "table", "bed", "chair", "sofa", "door", "stairs"]
# what is carried: the words, the English, the pronoun after it («коробку ... отнеси её»)
ITEM_RU = [("ящик", "the crate", "его"), ("коробку", "the box", "её"), ("этот ящик", "this crate", "его"), ("эту коробку", "this box", "её"),
           ("ящика", "the crate", "его")]
NUM_RU = [("две", 2), ("три", 3), ("пять", 5), ("десять", 10), ("пару", 2), ("четыре", 4), ("семь", 7)]


# ---------------------------------------------------------------- the kinds

def door_in(rng, out):
    for _ in range(170):
        q = rng.choice(DOOR_QUALS)
        t, te = thing("door", rng, q)
        v = rng.choice(["зайди", "заходи", "войди", "входи", "пройди", "проходи", "зайди-ка"])
        frames = ["{v} через {a}", "{v} в комнату через {a}", "{v} внутрь через {a}", "{v} туда через {a}"]
        if t.en_word == "door":     # «в дверь»; «во вход» is not said
            frames += ["{v} в {a}", "{v} в {a}"]
        out.append(row("door_in", "ru", rng.choice(frames).format(v=v, a=t.ru["acc"]), [f"go in through {t.en}"], rng, maybe_before("ru", rng)))
    for _ in range(25):        # the crosshair on it
        v = rng.choice(["зайди", "заходи", "войди", "пройди"])
        out.append(row("door_in", "ru", f"{v} через эту дверь", ["go in through this door"], rng))
    for _ in range(30):        # with a flank it stays a flank
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        v = rng.choice(["зайди", "заходи"])
        out.append(row("door_in", "ru", f"{v} с фланга через {t.ru['acc']}", [f"flank through {t.en}"], rng))
    for _ in range(50):
        q = rng.choice(DOOR_QUALS)
        _, te = thing("door", rng, q)
        v = rng.choice(["entra por", "métete por", "pasa por", "entra en la habitación por"])
        out.append(row("door_in", "es", f"{v} {te.es['T']}", [f"go in through {te.en}"], rng, maybe_before("es", rng)))
    for _ in range(30):
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        v = rng.choice(["get inside through", "head in through", "walk in through", "go into the room through", "step in through"])
        out.append(row("door_in", "en", f"{v} {t.en}", [f"go in through {t.en}"], rng, maybe_before("en", rng)))


def door_out(rng, out):
    for _ in range(130):
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        v = rng.choice(["выйди", "выходи", "вылези", "вылезай", "выйди-ка"])
        frame = rng.choice(["{v} через {a}", "{v} отсюда через {a}", "{v} оттуда через {a}", "{v} из комнаты через {a}", "{v} наружу через {a}"])
        out.append(row("door_out", "ru", frame.format(v=v, a=t.ru["acc"]), [f"leave through {t.en}"], rng, maybe_before("ru", rng)))
    for _ in range(60):
        line = rng.choice(["вылези отсюда", "вылези отсюда вообще, выйди", "выйди из комнаты", "выйди наружу", "выходи из комнаты",
                           "вылезай отсюда", "выйди отсюда вообще", "выбирайся из комнаты", "выйди из этой комнаты"])
        out.append(row("door_out", "ru", line, ["get out of the room"], rng))
    for _ in range(35):
        q = rng.choice(DOOR_QUALS)
        _, te = thing("door", rng, q)
        out.append(row("door_out", "es", f"{rng.choice(['sal por', 'sal de aquí por', 'sal de la habitación por'])} {te.es['T']}", [f"leave through {te.en}"], rng))
    for _ in range(15):
        out.append(row("door_out", "es", rng.choice(["sal de la habitación", "sal de esta habitación", "sal fuera de la habitación"]), ["get out of the room"], rng))
    for _ in range(20):
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        out.append(row("door_out", "en", f"{rng.choice(['get out through', 'exit via', 'go out through', 'walk out through'])} {t.en}", [f"leave through {t.en}"], rng))


def door_close(rng, out):
    for _ in range(150):
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        v = rng.choice(["закрой", "закрывай", "захлопни", "закрой-ка"])
        frame = rng.choice(["{v} {a}", "{v} {a}", "{v} за собой {a}", "{v} {a} за собой"])
        out.append(row("door_close", "ru", frame.format(v=v, a=t.ru["acc"]), [f"close {t.en}"], rng, maybe_before("ru", rng)))
    for _ in range(40):
        v = rng.choice(["закрой", "закрывай", "захлопни"])
        line, ans = rng.choice([(f"{v} эту дверь", "close this door"), (f"{v} дверь", "close the door"), (f"{v} за собой дверь", "close the door"),
                                (f"{v} дверь за собой", "close the door")])
        out.append(row("door_close", "ru", line, [ans], rng))
    for _ in range(25):        # the door named before: «закрой её»
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        before = [rng.choice([f"иди к {t.ru['dat']}", f"открой {t.ru['acc']}", f"зайди через {t.ru['acc']}"])]
        pron = L.RU_PRON[t.ru_gender]["acc"][0]
        out.append(row("door_close", "ru", f"{rng.choice(['закрой', 'закрывай'])} {pron}", [f"close {t.en}"], rng, before))
    for _ in range(60):        # in, then shut it
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        line, parts = rng.choice([
            (f"заходи в комнату и закрой за собой {t.ru['acc']}", ["go inside", f"close {t.en}"]),
            (f"зайди внутрь и закрой {t.ru['acc']}", ["go inside", f"close {t.en}"]),
            (f"зайди через {t.ru['acc']} и закрой {L.RU_PRON[t.ru_gender]['acc'][0]}", [f"go in through {t.en}", f"close {t.en}"]),
            (f"заходи туда в комнату и закрой за собой {t.ru['acc']}", ["go inside", f"close {t.en}"]),
            (f"войди и закрой за собой {t.ru['acc']}", ["go inside", f"close {t.en}"])])
        out.append(row("door_close", "ru", line, parts, rng))
    for _ in range(35):
        q = rng.choice(DOOR_QUALS)
        _, te = thing("door", rng, q)
        out.append(row("door_close", "es", f"{rng.choice(['cierra', 'cierra bien'])} {te.es['T']}", [f"close {te.en}"], rng))
    for _ in range(25):
        q = rng.choice(DOOR_QUALS)
        t, _ = thing("door", rng, q)
        out.append(row("door_close", "en", f"{rng.choice(['shut', 'shut', 'close up'])} {t.en}", [f"close {t.en}"], rng))


LIE_RU = ["ляг", "ляг", "ляжь", "ляж", "ляш", "лях", "ляс", "ложись", "приляг", "заляг"]


def lie_on(rng, out):
    for _ in range(230):
        obj = rng.choice(LIE_ON)
        t, _ = thing(obj, rng)
        v = rng.choice(LIE_RU)
        frame = rng.choice(["{v} на {a}", "{v} на {a}", "вот {n}, {v} на {p}", "{v} на {a} тоже", "{v} на {a} и лежи"])
        pron = L.RU_PRON[t.ru_gender]["acc"][1]
        line = frame.format(v=v, a=t.ru["acc"], n=t.ru["nom"], p=pron)
        ans = f"lie down on {t.en}" + (" too" if line.endswith("тоже") else "")
        out.append(row("lie_on", "ru", line, [ans], rng, maybe_before("ru", rng)))
    for _ in range(25):        # the floor
        v = rng.choice(LIE_RU)
        out.append(row("lie_on", "ru", f"{v} на пол", ["lie down on the floor"], rng))
    for _ in range(25):        # «ляжный диван»: «ляг на диван» as the recognizer heard it
        obj = rng.choice(["sofa", "sofa", "bed"])
        t, _ = thing(obj, rng, None)
        adj = rng.choice(["ляжный", "ляшный", "ляжная", "ляшная"]) if t.ru_gender == "f" else rng.choice(["ляжный", "ляшный"])
        if t.ru_gender == "f":
            adj = adj[:-2] + "ая"
        out.append(row("lie_on", "ru", f"{adj} {t.ru['nom']}", [f"lie down on {t.en}"], rng, tail=False))
    for _ in range(60):        # alone
        v = rng.choice(["ляг", "ляж", "ляш", "лях", "приляг", "прыляж", "заляг", "ложись", "ляжь", "ляг тут", "приляг тут"])
        ans = "lie down here" if v.endswith("тут") else "lie down"
        out.append(row("lie_on", "ru", v, [ans], rng))
    for _ in range(45):
        obj = rng.choice(LIE_ON)
        _, te = thing(obj, rng)
        v = rng.choice(["túmbate en", "acuéstate en", "échate en", "túmbate encima de"])
        es_t = te.es["T"] if not v.endswith("de") else te.es["T:de"].split(" ", 1)[1] if te.es["T:de"].startswith("de ") else te.es["T:de"]
        line = f"{v} {te.es['T']}" if not v.endswith("de") else f"túmbate encima {te.es['T:de']}"
        out.append(row("lie_on", "es", line, [f"lie down on {te.en}"], rng))
    for _ in range(25):
        obj = rng.choice(LIE_ON)
        t, _ = thing(obj, rng)
        out.append(row("lie_on", "en", f"{rng.choice(['lay down on', 'lie on', 'get down and lie on', 'go prone on'])} {t.en}", [f"lie down on {t.en}"], rng))


def sit_on(rng, out):
    for _ in range(150):
        obj = rng.choice(SIT_ON)
        t, _ = thing(obj, rng)
        v = rng.choice(["сядь", "садись", "присядь", "сядь-ка", "посиди"])
        pron = L.RU_PRON[t.ru_gender]["acc"][1]
        frame = rng.choice(["{v} на {a}", "{v} на {a}", "{v}, {v} на {a}", "вот {n}, {v} на {p}", "вот {n} {v} на {p}"])
        out.append(row("sit_on", "ru", frame.format(v=v, a=t.ru["acc"], n=t.ru["nom"], p=pron), [f"sit down on {t.en}"], rng, maybe_before("ru", rng)))
    for _ in range(40):
        obj = rng.choice(SIT_ON)
        _, te = thing(obj, rng)
        out.append(row("sit_on", "es", f"{rng.choice(['siéntate en', 'siéntate encima de', 'ponte sentado en'])} {te.es['T']}".replace("de el ", "del "),
                       [f"sit down on {te.en}"], rng))
    for _ in range(20):
        obj = rng.choice(SIT_ON)
        t, _ = thing(obj, rng)
        out.append(row("sit_on", "en", f"{rng.choice(['sit on', 'have a seat on', 'take a seat on'])} {t.en}", [f"sit down on {t.en}"], rng))


OFF_RU = ["слезь", "слезь", "слезай", "встань", "вставай", "спрыгни", "сойди", "слей", "слезь-ка"]


def get_off(rng, out):
    for _ in range(180):
        obj = rng.choice(OFF)
        t, _ = thing(obj, rng)
        v = rng.choice(OFF_RU)
        g = t.ru["gen"]
        frame = rng.choice(["{v} {w} {g}", "{v} {w} {g}", "{v} {w} {g} на пол", "{v} {w} {g} уже"])
        out.append(row("get_off", "ru", frame.format(v=v, w=ru_with(g), g=g), [f"climb down off {t.en}"], rng, maybe_before("ru", rng)))
    for _ in range(40):
        obj = rng.choice(OFF)
        _, te = thing(obj, rng)
        out.append(row("get_off", "es", f"{rng.choice(['bájate', 'baja', 'quítate', 'levántate'])} {te.es['T:de']}", [f"climb down off {te.en}"], rng))
    for _ in range(20):
        obj = rng.choice(OFF)
        t, _ = thing(obj, rng)
        out.append(row("get_off", "en", f"{rng.choice(['get off', 'get down from', 'step off', 'get up off'])} {t.en}", [f"climb down off {t.en}"], rng))


def off_then(rng, out):
    for _ in range(60):
        a = rng.choice(["sofa", "bed", "chair", "table"])
        b = rng.choice([o for o in SIT_ON if o != a])
        ta, _ = thing(a, rng)
        tb, _ = thing(b, rng)
        g = ta.ru["gen"]
        v1 = rng.choice(["встань", "слезь", "вставай", "слезай"])
        sep = rng.choice([", ", " и ", ", потом ", " и потом "])
        out.append(row("off_then", "ru", f"{v1} {ru_with(g)} {g}{sep}{rng.choice(['сядь', 'садись', 'присядь'])} на {tb.ru['acc']}",
                       [f"climb down off {ta.en}", f"sit down on {tb.en}"], rng))
    for _ in range(30):
        a = rng.choice(OFF)
        ta, _ = thing(a, rng)
        g = ta.ru["gen"]
        out.append(row("off_then", "ru", f"{rng.choice(['слезь', 'спрыгни', 'слезай'])} {ru_with(g)} {g} и {rng.choice(['иди ко мне', 'беги ко мне', 'подойди ко мне'])}",
                       [f"climb down off {ta.en}", "come to me"], rng))
    for _ in range(35):
        line = rng.choice(["слезь ко мне", "ко мне, ко мне, слезь ко мне", "спрыгни ко мне", "слезай ко мне", "ко мне, слезь ко мне",
                           "слезь и иди ко мне", "спускайся ко мне"])
        out.append(row("off_then", "ru", line, ["jump down", "come to me"], rng))


def jump_crouch(rng, out):
    for _ in range(60):
        obj = rng.choice(ONTO)
        t, _ = thing(obj, rng)
        v = rng.choice(["запрыгни", "залезь", "заберись"])
        c = rng.choice(["присядь", "сядь", "пригнись", "присядь там"])
        out.append(row("jump_crouch", "ru", f"{v} на {t.ru['acc']} и {c}", [f"jump onto {t.en}", "crouch"], rng))


def carry_dat(rng, out):
    for _ in range(200):
        obj = rng.choice(TO)
        t, _ = thing(obj, rng)
        v = rng.choice(["отнеси", "отнеси", "неси", "доставь", "оттащи", "унеси", "отвези", "отнеси-ка"])
        to = (rng.choice(["к ", "к "]) if rng.random() < 0.3 else "")
        to = "ко " if to and re.match(r"(вс|мн)", t.ru["dat"]) else to
        item, item_en = rng.choice([("его", "it"), ("её", "it"), ("это", "it")] + [(i, e.replace("this ", "the ")) for i, e, _ in ITEM_RU[:4]])
        out.append(row("carry_dat", "ru", f"{v} {item} {to}{t.ru['dat']}", [f"carry {item_en} to {t.en}"], rng, maybe_before("ru", rng)))


def take_carry(rng, out):
    for _ in range(70):
        obj = rng.choice(TO)
        t, _ = thing(obj, rng)
        item, item_en, it = rng.choice(ITEM_RU)
        to = "к " if rng.random() < 0.3 else ""
        v1, v2 = rng.choice([("возьми", "отнеси"), ("возьми", "доставь"), ("подними", "отнеси"), ("бери", "неси"), ("хватай", "тащи")])
        sep = rng.choice([" и ", ", ", " и потом ", ", потом "])
        out.append(row("take_carry", "ru", f"{v1} {item}{sep}{v2} {it} {to}{t.ru['dat']}", [f"pick up {item_en}", f"carry it to {t.en}"], rng))
    for _ in range(50):        # the future of the owner's «ты подождёшь ..., потом возьмёшь ... и доставишь его камню»
        obj = rng.choice(TO)
        t, _ = thing(obj, rng)
        item, item_en, it = rng.choice(ITEM_RU)
        w, n = rng.choice(NUM_RU)
        unit = "секунды" if n in (2, 3, 4) and w != "пару" else "секунд"
        to = "к " if rng.random() < 0.3 else ""
        line = (f"ты подождёшь {w} {unit}, потом возьмёшь {item} и {rng.choice(['доставишь', 'отнесёшь'])} {it} {to}{t.ru['dat']}"
                if rng.random() < 0.5 else
                f"подожди {w} {unit}, потом возьми {item} и {rng.choice(['доставь', 'отнеси'])} {it} {to}{t.ru['dat']}")
        out.append(row("take_carry", "ru", line, [f"wait for {n} seconds", f"pick up {item_en}", f"carry it to {t.en}"], rng))


def put_climb(rng, out):
    for _ in range(80):
        obj = rng.choice(ONTO[:-2])
        t, _ = thing(obj, rng)
        item, item_en = rng.choice([(i, e) for i, e, _ in ITEM_RU[:4]] + [("его", "it"), ("её", "it")])
        v1 = rng.choice(["поставь", "положи", "опусти", "брось"])
        v2 = rng.choice(["залезь", "запрыгни", "заберись"])
        sep = rng.choice([" и ", ", потом ", " и потом "])
        first = "put it down" if item_en == "it" else f"put {item_en.replace('this ', 'the ')} down"
        out.append(row("put_climb", "ru", f"{v1} {item}{sep}{v2} на {t.ru['acc']}", [first, f"climb onto {t.en}"], rng))


def up_onto(rng, out):
    for _ in range(110):
        obj = rng.choice(ONTO)
        t, _ = thing(obj, rng)
        v = rng.choice(["залезь", "залез", "забирайся", "заберись", "запрыгни", "полезай"])
        frame = rng.choice(["{v} на {a} наверх", "{v} наверх на {a}", "{v} на {a} наверх", "поднимись на {a}", "{v} на самый верх {g}"])
        line = frame.format(v=v, a=t.ru["acc"], g=t.ru["gen"])
        out.append(row("up_onto", "ru", line, [f"climb up onto {t.en}"], rng, maybe_before("ru", rng)))
    for _ in range(40):        # "this": the crosshair on it
        obj = rng.choice(ONTO)
        t, _ = thing(obj, rng, None)
        this = {"m": "этот", "f": "эту", "n": "это", "p": "эти"}[t.ru_gender]
        v = rng.choice(["залезь", "залез", "заберись", "запрыгни"])
        line = rng.choice([f"вот на {this} {t.ru['acc']} {v} наверх", f"{v} на {this} {t.ru['acc']} наверх", f"{v} наверх на {this} {t.ru['acc']}"])
        out.append(row("up_onto", "ru", line, [f"climb onto this {t.en_word}"], rng))
    for _ in range(60):        # after the bot said what it is: «залезь на неё наверх»
        obj = rng.choice(ONTO)
        t, _ = thing(obj, rng)
        pron = L.RU_PRON[t.ru_gender]["acc"][1]
        v = rng.choice(["залезь", "залез", "залез, залезь", "заберись", "запрыгни"])
        line = rng.choice([f"{v} на {pron} наверх", f"{v} на {pron}", f"{v} наверх на {pron}"])
        said = "the " + (f"{t.qual} " if t.qual else "") + obj.replace("_", " ")   # the brain's own words for it (coop_cli: own)
        out.append(row("up_onto", "ru", line, [f"climb up onto {said}"], rng, before=["что это"], bot=f"That's {said}."))
    for _ in range(25):
        obj = rng.choice(ONTO)
        _, te = thing(obj, rng)
        out.append(row("up_onto", "es", f"{rng.choice(['súbete a', 'súbete encima de', 'trepa a'])} {te.es['T']}".replace("a el ", "al ").replace("de el ", "del "),
                       [f"climb up onto {te.en}"], rng))


def back(rng, out):
    for _ in range(80):
        line = rng.choice(["вернись", "вернись обратно", "вернись назад", "возвращайся", "возвращайся обратно", "вернись туда", "туда вернись",
                           "иди обратно", "вернись на место", "вернись обратно туда"])
        ans = "go back to your spot" if line.endswith("место") else "go back"
        out.append(row("back", "ru", line, [ans], rng, maybe_before("ru", rng, 0.4)))
    for _ in range(40):
        line = rng.choice(["вернись ко мне", "вернись сюда", "возвращайся ко мне", "вернись обратно ко мне", "возвращайся сюда"])
        out.append(row("back", "ru", line, ["come back to me"], rng))
    for _ in range(30):
        line, ans = rng.choice([("vuelve", "go back"), ("regresa", "go back"), ("vuelve atrás", "go back"), ("regresa allí", "go back"),
                                ("vuelve aquí", "come back to me"), ("vuelve conmigo", "come back to me"), ("regresa aquí", "come back to me")])
        out.append(row("back", "es", line, [ans], rng))


def here_stay(rng, out):
    for _ in range(40):
        line = rng.choice(["иди вот сюда, встань", "иди сюда и встань", "подойди сюда и стой", "иди вот сюда встань", "иди сюда и стой тут",
                           "подойди вот сюда и встань"])
        out.append(row("here_stay", "ru", line, ["go here", "stay here"], rng))
    for _ in range(40):        # after another order: the line is its own
        line = rng.choice(["вот сюда встань", "а и сюда, вот сюда встань", "встань вот сюда", "сюда встань", "вот тут встань"])
        before = [rng.choice(["покатай стену", "перепрыгни через стену", "толкни коробку", "покатай катушку", "проверь окно"])]
        out.append(row("here_stay", "ru", line, ["stay here"], rng, before=before))


def wall_cont(rng, out):
    for _ in range(50):
        before = [rng.choice(["перепрыгни эту стену", "перепрыгни через стену", "перепрыгни стену", "давай перепрыгни эту стенку"])]
        line = rng.choice(["через стену прям", "прям через неё", "через стену давай", "да через стену", "прямо через стенку", "через неё прыгай"])
        out.append(row("wall_cont", "ru", line, ["jump over this wall"], rng, before=before))


def queued_two(rng, out):
    for _ in range(60):
        obj = rng.choice(["rock", "rock", "table", "bed", "chair", "sofa"])
        t, _ = thing(obj, rng)
        pron = L.RU_PRON[t.ru_gender]["dat"][1]
        pron_acc = L.RU_PRON[t.ru_gender]["acc"][1]
        line = rng.choice([
            f"когда я скажу иди к {t.ru['dat']}, ты подойдёшь к {pron} и запрыгнешь",
            f"когда я скажу, подойди к {t.ru['dat']} и запрыгни на {pron_acc}",
            f"по моей команде подойди к {t.ru['dat']} и залезь на {pron_acc}",
            f"когда скажу, иди к {t.ru['dat']} и запрыгни на {pron_acc}"])
        out.append(row("queued_two", "ru", line, [f"on my go move to {t.en}", f"jump onto {t.en}"], rng, lead=False))


def retry(rng, out):
    for _ in range(50):
        line = rng.choice(["найди путь, попробуй ещё раз", "попробуй ещё раз", "давай ещё раз попробуй", "попробуй снова",
                           "ещё раз попробуй найти путь", "найди дорогу и попробуй ещё раз", "попробуй-ка ещё раз"])
        out.append(row("retry", "ru", line, ["try again"], rng, maybe_before("ru", rng, 0.5)))


def remark(rng, out):
    for _ in range(45):
        line = rng.choice(["у меня получилось", "но у меня получилось", "у меня получилось всё", "я смог", "получилось у меня",
                           "смотри, у меня получилось", "а у меня получилось"])
        out.append(row("remark", "ru", line, ["i made it"], rng, maybe_before("ru", rng, 0.5), tail=False))
    for _ in range(40):
        line = rng.choice(["нифига себе", "ничего себе", "офигеть", "вот это да", "ни фига себе", "ого, ничего себе", "обалдеть"])
        out.append(row("remark", "ru", line, ["seriously?"], rng, maybe_before("ru", rng, 0.5), tail=False))
    for _ in range(15):
        line, ans = rng.choice([("lo logré", "i made it"), ("me ha salido", "i made it"), ("¡no me digas!", "seriously?"), ("¿en serio?", "seriously?")])
        out.append(row("remark", "es", line, [ans], rng))


def jump_follow(rng, out):
    for _ in range(40):
        line = rng.choice(["теперь перепрыгни через эту стену и беги за мной", "перепрыгни через эту стену и иди за мной",
                           "перепрыгни стену и беги за мной", "перепрыгни через стенку и давай за мной", "перепрыгни через стену, потом за мной"])
        out.append(row("jump_follow", "ru", line, ["jump over this wall", "follow me"], rng, lead=False))


def means_carry(rng, out):
    """"Using A and B, bring the box to C" (TODO 5i): the box goes to C, A and B are the way there (the decoder had swapped the box
    and the place)."""
    for _ in range(70):
        objs = rng.sample(["table", "table", "chair", "bed", "rock", "sofa"], 3)
        ta, tb, tc = (thing(o, rng)[0] for o in objs)
        if len({ta.en, tb.en, tc.en}) < 3:
            continue
        item, item_en = rng.choice([("коробку", "the box"), ("ящик", "the crate"), ("эту коробку", "this box")])
        lang = rng.choice(["en", "en", "ru"])
        two = rng.random() < 0.6
        means_en = f"{ta.en} and {tb.en}" if two else ta.en
        if lang == "en":
            verb = rng.choice(["bring", "carry", "take"])
            item_e = rng.choice(["the box", "the crate", "this box"])
            line = rng.choice([f"using {means_en}, {verb} {item_e} to {tc.en}", f"{verb} {item_e} to {tc.en} using {means_en}",
                               f"use {means_en} to {verb} {item_e} on top of {tc.en}"])
            ans = f"{verb} {item_e} {'on top of' if 'on top of' in line else 'to'} {tc.en} using {means_en}"
        else:
            means_ru = f"{ta.ru['gen']} и {tb.ru['gen']}" if two else ta.ru["gen"]
            line = rng.choice([f"с помощью {means_ru} отнеси {item} на {tc.ru['acc']}", f"отнеси {item} на {tc.ru['acc']} через {ta.ru['acc']}" if not two
                               else f"по {ta.ru['dat']} и {tb.ru['dat']} отнеси {item} на {tc.ru['acc']}"])
            ans = f"bring {item_en} to {tc.en} using {means_en}"
        out.append(row("means_carry", lang, line, [ans], rng))


CLIMB_RU = ["залезь", "залезай", "запрыгни", "заберись", "забирайся", "лезь"]
STEP = ["chair", "chair", "sofa", "crate", "crate", "table", "bed", "rock", "spool", "car"]
STEP_ONTO = ["table", "table", "bed", "bed", "car", "tree", "rock", "crate", "chair"]


def from_ru(t):
    """«со стула», «с дивана», «с крыши тачки» (a car is stood on by its roof)."""
    if t.en.endswith("car"):
        return "с крыши " + t.ru["gen"]
    return f"{ru_with(t.ru['gen'])} {t.ru['gen']}"


def means_from(rng, out):
    """Run 2's contrast rows (2026-11-04): a thing said with «с / со» before a climb, «подставь X», «pon X ... y súbete» are the step,
    "using X", as the rounds before taught (v69's first run, with get_off and put_climb, lost that on test67: «со стула залезь на
    белый стол», «подставь ящик к белому столу, залезай на стол», «pon una caja debajo de la ventana y cuélate»)."""
    for _ in range(150):
        step = rng.choice(STEP)
        ts, _ = thing(step, rng)
        kind = rng.random()
        if kind < 0.2:                                         # into a window
            v = rng.choice(["залезай", "залезь", "лезь", "пролезь", "заберись"])
            line = rng.choice([f"{from_ru(ts)} {v} в окно", f"{v} в окно {from_ru(ts)}"])
            ans = f"get in the window using {ts.en}"
        elif kind < 0.3:                                       # over a fence
            tf, _ = thing("fence", rng)
            line = rng.choice([f"{from_ru(ts)} перепрыгни через {tf.ru['acc']}", f"перемахни через {tf.ru['acc']} {from_ru(ts)}"])
            ans = f"jump over {tf.en} using {ts.en}"
        else:                                                  # onto a thing
            onto = rng.choice([o for o in STEP_ONTO if o != step])
            to, _ = thing(onto, rng)
            v = rng.choice(CLIMB_RU)
            line = rng.choice([f"{from_ru(ts)} {v} на {to.ru['acc']}", f"{v} на {to.ru['acc']} {from_ru(ts)}"])
            ans = f"climb onto {to.en} using {ts.en}"
        out.append(row("means_from", "ru", line, [ans], rng, maybe_before("ru", rng)))
    for _ in range(70):                                        # «подставь X (к Y) и залезь»
        step = rng.choice(["crate", "crate", "chair", "table", "sofa", "spool"])
        ts, _ = thing(step, rng)
        onto = rng.choice([o for o in ["table", "bed", "car", "tree", "rock", "fence"] if o != step])
        to, _ = thing(onto, rng)
        pron = L.RU_PRON[to.ru_gender]["acc"][1]
        v = rng.choice(CLIMB_RU)
        if onto == "fence":
            line = rng.choice([f"перемахни через {to.ru['acc']}, {ts.ru['acc']} подставь", f"подставь {ts.ru['acc']} и перепрыгни через {to.ru['acc']}"])
            ans = f"jump over {to.en} using {ts.en}"
        else:
            line = rng.choice([f"подставь {ts.ru['acc']} к {to.ru['dat']} и {v} на {pron}", f"подставь {ts.ru['acc']} к {to.ru['dat']}, {v} на {to.ru['acc']}",
                               f"подставь {ts.ru['acc']} и {v} на {to.ru['acc']}", f"{v} на {to.ru['acc']}, {ts.ru['acc']} подставь"])
            ans = f"climb onto {to.en} using {ts.en}"
        out.append(row("means_from", "ru", line.replace("к вс", "ко вс"), [ans], rng))
    for _ in range(60):                                        # «pon X junto a Y y súbete», «pon X debajo de la ventana y cuélate»
        step = rng.choice(["crate", "crate", "chair", "table", "sofa", "spool"])
        _, es_s = thing(step, rng)
        if rng.random() < 0.3:
            _, es_w = thing("window", rng)
            line = f"pon {es_s.es['T']} debajo {es_w.es['T:de']} y {rng.choice(['cuélate', 'métete', 'entra', 'súbete y entra'])}"
            ans = f"get in the window using {es_s.en}"
        else:
            onto = rng.choice([o for o in ["table", "bed", "car", "rock", "tree"] if o != step])
            _, es_o = thing(onto, rng)
            line = rng.choice([f"pon {es_s.es['T']} junto {es_o.es['T:a']} y súbete", f"pon {es_s.es['T']} y súbete {es_o.es['T:a']}",
                               f"súbete {es_o.es['T:a']} desde {es_s.es['T']}"])
            ans = f"climb onto {es_o.en} using {es_s.en}"
        out.append(row("means_from", "es", re.sub(r"\bde el\b", "del", re.sub(r"\ba el\b", "al", line)), [ans], rng))


KINDS = (means_carry, door_in, door_out, door_close, lie_on, sit_on, get_off, off_then, jump_crouch, carry_dat, take_carry, put_climb, up_onto,
         back, here_stay, wall_cont, queued_two, retry, remark, jump_follow)
# run 2 (v69s2): no put_climb (it said the opposite of the rounds before: «поставь X и залезь на Y» is "climb onto Y using X"), and the
# contrast rows of means_from
KINDS_2 = tuple(k for k in KINDS if k is not put_climb) + (means_from,)


# ---------------------------------------------------------------- run 3 (2026-11-04): what v69s2 lost on the memory scenarios

sys.path.insert(0, os.path.join(HERE, "..", "ml_v67"))
import lexicon_v67 as L67  # noqa: E402

# colours a player teaches (any colour, not the vocabulary's qualifiers): English, the Russian stem and its ending type
COLOURS = [("green", "зелён", "hard"), ("red", "красн", "hard"), ("blue", "син", "soft"), ("yellow", "жёлт", "hard"), ("white", "бел", "hard"),
           ("black", "чёрн", "hard"), ("grey", "сер", "hard"), ("orange", "оранжев", "hard"), ("brown", "коричнев", "hard"),
           ("pink", "розов", "hard"), ("purple", "фиолетов", "hard")]
# names a player gives a thing: the Russian word, its English (none the place vocabulary knows: "chest" is a crate, "target" an enemy)
NAMES = [("верстак", "workbench"), ("фонарь", "lantern"), ("тумба", "nightstand"), ("склад", "storeroom"),
         ("гараж", "garage"), ("полка", "shelf"), ("бочка", "barrel"), ("шкаф", "cupboard"), ("табурет", "stool"), ("пень", "stump"),
         ("лавка", "bench"), ("пьедестал", "pedestal"), ("подставка", "stand"), ("лежанка", "couch")]
TAUGHT = ["crate", "crate", "table", "table", "chair", "sofa", "bed", "rock", "spool", "door", "fence", "car"]   # not "target" (an enemy), not
# the stairs ("that's a stairs" walks there)
THIS_RU = {"m": "этот", "f": "эта", "n": "это", "p": "эти"}


def colour_ru(stem, kind, gender):
    return stem + L67._ADJ[kind][gender][0]


def statement(rng, out):
    """Words that teach, not orders (the owner teaches names and colours: [[teach-not-built-in]]; the memory reads the line itself,
    and needs the brain not to act on it): «этот ящик зелёный» -> "this crate is green", «это верстак» -> "this is a workbench",
    «этот стол называется верстак», «нет, это камень», after an order about the same thing or after the bot said what it is. v69s2
    wrote "pick up the green crate", "climb onto the crate"."""
    for _ in range(330):
        obj = rng.choice(TAUGHT)
        t, _ = thing(obj, rng, None)
        word = t.en_word
        kind = rng.random()
        before, bot = maybe_before("ru", rng, 0.2), None
        if kind < 0.3:                                             # a colour
            en_c, stem, typ = rng.choice(COLOURS)
            c = colour_ru(stem, typ, t.ru_gender)
            line = rng.choice([f"{THIS_RU[t.ru_gender]} {t.ru['nom']} {c}", f"{t.ru['nom']} {c}", f"{THIS_RU[t.ru_gender]} {t.ru['nom']} вообще-то {c}",
                               f"запомни, {THIS_RU[t.ru_gender]} {t.ru['nom']} {c}"])
            ans = f"this {word} is {en_c}"
            if rng.random() < 0.35:                                # said right after an order about it
                before = [rng.choice([f"возьми {t.ru['acc']}", f"иди к {t.ru['dat']}", f"вот {ru_adj_any(rng, t)} {t.ru['acc']} возьми",
                                      f"проверь {t.ru['acc']}", f"залезь на {t.ru['acc']}"])]
        elif kind < 0.5:                                           # a name
            name, en_n = rng.choice(NAMES)
            line = rng.choice([f"это {name}", f"это у нас {name}", f"вот это {name}", f"это называется {name}"])
            ans = rng.choice([f"this is a {en_n}", f"that's a {en_n}"]) if "называется" not in line else f"this is called a {en_n}"
        elif kind < 0.65:                                          # a thing called so
            name, en_n = rng.choice(NAMES)
            line = rng.choice([f"{THIS_RU[t.ru_gender]} {t.ru['nom']} называется {name}", f"{t.ru['nom']} называется {name}"])
            ans = f"this {word} is called a {en_n}"
        elif kind < 0.8:                                           # what kind of thing it is, with a colour
            en_c, stem, typ = rng.choice(COLOURS)
            line = f"это {colour_ru(stem, typ, t.ru_gender)} {t.ru['nom']}"
            ans = f"this is the {en_c} {word}"
        else:                                                      # after "what is that?" and the bot's answer: not that, this
            other_obj = rng.choice([o for o in TAUGHT if o != obj])
            said = "the " + other_obj.replace("_", " ")
            before, bot = ["что это"], f"That's {said}."
            if rng.random() < 0.5:
                name, en_n = rng.choice(NAMES)
                line, ans = rng.choice([(f"нет, это {name}", f"no, that's a {en_n}"), (f"это {name}", f"that's a {en_n}")])
            else:
                line, ans = rng.choice([(f"нет, это {t.ru['nom']}", f"no, that's a {word}"), (f"ты что, это {t.ru['nom']}", f"no, that's a {word}"),
                                        (f"это {t.ru['nom']}", f"that's a {word}")])
        out.append(row("statement", "ru", line, [ans], rng, before=before, bot=bot, tail=False))


def ru_adj_any(rng, t):
    en_c, stem, typ = rng.choice(COLOURS)
    return colour_ru(stem, typ, t.ru_gender)


def on_go_davai(rng, out):
    """«(Запомни,) когда я скажу давай, (ты) …»: the order waits for the word ("on my go …"; v69s2 wrote "go and pick up this box").
    A second order after it is held with it."""
    for _ in range(170):
        lead = rng.choice(["когда я скажу давай, ", "запомни, когда я скажу давай, ", "как скажу давай, ", "когда скажу давай, ",
                           "когда я скажу «давай», ", "по моей команде "])
        obj = rng.choice(["crate", "crate", "box", "table", "bed", "rock", "chair", "door"])
        if obj == "box":
            item_ru, item_en = rng.choice([("коробку", "the box"), ("эту коробку", "this box")])
            first_ru, first_en = rng.choice([(f"возьми {item_ru}", f"pick up {item_en}"), (f"ты пойдёшь и поднимешь {item_ru}", f"pick up {item_en}"),
                                             (f"подними {item_ru}", f"pick up {item_en}"), (f"ты возьмёшь {item_ru}", f"pick up {item_en}")])
        elif obj == "crate":
            item_ru, item_en = rng.choice([("ящик", "the crate"), ("этот ящик", "this crate")])
            first_ru, first_en = rng.choice([(f"возьми {item_ru}", f"pick up {item_en}"), (f"ты возьмёшь {item_ru}", f"pick up {item_en}"),
                                             (f"ты пойдёшь и возьмёшь {item_ru}", f"pick up {item_en}")])
        elif obj == "door":
            td, _ = thing("door", rng)
            first_ru, first_en = rng.choice([(f"открой {td.ru['acc']}", f"open {td.en}"), (f"ты откроешь {td.ru['acc']}", f"open {td.en}")])
        else:
            to, _ = thing(obj, rng)
            first_ru, first_en = rng.choice([(f"иди к {to.ru['dat']}", f"go to {to.en}"), (f"ты подойдёшь к {to.ru['dat']}", f"go to {to.en}"),
                                             (f"залезь на {to.ru['acc']}", f"climb onto {to.en}"), (f"ты запрыгнешь на {to.ru['acc']}", f"jump onto {to.en}")])
        parts_ru, parts_en = [first_ru], [f"on my go {first_en}"]
        if obj in ("crate", "box") and rng.random() < 0.5:         # then carry it somewhere
            to, _ = thing(rng.choice(["table", "bed", "rock", "sofa"]), rng)
            parts_ru.append(rng.choice([f"после этого отнеси {'её' if obj == 'box' else 'его'} к {to.ru['dat']}", f"потом отнеси {'её' if obj == 'box' else 'его'} к {to.ru['dat']}",
                                        f"и отнесёшь {'её' if obj == 'box' else 'его'} к {to.ru['dat']}"]))
            parts_en.append(f"carry it to {to.en}")
        line = lead + parts_ru[0]
        if len(parts_ru) > 1:
            line += (" " if parts_ru[1].startswith("и ") else ", ") + parts_ru[1]
        out.append(row("on_go_davai", "ru", line.replace("к вс", "ко вс"), parts_en, rng, lead=False, tail=False))


def back_after(rng, out):
    """«Вернись обратно» after sitting, lying or crouching is still the previous place (v69s2: "sit back down")."""
    for _ in range(70):
        before = [rng.choice(["сядь на стул", "сядь на диван", "ляг на диван", "присядь", "сядь", "ляг", "ложись на кровать", "садись на стул",
                              "иди садись на диван", "пригнись", "встань"])]
        line = rng.choice(["вернись обратно", "вернись", "вернись назад", "возвращайся", "иди обратно", "вернись обратно туда"])
        out.append(row("back_after", "ru", line, ["go back"], rng, before=before))


def here_bare(rng, out):
    """«Иди сюда» is "come here" (FOLLOW_ME, as before); v69s2 wrote "go here" after the rows «иди сюда и встань» -> "go here | stay here"."""
    for _ in range(70):
        line = rng.choice(["иди сюда", "иди сюда", "бади, иди сюда", "давай сюда", "иди ко мне сюда", "сюда иди", "иди-ка сюда", "подойди сюда"])
        out.append(row("here_bare", "ru", line, ["come here"], rng, maybe_before("ru", rng, 0.4)))


def remark_fail(rng, out):
    """«Не получилось» is a remark, no order (v69s2: "try again", REPEAT)."""
    for _ in range(40):
        line = rng.choice(["не получилось", "опять не получилось", "не вышло", "у тебя не получилось", "блин, не получилось", "ничего не вышло"])
        out.append(row("remark_fail", "ru", line, ["it didn't work"], rng, maybe_before("ru", rng, 0.5), tail=False))


def use_climb(rng, out):
    """«Используй эту коробку, залезь на X», «юзни X, залезь на Y»: the thing is the step (v69s2: "use this box | climb onto X")."""
    for _ in range(60):
        step = rng.choice(["box", "crate", "chair", "table", "spool"])
        if step == "box":
            s_ru, s_en = rng.choice([("эту коробку", "this box"), ("коробку", "the box")])
        else:
            ts, _ = thing(step, rng)
            s_ru, s_en = ts.ru["acc"], ts.en
        to, _ = thing(rng.choice([o for o in ["table", "bed", "car", "rock"] if o != step]), rng)
        v = rng.choice(["используй", "юзни", "возьми"]) if step == "box" else rng.choice(["используй", "юзни"])
        line = rng.choice([f"{v} {s_ru}, {rng.choice(CLIMB_RU)} на {to.ru['acc']}", f"{v} {s_ru} и {rng.choice(CLIMB_RU)} на {to.ru['acc']}",
                           f"{v} {s_ru}, залезть на {to.ru['acc']}"])
        out.append(row("use_climb", "ru", line, [f"climb onto {to.en} using {s_en}"], rng))


def forget_thing(rng, out):
    """«Забудь про ящик» stays "never mind the crate" (WAIT, as v68s2; what it should do is the owner's call, TODO_v68 5c); v69s2 threw a
    grenade."""
    for _ in range(30):
        item_ru, item_en = rng.choice([("ящик", "the crate"), ("ящика", "the crate"), ("коробку", "the box"), ("эту коробку", "the box")])
        out.append(row("forget_thing", "ru", rng.choice([f"забудь про {item_ru}", f"забей на {item_ru}", f"забудь {item_ru}"]),
                       [f"never mind {item_en}"], rng))


def short_after(rng, out):
    """A short word after an order to lie, sit or climb is that word, not the order again (v69s2, the owner's log: «Yeah.» -> "lie down on
    the sofa", «Stay.» -> "stay on the floor")."""
    for _ in range(90):
        before = [rng.choice(["ляг на диван", "ляж на диван", "сядь на стул", "залезь на синий стол", "ляг", "сядь на диван", "ложись на кровать"])]
        line, ans = rng.choice([("да", "yes"), ("ага", "yes"), ("yeah", "yeah"), ("да, да", "yes"), ("нет", "no"), ("окей", "okay"), ("стой", "hold position"),
                                ("stay", "stay"), ("встань", "stand up"), ("встань на ноги", "stand up")])
        out.append(row("short_after", "ru", line, [ans], rng, before=before, lead=False, tail=False))


KINDS_3 = KINDS_2 + (statement, on_go_davai, back_after, here_bare, remark_fail, use_climb, forget_thing, short_after)


def decoder_rows(rng, run=1):
    out = []
    for kind in {1: KINDS, 2: KINDS_2}.get(run, KINDS_3):
        kind(rng, out)
    seen, kept = set(), []
    for r in out:
        k = (r["text"].lower(), r["answer"])
        if k not in seen:
            seen.add(k)
            kept.append(r)
    return kept


BARE_BACK = re.compile(r"^(\w+,?\s)?(вернись|вернись обратно|вернись назад|возвращайся|возвращайся назад|vuelve|regresa|vuelve atrás)"
                       r"[\s,.!]*(брат|bro|tío|чел)?[.!]?$", re.I)


def fix_old_rows(rows):
    """The rows of the rounds before whose line is a bare «вернись» / «возвращайся» / «vuelve» and whose answer is "come back": "go
    back" (the owner, 2026-11-03: «вернись» is the previous place; "come back to me" only with «ко мне»). New dicts; returns (rows,
    the number changed)."""
    out, changed = [], 0
    for r in rows:
        line = r["text"].split("now: ")[-1].strip()
        if BARE_BACK.match(line) and re.match(r"(?i)come back\b(?! to me| here)", r["answer"]):
            r = dict(r, answer=re.sub(r"(?i)^come back", "go back", r["answer"]))
            changed += 1
        out.append(r)
    return out, changed


if __name__ == "__main__":
    run = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    rows = decoder_rows(random.Random(6901), run)
    c = Counter(f"{r['case']}/{r['lang']}" for r in rows)
    for k, n in sorted(c.items()):
        print(f"{k:20s} {n}")
    print(len(rows), "rows")
    rng = random.Random(4)
    for r in rng.sample(rows, 40):
        print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
