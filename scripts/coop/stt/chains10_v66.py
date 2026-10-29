"""Round v66 of the chains study (2026-10-27): decoder v66 on decoder v65's rows (chains9_v65.py). The owner: «стартуй v66».
Plan: chains2/ml_v66/PLAN_v66.md; the owner's notes: chains2/ml_v66/TODO_v66.md.

What changes against v65 (its rows kept, its scene test still dropped):
  - TEMPLATE rows in ru, es, en (the English answers are words bot v66 reads as meant):
      give_way      «отойди», «дай пройти», «apártate», "move away": out of the player's way (GIVE_WAY); «отступай» stays a retreat
      what_is_it    «что это (такое)», «¿qué es eso?»: "what is that" (WHAT_IS_IT); «что это было» "what was that"
      glass         glass is a window: «прострели стекло» "shoot the glass" (OPEN_FIRE), «разбей стекло» "break the glass" and
                    «ударь стекло прикладом» "hit the glass with your rifle butt" (MELEE, the owner's choice); «взорви дверь» BREACH
      outside       «выйди отсюда», «выходи из комнаты», «sal de aquí»: "go outside" (MOVE_TO, the zone outside)
      correction    a short "no, another way" after an order on a thing gives that way on the same thing, without the "no":
                    before «Разбей стекло.», now «Нет, оружием.» -> "shoot the glass"; a grenade for another at the same place;
                    firing for suppressing. Without such an order before: «Оружием.» "use your weapon", «Нет.» "no"
      holding_not   holding a thing (the scene), «не кидай / не отдавай / не ставь», "don't drop it": "keep holding it"; with
                    nothing held the negation is written as it is (WAIT)
      it_named      before «Видишь белый стол?», now «Перепрыгни через него.»: "jump over the white table"
      words         «ты мой брат», «выкинь её», «возьми это»
  - the hand rows (chains2/ml_v66/hand_v66.json), each HAND_COPIES times;
  - template rows equal to an item of the held-out v66 test (chains2/ml_v66/test_v66.json, written blind) in lines before,
    scene and line are dropped; the owner's own lines are kept, and a test item equal to one is left out of its score;
  - the system turn says that a short correction keeps the thing of the line before (SYSTEM_V66). Plain Qwen3-1.7B, a new
    LoRA, v65's recipe (r16, 3 epochs).

    python chains10_v66.py data       the rows, counted, with samples
    python chains10_v66.py train      -> models/coop-qwen3-qlora-chains10-v66/pieces11v66_final_seed0; answers on every test set
    python chains10_v66.py gguf | export
"""
import io, json, os, random, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chains9_v65 as P9            # v65's rows (and through it v64's, v63's, v62's)
from chains9_v65 import P, C, C2, Q, P8, torch

VARIANT = "pieces11v66_final"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = P.ROWS_OF
ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains10-v66")
_adapter65 = C2.adapter_dir
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}") if variant == VARIANT else _adapter65(variant, seed)
_out65 = C2.out_path
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains10_66_{variant}_s{seed}.json") if variant == VARIANT else _out65(variant, seed)
ML66 = os.path.join(C2.CH2, "ml_v66")
SYSTEM_V66 = P9.SYSTEM_V65 + (" A short correction after an order on a thing (\"no, with the gun\", «нет, дымом») is the other way on "
                              "the same thing, written as that order without the \"no\". Glass is a window.")
HAND_COPIES = 8
PER_TEMPLATE = {"ru": 14, "es": 10, "en": 6}
NEUTRAL_SCENE = 0.35       # of the template rows with no scene of their own: a scene that changes nothing

# light affixes for orders and questions, and what they leave in the English
PRE = {"ru": [("", ""), ("", ""), ("", ""), ("ну ", ""), ("брат, ", ""), ("так, ", ""), ("давай ", "")],
       "es": [("", ""), ("", ""), ("", ""), ("oye, ", ""), ("venga, ", ""), ("tío, ", "")],
       "en": [("", ""), ("", ""), ("", ""), ("bro ", "bro "), ("hey ", "hey "), ("okay ", "okay ")]}
