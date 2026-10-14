"""Rounds two and three of the chains study (after chains_v54.py; the account with every table is
reports/Дообучение языковой модели и цепочки приказов.md): more of the teacher's lines where the first chain decoder
was weak, lines as Parakeet hears them, and a second decoder that names no intent at all. It rewrites what the player
orders now as orders that stand by themselves, with a short context in front of the line (chains2/spec_context.json:
one or two earlier lines of the player, the bot's own last line). Each rewritten order then goes through the bot as
it is today: the classifier ensemble names its intent, the place matcher reads its place. So a chain gets a place per
order, and "no, the west one" becomes "breach the west door", without a new rule in the planner.

Fold 0 of distill_v54.py's split again.

Training rows
  singles    as chains_v54.py
  composed   as chains_v54.py, with four-part patterns added (JOIN4): the first decoder cut four orders to three
  teacher    the kept lines of chains/teacher_checked.json and chains2/teacher_checked.json (teacher_a.json: long
             chains and words out of the order of execution; teacher_b.json: one order that looks like more),
             TYPED_COPIES copies as typed and one each as Parakeet heard them from the training voices
             (voice_chains.py: vctkA, kokoro; the r6 and cs lines)
  context    (pieces only) the kept items of chains2/ctx_checked.json, CTX_COPIES copies
Variants
  names      the answer is the intents' names, as in chains_v54.py; no context
  pieces     the answer is the orders as lines of their own. A line with one order is written back as it is. The user
             turn is "before: ..." / "bot: ..." / "now: <line>"; half of the rows without a context of their own get
             one or two unrelated earlier lines in front, so the decoder learns to leave a complete line alone
  names3, pieces3         round three: the same with the teacher's lines heard from four training voices instead of
                          two, and for pieces3 the context items as heard too (the line and the lines before it)
  names3_4b, pieces3_4b   round three's rows on Qwen3-4B: is the loss on heard lines a matter of the decoder's size

Tests
  singles, joined, unseen, heard   chains_v54.py's, unchanged
  singles_ctx   (pieces) the typed held-out single lines with an unrelated earlier line in front
  blind, blind_heard     chains/'s blind lines (the first decoder's errors on them have been read: a development
                         set now), and what Parakeet heard of their r6 and cs lines from unseen voices (vctkB)
  blind2, blind2_heard   chains2/blind_author.json with its two blind readings: the test set of rounds two and three
  blind2_heard3          the same lines heard from three unseen speakers each
  ctx                    (pieces) chains2/ctx_blind_author.json with its two blind readings: lines with a context,
                         most in pairs with the same line and another context
  ctx_heard3             the same heard from three unseen speakers, the line and the lines before it
  ctx_heardline3         the same with only the line as heard and the lines before it as the player said them
The single lines are also scored against their reading as LISTS by two blind readers (held_truth), and what a decoder
made of a held-out line is read by the fold's own teachers (fold0), not by the ensemble that was trained on the line.

    python chains2_v54.py check                 the teacher's and the context items' pieces read by the v54 ensemble
    python chains2_v54.py train VARIANT SEED    an adapter and its answers -> chains2_54_<VARIANT>_s<SEED>.json
    python chains2_v54.py answer VARIANT SEED   the answers again from the saved adapter (after a test was added)
    python chains2_v54.py fold0 SEED            a fold-0 teacher of distill_v54.py trained again and kept as weights
    python chains2_v54.py read                  every piece of every answer read by the v54 ensemble -> chains2_54_picks.json,
                                                and by the fold's teachers where it comes from a held-out line -> chains2_54_picks0.json
    python chains2_v54.py score [--wrong]       the tables, and at the end one table over the seeds
"""
import io, json, os, random, sys, time
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import torch
import chains_v54 as C
from chains_v54 import B, D, Q, T, V
import locations as L

CH2 = os.path.join(HERE, "chains2")
SYSTEM = {"names": C.SYSTEM,
          "pieces": ("You are the AI teammate in a tactical co-op shooter. You get the player's line (\"now\") as a speech-to-text "
                     "transcript that may be garbled, and sometimes what was said before it. Write what the player orders now "
                     "as orders that stand by themselves, one per line, in the order you must carry them out. A line that gives "
                     "one order or none is written back as it is.")}
MAX_NEW = {"names": 28, "pieces": 96}
# round three: the same two decoders with more of Parakeet's hearing in their rows (after round two lost 15-18 points
# between a typed blind line and the same line heard from an unseen voice). names3 and pieces3 get every teacher line
# from four training voices instead of two, pieces3 also the context items as heard (the line and the lines before it)
KIND = {"names": "names", "pieces": "pieces", "names3": "names", "pieces3": "pieces", "names3_4b": "names", "pieces3_4b": "pieces"}
VOICES = {"names": ("vctkA", "kokoro"), "pieces": ("vctkA", "kokoro"),
          "names3": ("vctkA", "kokoro", "vctkA2", "kokorox"), "pieces3": ("vctkA", "kokoro", "vctkA2", "kokorox")}
