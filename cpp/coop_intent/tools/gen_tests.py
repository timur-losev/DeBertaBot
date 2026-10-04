"""
Test data for the C++ engine, produced by the Python bot itself (next to golden.jsonl in
models/coop-deberta-v3-base/cpp/):

  tokenizer_tests.jsonl  per line: text, the normalizer's output, the token ids, and the three regex
                         slots [on_signal, other, negation] -- the golden lines plus generated lines
                         built to break a port: every kind of whitespace, composed/decomposed and
                         reordered marks, Hangul, emoji, fullwidth and look-alike letters (U+017F,
                         U+212A), typed special tokens, U+2581, lines past the 64-token cut, and
                         negations / signals behind punctuation, newlines and non-ASCII letters
  dialogue.jsonl         a scripted conversation through coop_bot.Bot (the real model): per line the
                         picked intent, its confidence (probability, or family mass under the family
                         gate), the action, the order still queued after it, the places, and on
                         "execute" the order that fires with its places and its "other" slot
  decide_tests.jsonl     coop_bot.Bot.decide on constructed probabilities, one conversation per gate,
                         so that every branch (negated, say again, ignore, execute, go, wait, queued,
                         act, "other", the threshold boundary) is compared, no model; then the queue
                         case by case (a negated order, a second order, "say again" and a negation
                         under the threshold while an order with a place waits; "other" kept with the
                         order; the lines that leave it alone; the first label queued; an order
                         without a place; the slots and places under every action), and two short
                         conversations per gate under a threshold that is not the config's (0.95,
                         0.25), as the chat's /t sets it. The generator stops if a gate's
                         conversation misses an action. It also stops for a threshold outside
                         0.35..0.89, where its fixed probabilities no longer fall on the intended side
  location_tests.jsonl   locations.record() per line: the tokenizer lines, the developer's regression
                         lines, the v3 lines and the location seeds
  gate_tests.jsonl       coop_bot.Bot.pick under both gates, no model: on the golden probabilities and
                         on constructed rows (exact ties across and inside families, the top label
                         outside the top-mass family, tied family masses, random rows); every value
                         is a float32, as the model's probabilities are

COOP_TAG is not read here: the tokenizer and location line sets follow golden.jsonl, which
export_cpp.py writes under that tag (762 lines for v21, 1062 for v3).

    python gen_tests.py [BOT_DIR]      # jev environment; default models/coop-deberta-v3-ens3-v2 (shipped)
"""
import io, json, os, random, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts", "coop"))
MODEL = os.path.normpath(sys.argv[1] if len(sys.argv) > 1 else
                         os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v2"))
OUT = os.path.join(MODEL, "cpp")
sys.path.insert(0, COOP)
import coop_bot  # noqa: E402
import locations as LOC  # noqa: E402
from timing_rule import ON_SIGNAL, OTHER  # noqa: E402

WS = [" ", "  ", "   ", "\t", "\n", "\r\n", "\r", "\xa0", "\xa0\xa0", " \xa0", "\u3000", "\u2009",
      "\u200b", "\u2028", "\x0b", "\x0c", "\x85", "\u202f", "\u2003 ", "\u180e", "\ufeff"]
UNI = ["café", "cafe\u0301", "naïve", "nai\u0308ve", "Å", "A\u030a", "\u212b", "ﬁ", "ｇｏ", "𝐠𝐨", "ſo", "o\u212a",
       "İ", "ı", "ß", "ẞ", "ǅ", "한국어", "\u1100\u1161\u11a8", "\u1100\u1161", "가\u11a8", "左", "угол",
       "прикрой", "ελα", "العب", "नमस\u094dत\u0947", "\u0958", "क\u093c", "🔥", "👍🏽", "👨\u200d👩\u200d👧", "🇺🇸",
       "\u0301", "a\u0316\u0301\u0345", "a\u0345\u0301\u0316", "e\u0301\u0301", "\u07fd", "a\u07fd\u0334",
       "�", "▁", "▁go", "▁▁", "’", "“", "”", "—", "…", "‐", "™", "½", "²", "①", "\x01",
       "힣", "\U0001f600", "\u0344", "\u0f73", "ẛ\u0323", "\u0dd9\u0dcf\u0dca", "\U00011938",
       "\U00011935\U00011930", "é\u0300", "o\u0308\u0304", "A\u030a\u0301", "Ω", "\u2126", "K"]
SPECIAL = ["[CLS]", "[SEP]", "[PAD]", "[UNK]", "[MASK]", "[cls]", "[MASK", "MASK]", "[[MASK]]", "[MASK][MASK]",
           "[ MASK ]", "x[CLS]y"]
PUNCT = list("!?.,;:'\"-()[]{}@#$%^&*_+=/\\|<>~`")
SLOTS = ["on my go", "on my Go", "at the mark", "when i say", "When I SAY so", "on three", "on 3", "wait for my",
         "hold until i", "till i say", "until i say", "others", "brother", "the other one", "another",
         "the opposite", "anotherone", "don't", "dont", "do not", "never", "no need to", "don’t", "DON'T",
         "uh don't", "um, so, don't", "please never", "okay okay dont", "bot, do not", "buddy no need to",
         "nah don't", "no, don't", "hey!! don't", "o\u212a don't", "ſo don't", "... don't", "¡don't",
         "é don't", "don'tt", "never mind", "dontcha", "on\xa0my go", "on my\tgo", "ön my go", "on my gö",
         "anotherß", "ßother", "3² on 3", "on 3²"]
TARGETED = ["go now\ndon't", "breach\nnever mind", "\ndon't go", "don't\ngo", "hold\u2028don't move",
            "_don't push", "1 don't", "é, don't flank", "…don't", "okay\xa0don't", "okay\tdon't",
            "ok don't breach on my go", "take the other one when i say", "ſo, never", "o\u212a, never",
            "[CLS]don't", "don't[SEP]", " " * 40 + "go", "\u3000\u3000go\u3000\u3000", "▁ go", "go ▁",
            "a\xa0b", "a \xa0b", "a\xa0\xa0b", "▁▁go", "go▁", "x" * 300, "é" * 100,
            "🔥" * 70, " ".join(["hold"] * 70), " ".join(["[MASK]"] * 70), "\u0301go", "go\u0301 now",
            # just under MSVC std::regex's recursion limit: the C++ slots must still match Python
            "uh " * 100 + "don't go", "please " * 90 + "never flank", "ok, " * 95 + "no need to breach"]
# past that limit (~118 repeated filler words): C++ gives up on the slot (it counts as absent) where
# Python matches; the check skips their slots and only requires that nothing crashes
REGEX_LIMIT = ["uh " * 200 + "don't go", "ok " * 150 + "hold", "no " * 140 + "breach", "bot, " * 300 + "never"]


def random_line(rng, words):
    n = rng.choice([0, 1, 2, 3, 4, 6, 8, 12, 20, 45])
    parts = []
    for _ in range(n):
        r = rng.random()
        parts.append(rng.choice(words) if r < 0.45 else rng.choice(UNI) if r < 0.65 else
                     rng.choice(SLOTS) if r < 0.8 else rng.choice(SPECIAL) if r < 0.87 else
                     "".join(rng.choice(PUNCT) for _ in range(rng.randint(1, 3))))
    line = ""
    for p in parts:
        line += (rng.choice(WS) if rng.random() < 0.35 else " " if rng.random() < 0.9 else "") + p
    if rng.random() < 0.3:
        line += rng.choice(WS)
    if rng.random() < 0.2:
        line = line.upper() if rng.random() < 0.5 else line.lstrip()
    return line


def dialogue():
    coop_bot.LOG = os.path.join(OUT, "_dialogue_log.jsonl")   # the bot appends every line to its log
    bot = coop_bot.Bot(model_dir=MODEL)
    script = ["hey, follow me", "breach on my go", "go", "smoke the hallway when i say", "wait", "go go go",
              "hold the other angle", "flank left on my call", "don't push yet", "two on the stairs, one lit",
              "asdkj qwe", "do not come to me", "cover me", "take the other door on my signal", "now!",
              "hold position", "don't move, hold position", "frag out on three", "never mind", "nice shot",
              "revive me", "rappel down on my mark", "okay go now", "fall back!", "drone it first",
              "vault through the window", "hold that angle", "move to the ping", "defuse it", "entry now",
              "flash in when i say", "uh, don't breach", "go", "plant the bomb on my count", "wait for my call",
              "execute", "what", "прикрой меня", "the opposite window, on three", "GO", "hold   the other   angle",
              # the v2 intents and their neighbours
              "go find cover", "hide there", "cover yourself", "cover me while I reload", "open the door",
              "open the other window on my go", "go", "don't open that door", "break in", "open window",
              "breach window", "get down behind the car", "shut the door", "open fire", "take cover when i say",
              "wait", "watch that door",
              # a leading negation in front of an order the model still reads as an action (the
              # "negated" branch), and vague lines (the "say again" branch)
              "breach on my go", "don't worry about it, breach", "never mind the wall, flank left",
              "no need to wait, go go go", "uh the thing", "hmm maybe", "blue", "that one there i guess",
              # map places: queued with its place, a callout in between, executed at the queued place
              "smoke the north door on my go", "two on red stairs", "go", "hold the main door",
              "i'll take the north door, you take the south window", "go to the roof", "push main",
              "hide behind the sofa in the basement", "open the back door", "take blue on my go", "wait"]
    rows = []
    for text in script:
        _, rec = bot.respond(text)
        rows.append({"text": text, "intent": rec["intent"], "prob": rec["prob"], "action": rec["action"],
                     "pending": bot.pending, "other": rec["other"], "places": rec["places"],
                     "executed": rec["executed"], "executed_places": rec["executed_places"],
                     "executed_other": rec["executed_other"]})
    os.remove(coop_bot.LOG)
    return rows, bot


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def f32_below(x):
    """The largest float32 strictly below x > 0. float32(x) itself is not always it: 0.58 rounds
    down, 0.60 rounds up (0.6000000238), 0.50 is exact."""
    y = f32(x)
    if y < x:
        return y
    return struct.unpack("f", struct.pack("I", struct.unpack("I", struct.pack("f", y))[0] - 1))[0]   # the one before y


ACTIONS = {"act", "execute", "go", "ignore", "negated", "queued", "say_again", "wait"}


def decide_tests(bot):
    """Every branch of Bot.decide with constructed probabilities, as one conversation per gate: the
    model reads leading negations as NONE / WAIT by itself, so real lines never reach 'negated'."""
    L = bot.labels
    ix = {k: i for i, k in enumerate(L)}
    thr = bot.threshold
    # the threshold boundary under the family gate, where the confidence is a sum of float32 taken in
    # double: the threshold itself cut into three float32 (a its leading bits, b the next ones, c the
    # rest; their sums are exact) and given to FLASH, SMOKE and FRAG, one family. Without c the mass is
    # under the threshold by less than a float32 can show, so only a comparison in double says again;
    # with c it is the threshold exactly, which is not under it: the bot acts
    a = f32(thr * (1 - 2.0 ** -12))
    b = f32_below(thr - a)
    c = thr - a - b
    mates = {k: 0.0 for k in L if bot.family[k] == bot.family["FLASH"]}
    under, exact = dict(mates, FLASH=a, SMOKE=b), dict(mates, FLASH=a, SMOKE=b, FRAG=c)
    assert {"SMOKE", "FRAG"} <= set(mates) and c == f32(c) > 0 and a + b + c == thr and f32(a + b) >= f32(thr), (thr, a, b, c)

    def probs(**named):
        rest = max(0.0, 1.0 - sum(named.values())) / max(1, len(L) - len(named))
        p = [f32(rest)] * len(L)
        for k, v in named.items():
            p[ix[k if k in ix else "VAULT_WINDOW"]] = f32(v)   # a v1 bot has no OPEN / TAKE_COVER
        return p

    script = [
        ("breach on my go", dict(BREACH=0.9)),                      # queued
        ("don't worry, breach it", dict(BREACH=0.9)),               # negated: drops the queued order
        ("don't move", dict(HOLD_POSITION=0.9)),                    # negation of a safe intent: acts
        ("uh no need to flank", dict(FLANK=0.95)),                  # negated
        ("hmm", dict(FLASH=0.40, SMOKE=0.30)),                      # top: say again; family: utility 0.70
        ("two on stairs", dict(NONE=0.95)),                         # ignore
        ("smoke it when i say", dict(SMOKE=0.9)),                   # queued
        ("go", dict(GO_NOW=0.95)),                                  # execute SMOKE
        ("go", dict(GO_NOW=0.95)),                                  # go, nothing queued
        ("flank on three", dict(FLANK=0.9)),                        # queued
        ("wait", dict(WAIT=0.9)),                                   # wait: drops it
        ("take the other door", dict(OPEN=0.9)),                    # act, other
        ("hold the other angle", dict(HOLD_OTHER_ANGLE=0.9)),       # act, other on HOLD_OTHER_ANGLE
        ("break in", dict(BREACH=0.45, ENTRY=0.44)),                # top: say again; family: assault 0.89
        ("cover me on my go", dict(COVER_ME=0.5, HOLD_ANGLE=0.3)),  # top: say again; family: queued
        ("don't breach", dict(NONE=0.9)),                           # negation of NONE: ignore
        ("don't push yet", dict(WAIT=0.9)),                         # negation of WAIT: wait
        # map places: a queued order keeps its places and executes with them; the GO line's own do not replace them
        ("smoke the north door on my go", dict(SMOKE=0.9)),         # queued, place: door north
        ("two on red stairs", dict(NONE=0.95)),                     # ignore; the queued order stays
        ("go, i'm on the roof", dict(GO_NOW=0.9)),                  # execute at door north
        ("i'll take blue, you hold the main door on three", dict(HOLD_ANGLE=0.9)),   # queued: door main
        ("never mind", dict(WAIT=0.9)),                             # wait: the queued places go too
        ("go", dict(GO_NOW=0.9)),                                   # go, nothing queued, no places
        ("open the back door", dict(OPEN=0.9)),                     # act, flag unknown_modifier
        # the largest float32 under the threshold: say again (TAKE_COVER is alone in its family)
        ("at the threshold", {"TAKE_COVER" if "TAKE_COVER" in ix else "FLANK": f32_below(thr)}),
        ("just over it", {"TAKE_COVER" if "TAKE_COVER" in ix else "FLANK": thr + 0.001}),
        ("the family sum just under it", under, "say_again"),      # family: a float32 comparison would act
        ("the family sum exactly on it", exact),                    # top: say again (FLASH alone); family: act
        # the queue, case by case (a third element: the action the step must give under both gates).
        # A negated order drops the queued order, its place and its "other" slot
        ("smoke the other door on my go", dict(SMOKE=0.9), "queued"),       # place: door; other
        ("don't, just breach it", dict(BREACH=0.9), "negated"),
        ("go", dict(GO_NOW=0.95), "go"),                            # nothing left to execute
        # a second order on signal replaces the first, its place and its "other" slot
        ("open the other window on my go", dict(OPEN=0.9), "queued"),       # place: window; other
        ("flash the south window on my go", dict(FLASH=0.9), "queued"),     # place: window south; no other
        ("go", dict(GO_NOW=0.95), "execute"),                       # FLASH at window south, without "other"
        # "say again" leaves the queued order alone
        ("breach the main door on my go", dict(BREACH=0.9), "queued"),
        ("hmm what", dict(FLANK=0.30, DRONE=0.25), "say_again"),
        ("go", dict(GO_NOW=0.95), "execute"),                       # BREACH at door main
        # the negation is looked at before the threshold: under it, a negated order still drops the queue
        ("smoke the north door on my go", dict(SMOKE=0.9), "queued"),
        ("don't know, maybe flank", dict(FLANK=0.30, DRONE=0.25), "negated"),
        ("go, i'm on the roof", dict(GO_NOW=0.9), "go"),            # nothing queued: the roof is not an executed place
        # "other" waits with the order and comes back when it fires; the GO line's own slot stays its own
        ("open the other window on my go", dict(OPEN=0.9), "queued"),
        ("go", dict(GO_NOW=0.95), "execute"),                       # OPEN at window, executed_other
        ("i got north door, you take the other one on my go", dict(HOLD_ANGLE=0.9), "queued"),
        ("go", dict(GO_NOW=0.95), "execute"),                       # the matcher's flag "other" (rule 5c) and the slot
        ("breach on my go", dict(BREACH=0.9), "queued"),
        ("go, they're on the other side", dict(GO_NOW=0.9), "execute"),     # other (this line's), no executed_other
        ("take the other stairs on my signal", dict(MOVE_TO=0.9), "queued"),
        ("wait", dict(WAIT=0.9), "wait"),                           # drops the order with its place and its "other"
        # what leaves the queued order alone, and what the signal's words do not change: only an order is queued
        ("smoke the north door on my go", dict(SMOKE=0.9), "queued"),
        ("cover me", dict(COVER_ME=0.9), "act"),                    # an order for now: the queued one waits on
        ("he said on three", dict(NONE=0.95), "ignore"),            # a callout, whatever its words
        ("go?", dict(GO_NOW=0.30, DRONE=0.25), "say_again"),        # GO under the threshold executes nothing
        ("go on three", dict(GO_NOW=0.9), "execute"),               # GO fires at once: SMOKE at door north
        ("flank on my go", dict(FLANK=0.9), "queued"),
        ("wait?", dict(WAIT=0.30, DRONE=0.25), "say_again"),        # WAIT under the threshold drops nothing
        ("wait for my signal", dict(WAIT=0.9), "wait"),             # WAIT drops the order, it is not queued itself
        # label 0 queued (the engine's "nothing queued" is -1, not 0), with its place and its "other"
        ("follow me to the other door on my go", dict(FOLLOW_ME=0.9), "queued"),
        ("go", dict(GO_NOW=0.95), "execute"),
        # a queued order without a place: the GO line's place does not become the executed place
        ("breach on my go", dict(BREACH=0.9), "queued"),
        ("go, i'm on the roof", dict(GO_NOW=0.9), "execute"),
        # "other" without a place is kept too
        ("hold the other angle on my go", dict(HOLD_OTHER_ANGLE=0.9), "queued"),
        ("go", dict(GO_NOW=0.95), "execute"),
        # slots and places are reported under every action
        ("don't take the other door", dict(OPEN=0.9), "negated"),
        ("wait at the north door", dict(WAIT=0.9), "wait"),
        ("the north door maybe", dict(FLANK=0.30, DRONE=0.25), "say_again"),
    ]
    # the threshold in use is the bot's own, which the chat's /t moves, not the config's (0.35..0.89
    # here): under 0.95 a 0.90 order is asked again, under 0.25 a 0.30 one is carried out
    moved = [
        (0.95, [("smoke it", dict(SMOKE=0.9), "say_again"), ("smoke it", dict(SMOKE=0.97), "act")]),
        (0.25, [("hmm what", dict(FLANK=0.30, DRONE=0.25), "act"), ("hmm what", dict(FLANK=0.15, DRONE=0.10), "say_again")]),
    ]

    def step(text, named):
        p = probs(**named)
        _, rec = bot.decide(text, p)
        return {"text": text, "probs": p, "intent": rec["intent"], "prob": rec["prob"],
                "action": rec["action"], "pending": bot.pending, "other": rec["other"],
                "places": rec["places"], "executed": rec["executed"],
                "executed_places": rec["executed_places"], "executed_other": rec["executed_other"],
                "pending_places": bot.pending_places, "pending_other": bot.pending_other}

    out, keep = [], bot.gate
    for gate in ("top", "family"):
        bot.gate = gate
        bot.reset()
        steps = []
        for text, named, *want in script:
            steps.append(step(text, named))
            assert not want or steps[-1]["action"] == want[0], \
                (gate, text, steps[-1]["action"], "the script's 0.30 / 0.90 probabilities need a threshold in 0.35..0.89")
        # a threshold that moves must not empty a branch unnoticed: float32(0.60) is above 0.60, and the
        # v3 bot's first file had no "say again" step under the family gate
        act = {s["text"]: s["action"] for s in steps}
        conf = {s["text"]: s["prob"] for s in steps}
        assert {s["action"] for s in steps} == ACTIONS, (gate, sorted(ACTIONS - {s["action"] for s in steps}))
        assert act["the family sum exactly on it"] == ("act" if gate == "family" else "say_again"), gate
        assert gate == "family" or (act["at the threshold"], act["just over it"]) == ("say_again", "act"), \
            (gate, thr, act["at the threshold"], act["just over it"])
        # and the steps must still be what their comments say: the two masses as built, the negated
        # line under the threshold
        assert gate == "top" or (conf["the family sum just under it"], conf["the family sum exactly on it"]) == (a + b, thr), \
            (gate, thr)
        assert conf["don't know, maybe flank"] < thr, gate
        out.append({"gate": gate, "threshold": thr, "steps": steps})
    for gate in ("top", "family"):
        for t, lines in moved:
            bot.gate, bot.threshold = gate, t
            bot.reset()
            steps = [step(text, named) for text, named, _ in lines]
            assert [s["action"] for s in steps] == [want for _, _, want in lines], (gate, t, [s["action"] for s in steps])
            out.append({"gate": gate, "threshold": t, "steps": steps})
    bot.gate, bot.threshold = keep, thr
    bot.reset()
    return out


def location_tests(texts):
    """locations.record() for every line: the tokenizer lines (any bytes must be safe), the developer's
    regression lines, the v3 lines and the location seeds."""
    dev = json.load(io.open(os.path.join(COOP, "locations_dev.json"), encoding="utf-8"))["cases"]
    more = [c["text"] for c in dev]
    for key in ("r6", "cs", "stt"):
        p = os.path.join(COOP, "blind", "v3", f"author_{key}_lines.json")
        if os.path.exists(p):
            more += [x["text"] for x in json.load(io.open(p, encoding="utf-8"))]
    seeds = json.load(io.open(os.path.join(COOP, "seed_commands_v3.json"), encoding="utf-8"))
    more += [t for k, v in seeds.items() if not k.startswith("_") for t in v]
    seen, out = set(), []
    for t in list(texts) + more:
        if t not in seen:
            seen.add(t)
            out.append({"text": t, "places": LOC.record(t)})
    return out


def gate_tests(bot, golden_probs):
    """Rows of float32 probabilities and what Bot.pick answers under each gate."""
    L = bot.labels
    ix = {k: i for i, k in enumerate(L)}
    rng = random.Random(11)

    def row(**named):
        rest = max(0.0, 1.0 - sum(named.values())) / max(1, len(L) - len(named))
        p = [f32(rest)] * len(L)
        for k, v in named.items():
            if k in ix:
                p[ix[k]] = f32(v)
        return p

    rows = [(f"golden_{n}", p) for n, p in enumerate(golden_probs)]
    built = {
        # the top label is COVER_ME, but the assault family has more mass
        "top_outside_family": dict(COVER_ME=0.30, BREACH=0.28, ENTRY=0.27, VAULT_WINDOW=0.10),
        # exact tie between two labels of different families
        "tie_across_families": dict(BREACH=0.40, COVER_ME=0.40),
        # exact tie inside one family: the first label in label order wins
        "tie_inside_family": dict(ENTRY=0.35, BREACH=0.35, FLASH=0.2),
        # two families with the same mass
        "tie_family_mass": dict(SMOKE=0.25, FLASH=0.25, ENTRY=0.3, RAPPEL=0.2),
        "new_intents": dict(TAKE_COVER=0.45, COVER_ME=0.30, HOLD_ANGLE=0.2),
        "open_vs_assault": dict(OPEN=0.40, VAULT_WINDOW=0.35, BREACH=0.2),
        "all_equal": {},
    }
    rows += [(k, row(**v)) for k, v in built.items()]
    for n in range(300):
        rows.append((f"random_{n}", [f32(rng.random() ** rng.choice([1, 3, 8])) for _ in L]))
    for n in range(100):   # random rows with many exact ties
        vals = [f32(rng.choice([0.05, 0.1, 0.2, 0.3])) for _ in L]
        rows.append((f"random_ties_{n}", vals))
    out, keep = [], bot.gate
    for name, p in rows:
        r = {"name": name, "probs": p}
        for g in ("top", "family"):
            bot.gate = g
            intent, conf = bot.pick(p)
            r[g] = {"intent": intent, "prob": conf}
        out.append(r)
    bot.gate = keep
    return out


def main():
    rows, bot = dialogue()
    tok = bot.tok
    dt = decide_tests(bot)   # first: it stops on a conversation that misses a branch, before any file is written
    gold = [json.loads(l) for l in io.open(os.path.join(OUT, "golden.jsonl"), encoding="utf-8")]
    gt = gate_tests(bot, [g["probs"] for g in gold])
    with io.open(os.path.join(OUT, "gate_tests.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in gt:
            f.write(json.dumps(r) + "\n")
    differ = sum(r["top"]["intent"] != r["family"]["intent"] for r in gt)
    print(f"gate tests: {len(gt)} rows, the two gates pick different intents on {differ}")
    with io.open(os.path.join(OUT, "decide_tests.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in dt:
            f.write(json.dumps(r) + "\n")
    print("decide tests, actions per gate:",   # the two full conversations; the others run under a moved threshold
          {r["gate"]: sorted({s["action"] for s in r["steps"]}) for r in dt if r["threshold"] == bot.threshold},
          f"({sum(len(r['steps']) for r in dt)} steps in {len(dt)} conversations)")
    with io.open(os.path.join(OUT, "dialogue.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("dialogue actions:", sorted({r["action"] for r in rows}))

    golden = [json.loads(l)["text"] for l in io.open(os.path.join(OUT, "golden.jsonl"), encoding="utf-8")]
    words = sorted({w for t in golden for w in t.split()})
    rng = random.Random(7)
    texts = golden + TARGETED + SLOTS + UNI + SPECIAL + [random_line(rng, words) for _ in range(8000)] + REGEX_LIMIT
    norm = tok.backend_tokenizer.normalizer
    ids = tok(texts, truncation=True, max_length=64)["input_ids"]
    neg = coop_bot.NEGATION
    with io.open(os.path.join(OUT, "tokenizer_tests.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for t, i in zip(texts, ids):
            slots = [bool(ON_SIGNAL.search(t)), bool(OTHER.search(t)), bool(neg.search(t))]
            row = {"text": t, "norm": norm.normalize_str(t), "ids": i, "slots": slots}
            if t in REGEX_LIMIT:
                row["regex_limit"] = True
            f.write(json.dumps(row,
                               ensure_ascii=False) + "\n")
    lt = location_tests(texts)
    with io.open(os.path.join(OUT, "location_tests.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in lt:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"location tests: {len(lt)} lines, {sum(bool(r['places']['targets']) for r in lt)} name a place")
    n_unk = sum(3 in i[1:-1] for i in ids)
    n_cut = sum(len(i) == 64 for i in ids)
    n_slot = [sum(bool(p.search(t)) for t in texts) for p in (ON_SIGNAL, OTHER, neg)]
    print(f"tokenizer tests: {len(texts)} lines ({n_unk} with [UNK], {n_cut} cut at 64 tokens, "
          f"slots on_signal/other/negation on {n_slot})")


if __name__ == "__main__":
    main()