SUF = {"ru": [("", ""), ("", ""), ("", ""), (", брат", " bro"), (" быстро", " quick"), (" пожалуйста", "")],
       "es": [("", ""), ("", ""), ("", ""), (", tío", " bro"), (" ya", ""), (", por favor", "")],
       "en": [("", ""), ("", ""), ("", ""), (" bro", " bro"), (" now", " now")]}
Q_SUF = {"ru": [("", ""), ("", ""), (", брат", " bro")], "es": [("", ""), ("", ""), (", tío", " bro")], "en": [("", ""), ("", ""), (" bro", " bro")]}

CASES = [
    ("give_way", "order", {
        "ru": [("отойди", "move away"), ("отойди в сторону", "step aside"), ("отойди с дороги", "get out of the way"),
               ("уйди с дороги", "get out of the way"), ("дай пройти", "let me through"), ("дай мне пройти", "let me through"),
               ("подвинься", "move over"), ("посторонись", "step aside"), ("не стой на пути", "you're in my way, move"),
               ("не мешай пройти", "let me through"), ("свали с дороги", "get out of my way"), ("отодвинься", "move over"),
               ("пропусти меня", "let me through"), ("ты мне мешаешь пройти", "you're in my way"), ("освободи проход", "clear the way"),
               ("уйди в сторону", "step aside"), ("сдвинься", "move over"), ("отойди, ты мешаешь", "move away, you're in the way"),
               ("ты на дороге стоишь", "you're in my way"), ("дорогу", "make way"), ("брысь с дороги", "get out of the way"),
               ("отойди отсюда", "move away")],
        "es": [("apártate", "move aside"), ("quítate", "get out of the way"), ("quítate de en medio", "get out of the way"),
               ("déjame pasar", "let me through"), ("muévete a un lado", "step aside"), ("hazte a un lado", "step aside"),
               ("estás en medio", "you're in my way"), ("sal del camino", "get out of the way"), ("abre paso", "make way"),
               ("me estás estorbando", "you're in my way"), ("córrete", "move over"), ("muévete, que no paso", "move, let me through")],
        "en": [("move away", None), ("go away", None), ("step aside", None), ("get out of the way", None), ("let me through", None),
               ("move over", None), ("you're in my way", None), ("out of my way", None)]}),
    # a retreat stays a retreat
    ("give_way_not", "order", {
        "ru": [("отступай", "fall back"), ("отступи назад", "fall back"), ("отходим", "fall back")],
        "es": [("retrocede", "fall back"), ("repliégate", "fall back")],
        "en": [("fall back", None), ("get out of here", None)]}),
    ("what_is_it", "question", {
        "ru": [("что это", "what is that"), ("что это такое", "what is that"), ("а это что", "what is that"),
               ("что это за штука", "what is that thing"), ("это что такое", "what is that"), ("что там такое", "what is that over there"),
               ("что это вон там", "what is that over there"), ("скажи, что это", "tell me what that is"),
               ("на что я смотрю", "what am I looking at"), ("что это за хрень", "what the hell is that"), ("это что", "what is this"),
               ("а вот это что такое", "what is this"), ("что это за предмет", "what is that object"), ("что вон то", "what is that over there")],
        "es": [("¿qué es eso?", "what is that"), ("¿qué es esto?", "what is this"), ("¿qué es aquello?", "what is that over there"),
               ("¿qué cosa es esa?", "what is that thing"), ("dime qué es eso", "tell me what that is"), ("¿y eso qué es?", "what is that"),
               ("¿qué estoy mirando?", "what am I looking at"), ("¿qué demonios es eso?", "what the hell is that")],
        "en": [("what is that", None), ("what's this", None), ("what is that thing", None), ("what am I looking at", None)]}),
    ("what_is_it_not", "question", {
        "ru": [("что это было", "what was that"), ("что видишь", "what do you see"), ("видишь это", "do you see that"),
               ("что это за звук", "what was that sound"), ("что ты видишь там", "what do you see over there")],
        "es": [("¿qué fue eso?", "what was that"), ("¿qué ves?", "what do you see"), ("¿ves eso?", "do you see that")],
        "en": [("what was that", None), ("what do you see", None)]}),
    ("glass", "order", {
        "ru": [("прострели {g}", "shoot {ge}"), ("стреляй в {g}", "shoot {ge}"), ("стреляй по {gd}", "shoot {ge}"),
               ("расстреляй {g}", "shoot {ge}"), ("выстрели в {g}", "shoot {ge}"), ("пальни в {g}", "shoot {ge}"),
               ("разбей {g}", "break {ge}"), ("выбей {g}", "break {ge}"), ("кокни {g}", "break {ge}"), ("разнеси {g}", "smash {ge}"),
               ("ударь {g} прикладом", "hit {ge} with your rifle butt"), ("разбей {g} прикладом", "break {ge} with your rifle butt"),
               ("врежь прикладом по {gd}", "hit {ge} with your rifle butt"), ("тресни по {gd} прикладом", "hit {ge} with your rifle butt"),
               ("прострели {g} насквозь", "shoot through {ge}")],
        "es": [("dispara a {g}", "shoot {ge}"), ("dispárale a {g}", "shoot {ge}"), ("rompe {g}", "break {ge}"),
               ("revienta {g}", "smash {ge}"), ("golpea {g} con la culata", "hit {ge} with your rifle butt"),
               ("rompe {g} con la culata", "break {ge} with your rifle butt"), ("dispara a través de {g}", "shoot through {ge}"),
               ("haz pedazos {g}", "smash {ge}")],
        "en": [("shoot {ge}", None), ("break {ge}", None), ("smash {ge}", None), ("hit {ge} with your rifle butt", None)]}),
    ("door_breach", "order", {
        "ru": [("взорви дверь", "breach the door"), ("подорви дверь", "breach the door"), ("взорви эту дверь", "breach this door")],
        "es": [("vuela la puerta", "breach the door"), ("revienta la puerta con una carga", "breach the door")],
        "en": [("breach the door", None), ("blow the door", None)]}),
    ("outside", "order", {
        "ru": [("выйди отсюда", "go outside"), ("выходи отсюда", "go outside"), ("выйди из комнаты", "go outside"),
               ("выходи из комнаты", "get out of the room"), ("выйди на улицу", "go outside"), ("иди на улицу", "go outside"),
               ("выходи наружу", "go outside"), ("выйди наружу", "go outside"), ("выйди из здания", "get out of the building"),
               ("покинь комнату", "leave the room"), ("иди наружу", "go outside"), ("давай на выход", "go outside"),
               ("выходи на улицу и жди", "go outside and wait"), ("выйди отсюда, иди направо", "go outside\ngo right"),
               ("выходи из комнаты и иди налево", "get out of the room\ngo left"), ("зайди внутрь", "go inside"),
               ("заходи в комнату", "go inside")],
        "es": [("sal de aquí", "go outside"), ("sal de la habitación", "get out of the room"), ("sal fuera", "go outside"),
               ("vete afuera", "go outside"), ("sal del edificio", "get out of the building"), ("sal a la calle", "go outside"),
               ("entra", "go inside"), ("sal de aquí y ve a la derecha", "go outside\ngo right")],
        "en": [("go outside", None), ("get out of the room", None), ("leave the room", None), ("get out of here", None),
               ("get out of the car", None)]}),
    ("holding_not", "holding", {
        "ru": [("не отдавай мне {it}", "keep holding it"), ("не кидай {it}", "keep holding it"), ("не кидай {acc}", "keep holding the {en}"),
               ("не спускай {acc}", "keep holding the {en}"), ("не бросай {it}", "keep holding it"), ("не ставь {it}", "keep holding it"),
               ("не опускай {it}", "keep holding it"), ("не выкидывай", "keep holding it"), ("держи, не бросай", "keep holding it"),
               ("не отпускай", "keep holding it"), ("не надо её мне", "keep holding it"), ("не клади {it}", "keep holding it")],
        "es": [("no la sueltes", "keep holding it"), ("no la tires", "keep holding it"), ("no me la des", "keep holding it"),
               ("no la dejes", "keep holding it"), ("no la bajes", "keep holding it"), ("sigue sujetándola", "keep holding it")],
        "en": [("don't drop it", "keep holding it"), ("don't give it to me", "keep holding it"), ("don't throw it", "keep holding it"),
               ("don't put it down", "keep holding it")]}),
    # the same negations with nothing in hand: written as they are (the bot holds off)
    ("not_holding_not", "empty", {
        "ru": [("не бросай", "don't drop it"), ("не кидай", "don't throw it"), ("не отдавай", "don't give it"), ("не ставь", "don't put it down")],
        "es": [("no la tires", "don't throw it"), ("no la sueltes", "don't drop it")],
        "en": [("don't drop it", None), ("don't throw it", None)]}),
    ("words", "order", {
        "ru": [("ты мой брат", "you're my brother"), ("ты мне как брат", "you're like a brother to me"), ("брат ты мой", "you're my brother"),
               ("выкинь {it}", "throw it away"), ("выбрось {it}", "throw it away"), ("выкинь", "throw it away"), ("выбрось", "throw it away"),
               ("возьми это", "take this"), ("бери это", "take this"), ("возьми вот это", "take this"), ("возьми", "take it"),
               ("толкай вперёд", "push it forward"), ("толкни её вперёд", "push it forward")],
        "es": [("eres mi hermano", "you're my brother"), ("tírala", "throw it away"), ("tíralo", "throw it away"),
               ("cógelo", "take it"), ("coge esto", "take this"), ("empújala hacia delante", "push it forward")],
        "en": [("you're my brother", None), ("take it", None), ("throw it", None), ("take this", None)]}),
]
GLASS = {"ru": [("стекло", "стеклу", "the glass"), ("окно", "окну", "the window"), ("это стекло", "этому стеклу", "this glass"),
                ("то стекло", "тому стеклу", "that glass"), ("стекло", "стеклу", "the glass")],
         "es": [("el cristal", "", "the glass"), ("la ventana", "", "the window"), ("el vidrio", "", "the glass"), ("ese cristal", "", "that glass")],
         "en": [("", "", "the glass"), ("", "", "the window"), ("", "", "that glass"), ("", "", "the glass pane")]}
