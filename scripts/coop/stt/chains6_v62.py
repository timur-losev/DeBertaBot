"""Round v62 of the chains study (2026-10-22): the decoder for the v6x line, three languages in, English orders out.
The owner: "сделать multilingual ... русский, английский, испанский"; then, after the probe of 2026-10-22 (reports/Мультиязычный
бот - русский, английский, испанский.md, section 7a: decoder v59 copies Russian and Spanish lines as they are, 10/39 and
13/39; plain Qwen3-1.7B with a translation prompt 30/39 and 28/39), "да" to training the decoder on three languages.

What changes against round six (chains5_v59.py):
  - the labels are v61's (57 intents: the shooter's 47 and the farmer's and builder's ten) and the calculator is the v61 ensemble;
    the English singles are v61's rows (lines, seeds, the owner's heard lines, the transcripts, the accented ones);
  - the player's lines also come in Russian and Spanish (chains2/ml_v62: prep_ml_v62.py cut the batches, AI translators wrote
    them under TRANSLATE.md): the v61 authored lines and 12 seeds per intent as singles, round two's teacher chains and round six's
    context items; the answer is always the English one, so the decoder learns to translate and to split in one step;
  - Russian and Spanish lines of several orders made from the translated singles with each language's own joiners (ML_JOIN);
  - half of the Russian and Spanish inputs lowercased without their final .!? (what the game's recognizer hands over);
  - the system turn says that the player speaks English, Russian or Spanish and that the orders are written in English.
The decoder starts from plain Qwen3-1.7B with a new LoRA (not round six's adapter: that one learned to copy every single line).

    python chains6_v62.py data      the rows, counted (a dry run)
    python chains6_v62.py train     pieces7ml_final seed 0 -> models/coop-qwen3-qlora-chains6-v62/pieces7ml_final_seed0; answers on
                                    round three's English test sets (chains6_62_pieces7ml_final_s0.json) and on the Russian and
                                    Spanish ones (chains6_62_ml_pieces7ml_final_s0.json)
    python chains6_v62.py baselines the Russian and Spanish test sets answered by round six's decoder (no router) and by plain
                                    Qwen3-1.7B with a translation prompt -> chains6_62_ml_v59.json, chains6_62_ml_qwen.json
    python chains6_v62.py gguf      the adapter merged, GGUF in 4 bits
    python chains6_v62.py export    models/coop-chain-v62/cpp: decoder v62 with router v59 (for English lines)
    python chains6_v62.py score     English: round six's decoder against v62, both through router v59; Russian and Spanish: v59, plain
                                    Qwen and v62 with no router; every piece read by the v61 ensemble -> chains6_62_score.log
"""
import io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v61"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, COOP)
import coop_v2 as V                    # the v61 vocabulary, imported first
import build_v61
sys.modules["build_v54"] = build_v61   # the chain modules import build_v54 by name; they get v61's lines and seeds
import torch
import qlora_v54 as Q
import chains_v54 as C
import chains2_v54 as C2
assert V.TAG == "v61" and len(V.INTENTS) == 57, (V.TAG, len(V.INTENTS))

MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
C.BOT = os.path.join(MODELS, "coop-deberta-v3-ens3-v61")    # the calculator
VARIANT, ROWS_OF = os.environ.get("CHAINS6_VARIANT", "pieces7ml_final"), "pieces3"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = ROWS_OF
ADAPTER = os.path.join(MODELS, "coop-qwen3-qlora-chains6-v62")
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}")
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains6_62_{variant}_s{seed}.json")
ML = os.path.join(C2.CH2, "ml_v62")
LANGS = ("ru", "es")
SYSTEM_V62 = ("You are the AI teammate in a tactical co-op shooter. You get the player's line (\"now\") as a speech-to-text transcript "
              "that may be garbled, and sometimes what was said before it. The player speaks English, Russian or Spanish. Write what "
              "the player orders now in English, as orders that stand by themselves, one per line, in the order you must carry them "
              "out. An English line that gives one order or none is written back as it is; a Russian or Spanish one is written in "
              "English.")
