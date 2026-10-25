"""Decoder v63 against v64 (chains8_v64.py), every English piece read by the bot v64 ensemble.

    python score_chains8_v64.py dump     (the v61 vocabulary, as the chain modules need) -> chains8_64_dump.json: per test set,
                                         every item's expected orders and both decoders' answers
    python score_chains8_v64.py score    (COOP_TAG=v64) -> chains8_64_score.log

Sets: the v64 held-out singles (en, ru, es: a tenth of the new lines, never trained on; expected = the line's intent), the
owner's hand rows (trained on: what was wrong in the game, shown as a check), the Russian and Spanish sets of round v62
(dev, blind2, ctx), the pairs test of v63, round three's English sets (decoder alone). A line is right when the sequence of
orders read from its pieces is the expected one. COLLECT and DELIVER count as one (one family since v64, the owner's choice).
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "chains8_64_dump.json")


def jl(*p):
    return json.load(io.open(os.path.join(HERE, *p), encoding="utf-8"))


def dump():
    sys.path.insert(0, HERE)
    import chains8_v64 as P8
    P, C2 = P8.P, P8.C2
    sets = {}
    t64, t63 = jl("chains8_64_test_pieces9v64_final_s0.json")["pred"], jl("chains8_64_test_v63.json")["pred"]
    test = jl("chains2", "ml_v64", "test_v64.json")
    for lang, items in test.items():
        sets[f"v64 held-out {lang}"] = [{"id": t["id"], "orders": t["orders"], "v63": t63[lang][t["id"]], "v64": t64[lang][t["id"]]} for t in items]
    hand = jl("chains2", "ml_v64", "hand_v64.json")["items"]
    sets["owner hand rows (trained on)"] = [{"id": f"hand_{k:03d}", "text": it["text"], "en": it["en"], "v63": t63["hand"][f"hand_{k:03d}"],
                                             "v64": t64["hand"][f"hand_{k:03d}"]} for k, it in enumerate(hand)]
    m63, m64 = jl("chains7_63_ml_pieces8and_final_s0.json")["pred"], jl("chains8_64_ml_pieces9v64_final_s0.json")["pred"]
    for name, items in P.ml_tests().items():
        sets[name] = [{"id": t["id"], "orders": t["orders"], "v63": m63[name][t["id"]], "v64": m64[name][t["id"]]} for t in items]
    p63, p64 = jl("chains7_63_pairs_pieces8and_final_s0.json")["pred"], jl("chains8_64_pairs_pieces9v64_final_s0.json")["pred"]
    pairs = json.load(io.open(P8.P7.PAIRS_TEST_PATH, encoding="utf-8"))
    for lang, items in pairs.items():
        sets[f"pairs {lang}"] = [{"id": t["id"], "orders": t["orders"], "v63": p63[lang][t["id"]], "v64": p64[lang][t["id"]]} for t in items]
    e63, e64 = jl("chains7_63_pieces8and_final_s0.json")["pred"], jl("chains8_64_pieces9v64_final_s0.json")["pred"]
    ts = C2.tests()
    for s in ("blind2", "blind2_heard3", "ctx", "ctx_heard3"):
        sets[f"en {s} (decoder alone)"] = [{"id": t["id"], "orders": t["orders"], "v63": e63[s][t["id"]], "v64": e64[s][t["id"]]}
                                           for t in ts[s] if t.get("orders")]
    json.dump(sets, io.open(DUMP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in sets.items()})


def score():
    os.environ["COOP_TAG"] = "v64"
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import coop_v2 as V
    assert V.TAG == "v64" and len(V.INTENTS) == 69
    bot = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v64"))
    cfg = json.load(io.open(os.path.join(bot, "bot_config.json"), encoding="utf-8"))
    sets = json.load(io.open(DUMP, encoding="utf-8"))
    split = lambda a: [p.strip() for p in a.split("\n") if p.strip()]   # noqa: E731
    norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()          # noqa: E731
    pieces = sorted({norm(p) for items in sets.values() for it in items for k in ("v63", "v64") for p in split(it[k])} |
                    {norm(e) for it in sets["owner hand rows (trained on)"] for e in it["en"]})
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    runs = []
    for m in cfg["members"]:
        tok = AutoTokenizer.from_pretrained(os.path.join(bot, m))
        model = AutoModelForSequenceClassification.from_pretrained(os.path.join(bot, m), dtype=torch.float32).to(dev).eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(pieces), 128):
                x = tok(pieces[i:i + 128], padding=True, truncation=True, max_length=64, return_tensors="pt").to(dev)
                out += torch.softmax(model(**x).logits, -1).cpu().tolist()
        runs.append(out)
        del model
    pick = {}
    for n, t in enumerate(pieces):
        p = [sum(r[n][j] for r in runs) / len(runs) for j in range(len(V.INTENTS))]
        pick[t] = V.pick(p, cfg["gate"], cfg["threshold"])[0]
    same = lambda i: "carry" if i in ("COLLECT", "DELIVER") else ("HELP" if i == "REVIVE_ME" else i)   # noqa: E731
    orders = lambda a: [same(pick[norm(p)]) for p in split(a)] or ["NONE"]                       # noqa: E731
    log = io.StringIO()
    print(f"{'':44s}{'v63':>8s}{'v64':>8s}", file=log)
    hand_rows = []
    for name, items in sets.items():
        if name.startswith("owner hand"):
            exp = lambda it: [same(pick[norm(e)]) for e in it["en"]]   # noqa: E731
        else:
            exp = lambda it: [same(o) for o in it["orders"]]           # noqa: E731
        r = {k: sum(orders(it[k]) == exp(it) for it in items) for k in ("v63", "v64")}
        print(f"{name + ' (' + str(len(items)) + ')':44s}{100 * r['v63'] / len(items):8.1f}{100 * r['v64'] / len(items):8.1f}", file=log)
        if name.startswith("owner hand"):
            hand_rows = [(it["text"], it["v63"].replace("\n", " | "), it["v64"].replace("\n", " | "), orders(it["v64"]) == exp(it)) for it in items]
    print("\nthe owner's lines (hand rows): v63 -> v64", file=log)
    for text, a, b, ok in hand_rows:
        print(f"  {'ok ' if ok else 'NO '} {text:42s} {a:34s} -> {b}", file=log)
    for lang in ("ru", "es", "en"):
        items = sets[f"v64 held-out {lang}"]
        bad = [it for it in items if orders(it["v64"]) != [same(o) for o in it["orders"]]]
        print(f"\nv64 held-out {lang}: {len(bad)} wrong", file=log)
        for it in bad[:25]:
            print(f"  {it['orders'][0]:14s} {it['v64'].replace(chr(10), ' | '):50s} read {orders(it['v64'])}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, "chains8_64_score.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    {"dump": dump, "score": score}[sys.argv[1]]()
