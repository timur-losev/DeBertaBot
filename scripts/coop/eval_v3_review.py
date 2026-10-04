"""
v3, POST-REVIEW numbers: every figure here was computed AFTER all 150 v3 blind lines, their labels
and the first results had been seen (the review of 2026-10-03/04, review_v3/README.md). The slices,
the joint rate and the intervals were chosen by reviewers who knew the outcome, so none of this is a
blind measurement; the blind ones are eval_v3_rules_v1.log (matcher) and sections B-C of
eval_v3.log (classifier). No rule, seed, label or threshold was fitted on these numbers.
Stored files only: no model is loaded and every run prints the same.

A. Classifier on the 150 v3 lines, shipped v2 against the re-trained ens3 (leave one author out),
   both gates: near, exact ok and wrong family by count, per author; the paired bootstrap of the
   score (near - 2 x wrong family, what eval_v3.log calls "score") AND of near alone; the gain
   without author r6.
B. The same on the novel v3 lines (eval_v2.novelty: the nearest other-author line or seed is below
   0.5 char-n-gram cosine) and on the near-copies.
C. Joint rate: intent near AND the matcher's primary exact on the same line; with the rules on disk
   (v2, tuned on r6 and cs) and with rules v1 (their misses are parsed from eval_v3_rules_v1.log:
   the v1 files are not in the archive).
D. The 483 older lines, v3 study against v21 study, per gate: near and wrong family by count, the
   fold thresholds of each study, the lines whose outcome changed.
E. Shipped bot, raw line against "strip": the lines whose answer changes, exact sign test.
F. Matcher per author under rules v1 and v2, and what the 150 primaries carry (role, flag).
G. One more author, written during the review (review_v3/fresh_author.json: ONE AI author who is
   also the only labeller, partly blind, short seed-like lines): the matcher and both bots, from the
   archived probabilities of the shipped v2 and the final v3 model.
Intervals: differences are the paired bootstrap of eval_v3.bootstrap (4000 resamples of the lines,
seed 0: over lines of these authors, not over authors); single rates are Wilson 95%.

    python eval_v3_review.py > eval_v3_review.log     # any python with scikit-learn (B); writes results_v3_review.json
"""
import hashlib, io, json, math, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eval_v3 as X  # noqa: E402  (sets COOP_TAG=v3; per_item, bootstrap, ens_preds are the log's own)

# the matcher as it was when this review ran: rule set v2 (the current locations.py is rule set v3)
V, LOC = X.V, X.load_rules("v2")
REVIEW = os.path.join(HERE, "review_v3")


def wilson(k, n, z=1.96):
    """Wilson 95% interval of k/n, in percent."""
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, 100 * (c - h)), min(100.0, 100 * (c + h))


def rate(k, n):
    lo, hi = wilson(k, n)
    return f"{100 * k / n:5.1f}% ({k}/{n}) [{lo:.1f}, {hi:.1f}]"


def ci(d):
    return "{:+.1f} [{:+.1f}, {:+.1f}]".format(*(round(x, 1) + 0.0 for x in d))   # + 0.0: no "-0.0"


def sign_test(up, down):
    """Exact two-sided sign test on the lines that changed."""
    n = up + down
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(up, down) + 1)) / 2 ** n) if n else 1.0


def marks(preds, sl):
    """Per line (near, wrong family, exact ok) as 0/1: coop_v2.score of that one line."""
    out = {}
    for i in sl:
        s = V.score(preds, [i])
        out[i["id"]] = (s["near_count"], s["cross_count"], int(s["ok"]))
    return out


def counts(m, sl):
    return [sum(m[i["id"]][k] for i in sl) for k in range(3)]


def col(m, k):
    """One mark of marks(): 0 near, 1 wrong family, 2 exact ok."""
    return {i: v[k] for i, v in m.items()}


def diff(x, y, sl):
    """Paired x - y over the lines of sl (x, y: id -> number): the bootstrap of eval_v3, the lines
    up and down, the sign test."""
    up, down = sum(x[i["id"]] > y[i["id"]] for i in sl), sum(x[i["id"]] < y[i["id"]] for i in sl)
    return {"diff": list(X.bootstrap(x, y, sl)), "up": up, "down": down, "sign_p": sign_test(up, down)}