# round six's recipe, the same numbers
V55_COPIES = V58_COPIES = V59_COPIES = 6
CTX_EXTRA = ((0, 0.4), (1, 0.25), (2, 0.2), (3, 0.15))
P_CONTEXT, N_BEFORE = 0.5, ((1, 0.35), (2, 0.25), (3, 0.15), (4, 0.12), (5, 0.13))
# the Russian and Spanish part
ML_COMPOSED = 1200          # lines of several orders per language, made from the translated singles
ML_CHAIN_COPIES = 1         # the translated teacher chains
ML_CTX_COPIES = 2           # the translated context items, each copy with other older lines
P_LOWER = 0.5               # an input lowercased and without its final .!?
ML_JOIN = {
    "ru": ["{a}, потом {b}", "{a}, а потом {b}", "{a} и {b}", "{a}, затем {b}", "сначала {a}, потом {b}", "{a}. {b}", "{a} {b}",
           "{a}, после этого {b}", "{a}, а затем {b}", "{a} и потом {b}", "{a}, а как закончишь, {b}",
           "{a}, {b}, потом {c}", "{a}, потом {b}, потом {c}", "сначала {a}, потом {b}, а потом {c}", "{a}. {b}. {c}", "{a}, {b} и {c}"],
    "es": ["{a} y luego {b}", "{a}, luego {b}", "{a} y {b}", "primero {a}, luego {b}", "{a}, después {b}", "{a}. {b}", "{a} {b}",
           "{a} y después {b}", "{a}, y cuando termines {b}", "{a}, entonces {b}",
           "{a}, {b} y luego {c}", "primero {a}, luego {b}, después {c}", "{a}. {b}. {c}", "{a}, {b} y {c}"]}
# The English chains and context items of the speech-to-text author keep the recognizer's slips as heard ("look at the so far",
# "bridge the wall"): rule 11 of the context spec, for English input. A Russian or Spanish player says «диван» / «sofá», and
# the translators wrote what was meant (the translator of ru_chain_00 pointed this out); the place matcher knows none of these
# slips. So in the Russian and Spanish rows the English answer says what was meant. 61 of 2765 pieces.
SLIPS = {"so far": "sofa", "bridge": "breach", "flesh": "flash", "repel": "rappel", "drown": "drone", "rough": "roof", "volt": "vault",
         "base man": "basement", "stars": "stairs", "stares": "stairs", "cable": "table", "vest door": "west door", "mean door": "main door"}


def mend(pieces):
    out = []
    for p in pieces:
        for k, v in SLIPS.items():
            p = re.sub(rf"\b{k}\b", v, p, flags=re.I)
        out.append(p)
    return out


# the developer's 82 cases of the probe (reports/..., section 7a), kept with the round as a test set
DEV_CASES = os.path.join(ML, "dev_cases.json")


def jl(*p):
    return json.load(io.open(os.path.join(*p), encoding="utf-8"))


def spoken(t, rng):
    """Half of the inputs as the recognizer hands them over: lowercased, no final .!?"""
    return re.sub(r"[.!?]+$", "", t.strip()).lower() if rng.random() < P_LOWER else t


def translations(lang, kind):
    """id -> the translator's item, over every batch of that language and kind (chains2/ml_v62/out)."""
    out = {}
    for f in sorted(os.listdir(os.path.join(ML, "out"))):
        if f.startswith(f"{lang}_{kind}_") and f.endswith(".json"):
            for it in jl(ML, "out", f)["items"]:
                out[it["id"]] = it
    return out


def sources():
    """The English items prep_ml_v62.py cut into batches, by kind: id -> item."""
    out = {"single": {}, "chain": {}, "ctx": {}}
    for f in sorted(os.listdir(os.path.join(ML, "in"))):
        if f.startswith("ru_") and f.endswith(".json"):
            d = jl(ML, "in", f)
            for it in d["items"]:
                out[d["kind"]][it["id"]] = it
    return out