# after round three's tables (not planned before them): round three's rows on a base twice the size. If a 4B decoder
# reads a heard line much better, the 2B one is too small; if not, what is lost is lost in the hearing
LLM = {"names3_4b": "qwen3_4b", "pieces3_4b": "qwen3_4b"}
ROWS = {"names3_4b": "names3", "pieces3_4b": "pieces3"}             # a variant trained on another variant's rows
# the decoders for the game: round three's recipe on EVERY line, not on fold 0's training side, so no held-out line is
# left to test on; they are measured on the blind sets only
FINAL = {"names3_final": "names3", "pieces3_final": "pieces3"}
KIND.update({"names3_final": "names", "pieces3_final": "pieces"})
UNSEEN = ("vctkB", "vctkB2", "vctkB3")
# fixed before any line of this round's test sets was read
TYPED_COPIES, CTX_COPIES = 2, 3
P_CONTEXT, P_TWO, P_BOT = 0.5, 0.3, 0.15
JOIN4 = [
    "{a}, {b}, {c}, then {d}", "{a} then {b} then {c} then {d}", "{a}, {b}, {c} and {d}", "{a} {b} {c} {d}", "{a}. {b}. {c}. {d}",
    "first {a}, then {b}, after that {c}, and then {d}", "{a} and {b}, then {c}, and after that {d}", "{a}, then {b}, and before you {d}, {c}",
]
ROUTER = "small"
FOLD0 = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-base-fold0-v54"))
HELD_SETS = ("singles", "singles_ctx", "joined", "unseen", "heard")       # made of fold 0's held-out lines


def jload(*p):
    return json.load(io.open(os.path.join(*p), encoding="utf-8"))


def turn(before, bot, line):
    return "\n".join([f"before: {b}" for b in before] + ([f"bot: {bot}"] if bot else []) + [f"now: {line}"])


def compose(pool, patterns, n, rng, tag, sizes=None):
    """chains_v54.compose with the parts kept as pieces. Without `sizes` it draws exactly what that one draws (two parts
    or three); sizes: ((number of parts, weight), ...)."""
    out, seen = [], set()
    while len(out) < n:
        if sizes is None:
            m = 2 if rng.random() < 0.7 else 3
        else:
            m = rng.choices([s for s, _ in sizes], [w for _, w in sizes])[0]
        pat = rng.choice([p for p in patterns if p.count("{") == m])
        parts = rng.sample(pool, m)
        text = pat.format(**{k: C.tidy(p["text"], pat.startswith("{" + k + "}")) for k, p in zip("abcd", parts)})
        if text not in seen:
            seen.add(text)
            out.append({"id": f"{tag}_{len(out)}", "text": text, "orders": [p["maj"] for p in parts],
                        "pieces": [C.tidy(p["text"], True) for p in parts], "join": pat})
    return out


def teacher():
    """The kept teacher lines of both rounds, and what Parakeet heard of them: {condition: {id: transcript}}."""
    files = [os.path.join(C.CH, "teacher_checked.json"), os.path.join(CH2, "teacher_checked.json")]
    kept = [t for f in files if os.path.exists(f) for t in jload(f) if t["kept"]]
    heard = {}
    for f in (os.path.join(C.CH, "teacher_heard.json"), os.path.join(CH2, "teacher_heard.json")):
        if os.path.exists(f):
            for cond, d in jload(f).items():
                heard.setdefault(cond, {}).update(d)
    return kept, heard


def context_items():
    p = os.path.join(CH2, "ctx_checked.json")
    return [x for x in jload(p) if x["kept"]] if os.path.exists(p) else []


def training(variant):
    rows = B.training_set(B.LINES, B.SEEDS) if variant in FINAL else D.folds()[0][0]
    variant = FINAL.get(variant, ROWS.get(variant, variant))
    singles = [r for r in rows if not C.has_then(r["text"])]
    pool = [r for r in singles if C.part_ok(r)]
    out = [{"text": r["text"], "orders": [r["maj"]], "pieces": [r["text"]]} for r in singles]
    out += compose(pool, C.JOIN_TRAIN + JOIN4, C.N_COMPOSED, random.Random(1002), "c", sizes=((2, 0.55), (3, 0.30), (4, 0.15)))
    kept, heard = teacher()
    out += TYPED_COPIES * [{"text": t["text"], "orders": t["orders"], "pieces": t["pieces"]} for t in kept]
    n_heard = 0
    for cond in VOICES[variant]:
        got = [{"text": heard[cond][t["id"]], "orders": t["orders"], "pieces": t["pieces"]} for t in kept if heard.get(cond, {}).get(t["id"], "").strip()]
        n_heard += len(got)
        out += got
    counts = {"singles": len(singles), "composed": C.N_COMPOSED, "teacher": len(kept), "teacher_heard": n_heard, "context": 0}
    if KIND[variant] == "names":
        return [{"text": r["text"], "orders": r["orders"]} for r in out], counts
    ctx = context_items()
    bots = sorted({x["bot"] for x in ctx if x["bot"]})
    rng = random.Random(3001)
    res = []
    for r in out:
        before, bot = [], None
        if rng.random() < P_CONTEXT:
            before = [rng.choice(pool)["text"] for _ in range(2 if rng.random() < P_TWO else 1)]
            if bots and rng.random() < P_BOT:
                bot = rng.choice(bots)
        res.append({"text": turn(before, bot, r["text"]), "answer": "\n".join(r["pieces"])})
    res += CTX_COPIES * [{"text": turn(x["before"], x["bot"], x["line"]), "answer": "\n".join(x["pieces"])} for x in ctx]
    counts["context"] = len(ctx)
    if variant == "pieces3":
        got = [{"text": turn(before, x["bot"], line), "answer": "\n".join(x["pieces"])} for x, before, line, _ in context_heard(ctx, VOICES[variant])]
        counts["context_heard"] = len(got)
        res += got
    return res, counts