def study(tag):
    """The deployable ens3 picks of a study per gate (eval_v3.ens_preds: leave one author out, each
    fold's out-of-fold threshold), its lines, the fold thresholds, and the eval_v2 it loaded."""
    ens, _, items = X.ens_preds(tag)
    E = sys.modules["eval_v2"]
    run = E.average(E.load_runs("base"))
    return ens, items, {g: E.deploy(run, g)[1] for g in E.GATES}, E


def shipped():
    R = json.load(io.open(os.path.join(HERE, "results_v3_shipped.json"), encoding="utf-8"))
    return R, {m: {k: V.pick(row, R["gate"], R["threshold"])[0] for k, row in R[m].items()} for m in ("raw", "strip")}


def primaries(sl):
    """Per line: the matcher's primary target (rules on disk) and whether it is the readers' target,
    compared as eval_v3.matcher compares it (object, qualifier, zone)."""
    out = {}
    for it in sl:
        t = LOC.find(it["text"])["target"]
        got = (t["object"], t["qualifier"], t["zone"]) if t else (None, None, None)
        out[it["id"]] = {"t": t, "exact": got == it["target"]}
    return out


def rules_v1_misses(n_lines):
    """The lines rules v1 (frozen before the blind lines existed) got wrong: the mismatch ids of
    section A of eval_v3_rules_v1.log, checked against that log's own total."""
    ids, inside, total = [], False, None
    for line in io.open(os.path.join(HERE, "eval_v3_rules_v1.log"), encoding="utf-8"):
        m = re.match(r"  all\s+exact\s+[\d.]+% \((\d+)/(\d+)\)", line)
        if m and total is None:
            total = (int(m.group(1)), int(m.group(2)))
        if "mismatches (" in line:
            inside = True
        elif inside and re.match(r"    \S", line):
            ids.append(line.split()[0])
        elif inside and not line.startswith("     "):
            break
    assert total == (n_lines - len(ids), n_lines), (total, len(ids))
    return set(ids)


def by_author(v3):
    return [(f"all ({len(v3)})", v3)] + [(f"author {a} ({sum(i['author'] == a for i in v3)})",
                                          [i for i in v3 if i["author"] == a]) for a in V.AUTHORS]


def section_a(M, S, thr, v3, R):
    print(f"A. CLASSIFIER on the {len(v3)} v3 lines: shipped ({R['model']}, {R['gate']} gate, threshold {R['threshold']}, "
          "raw line) against re-trained ens3 (leave one author out)")
    print("   fold thresholds of the re-trained ens3: " + "; ".join(
        f"{g} gate " + " / ".join(f"{a} {thr[g][a]:.2f}" for a in V.AUTHORS) for g in thr))
    print("   lines near / exact ok / wrong family, and the score (near - 2 x wrong family, % of the lines)")
    res = {"thresholds": thr, "counts": {}, "retrained_minus_shipped": {}}
    for name, sl in by_author(v3):
        cells = []
        for k, m in M.items():
            near, wf, ok = counts(m, sl)
            cells.append(f"{k} {near:>3} / {ok:>3} / {wf}  score {100 * (near - 2 * wf) / len(sl):5.1f}")
            res["counts"].setdefault(name, {})[k] = {"n": len(sl), "near": near, "ok": ok, "wrong_family": wf}
        print(f"  {name:<16} " + "   | ".join(cells))
    print("   re-trained - shipped, paired over lines (95% CI over lines of these three authors, not over authors);\n"
          "   near: lines gained / lost, exact sign test")
    slices = [("all lines", v3), ("without author r6", [i for i in v3 if i["author"] != "r6"])] + \
             [(f"author {a} only", [i for i in v3 if i["author"] == a]) for a in V.AUTHORS]
    for name, sl in slices:
        for g in ("top", "family"):
            a, b = M[f"ens3/{g}"], M["shipped"]
            sc, nr, wf = diff(S[f"ens3/{g}"], S["shipped"], sl), diff(col(a, 0), col(b, 0), sl), diff(col(a, 1), col(b, 1), sl)
            res["retrained_minus_shipped"].setdefault(name, {})[g] = {"score": sc["diff"], "near": nr, "wrong_family": wf}
            print(f"  {name + f' (n={len(sl)})' if g == 'top' else '':<28} {g:<7} score {ci(sc['diff']):<21} near {ci(nr['diff']):<20} "
                  f"({nr['up']} / {nr['down']}, p={nr['sign_p']:.3f})   wrong family: {wf['down']} removed, {wf['up']} new")
    return res


