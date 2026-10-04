"""
Scores the v2 study (train_v2.py cv): 24 intents, leave one author out, 3 seeds, strict count.

Methods
  base    deberta-v3-base, one model (the shipped v1 bot's recipe); 3 seeds -> mean [min-max]
  large   deberta-v3-large, one model; 3 seeds
  ens3    the three base seeds with their probabilities averaged (one number: it uses all seeds)
Gates (coop_v2.pick): "top" (the top intent's probability) and "family" (the top family's mass).
Deployable numbers: the threshold of each held-out fold is fitted on that fold's out-of-fold
predictions over the two training authors (criterion near - 2 * wrong family), then applied to the
held-out author; nothing is fitted on a scored line.

Slices
  all      the 483 lines (363 v1 + 120 v2)
  v2       the 120 lines written for TAKE_COVER / OPEN and the orders they touch
  novel    lines whose nearest training line (another author's line or a seed command) has a char
           2-5-gram tf-idf cosine below 0.5
The equal-risk table is a DIAGNOSTIC: the threshold is swept on the scored lines themselves (every
distinct confidence value), which flatters every method alike.

    python eval_v2.py      # base anaconda python (scikit-learn); reads every results_v2_probs*.json
"""
import glob, io, json, os, random, statistics, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_v2 as V  # noqa: E402

R = {}
for _p in sorted(glob.glob(os.path.join(HERE, f"results_{V.TAG}_probs*.json"))):   # one file per training process
    for _size, _runs in json.load(io.open(_p, encoding="utf-8")).items():
        if not _size.startswith("_"):
            R.setdefault(_size, {}).update(_runs)
ITEMS = V.load_items()
BY = {i["id"]: i for i in ITEMS}
SEEDS = [0, 1, 2]
GATES = ("top", "family")
CAPS = (2, 4, 6.5)


def load_runs(size):
    out = []
    for s in SEEDS:
        test, oof, per_fold = {}, {}, {}
        for held in V.AUTHORS:
            r = R[size][f"{held}/{s}"]
            test.update(r["test"])
            oof[held] = {k: v for k, v in r["oof"].items() if not k.startswith("seed_")}
            per_fold[held] = r["test"]
        out.append({"test": test, "oof": oof, "fold_test": per_fold})
    return out


def average(runs):
    avg = lambda ds: {k: [statistics.fmean(d[k][j] for d in ds) for j in range(len(V.INTENTS))] for k in ds[0]}
    return {"test": avg([r["test"] for r in runs]),
            "oof": {h: avg([r["oof"][h] for r in runs]) for h in V.AUTHORS},
            "fold_test": {h: avg([r["fold_test"][h] for r in runs]) for h in V.AUTHORS}}


def deploy(run, gate):
    """Per held-out author: threshold from that fold's OOF predictions, applied to its lines."""
    preds, thrs, probe = {}, {}, {}
    for held in V.AUTHORS:
        t, _ = V.fit_threshold(run["oof"][held], ITEMS, gate)
        thrs[held] = t
        for k, row in run["fold_test"][held].items():
            if k in BY:
                preds[k] = V.pick(row, gate, t)[0]
            else:
                probe.setdefault(k, []).append(V.pick(row, gate, t))
    return preds, thrs, probe


def novelty():
    from sklearn.feature_extraction.text import TfidfVectorizer
    seeds = V.seed_items()
    texts = [i["text"].lower() for i in ITEMS] + [s["text"].lower() for s in seeds]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    X = vec.fit_transform(texts)
    sim = (X[:len(ITEMS)] @ X.T).toarray()
    out = {}
    for a, it in enumerate(ITEMS):
        others = [b for b, jt in enumerate(ITEMS) if jt["author"] != it["author"]] + \
                 list(range(len(ITEMS), len(texts)))
        out[it["id"]] = max(sim[a, b] for b in others)
    return out


