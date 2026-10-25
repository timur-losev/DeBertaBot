"""Round v64 of the chains study (2026-10-25): decoder v64, for bot v64 (69 intents: melee, holster, the report, the body,
push, roll, drop, and the talking/carrying lines of v62). The owner: "посмотри ещё в последней сессии я пытался заставить
его взять именно картонную коробку, а он не понял. И начинай обучение".

What changes against v63 (chains7_v63.py, its rows kept as they are):
  - the new singles in three languages: every player line v62 and v64 added that the decoder never saw (prep_ml_v64.py: 967
    English lines; chains2/ml_v64/out: their Russian and Spanish translations under TRANSLATE.md). English is written back as it
    is; Russian and Spanish are answered in English. A tenth of them (by id) is held out as the v64 test, never trained on;
  - Russian and Spanish lines of two or three orders, each with at least one new single (ML_JOIN and the «и» / «y» pairs), and
    English pairs with "and": the new orders inside a line of several (different actions only, as in v63);
  - the hand rows (chains2/ml_v64/hand_v64.json): the owner's own lines from the games of 2026-10-24/25 that decoder v63 wrote
    wrong, replayed through the deployed chain («Кати эту катушку» -> "Catch this loop", «Подними эту коробку», «картонную
    коробку», «Голые руки» -> "Go easy", «Убери оружие» -> "Take out your weapon"), and «молодец» right after «иди за мной»;
  - the decoder starts from plain Qwen3-1.7B with a new LoRA, as v63 did; same recipe (r16, 3 epochs) and system turn;
  - the router stays v63's (English lines of one order go to the classifier as they are).

    python chains8_v64.py data       the rows, counted, and the v64 test written (chains2/ml_v64/test_v64.json)
    python chains8_v64.py train      -> models/coop-qwen3-qlora-chains8-v64/pieces9v64_final_seed0; answers on every test set
    python chains8_v64.py answer63   decoder v63's answers on the v64 test (for the comparison)
    python chains8_v64.py gguf | export | score
"""
import io, json, os, random, re, sys, time, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chains7_v63 as P7             # v63's rows (and through it chains6_v62: the v61 vocabulary, the chain modules)
from chains7_v63 import P, C, C2, Q, V, torch

VARIANT = "pieces9v64_final"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = P.ROWS_OF
ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains8-v64")
_adapter63 = C2.adapter_dir
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}") if variant == VARIANT else _adapter63(variant, seed)
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains8_64_{variant}_s{seed}.json")
ML64 = os.path.join(C2.CH2, "ml_v64")
TEST_PATH = os.path.join(ML64, "test_v64.json")
HELD = 0.10                  # of the new singles (by id), the v64 test
SINGLE_COPIES = 2            # each new Russian / Spanish single twice (each copy spoken its own way, with its own older lines)
COMPOSED = 900               # per language: lines of two or three orders, at least one of them new (ML_JOIN)
PAIRS = 700                  # per language (and English): short pairs joined by "and" / «и» / «y», at least one new
HAND_COPIES = 8
# the families of the new intents (coop_v2 v64: the gate's families); the rest are v61's
FAMILY = dict(V.FAMILY, MELEE="melee", HOLSTER="holster", STATUS_REPORT="status", BODY_STATE="body", PUSH="push", ROLL="roll",
              DROP="drop")
FAMILY.update(COLLECT="carry", DELIVER="carry", SEE_THING="see", SEE_ME="see")   # v62 intents not in v61: each its own family otherwise


def held(item_id):
    return zlib.crc32(item_id.encode()) % 1000 < HELD * 1000


def new_singles():
    """{"en": [...], "ru": [...], "es": [...]} of {"id", "text", "en", "maj"}; and the held-out ones the same way."""
    src = {}
    for f in sorted(os.listdir(os.path.join(ML64, "in"))):
        if f.startswith("ru_") and f.endswith(".json"):
            for it in P.jl(ML64, "in", f)["items"]:
                src[it["id"]] = it
    out = {"en": [{"id": i, "text": s["en"], "en": s["en"], "maj": s["intent"]} for i, s in src.items()]}
    for lang in P.LANGS:
        tr = {}
        for f in sorted(os.listdir(os.path.join(ML64, "out"))):
            if f.startswith(f"{lang}_single_") and f.endswith(".json"):
                tr.update({it["id"]: it for it in P.jl(ML64, "out", f)["items"]})
        missing = [i for i in src if i not in tr]
        assert not missing, (lang, len(missing), missing[:5])
        out[lang] = [{"id": i, "text": tr[i]["text"], "en": s["en"], "maj": s["intent"]} for i, s in src.items()]
    train = {k: [x for x in v if not held(x["id"])] for k, v in out.items()}
    test = {k: [x for x in v if held(x["id"])] for k, v in out.items()}
    return train, test


def old_pools():
    """The v62/v63 singles a new one is joined with: per language [{"text", "en", "maj"}] (v63's short pools, both halves)."""
    pools = P7.short_pools()
    return {k: tr + te for k, (tr, te) in pools.items()}