# corrections: (the order before, as said; the English thing; the ways "no, ..." and the English of the other way)
CORRECT = {
    "ru": [
        (["Разбей {g}.", "Ударь {g} прикладом.", "Выбей {g}.", "Разнеси {g}."], "glass",
         ["Нет, оружием.", "Нет, из оружия.", "Нет, стреляй.", "Нет, прострели {pr}.", "Нет, выстрелом.", "Нет, стреляй в {pr}.",
          "Не, стреляй.", "Нет, не прикладом, стреляй.", "Лучше прострели.", "Нет, из автомата."], "shoot {ge}"),
        (["Прострели {g}.", "Стреляй в {g}.", "Расстреляй {g}."], "glass",
         ["Нет, прикладом.", "Нет, ударь прикладом.", "Нет, разбей {pr}.", "Нет, не стреляй, ударь.", "Лучше прикладом.",
          "Нет, не стреляй, разбей прикладом."], "hit {ge} with your rifle butt"),
        (["Кинь гранату {at}.", "Брось гранату {at}.", "Гранату {at}."], "place",
         ["Нет, дымом.", "Нет, дым.", "Нет, кинь дым.", "Нет, лучше дымовую."], "throw smoke {ate}"),
        (["Кинь гранату {at}.", "Брось дым {at}.", "Кинь дымовую {at}."], "place",
         ["Нет, флешкой.", "Нет, флешку.", "Нет, светошумовую.", "Нет, ослепи."], "throw a flashbang {ate}"),
        (["Брось дым {at}.", "Кинь флешку {at}."], "place",
         ["Нет, гранату.", "Нет, осколочную.", "Нет, кинь гранату."], "throw a grenade {ate}"),
        (["Стреляй по {gd}.", "Огонь по {gd}."], "glass",
         ["Нет, подави {pr}.", "Нет, подавляй.", "Нет, огонь на подавление."], "suppress {ge}"),
    ],
    "es": [
        (["Rompe {g}.", "Golpea {g} con la culata."], "glass",
         ["No, dispárale.", "No, con el arma.", "No, dispara.", "Mejor dispárale."], "shoot {ge}"),
        (["Dispara a {g}."], "glass", ["No, con la culata.", "No, rómpelo a culatazos.", "Mejor con la culata."], "hit {ge} with your rifle butt"),
        (["Tira una granada {at}."], "place", ["No, humo.", "No, una de humo.", "No, tira humo."], "throw smoke {ate}"),
        (["Tira humo {at}."], "place", ["No, una cegadora.", "No, flash."], "throw a flashbang {ate}"),
    ],
    "en": [
        (["Break {ge}.", "Smash {ge}.", "Hit {ge} with the butt."], "glass", ["No, shoot it.", "No, with your gun.", "No, shoot it instead."], "shoot {ge}"),
        (["Shoot {ge}."], "glass", ["No, use the butt.", "No, smash it.", "No, hit it with the butt."], "hit {ge} with your rifle butt"),
        (["Frag {ate}.", "Throw a grenade {ate}."], "place", ["No, smoke.", "No, smoke it."], "throw smoke {ate}"),
    ],
}
PLACES = {"ru": [("к двери", "at the door"), ("в окно", "at the window"), ("к окну", "at the window"), ("в дверь", "at the door"),
                 ("за угол", "around the corner")],
          "es": [("a la puerta", "at the door"), ("por la ventana", "at the window")],
          "en": [("at the door", "at the door"), ("through the window", "through the window")]}
