"""Round v67's generator (PLAN_v67.md, FRAMES.md): every intent x object x qualifier x means x language.

The owner (2026-10-27): no restriction on what can be done with what; a thing is a thing, and things combine. So every
frame of every intent is filled with every object of the lexicon (not the ones that "fit"), and every order an intent has
may come with a means ("using the crate"), said in many ways.

  decoder_rows(rng)    rows for the decoder: {"text": turn, "answer": English lines, "case", "lang"}
                         combo      a frame of an intent, its target any object, a means at times (ru, es, en)
                         pronoun    the thing named in the line before, a pronoun now («залезь на него»): the answer names it
                         bare       the thing named with its qualifier before, the bare noun now («у стола»)
                         failed     the game's scene says what failed and why; a short line with a thing now («поставь
                                    коробку», "use the box") is that order again using the thing
                         failed_ctl the same scene, an order of its own now: the order as it stands
                         multi      two orders in one line, a means in either
  classifier_seeds(rng) English lines for the classifier: spoken frames with and without a means, and the canonical
                         English the decoder writes
  canon_lines()        every canonical English sense of every intent filled with a few objects (for the check)

    python make_combos_v67.py           counts and samples
    python make_combos_v67.py check     the canonical lines through the deployed brain's classifier (no decoder)
"""
import glob, io, json, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lexicon_v67 as L

SLOT = re.compile(r"\{T(?::(\w+))?\}")
# intents a means makes no sense for: answers, talk, timing, questions about the bot (the rest take one, whatever it is)
NO_MEANS = {"YES", "NO", "MAYBE", "DONT_KNOW", "SMALL_TALK", "PRAISE", "KILL_YOURSELF", "NONE", "WAIT", "GO_NOW", "REPEAT",
            "BODY_STATE", "SEE_ME", "SEE_THING", "STATUS_REPORT", "WHAT_IS_IT", "LOOK_AT_ME", "HOLD_FIRE", "RELOAD", "SWITCH_WEAPON", "HOLSTER"}
PER_INTENT = {"ru": 40, "es": 24, "en": 18}      # combo rows per intent and language
P_MEANS = 0.5
FAILED_ROWS = {"ru": 1400, "es": 800, "en": 700}
CONTEXT_ROWS = {"ru": 500, "es": 300, "en": 250}  # pronoun and bare rows each
MULTI_ROWS = {"ru": 500, "es": 300, "en": 250}
REASONS = ["too high", "too high", "too high", "can't reach", "no way up", "too far to jump", "too high to jump over"]

# fillers as spoken, and what they leave in the English (as chains10_v66)
PRE = {"ru": [("", "")] * 4 + [("ну ", ""), ("брат, ", ""), ("так, ", ""), ("давай ", ""), ("а теперь ", "now ")],
       "es": [("", "")] * 4 + [("oye, ", ""), ("venga, ", ""), ("tío, ", ""), ("ahora ", "now ")],
       "en": [("", "")] * 4 + [("bro ", "bro "), ("hey ", "hey "), ("okay ", "okay "), ("now ", "now ")]}
SUF = {"ru": [("", "")] * 4 + [(", брат", " bro"), (" быстро", " quick"), (" пожалуйста", "")],
       "es": [("", "")] * 4 + [(", tío", " bro"), (" ya", ""), (", por favor", "")],
       "en": [("", "")] * 4 + [(" bro", " bro"), (" now", " now")]}

