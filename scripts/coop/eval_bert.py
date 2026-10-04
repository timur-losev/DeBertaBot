"""
Scores the fine-tuned BERT classifiers from train_bert.py next to the earlier methods, with the
strict metrics of robustness.py (only NONE counts as doing nothing).

Thresholds for the fine-tuned models, never fitted on held-out lines:
  inner      models trained on one training author, scored on the other (the first protocol;
             review found them under-confident for DeBERTa, so the threshold landed too low)
  oof        5-fold out-of-fold predictions over the 242 training lines, same optimizer steps as the
             deployed model (train_bert.py --oof)
Fitting maximises near - 2 * wrong-family on integer counts (float ties picked by rounding noise in
the first version). Each seed gives one full set of 363 held-out predictions; tables show the mean
over seeds and, in brackets, the range.

The last table is a DIAGNOSTIC, not a result: a threshold swept on the test lines themselves, to
compare methods at the same wrong-family rate. It flatters every method equally and is labelled.

    $env:OLLAYA_URL='http://127.0.0.1:9'   # cache only, no model is loaded
    python eval_bert.py
"""
import io, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossval as X  # noqa: E402
import robustness as RB  # noqa: E402
import run_coop as C  # noqa: E402

ITEMS = X.ITEMS
LABELS = C.INTENTS


def to_raw(probs):
    """{id: [p per label]} -> {id: (label, pmax)}"""
    out = {}
    for k, row in probs.items():
        j = max(range(len(row)), key=row.__getitem__)
        out[k] = (LABELS[j], row[j])
    return out


def fit_thr_int(raw, items):
    """Threshold maximising near_count - 2 * cross_count; ties go to the lowest threshold."""
    ids = {i["id"] for i in items if i["id"] in raw}
    sub = [i for i in items if i["id"] in ids]
    best = None
    for t in range(0, 100, 2):
        s = RB.sc(C.gate({k: raw[k] for k in ids}, t / 100), sub, True)
        v = round(s["near"] * len(sub)) - 2 * round(s["cross"] * len(sub))
        if best is None or v > best[0]:
            best = (v, t / 100)
    return best[1]


def stats_for(per_seed, sl):
    ss = [RB.sc(p, sl, True) for p in per_seed]
    m = {k: (statistics.mean(s[k] for s in ss), min(s[k] for s in ss), max(s[k] for s in ss))
         for k in ("near", "ok", "cross", "fired_on_nonorder")}
    crit = [s["near"] - 2 * s["cross"] for s in ss]
    m["crit"] = (statistics.mean(crit), min(crit), max(crit))
    return m


