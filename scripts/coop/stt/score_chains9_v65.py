"""Decoder v64 against v65 (chains9_v65.py) on the sets of the earlier rounds, every English piece read by the bot v65
ensemble (the game's classifier from v65 on): what the scene rows cost or gained on lines without a scene.

    python score_chains9_v65.py dump     (the chain modules' environment) -> chains9_65_dump.json
    python score_chains9_v65.py score    (COOP_TAG=v65) -> chains9_65_score.log

Sets as score_chains8_v64.py: the v64 held-out singles (en, ru, es; never trained on), the owner's v64 hand rows (trained on
by both), the Russian and Spanish sets of round v62 (dev, blind2, ctx), the pairs test of v63, round three's English sets
(decoder alone). The scene sets are measure_v65.py's. A line is right when the sequence of orders read from its pieces is the
expected one; COLLECT and DELIVER count as one here, as in v64's score.
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "chains9_65_dump.json")


def jl(*p):
    return json.load(io.open(os.path.join(HERE, *p), encoding="utf-8"))


def dump():
    sys.path.insert(0, HERE)
    import chains8_v64 as P8
    P, C2 = P8.P, P8.C2
    sets = {}
    a, b = jl("chains8_64_test_pieces9v64_final_s0.json")["pred"], jl("chains9_65_test64_pieces10v65_final_s0.json")["pred"]
    test = jl("chains2", "ml_v64", "test_v64.json")
    for lang, items in test.items():
        sets[f"v64 held-out {lang}"] = [{"id": t["id"], "orders": t["orders"], "v64": a[lang][t["id"]], "v65": b[lang][t["id"]]} for t in items]
    hand = jl("chains2", "ml_v64", "hand_v64.json")["items"]
    sets["owner v64 hand rows (trained on)"] = [{"id": f"hand_{k:03d}", "text": it["text"], "en": it["en"], "v64": a["hand"][f"hand_{k:03d}"],
                                                 "v65": b["hand"][f"hand_{k:03d}"]} for k, it in enumerate(hand)]
    a, b = jl("chains8_64_ml_pieces9v64_final_s0.json")["pred"], jl("chains9_65_ml_pieces10v65_final_s0.json")["pred"]
    for name, items in P.ml_tests().items():
        sets[name] = [{"id": t["id"], "orders": t["orders"], "v64": a[name][t["id"]], "v65": b[name][t["id"]]} for t in items]
    a, b = jl("chains8_64_pairs_pieces9v64_final_s0.json")["pred"], jl("chains9_65_pairs_pieces10v65_final_s0.json")["pred"]
    pairs = json.load(io.open(P8.P7.PAIRS_TEST_PATH, encoding="utf-8"))
    for lang, items in pairs.items():
        sets[f"pairs {lang}"] = [{"id": t["id"], "orders": t["orders"], "v64": a[lang][t["id"]], "v65": b[lang][t["id"]]} for t in items]
    a, b = jl("chains8_64_pieces9v64_final_s0.json")["pred"], jl("chains9_65_pieces10v65_final_s0.json")["pred"]
    ts = C2.tests()
    for s in ("blind2", "blind2_heard3", "ctx", "ctx_heard3"):
        sets[f"en {s} (decoder alone)"] = [{"id": t["id"], "orders": t["orders"], "v64": a[s][t["id"]], "v65": b[s][t["id"]]}
                                           for t in ts[s] if t.get("orders")]
    json.dump(sets, io.open(DUMP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in sets.items()})


def score():
    os.environ["COOP_TAG"] = "v65"
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import coop_v2 as V
    assert V.TAG == "v65" and len(V.INTENTS) == 69
    bot = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v65"))
    cfg = json.load(io.open(os.path.join(bot, "bot_config.json"), encoding="utf-8"))
    sets = json.load(io.open(DUMP, encoding="utf-8"))
    split = lambda a: [p.strip() for p in a.split("\n") if p.strip()]   # noqa: E731
    norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()          # noqa: E731
    hand = "owner v64 hand rows (trained on)"
    pieces = sorted({norm(p) for items in sets.values() for it in items for k in ("v64", "v65") for p in split(it[k])} |
                    {norm(e) for it in sets[hand] for e in it["en"]})
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
    print(f"{'(read by bot v65)':44s}{'v64':>8s}{'v65':>8s}", file=log)
    worse = []
    for name, items in sets.items():
        if name == hand:
            exp = lambda it: [same(pick[norm(e)]) for e in it["en"]]   # noqa: E731
        else:
            exp = lambda it: [same(o) for o in it["orders"]]           # noqa: E731
        r = {k: sum(orders(it[k]) == exp(it) for it in items) for k in ("v64", "v65")}
        print(f"{name + ' (' + str(len(items)) + ')':44s}{100 * r['v64'] / len(items):8.1f}{100 * r['v65'] / len(items):8.1f}", file=log)
        worse += [(name, it) for it in items if orders(it["v64"]) == exp(it) and orders(it["v65"]) != exp(it)]
    print(f"\nright with v64, wrong with v65: {len(worse)}", file=log)
    for name, it in worse[:60]:
        print(f"  {name[:22]:22s} {it['v64'].replace(chr(10), ' | ')[:44]:44s} -> {it['v65'].replace(chr(10), ' | ')[:44]}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, "chains9_65_score.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    {"dump": dump, "score": score}[sys.argv[1]]()
