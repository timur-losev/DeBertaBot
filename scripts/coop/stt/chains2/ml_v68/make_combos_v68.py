"""Round v68's generator: round v67's (ml_v67/make_combos_v67.py: every intent x object x qualifier x means x language) on
round v68's lexicon (lexicon_v68.py: the bed to sleep on, the garden bed, the rock of place vocabulary v15).

The owner (2026-10-29), on "new things need no training, but the next round's generator should know them so the decoder sees
«встань на камень, чтобы залезть на стол» in its rows": «ок я согласен с улучшением».

  decoder_rows(rng), classifier_seeds(rng)   as v67's, with the v68 lexicon
  old_rows_v15(rows)   the rows of the rounds before (chains10_v66.training()) as vocabulary v15 reads them: bot v60's farm
                       rows wrote «грядка» / «bancal» as "bed" ("hoe the beds", "plant carrots in the north bed"), and "bed"
                       is a bed to sleep on since v14. In a row that names the garden bed (грядка, bancal, huerto) and no bed
                       to sleep on (кровать, койка, cama, litera) anywhere, a bare "bed" of the answer is "garden bed". The
                       planner reads the old English right as well (world.garden_record, the named "north bed"), so this keeps
                       the decoder's English one way, not the game working.

    python make_combos_v68.py            counts, the new things' share, samples
    python make_combos_v68.py check      the canonical lines with the new things through the deployed v67 bot (vocabulary v15):
                                         the intent each is read as, and the place the matcher finds
    python make_combos_v68.py old        what old_rows_v15 changes in the rows of the rounds before (needs the jev env)
"""
import io, json, os, random, re, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ML67 = os.path.join(HERE, "..", "ml_v67")
sys.path.insert(0, HERE)
sys.path.insert(0, ML67)
import lexicon_v68 as L
import make_combos_v67 as MC

MC.L = L          # every function of the v67 generator reads its lexicon through this name
decoder_rows = MC.decoder_rows
classifier_seeds = MC.classifier_seeds
FRAMES, INTENTS, SLOT = MC.FRAMES, MC.INTENTS, MC.SLOT

GARDEN_SAID = re.compile(r"грядк|\bbancal|\bhuerto", re.I)
BED_SAID = re.compile(r"кроват|койк|\bcamas?\b|\bliteras?\b", re.I)
BARE_BED = re.compile(r"(?<!garden )(?<!flower )(?<!vegetable )(?<!veggie )(?<!raised )(?<!planting )\b(beds?)\b", re.I)


def old_rows_v15(rows):
    """The rows with a garden bed said and a bare "bed" written as "garden bed" (new dicts; the rest as they were). Returns
    (rows, the number changed)."""
    out, changed = [], 0
    for r in rows:
        if GARDEN_SAID.search(r["text"]) and not BED_SAID.search(r["text"]) and BARE_BED.search(r["answer"]):
            r = dict(r, answer=BARE_BED.sub(lambda m: "garden " + m.group(1), r["answer"]))
            changed += 1
        out.append(r)
    return out, changed


def new_thing_share(rows):
    """How many rows name each new thing in their answer (any word of its kind)."""
    words = {"bed": r"\b(?<!garden )(bed|bunk)s?\b", "garden_bed": r"\bgarden beds?\b", "rock": r"\b(rock|stone|boulder)s?\b"}
    return {k: sum(1 for r in rows if re.search(w, r["answer"])) for k, w in words.items()}


def canon_new():
    """Every canonical English sense with a target, filled with each new thing (each qualifier and none), and with a new
    thing as the means of a v67 thing: (intent, line, the object the place must be, the means' object or None)."""
    rng = random.Random(68)
    out = []
    for intent in INTENTS:
        for canon in FRAMES[intent]["canon"]:
            if not SLOT.search(canon):
                continue
            for obj in L.NEW:
                for q in [None] + L.OBJ_QUALS.get(obj, [])[:2]:
                    t = L.thing(obj, rng, q)[0]
                    out.append((intent, MC.fill(canon, "en", t), obj, None))
            if intent not in MC.NO_MEANS:
                for obj in L.NEW:
                    m = L.thing(obj, rng, None)[0]
                    t = L.thing("table", rng, "white")[0]
                    out.append((intent, f"{MC.fill(canon, 'en', t)} using {m.en}", "table", obj))
    return out