def section_b(E, M, S, v3):
    sim = E.novelty()
    print("\nB. NOVELTY of the v3 lines (eval_v2.novelty: char 2-5-gram tf-idf cosine to the nearest other-author line\n"
          "   or seed, the measure and the 0.5 cut of the v2 study; neither was chosen on v3 lines)\n"
          "   novel is relative to the training data of the re-trained fold: the other authors' lines, their v3 lines included,\n"
          "   and the v3 seeds. The shipped bot saw neither the v3 lines nor the location seeds (and it did see the same\n"
          "   author's older lines), so its rows are not 'the shipped bot on lines novel to it'")
    res = {}
    for name, sl in (("novel (< 0.5)", [i for i in v3 if sim[i["id"]] < 0.5]),
                     ("near-copy (>= 0.5)", [i for i in v3 if sim[i["id"]] >= 0.5])):
        n = len(sl)
        row = {"n": n, "per_author": {a: sum(i["author"] == a for i in sl) for a in V.AUTHORS}}
        print(f"  {name}: n={n} (" + ", ".join(f"{a} {c}" for a, c in row["per_author"].items()) + ")")
        for k, m in M.items():
            near, wf, ok = counts(m, sl)
            row[k] = {"near": near, "ok": ok, "wrong_family": wf}
            print(f"    {k:<12} near {100 * near / n:5.1f}% ({near}/{n})   wrong family {100 * wf / n:4.1f}% ({wf}/{n})")
        for g in ("top", "family"):
            sc, nr = diff(S[f"ens3/{g}"], S["shipped"], sl), diff(col(M[f"ens3/{g}"], 0), col(M["shipped"], 0), sl)
            row[f"ens3/{g} - shipped"] = {"score": sc["diff"], "near": nr}
            print(f"    ens3/{g} - shipped: score {ci(sc['diff'])}   near {ci(nr['diff'])} ({nr['up']} / {nr['down']})")
        res[name] = row
    res["similarity"] = {i["id"]: round(sim[i["id"]], 4) for i in v3}
    return res


def section_c(M, picks, P2, miss1, v3):
    print("\nC. JOINT: intent near AND the matcher's primary exact on the same line (the planner needs both)")
    exact = {"rules v2 (on disk; r6 and cs after tuning, stt held out)": {i["id"]: P2[i["id"]]["exact"] for i in v3},
             "rules v1 (frozen before the lines; misses from eval_v3_rules_v1.log)": {i["id"]: i["id"] not in miss1 for i in v3}}
    res = {}
    for rules, ex in exact.items():
        print(f"  matcher {rules}")
        J = {k: {i["id"]: int(m[i["id"]][0] and ex[i["id"]]) for i in v3} for k, m in M.items()}
        for k in M:
            cells = []
            for name, sl in by_author(v3):
                j = sum(J[k][i["id"]] for i in sl)
                res.setdefault(rules.split(" (")[0], {}).setdefault(k, {})[name] = [j, len(sl)]
                cells.append(f"{name.split(' (')[0]} {rate(j, len(sl))}")
            print(f"    {k:<12} " + "   ".join(cells))
        for g in ("top", "family"):
            d = diff(J[f"ens3/{g}"], J["shipped"], v3)
            res[rules.split(" (")[0]][f"ens3/{g} - shipped"] = d
            print(f"    ens3/{g} - shipped: {ci(d['diff'])} ({d['up']} lines gained, {d['down']} lost)")
    orders = [i for i in v3 if i["maj"] != "NONE"]
    m, ex = M["ens3/family"], exact[next(iter(exact))]
    lost = [i for i in v3 if m[i["id"]][0] and not ex[i["id"]]]
    print(f"  ens3/family, rules v2: on the {len(orders)} lines whose truth is an order, near {counts(m, orders)[0]}, "
          f"near and exact place {sum(m[i['id']][0] and ex[i['id']] for i in orders)}")
    print("  near, but the place is wrong (truth -> pick; on a NONE pick the bot does nothing with the place):")
    for i in lost:
        print(f"    {i['id']:<10} {i['maj']} -> {picks['ens3/family'][i['id']]:<8} {i['text']!r}")
    res["near_but_place_wrong"] = [i["id"] for i in lost]
    return res