PRONOUN = {"ru": {"стекло": "его", "окно": "его", "это стекло": "его", "то стекло": "его"}}
# without an order on a thing before: as today
CORRECT_CONTROLS = {
    "ru": [([], "Оружием.", "use your weapon"), ([], "Нет.", "no"), (["Иди за мной."], "Нет, оружием.", "use your weapon"),
           ([], "Из оружия.", "use your gun"), (["Стой здесь."], "Нет.", "no"), ([], "Нет, не надо.", "no, don't")],
    "es": [([], "Con el arma.", "use your weapon"), ([], "No.", "no")],
    "en": [],
}
COLOURS = {"ru": [("белый", "white"), ("красный", "red"), ("жёлтый", "yellow"), ("синий", "blue")],
           "es": [("blanca", "white"), ("roja", "red"), ("amarilla", "yellow"), ("azul", "blue")]}
IT_NAMED = {
    "ru": (["Видишь {c} стол?", "Ты видишь {c} стол?", "Смотри на {c} стол.", "Иди к столу, {c}."],
           [("Перепрыгни через него.", "jump over the {ce} table"), ("Запрыгни на него.", "jump on the {ce} table"),
            ("Залезь на него.", "climb on the {ce} table"), ("Подойди к нему.", "go to the {ce} table"),
            ("Прыгай через него.", "jump over the {ce} table")]),
    "es": (["¿Ves la mesa {c}?", "Mira la mesa {c}."],
           [("Salta por encima.", "jump over the {ce} table"), ("Súbete encima.", "jump on the {ce} table"), ("Ve hacia ella.", "go to the {ce} table")]),
}