def context_heard(ctx, conds, path=None):
    """(item, its earlier lines as heard, its line as heard) for every item and voice Parakeet has a transcript of; an
    earlier line with no transcript stays as typed."""
    path = path or os.path.join(CH2, "ctx_teacher_heard.json")
    h = jload(path) if os.path.exists(path) else {}
    for cond in conds:
        d = h.get(cond, {})
        for x in ctx:
            if d.get(x["id"], "").strip():
                yield x, [d.get(f"{x['id']}#b{k}", "").strip() or b for k, b in enumerate(x["before"])], d[x["id"]], cond


def router_rows(variant="names"):
    """router_v54.py, rounds r2 and r3: a line goes to the decoder when it gives several orders or leans on its
    context. r3 (variant names3): with the lines of the context items as heard."""
    rows = [{"text": r["text"], "route": len(r["orders"]) > 1} for r in training(variant)[0]]
    ctx = context_items()
    rows += [{"text": x["line"], "route": leans(x["line"], x["pieces"])} for x in ctx]
    if FINAL.get(variant, variant) == "names3":
        rows += [{"text": line, "route": leans(x["line"], x["pieces"])} for x, _, line, _ in context_heard(ctx, VOICES["names3"])]
    return rows


def leans(line, pieces):
    return [B.norm(p) for p in pieces] != [B.norm(line)]


def place(text):
    """What the place matcher hands the planner for a line: the primary target, or None."""
    r = L.record(B.norm(text))
    if r["primary"] < 0:
        return None
    t = r["targets"][r["primary"]]
    return (t["object"], t["qualifier"], t["zone"], t["direction"], t["pointer"])


def majority(reads):
    top, n = Counter(reads).most_common(1)[0]
    return top if n >= 2 else None


def blind2():
    paths = [os.path.join(CH2, f) for f in ("blind_author.json", "blind_ann1.json", "blind_ann2.json")]
    if not all(map(os.path.exists, paths)):
        return []
    auth, a1, a2 = map(jload, paths)
    out = []
    for a in auth:
        top = majority([tuple(a["orders"]), tuple(a1[a["id"]]), tuple(a2[a["id"]])])
        out.append({"id": a["id"], "voice": a["voice"], "text": a["text"], "orders": list(top) if top else None})
    return out


def ctx_blind():
    """The context items with what two of the three readers agree on: the intents, and the place of each order as the
    place matcher reads it from the reader's own piece."""
    paths = [os.path.join(CH2, f) for f in ("ctx_blind_author.json", "ctx_blind_ann1.json", "ctx_blind_ann2.json")]
    if not all(map(os.path.exists, paths)):
        return []
    auth, a1, a2 = map(jload, paths)
    out = []
    for a in auth:
        reads = [a, a1[a["id"]], a2[a["id"]]]
        orders = majority([tuple(r["orders"]) for r in reads])
        places = majority([tuple(place(p) for p in r["pieces"]) for r in reads])
        out.append({"id": a["id"], "voice": a["voice"], "before": a["before"], "bot": a["bot"], "text": a["line"], "pair": a.get("pair"),
                    "orders": list(orders) if orders else None, "places": list(places) if places is not None else None,
                    "route": leans(a["line"], a["pieces"])})
    return out


def held_truth():
    """The typed held-out single lines of fold 0 read again as LISTS under spec_chain.json by two blind readers
    (chains2/held_ann1.json, held_ann2.json): line id -> the list both give. Their one-intent labels come from a spec
    that allowed one intent a line, so a decoder that finds the two orders of "flash the room and then entry" is
    marked wrong by them."""
    paths = [os.path.join(CH2, f) for f in ("held_ann1.json", "held_ann2.json")]
    if not all(map(os.path.exists, paths)):
        return {}
    a, b = map(jload, paths)
    return {k: a[k] for k in a if a[k] == b.get(k)}


def heard_rows(rows, path, cond="vctkB"):
    h = jload(path).get(cond, {}) if os.path.exists(path) else {}
    return [dict(t, text=h[t["id"]]) for t in rows if h.get(t["id"], "").strip()]


def heard3(rows, path):
    """Every r6 and cs line as each of three unseen speakers was heard (voice_chains.py test3): ids id@condition."""
    return [dict(t, id=f"{t['id']}@{c}") for c in UNSEEN for t in heard_rows(rows, path, c)]


def ctx_heard3(rows):
    """The context items the same way: the line and the lines before it as heard; the bot's line is its own text."""
    return [dict(t, id=f"{t['id']}@{c}", text=line, before=before, pair=f"{t['pair']}@{c}" if t["pair"] else None)
            for t, before, line, c in context_heard(rows, UNSEEN, os.path.join(CH2, "ctx_blind_heard.json"))]


def ctx_heardline3(rows):
    """The same with only the line as heard and the lines before it as the player said them: what the decoder gets
    when the game keeps an earlier order as it was understood, not as the recognizer printed it."""
    return [dict(t, before=by_id[t["id"].split("@")[0]]["before"]) for by_id in [{r["id"]: r for r in rows}] for t in ctx_heard3(rows)]