def section_d(ens3, items3, thr3):
    ens21, items21, thr21, _ = study("v21")
    ids = {i["id"] for i in items21}
    sl = [i for i in items3 if i["version"] != "v3" and i["id"] in ids]
    n_none = sum(i["maj"] == "NONE" for i in sl)
    print(f"\nD. THE {len(sl)} OLDER LINES, v21 study -> v3 study (both leave one author out, ens3; the v3 study adds the\n"
          "   v3 lines of the two training authors and the location seeds, and refits each fold's threshold)")
    res = {}
    for g in ("top", "family"):
        a, b = marks(ens3[g], sl), marks(ens21[g], sl)
        (na, wa, _), (nb, wb, _) = counts(a, sl), counts(b, sl)
        fa, fb = (round(V.score(p[g], sl)["fired_on_nonorder"] * n_none) for p in (ens3, ens21))
        sc = X.bootstrap(X.per_item(ens3[g], sl), X.per_item(ens21[g], sl), sl)
        nr, wf = diff(col(a, 0), col(b, 0), sl), diff(col(a, 1), col(b, 1), sl)
        changed = [i for i in sl if a[i["id"]][:2] != b[i["id"]][:2]]
        res[g] = {"v21": {"near": nb, "wrong_family": wb, "acts_on_nonorder": fb, "thresholds": thr21[g]},
                  "v3": {"near": na, "wrong_family": wa, "acts_on_nonorder": fa, "thresholds": thr3[g]},
                  "score": list(sc), "near": nr, "wrong_family": wf, "n_nonorder": n_none,
                  "picks_differ": sum(ens3[g][i["id"]] != ens21[g][i["id"]] for i in sl),
                  "changed": {i["id"]: [ens21[g][i["id"]], ens3[g][i["id"]]] for i in changed}}
        print(f"  {g} gate: fold thresholds (r6 / cs / stt) " + " / ".join(f"{thr21[g][h]:.2f}" for h in V.AUTHORS) + " -> " +
              " / ".join(f"{thr3[g][h]:.2f}" for h in V.AUTHORS))
        print(f"    near {nb} -> {na} ({ci(nr['diff'])}; {nr['up']} gained, {nr['down']} lost)   wrong family {wb} -> {wa} "
              f"({wf['up']} new, {wf['down']} removed)   acts on non-order {fb}/{n_none} -> {fa}/{n_none}")
        print(f"    score {ci(sc)} (the line eval_v3.log prints); picks that differ: {res[g]['picks_differ']}")
        print("    lines whose outcome changed (truth: v21 pick -> v3 pick):")
        for i in changed:
            what = [w for w, on in (("near lost", a[i["id"]][0] < b[i["id"]][0]), ("near gained", a[i["id"]][0] > b[i["id"]][0]),
                                    ("wrong family new", a[i["id"]][1] > b[i["id"]][1]),
                                    ("wrong family removed", a[i["id"]][1] < b[i["id"]][1])) if on]
            print(f"      {i['id']:<10} {str(i['maj']) + ':':<17} {ens21[g][i['id']]:<16} -> {ens3[g][i['id']]:<16} "
                  f"{', '.join(what):<32} {i['text']!r}")
    return res


