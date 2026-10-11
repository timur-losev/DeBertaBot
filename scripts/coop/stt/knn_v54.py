"""A nearest-neighbour memory of commands on the student's own pooled vectors (HANDOFF.md, "brains", tier 2): can the
classifier's encoder double as an embedder, so that a player adds a command at run time ("when I say frag out, do X")
without retraining, and so that an unsure line falls back to its nearest known command?

Reads the vectors distill_v54.py student writes per fold (kd54_emb_<size>_<tag>_s<seed>_f<fold>.npz: the fold's training
lines and its test lines through the fold's student) and the student's own probabilities, and compares on the held-out
lines, typed and as VCTK pool B heard them:
  head          the student's softmax head, gate and threshold fitted as score_v54.py fits them
  knn-all       cosine nearest neighbours among the fold's training lines (typed lines, seeds, transcripts), k = 1 and 5
  knn-seeds     ... among the seed commands only: what a memory of player-defined commands looks like
  hybrid        the head where its confidence reaches the threshold, else the k = 5 vote among all training lines
  new command   for every intent: its seeds alone are the memory for it, everything else keeps the full memory; a line of
                the intent counts when its nearest seed-of-that-intent is nearer than any other neighbour -- how often a
                command the player defined by a few phrases would be recognised from a new wording

    python knn_v54.py SIZE TAG [SEED]        e.g. python knn_v54.py xsmall kd 0
"""
import io, json, os, sys
from collections import Counter
os.environ["COOP_TAG"] = "v54"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import numpy as np
import coop_v2 as V

size, tag = sys.argv[1], sys.argv[2]
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
items = {i["id"]: i for i in V.load_items() if i["maj"]}
seeds = {s["id"]: s for s in V.seed_items()}
truth = {**{k: i["maj"] for k, i in items.items()}, **{k: s["maj"] for k, s in seeds.items()}}
student = json.load(io.open(os.path.join(HERE, f"kd54_student_{size}_{tag}_s{seed}.json"), encoding="utf-8"))
probs = student["probs"]


def base_id(k):
    return k.split("|", 1)[1] if "|" in k else k


def label_of(k):
    return truth[base_id(k)]


# ---- the head's gate and threshold, as score_v54.py fits them (training voices, r6 and cs lines)
spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731
FIT = ["clean", "kokoro", "kokorox", "vctkA"]


def by(c, keep):
    return {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == c and keep(items[k.split("|", 1)[1]])}


best = None
for gate in ("top", "family"):
    for t in range(0, 100, 2):
        near = cross = 0
        for c in FIT:
            p = by(c, spoken)
            s = V.score(V.picks(p, gate, t / 100), [items[k] for k in p])
            near += s["near_count"]; cross += s["cross_count"]
        v = near - 2 * cross
        if best is None or v > best[0] or (v == best[0] and gate == "top" and best[1] != "top"):
            best = (v, gate, t / 100)
_, gate, thr = best
print(f"student {size} {tag} seed {seed}: head gate {gate}, threshold {thr:.2f}")

# ---- the vectors, fold by fold
folds = []
for f in range(5):
    z = np.load(os.path.join(HERE, f"kd54_emb_{size}_{tag}_s{seed}_f{f}.npz"))
    x = z["x"].astype("float32")
    x /= np.linalg.norm(x, axis=1, keepdims=True) + 1e-9
    folds.append({"ids": list(z["ids"]), "x": x, "train": list(z["train"]), "test": list(z["test"])})


def vote(neigh_labels, neigh_sims):
    c = Counter()
    for l, s in zip(neigh_labels, neigh_sims):
        c[l] += s
    return c.most_common(1)[0][0]