def compose(new, old, lang, pats, n, rng, max_words=None):
    """Lines of len(pattern) orders of different families, the first or a random part new; answers in English."""
    out, seen, tries = [], set(), 0
    ok = lambda x: C.part_ok({"text": x["en"], "maj": x["maj"]}) and x["maj"] not in ("NONE", "KILL_YOURSELF") and (max_words is None or P7.words(x["en"]) <= max_words)  # noqa: E731
    new, old = [x for x in new if ok(x)], [x for x in old if ok(x)]
    while len(out) < n and tries < 60 * n:
        tries += 1
        pat = rng.choice(pats)
        m = pat.count("{")
        parts = [rng.choice(new)] + [rng.choice(new if rng.random() < 0.3 else old) for _ in range(m - 1)]
        rng.shuffle(parts)
        if len({FAMILY.get(p["maj"], p["maj"]) for p in parts}) < m:
            continue
        text = pat.format(**{k: C.tidy(p["text"], pat.startswith("{" + k + "}")) for k, p in zip("abc", parts)})
        if text in seen:
            continue
        seen.add(text)
        out.append({"text": P.spoken(text, rng) if lang != "en" else text, "pieces": [C.tidy(p["en"], True) for p in parts]})
    return out


def with_context(text, pool, rng):
    before = []
    if rng.random() < P.P_CONTEXT:
        k = rng.choices([k for k, _ in P.N_BEFORE], [w for _, w in P.N_BEFORE])[0]
        before = [P.spoken(rng.choice(pool)["text"], rng) for _ in range(k)]
    return before


def v64_rows(rng):
    train, test = new_singles()
    old = old_pools()
    rows, counts = [], {}
    for lang in ("en",) + P.LANGS:
        sing, pool = train[lang], train[lang] + old[lang]
        n = 0
        for copy in range(1 if lang == "en" else SINGLE_COPIES):
            for s in sing:
                text = s["text"] if lang == "en" else P.spoken(s["text"], rng)
                rows.append({"text": C2.turn(with_context(text, pool, rng), None, text), "answer": s["en"].strip()})
                n += 1
        made = [] if lang == "en" else compose(sing, old[lang], lang, P.ML_JOIN[lang], COMPOSED, rng)
        pairs = compose(sing, old[lang], lang, P7.PAIR_JOIN[lang], PAIRS, rng, max_words=P7.SHORT)
        for r in made + pairs:
            rows.append({"text": C2.turn(with_context(r["text"], pool, rng), None, r["text"]), "answer": "\n".join(r["pieces"])})
        counts[lang] = {"singles": n, "composed": len(made), "pairs": len(pairs), "held_out": len(test[lang])}
    hand = P.jl(ML64, "hand_v64.json")["items"]
    for it in hand:
        for copy in range(HAND_COPIES):
            text = P.spoken(it["text"], rng)
            older = with_context(text, train[it["lang"]], rng) if not it["before"] and copy % 2 else []
            rows.append({"text": C2.turn(older + [P.spoken(b, rng) for b in it["before"]], None, text), "answer": "\n".join(it["en"])})
    counts["hand"] = {"items": len(hand), "rows": len(hand) * HAND_COPIES}
    json.dump({k: [{"id": x["id"], "text": x["text"], "en": x["en"], "orders": [x["maj"]]} for x in v] for k, v in test.items()},
              io.open(TEST_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return rows, counts


def training():
    rows, counts, split = P7.training()
    new, ncounts = v64_rows(random.Random(6401))
    counts.update({"v64": ncounts, "v63_rows": len(rows), "v64_rows": len(new)})
    return rows + new, counts, split


def test_answers(model, turns, path):
    test = P.jl(TEST_PATH)
    pred = {}
    for lang, items in test.items():
        texts = [C2.turn([], None, re.sub(r"[.!?]+$", "", t["text"].strip()).lower() if lang != "en" else t["text"]) for t in items]
        pred[lang] = dict(zip([t["id"] for t in items], C.generate(model, turns, texts, max_new=C2.MAX_NEW["pieces"])))
    hand = P.jl(ML64, "hand_v64.json")["items"]
    texts = [C2.turn(it["before"], None, it["text"]) for it in hand]
    pred["hand"] = dict(zip([f"hand_{k:03d}" for k in range(len(hand))], C.generate(model, turns, texts, max_new=C2.MAX_NEW["pieces"])))
    json.dump({"pred": pred}, io.open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"v64 test answers -> {path}", flush=True)


def train(seed=0):
    t0 = time.time()
    rows, counts, split = training()
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=P.SYSTEM_V62, checkpoint=True)
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": P.SYSTEM_V62, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"chains8 {VARIANT} seed {seed}: {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    test_answers(model, turns, os.path.join(HERE, f"chains8_64_test_{VARIANT}_s{seed}.json"))
    C2.answers(model, turns, VARIANT, seed, extra)
    P.ml_answers(model, turns, os.path.join(HERE, f"chains8_64_ml_{VARIANT}_s{seed}.json"), extra)
    P7.pairs_answers(model, turns, os.path.join(HERE, f"chains8_64_pairs_{VARIANT}_s{seed}.json"))


def answer63():
    from peft import PeftModel
    model, tok = Q.load(C.NAME)
    m63 = PeftModel.from_pretrained(model, os.path.join(P.MODELS, "coop-qwen3-qlora-chains7-v63", "pieces8and_final_seed0"))
    test_answers(m63, Q.Turns(tok, P.SYSTEM_V62), os.path.join(HERE, "chains8_64_test_v63.json"))


def gguf(seed=0):
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    sys.argv = [sys.argv[0], VARIANT, str(seed)]
    C2.SYSTEM["pieces"] = P.SYSTEM_V62
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v64", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS8_ROUTER", "coop-router-deberta-v3-small-v63"))
    E.main()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts, ensure_ascii=False, indent=1), len(rows), "rows")
        for r in random.Random(1).sample(rows[-(counts["v64_rows"]):], 14):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        train(seed)
    elif what == "answer63":
        answer63()
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    else:
        print(__doc__)