def section_e(R, ship, v3):
    raw, strip = marks(ship["raw"], v3), marks(ship["strip"], v3)
    changed = [i for i in v3 if ship["raw"][i["id"]] != ship["strip"][i["id"]]]
    nr, wf = diff(col(strip, 0), col(raw, 0), v3), diff(col(strip, 1), col(raw, 1), v3)
    sc = X.bootstrap(X.per_item(ship["strip"], v3), X.per_item(ship["raw"], v3), v3)
    (n0, w0, _), (n1, w1, _) = counts(raw, v3), counts(strip, v3)
    print(f"\nE. SHIPPED BOT, raw line against 'strip' (attached side / colour words removed): "
          f"{sum(R['raw_text'][i['id']] != R['strip_text'][i['id']] for i in v3)} of {len(v3)} lines are rewritten")
    print(f"  near {n0} -> {n1} ({ci(nr['diff'])}), wrong family {w0} -> {w1}, score {ci(sc)}")
    print(f"  answers that differ: {len(changed)} ({nr['up']} better, {nr['down']} worse on near; exact sign test p={nr['sign_p']:.3f}); "
          "no line improves, so the interval cannot go above zero")
    for i in changed:
        cells = []
        for mode in ("raw", "strip"):
            top, conf = V.confidence(R[mode][i["id"]], R["gate"])
            cells.append(f"{mode} {ship[mode][i['id']]} ({top} {conf:.3f})")
        print(f"    {i['id']:<10} truth {i['maj']:<10} {' -> '.join(cells)}\n{'':15}{R['raw_text'][i['id']]!r} -> {R['strip_text'][i['id']]!r}")
    return {"rewritten": sum(R["raw_text"][i["id"]] != R["strip_text"][i["id"]] for i in v3),
            "raw": {"near": n0, "wrong_family": w0}, "strip": {"near": n1, "wrong_family": w1},
            "changed": {i["id"]: [ship["raw"][i["id"]], ship["strip"][i["id"]]] for i in changed},
            "near": nr, "wrong_family": wf, "score": list(sc)}


def section_f(P2, miss1, v3):
    print("\nF. MATCHER, exact primary per author: rules v1 (frozen before the lines; eval_v3_rules_v1.log) -> rules v2\n"
          "   (on disk; edited after the first blind run from the r6 and cs lines, stt not used)")
    res = {"per_author": {}}
    for name, sl in by_author(v3):
        k1, k2 = sum(i["id"] not in miss1 for i in sl), sum(P2[i["id"]]["exact"] for i in sl)
        up = sum(P2[i["id"]]["exact"] and i["id"] in miss1 for i in sl)
        down = sum(not P2[i["id"]]["exact"] and i["id"] not in miss1 for i in sl)
        res["per_author"][name] = {"v1": k1, "v2": k2, "n": len(sl), "gained": up, "lost": down}
        print(f"  {name:<16} {rate(k1, len(sl))} -> {rate(k2, len(sl))}   {up} gained, {down} lost"
              + (f", exact sign test p={sign_test(up, down):.2f}" if "stt" in name else ""))
    T = {i["id"]: P2[i["id"]]["t"] for i in v3}
    role = [i for i in v3 if T[i["id"]] and T[i["id"]]["role"]]
    flag = [i for i in v3 if T[i["id"]] and T[i["id"]]["flag"]]
    clean = sum(bool(T[i["id"]]) and not T[i["id"]]["role"] and not T[i["id"]]["flag"] for i in v3)
    both = [i["id"] for i in role if T[i["id"]]["flag"]]      # counted under the roles and under the flags
    res["role"] = dict(Counter(T[i["id"]]["role"] for i in role).most_common())
    res["flag"] = dict(Counter(T[i["id"]]["flag"] for i in flag).most_common())
    res["no_place"], res["no_role_no_flag"], res["role_and_flag"] = sum(T[i["id"]] is None for i in v3), clean, both
    print(f"  the {len(v3)} primaries (rules v2): {len(role)} carry a role (" + ", ".join(f"{r} {c}" for r, c in res["role"].items()) +
          f"), {len(flag)} a flag (" + ", ".join(f"{r} {c}" for r, c in res["flag"].items()) +
          f"), {len(both)} of them both ({', '.join(both)}), {clean} neither, {res['no_place']} lines have no place")
    print("  a role means 'the bot is NOT sent there' (locations.py), and eval_v3 does not score it; the primaries with one:")
    acting = lambda i: i["maj"] not in ("NONE", "WAIT")   # noqa: E731
    for r in res["role"]:
        sl = [i for i in role if T[i["id"]]["role"] == r]
        ex = [i for i in sl if acting(i) and P2[i["id"]]["exact"]]
        print(f"    {r:<7} {len(sl)} lines, {sum(acting(i) for i in sl)} with an order to act on as truth"
              + (f"; on {len(ex)} of them it IS the readers' target: {', '.join(i['id'] for i in ex)}" if ex else ""))
    res["role_on_acting_order_exact"] = [i["id"] for i in role if acting(i) and P2[i["id"]]["exact"]]
    return res