def tests():
    _, test = D.folds()[0]
    items = {i["id"]: i for i in B.LINES}
    held = sorted({r["id"].split("|", 1)[1] for r in test})
    typed = [{"text": items[k]["text"], "maj": items[k]["maj"]} for k in held]
    heard = [{"text": B.heard("vctkB")[k], "maj": items[k]["maj"]} for k in held if k in B.SPOKEN]
    rows, _ = D.folds()[0]
    pool = [r for r in rows if not C.has_then(r["text"]) and C.part_ok(r)]
    rng = random.Random(3002)
    b1 = C.blind()
    b2 = blind2()
    cb = ctx_blind()
    return {"singles": [{"id": r["id"], "text": r["text"]} for r in test],
            "singles_ctx": [{"id": r["id"], "text": r["text"], "before": [rng.choice(pool)["text"]], "bot": None} for r in test if r["id"].startswith("typed|")],
            "joined": compose(list(filter(C.part_ok, typed)), C.JOIN_TRAIN, C.N_TEST, random.Random(2001), "joined"),
            "unseen": compose(list(filter(C.part_ok, typed)), C.JOIN_TEST, C.N_TEST, random.Random(2002), "unseen"),
            "heard": compose(list(filter(C.part_ok, heard)), C.JOIN_TEST, C.N_TEST, random.Random(2003), "heard"),
            "blind": b1, "blind_heard": heard_rows(b1, os.path.join(C.CH, "blind_heard.json")),
            "blind2": b2, "blind2_heard": heard_rows(b2, os.path.join(CH2, "blind_heard.json")),
            "blind2_heard3": heard3(b2, os.path.join(CH2, "blind_heard.json")),
            "ctx": cb, "ctx_heard3": ctx_heard3(cb), "ctx_heardline3": ctx_heardline3(cb)}


SETS = {"names": ("singles", "joined", "unseen", "heard", "blind", "blind_heard", "blind2", "blind2_heard", "blind2_heard3"),
        "pieces": ("singles", "singles_ctx", "joined", "unseen", "heard", "blind", "blind_heard", "blind2", "blind2_heard", "blind2_heard3", "ctx", "ctx_heard3",
                   "ctx_heardline3")}


def adapter_dir(variant, seed):
    return os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", f"coop-{LLM.get(variant, C.NAME)}-qlora-chains2-v54", f"{variant}_seed{seed}"))


def out_path(variant, seed):
    return os.path.join(HERE, f"chains2_54_{variant}_s{seed}.json")


def answers(model, turns, variant, seed, extra):
    t0 = time.time()
    ts = tests()
    pred = {}
    for name in SETS[KIND[variant]]:
        if variant in FINAL and name in HELD_SETS:        # trained on those lines
            continue
        texts = [t["text"] if KIND[variant] == "names" else turn(t.get("before", []), t.get("bot"), t["text"]) for t in ts[name]]
        pred[name] = dict(zip([t["id"] for t in ts[name]], C.generate(model, turns, texts, max_new=MAX_NEW[KIND[variant]])))
    json.dump({"variant": variant, "seed": seed, **extra, "answer_s": round(time.time() - t0), "pred": pred}, io.open(out_path(variant, seed), "w", encoding="utf-8"), indent=1)
    print(f"chains2 {variant} seed {seed}: " + ", ".join(f"{k} {len(v)}" for k, v in pred.items()) + f" answered in {time.time() - t0:.0f}s", flush=True)