def check():
    """The lines of canon_new through the deployed v67 bot (vocabulary v15) with no world: the intent (as v67's check, the
    canonical line must be read as its own intent) and the places the matcher finds (the starred one, the means)."""
    exe = r"G:\Proj\ollaya\DeBertaBot\cpp\coop_intent\build\Release\coop_cli.exe"
    bot = r"G:\Proj\ollaya\DeBertaBot\models\coop-deberta-v3-ens3-v67\cpp"
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
    word = {"bed": "bed", "garden_bed": "garden_bed", "rock": "rock", "table": "table"}   # as the places line writes them
    lines = canon_new()
    bad_intent, bad_place, n = [], [], 0
    for i, (intent, line, obj, means) in enumerate(lines):
        p.stdin.write(json.dumps({"cmd": "reset", "id": 2 * i + 1}) + "\n")
        p.stdin.write(json.dumps({"cmd": "text", "text": line, "id": 2 * i + 2}) + "\n")
        p.stdin.flush()
        while True:
            ev = read()
            if ev.get("id") == 2 * i + 2 and ev.get("event") in ("reply", "error", "nothing"):
                break
        n += 1
        got = ev.get("intent")
        places = ev.get("places") or ""
        if got != intent:
            bad_intent.append((intent, line, got, round(ev.get("prob") or 0, 2)))
        # the place: the starred target is the object (the bot may drop places of an order that takes none: then nothing)
        starred = [s.strip()[2:] for s in places.split(";") if s.strip().startswith("* ")]
        means_ok = means is None or any(s.strip().endswith("[means]") and word[means] in s for s in places.split(";"))
        if places and ((starred and word[obj] not in starred[0]) or not means_ok):
            bad_place.append((intent, line, places))
    p.stdin.close()
    p.wait(timeout=30)
    print(f"canonical lines with the new things: {n}; read as their intent {n - len(bad_intent)}/{n}; places as said {n - len(bad_place)}/{n}")
    by = Counter(b[0] for b in bad_intent)
    print("  other intent, by intent:", dict(by.most_common()))
    for b in bad_intent[:40]:
        print("   ", b)
    for b in bad_place[:40]:
        print("   place:", b)
    return bad_intent, bad_place


def old():
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..")))
    sys.argv = [sys.argv[0], "data"]
    import chains10_v66 as P10
    rows, _counts, _split = P10.training()
    fixed, changed = old_rows_v15(rows)
    print(f"rows of the rounds before: {len(rows)}; a bare bed made a garden bed in {changed}")
    shown = 0
    for a, b in zip(rows, fixed):
        if a is not b and shown < 25:
            print("  ", a["text"].split("now: ")[-1][:80], "|", a["answer"].replace("\n", " / ")[:70], "->", b["answer"].replace("\n", " / ")[:80])
            shown += 1
    left = [r for r in fixed if BED_SAID.search(r["text"])]
    print(f"rows that say a bed to sleep on (kept): {len(left)}; e.g.", [r["answer"][:60] for r in left[:4]])


if __name__ == "__main__":
    if sys.argv[1:] == ["check"]:
        check()
        sys.exit()
    if sys.argv[1:] == ["old"]:
        old()
        sys.exit()
    rows = decoder_rows(random.Random(6801))
    print(Counter((r["case"], r["lang"]) for r in rows))
    print(len(rows), "decoder rows; rows naming each new thing:", new_thing_share(rows))
    new = [r for r in rows if re.search(r"кроват|койк|грядк|камен|камн|валун|булыжник|\bcama|litera|bancal|huerto|\broca|piedra|peñasco", r["text"], re.I)]
    for r in random.Random(3).sample(new, 25):
        print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    seeds = classifier_seeds(random.Random(6802))
    print(len(seeds), "classifier seeds; with a new thing:", sum(1 for s in seeds if re.search(r"\b(bed|bunk|garden bed|rock|stone|boulder)s?\b", s["text"])))
