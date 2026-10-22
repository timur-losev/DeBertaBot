"""Precision and recall of every reader on the same held-out lines (build_v61.py's split, seed S fold F).

Readers (each a probability row over the 57 intents per test line):
  DeBERTa seed S       the v61 out-of-fold model of this very split (finaloof61_<S>.json): one DeBERTa-v3-base
  DeBERTa ensemble     the average of the three v61 out-of-fold runs (every line unseen by each), as the bot ships
  decider zero-shot    the published decider-2b, upstream temperature 1.18 (schema-first)
  decider LoRA         decider-2b + the LoRA of run.py, bf16 on the GPU
  decider LoRA Q8_0 / Q4_K_M   the same merged into the weights, GGUF, llama.cpp on the CPU (decider_eval)

Metrics, per subset of the test lines (the owner's own heard lines; typed lines; unseen voices = VCTK pool B; the Russian
voices; all heard lines):
  accuracy               the top intent is the labelled one
  macro P / R / F1       per intent at the top intent, averaged over the intents present in the subset
  as the bot acts        the bot's own rule (coop_v2.pick: family gate, threshold 0.66): it acts on a line when its pick is
                         an order; precision = acted right / acted; recall = acted right / lines that are orders;
                         wrong = acted wrong / all lines (a line labelled NONE that the bot acts on is wrong too)
  recall at precision    the threshold swept on the family mass: the best recall with acting precision >= 97% / 99%
                         (chosen on these very lines for every reader alike: a comparison, not a deployable number)
Differences: paired bootstrap (2,000 resamples) of the accuracy difference, decider LoRA minus DeBERTa ensemble.

    python compare.py [--seed 0 --fold 0]   -> results/compare_s0f0.md
"""
import argparse, glob, io, json, math, os, random
import common as C
import coop_v2 as V

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--fold", type=int, default=0)
a = ap.parse_args()
tag = f"s{a.seed}f{a.fold}"
_, test = C.split(a.seed, a.fold)
gold = {r["id"]: r["maj"] for r in test}
L = list(V.INTENTS)
assert L == C.intents()[0]


def softmax(row, T=1.0):
    m = max(row)
    e = [math.exp((x - m) / T) for x in row]
    s = sum(e)
    return [x / s for x in e]


readers = {}
oof = [json.load(io.open(os.path.join(C.STT, f"finaloof61_{s}.json"), encoding="utf-8"))["probs"] for s in (0, 1, 2)]
readers[f"DeBERTa seed {a.seed}"] = {k: oof[a.seed][k] for k in gold}
readers["DeBERTa ensemble"] = {k: [sum(o[k][j] for o in oof) / 3 for j in range(len(L))] for k in gold}
for name, fname, T in (("decider zero-shot", "zeroshot", 1.18), ("decider LoRA bf16", "lora", 1.0)):
    p = os.path.join(C.RES, f"{fname}_{tag}.json")
    if os.path.exists(p):
        d = json.load(io.open(p, encoding="utf-8"))
        readers[name] = {k: softmax(v, T) for k, v in d["logits"].items()}
for p in sorted(glob.glob(os.path.join(C.RES, f"gguf_*_{tag}.jsonl"))):
    rows = [json.loads(l) for l in io.open(p, encoding="utf-8")]
    head, rows = rows[0], rows[1:]
    if len(rows) == len(gold):
        q = os.path.basename(p)[len("gguf_"):-len(f"_{tag}.jsonl")]
        readers[f"decider {q}"] = {r["id"]: softmax(r["logits"]) for r in rows}
if "decider LoRA bf16" in readers:      # exploratory: the two families averaged, equal weights, no tuning
    readers["DeBERTa ensemble + decider LoRA"] = {k: [(x + y) / 2 for x, y in zip(readers["DeBERTa ensemble"][k],
                                                                                  readers["decider LoRA bf16"][k])] for k in gold}
for name, r in readers.items():
    assert set(r) == set(gold), (name, len(set(gold) - set(r)))

subsets = {"owner's lines": lambda k: k.startswith("owner|"), "typed": lambda k: k.startswith("typed|"),
           "unseen voices": lambda k: k.startswith("vctkB|"), "Russian voices": lambda k: k.startswith("ru|"),
           "all heard": lambda k: k.split("|")[0] in ("vctkB", "vctkA", "kokoro", "kokorox", "clean", "ru", "de")}


