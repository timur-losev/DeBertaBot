"""
Leave-one-author-out: can what a studio would collect from playtests close the gap?

run_coop.py measured every model zero-shot, with thresholds from the experimenter's dev set, and the
dev set turned out easier than the blind authors (laya:en 66% on dev, 55% on test). So every choice
here is made on two authors' lines and scored on the third's, three times over; the table is the
union of the three held-out folds, 363 lines. That is what "we recorded two playtest groups and
shipped to a third" looks like.

  base            the zero-shot vocabulary (intents.json), threshold fitted on the two training authors
  +examples       each intent's description carries up to 8 training lines as examples, NONE up to 12
                  (few-shot through the description: decision reads 16k tokens, von 8k, nli 512 per pair)
  +order gate     a separate noul "is this an order to the bot?"; below its training-fitted cut -> NONE
  +neg guard      code: a negator word in the line and a non-safe pick -> NONE
  kNN / logreg    char n-gram tf-idf trained on the two authors: the no-model control

    python crossval.py
"""
import io, json, os, re, statistics, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_coop as C  # noqa: E402

ITEMS = C.load_test()
AUTHORS = ["r6", "cs", "stt"]
# Generic English negators, fixed before this run. "forget" is from dev.json ("forget the smoke").
NEG = re.compile(r"\b(don'?t|do not|dont|no|not|never|nah|nope|cancel|forget)\b", re.I)
GATE_Q = {"type": "noul", "instructions": "The player is giving the bot an order to do something."}


# Examples per intent (NONE gets more: it covers callouts, chatter and negations). gliclass returns
# 422 past 2 per intent. The 400-character cap on decision:eos is a leftover from a false diagnosis:
# its "Scan node ... Subgraph has nodes running on device" errors were a use-after-free in ONNX
# Runtime 1.26+ that fires after the runner sits idle for 10 s (see ../../COOP-BOT.md), not a length
# limit. Kept so the published numbers reproduce from the cache.
N_EX = {"decision:eos": (8, 12, 400), "von:1.1": (8, 12, None), "nli:latest": (8, 12, None),
        "gliclass:large": (2, 3, None)}


def rich_criteria(train, n=8, n_none=12, cap=None):
    ex = {k: [] for k in C.INTENTS}
    for it in train:
        if it["maj"] and len(ex[it["maj"]]) < (n_none if it["maj"] == "NONE" else n):
            ex[it["maj"]].append(it["text"])
    crit = {}
    for k in C.INTENTS:
        d = C.I[k]["description"]
        if ex[k]:
            d += ". Examples:"
            for t in ex[k]:
                add = f' "{t}";'
                if cap and len(d) + len(add) > cap:
                    break
                d += add
            d = d.rstrip(";")
        crit[C.I[k]["label"]] = d
    return crit, {C.I[k]["label"]: k for k in C.INTENTS}, ex


def fit_thr(raw, train):
    def v(t):
        s = C.score(C.gate(raw, t), train)
        return s["near"] - 2 * s["cross"]  # the owner's criterion: near misses fine, wrong family not
    best = max((v(t / 100), -t) for t in range(0, 100, 2))
    return -best[1] / 100


def model_raw(model, style, items, crit=None, back=None):
    out = {}
    for it in items:
        if crit is None:
            p, pm, _, _, _ = C.classify(model, style, it["text"])
        else:
            q = {"intent": {"type": "choice", "instructions": C.INSTR, "criteria": crit}}
            ans, _ = C.ollaya(model, it["text"], q)
            lab, probs = ans["intent"]
            p, pm = back[lab], max(probs.values())
        out[it["id"]] = (p, pm)
    C.save()
    return out


