"""Round v63 of the chains study (2026-10-22): two orders joined by "and" / «и» / «y» are two orders.
The owner, after playing chain v62 in Russian: "бот не понимает союз и не выполняет команды последовательно. Хотя если я скажу
потом, тогда он сделает две команды." The log: «иди ко мне сюда и прыгни», «прыгни и подойди ко мне», «подпрыгни и стреляй»,
«поднимись вверх и спустись ко мне» each gave one order. Decoder v62 writes such a line as ONE English line ("jump up and
shoot"), and the classifier reads one intent of it; English has the same fault ("come here and jump", "reload and cover me"),
since round six. With "then" / «потом» it always splits. The rows behind it:
  - singles copied as they are that hold two actions joined by "and" ("come here and hold this angle"), and their Russian and
    Spanish translations (172 and 209 with «и» / «y» answered as one English line);
  - few lines of two SHORT orders joined by "and": the composed lines were made mostly of long authored lines.
What changes against v62 (chains6_v62.py, everything else as it was):
  - a single whose two halves around its first "and" are read by the v61 ensemble as two orders of different families, each at
    0.9 or more, is left out of the rows (in English, and its Russian and Spanish translations): splitting it by that reading was
    wrong too often (one rappel, one grenade); halves of the same family stay ("push in and clear the room");
  - short pairs: per language 2,500 lines of two (a quarter three) short orders of different families joined by "and" / «и» /
    «y» (PAIR_JOIN), made from singles of at most SHORT words; 15% of those singles are held out and make the pairs test set
    (150 per language, never trained on);
  - the router (router_v63.py) gets the English pairs as lines for the decoder.

    python chains7_v63.py data       the rows, counted, and the pairs test written (chains2/ml_v62/pairs_test.json)
    python chains7_v63.py train      pieces8and_final seed 0 -> models/coop-qwen3-qlora-chains7-v63/...; answers on every test set
    python chains7_v63.py answer62   decoder v62's answers on the pairs test (for the comparison)
    python chains7_v63.py gguf | export | score
"""
import io, json, os, random, re, sys, time, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("CHAINS6_VARIANT", "pieces8and_final")
import chains6_v62 as P              # the v61 vocabulary, build_v61, the chain modules, v62's rows
from chains6_v62 import C, C2, Q, V, build_v61, torch

VARIANT = P.VARIANT
assert VARIANT == "pieces8and_final", VARIANT
ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains7-v63")
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}")
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains7_63_{variant}_s{seed}.json")
SHORT = 6                       # words: a short order
CONF = 0.9                      # both halves of a single at least this sure, and of different families, to count as two orders
PAIRS = 2500                    # short pairs per language
PAIRS_TEST = 150
HELD = 0.15                     # of the short singles, kept out of the training pairs for the test
PAIR_JOIN = {
    "en": ["{a} and {b}", "{a} and {b}", "{a}, and {b}", "{a} and also {b}", "{a}, {b} and {c}", "{a} and {b} and {c}"],
    "ru": ["{a} и {b}", "{a} и {b}", "{a}, и {b}", "{a} и ещё {b}", "{a}, {b} и {c}", "{a} и {b} и {c}"],
    "es": ["{a} y {b}", "{a} y {b}", "{a}, y {b}", "{a} y también {b}", "{a}, {b} y {c}", "{a} y {b} y {c}"]}
AND = re.compile(r"\s+and\s+", re.I)
PAIRS_TEST_PATH = os.path.join(P.ML, "pairs_test.json")


def held(text):
    return zlib.crc32(text.strip().lower().encode()) % 1000 < HELD * 1000


def words(t):
    return len(re.findall(r"\w+", t))