def train(variant, seed):
    t0 = time.time()
    rows, counts = training(variant)
    name = LLM.get(variant, C.NAME)
    model, turns = Q.train(name, rows, seed, Q.TAGS["r16"], system=SYSTEM[KIND[variant]], checkpoint=True)
    d = adapter_dir(variant, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[name], **Q.TAGS["r16"], "system": SYSTEM[KIND[variant]], **extra}, io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1)
    print(f"chains2 {variant} seed {seed}: {counts}, {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    answers(model, turns, variant, seed, extra)


def answer(variant, seed):
    from peft import PeftModel
    model, tok = Q.load(LLM.get(variant, C.NAME))
    model = PeftModel.from_pretrained(model, adapter_dir(variant, seed))
    old = jload(out_path(variant, seed))
    answers(model, Q.Turns(tok, SYSTEM[KIND[variant]]), variant, seed, {k: old[k] for k in ("rows", "n_rows", "train_s")})


def check():
    """The classifier as the teacher's calculator, as chains_v54.check: a line or an item is kept when the v54 ensemble
    reads every piece as the teacher labelled it."""
    def run(label, rows, key):
        picks, cfg = C.bot_picks([{"id": f"{t['id']}#{k}", "text": p} for t in rows for k, p in enumerate(t["pieces"])])
        n = agree = 0
        conf = Counter()
        for t in rows:
            assert len(t["orders"]) == len(t["pieces"]) and set(t["orders"]) <= set(V.INTENTS), t["id"]
            got = [picks[f"{t['id']}#{k}"] for k in range(len(t["pieces"]))]
            t["classifier"] = [g[0] for g in got]
            t["kept"] = t["classifier"] == t["orders"]
            for want, g in zip(t["orders"], got):
                n += 1
                agree += g[0] == want
                if g[0] != want:
                    conf[(want, "unsure" if g[0] == "NONE" and g[1][0] != "NONE" else g[0])] += 1
        kept = [t for t in rows if t["kept"]]
        print(f"{label}: {len(rows)} {key}, {n} pieces; the classifier reads {agree} as labelled ({100 * agree / n:.1f}%); kept {len(kept)} ({100 * len(kept) / len(rows):.1f}%)")
        print(f"  kept by number of orders: " + ", ".join(f"{g}: {sum(len(t['orders']) == g for t in kept)}/{sum(len(t['orders']) == g for t in rows)}" for g in sorted({len(t['orders']) for t in rows})))
        print("  the commonest disagreements (teacher -> classifier): " + "; ".join(f"{a} -> {b} x{c}" for (a, b), c in conf.most_common(10)))
        return rows

    lines = []
    for f in ("teacher_a.json", "teacher_b.json"):
        if os.path.exists(os.path.join(CH2, f)):
            lines += run(f, jload(CH2, f), "lines")
    if lines:
        json.dump(lines, io.open(os.path.join(CH2, "teacher_checked.json"), "w", encoding="utf-8"), indent=1)
    if os.path.exists(os.path.join(CH2, "ctx_teacher.json")):
        ctx = run("ctx_teacher.json", jload(CH2, "ctx_teacher.json"), "items")
        json.dump(ctx, io.open(os.path.join(CH2, "ctx_checked.json"), "w", encoding="utf-8"), indent=1)
        print(f"  items whose pieces differ from the line: {sum(leans(x['line'], x['pieces']) for x in ctx)}; kept of them {sum(x['kept'] and leans(x['line'], x['pieces']) for x in ctx)}")


def fold0(seed):
    """A fold-0 teacher of distill_v54.py trained again and kept this time (models/coop-deberta-v3-base-fold0-v54/seed<SEED>,
    weights not in git). The three of them read what a decoder made of a held-out line; the v54 ensemble itself was
    trained on those lines and would read their pieces too kindly."""
    t0 = time.time()
    rows, test = D.folds()[0]
    ep = max(1, round(B.EPOCHS * B.steps(len(B.training_set(B.LINES, B.SEEDS))) / B.steps(len(rows))))
    probs, model, tok = T.train_predict("base", rows, test, seed, D.DEVICE, epochs=ep)
    d = os.path.join(FOLD0, f"seed{seed}")
    os.makedirs(d, exist_ok=True)
    model.to("cpu").save_pretrained(d, safe_serialization=True)
    tok.save_pretrained(d)
    old = jload(HERE, f"kd54_teacher_s{seed}.json")["0"]["test"]
    top = lambda row: max(range(len(row)), key=row.__getitem__)  # noqa: E731
    same = sum(top(probs[k]) == top(old[k]) for k in probs)
    json.dump({"training_lines": len(rows), "epochs": ep, "seed": seed, "same_top_intent_as_kd54_teacher": [same, len(probs)]}, io.open(os.path.join(d, "trained_on.json"), "w"), indent=1)
    print(f"fold-0 teacher seed {seed}: {len(rows)} lines, {ep} epochs, {time.time() - t0:.0f}s; its top intent is the kd54 teacher's on {same} of {len(probs)} test rows", flush=True)


def read():
    """Every piece the pieces decoders wrote, every blind line and every context line, read by the v54 ensemble with
    its gate and threshold: text (as the bot gets it) -> [pick, top intent, confidence] (chains2_54_picks.json). And
    what the decoders made of the held-out lines of fold 0, read by the fold's own three teachers (fold0), if they
    are there (chains2_54_picks0.json)."""
    ts = tests()
    texts = {B.norm(t["text"]) for name in ts if name not in HELD_SETS for t in ts[name]}
    held = set()
    for fn in os.listdir(HERE):
        if fn.startswith("chains2_54_pieces") and fn.endswith(".json"):
            for name, d in jload(HERE, fn)["pred"].items():
                got = {B.norm(p) for a in d.values() for p in a.split("\n") if p.strip()}
                texts |= got
                if name in HELD_SETS:
                    held |= got

    def write(texts, path, members=None):
        texts = sorted(t for t in texts if t)
        picks, _ = C.bot_picks([{"id": str(n), "text": t} for n, t in enumerate(texts)], members)
        json.dump({t: [picks[str(n)][0], picks[str(n)][1][0], round(picks[str(n)][1][1], 3)] for n, t in enumerate(texts)},
                  io.open(os.path.join(HERE, path), "w", encoding="utf-8"), indent=0)
        print(f"{len(texts)} texts read -> {path}", flush=True)

    write(texts, "chains2_54_picks.json")
    dirs = [os.path.join(FOLD0, f"seed{s}") for s in (0, 1, 2)]
    if all(os.path.exists(os.path.join(d, "config.json")) for d in dirs):
        write(held, "chains2_54_picks0.json", dirs)


def split(a):
    return [p.strip() for p in a.split("\n") if p.strip()]


def orders_of(pieces, picks):
    """The bot's reading of rewritten orders: each piece's pick; a piece it takes for no order (or is unsure of) drops out."""
    got = [picks[B.norm(p)][0] for p in pieces if B.norm(p) in picks]
    return [g for g in got if g != "NONE"] or ["NONE"]


def score(wrong=False):
    ts = tests()
    items = {i["id"]: i for i in B.LINES}
    picks = jload(HERE, "chains2_54_picks.json") if os.path.exists(os.path.join(HERE, "chains2_54_picks.json")) else {}
    # what a decoder made of a held-out line is read by the fold's own teachers when they are there (fold0), else by
    # the v54 ensemble, which was trained on the line
    picks0 = jload(HERE, "chains2_54_picks0.json") if os.path.exists(os.path.join(HERE, "chains2_54_picks0.json")) else {}
    reader = lambda name: picks0 if picks0 and name in HELD_SETS else picks  # noqa: E731
    print("pieces of held-out lines are read by " + ("the fold's own three teachers" if picks0 else "the v54 ensemble, which has seen those lines whole (run `fold0` and `read`)"))
    summary = {}

    def note(variant, key, value):
        summary.setdefault((variant, key), []).append(value)

    tf = [jload(HERE, f"kd54_teacher_s{s}.json") for s in (0, 1, 2)]
    ens = {k: [sum(r["0"]["test"][k][j] for r in tf) / 3 for j in range(len(V.INTENTS))] for k in tf[0]["0"]["test"]}
    cfg = jload(C.BOT, "bot_config.json")
    oof = lambda k: V.pick(ens[k], cfg["gate"], cfg["threshold"])[0]  # noqa: E731
    for name in ("blind", "blind2", "ctx"):
        rows = ts[name]
        if rows:
            print(f"{name}: {len(rows)} items, two of three readers agree on the intents of {sum(t['orders'] is not None for t in rows)}"
                  + (f", and on every place of {sum(t['places'] is not None for t in rows)}; {sum(t['route'] for t in rows)} lean on the context" if name == "ctx" else ""))

    def crit(ids, pick_of):
        near = cross = 0
        for k in ids:
            it, p = items[k.split("|", 1)[1]], pick_of(k)
            good = p is not None and (p in it["accept"] or V.FAMILY[p] == V.FAMILY[it["maj"]])
            near += good
            cross += not good and p != "NONE"
        return f"{100 * near / len(ids):6.1f} {100 * cross / len(ids):9.1f}% {100 * (near - 2 * cross) / len(ids):10.1f}"

    def chain_table(pred, got_of, variant):
        print(f"  {'lines with several orders: the list exact':60s} {'n':>5s} {'exact':>7s} {'right count':>12s}")
        for name, label in (("blind2", "this round's blind lines, typed"), ("blind2_heard", "  this round's blind lines (r6, cs) heard from an unseen voice"),
                            ("blind2_heard3", "  the same heard from three unseen voices"),
                            ("blind", "the first blind lines (development), typed"), ("blind_heard", "  the first blind lines (r6, cs) heard from an unseen voice"),
                            ("joined", "held-out lines, training patterns"), ("unseen", "held-out lines, unseen patterns"),
                            ("heard", "held-out lines heard from unseen voices, unseen patterns")):
            rows = [t for t in ts[name] if t.get("orders")]
            if not rows or name not in pred:
                continue
            groups = [(label, rows)]
            if name.startswith("blind") and not name.endswith("heard"):
                groups += [(f"    {w}", [t for t in rows if f(len(t["orders"]))]) for w, f in (("one order", lambda n: n == 1), ("two orders", lambda n: n == 2), ("three orders", lambda n: n == 3), ("four orders", lambda n: n == 4))]
            for lab, sub in groups:
                if sub:
                    got = [got_of(name, t) for t in sub]
                    exact = 100 * sum(g == t['orders'] for g, t in zip(got, sub)) / len(sub)
                    print(f"  {lab:60s} {len(sub):5d} {exact:7.1f} {100 * sum(len(g) == len(t['orders']) for g, t in zip(got, sub)) / len(sub):12.1f}")
                    note(variant, f"{label.strip()}{' / ' + lab.strip() if lab != label else ''}", exact)
            if wrong and name == "blind2":
                for t in rows:
                    if got_of(name, t) != t["orders"]:
                        print(f"      {t['id']}  {t['text']!r}\n          truth {t['orders']}  answer {pred[name][t['id']]!r} -> {got_of(name, t)}")

    held = held_truth()
    if held:
        print(f"the {len([t for t in ts['singles'] if t['id'].startswith('typed|')])} typed held-out single lines read as lists: two blind readers agree on {len(held)}, "
              f"{sum(len(v) > 1 for v in held.values())} of them several orders")

    def held_table(got_of, variant, what):
        """The old single lines against the lists the two readers agree on."""
        if not held:
            return
        print(f"  {'held-out single lines against their reading as lists, ' + what:60s} {'n':>5s} {'exact':>7s}   (the ensemble alone)")
        for cond, label in (("typed", "typed"), ("vctkB", "heard from unseen voices")):
            ids = [t["id"] for t in ts["singles"] if t["id"].split("|", 1)[0] == cond and t["id"].split("|", 1)[1] in held]
            for lab, sub in ((label, ids), ("    one order", [k for k in ids if len(held[k.split("|", 1)[1]]) == 1]), ("    several orders", [k for k in ids if len(held[k.split("|", 1)[1]]) > 1])):
                if sub:
                    exact = 100 * sum(got_of(k) == held[k.split('|', 1)[1]] for k in sub) / len(sub)
                    alone = 100 * sum([oof(k)] == held[k.split('|', 1)[1]] for k in sub) / len(sub)
                    print(f"  {lab:60s} {len(sub):5d} {exact:7.1f}   ({alone:.1f})")
                    if lab == label:
                        note(variant, f"old single lines as lists, {what}, {label}", exact)
                        note("the ensemble alone", f"old single lines as lists, {label}", alone)

    for fn in sorted(f for f in os.listdir(HERE) if f.startswith("chains2_54_") and f.endswith(".json") and "_picks" not in f):
        r = jload(HERE, fn)
        pred, variant = r["pred"], r["variant"]
        print(f"\nvariant {variant}, seed {r['seed']}: {r['n_rows']} rows ({r['rows']}), {r['train_s']} s of training, {r['answer_s']} s of answers")
        if KIND[variant] == "names":
            chain_table(pred, lambda name, t: C.parse(pred[name][t["id"]]), variant)
            if "singles" not in pred:         # trained on every line: no held-out line to answer
                continue
            held_table(lambda k: C.parse(pred["singles"][k]), variant, "the decoder alone")
            print(f"  {'held-out single lines (no threshold)':60s} {'n':>5s} {'one intent':>11s} {'near':>6s} {'wrong fam':>10s} {'criterion':>10s}")
            def single(k):
                """The one intent of an answer; an answer that is a list or not a name is no pick at all."""
                p = C.parse(pred["singles"][k])
                return p[0] if len(p) == 1 and p[0] in V.FAMILY else None

            for cond, label in (("typed", "typed"), ("vctkB", "heard from unseen voices")):
                ids = [t["id"] for t in ts["singles"] if t["id"].split("|", 1)[0] == cond]
                one = sum(len(C.parse(pred["singles"][k])) == 1 for k in ids)
                print(f"  {label:60s} {len(ids):5d} {100 * one / len(ids):11.1f} " + crit(ids, single))
            continue
        if not picks:
            print("  (run `read` first)")
            continue
        chain_table(pred, lambda name, t: orders_of(split(pred[name][t["id"]]), reader(name)), variant)
        if "singles" in pred:                 # not for a decoder trained on every line
            print(f"  {'held-out lines joined: the parts written back word for word':60s} {'n':>5s} {'exact':>7s}")
            for name in ("joined", "unseen", "heard"):
                rows = ts[name]
                print(f"  {name:60s} {len(rows):5d} {100 * sum([B.norm(p) for p in split(pred[name][t['id']])] == [B.norm(p) for p in t['pieces']] for t in rows) / len(rows):7.1f}")
            text_of = {t["id"]: t["text"] for t in ts["singles"]}

            def same_as_said(name, k):
                return [B.norm(p) for p in split(pred[name][k])] == [B.norm(text_of[k])]

            def one_pick(name, k):
                """The bot's pick for a held-out single line the decoder wrote back: unchanged, the fold's ensemble's own
                pick; changed, what the fold's teachers read in the one piece (no pick without them); split, no pick."""
                a = split(pred[name][k])
                if same_as_said(name, k):
                    return oof(k)
                return picks0[B.norm(a[0])][0] if len(a) == 1 and B.norm(a[0]) in picks0 else None

            def through(k):
                """The same as a list, for held_table: a split line is the list of what is read in its pieces."""
                a = split(pred["singles"][k])
                return [oof(k)] if same_as_said("singles", k) else orders_of(a, reader("singles"))

            print(f"  {'held-out single lines through the decoder':60s} {'n':>5s} {'one piece':>10s} {'unchanged':>10s} {'near':>6s} {'wrong fam':>10s} {'criterion':>10s}   (the ensemble alone)")
            for name, cond, label in (("singles", "typed", "typed"), ("singles", "vctkB", "heard from unseen voices"), ("singles_ctx", "typed", "typed, an unrelated earlier line in front")):
                ids = [t["id"] for t in ts[name] if t["id"].split("|", 1)[0] == cond]
                one = sum(len(split(pred[name][k])) == 1 for k in ids)
                res = crit(ids, lambda k: one_pick(name, k))
                print(f"  {label:60s} {len(ids):5d} {100 * one / len(ids):10.1f} {100 * sum(same_as_said(name, k) for k in ids) / len(ids):10.1f} " + res + f"   ({crit(ids, oof).split()[-1]})")
                note(variant, f"old single lines through the decoder, criterion, {label}", float(res.split()[-1]))
                note(variant, f"old single lines written back unchanged, {label}", 100 * sum(same_as_said(name, k) for k in ids) / len(ids))
                if name == "singles":
                    note("the ensemble alone", f"old single lines, criterion, {label}", float(crit(ids, oof).split()[-1]))
            held_table(through, variant, "the decoder alone")
        def ok(t, pieces):
            """(the intents are right, the intents and every place are right) for a context item."""
            intents = orders_of(pieces, picks) == t["orders"]
            places = t["places"] is None or [place(p) for p in pieces] == [tuple(x) if x is not None else None for x in t["places"]]
            return intents, intents and places

        for cname, clabel in (("ctx", "lines with a context, typed"), ("ctx_heard3", "lines with a context (r6, cs) heard from three unseen voices"),
                              ("ctx_heardline3", "the same, the earlier lines as the player said them")):
            rows = [t for t in ts[cname] if t["orders"]]
            if not rows or cname not in pred:
                continue
            print(f"  {clabel:60s} {'n':>5s} {'intents':>8s} {'and places':>11s}   (the bot today on the bare line: intents, and places)")
            pairs = {}
            for lab, sub in (("all items", rows), ("  the line leans on its context", [t for t in rows if t["route"]]), ("  the line stands by itself", [t for t in rows if not t["route"]])):
                res = [ok(t, split(pred[cname][t["id"]])) for t in sub]
                bare = [ok(t, [t["text"]]) for t in sub]
                print(f"  {lab:60s} {len(sub):5d} {100 * sum(a for a, _ in res) / len(sub):8.1f} {100 * sum(b for _, b in res) / len(sub):11.1f}   ({100 * sum(a for a, _ in bare) / len(sub):.1f}, {100 * sum(b for _, b in bare) / len(sub):.1f})")
                note(variant, f"{clabel}: intents and places / {lab.strip()}", 100 * sum(b for _, b in res) / len(sub))
                note("the ensemble alone", f"{clabel}: intents and places / {lab.strip()}", 100 * sum(b for _, b in bare) / len(sub))
            for t in rows:
                if t["pair"]:
                    pairs.setdefault(t["pair"], []).append(ok(t, split(pred[cname][t["id"]]))[1])
            full = [v for v in pairs.values() if len(v) == 2]
            print(f"  {'  pairs (one line, two contexts) with both items right':60s} {len(full):5d} {'':8s} {100 * sum(all(v) for v in full) / max(len(full), 1):11.1f}")
            note(variant, f"{clabel}: pairs with both items right", 100 * sum(all(v) for v in full) / max(len(full), 1))
            if wrong and cname == "ctx":
                for t in rows:
                    if not ok(t, split(pred[cname][t["id"]]))[1]:
                        print(f"      {t['id']}  before {t['before']} bot {t['bot']!r} now {t['text']!r}\n          truth {t['orders']} {t['places']}  answer {split(pred[cname][t['id']])} -> {orders_of(split(pred[cname][t['id']]), picks)}")
        # the bot wired: the router sends a line to the decoder or to the ensemble
        rnd = "final" if variant in FINAL else "r3" if "3" in variant else "r2"
        rp = os.path.join(HERE, f"router54_{rnd}_{ROUTER}_s0.json")
        if not os.path.exists(rp):
            continue
        import router_v54 as R
        pr = jload(rp)["probs"]
        print(f"  the bot wired through the router ({rnd} {ROUTER}): a line it sends on is rewritten by this decoder, every other line goes to the ensemble as today")
        print(f"  {'':60s} {'n':>5s} {'sent on':>8s} {'exact':>7s}   (the ensemble alone)")
        for name, label in (("blind2", "this round's blind lines, typed"), ("blind2_heard", "  this round's blind lines (r6, cs) heard from an unseen voice"),
                            ("blind2_heard3", "  the same heard from three unseen voices"), ("ctx", "lines with a context, typed (intents and places)"),
                            ("ctx_heard3", "  lines with a context heard from three unseen voices")):
            rows = [t for t in ts[name] if t.get("orders")]
            if not rows or name not in pr or name not in pred:
                continue
            hit = alone = sent = 0
            for t in rows:
                go = pr[name][t["id"]] >= R.CUT
                sent += go
                pieces = split(pred[name][t["id"]]) if go else [t["text"]]
                if name.startswith("ctx"):
                    hit += ok(t, pieces)[1]
                    alone += ok(t, [t["text"]])[1]
                else:
                    hit += orders_of(pieces, picks) == t["orders"]
                    alone += orders_of([t["text"]], picks) == t["orders"]
            print(f"  {label:60s} {len(rows):5d} {100 * sent / len(rows):7.1f}% {100 * hit / len(rows):7.1f}   ({100 * alone / len(rows):.1f})")
            note(variant, f"wired through the router / {label.strip()}", 100 * hit / len(rows))
            note("the ensemble alone", label.strip(), 100 * alone / len(rows))
        if "singles" not in pred:
            continue
        print(f"  {'held-out single lines':60s} {'n':>5s} {'sent on':>8s} {'near':>6s} {'wrong fam':>10s} {'criterion':>10s}   (the ensemble alone)")
        for cond, label in (("typed", "typed"), ("vctkB", "heard from unseen voices")):
            ids = [t["id"] for t in ts["singles"] if t["id"].split("|", 1)[0] == cond]
            go = {k: pr["singles"][k] >= R.CUT for k in ids}
            res = crit(ids, lambda k: one_pick("singles", k) if go[k] else oof(k))
            print(f"  {label:60s} {len(ids):5d} {100 * sum(go.values()) / len(ids):7.1f}% " + res + f"   ({crit(ids, oof).split()[-1]})")
            note(variant, f"wired through the router / old single lines, criterion, {label}", float(res.split()[-1]))
        held_table(lambda k: through(k) if pr["singles"][k] >= R.CUT else [oof(k)], variant, "wired through the router")

    # every seed in one table
    seeds = max((len(v) for (variant, _), v in summary.items() if variant != "the ensemble alone"), default=0)
    if seeds > 1:
        print(f"\nover the seeds (mean, lowest to highest); the ensemble alone has no seed")
        for (variant, key), v in summary.items():
            if variant == "the ensemble alone":
                print(f"  {'the ensemble alone: ' + key:104s} {v[0]:6.1f}")
            else:
                print(f"  {variant + ': ' + key:104s} {sum(v) / len(v):6.1f}   {min(v):5.1f} .. {max(v):5.1f}   ({len(v)} seeds)")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "check":
        check()
    elif mode == "train":
        train(sys.argv[2], int(sys.argv[3]))
    elif mode == "answer":
        answer(sys.argv[2], int(sys.argv[3]))
    elif mode == "read":
        read()
    elif mode == "fold0":
        fold0(int(sys.argv[2]))
    elif mode == "score":
        score("--wrong" in sys.argv)
    else:
        sys.exit(__doc__)