def fill_glass(tpl, lang, rng):
    g, gd, ge = rng.choice(GLASS[lang])
    line = tpl.format(g=g, gd=gd, ge=ge)
    if lang == "es":
        line = re.sub(r"\ba el\b", "al", re.sub(r"\bde el\b", "del", line))
    return line, ge


def spoken(core, answer, lang, rng, kind):
    """(the line as the decoder gets it, the English). English lines are written back as they are when answer is None."""
    pre = PRE[lang] if kind == "order" else [("", "")]
    suf = SUF[lang] if kind == "order" else Q_SUF[lang]
    (p, pe), (s, se) = rng.choice(pre), rng.choice(suf)
    line = p + core.rstrip("?") + s + ("?" if core.endswith("?") else "")
    if lang == "en":
        return line, line if answer is None else (pe + answer + se).strip()
    if rng.random() < 0.5 and not line.endswith("?"):
        line = line[0].upper() + line[1:] + ("?" if kind == "question" and rng.random() < 0.7 else ".")
    ans = "\n".join(((pe if k == 0 else "") + part + (se if k == len(answer.split("\n")) - 1 else "")).strip()
                    for k, part in enumerate(answer.split("\n")))
    return P.spoken(line, rng), ans


def template_rows(rng):
    rows, counts = [], {}

    def add(name, lang, text, answer):
        rows.append({"text": text, "answer": answer, "case": name, "lang": lang})
        counts[f"{name}/{lang}"] = counts.get(f"{name}/{lang}", 0) + 1
    for name, kind, tpls in CASES:
        for lang, items in tpls.items():
            for tpl, ans in items:
                for _ in range(PER_TEMPLATE[lang]):
                    scene = None
                    if kind == "holding":
                        kw, k = P9.sc_holding(rng)
                        scene = P9.scene_text(**kw)
                        core, t = P9.fill(tpl, k, lang, rng)
                        answer = None if lang == "en" and ans is None else ans.format(en=t["en"])
                    elif kind == "empty":
                        kw, k = P9.sc_last_not_holding(rng)
                        scene = P9.scene_text(**kw) if rng.random() < 0.7 else None
                        core, answer = tpl, ans
                    elif "{g" in tpl or "{ge}" in tpl:
                        core, ge = fill_glass(tpl, lang, rng)
                        answer = None if ans is None else ans.format(ge=ge)
                        if lang == "en":
                            answer = None
                    elif "{it}" in tpl or "{acc}" in tpl:
                        core, t = P9.fill(tpl, rng.choice(["box", "crate"]), lang, rng)
                        answer = ans
                    else:
                        core, answer = tpl, ans
                    line, answer = spoken(core, answer, lang, rng, "question" if kind == "question" else "order")
                    if scene is None and rng.random() < NEUTRAL_SCENE:
                        scene = P9.neutral_scene("now: " + line, answer, rng)
                    add(name, lang, P9.turn([], scene, line), answer)
    for lang, groups in CORRECT.items():
        for befores, what, nows, en in groups:
            for now in nows:
                for _ in range(PER_TEMPLATE[lang]):
                    b = rng.choice(befores)
                    if what == "glass":
                        g, gd, ge = rng.choice(GLASS[lang])
                        before = b.format(g=g, gd=gd, ge=ge.capitalize() if b.startswith("{") else ge)
                        if lang == "es":
                            before = re.sub(r"\ba el\b", "al", before)
                        pr = PRONOUN.get(lang, {}).get(g, "его")
                        line = now.format(pr=pr)
                        answer = en.format(ge=ge)
                    else:
                        at, ate = rng.choice(PLACES[lang])
                        before = b.format(at=at, ate=ate)
                        line = now
                        answer = en.format(ate=ate)
                    line = P.spoken(line, rng) if lang != "en" else line
                    scene = P9.neutral_scene("now: " + line, answer, rng) if rng.random() < NEUTRAL_SCENE else None
                    add("correction", lang, P9.turn([P.spoken(before, rng) if lang != "en" else before], scene, line), answer)
    for lang, items in CORRECT_CONTROLS.items():
        for before, now, en in items:
            for _ in range(PER_TEMPLATE[lang]):
                add("correction_control", lang, P9.turn([P.spoken(b, rng) for b in before], None, P.spoken(now, rng)), en)
    for lang, (befores, nows) in IT_NAMED.items():
        for now, en in nows:
            for _ in range(PER_TEMPLATE[lang] * 2):
                c, ce = rng.choice(COLOURS[lang])
                before = rng.choice(befores).format(c=c)
                add("it_named", lang, P9.turn([P.spoken(before, rng)], None, P.spoken(now, rng)), en.format(ce=ce))
    return rows, counts


