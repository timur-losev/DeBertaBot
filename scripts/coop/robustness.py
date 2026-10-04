"""
The checks an adversarial review asked for, all from cached model answers (no model is loaded:
point OLLAYA_URL / QWEN_URL at a dead port and any cache miss fails instead of reloading a model).

  1. STRICT safety     only NONE counts as doing nothing. The first write-up also exempted WAIT and
                       HOLD_POSITION, which are real orders (hold makes the bot stay in a fight).
  2. NEAR-DUPLICATES   all authors are agents of one model family and reuse phrasings. Each test line
                       gets its highest char-ngram cosine to the OTHER two authors' lines; methods are
                       scored separately on lines with (>= 0.5) and without (< 0.5) a close copy.
  3. PER AUTHOR        the STT author imitates the real input path; pooled numbers can hide it.
  4. HONEST decision+examples threshold: fitted only on training lines NOT quoted in its own
                       descriptions (the first run fitted it in-sample).
  5. FAMILY KEY WITH THE FAST decision (descriptions only, 244 ms) instead of the +examples one (~740 ms).
  6. LEARNING CURVE WITH A THRESHOLD fitted by an inner 2-fold split of each training subset.
  7. LATENCY of the logreg, measured.

    $env:OLLAYA_URL='http://127.0.0.1:9'; $env:QWEN_URL='http://127.0.0.1:9'; python robustness.py
"""
import io, json, os, random, statistics, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossval as X  # noqa: E402
import run_coop as C  # noqa: E402

ITEMS = X.ITEMS
BY_ID = {i["id"]: i for i in ITEMS}
SAFE_LOOSE = {"NONE", "WAIT", "HOLD_POSITION"}


def sc(pred, items, strict):
    C.SAFE = {"NONE"} if strict else SAFE_LOOSE
    s = C.score(pred, items)
    C.SAFE = SAFE_LOOSE
    return s


def fmt(s):
    return f"{100*s['near']:>5.0f} {100*s['cross']:>6.1f} {100*s['fired_on_nonorder']:>6.1f}"


def fit_thr(raw, items, strict=True):
    def v(t):
        s = sc(C.gate(raw, t), items, strict)
        return s["near"] - 2 * s["cross"]
    return -max((v(t / 100), -t) for t in range(0, 100, 2))[1] / 100


def nearest_sim():
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    X_ = vec.fit_transform([i["text"].lower() for i in ITEMS])
    sim = (X_ @ X_.T).toarray()
    out = {}
    for a, it in enumerate(ITEMS):
        others = [b for b, jt in enumerate(ITEMS) if jt["author"] != it["author"]]
        out[it["id"]] = max(sim[a, b] for b in others)
    return out