def ml_rows(pool_en, bots):
    """The Russian and Spanish rows: singles, composed, chains, context items. Returns (rows, counts)."""
    src = sources()
    rows, counts = [], {}
    rng = random.Random(6201)
    for lang in LANGS:
        sing = translations(lang, "single")
        singles = [{"text": sing[i]["text"], "en": s["en"], "maj": s["intent"]} for i, s in src["single"].items() if i in sing]
        pool = [s for s in singles if C.part_ok({"text": s["en"], "maj": s["maj"]})]
        for s in singles:
            rows.append({"lang": lang, "before": None, "text": spoken(s["text"], rng), "pieces": [s["en"]]})
        seen, comp = set(), []
        while len(comp) < ML_COMPOSED:
            m = 2 if rng.random() < 0.7 else 3
            pat = rng.choice([p for p in ML_JOIN[lang] if p.count("{") == m])
            parts = rng.sample(pool, m)
            text = pat.format(**{k: C.tidy(p["text"], pat.startswith("{" + k + "}")) for k, p in zip("abc", parts)})
            if text not in seen:
                seen.add(text)
                comp.append({"lang": lang, "before": None, "text": spoken(text, rng), "pieces": [C.tidy(p["en"], True) for p in parts]})
        rows += comp
        ch = translations(lang, "chain")
        chains = [{"lang": lang, "before": None, "text": spoken(ch[i]["text"], rng), "pieces": mend(s["pieces"])}
                  for i, s in src["chain"].items() if i in ch]
        rows += ML_CHAIN_COPIES * chains
        cx = translations(lang, "ctx")
        ctx = []
        for i, s in src["ctx"].items():
            if i not in cx or len(cx[i].get("before", [])) != len(s["before"]):
                continue
            for _ in range(ML_CTX_COPIES):
                n = min(rng.choices([k for k, _ in CTX_EXTRA], [w for _, w in CTX_EXTRA])[0], 5 - len(s["before"]))
                older = [spoken(rng.choice(singles)["text"], rng) for _ in range(max(0, n))]
                ctx.append({"lang": lang, "before": older + [spoken(b, rng) for b in cx[i]["before"]], "bot": s["bot"],
                            "text": spoken(cx[i]["text"], rng), "pieces": mend(s["pieces"])})
        rows += ctx
        # some singles and composed lines get unrelated earlier lines in the same language, as round six's English rows
        for r in rows:
            if r.get("lang") == lang and r["before"] is None:
                before, bot = [], None
                if rng.random() < P_CONTEXT:
                    k = rng.choices([k for k, _ in N_BEFORE], [w for _, w in N_BEFORE])[0]
                    before = [spoken(rng.choice(singles)["text"], rng) for _ in range(k)]
                    if bots and rng.random() < C2.P_BOT:
                        bot = rng.choice(bots)
                r["before"], r["bot"] = before, bot
        counts[lang] = {"singles": len(singles), "composed": len(comp), "chains": len(chains) * ML_CHAIN_COPIES, "context": len(ctx)}
    return [{"text": C2.turn(r["before"], r.get("bot"), r["text"]), "answer": "\n".join(r["pieces"])} for r in rows], counts