def qwen_raw(items, examples=None):
    out = {}
    labels = {C.I[k]["label"]: k for k in C.INTENTS}
    schema = {"intent": {"type": "enum", "choices": list(labels),
                         "description": "Which order the player is giving the bot"}}
    for it in items:
        ctx = f'A player in a tactical shooter said to their AI teammate: "{it["text"]}"'
        if examples:
            ctx += "\nOrders the bot understands, with examples of how players say them:\n" + "\n".join(
                f"- {C.I[k]['label']}: " + "; ".join(f'"{t}"' for t in examples[k][:5]) for k in C.INTENTS)
        key = "qwen-fewshot|" + ctx
        if key not in C.CACHE:
            r, ms = C._post(C.QWEN, {"context": ctx, "schema": schema})
            t = r["field_telemetry"]["intent"]
            C.CACHE[key] = [t["value"], max(c["probability"] for c in t["top_choices"]), ms]
            C._dirty[0] += 1
            C.save()
        v, pm, _ = C.CACHE[key]
        out[it["id"]] = (labels[v], pm)
    return out


def gate_scores(model, items):
    out = {}
    for it in items:
        ans, _ = C.ollaya(model, it["text"], {"g": GATE_Q})
        out[it["id"]] = ans["g"][0]
    C.save()
    return out


def apply_neg(pred, items):
    return {it["id"]: ("NONE" if NEG.search(it["text"]) and pred[it["id"]] not in C.SAFE else pred[it["id"]])
            for it in items}


def sk_models(train, test):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    tr = [it for it in train if it["maj"]]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    X = vec.fit_transform([it["text"].lower() for it in tr])
    y = [it["maj"] for it in tr]
    Xt = vec.transform([it["text"].lower() for it in test])
    out = {}
    lr = LogisticRegression(max_iter=2000, C=10).fit(X, y)
    pr = lr.predict_proba(Xt)
    out["logreg char-ngrams"] = {it["id"]: (lr.classes_[row.argmax()], row.max()) for it, row in zip(test, pr)}
    kn = KNeighborsClassifier(n_neighbors=3, metric="cosine", weights="distance").fit(X, y)
    pr = kn.predict_proba(Xt)
    out["kNN char-ngrams"] = {it["id"]: (kn.classes_[row.argmax()], row.max()) for it, row in zip(test, pr)}
    return out


