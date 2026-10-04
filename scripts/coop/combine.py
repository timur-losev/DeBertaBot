"""
Two follow-ups to crossval.py, same leave-one-author-out protocol.

1. COMBINATIONS of the two leaders, which fail in different places (decision:eos reads callouts and
   negations better, the char-ngram logreg reads slang, on-signal and other-ref lines better):
     veto        logreg picks; if decision says NONE / WAIT / HOLD_POSITION, do nothing
     family key  logreg picks; act only if decision's pick is in the same family, else do nothing
     exact key   act only if both pick the same intent
   Each rule has no parameter of its own (both models keep their training-fitted thresholds). The
   rule to recommend is chosen by its score on the training authors, fold by fold.

2. LEARNING CURVE: how many labelled playtest lines the logreg needs before it beats the zero-shot
   decision model. Trained on random subsets of the two training authors, scored on the third.

    python combine.py
"""
import io, json, os, random, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossval as X  # noqa: E402
import run_coop as C  # noqa: E402

ITEMS = X.ITEMS
FAM = C.FAMILY


def dec_raw(train, items):
    cr, br, _ = X.rich_criteria(train, *X.N_EX["decision:eos"])
    return X.model_raw("decision:eos", None, items, cr, br)


def lr_raw(train, items):
    return X.sk_models(train, items)["logreg char-ngrams"]


def lr_inner(held):
    """logreg predictions on the training authors without training on them (inner swap), for fitting."""
    a, b = [x for x in X.AUTHORS if x != held]
    out = {}
    out.update(lr_raw([i for i in ITEMS if i["author"] == a], [i for i in ITEMS if i["author"] == b]))
    out.update(lr_raw([i for i in ITEMS if i["author"] == b], [i for i in ITEMS if i["author"] == a]))
    return out


RULES = {
    "logreg alone": lambda l, d: l,
    "decision alone": lambda l, d: d,
    "veto: logreg, unless decision does nothing": lambda l, d: "NONE" if d in C.SAFE else l,
    "family key: act if same family": lambda l, d: l if FAM[l] == FAM[d] else "NONE",
    "exact key: act if same intent": lambda l, d: l if l == d else "NONE",
}


def val(s):
    return s["near"] - 2 * s["cross"]


def main():
    final = {r: {} for r in RULES}
    chosen = []
    for held in X.AUTHORS:
        train = [i for i in ITEMS if i["author"] != held]
        test = [i for i in ITEMS if i["author"] == held]
        d_tr, d_te = dec_raw(train, train), dec_raw(train, test)
        l_tr, l_te = lr_inner(held), lr_raw(train, test)
        td, tl = X.fit_thr(d_tr, train), X.fit_thr(l_tr, train)
        gd_tr, gl_tr = C.gate(d_tr, td), C.gate(l_tr, tl)
        gd_te, gl_te = C.gate(d_te, td), C.gate(l_te, tl)
        on_train = {}
        for r, f in RULES.items():
            on_train[r] = val(C.score({k: f(gl_tr[k], gd_tr[k]) for k in gl_tr}, train))
            final[r].update({k: f(gl_te[k], gd_te[k]) for k in gl_te})
        best = max(on_train, key=on_train.get)
        chosen.append(best)
        print(f"fold {held}: thresholds decision {td:.2f} logreg {tl:.2f}; best rule on training authors: {best}")
    C.save(True)

    print(f"\nCOMBINATIONS, held-out union ({len(ITEMS)} lines)")
    print(f"{'rule':<46} {'ok':>4} {'near':>5} {'safe':>5} {'cross':>6} {'LOUD':>5} {'fires':>6}")
    table = {}
    for r, pred in final.items():
        s = C.score(pred, ITEMS)
        table[r] = s
        print(f"{r:<46} {100*s['ok']:>4.0f} {100*s['near']:>5.0f} {100*s['safe']:>5.0f} {100*s['cross']:>6.0f}"
              f" {100*s['loud']:>5.0f} {100*s['fired_on_nonorder']:>6.0f}")

    print("\nLEARNING CURVE: logreg trained on N lines from the two training authors (5 random draws each)")
    print(f"{'N lines':>8} {'ok':>5} {'near':>5} {'cross':>6} {'fires':>6}   (argmax, no threshold)")
    curve = {}
    for n in (22, 44, 66, 110, 176, 242):
        runs = []
        for seed in range(5):
            pred = {}
            for held in X.AUTHORS:
                train = [i for i in ITEMS if i["author"] != held and i["maj"]]
                test = [i for i in ITEMS if i["author"] == held]
                sub = random.Random(seed * 100 + n).sample(train, min(n, len(train)))
                # every intent needs at least one line or the classifier cannot name it
                raw = lr_raw(sub, test)
                pred.update({k: v[0] for k, v in raw.items()})
            runs.append(C.score(pred, ITEMS))
        m = {k: statistics.mean(r[k] for r in runs) for k in ("ok", "near", "cross", "fired_on_nonorder")}
        curve[n] = m
        print(f"{n:>8} {100*m['ok']:>5.0f} {100*m['near']:>5.0f} {100*m['cross']:>6.0f} {100*m['fired_on_nonorder']:>6.0f}")
    json.dump({"rules": table, "chosen_per_fold": chosen, "curve": curve},
              io.open(os.path.join(HERE, "results_combine.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
