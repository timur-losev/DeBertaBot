"""
Fine-tuned laya against fine-tuned DeBERTa (both with the seed commands in training), zero-shot laya
and zero-shot decision:eos, on the same 363 held-out lines (leave one author out, 3 seeds).

Strict metrics (only NONE is doing nothing); equal-risk columns use an oracle threshold swept on the
test lines (a diagnostic that treats every method alike); paired bootstrap on the difference.

    $env:OLLAYA_URL='http://127.0.0.1:9'; python compare_laya_ft.py
"""
import io, json, os, statistics, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bootstrap_bert as BB  # noqa: E402
import crossval as X  # noqa: E402
import eval_bert as E  # noqa: E402
import robustness as RB  # noqa: E402

ITEMS = X.ITEMS


def seeds_of(get):
    return [{k: v for h in X.AUTHORS for k, v in E.to_raw(get(h, s)).items() if not k.startswith("probe_")}
            for s in "012"]


def main():
    P = json.load(io.open(os.path.join(HERE, "results_bert_probs.json"), encoding="utf-8"))
    S = json.load(io.open(os.path.join(HERE, "results_seed_check.json"), encoding="utf-8"))
    Z = json.load(io.open(os.path.join(HERE, "results_coop_test.json"), encoding="utf-8"))["raw"]
    methods = {
        "laya:en fine-tuned + seeds": seeds_of(lambda h, s: P["laya:en-ft+seeds"][f"{h}/{s}"]["test"]),
        "DeBERTa-v3-base fine-tuned + seeds": seeds_of(lambda h, s: S[f"{h}/{s}"]),
        "laya:en zero-shot": [{k: tuple(v) for k, v in Z["laya:en phrase"].items()}],
        "decision:eos zero-shot": [{k: tuple(v) for k, v in Z["decision:eos phrase+desc"].items()}],
    }
    sim = RB.nearest_sim()
    novel = [i for i in ITEMS if sim[i["id"]] < 0.5]
    print(f"{'method':<36} {'argmax: near':>12} {'wrong fam':>10} {'non-order':>10}")
    for m, rr in methods.items():
        am = [RB.sc({k: v[0] for k, v in r.items()}, ITEMS, True) for r in rr]
        f = lambda key: 100 * statistics.mean(s[key] for s in am)
        print(f"{m:<36} {f('near'):>12.1f} {f('cross'):>10.1f} {f('fired_on_nonorder'):>10.1f}")
    rng = np.random.default_rng(0)
    for name, sl in (("all", ITEMS), ("novel", novel)):
        mats = {m: [BB.indicators(r, sl) for r in rr] for m, rr in methods.items()}
        n = len(sl)
        samples = [np.bincount(rng.integers(0, n, n), minlength=n).astype(float) for _ in range(BB.B)]
        full = np.ones(n)
        print(f"\n{name} (n={n}): best near at wrong family <= cap (oracle threshold); diff = laya fine-tuned minus row")
        for cap in (0.02, 0.065):
            point = {m: np.mean([BB.best_near(a, b, full, cap) for a, b in mats[m]]) for m in mats}
            reps = {m: np.array([np.mean([BB.best_near(a, b, c, cap) for a, b in mats[m]]) for c in samples])
                    for m in mats}
            ref = "laya:en fine-tuned + seeds"
            print(f"  cap {100*cap:.1f}%")
            for m in mats:
                line = f"    {m:<36} {100*point[m]:5.1f}"
                if m != ref:
                    d = reps[ref] - reps[m]
                    lo, hi = np.percentile(d, [2.5, 97.5])
                    line += f"   diff {100*(point[ref]-point[m]):+5.1f} [{100*lo:+.1f}, {100*hi:+.1f}]"
                print(line)


if __name__ == "__main__":
    main()