def main():
    rows = {}      # method -> {id: final pick}
    thrs = {}      # method -> [thr per fold]
    gate_auc = {}
    for held in AUTHORS:
        train = [it for it in ITEMS if it["author"] != held]
        test = [it for it in ITEMS if it["author"] == held]
        crit_rich, back_rich, examples = rich_criteria(train)
        methods = {}
        for m, s in (("laya:en", "phrase"), ("von:1.1", "phrase"), ("gliclass:large", "phrase"),
                     ("nli:latest", "phrase"), ("decision:eos", "phrase+desc")):
            methods[f"{m} base"] = (model_raw(m, s, train), model_raw(m, s, test))
        for m in ("decision:eos", "von:1.1", "nli:latest", "gliclass:large"):
            cr, br, _ = rich_criteria(train, *N_EX[m])
            methods[f"{m} +examples"] = (model_raw(m, None, train, cr, br), model_raw(m, None, test, cr, br))
        methods["qwen base"] = (qwen_raw(train), qwen_raw(test))
        methods["qwen +examples in context"] = (qwen_raw(train, examples), qwen_raw(test, examples))
        sk_tr = sk_models([it for it in ITEMS if it["author"] not in (held,)], test)
        # the sklearn models cannot be scored on their own training lines; fit their threshold by an
        # inner split (train on one training author, score the other, both ways)
        inner = {k: {} for k in sk_tr}
        tr_auth = [a for a in AUTHORS if a != held]
        for a, b in (tr_auth, tr_auth[::-1]):
            part = sk_models([it for it in ITEMS if it["author"] == a], [it for it in ITEMS if it["author"] == b])
            for k in part:
                inner[k].update(part[k])
        for k in sk_tr:
            methods[k] = (inner[k], sk_tr[k])

        # the order gate, per model, fitted on the training authors
        gates = {}
        for g in ("decision:eos", "laya:en", "gliclass:large", "nli:latest"):
            gtr, gte = gate_scores(g, train), gate_scores(g, test)
            gates[g] = (gtr, gte)
            pos = [gte[it["id"]] for it in test if it["maj"] and it["maj"] != "NONE"]
            neg = [gte[it["id"]] for it in test if it["maj"] == "NONE"]
            auc = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
            gate_auc.setdefault(g, []).append(auc)

        for name, (rtr, rte) in methods.items():
            t = fit_thr(rtr, train)
            thrs.setdefault(name, []).append(t)
            rows.setdefault(name + "  (argmax)", {}).update({k: v[0] for k, v in rte.items()})
            rows.setdefault(name + "  (+threshold)", {}).update(C.gate(rte, t))
            rows.setdefault(name + "  (+neg guard)", {}).update(apply_neg({k: v[0] for k, v in rte.items()}, test))
            rows.setdefault(name + "  (+threshold +neg guard)", {}).update(apply_neg(C.gate(rte, t), test))

        # best intent model + best gate, both fitted on training authors
        for base in ("decision:eos +examples", "decision:eos base", "nli:latest base", "laya:en base"):
            rtr, rte = methods[base]
            for g, (gtr, gte) in gates.items():
                best = None
                for gt in [i / 20 for i in range(0, 20)]:
                    for it_thr in (0.0, thrs[base][-1]):
                        ptr = {k: (v[0] if (v[1] >= it_thr and gtr[k] >= gt) else "NONE") for k, v in rtr.items()}
                        s = C.score(ptr, train)
                        val = s["near"] - 2 * s["cross"]
                        if best is None or val > best[0]:
                            best = (val, gt, it_thr)
                _, gt, it_thr = best
                pte = {k: (v[0] if (v[1] >= it_thr and gte[k] >= gt) else "NONE") for k, v in rte.items()}
                rows.setdefault(f"{base} + {g} order gate", {}).update(pte)
                rows.setdefault(f"{base} + {g} order gate +neg guard", {}).update(apply_neg(pte, test))
        C.save(True)
        print(f"fold held={held} done", flush=True)

    print(f"\nLEAVE-ONE-AUTHOR-OUT, union of the three held-out folds ({len(ITEMS)} lines)")
    print(f"order-gate AUC (NONE vs an order) per held-out fold: "
          + ", ".join(f"{g} {statistics.mean(a):.2f}" for g, a in gate_auc.items()))
    kinds = ["callout", "chatter", "negated", "compound", "on_signal", "other_ref", "plain", "slang"]
    print("columns: ok = exact intent accepted; near = ok or same family (BREACH for ENTRY is fine);"
          " safe = did nothing; cross = acted, wrong family; fires = acted on a callout/chatter/negation line")
    print(f"\n{'method':<62} {'ok':>4} {'near':>5} {'safe':>5} {'cross':>6} {'fires':>6}   near by kind: "
          + " ".join(f"{k[:8]:>8}" for k in kinds))
    table = {}
    val = lambda s: s["near"] - 2 * s["cross"]
    for name, pred in sorted(rows.items(), key=lambda x: -val(C.score(x[1], ITEMS))):
        s = C.score(pred, ITEMS)
        byk = {k: C.score(pred, [i for i in ITEMS if i["kind"] == k])["near"] for k in kinds}
        table[name] = {**s, "by_kind_near": byk}
        print(f"{name:<62} {100*s['ok']:>4.0f} {100*s['near']:>5.0f} {100*s['safe']:>5.0f} {100*s['cross']:>6.0f}"
              f" {100*s['fired_on_nonorder']:>6.0f}   " + " ".join(f"{100*byk[k]:>8.0f}" for k in kinds))
    json.dump({"table": table, "thresholds": thrs, "gate_auc": gate_auc, "predictions": rows},
              io.open(os.path.join(HERE, "results_crossval.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