def two_orders(english):
    """English singles -> {single: [half, half]} where the halves around the first "and" read as two orders of different
    families, each at CONF or more (the v61 ensemble)."""
    cand = {}
    for t in set(english):
        parts = AND.split(t.strip(), maxsplit=1)
        if len(parts) == 2 and all(words(p) >= 1 for p in parts):
            cand[t] = [C.tidy(parts[0], True), C.tidy(parts[1], True)]
    halves = sorted({h for v in cand.values() for h in v})
    got, _ = C.bot_picks([{"id": str(n), "text": h} for n, h in enumerate(halves)])
    pick = {h: got[str(n)] for n, h in enumerate(halves)}
    out = {}
    for t, (a, b) in cand.items():
        (ia, (_, ca)), (ib, (_, cb)) = pick[a], pick[b]     # bot_picks: (pick under the threshold, (pick, confidence))
        if "NONE" not in (ia, ib) and ca >= CONF and cb >= CONF and V.FAMILY[ia] != V.FAMILY[ib]:
            out[t] = [a, b]
    return out


def short_pools():
    """Per language: [{"text" (that language), "en", "maj"}] of short single orders, split into (train, test) by held()."""
    rows = build_v61.training_set(build_v61.LINES, build_v61.SEEDS, build_v61.OWNER)
    en = {}
    for r in rows:
        if "|" not in r["id"] and words(r["text"]) <= SHORT and C.part_ok(r) and r["maj"] != "NONE" and not AND.search(r["text"]):
            en.setdefault(r["text"].strip(), r["maj"])
    pools = {"en": [{"text": t, "en": t, "maj": m} for t, m in en.items()]}
    src = P.sources()
    for lang in P.LANGS:
        tr = P.translations(lang, "single")
        pools[lang] = [{"text": tr[i]["text"], "en": s["en"], "maj": s["intent"]} for i, s in src["single"].items()
                       if i in tr and words(s["en"]) <= SHORT and s["intent"] != "NONE" and C.part_ok({"text": s["en"], "maj": s["intent"]})
                       and not AND.search(s["en"])]
    return {k: ([x for x in v if not held(x["en"])], [x for x in v if held(x["en"])]) for k, v in pools.items()}


def compose_pairs(pool, lang, n, rng):
    out, seen = [], set()
    tries = 0
    while len(out) < n and tries < 50 * n:
        tries += 1
        pat = rng.choice(PAIR_JOIN[lang])
        m = pat.count("{")
        parts = rng.sample(pool, m)
        if len({V.FAMILY[p["maj"]] for p in parts}) < m:          # different actions only
            continue
        text = pat.format(**{k: C.tidy(p["text"], pat.startswith("{" + k + "}")) for k, p in zip("abc", parts)})
        if text in seen:
            continue
        seen.add(text)
        out.append({"text": P.spoken(text, rng) if lang != "en" else text, "pieces": [C.tidy(p["en"], True) for p in parts],
                    "orders": [p["maj"] for p in parts]})
    return out