def section_g(items3):
    path = os.path.join(REVIEW, "fresh_author.json")
    A = json.load(io.open(path, encoding="utf-8"))
    stamp = io.open(os.path.join(REVIEW, "fresh_author.sha256"), encoding="utf-8").read().split()
    digest = hashlib.sha256(io.open(path, "rb").read()).hexdigest()
    lines = [dict(l, maj=l["intent"], accept={l["intent"]},
                  target=(l["target"]["object"], l["target"]["qualifier"], l["target"]["zone"])) for l in A["lines"]]
    place, plain = [l for l in lines if l["cat"] != "plain"], [l for l in lines if l["cat"] == "plain"]
    print(f"\nG. FRESH REVIEW AUTHOR (review_v3/fresh_author.json; sha256 {digest[:16]}... "
          f"{'equals' if digest == stamp[0] else 'DIFFERS FROM'} the stamp of {stamp[-1]})")
    print(f"   {len(lines)} lines: {len(place)} that name a place + {len(plain)} plain orders. ONE AI author who is also the ONLY\n"
          "   labeller (no second reader); blindness partial (written from blind/spec_v3.json, but the author's task text\n"
          "   carried the titles of earlier findings); short seed-like lines. Scored on the author's own label, no\n"
          "   alternates. A direction check, not a held-out rate.")
    words = lambda t: " ".join(w[0] for w in LOC.tokenize(t))   # noqa: E731
    length = lambda sl: sum(len(words(l["text"]).split()) for l in sl) / len(sl)   # noqa: E731
    train = {}
    for i in items3 + V.seed_items():
        train.setdefault(words(i["text"]), []).append(i["id"])      # one text can be several training rows
    same = {l["id"]: train[words(l["text"])] for l in lines if words(l["text"]) in train}
    print(f"   mean length in the matcher's tokens: place lines {length(place):.1f}, the project's v3 lines " + " / ".join(
        f"{a} {length([i for i in items3 if i['version'] == 'v3' and i['author'] == a]):.1f}" for a in V.AUTHORS) +
          f"; {len(same)} lines equal a training text\n   of the final model token for token (" +
          ", ".join(f"{k} = {' = '.join(v)}" for k, v in same.items()) + ")")
    P = primaries(lines)
    ex = lambda sl: sum(P[l["id"]]["exact"] for l in sl)   # noqa: E731
    res = {"sha256_matches": digest == stamp[0], "n_place": len(place), "n_plain": len(plain), "equal_to_training_text": same,
           "matcher": {"place": ex(place), "plain_no_place": sum(P[l["id"]]["t"] is None for l in plain), "all": ex(lines),
                       "misses": [l["id"] for l in lines if not P[l["id"]]["exact"]]}, "classifier": {}}
    print(f"  matcher rules v2, exact primary: place lines {rate(ex(place), len(place))}; no place found on "
          f"{res['matcher']['plain_no_place']}/{len(plain)} plain orders; all lines {rate(ex(lines), len(lines))}")
    print("    misses: " + "; ".join(f"{l['id']} {l['text']!r}" for l in lines if not P[l["id"]]["exact"]))
    M = {}
    # the archive holds the answers of one training run of v3 (review_v3/README.md): a re-trained model needs its own
    for name, f, which in (("shipped v2", "fresh_probs_v2.json", ""),
                           ("final v3", "fresh_probs_v3.json", ", the model as trained on this Mac (MPS), scored from archived "
                                                               "probabilities and to be re-run if the model is re-trained")):
        R = json.load(io.open(os.path.join(REVIEW, f), encoding="utf-8"))
        assert R["labels"] == V.INTENTS and R["families"] == V.FAMILY, f
        preds = {k: V.pick(row, R["gate"], R["threshold"])[0] for k, row in R["probs"].items()}
        M[name] = m = marks(preds, lines)
        res["classifier"][name] = row = {"model": R["model"], "gate": R["gate"], "threshold": R["threshold"]}
        print(f"  {name} ({R['model']}, {R['gate']} gate, {R['threshold']:.2f}){which}:")
        for label, sl in (("place lines", place), ("plain orders", plain)):
            near, wf, ok = counts(m, sl)
            joint = [sum(m[l["id"]][k] and P[l["id"]]["exact"] for l in sl) for k in (0, 2)]
            row[label] = {"n": len(sl), "near": near, "ok": ok, "wrong_family": wf, "near_and_place": joint[0], "ok_and_place": joint[1]}
            print(f"    {label:<12} near {rate(near, len(sl))}   exact ok {rate(ok, len(sl))}   wrong family {wf}/{len(sl)}"
                  + (f"\n{'':17}near and exact place {rate(joint[0], len(sl))}   exact intent and exact place {rate(joint[1], len(sl))}"
                     if sl is place else ""))
        print("    not near: " + ("; ".join(f"{l['id']} {l['intent']} -> {preds[l['id']]} {l['text']!r}"
                                            for l in lines if not m[l["id"]][0]) or "none"))
    for label, sl in (("place lines", place), ("plain orders", plain)):
        d = {k: diff(col(M["final v3"], j), col(M["shipped v2"], j), sl) for k, j in (("near", 0), ("ok", 2))}
        res["classifier"][f"v3 - v2, {label}"] = d
        print(f"  final v3 - shipped v2, {label}: near {d['near']['up']} lines better, {d['near']['down']} worse (exact sign test "
              f"p={d['near']['sign_p']:.3f}); exact ok {d['ok']['up']} better, {d['ok']['down']} worse (p={d['ok']['sign_p']:.4f})")
    return res