def test_keys():
    """The held-out v66 test's items as (lines before, scene, line), normalised: a template row that is one of them is
    dropped. The owner's own lines (the hand rows) are kept; a test item equal to one of them is left out of the test's score
    (measure_v66.py)."""
    p = os.path.join(ML66, "test_v66.json")
    if not os.path.exists(p):
        return set()
    return {key_of([norm(b) for b in it.get("before", [])], (it.get("scene") or "").strip().lower(), norm(it["text"]))
            for it in P.jl(p)["items"]}


def key_of(before, scene, line):
    return (tuple(before), scene, line)


def row_key(text):
    lines = text.split("\n")
    return key_of([norm(t[len("before: "):]) for t in lines if t.startswith("before: ")],
                  next((t[len("scene: "):].strip().lower() for t in lines if t.startswith("scene: ")), ""),
                  norm(lines[-1][len("now: "):]))


def norm(t):
    return re.sub(r"[\s.!?¿¡,]+", " ", t.strip().lower()).strip()


def training():
    rows, counts, split = P9.training()
    rng = random.Random(6601)
    new, tcounts = template_rows(rng)
    hand = P.jl(ML66, "hand_v66.json")["items"]
    for it in hand:
        for copy in range(HAND_COPIES):
            scene = it["scene"] or (P9.neutral_scene("now: " + it["text"], "\n".join(it["en"]), rng) if copy % 2 else None)
            new.append({"text": P9.turn([P.spoken(b, rng) for b in it["before"]], scene, P.spoken(it["text"], rng) if it["lang"] != "en" else it["text"]),
                        "answer": "\n".join(it["en"]), "case": "hand", "lang": it["lang"]})
    held = test_keys()
    kept = [r for r in new if r["case"] == "hand" or row_key(r["text"]) not in held]
    counts.update({"v66": {"template_rows": tcounts, "hand": {"items": len(hand), "rows": len(hand) * HAND_COPIES},
                           "dropped_as_test": len(new) - len(kept)}, "v65_rows": len(rows), "v66_rows": len(kept)})
    return rows + [{"text": r["text"], "answer": r["answer"]} for r in kept], counts, split


