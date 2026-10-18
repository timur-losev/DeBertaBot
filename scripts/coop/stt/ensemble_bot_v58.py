"""bot_config.json for the v58 ensemble, with the gate and the threshold fitted on build_v58.py's own out-of-fold runs
(three seeds, five folds each, the recipe that is shipped), then export_cpp.py, gen_tests.py and gen_world_tests.py for its
cpp/ directory. Prints the numbers: the fitted gate and threshold, VCTK pool B (speakers that only read test lines), typed,
and the v57 lines alone (v58 has none of its own: its seeds are tested by score_cont_v58.py).

    python ensemble_bot_v58.py
"""
import io, json, os, subprocess, sys
os.environ["COOP_TAG"] = "v58"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, COOP)
import coop_v2 as V

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v58"))
assert all(os.path.exists(os.path.join(OUT, f"seed{s}", "model.safetensors")) for s in (0, 1, 2)), "no final v58 members"
items = {i["id"]: i for i in V.load_items() if i["maj"]}
seeds = {s["id"]: s for s in V.seed_items()}
spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731
runs = [json.load(io.open(os.path.join(HERE, f"finaloof58_{s}.json"), encoding="utf-8"))["probs"] for s in (0, 1, 2)]
probs = {}
for r in runs:
    for k, v in r.items():
        probs.setdefault(k, []).append(v)
probs = {k: [sum(x[j] for x in v) / len(v) for j in range(len(V.INTENTS))] for k, v in probs.items() if len(v) == 3}


def by(c, keep=lambda i: True):
    return {k.split("|", 1)[1]: v for k, v in probs.items()
            if k.split("|", 1)[0] == c and k.split("|", 1)[1] in items and keep(items[k.split("|", 1)[1]])}


def crit(p, gate, t):
    s = V.score(V.picks(p, gate, t), [items[k] for k in p])
    return s, 100 * (s["near"] - 2 * s["cross"])


best = None
for gate in ("top", "family"):
    for t in range(0, 100, 2):
        near = cross = 0
        for c in ("clean", "kokoro", "kokorox", "vctkA"):
            s = V.score(V.picks(by(c, spoken), gate, t / 100), [items[k] for k in by(c, spoken)])
            near += s["near_count"]; cross += s["cross_count"]
        v = near - 2 * cross
        # a tie between the gates goes to the family gate, v57's: on v58's runs both gates scored 3537 at 0.66, and the family
        # gate read round three's blind chains better (81.3 typed, 58.3 heard, against 79.3 and 57.7 under the top gate:
        # "come to my pin" is FOLLOW_ME 0.60 and MOVE_TO beside it, one family)
        if best is None or v > best[0] or (v == best[0] and gate == "family" and best[1] != "family"):
            best = (v, gate, t / 100)
_, gate, thr = best
print(f"v58 ensemble, build_v58.py out-of-fold (three seeds): gate {gate}, threshold {thr:.2f}")
for name, p in (("VCTK pool B, r6+cs", by("vctkB", spoken)), ("typed, all lines", by("typed")),
                ("typed, v57 lines", by("typed", lambda i: i["version"] == "v57")),
                ("VCTK pool B, v57 lines", by("vctkB", lambda i: spoken(i) and i["version"] == "v57")),
                ("typed, v1-v56 lines", by("typed", lambda i: i["version"] != "v57"))):
    s, c = crit(p, gate, thr)
    print(f"  {name:24} n={s['n']:4}  near {100 * s['near']:.1f}  wrong family {100 * s['cross']:.1f}%  criterion {c:.1f}")
cfg = {"labels": V.INTENTS, "threshold": thr, "gate": gate, "families": V.FAMILY,
       "phrases": {k: v["label"] for k, v in V.I.items()}, "base_model": "microsoft/deberta-v3-base", "members": ["seed0", "seed1", "seed2"],
       "recipe": {"max_len": 64, "batch": 16, "epochs": 12, "weight_decay": 0.01, "warmup": 0.1, "lr": 5e-05, "dtype": "float32", "seeds": [0, 1, 2]},
       "trained_on": f"{len(items)} lines from 3 AI-written authors + {len(seeds)} seed commands (seed_commands_v58.json), typed, plus what "
                     "Parakeet TDT 0.6B v2 heard when the r6 and cs lines and the seed commands were read by synthesized voices (Windows, Kokoro, "
                     "VCTK pool A); transcripts that are word for word a typed command of another intent left out (build_v58.py)",
       "threshold_from": "build_v58.py's 5-fold out-of-fold predictions, three seeds with their own splits, averaged, on the r6 and cs lines "
                         "as Parakeet heard them from the training voices; criterion near - 2*wrong-family. Work-machine build (CUDA)",
       "input": "speech-to-text output lowercased, final .!? stripped, inner punctuation kept"}
json.dump(cfg, io.open(os.path.join(OUT, "bot_config.json"), "w", encoding="utf-8"), indent=1)
env = {**os.environ, "HF_HUB_OFFLINE": "1", "COOP_TAG": "v58"}
subprocess.run([sys.executable, os.path.join(COOP, "export_cpp.py"), OUT], check=True, env=env)
subprocess.run([sys.executable, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_tests.py"), OUT], check=True, env=env)
subprocess.run([sys.executable, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_world_tests.py"), OUT], check=True, env=env)