def stats(pred_list, sl):
    ss = [V.score(p, sl) for p in pred_list]
    m = lambda k: (statistics.fmean(s[k] for s in ss), min(s[k] for s in ss), max(s[k] for s in ss))
    return {k: m(k) for k in ("near", "ok", "cross", "fired_on_nonorder")} | {
        "crit": (statistics.fmean(s["near"] - 2 * s["cross"] for s in ss),
                 min(s["near"] - 2 * s["cross"] for s in ss), max(s["near"] - 2 * s["cross"] for s in ss))}


def fmt(v):
    return f"{100 * v[0]:5.1f} [{100 * v[1]:.0f}-{100 * v[2]:.0f}]" if abs(v[1] - v[2]) > 1e-9 else f"{100 * v[0]:5.1f}      "


def new_intent_table(pred_list, raw_list, sl):
    """On the v2 lines: how the new intents and their neighbours come out (share of lines, mean over
    seeds). raw_list: the same models' picks with no threshold, to tell "say again" (a pick under the
    threshold) from a confident NONE (the bot acknowledges and does nothing)."""
    rows = {
        "TAKE_COVER lines -> TAKE_COVER": ("TAKE_COVER", lambda p, r: p == "TAKE_COVER"),
        "TAKE_COVER lines -> say again (under threshold)": ("TAKE_COVER", lambda p, r: p == "NONE" and r != "NONE"),
        "TAKE_COVER lines -> NONE (ignored)": ("TAKE_COVER", lambda p, r: r == "NONE"),
        "TAKE_COVER lines -> COVER_ME/HOLD_*": ("TAKE_COVER", lambda p, r: V.FAMILY[p] == "hold"),
        "OPEN lines -> OPEN": ("OPEN", lambda p, r: p == "OPEN"),
        "OPEN lines -> say again (under threshold)": ("OPEN", lambda p, r: p == "NONE" and r != "NONE"),
        "OPEN lines -> NONE (ignored)": ("OPEN", lambda p, r: r == "NONE"),
        "OPEN lines -> assault family": ("OPEN", lambda p, r: V.FAMILY[p] == "assault"),
        "COVER_ME lines -> COVER_ME": ("COVER_ME", lambda p, r: p == "COVER_ME"),
        "COVER_ME lines -> TAKE_COVER": ("COVER_ME", lambda p, r: p == "TAKE_COVER"),
        "assault-family lines -> OPEN": ("assault", lambda p, r: p == "OPEN"),
        "HOLD_ANGLE lines -> TAKE_COVER/OPEN": ("HOLD_ANGLE", lambda p, r: p in V.NEW),
        "NONE lines (callout/negated/out of menu) -> acts": ("NONE", lambda p, r: p != "NONE"),
        "WAIT lines -> WAIT": ("WAIT", lambda p, r: p == "WAIT"),
    }
    out = {}
    for name, (who, test) in rows.items():
        lines = [i for i in sl if (V.FAMILY.get(i["maj"]) == who if who == "assault" else i["maj"] == who)]
        vals = [sum(test(p[i["id"]], r[i["id"]]) for i in lines) / max(len(lines), 1)
                for p, r in zip(pred_list, raw_list)]
        out[name] = (statistics.fmean(vals), min(vals), max(vals), len(lines))
    return out


def equal_risk(run_list, gate, sl):
    """Best near with wrong family <= cap, threshold swept over every confidence on these lines."""
    res = []
    for cap in CAPS:
        vals = []
        for run in run_list:
            conf = {i["id"]: V.confidence(run["test"][i["id"]], gate)[1] for i in sl}
            best = 0.0
            for t in sorted(set(conf.values())) + [float("inf")]:
                s = V.score({i["id"]: V.pick(run["test"][i["id"]], gate, t)[0] for i in sl}, sl)
                if s["cross"] * 100 <= cap + 1e-9:
                    best = max(best, s["near"])
            vals.append(best)
        res.append(statistics.fmean(vals))
    return res