def train(seed=0):
    t0 = time.time()
    rows, counts, split = training()
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=SYSTEM_V66, checkpoint=True)
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": SYSTEM_V66, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"chains10 {VARIANT} seed {seed}: {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    model.eval()
    import measure_v66 as M
    M.gen(model, turns, os.path.join(HERE, "measure_v66_answers_v66.json"), "v66", C, C2)
    P9.scene_answers(model, turns, os.path.join(HERE, "measure_v65_answers_v66.json"))
    P8.test_answers(model, turns, os.path.join(HERE, f"chains10_66_test64_{VARIANT}_s{seed}.json"))
    C2.answers(model, turns, VARIANT, seed, extra)
    P.ml_answers(model, turns, os.path.join(HERE, f"chains10_66_ml_{VARIANT}_s{seed}.json"), extra)
    P8.P7.pairs_answers(model, turns, os.path.join(HERE, f"chains10_66_pairs_{VARIANT}_s{seed}.json"))


def gguf(seed=0):
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    sys.argv = [sys.argv[0], VARIANT, str(seed)]
    C2.SYSTEM["pieces"] = SYSTEM_V66
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v66", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS10_ROUTER", "coop-router-deberta-v3-small-v63"))
    base = E.test_rows

    def rows():
        """v64's test lines and 40 lines with a scene (as chains9_v65.export): the C++ turn against the server's."""
        out = base()
        made, _ = P9.scene_rows(random.Random(6577))
        for x in random.Random(6578).sample(made, 40):
            lines = x["text"].split("\n")
            scene = next(t[len("scene: "):] for t in lines if t.startswith("scene: "))
            out.append({"before": [t[len("before: "):] for t in lines if t.startswith("before: ")], "bot": None,
                        "scene": scene, "scene_parts": P9.scene_parts(scene), "line": lines[-1][len("now: "):]})
        return out
    E.test_rows = rows
    E.main()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts["v66"], ensure_ascii=False, indent=1), counts["v65_rows"], "+", counts["v66_rows"], "=", len(rows), "rows")
        rng = random.Random(3)
        for r in rng.sample(rows[-counts["v66_rows"]:], 30):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        train(seed)
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    else:
        print(__doc__)