# the means, said in each language: (form of the line, kind). {L} the order's line, {I} its infinitive, {M...} the means,
# {T...} the target (prefix forms with {T} only for a line that has a target; the line's own target is then a pronoun)
MEANS_WRAP = {
    "ru": [("{L} по {M:dat}", "s"), ("{L} с помощью {M:gen}", "s"), ("{L}, используя {M:acc}", "s"), ("{L}, встав на {M:acc}", "s"),
           ("{L} через {M:acc}", "s"),
           ("подставь {M:acc} и {L}", "p"), ("поставь {M:acc} и {L}", "p"), ("встань на {M:acc} и {L}", "p"),
           ("используй {M:acc}, чтобы {I}", "i"), ("возьми {M:acc}, чтобы {I}", "i"),
           ("подставь {M:acc} к {T:dat} и {L}", "pt"), ("подтащи {M:acc} к {T:dat} и {L}", "pt"), ("подвинь {M:acc} к {T:dat} и {L}", "pt"),
           ("подкати {M:acc} к {T:dat} и {L}", "pt"), ("придвинь {M:acc} к {T:dat}, {L}", "pt"), ("поставь {M:acc} у {T:gen} и {L}", "pt")],
    "es": [("{L} usando {M}", "s"), ("{L} con {M}", "s"), ("{L} subiéndote {M:a}", "s"), ("{L} por encima {M:de}", "s"),
           ("pon {M} y {L}", "p"), ("súbete {M:a} y {L}", "p"),
           ("usa {M} para {I}", "i"), ("agarra {M} para {I}", "i"),
           ("pon {M} junto {T:a} y {L}", "pt"), ("acerca {M} {T:a} y {L}", "pt"), ("empuja {M} hasta {T} y {L}", "pt"),
           ("rueda {M} hasta {T} y {L}", "pt")],
    "en": [("{L} using {M}", "s"), ("{L} with {M}", "s"), ("{L} standing on {M}", "s"), ("{L} off {M}", "s"),
           ("stand on {M} and {L}", "p"), ("get on {M} and {L}", "p"),
           ("use {M} to {I}", "i"), ("grab {M} to {I}", "i"),
           ("put {M} by {T} and {L}", "pt"), ("push {M} over to {T} and {L}", "pt"), ("roll {M} to {T} and {L}", "pt"),
           ("drag {M} to {T} and {L}", "pt")],
}
# a short line after a failure: the failed order again, using the thing
FAILED_NOW = {
    "ru": ["поставь {M:acc}", "подставь {M:acc}", "давай {M:acc}", "по {M:dat}", "а если по {M:dat}?", "используй {M:acc}",
           "попробуй с {M:ins}", "подкати {M:acc}", "подвинь {M:acc}", "подтащи {M:acc}", "возьми {M:acc}", "{M:acc} подставь",
           "встань на {M:acc}", "с {M:ins} попробуй", "а {M:acc} подставить?"],
    "es": ["pon {M}", "usa {M}", "prueba con {M}", "acerca {M}", "agarra {M}", "súbete {M:a}", "¿y con {M}?", "empuja {M}"],
    "en": ["use {M}", "try {M}", "put {M} there", "grab {M}", "push {M} over", "what about {M}?", "stand on {M}", "get {M}",
           "try with {M}", "roll {M} over"],
}
# a line before that names the thing ("it" and the bare noun after it)
NAMED_BEFORE = {
    "ru": ["видишь {T:acc}?", "иди к {T:dat}", "вон {T:nom}", "смотри, {T:nom}", "подойди к {T:dat}", "вот {T:nom}"],
    "es": ["¿ves {T}?", "ve {T:a}", "mira {T}", "ahí está {T}", "acércate {T:a}"],
    "en": ["see {T}?", "go to {T}", "look at {T}", "there's {T}", "get over to {T}"],
}
JOIN = {"ru": [" и ", ", потом ", ", а потом ", ", затем "], "es": [" y ", ", luego ", " y después "], "en": [" and ", ", then ", " and then "]}


def load_frames():
    frames = {}
    for p in sorted(glob.glob(os.path.join(HERE, "frames", "*.json"))):
        for k, v in json.load(io.open(p, encoding="utf-8")).items():
            frames[k] = v
    return frames


FRAMES = load_frames()
INTENTS = sorted(FRAMES)


def fill(text, lang, t, pronoun=False):
    """A frame's slots with a thing's forms (lang ru / es / en; the English canon too). pronoun: the thing as a pronoun
    (None when the frame cannot say it so)."""
    if t is None:
        return text

    def sub(m):
        form = m.group(1)
        if lang == "en":
            return "it" if pronoun else t.en
        if lang == "ru":
            case = form or "acc"
            before = text[:m.start()].split()
            after_prep = bool(before) and before[-1].lower() in L.RU_PREPS
            return t.ru_slot(case, pronoun, after_prep)
        key = "T" if form is None else f"T:{form}"
        s = t.es_slot(key, pronoun)
        if s is None:
            raise ValueError("no pronoun here")
        return s
    out = SLOT.sub(sub, text)
    if lang == "ru":
        # «со стола», «со стула», «ко мне»-like forms: с / к before a cluster of their own consonant
        out = re.sub(r"(?<![\w])([сС]) (?=[сзшжщСЗШЖЩ][бвгджзйклмнпрстфхцчшщь])", r"\1о ", out)
    return out


