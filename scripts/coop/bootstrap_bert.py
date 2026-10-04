"""
Paired bootstrap for the equal-risk comparison in eval_bert.py's diagnostic table.

For every method, and every seed of a fine-tuned method, a line-by-threshold matrix of "near" and
"wrong family" indicators (strict safety) is built once. A bootstrap replicate resamples the lines,
re-sweeps the threshold (oracle, as in the diagnostic) and takes the best near with wrong family at or
under the cap; fine-tuned methods average that over their seeds. The difference between two methods
is taken inside each replicate, so the interval is paired.

    $env:OLLAYA_URL='http://127.0.0.1:9'; python bootstrap_bert.py
"""
import io, json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossval as X  # noqa: E402
import eval_bert as E  # noqa: E402
import robustness as RB  # noqa: E402
import run_coop as C  # noqa: E402

ITEMS = X.ITEMS
THR = [t / 50 for t in range(50)]
B = 2000
CAPS = (0.02, 0.065)


def indicators(raw, items):
    """raw {id: (label, pmax)} -> near, cross arrays [T, N] (strict: only NONE does nothing).

    Thresholds are EXACT: every distinct pmax of this method on these lines, plus 'never act'. A
    fixed grid (the first version used t/50, ending at 0.98) cannot reach models whose wrong picks
    sit above 0.98, and reported them as 0 -- a review caught it."""
    thr = sorted({pm for it in items for pm in [raw[it["id"]][1]]}) + [float("inf")]
    thr = [0.0] + thr
    near = np.zeros((len(thr), len(items)), dtype=np.int8)
    cross = np.zeros_like(near)
    for n, it in enumerate(items):
        lab, pm = raw[it["id"]]
        for t, th in enumerate(thr):
            p = lab if pm >= th else "NONE"
            good = p in it["accept"] or (it["maj"] and C.FAMILY[p] == C.FAMILY[it["maj"]])
            near[t, n] = good
            cross[t, n] = (not good) and p != "NONE"
    return near, cross


def best_near(near, cross, counts, cap):
    tot = counts.sum()
    ns, cs = near @ counts / tot, cross @ counts / tot
    ok = cs <= cap + 1e-12
    return ns[ok].max() if ok.any() else 0.0


def main():
    P = json.load(io.open(os.path.join(HERE, "results_bert_probs.json"), encoding="utf-8"))
    sim = RB.nearest_sim()
    dec_raw = {}
    for held in X.AUTHORS:
        test = [i for i in ITEMS if i["author"] == held]
        dec_raw.update(X.model_raw("decision:eos", "phrase+desc", test))
    methods = {"decision:eos (zero-shot)": [dec_raw]}
    for name in ("microsoft/deberta-v3-base@selected-hi", "answerdotai/ModernBERT-large@selected-hi",
                 "answerdotai/ModernBERT-base@selected-hi", "microsoft/deberta-v3-base"):
        runs = P[name]
        seeds = sorted({k.split("/")[1] for k in runs if not k.startswith("_")})
        methods[name.split("/")[-1]] = [
            {k: v for h in X.AUTHORS for k, v in E.to_raw(runs[f"{h}/{s}"]["test"]).items()} for s in seeds]
    rng = np.random.default_rng(0)
    out = {}
    for slice_name, sl in (("all", ITEMS), ("novel", [i for i in ITEMS if sim[i["id"]] < 0.5]),
                           ("novel<0.4", [i for i in ITEMS if sim[i["id"]] < 0.4])):
        mats = {m: [indicators(r, sl) for r in rs] for m, rs in methods.items()}
        n = len(sl)
        samples = [np.bincount(rng.integers(0, n, n), minlength=n).astype(float) for _ in range(B)]
        full = np.ones(n)
        print(f"\n{slice_name} (n={n}): best near at wrong family <= cap, oracle threshold; "
              f"difference = DeBERTa-v3-base@selected-hi minus the row, 95% paired bootstrap CI")
        for cap in CAPS:
            point = {m: np.mean([best_near(a, b, full, cap) for a, b in mats[m]]) for m in mats}
            reps = {m: np.array([np.mean([best_near(a, b, c, cap) for a, b in mats[m]]) for c in samples])
                    for m in mats}
            ref = "deberta-v3-base@selected-hi"
            print(f"  cap {100*cap:.1f}%")
            for m in mats:
                line = f"    {m:<34} {100*point[m]:5.1f}"
                if m != ref:
                    d = reps[ref] - reps[m]
                    lo, hi = np.percentile(d, [2.5, 97.5])
                    line += f"   diff {100*(point[ref]-point[m]):+5.1f}  [{100*lo:+.1f}, {100*hi:+.1f}]"
                    out[f"{slice_name}|{cap}|{m}"] = [point[ref] - point[m], lo, hi]
                print(line)
    json.dump(out, io.open(os.path.join(HERE, "results_bert_bootstrap.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