def metrics(probs, keys, thr=0.66):
    top = {k: L[max(range(len(L)), key=probs[k].__getitem__)] for k in keys}
    acc = sum(top[k] == gold[k] for k in keys) / len(keys)
    present = sorted({gold[k] for k in keys})
    P, R = [], []
    for c in present:
        tp = sum(top[k] == c and gold[k] == c for k in keys)
        pp = sum(top[k] == c for k in keys)
        P.append(tp / pp if pp else 0.0)
        R.append(tp / sum(gold[k] == c for k in keys))
    F = [2 * p * r / (p + r) if p + r else 0.0 for p, r in zip(P, R)]
    act = act_bot(probs, keys, thr)
    return {"acc": acc, "mP": sum(P) / len(P), "mR": sum(R) / len(R), "mF": sum(F) / len(F), **act,
            "r97": best_recall(probs, keys, 0.97), "r99": best_recall(probs, keys, 0.99)}


def act_bot(probs, keys, thr):
    acted = right = wrong = 0
    orders = sum(gold[k] != "NONE" for k in keys)
    for k in keys:
        p = V.pick(probs[k], "family", thr)[0]
        if p != "NONE":
            acted += 1
            right += p == gold[k]
            wrong += p != gold[k]
    return {"P": right / acted if acted else 0.0, "R": right / orders if orders else 0.0, "wrong": wrong / len(keys)}


def best_recall(probs, keys, prec):
    conf = sorted(((V.pick(probs[k], "family", 0.0)[1], V.pick(probs[k], "family", 0.0)[0], k) for k in keys), reverse=True)
    orders = sum(gold[k] != "NONE" for k in keys)
    best, acted, right = (0.0, None), 0, 0
    for c, p, k in conf:                     # lowering the threshold one line at a time
        if p == "NONE":
            continue
        acted += 1
        right += p == gold[k]
        if right / acted >= prec and right / orders > best[0]:
            best = (right / orders, c)
    return best


def boot(diffs, n=2000):
    rng = random.Random(0)
    m = len(diffs)
    s = sorted(sum(diffs[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return s[int(0.025 * n)], s[int(0.975 * n)]


out = [f"# decider-2b against DeBERTa v61: split seed {a.seed}, fold {a.fold}", "",
       f"{len(test)} held-out lines: " + ", ".join(f"{n} {sum(f(k) for k in gold)}" for n, f in subsets.items()), ""]
for sname, f in subsets.items():
    keys = [k for k in gold if f(k)]
    out += [f"## {sname} ({len(keys)} lines, {sum(gold[k] != 'NONE' for k in keys)} orders)", "",
            "| reader | accuracy | macro P | macro R | macro F1 | acting P @0.66 | acting R @0.66 | wrong acts | R @ P>=97% | R @ P>=99% |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for name, probs in readers.items():
        m = metrics(probs, keys)
        out.append(f"| {name} | {100 * m['acc']:.1f} | {100 * m['mP']:.1f} | {100 * m['mR']:.1f} | {100 * m['mF']:.1f} | "
                   f"{100 * m['P']:.1f} | {100 * m['R']:.1f} | {100 * m['wrong']:.1f} | {100 * m['r97'][0]:.1f} | {100 * m['r99'][0]:.1f} |")
    if "decider LoRA bf16" in readers:
        top = lambda r, k: L[max(range(len(L)), key=r[k].__getitem__)]   # noqa: E731
        d = [(top(readers["decider LoRA bf16"], k) == gold[k]) - (top(readers["DeBERTa ensemble"], k) == gold[k]) for k in keys]
        lo, hi = boot(d)
        out += ["", f"Accuracy, decider LoRA bf16 minus DeBERTa ensemble: {100 * sum(d) / len(d):+.1f} points "
                    f"(95% bootstrap {100 * lo:+.1f} .. {100 * hi:+.1f})"]
    out.append("")
text = "\n".join(out)
io.open(os.path.join(C.RES, f"compare_{tag}.md"), "w", encoding="utf-8").write(text)
print(text)