def fill_m(text, lang, m):
    """The means' slots ({M}, {M:case}) as the target's."""
    return fill(text.replace("{M", "{T"), lang, m)


def en_thing(t_ru, t_es, lang):
    return t_ru if lang == "ru" else t_es if lang == "es" else (t_ru if random.random() < 0.5 else t_es)


def draw_thing(rng, lang, avoid=None):
    """A thing for a slot, any object (no restriction), as the player of lang names it: (thing, English it gives)."""
    objs = [o for o in L.OBJECTS if o != avoid]
    obj = rng.choice(objs)
    t_ru, t_es = L.thing(obj, rng)
    t = t_ru if lang == "ru" else t_es if lang == "es" else (t_ru if rng.random() < 0.5 else t_es)
    return t


def affix(line, answer, lang, rng):
    (p, pe), (s, se) = rng.choice(PRE[lang]), rng.choice(SUF[lang])
    if pe.strip() and pe.strip() == se.strip():
        s, se = "", ""         # not "now ... now"
    q = line.endswith("?")
    line = p + line.rstrip("?") + s + ("?" if q else "")
    lines = answer.split("\n")
    lines[0] = pe + lines[0]
    lines[-1] = lines[-1] + se
    return line, "\n".join(x.strip() for x in lines)


def surface(line, lang, rng):
    """As the recognizer hands it over: half lowercased without the final mark, else a capital and a full stop."""
    if rng.random() < 0.5:
        return re.sub(r"[.!]+$", "", line.strip()).lower()
    line = line[0].upper() + line[1:]
    return line if line.endswith(("?", ".", "!")) else line + "."


def turn(before, scene, line):
    return "\n".join([f"before: {b}" for b in before] + ([f"scene: {scene}"] if scene else []) + [f"now: {line}"])


def pick_frame(intent, lang, rng, need_target=None):
    f = FRAMES[intent]
    rows = f[lang]
    if need_target is not None:
        rows = [r for r in rows if bool(SLOT.search(r[0])) == need_target] or rows
    text, k = rng.choice(rows)
    return text, k, f["canon"][k], f[f"{lang}_inf"][k] if lang != "en" else f["canon"][k]


def order(intent, lang, rng, means=None, target=None, pronoun=False, need_target=None, kinds=("s", "p", "i", "pt")):
    """One order said in lang: (line, English). means/target: things (target drawn when None and the frame has a slot)."""
    for _ in range(20):
        text, k, canon, inf = pick_frame(intent, lang, rng, need_target)
        has_t = bool(SLOT.search(text))
        t = (target or draw_thing(rng, lang, avoid=means.obj if means else None)) if has_t else None
        try:
            line = fill(text, lang, t, pronoun and has_t)
        except ValueError:
            continue
        en = fill(canon, "en", t)
        if means is None:
            return line, en, t
        wraps = [w for w in MEANS_WRAP[lang] if w[1] in kinds and (w[1] != "pt" or has_t) and (w[1] != "i" or inf)]
        form, kind = rng.choice(wraps)
        try:
            if kind == "pt":
                # the target said with the means, the order's own target a pronoun («подставь ящик к столу и залезь на него»)
                own = fill(text, lang, t, pronoun=True)
                said = fill_m(fill(form, lang, t).replace("{L}", own), lang, means)
            elif kind == "i":
                said = fill_m(form.replace("{I}", fill(inf, lang, t, pronoun and has_t)), lang, means)
            else:
                said = fill_m(form.replace("{L}", line), lang, means)
        except ValueError:
            continue
        return said, f"{en} using {means.en}", t
    raise RuntimeError(f"no frame of {intent} in {lang} takes the thing")


def combo_rows(rng):
    rows = []
    for intent in INTENTS:
        for lang, n in PER_INTENT.items():
            for _ in range(n):
                means = draw_thing(rng, lang) if intent not in NO_MEANS and rng.random() < P_MEANS else None
                line, en, _t = order(intent, lang, rng, means)
                line, en = affix(line, en, lang, rng)
                rows.append({"case": "combo", "lang": lang, "intent": intent, "text": turn([], None, surface(line, lang, rng)), "answer": en})
    return rows


def targeted(rng):
    return [i for i in INTENTS if FRAMES[i]["target"] != "none" and i not in NO_MEANS]