def main():
    print("POST-REVIEW numbers (eval_v3_review.py): computed after every v3 blind line, its labels and the first results\n"
          "had been seen (review of 2026-10-03/04, review_v3/README.md). Slices, joint rates and intervals were chosen with\n"
          "the results in view: not blind measurements. Stored probabilities only, no model loaded.\n")
    ens3, items3, thr3, E3 = study("v3")
    v3 = [i for i in items3 if i["version"] == "v3"]
    R, ship = shipped()
    picks = {"shipped": ship["raw"], "ens3/top": ens3["top"], "ens3/family": ens3["family"]}
    M = {k: marks(p, v3) for k, p in picks.items()}
    S = {k: X.per_item(p, v3) for k, p in picks.items()}     # the score per line, as eval_v3.log bootstraps it
    P2, miss1 = primaries(v3), rules_v1_misses(len(v3))
    res = {"_note": "POST-REVIEW numbers, computed after every v3 blind line was seen (eval_v3_review.py); "
                    "differences are [mean, 2.5%, 97.5%] of the paired bootstrap over lines, in points"}
    res["A_classifier"] = section_a(M, S, thr3, v3, R)
    res["B_novelty"] = section_b(E3, M, S, v3)
    res["C_joint"] = section_c(M, picks, P2, miss1, v3)
    res["D_older_lines"] = section_d(ens3, items3, thr3)
    res["E_strip"] = section_e(R, ship, v3)
    res["F_matcher"] = section_f(P2, miss1, v3)
    res["F_matcher"]["rules_v1_misses"] = sorted(miss1)
    res["G_fresh_author"] = section_g(items3)
    json.dump(res, io.open(os.path.join(HERE, "results_v3_review.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
