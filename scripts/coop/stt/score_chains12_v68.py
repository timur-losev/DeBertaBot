"""Decoders v67s (deployed) and v68s (chains12_v68.py: the timer rows and the new things) on the sets of the earlier rounds, every English piece
read by the bot v67 ensemble (the classifier that goes with them): what the v68 rows cost or gained on the older lines (a copy of score_chains11_v67.py;
the classifier is bot v67, as deployed).

    python score_chains12_v68.py dump [DECODER ...]    (the chain modules' environment) -> chains12_68_dump.json
    python score_chains12_v68.py score                  (COOP_TAG=v67) -> chains12_68_score.log

DECODER: v66, v67s, v68s, v68s2 (default: those whose answer files exist). Sets and rules as score_chains10_v66.py: the v64 held-out
singles (en, ru, es; never trained on), the owner's v64 hand rows (trained on by all), the Russian and Spanish sets of round
v62 (dev, blind2, ctx), the pairs test of v63, round three's English sets (decoder alone). A line is right when the sequence
of orders read from its pieces is the expected one; COLLECT and DELIVER count as one, as in v64's score. The scene sets are
measure_v65.py's, test66 measure_v66.py's, test67 measure_v67_cli.py's.
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "chains12_68_dump.json")
FILES = {"v66": ("chains10_66", "pieces11v66_final"), "v67s": ("chains11_67", "pieces12v67s_final"), "v68s": ("chains12_68", "pieces13v68s_final"), "v68s2": ("chains12_68", "pieces13v68s2_final")}


def jl(*p):
    return json.load(io.open(os.path.join(HERE, *p), encoding="utf-8"))


def answers(dec, kind):
    stem, variant = FILES[dec]
    return jl(f"{stem}_{kind + '_' if kind else ''}{variant}_s0.json")["pred"]


def dump(decoders):
    sys.path.insert(0, HERE)
    import chains8_v64 as P8
    P, C2 = P8.P, P8.C2
    decoders = decoders or [d for d in FILES if os.path.exists(os.path.join(HERE, f"{FILES[d][0]}_test64_{FILES[d][1]}_s0.json"))]
    sets = {}
    a = {d: answers(d, "test64") for d in decoders}
    for lang, items in jl("chains2", "ml_v64", "test_v64.json").items():
        sets[f"v64 held-out {lang}"] = [{"id": t["id"], "orders": t["orders"], **{d: a[d][lang][t["id"]] for d in decoders}} for t in items]
    hand = jl("chains2", "ml_v64", "hand_v64.json")["items"]
    sets["owner v64 hand rows (trained on)"] = [{"id": f"hand_{k:03d}", "text": it["text"], "en": it["en"],
                                                 **{d: a[d]["hand"][f"hand_{k:03d}"] for d in decoders}} for k, it in enumerate(hand)]
    a = {d: answers(d, "ml") for d in decoders}
    for name, items in P.ml_tests().items():
        sets[name] = [{"id": t["id"], "orders": t["orders"], **{d: a[d][name][t["id"]] for d in decoders}} for t in items]
    a = {d: answers(d, "pairs") for d in decoders}
    for lang, items in json.load(io.open(P8.P7.PAIRS_TEST_PATH, encoding="utf-8")).items():
        sets[f"pairs {lang}"] = [{"id": t["id"], "orders": t["orders"], **{d: a[d][lang][t["id"]] for d in decoders}} for t in items]
    a = {d: answers(d, "") for d in decoders}
    ts = C2.tests()
    for s in ("blind2", "blind2_heard3", "ctx", "ctx_heard3"):
        sets[f"en {s} (decoder alone)"] = [{"id": t["id"], "orders": t["orders"], **{d: a[d][s][t["id"]] for d in decoders}}
                                           for t in ts[s] if t.get("orders")]
    json.dump({"decoders": decoders, "sets": sets}, io.open(DUMP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(decoders, {k: len(v) for k, v in sets.items()})


def score():
    os.environ["COOP_TAG"] = "v67"
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import coop_v2 as V
    assert V.TAG == "v67" and len(V.INTENTS) == 71
    bot = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v67"))
    cfg = json.load(io.open(os.path.join(bot, "bot_config.json"), encoding="utf-8"))
    d = json.load(io.open(DUMP, encoding="utf-8"))
    decoders, sets = d["decoders"], d["sets"]
    split = lambda a: [p.strip() for p in a.split("\n") if p.strip()]   # noqa: E731
    norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()          # noqa: E731
    hand = "owner v64 hand rows (trained on)"
    pieces = sorted({norm(p) for items in sets.values() for it in items for k in decoders for p in split(it[k])} |
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
    print(f"{'(read by bot v67, family gate, ' + str(cfg['threshold']) + ')':44s}" + "".join(f"{k:>8s}" for k in decoders), file=log)
    total = {k: 0 for k in decoders}
    n_all = 0
    flips = {}
    for name, items in sets.items():
        if name == hand:
            exp = lambda it: [same(pick[norm(e)]) for e in it["en"]]   # noqa: E731
        else:
            exp = lambda it: [same(o) for o in it["orders"]]           # noqa: E731
        r = {k: sum(orders(it[k]) == exp(it) for it in items) for k in decoders}
        print(f"{name + ' (' + str(len(items)) + ')':44s}" + "".join(f"{100 * r[k] / len(items):8.1f}" for k in decoders), file=log)
        if name != hand:
            n_all += len(items)
            for k in decoders:
                total[k] += r[k]
        for a in decoders:
            for b in decoders:
                if a != b:
                    flips.setdefault((a, b), []).extend((name, it) for it in items if orders(it[a]) == exp(it) and orders(it[b]) != exp(it))
    print(f"{'all but the hand rows (' + str(n_all) + ')':44s}" + "".join(f"{100 * total[k] / n_all:8.1f}" for k in decoders), file=log)
    for a, b in (("v67s", "v68s"), ("v67s", "v68s2"), ("v68s", "v68s2")):
        if a in decoders and b in decoders:
            print(f"\nright with {a}, wrong with {b}: {len(flips[(a, b)])}; wrong with {a}, right with {b}: {len(flips[(b, a)])}", file=log)
            for name, it in flips[(a, b)][:40]:
                print(f"  {name[:22]:22s} {it[a].replace(chr(10), ' | ')[:44]:44s} -> {it[b].replace(chr(10), ' | ')[:44]}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, "chains12_68_score.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        dump(sys.argv[2:])
    else:
        score()