def english_rows():
    """Round six's training with v61's rows (chains5_v59.training): singles, composed, the teacher chains, the context items."""
    rows = build_v61.training_set(build_v61.LINES, build_v61.SEEDS, build_v61.OWNER)
    import make_spec_v55
    fragments = {t for v in make_spec_v55.FRAGMENTS_TO.values() for t in v}
    rows = [r for r in rows if not (r["id"].startswith("seed_") or "|seed_" in r["id"]) or r["text"].strip().lower() not in fragments]
    singles = [r for r in rows if not C.has_then(r["text"])]
    pool = [r for r in singles if C.part_ok(r)]
    out = [{"text": r["text"], "pieces": [r["text"]]} for r in singles]
    out += [{"text": r["text"], "pieces": r["pieces"]} for r in C2.compose(pool, C.JOIN_TRAIN + C2.JOIN4, C.N_COMPOSED, random.Random(1002), "c",
                                                                          sizes=((2, 0.55), (3, 0.30), (4, 0.15)))]
    kept, heard = C2.teacher()
    out += C2.TYPED_COPIES * [{"text": t["text"], "pieces": t["pieces"]} for t in kept]
    n_heard = 0
    for cond in C2.VOICES[ROWS_OF]:
        got = [{"text": heard[cond][t["id"]], "pieces": t["pieces"]} for t in kept if heard.get(cond, {}).get(t["id"], "").strip()]
        n_heard += len(got)
        out += got
    ctx = [x for x in jl(C2.CH2, "ctx_checked_v59.json") if x["kept"]]
    bots = sorted({x["bot"] for x in ctx if x["bot"]})
    rng = random.Random(3001)
    res = []
    for r in out:
        before, bot = [], None
        if rng.random() < P_CONTEXT:
            n = rng.choices([k for k, _ in N_BEFORE], [w for _, w in N_BEFORE])[0]
            before = [rng.choice(pool)["text"] for _ in range(n)]
            if bots and rng.random() < C2.P_BOT:
                bot = rng.choice(bots)
        res.append({"text": C2.turn(before, bot, r["text"]), "answer": "\n".join(r["pieces"])})
    crng = random.Random(3002)
    copies = lambda x: (V59_COPIES if x["id"].startswith("x59_") else V58_COPIES if x["id"].startswith("x58_")   # noqa: E731
                        else V55_COPIES if x["id"].startswith("x55_") else C2.CTX_COPIES)
    for copy in range(max(C2.CTX_COPIES, V55_COPIES, V58_COPIES, V59_COPIES)):
        for x in ctx:
            if copy >= copies(x):
                continue
            n = min(crng.choices([k for k, _ in CTX_EXTRA], [w for _, w in CTX_EXTRA])[0], 5 - len(x["before"]))
            older = [crng.choice(pool)["text"] for _ in range(max(0, n))]
            res.append({"text": C2.turn(older + x["before"], x["bot"], x["line"]), "answer": "\n".join(x["pieces"])})
    old_ctx = [x for x in ctx if not x["id"].startswith(("x58_", "x59_"))]
    v58_ctx = [x for x in ctx if x["id"].startswith("x58_")]
    v59_ctx = [x for x in ctx if x["id"].startswith("x59_")]
    got = [{"text": C2.turn(b, x["bot"], line), "answer": "\n".join(x["pieces"])} for x, b, line, _ in C2.context_heard(old_ctx, C2.VOICES[ROWS_OF])]
    got58 = [{"text": C2.turn(b, x["bot"], line), "answer": "\n".join(x["pieces"])}
             for x, b, line, _ in C2.context_heard(v58_ctx, C2.VOICES[ROWS_OF], os.path.join(C2.CH2, "ctx_teacher_v58_heard.json"))]
    got59 = [{"text": C2.turn(b, x["bot"], line), "answer": "\n".join(x["pieces"])}
             for x, b, line, _ in C2.context_heard(v59_ctx, C2.VOICES[ROWS_OF], os.path.join(C2.CH2, "ctx_teacher_v59_heard.json"))]
    res += got + got58 + got59
    counts = {"singles": len(singles), "composed": C.N_COMPOSED, "teacher": len(kept), "teacher_heard": n_heard, "context": len(ctx),
              "context_heard": len(got) + len(got58) + len(got59)}
    return res, counts, pool, bots


def training():
    en, en_counts, pool, bots = english_rows()
    ml, ml_counts = ml_rows(pool, bots)
    return en + ml, {"en": en_counts, **ml_counts, "en_rows": len(en), "ml_rows": len(ml)}


# ---- the Russian and Spanish test sets ----------------------------------------------------------------------------------

def ml_tests():
    """{set: [{"id", "before", "bot", "text", "orders", "places"}]}: the developer's 82 cases (dev_ru, dev_es) and the blind
    translations of round three's chains and context items (blind2_ru, ctx_ru, blind2_es, ctx_es)."""
    ts = C2.tests()
    out = {}
    dev = jl(DEV_CASES)["items"]
    for lang in LANGS:
        out[f"dev_{lang}"] = [{"id": f"dev_{lang}_{k:02d}", "before": it["lines"][:-1], "bot": None, "text": it["lines"][-1],
                               "orders": [o for o in it["expect"] if o != "NONE"] or ["NONE"], "places": None, "v6x": it.get("v6x", False)}
                              for k, it in enumerate(x for x in dev if x["lang"] == lang)]
        for s in ("blind2", "ctx"):
            p = os.path.join(ML, "test_out", f"{lang}_{s}.json")
            if not os.path.exists(p):
                continue
            tr = {it["id"]: it for it in jl(p)["items"]}
            out[f"{s}_{lang}"] = [{"id": t["id"], "before": tr[t["id"]].get("before", t.get("before", [])), "bot": t.get("bot"),
                                   "text": tr[t["id"]]["text"], "orders": t["orders"], "places": t.get("places")}
                                  for t in ts[s] if t.get("orders") and t["id"] in tr]
    return out