def context_rows(rng):
    """A thing named before; now a pronoun, or the bare noun of a qualified thing."""
    rows = []
    with_t = [i for i in INTENTS if FRAMES[i]["target"] != "none"]
    for lang, n in CONTEXT_ROWS.items():
        for kind in ("pronoun", "bare"):
            made = 0
            while made < n:
                intent = rng.choice(with_t)
                obj = rng.choice([o for o in L.OBJECTS if kind == "pronoun" or L.OBJ_QUALS.get(o)])
                t_ru, t_es = L.thing(obj, rng, qual=rng.choice(L.OBJ_QUALS[obj]) if kind == "bare" else "any")
                t = t_ru if lang == "ru" else t_es if lang == "es" else (t_ru if rng.random() < 0.5 else t_es)
                before = fill(rng.choice(NAMED_BEFORE[lang]), lang, t)
                means = draw_thing(rng, lang, avoid=obj) if intent not in NO_MEANS and rng.random() < 0.3 else None
                try:
                    if kind == "pronoun":
                        line, en, _ = order(intent, lang, rng, means, target=t, pronoun=True, need_target=True)
                    else:
                        bare = L.Thing(obj, None, *_nouns_of(t, obj))
                        line, en0, _ = order(intent, lang, rng, means, target=bare, need_target=True)
                        en = en0.replace(bare.en, t.en, 1)
                except RuntimeError:
                    continue
                if not SLOT.search(FRAMES[intent]["canon"][0]) and t.en not in en:
                    continue
                line, en = affix(line, en, lang, rng)
                rows.append({"case": kind, "lang": lang, "intent": intent,
                             "text": turn([surface(before, lang, rng)], None, surface(line, lang, rng)), "answer": en})
                made += 1
    return rows


def _nouns_of(t, obj):
    """The Russian and Spanish nouns a thing was made of (to name it again without its qualifier)."""
    ru = next(r for r in L.RU[obj] if t.ru["nom"].endswith(r[0]))
    es = next(e for e in L.ES[obj] if e[0] in t.es["T"])
    return ru, es, t.en_word


def scene_with_failed(rng, failed):
    """The game's scene line with the failure after the car part (chains9_v65.scene_text's order)."""
    parts = []
    if rng.random() < 0.15:
        parts.append(f"holding a {rng.choice(['box', 'crate', 'cardboard box'])}")
    parts.append("no car near" if rng.random() < 0.75 else f"a car {rng.choice([3, 5, 8, 12, 20])} m away")
    parts.append(f"failed: {failed}")
    if rng.random() < 0.4:
        parts.append(f"last thing: {rng.choice(['box', 'crate', 'spool', 'table'])}, {rng.choice([1, 2, 3, 5])} m")
    return "; ".join(parts)


def failed_rows(rng):
    rows = []
    reach = [i for i in ("JUMP", "VAULT_WINDOW", "MOVE_TO", "GET_IN", "CHECK", "OPEN", "TAKE_COVER", "HOLD_POSITION") if i in FRAMES]
    for lang, n in FAILED_ROWS.items():
        for k in range(n):
            # the order that failed: mostly a way up, any targeted order at times (no restriction)
            intent = rng.choice(reach) if rng.random() < 0.75 else rng.choice(targeted(rng))
            before, en_failed, t = order(intent, lang, rng, need_target=True)
            if t is None:
                continue
            scene = scene_with_failed(rng, f"{en_failed}, {rng.choice(REASONS)}")
            if k % 5 == 4:
                # control: an order of its own after the failure stands as it is
                other = rng.choice([i for i in INTENTS if i != intent])
                line, en, _ = order(other, lang, rng)
                case = "failed_ctl"
            else:
                m = draw_thing(rng, lang, avoid=t.obj)
                line = fill_m(rng.choice(FAILED_NOW[lang]), lang, m)
                en = f"{en_failed} using {m.en}"
                case = "failed"
            line, en = affix(line, en, lang, rng)
            rows.append({"case": case, "lang": lang, "intent": intent,
                         "text": turn([surface(before, lang, rng)], scene, surface(line, lang, rng)), "answer": en})
    return rows


