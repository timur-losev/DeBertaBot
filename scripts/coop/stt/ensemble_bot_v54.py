"""bot_config.json for the v54 ensemble trained on the work machine, with the gate and threshold fitted on the fold
teachers' out-of-fold run (distill_v54.py teachers: the same recipe on one fixed 5-fold split; build_v54.py's own
out-of-fold run with its per-seed splits was not run here -- the owner runs it on the MacBook, and score_v54.py then
writes the config that counts). Then export_cpp.py, gen_tests.py and gen_world_tests.py for its cpp/ directory.

    python ensemble_bot_v54.py
"""
import io, json, os, subprocess, sys
os.environ["COOP_TAG"] = "v54"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, COOP)
import coop_v2 as V

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v54"))
assert all(os.path.exists(os.path.join(OUT, f"seed{s}", "model.safetensors")) for s in (0, 1, 2)), "no final v54 members"
items = {i["id"]: i for i in V.load_items() if i["maj"]}
spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731
runs = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2)]
assert all(len(r) == 5 for r in runs), "the fold teachers are not all done"
probs = {}
for r in runs:
    for f in r.values():
        for k, v in f["test"].items():
            probs.setdefault(k, []).append(v)
probs = {k: [sum(x[j] for x in v) / 3 for j in range(len(V.INTENTS))] for k, v in probs.items() if len(v) == 3}


def by(c):
    return {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == c and spoken(items[k.split("|", 1)[1]])}


best = None
for gate in ("top", "family"):
    for t in range(0, 100, 2):
        near = cross = 0
        for c in ("clean", "kokoro", "kokorox", "vctkA"):
            p = by(c)
            s = V.score(V.picks(p, gate, t / 100), [items[k] for k in p])
            near += s["near_count"]; cross += s["cross_count"]
        v = near - 2 * cross
        if best is None or v > best[0] or (v == best[0] and gate == "top" and best[1] != "top"):
            best = (v, gate, t / 100)
_, gate, thr = best
p = by("vctkB")
s = V.score(V.picks(p, gate, thr), [items[k] for k in p])
print(f"v54 ensemble, fold teachers' out-of-fold: gate {gate}, threshold {thr:.2f}; VCTK pool B near {100 * s['near']:.1f}, wrong family "
      f"{100 * s['cross']:.1f}%, criterion {100 * (s['near'] - 2 * s['cross']):.1f} (n={s['n']})")
cfg = {"labels": V.INTENTS, "threshold": thr, "gate": gate, "families": V.FAMILY,
       "phrases": {k: v["label"] for k, v in V.I.items()}, "base_model": "microsoft/deberta-v3-base", "members": ["seed0", "seed1", "seed2"],
       "recipe": {"max_len": 64, "batch": 16, "epochs": 12, "weight_decay": 0.01, "warmup": 0.1, "lr": 5e-05, "dtype": "float32", "seeds": [0, 1, 2]},
       "trained_on": f"{len(items)} lines from 3 AI-written authors + {len(V.seed_items())} seed commands (seed_commands_v54.json), typed, plus what "
                     "Parakeet TDT 0.6B v2 heard when the r6 and cs lines and the seed commands were read by synthesized voices (Windows, Kokoro, "
                     "VCTK pool A); transcripts that are word for word a typed command of another intent left out (build_v54.py)",
       "threshold_from": "5-fold out-of-fold predictions of the same recipe on ONE fixed split shared by the three seeds (distill_v54.py teachers), "
                         "three seeds averaged, on the r6 and cs lines as Parakeet heard them from the training voices; criterion near - 2*wrong-family. "
                         "Work-machine build (CUDA); build_v54.py's own out-of-fold run is the MacBook's (score_v54.py)",
       "input": "speech-to-text output lowercased, final .!? stripped, inner punctuation kept"}
json.dump(cfg, io.open(os.path.join(OUT, "bot_config.json"), "w", encoding="utf-8"), indent=1)
env = {**os.environ, "HF_HUB_OFFLINE": "1"}
subprocess.run([sys.executable, os.path.join(COOP, "export_cpp.py"), OUT], check=True, env=env)
subprocess.run([sys.executable, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_tests.py"), OUT], check=True, env=env)
subprocess.run([sys.executable, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_world_tests.py"), OUT], check=True, env=env)