def ml_answers(model, turns, path, extra):
    pred = {}
    for name, items in ml_tests().items():
        texts = [C2.turn(t["before"], t["bot"], re.sub(r"[.!?]+$", "", t["text"].strip()).lower()) for t in items]
        pred[name] = dict(zip([t["id"] for t in items], C.generate(model, turns, texts, max_new=C2.MAX_NEW["pieces"])))
    json.dump({**extra, "pred": pred}, io.open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("ml answers: " + ", ".join(f"{k} {len(v)}" for k, v in pred.items()) + f" -> {path}", flush=True)


def train(seed=0):
    t0 = time.time()
    rows, counts = training()
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=SYSTEM_V62, checkpoint=True)
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": SYSTEM_V62, "p_context": P_CONTEXT, "n_before": N_BEFORE, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"chains6 {VARIANT} seed {seed}: {counts}, {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    C2.answers(model, turns, VARIANT, seed, extra)
    ml_answers(model, turns, os.path.join(HERE, f"chains6_62_ml_{VARIANT}_s{seed}.json"), extra)


def baselines():
    """Round six's decoder (its own system turn, no router) and plain Qwen3-1.7B with a translation prompt on the ru/es sets."""
    from peft import PeftModel
    model, tok = Q.load(C.NAME)
    v59 = PeftModel.from_pretrained(model, os.path.join(MODELS, "coop-qwen3-qlora-chains5-v59", "pieces6_final_seed0"))
    ml_answers(v59, Q.Turns(tok, C2.SYSTEM["pieces"]), os.path.join(HERE, "chains6_62_ml_v59.json"), {"decoder": "round six (v59), no router"})
    with v59.disable_adapter():
        sys_tr = ("You translate a player's voice orders to their AI teammate in a tactical co-op shooter into English. The order is "
                  "Russian or Spanish, as speech-to-text heard it. Write it as short English orders the way a gamer would say them, one "
                  "order per line, in the order they must be carried out. Keep game words: flashbang, smoke, frag, pin, stairs, window. "
                  "If the line is not an order (a question, chatter, yes or no), translate it as it is. Write only the English.")
        ml_answers(v59, Q.Turns(tok, sys_tr), os.path.join(HERE, "chains6_62_ml_qwen.json"), {"decoder": "plain Qwen3-1.7B, translation prompt"})


def gguf(seed=0):
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    """models/coop-chain-v62/cpp: decoder v62 and router v59 (the router decides only for English lines)."""
    sys.argv = [sys.argv[0], VARIANT, str(seed)]
    C2.SYSTEM["pieces"] = SYSTEM_V62       # the exporter writes the system turn (and its chain tests) from here
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v62", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS6_ROUTER", "coop-router-deberta-v3-small-v59"))
    E.main()


REPEAT_LINE = re.compile(r"^\W*(?:(?:uh|um|ok|okay|so|and|yeah|nah|no)\W+)*(?:try (?:that |it |this )?again|again|do (?:that|it|this) again|"
                         r"(?:one more|once more)(?: time)?|same again|more|repeat(?: that)?)\W*(?:please)?\W*$", re.I)
NEGATED = re.compile(r"^\W*(?:(?:no|nah|ok|okay|hey)\W+)*(?:don'?t|do not|never)\b", re.I)