def pair_rows(rng):
    pools = short_pools()
    rows, test, counts = [], {}, {}
    for lang in ("en",) + P.LANGS:
        train_pool, test_pool = pools[lang]
        made = compose_pairs(train_pool, lang, PAIRS, rng)
        trng = random.Random(6301)
        test[lang] = [dict(t, id=f"pair_{lang}_{k:03d}") for k, t in enumerate(compose_pairs(test_pool, lang, PAIRS_TEST, trng))]
        for r in made:
            before = []
            if rng.random() < P.P_CONTEXT:
                k = rng.choices([k for k, _ in P.N_BEFORE], [w for _, w in P.N_BEFORE])[0]
                before = [rng.choice(train_pool)["text"] for _ in range(k)]
            rows.append({"text": C2.turn(before, None, r["text"]), "answer": "\n".join(r["pieces"])})
        counts[lang] = {"pool": len(train_pool), "held": len(test_pool), "pairs": len(made), "test": len(test[lang])}
    json.dump(test, io.open(PAIRS_TEST_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return rows, counts


def training():
    rows, counts = P.training()
    # singles answered as they are whose two halves read as two orders: left out. Splitting them by the classifier's reading
    # was tried first and is wrong too often ("get on the rope and drop in when i give the word" is one rappel, "cook it and
    # send it" one grenade): the copy that teaches "X and Y" stays one line goes, and the short pairs teach the split
    english = [r["answer"] for r in rows if "\n" not in r["answer"]]
    split = two_orders([t for t in english if AND.search(t)])
    kept = [r for r in rows if r["answer"] not in split]
    pairs, pcounts = pair_rows(random.Random(6302))
    counts.update({"singles_left_out": len(split), "rows_left_out": len(rows) - len(kept), "pairs": pcounts})
    return kept + pairs, counts, split


def train(seed=0):
    t0 = time.time()
    rows, counts, split = training()
    json.dump(split, io.open(os.path.join(P.ML, "singles_left_out_v63.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=P.SYSTEM_V62, checkpoint=True)
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": P.SYSTEM_V62, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"chains7 {VARIANT} seed {seed}: {counts}, {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    C2.answers(model, turns, VARIANT, seed, extra)
    P.ml_answers(model, turns, os.path.join(HERE, f"chains7_63_ml_{VARIANT}_s{seed}.json"), extra)
    pairs_answers(model, turns, os.path.join(HERE, f"chains7_63_pairs_{VARIANT}_s{seed}.json"))


def pairs_answers(model, turns, path):
    test = json.load(io.open(PAIRS_TEST_PATH, encoding="utf-8"))
    pred = {}
    for lang, items in test.items():
        texts = [C2.turn([], None, re.sub(r"[.!?]+$", "", t["text"].strip()).lower()) for t in items]
        pred[lang] = dict(zip([t["id"] for t in items], C.generate(model, turns, texts, max_new=C2.MAX_NEW["pieces"])))
    json.dump({"pred": pred}, io.open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"pairs answers -> {path}", flush=True)


def answer62():
    from peft import PeftModel
    model, tok = Q.load(C.NAME)
    m62 = PeftModel.from_pretrained(model, os.path.join(P.MODELS, "coop-qwen3-qlora-chains6-v62", "pieces7ml_final_seed0"))
    pairs_answers(m62, Q.Turns(tok, P.SYSTEM_V62), os.path.join(HERE, "chains7_63_pairs_v62.json"))


def gguf(seed=0):
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    sys.argv = [sys.argv[0], VARIANT, str(seed)]
    C2.SYSTEM["pieces"] = P.SYSTEM_V62
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v63", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS7_ROUTER", "coop-router-deberta-v3-small-v63"))
    E.main()


def score():
    """v62 against v63: round three's English blind sets (decoder alone), the Russian and Spanish sets, and the pairs test
    (every pair's sequence of orders, read by the v61 ensemble)."""
    out = io.StringIO()
    files = {"v62": ("chains6_62_pieces7ml_final_s0.json", "chains6_62_ml_pieces7ml_final_s0.json", "chains7_63_pairs_v62.json"),
             "v63": (f"chains7_63_{VARIANT}_s0.json", f"chains7_63_ml_{VARIANT}_s0.json", f"chains7_63_pairs_{VARIANT}_s0.json")}
    have = {k: [P.jl(HERE, f) if os.path.exists(os.path.join(HERE, f)) else None for f in v] for k, v in files.items()}
    pairs = json.load(io.open(PAIRS_TEST_PATH, encoding="utf-8"))
    ts = C2.tests()
    mts = P.ml_tests()
    texts = set()
    for k, (en, ml, pr) in have.items():
        for d in (en, ml, pr):
            if d:
                texts |= {build_v61.norm(p) for s in d["pred"].values() for a in s.values() for p in C2.split(a)}
    texts |= {build_v61.norm(t["text"]) for t in pairs["en"]} | {build_v61.norm(t["text"]) for s in ("blind2", "blind2_heard3", "ctx", "ctx_heard3") for t in ts[s]}
    texts = sorted(t for t in texts if t)
    got, _ = C.bot_picks([{"id": str(n), "text": t} for n, t in enumerate(texts)])
    picks = {t: [got[str(n)][0]] for n, t in enumerate(texts)}
    now = lambda orders: ["HELP" if o == "REVIVE_ME" else o for o in orders]   # noqa: E731

    def rate(items, pred, places=False):
        hit = 0
        for t in items:
            pieces = C2.split(pred[t["id"]])
            ok = C2.orders_of(pieces, picks) == now(t["orders"])
            if ok and places and t.get("places") is not None:
                ok = [C2.place(p) for p in pieces] == [tuple(x) if x is not None else None for x in t["places"]]
            hit += ok
        return f"{100 * hit / max(len(items), 1):10.1f}"

    print(f"{'':48s}{'v62':>10s}{'v63':>10s}", file=out)
    for lang in ("en",) + P.LANGS:
        print(f"{'pairs ' + lang + ' (' + str(len(pairs[lang])) + ', never trained on)':48s}" +
              "".join(rate(pairs[lang], h[2]["pred"][lang]) if h[2] else f"{'-':>10s}" for h in have.values()), file=out)
    for s in ("blind2", "blind2_heard3", "ctx", "ctx_heard3"):
        rows = [t for t in ts[s] if t.get("orders")]
        print(f"{'en ' + s + ' (decoder alone)':48s}" + "".join(rate(rows, h[0]["pred"][s], s.startswith("ctx")) if h[0] else f"{'-':>10s}" for h in have.values()), file=out)
    for s, items in mts.items():
        print(f"{s:48s}" + "".join(rate(items, h[1]["pred"][s], s.startswith("ctx")) if h[1] else f"{'-':>10s}" for h in have.values()), file=out)
    # English as the game runs it: a line under the router's cut goes to the classifier as it is (v62 with router v59, v63 with v63)
    routers = {"v62": ("router59_final_small_s0.json", "router59_v63sets.json"), "v63": ("router63_final_small_s0.json", "router63_final_small_s0.json")}
    if all(os.path.exists(os.path.join(HERE, f)) for v in routers.values() for f in v):
        rp = {k: (P.jl(HERE, a)["probs"], P.jl(HERE, b)["probs"]) for k, (a, b) in routers.items()}
        def wired(items, pred, pr):
            return {t["id"]: pred[t["id"]] if pr[t["id"]] >= 0.5 else t["text"] for t in items}

        print("\nEnglish through the router (v62 + router v59, v63 + router v63):", file=out)
        print(f"{'pairs en, through the router':48s}" + "".join(
            rate(pairs["en"], wired(pairs["en"], h[2]["pred"]["en"], rp[k][1]["pairs_en"])) if h[2] else f"{'-':>10s}" for k, h in have.items()), file=out)
        for s in ("blind2", "blind2_heard3", "ctx", "ctx_heard3"):
            rows = [t for t in ts[s] if t.get("orders")]
            print(f"{'en ' + s + ', through the router':48s}" + "".join(
                rate(rows, wired(rows, h[0]["pred"][s], rp[k][0][s]), s.startswith("ctx")) if h[0] else f"{'-':>10s}" for k, h in have.items()), file=out)
    print(out.getvalue(), end="")
    io.open(os.path.join(HERE, "chains7_63_score.log"), "w", encoding="utf-8").write(out.getvalue())


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts, ensure_ascii=False, indent=1), len(rows), "rows")
        for t, h in list(split.items())[:12]:
            print(f"  split: {t!r} -> {h}")
        for r in random.Random(1).sample(rows[-3 * PAIRS:], 8):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        train(seed)
    elif what == "answer62":
        answer62()
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    elif what == "score":
        score()
    else:
        print(__doc__)