def main():
    P = json.load(io.open(os.path.join(HERE, "results_bert_probs.json"), encoding="utf-8"))
    sim = RB.nearest_sim()
    novel = [i for i in ITEMS if sim[i["id"]] < 0.5]
    dup = [i for i in ITEMS if sim[i["id"]] >= 0.5]

    # decision:eos (descriptions, zero-shot) per fold, threshold fitted on the training authors
    dec, dec_raw = {}, {}
    for held in X.AUTHORS:
        train = [i for i in ITEMS if i["author"] != held]
        test = [i for i in ITEMS if i["author"] == held]
        tb = RB.fit_thr(X.model_raw("decision:eos", "phrase+desc", train), train)
        dec_raw.update(X.model_raw("decision:eos", "phrase+desc", test))
        dec[held] = C.gate(X.model_raw("decision:eos", "phrase+desc", test), tb)
    dec_all = {k: v for d in dec.values() for k, v in d.items()}

    methods = {}   # name -> list of per-seed prediction dicts
    raws = {}      # name -> list of per-seed raw dicts (for the diagnostic sweep)
    thr_log = {}
    for name, runs in P.items():
        if name.startswith("_"):
            continue
        short = name.split("/")[-1]
        seeds = sorted({k.split("/")[1] for k in runs if not k.startswith("_")})
        if not all(f"{h}/{s}" in runs for h in X.AUTHORS for s in seeds):
            print(f"(skipping {short}: not every fold/seed is finished)")
            continue
        variants = ["argmax"]
        if all("inner" in runs[f"{h}/{s}"] for h in X.AUTHORS for s in seeds):
            variants += ["threshold (inner)", "family key, inner thr"]
        if all("oof" in runs[f"{h}/{s}"] for h in X.AUTHORS for s in seeds):
            variants += ["threshold (oof)", "family key, oof thr"]
        sel = {h: runs[f"_selection/{h}"] for h in X.AUTHORS if f"_selection/{h}" in runs}
        if sel:
            print(f"{short}: chosen per held-out author: "
                  + ", ".join(f"{h} lr={v['lr']} epochs={v['epoch']}" for h, v in sel.items()))
        for variant in variants:
            per_seed, per_raw = [], []
            for sd in seeds:
                pred, rr = {}, {}
                for held in X.AUTHORS:
                    r = runs[f"{held}/{sd}"]
                    test_raw = to_raw(r["test"])
                    rr.update(test_raw)
                    if variant == "argmax":
                        pred.update({k: v[0] for k, v in test_raw.items()})
                        continue
                    train = [i for i in ITEMS if i["author"] != held]
                    src = r["oof"] if "oof" in variant else r["inner"]
                    t = fit_thr_int(to_raw(src), train)
                    thr_log.setdefault(f"{short} {variant}", []).append(t)
                    g = C.gate(test_raw, t)
                    if variant.startswith("threshold"):
                        pred.update(g)
                    else:
                        d = dec[held]
                        pred.update({k: (g[k] if C.FAMILY[g[k]] == C.FAMILY[d[k]] else "NONE") for k in g})
                per_seed.append(pred)
                per_raw.append(rr)
            methods[f"{short}, {variant}"] = per_seed
            raws[f"{short}, {variant}"] = per_raw

    R = json.load(io.open(os.path.join(HERE, "results_robustness.json"), encoding="utf-8"))["table"]
    ref_names = ["zero-shot decision:eos, dev thr 0.52", "decision:eos base, thr", "logreg, thr",
                 "family key: logreg + decision base", "zero-shot laya:en, argmax"]

    def fmt(v):
        return f"{100*v[0]:>5.1f} [{100*v[1]:.0f}-{100*v[2]:.0f}]" if v[1] != v[2] else f"{100*v[0]:>5.1f}"

    print(f"held-out union, {len(ITEMS)} lines; novel = {len(novel)} lines with no close copy in another author's set\n")
    hdr = (f"{'method':<46} {'near':>15} {'wrong fam':>14} {'non-order':>14} {'near-2*wf':>15}"
           f" {'novel: near':>15} {'novel: wf':>13} {'novel: n-2wf':>15}")
    print(hdr)
    table = {}
    for k in ref_names:
        s = R[k]
        a, n = s["strict"], s["novel_strict"]
        row = lambda x: (x, x, x)
        print(f"{k:<46} {fmt(row(a['near'])):>15} {fmt(row(a['cross'])):>14} {fmt(row(a['fired_on_nonorder'])):>14}"
              f" {fmt(row(a['near'] - 2*a['cross'])):>15} {fmt(row(n['near'])):>15} {fmt(row(n['cross'])):>13}"
              f" {fmt(row(n['near'] - 2*n['cross'])):>15}")
    for k, per_seed in methods.items():
        a, n = stats_for(per_seed, ITEMS), stats_for(per_seed, novel)
        table[k] = {"all": a, "novel": n, "copy": stats_for(per_seed, dup),
                    "per_author": {au: stats_for(per_seed, [i for i in ITEMS if i["author"] == au]) for au in X.AUTHORS}}
        print(f"{k:<46} {fmt(a['near']):>15} {fmt(a['cross']):>14} {fmt(a['fired_on_nonorder']):>14}"
              f" {fmt(a['crit']):>15} {fmt(n['near']):>15} {fmt(n['cross']):>13} {fmt(n['crit']):>15}")

    print("\nthresholds fitted (mean over folds and seeds):",
          {k: round(statistics.mean(v), 2) for k, v in thr_log.items()})

    # ---- diagnostic: best near at a capped wrong-family rate, threshold swept ON THE TEST LINES
    print("\nDIAGNOSTIC (oracle threshold swept on the test lines; compares methods at equal risk, not a result):")
    print(f"{'method':<34} " + " ".join(f"{'wf<=' + str(c) + '%':>14}" for c in (2, 4, 6.5, 10)) + "   (all lines | novel lines)")
    lr_raw = {}
    for held in X.AUTHORS:
        train = [i for i in ITEMS if i["author"] != held]
        test = [i for i in ITEMS if i["author"] == held]
        lr_raw.update(X.sk_models(train, test)["logreg char-ngrams"])
    cand = {"decision:eos (descriptions)": [dec_raw], "logreg char-ngrams": [lr_raw]}
    for k in raws:
        if k.endswith("argmax"):
            cand[k.replace(", argmax", " (fine-tuned)")] = raws[k]
    diag = {}
    for name, rlist in cand.items():
        cells = []
        for cap in (2, 4, 6.5, 10):
            vals_all, vals_nov = [], []
            for r in rlist:
                for sl, acc in ((ITEMS, vals_all), (novel, vals_nov)):
                    best = 0.0
                    # exact sweep: every distinct pmax on these lines, plus never acting
                    for t in sorted({r[i["id"]][1] for i in sl}) + [float("inf")]:
                        s = RB.sc(C.gate(r, t), sl, True)
                        if s["cross"] * 100 <= cap + 1e-9:
                            best = max(best, s["near"])
                    acc.append(best)
            cells.append((statistics.mean(vals_all), statistics.mean(vals_nov)))
        diag[name] = cells
        print(f"{name:<34} " + " ".join(f"{100*a:>6.1f} | {100*n:>5.1f}" for a, n in cells))

    print("\nCPU latency per line:", {k: f"{v['median']:.1f} ms" for k, v in P.get("_latency_cpu_ms", {}).items()})
    json.dump({"table": table, "thresholds": thr_log, "diagnostic_equal_risk": diag},
              io.open(os.path.join(HERE, "results_bert.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