def score():
    """English: round six's decoder against v62 through router v59 on round three's blind sets. Russian and Spanish: v59, plain
    Qwen and v62 with no router. Every piece read by the v61 ensemble; context items also by their places."""
    out = io.StringIO()
    ts = C2.tests()
    en_files = [("round six (v59)", os.path.join(HERE, "chains5_59_pieces6_final_s0.json")),
                ("v62", C2.out_path(VARIANT, 0))]
    en_preds = {n: jl(p)["pred"] for n, p in en_files if os.path.exists(p)}
    router = jl(HERE, "router59_final_small_s0.json")["probs"]
    ml_files = [("v59, no router", os.path.join(HERE, "chains6_62_ml_v59.json")), ("plain Qwen", os.path.join(HERE, "chains6_62_ml_qwen.json")),
                ("v62", os.path.join(HERE, f"chains6_62_ml_{VARIANT}_s0.json"))]
    ml_preds = {n: jl(p)["pred"] for n, p in ml_files if os.path.exists(p)}
    mts = ml_tests()
    texts = set()
    for s in ("blind2", "blind2_heard3", "ctx", "ctx_heard3"):
        texts |= {build_v61.norm(t["text"]) for t in ts[s]}
        for pred in en_preds.values():
            texts |= {build_v61.norm(p) for a in pred.get(s, {}).values() for p in C2.split(a)}
    for pred in ml_preds.values():
        texts |= {build_v61.norm(p) for a_set in pred.values() for a in a_set.values() for p in C2.split(a)}
    texts = sorted(t for t in texts if t)
    got, _ = C.bot_picks([{"id": str(n), "text": t} for n, t in enumerate(texts)])
    picks = {t: [got[str(n)][0]] for n, t in enumerate(texts)}

    # round three's labels are v54's: REVIVE_ME is HELP since v56 (the game's IntentFromLabel maps it so); a repeat or a
    # negation was labelled by rules that changed since (chains5_v59.score shows its numbers with and without them)
    en_text = {t["id"]: t["text"] for s in ("blind2", "ctx") for t in ts[s]}
    touched = lambda t: bool(REPEAT_LINE.match(en_text.get(t["id"], t["text"])) or NEGATED.match(en_text.get(t["id"], t["text"])))  # noqa: E731
    now = lambda orders: ["HELP" if o == "REVIVE_ME" else o for o in orders]   # noqa: E731

    def right(t, pieces, with_places):
        if C2.orders_of(pieces, picks) != now(t["orders"]):
            return False
        return not with_places or t.get("places") is None or [C2.place(p) for p in pieces] == [tuple(x) if x is not None else None for x in t["places"]]

    print("English (round three's blind sets; through router v59 a line under 0.5 goes to the classifier as it is)", file=out)
    print(f"{'':52s}" + "".join(f"{n:>22s}" for n in en_preds), file=out)
    for s, label in (("blind2", "chains, typed"), ("blind2_heard3", "chains, three unseen voices"), ("ctx", "context, typed (+places)"),
                     ("ctx_heard3", "context, three unseen voices (+places)")):
        rows = [t for t in ts[s] if t.get("orders")]
        keep = [t for t in rows if not (REPEAT_LINE.match(t["text"]) or NEGATED.match(t["text"]))]
        for sub, what in ((rows, label), (keep, f"  {label}, no repeats/negations")):
            for wired in (False, True):
                cells = []
                for n, pred in en_preds.items():
                    hit = sum(right(t, C2.split(pred[s][t["id"]]) if not wired or router[s][t["id"]] >= 0.5 else [t["text"]], s.startswith("ctx")) for t in sub)
                    cells.append(f"{100 * hit / max(len(sub), 1):22.1f}")
                print(f"{what + (', router' if wired else ''):52s}" + "".join(cells), file=out)
    print("\nRussian and Spanish (no router: every line to the decoder)", file=out)
    print(f"{'':52s}" + "".join(f"{n:>22s}" for n in ml_preds), file=out)
    for s, items in mts.items():
        keep = [t for t in items if not touched(t)]
        subs = ((items, f"{s}: all {len(items)}"),)
        subs += (([t for t in items if not t.get("v6x")], "  without farm/build"),) if s.startswith("dev") else \
                ((keep, f"  without the {len(items) - len(keep)} repeats and negations"),)
        for sub, label in subs:
            cells = []
            for n, pred in ml_preds.items():
                if s not in pred:
                    cells.append(f"{'-':>22s}")
                    continue
                hit = sum(right(t, C2.split(pred[s][t["id"]]), s.startswith("ctx")) for t in sub)
                cells.append(f"{100 * hit / max(len(sub), 1):22.1f}")
            print(f"{label:52s}" + "".join(cells), file=out)
    print(out.getvalue(), end="")
    io.open(os.path.join(HERE, "chains6_62_score.log"), "w", encoding="utf-8").write(out.getvalue())


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts = training()
        print(json.dumps(counts, ensure_ascii=False, indent=1), len(rows), "rows")
        for r in random.Random(0).sample(rows, 6):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        train(seed)
    elif what == "baselines":
        baselines()
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    elif what == "score":
        score()
    else:
        print(__doc__)