def main():
    # ---- the methods, per fold, thresholds fitted on the training authors under STRICT safety
    preds = {k: {} for k in ("zero-shot decision:eos, dev thr 0.52", "zero-shot gliclass, dev thr 0.38",
                             "zero-shot nli, dev thr 0.26", "zero-shot laya:en, argmax",
                             "decision:eos base, thr", "decision:eos +examples, honest thr",
                             "logreg, thr", "family key: logreg + decision base",
                             "family key: logreg + decision +examples", "exact key: logreg + decision base")}
    for it in ITEMS:
        for name, (m, s, t) in {"zero-shot decision:eos, dev thr 0.52": ("decision:eos", "phrase+desc", 0.52),
                                "zero-shot gliclass, dev thr 0.38": ("gliclass:large", "phrase", 0.38),
                                "zero-shot nli, dev thr 0.26": ("nli:latest", "phrase", 0.26),
                                "zero-shot laya:en, argmax": ("laya:en", "phrase", 0.0)}.items():
            p, pm, _, _, _ = C.classify(m, s, it["text"])
            preds[name][it["id"]] = p if pm >= t else "NONE"
    thr_log = {}
    for held in X.AUTHORS:
        train = [i for i in ITEMS if i["author"] != held]
        test = [i for i in ITEMS if i["author"] == held]
        base_tr = X.model_raw("decision:eos", "phrase+desc", train)
        base_te = X.model_raw("decision:eos", "phrase+desc", test)
        tb = fit_thr(base_tr, train)
        cr, br, ex = X.rich_criteria(train, *X.N_EX["decision:eos"])
        quoted = {t for k in ex for t in ex[k]}
        unq = [i for i in train if i["text"] not in quoted]
        rich_unq = X.model_raw("decision:eos", None, unq, cr, br)
        rich_te = X.model_raw("decision:eos", None, test, cr, br)
        tr_ = fit_thr(rich_unq, unq)
        # logreg: threshold from the inner swap between the two training authors
        a, b = [x for x in X.AUTHORS if x != held]
        inner = {}
        inner.update(X.sk_models([i for i in ITEMS if i["author"] == a], [i for i in ITEMS if i["author"] == b])["logreg char-ngrams"])
        inner.update(X.sk_models([i for i in ITEMS if i["author"] == b], [i for i in ITEMS if i["author"] == a])["logreg char-ngrams"])
        tl = fit_thr(inner, train)
        lr_te = X.sk_models(train, test)["logreg char-ngrams"]
        thr_log[held] = {"decision base": tb, "decision +examples (unquoted lines)": tr_,
                         "unquoted training lines": len(unq), "logreg": tl}
        gb, gr, gl = C.gate(base_te, tb), C.gate(rich_te, tr_), C.gate(lr_te, tl)
        preds["decision:eos base, thr"].update(gb)
        preds["decision:eos +examples, honest thr"].update(gr)
        preds["logreg, thr"].update(gl)
        for k in gl:
            preds["family key: logreg + decision base"][k] = gl[k] if C.FAMILY[gl[k]] == C.FAMILY[gb[k]] else "NONE"
            preds["family key: logreg + decision +examples"][k] = gl[k] if C.FAMILY[gl[k]] == C.FAMILY[gr[k]] else "NONE"
            preds["exact key: logreg + decision base"][k] = gl[k] if gl[k] == gb[k] else "NONE"

    sim = nearest_sim()
    dup = [i for i in ITEMS if sim[i["id"]] >= 0.5]
    novel = [i for i in ITEMS if sim[i["id"]] < 0.5]
    exact = sum(1 for i in ITEMS if sim[i["id"]] > 0.999)
    print(f"thresholds per fold (strict criterion): {json.dumps(thr_log)}")
    print(f"\nnear-duplicates: {len(dup)} of {len(ITEMS)} test lines have a char-ngram cosine >= 0.5 to another"
          f" author's line ({exact} are exact copies); {len(novel)} do not")

    print(f"\n{'method':<44} {'-- LOOSE (hold/wait = nothing) --':>22}  {'-------- STRICT (only NONE) --------':>36}")
    print(f"{'':<44} {'near  cross  fires':>22}  {'near  cross  fires':>20}  {'novel lines: near cross':>24}  {'with a copy: near cross':>24}")
    table = {}
    for name, p in preds.items():
        lo, st = sc(p, ITEMS, False), sc(p, ITEMS, True)
        nv, dp = sc(p, novel, True), sc(p, dup, True)
        table[name] = {"loose": lo, "strict": st, "novel_strict": nv, "dup_strict": dp,
                       "per_author_strict": {a: sc(p, [i for i in ITEMS if i["author"] == a], True) for a in X.AUTHORS}}
        print(f"{name:<44} {fmt(lo):>22}  {fmt(st):>20}  {100*nv['near']:>12.0f} {100*nv['cross']:>6.1f}"
              f"      {100*dp['near']:>12.0f} {100*dp['cross']:>6.1f}")

    print("\nPER AUTHOR, strict: near / wrong family / acts on non-order")
    print(f"{'method':<44} " + "".join(f"{a:>22}" for a in X.AUTHORS))
    for name in preds:
        print(f"{name:<44} " + "".join(
            f"{fmt(table[name]['per_author_strict'][a]):>22}" for a in X.AUTHORS))

    # ---- learning curve with an inner-fitted threshold, strict
    print("\nLEARNING CURVE, logreg, threshold fitted by inner 2-fold split of each subset, strict safety")
    print(f"{'N lines':>8} {'near':>5} {'cross':>6} {'fires':>6}   near on novel lines")
    curve = {}
    for n in (66, 110, 176, 242):
        runs, nov = [], []
        for seed in range(5):
            pred = {}
            for held in X.AUTHORS:
                train = [i for i in ITEMS if i["author"] != held and i["maj"]]
                test = [i for i in ITEMS if i["author"] == held]
                sub = random.Random(seed * 100 + n).sample(train, min(n, len(train)))
                h = len(sub) // 2
                inner = {}
                inner.update(X.sk_models(sub[:h], sub[h:])["logreg char-ngrams"])
                inner.update(X.sk_models(sub[h:], sub[:h])["logreg char-ngrams"])
                t = fit_thr(inner, sub)
                pred.update(C.gate(X.sk_models(sub, test)["logreg char-ngrams"], t))
            runs.append(sc(pred, ITEMS, True))
            nov.append(sc(pred, novel, True)["near"])
        m = {k: statistics.mean(r[k] for r in runs) for k in ("near", "cross", "fired_on_nonorder")}
        m["novel_near"] = statistics.mean(nov)
        curve[n] = m
        print(f"{n:>8} {100*m['near']:>5.0f} {100*m['cross']:>6.1f} {100*m['fired_on_nonorder']:>6.1f}   {100*m['novel_near']:>5.0f}")

    # ---- logreg latency
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    tr = [i for i in ITEMS if i["author"] != "stt" and i["maj"]]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    lr = LogisticRegression(max_iter=2000, C=10).fit(vec.fit_transform([i["text"].lower() for i in tr]), [i["maj"] for i in tr])
    ms = []
    for i in [i for i in ITEMS if i["author"] == "stt"]:
        t0 = time.perf_counter()
        lr.predict_proba(vec.transform([i["text"].lower()]))
        ms.append((time.perf_counter() - t0) * 1000)
    print(f"\nlogreg latency, one line, CPU: median {statistics.median(ms):.2f} ms, p90 {sorted(ms)[int(.9*len(ms))]:.2f} ms")

    json.dump({"thresholds": thr_log, "near_dup": {"dup": len(dup), "novel": len(novel), "exact": exact},
               "table": table, "curve": curve, "logreg_ms": statistics.median(ms)},
              io.open(os.path.join(HERE, "results_robustness.json"), "w"), indent=1, default=list)


if __name__ == "__main__":
    main()
