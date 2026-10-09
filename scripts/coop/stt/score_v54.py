"""The v54 build's check (as score_v4.py): every line predicted by models that never saw it, typed or spoken; three seeds
averaged. Gate and threshold: the project's criterion (near - 2 * wrong family; ties -> the lower threshold, top gate on
a tie) on the r6 and cs lines as Parakeet heard them from the training voices. VCTK pool B is then the honest row:
unseen line, unseen speaker, threshold not fitted on it. Also: the seventeen intents added since v4 one by one, and the older lines
alone (the lines v4 was checked on, with their v54 truth). Writes bot_config.json next to the final models."""
import io, json, os, sys
from collections import Counter
os.environ["COOP_TAG"] = "v54"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v54"))
items = {i["id"]: i for i in V.load_items() if i["maj"]}
FIT = ["clean", "kokoro", "kokorox", "vctkA"]
SHOW = [("typed", "typed text"), ("clean", "Windows voices"), ("kokoro", "Kokoro, English voices"), ("kokorox", "Kokoro, other-language voices"),
        ("vctkA", "VCTK, speakers used in training"), ("vctkB", "VCTK, speakers never in training")]
runs = [json.load(io.open(os.path.join(HERE, f"finaloof54_{s}.json"), encoding="utf-8")) for s in (0, 1, 2)
        if os.path.exists(os.path.join(HERE, f"finaloof54_{s}.json"))]
assert runs, "no results yet"
probs = {k: [sum(r["probs"][k][j] for r in runs) / len(runs) for j in range(len(V.INTENTS))] for k in runs[0]["probs"]}


def by(c, keep):
    return {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == c and keep(items[k.split("|", 1)[1]])}


spoken = lambda i: i["author"] in ("r6", "cs")
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
print(f"ensemble of {len(runs)} seeds, {runs[0]['epochs']} epochs; gate {gate}, threshold {thr:.2f}; "
      f"{len(items)} lines, {sum(i['version'] in ('v5', 'v51', 'v52', 'v53', 'v54') for i in items.values())} of them v5 ... v54 lines, "
      f"{sum('reread' in i['version'] for i in items.values())} lines with a re-read truth")


def table(title, keep):
    print(f"\n{title}")
    print(f"  {'what the classifier is given':38s} {'near':>6s} {'wrong fam':>10s} {'acts on non-order':>18s} {'criterion':>10s}")
    for c, label in SHOW:
        p = by(c, keep)
        if not p:
            continue
        s = V.score(V.picks(p, gate, thr), [items[k] for k in p])
        print(f"  {label:38s} {100 * s['near']:6.1f} {100 * s['cross']:9.1f}% {100 * s['fired_on_nonorder']:17.1f}% {100 * (s['near'] - 2 * s['cross']):10.1f}   n={s['n']}")


table("r6 and cs lines, all", spoken)
NEWER = lambda i: i["version"].split("-")[0] in ("v5", "v51", "v52", "v53", "v54")  # noqa: E731
table("r6 and cs lines written for v5 ... v54", lambda i: spoken(i) and NEWER(i))
table("r6 and cs lines written for v54 only", lambda i: spoken(i) and i["version"] == "v54")
table("r6 and cs lines bot v53 was checked on (722, with their v54 truth)", lambda i: spoken(i) and i["version"] != "v54")
table("r6 and cs older lines (the 422 lines v4 was checked on, with their v54 truth)", lambda i: spoken(i) and not NEWER(i))
table("stt lines (typed only, never voiced)", lambda i: i["author"] == "stt")

print("\nthe new intents (r6 and cs lines whose truth is the intent): picked exactly / in its family / another order / nothing")
for c, label in SHOW:
    p = by(c, spoken)
    pk = V.picks(p, gate, thr)
    row = []
    for intent in sorted(V.NEW5 | V.NEW51 | V.NEW52 | V.NEW53 | V.NEW54):
        ids = [k for k in p if items[k]["maj"] == intent]
        exact = sum(pk[k] == intent for k in ids)
        none = sum(pk[k] == "NONE" for k in ids)
        other = Counter(pk[k] for k in ids if pk[k] not in (intent, "NONE"))
        row.append(f"{intent} {exact}/{len(ids)}" + (f" (nothing {none})" if none else "")
                   + (" (" + ", ".join(f"{a} {b}" for a, b in other.most_common(3)) + ")" if other else ""))
    took = Counter((items[k]["maj"], pk[k]) for k in p if pk[k] in V.NEW5 | V.NEW51 | V.NEW52 | V.NEW53 | V.NEW54 and pk[k] not in items[k]["accept"])
    print(f"  {label:38s} " + " | ".join(row))
    if took:
        print(f"  {'':38s} wrongly picked a new intent: " + ", ".join(f"{a}->{b} {n}" for (a, b), n in took.most_common(6)))

print("\nthe same check at other thresholds (r6 and cs lines, VCTK speakers never in training):")
p = by("vctkB", spoken)
for g in ("top", "family"):
    row = []
    for t in (0.3, 0.5, 0.62, 0.7, 0.8, 0.9):
        s = V.score(V.picks(p, g, t), [items[k] for k in p])
        row.append(f"{t:.2f}: crit {100 * (s['near'] - 2 * s['cross']):.1f}, wf {100 * s['cross']:.1f}%, non-order {100 * s['fired_on_nonorder']:.1f}%")
    print(f"  gate {g}: " + " | ".join(row))
if all(os.path.exists(os.path.join(OUT_DIR, f"seed{s}", "model.safetensors")) for s in (0, 1, 2)):
    n_lines, n_seeds = len(items), len(V.seed_items())
    cfg = {"labels": V.INTENTS, "threshold": thr, "gate": gate, "families": V.FAMILY,
           "phrases": {k: v["label"] for k, v in V.I.items()}, "base_model": "microsoft/deberta-v3-base",
           "members": ["seed0", "seed1", "seed2"],
           "recipe": {"max_len": 64, "batch": 16, "epochs": runs[0]["epochs"], "weight_decay": 0.01, "warmup": 0.1, "lr": 5e-05, "dtype": "float32", "seeds": [0, 1, 2]},
           "trained_on": f"{n_lines} lines from 3 AI-written authors + {n_seeds} seed commands (seed_commands_v54.json), typed, plus what Parakeet TDT 0.6B v2 "
                         "heard when the r6 and cs lines and the seed commands were read by synthesized voices (Windows, Kokoro, VCTK pool A)",
           "threshold_from": "5-fold out-of-fold predictions (three seeds averaged) on the r6 and cs lines as Parakeet heard them from the training voices; "
                             "criterion near - 2*wrong-family",
           "input": "speech-to-text output lowercased, final .!? stripped, inner punctuation kept"}
    json.dump(cfg, io.open(os.path.join(OUT_DIR, "bot_config.json"), "w", encoding="utf-8"), indent=1)
    print(f"\nbot_config.json written: {OUT_DIR}")