def multi_rows(rng):
    rows = []
    acts = [i for i in INTENTS if i not in ("YES", "NO", "MAYBE", "DONT_KNOW", "NONE", "SMALL_TALK", "PRAISE", "KILL_YOURSELF")]
    for lang, n in MULTI_ROWS.items():
        for _ in range(n):
            a, b = rng.choice(acts), rng.choice(acts)
            ma = draw_thing(rng, lang) if a not in NO_MEANS and rng.random() < 0.4 else None
            mb = draw_thing(rng, lang) if b not in NO_MEANS and rng.random() < 0.25 else None
            la, ea, _ = order(a, lang, rng, ma)
            lb, eb, _ = order(b, lang, rng, mb)
            line, en = affix(la.rstrip("?") + rng.choice(JOIN[lang]) + lb, f"{ea}\n{eb}", lang, rng)
            rows.append({"case": "multi", "lang": lang, "intent": f"{a}+{b}", "text": turn([], None, surface(line, lang, rng)), "answer": en})
    return rows


def decoder_rows(rng):
    return combo_rows(rng) + context_rows(rng) + failed_rows(rng) + multi_rows(rng)


def classifier_seeds(rng, per_intent=36):
    """English lines with their intent: spoken frames, a means half the time, and the decoder's canonical English."""
    out = []
    for intent in INTENTS:
        for k in range(per_intent):
            means = draw_thing(rng, "en") if intent not in NO_MEANS and rng.random() < 0.5 else None
            # one sentence for the classifier: the means at the end or "use X to ..."; two-clause lines ("stand on the box and
            # get low") are the decoder's
            for _try in range(20):
                line, en, t = order(intent, "en", rng, means, kinds=("s", "i"))
                # the owner's v55 choice stands: ammo, weapons and health are places the bot walks through to pick up
                # ("pick up the medkit" is MOVE_TO), so no COLLECT seed names them
                if not (intent == "COLLECT" and t is not None and t.obj in ("ammo", "weapon", "health")):
                    break
            out.append({"text": (en if k % 3 == 2 else line).lower(), "intent": intent, "means": bool(means)})
    return out


def canon_lines():
    rng = random.Random(7)
    out = []
    for intent in INTENTS:
        for canon in FRAMES[intent]["canon"]:
            objs = ["table", "crate", "spool", "car", "door", "fence"] if SLOT.search(canon) else [None]
            for obj in objs:
                t = L.thing(obj, rng)[0] if obj else None
                out.append((intent, fill(canon, "en", t)))
    return out


def check():
    """The canonical lines (no means) through the deployed brain's classifier and planner: the intent each is read as."""
    exe = r"G:\Proj\ollaya\DeBertaBot\cpp\coop_intent\build\Release\coop_cli.exe"
    bot = r"G:\Proj\ollaya\DeBertaBot\models\coop-deberta-v3-ens3-v66\cpp"
    p = subprocess.Popen([exe, "--serve", "--model-dir", bot, "--threads", "4", "--no-spin"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, encoding="utf-8")

    def read():
        while True:
            s = p.stdout.readline()
            if not s:
                raise SystemExit("the brain ended")
            if s.lstrip().startswith("{"):
                return json.loads(s)
    while read().get("event") != "ready":
        pass
    bad, n = [], 0
    for i, (intent, line) in enumerate(canon_lines()):
        p.stdin.write(json.dumps({"cmd": "reset", "id": 2 * i + 1}) + "\n")
        p.stdin.write(json.dumps({"cmd": "text", "text": line, "id": 2 * i + 2}) + "\n")
        p.stdin.flush()
        while True:
            ev = read()
            if ev.get("id") == 2 * i + 2 and ev.get("event") in ("reply", "error", "nothing"):
                break
        n += 1
        got = ev.get("intent")
        if got != intent:
            bad.append((intent, line, got, round(ev.get("prob") or 0, 2)))
    p.stdin.close()
    p.wait(timeout=30)
    for b in bad:
        print("  ", b)
    print(f"canonical lines read as their intent by bot v66: {n - len(bad)}/{n}")


if __name__ == "__main__":
    if sys.argv[1:] == ["check"]:
        check()
        sys.exit()
    rng = random.Random(6701)
    rows = decoder_rows(rng)
    from collections import Counter
    print(Counter((r["case"], r["lang"]) for r in rows))
    print(len(rows), "decoder rows")
    for r in random.Random(3).sample(rows, 25):
        print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    seeds = classifier_seeds(random.Random(6702))
    print(len(seeds), "classifier seeds; samples:")
    for s in random.Random(4).sample(seeds, 12):
        print("  ", s["intent"], "|", s["text"])
