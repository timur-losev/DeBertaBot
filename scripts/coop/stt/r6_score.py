"""The result of r6_build.py: every r6 line predicted by models that never saw it, typed or spoken.

Gate and threshold are fitted the project's way (coop_v2.fit_threshold, criterion near - 2 * wrong family) on the
lines as Parakeet heard them from the TRAINING voices; the VCTK pool-B rows are then an honest test: unseen line,
unseen speaker, threshold not fitted on it. Writes bot_config.json next to the final models."""
import io, json, os, sys
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
ARM = sys.argv[1] if len(sys.argv) > 1 else "main"
OUT_DIR = os.path.join(HERE, "models_out", "coop-deberta-v3-ens3-r6stt" if ARM == "main" else f"coop-deberta-v3-ens3-r6{ARM}-stt")
WHAT = {"main": "r6 lines + seed commands", "cs": "r6 and cs lines + seed commands", "csstt": "r6, cs and stt lines + seed commands"}[ARM]
items = {i["id"]: i for i in V.load_items() if i["author"] == "r6" and i["maj"]}
FIT = ["clean", "kokoro", "kokorox", "vctkA"]
SHOW = [("typed", "typed text"), ("clean", "Windows voices"), ("kokoro", "Kokoro, English voices"), ("kokorox", "Kokoro, other-language voices"),
        ("vctkA", "VCTK, speakers used in training"), ("vctkB", "VCTK, speakers never in training")]


def load(arm, seeds):
    runs = []
    for s in seeds:
        p = os.path.join(HERE, f"r6oof_{arm}_{s}.json")
        if os.path.exists(p):
            runs.append(json.load(io.open(p, encoding="utf-8"))["probs"])
    if not runs:
        return None
    return {k: [sum(r[k][j] for r in runs) / len(runs) for j in range(len(V.INTENTS))] for k in runs[0]}, len(runs)


def by_cond(probs, cond):
    return {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == cond}


def fit(probs):
    """one gate and one threshold for the spoken lines of the training voices, pooled"""
    best = None
    for gate in ("top", "family"):
        for t in range(0, 100, 2):
            near = cross = 0
            for c in FIT:
                p = by_cond(probs, c)
                s = V.score(V.picks(p, gate, t / 100), [items[k] for k in p])
                near += s["near_count"]; cross += s["cross_count"]
            v = near - 2 * cross
            if best is None or v > best[0] or (v == best[0] and gate == "top" and best[1] != "top"):
                best = (v, gate, t / 100)
    return best[1], best[2]


def table(name, probs, gate, thr):
    print(f"\n{name}: gate {gate}, threshold {thr:.2f}")
    print(f"  {'what the classifier is given':38s} {'near':>6s} {'wrong fam':>10s} {'acts on non-order':>18s} {'criterion':>10s}")
    res = {}
    for c, label in SHOW:
        p = by_cond(probs, c)
        s = V.score(V.picks(p, gate, thr), [items[k] for k in p])
        res[c] = 100 * (s["near"] - 2 * s["cross"])
        print(f"  {label:38s} {100 * s['near']:6.1f} {100 * s['cross']:9.1f}% {100 * s['fired_on_nonorder']:17.1f}% {res[c]:10.1f}   n={s['n']}")
    return res


main = load(ARM, [0, 1, 2])
assert main, "no results yet"
gate, thr = fit(main[0])
print(f"r6 lines: {len(items)}; non-orders among them: {sum(i['maj'] == 'NONE' for i in items.values())}")
table(f"BOT ({ARM}), ensemble of {main[1]} seeds: {WHAT}, typed and as Parakeet heard them", main[0], gate, thr)
print("\n--- single models (seed 0), each with its own fitted gate and threshold: what the data choices are worth")
for arm, label in (("base", "typed text only (no Parakeet output in training)"), ("main", "r6 + seeds with Parakeet output"), ("cs", "the same + the cs author's lines"), ("csstt", "the same + the stt author's typed lines"), ("csnorm", "as cs, but no case and no punctuation anywhere")):
    r = load(arm, [0])
    if r:
        g, t = fit(r[0])
        table(f"{arm}: {label}", r[0], g, t)
if os.path.isdir(OUT_DIR) and all(os.path.exists(os.path.join(OUT_DIR, f"seed{s}", "model.safetensors")) for s in (0, 1, 2)):
    cfg = {"labels": V.INTENTS, "threshold": thr, "gate": gate, "families": V.FAMILY,
           "phrases": {k: v["label"] for k, v in V.I.items()}, "base_model": "microsoft/deberta-v3-base",
           "members": ["seed0", "seed1", "seed2"],
           "trained_on": WHAT + " (seed_commands_v31.json), typed and as Parakeet TDT 0.6B v2 heard them "
                         "from synthesized voices (Windows, Kokoro, VCTK pool A)",
           "threshold_from": "5-fold out-of-fold predictions on the r6 lines as Parakeet heard them from the training voices, three seeds averaged",
           "input": "speech-to-text output lowercased, final .!? stripped"}
    json.dump(cfg, io.open(os.path.join(OUT_DIR, "bot_config.json"), "w", encoding="utf-8"), indent=1)
    print(f"\nbot_config.json written: {OUT_DIR}")