def neighbours(cond_keep):
    """Per held-out line under the condition: (base id, [(label, sim)] among all training lines, nearest first,
    [(label, sim)] among the seeds, the head's probabilities, truth, best own-seed sim, best other-intent sim)."""
    out = []
    for fd in folds:
        pos = {k: i for i, k in enumerate(fd["ids"])}
        tr = [k for k in fd["train"]]
        tr_x = fd["x"][[pos[k] for k in tr]]
        tr_y = [label_of(k) for k in tr]
        sd = [k for k in tr if k.startswith("seed_")]
        sd_x = fd["x"][[pos[k] for k in sd]]
        sd_y = [label_of(k) for k in sd]
        te = [k for k in fd["test"] if k.split("|", 1)[0] == cond_keep and spoken(items[base_id(k)])]
        if not te:
            continue
        te_x = fd["x"][[pos[k] for k in te]]
        S_all = te_x @ tr_x.T
        S_sd = te_x @ sd_x.T
        for r, k in enumerate(te):
            o = np.argsort(-S_all[r])[:5]
            o2 = np.argsort(-S_sd[r])[:5]
            y = label_of(k)
            own = [j for j, l in enumerate(sd_y) if l == y]
            others = [j for j, l in enumerate(tr_y) if l != y]
            out.append((base_id(k), [(tr_y[j], float(S_all[r, j])) for j in o], [(sd_y[j], float(S_sd[r, j])) for j in o2], probs[k], y,
                        float(S_sd[r, own].max()) if own else None, float(S_all[r, others].max()) if others else None))
    return out


def fit_sim_gate():
    """The similarity under which the k = 5 vote among all training lines abstains (NONE): fitted on the training
    voices by the project's criterion, as the head's threshold is."""
    best = None
    rows = [x for c in FIT for x in neighbours(c)]
    for s in [i / 100 for i in range(50, 100)]:
        preds = {}
        for bid, nb, _, _, _, _, _ in rows:
            preds[bid + "|" + str(id(nb))] = vote([l for l, _ in nb], [x for _, x in nb]) if nb[0][1] >= s else "NONE"
        sc = V.score(preds, [dict(items[k.split("|", 1)[0]], id=k) for k in preds])
        v = sc["near_count"] - 2 * sc["cross_count"]
        if best is None or v > best[0]:
            best = (v, s)
    return best[1]


SIM_GATE = fit_sim_gate()
print(f"nearest-neighbour similarity gate (fitted on the training voices like the head's threshold): {SIM_GATE:.2f}")


def run(cond_keep, title):
    """cond_keep: test id prefix to keep ("typed", "vctkB")."""
    rows = {"head": {}, "knn-1 all": {}, "knn-5 all": {}, "knn-5 all, gated": {}, "knn-1 seeds": {}, "knn-5 seeds": {}, "hybrid": {},
            "hybrid, gated": {}}
    newcmd = Counter()
    newcmd_n = Counter()
    for bid, nb, nbs, p, y, own_best, other_best in neighbours(cond_keep):
        rows["knn-1 all"][bid] = nb[0][0]
        rows["knn-5 all"][bid] = vote([l for l, _ in nb], [x for _, x in nb])
        rows["knn-5 all, gated"][bid] = rows["knn-5 all"][bid] if nb[0][1] >= SIM_GATE else "NONE"
        rows["knn-1 seeds"][bid] = nbs[0][0]
        rows["knn-5 seeds"][bid] = vote([l for l, _ in nbs], [x for _, x in nbs])
        intent, conf = V.pick(p, gate, 0.0)
        rows["head"][bid] = intent if conf >= thr else "NONE"
        rows["hybrid"][bid] = intent if conf >= thr else rows["knn-5 all"][bid]
        rows["hybrid, gated"][bid] = intent if conf >= thr else rows["knn-5 all, gated"][bid]
        if own_best is not None and other_best is not None:
            newcmd_n[y] += 1
            newcmd[y] += own_best > other_best
    print(f"\n{title}: {len(rows['head'])} lines")
    print(f"  {'system':18s} {'near':>6s} {'wrong fam':>10s} {'acts on non-order':>18s} {'criterion':>10s}")
    for name, preds in rows.items():
        s = V.score(preds, [items[k] for k in preds])
        print(f"  {name:18s} {100 * s['near']:6.1f} {100 * s['cross']:9.1f}% {100 * s['fired_on_nonorder']:17.1f}% {100 * (s['near'] - 2 * s['cross']):10.1f}")
    tot = sum(newcmd.values()); n = sum(newcmd_n.values())
    print(f"  new command (seeds only know the intent): recognised {tot}/{n} = {100 * tot / max(n, 1):.1f}%; worst: " +
          ", ".join(f"{k} {newcmd[k]}/{newcmd_n[k]}" for k, _ in sorted(newcmd_n.items(), key=lambda kv: newcmd[kv[0]] / kv[1])[:6]))


run("typed", "held-out lines, typed")
run("vctkB", "held-out lines as VCTK pool B heard them (unseen speakers)")