def per_item(pred_list, sl):
    """near_i - 2 * cross_i per line, averaged over seeds."""
    out = {}
    for i in sl:
        v = []
        for p in pred_list:
            x = p[i["id"]]
            good = x in i["accept"] or bool(i["maj"] and V.FAMILY[x] == V.FAMILY[i["maj"]])
            v.append(int(good) - 2 * int(not good and x != "NONE"))
        out[i["id"]] = statistics.fmean(v)
    return out


def bootstrap(a, b, sl, reps=4000, seed=0):
    ids = [i["id"] for i in sl]
    rng = random.Random(seed)
    d = [a[k] - b[k] for k in ids]
    boots = sorted(statistics.fmean(d[rng.randrange(len(d))] for _ in d) for _ in range(reps))
    return 100 * statistics.fmean(d), 100 * boots[int(0.025 * reps)], 100 * boots[int(0.975 * reps)]


def main():
    sim = novelty()
    slices = {"all": ITEMS, "v1": [i for i in ITEMS if i["version"] in ("v1", "v1-reread")],
              "v2": [i for i in ITEMS if i["version"] == "v2"],
              "novel": [i for i in ITEMS if sim[i["id"]] < 0.5]}
    if any(i["version"] == "v3" for i in ITEMS):     # COOP_TAG=v3: the lines that name map places
        slices["v3"] = [i for i in ITEMS if i["version"] == "v3"]
    print(f"{len(ITEMS)} test lines ({len(slices['v1'])} v1, {len(slices['v2'])} v2), "
          f"{len(slices['novel'])} novel (nearest training line or seed < 0.5 cosine)\n")

    runs = {m: load_runs(m) for m in ("base", "large") if m in R and len(R[m]) == 9}
    if "base" in runs:
        runs["ens3"] = [average(runs["base"])]
    methods = {}   # (method, gate) -> {"preds": [...], "thr": [...], "probe": [...]}
    for m, rl in runs.items():
        for g in GATES:
            d = [deploy(r, g) for r in rl]
            methods[(m, g)] = {"preds": [x[0] for x in d], "thr": [x[1] for x in d], "probe": [x[2] for x in d],
                               "raw": [{k: V.pick(row, g, 0.0)[0] for k, row in r["test"].items() if k in BY} for r in rl]}

    v1ship = json.load(io.open(os.path.join(HERE, "results_v1_on_v2.json"), encoding="utf-8"))
    v1_preds = {k: V.pick(row, "top", v1ship["threshold"])[0] for k, row in v1ship["probs"].items()}

    table = {}
    print("DEPLOYABLE (out-of-fold threshold per fold). near / exact ok / wrong family / acts on non-order, %")
    print(f"{'method':<22} {'thr':>5} {'near':>13} {'ok':>13} {'wrong fam':>13} {'non-order':>13} "
          f"{'score':>13} | {'v2 near':>13} {'v2 wf':>13} | {'novel near':>13} {'novel wf':>13}")
    for (m, g), d in methods.items():
        st = {k: stats(d["preds"], sl) for k, sl in slices.items()}
        thr = statistics.fmean(t for x in d["thr"] for t in x.values())
        table[f"{m}/{g}"] = {"thr": thr, **{k: {q: list(v) for q, v in s.items()} for k, s in st.items()}}
        a, v2, nv = st["all"], st["v2"], st["novel"]
        print(f"{m + ', ' + g + ' gate':<22} {thr:5.2f} {fmt(a['near'])} {fmt(a['ok'])} {fmt(a['cross'])} "
              f"{fmt(a['fired_on_nonorder'])} {fmt(a['crit'])} | {fmt(v2['near'])} {fmt(v2['cross'])} | "
              f"{fmt(nv['near'])} {fmt(nv['cross'])}")
    s = V.score(v1_preds, slices["v2"])
    print(f"{'v1 bot as shipped':<22} {v1ship['threshold']:5.2f} {'':>13} {'':>13} {'':>13} {'':>13} {'':>13} | "
          f"{100 * s['near']:5.1f}         {100 * s['cross']:5.1f}         | (v2 lines only: it trained on v1)")

    print("\nNEW INTENTS on the v2 lines, deployable threshold (share of lines, mean over seeds; n lines)")
    nt = {k: new_intent_table(d["preds"], d["raw"], slices["v2"]) for k, d in methods.items()}
    v1_raw = {k: V.pick(row, "top", 0.0)[0] for k, row in v1ship["probs"].items()}
    nt[("v1 shipped", "top")] = new_intent_table([v1_preds], [v1_raw], slices["v2"])
    cols = list(nt)
    print(f"{'':<46}" + "".join(f"{m[:10] + '/' + g[:3]:>15}" for m, g in cols))
    for row in next(iter(nt.values())):
        n = next(iter(nt.values()))[row][3]
        print(f"{row + f' (n={n})':<46}" + "".join(f"{100 * nt[c][row][0]:15.1f}" for c in cols))

    print("\nDIAGNOSTIC, equal risk: best near with wrong family <= 2 / 4 / 6.5 % (threshold swept on the scored lines)")
    diag = {}
    for m, rl in runs.items():
        for g in GATES:
            diag[f"{m}/{g}"] = {k: equal_risk(rl, g, sl) for k, sl in slices.items()}
            e = diag[f"{m}/{g}"]
            print(f"{m + ', ' + g:<16} all " + " / ".join(f"{100 * x:4.1f}" for x in e["all"]) +
                  "   novel " + " / ".join(f"{100 * x:4.1f}" for x in e["novel"]) +
                  "   v2 " + " / ".join(f"{100 * x:4.1f}" for x in e["v2"]))

    print("\nPAIRED BOOTSTRAP of the deployable score (near - 2 * wrong family, points; 95% CI over lines)")
    boot = {}
    pi = {k: {sn: per_item(d["preds"], sl) for sn, sl in slices.items()} for k, d in methods.items()}
    pairs = [(("large", "top"), ("base", "top")), (("ens3", "top"), ("base", "top")),
             (("large", "top"), ("ens3", "top")), (("base", "family"), ("base", "top")),
             (("large", "family"), ("large", "top")), (("ens3", "family"), ("ens3", "top"))]
    for a, b in pairs:
        if a not in pi or b not in pi:
            continue
        row = {sn: bootstrap(pi[a][sn], pi[b][sn], sl) for sn, sl in slices.items()}
        boot[f"{a[0]}/{a[1]} - {b[0]}/{b[1]}"] = row
        print(f"{a[0] + '/' + a[1] + ' - ' + b[0] + '/' + b[1]:<28} " +
              "  ".join(f"{sn} {v[0]:+5.1f} [{v[1]:+5.1f}, {v[2]:+5.1f}]" for sn, v in row.items()))

    print("\nPROBES (the owner's live-test lines and v1's failed probes): pick at each fold model's threshold, majority over models")
    probes = V.probe_items()
    pr = {}
    for (m, g), d in methods.items():
        for p in probes:
            got = [x for probe in d["probe"] for x in probe.get(p["id"], [])]
            c = Counter(x[0] for x in got).most_common(1)[0]
            pr.setdefault(p["id"], {})[f"{m}/{g}"] = (c[0], c[1], len(got), statistics.fmean(x[1] for x in got))
    for p in probes:
        v1p = V.pick(v1ship["probs"][p["id"]], "top", v1ship["threshold"])
        cells = "  ".join(f"{k.split('/')[0][:5]}/{k.split('/')[1][:3]} {v[0]}{'' if v[1] == v[2] else f' {v[1]}/{v[2]}'}"
                          f"{' ok' if v[0] in p['accept'] else ' --'}" for k, v in pr[p["id"]].items())
        print(f"  {p['text']!r:<32} want {'/'.join(sorted(p['accept'])):<22} v1 {v1p[0]}  |  {cells}")

    json.dump({"table": table, "new_intents": {f"{m}/{g}": v for (m, g), v in nt.items()},
               "equal_risk": diag, "bootstrap": boot, "probes": pr,
               "slices": {k: len(v) for k, v in slices.items()}},
              io.open(os.path.join(HERE, f"results_{V.TAG}.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
