"""A provisional bot_config.json for bot v54, for trying the three final models before the out-of-fold runs are done:
bot v53's gate and threshold (family, 0.66), NOT fitted on v54. score_v54.py writes the real one and replaces this.

    python quick_config_v54.py            # refuses to replace a config that score_v54.py wrote, unless --force
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v54"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v54"))
path = os.path.join(OUT_DIR, "bot_config.json")
assert all(os.path.exists(os.path.join(OUT_DIR, f"seed{s}", "model.safetensors")) for s in (0, 1, 2)), "the three final models first"
if os.path.exists(path) and "--force" not in sys.argv:
    old = json.load(io.open(path, encoding="utf-8"))
    if not str(old.get("threshold_from", "")).startswith("PROVISIONAL"):
        sys.exit(f"{path} was written by score_v54.py: kept (--force replaces it)")
n_lines, n_seeds = len([i for i in V.load_items() if i["maj"]]), len(V.seed_items())
cfg = {"labels": V.INTENTS, "threshold": 0.66, "gate": "family", "families": V.FAMILY,
       "phrases": {k: v["label"] for k, v in V.I.items()}, "base_model": "microsoft/deberta-v3-base",
       "members": ["seed0", "seed1", "seed2"],
       "recipe": {"max_len": 64, "batch": 16, "epochs": 12, "weight_decay": 0.01, "warmup": 0.1, "lr": 5e-05, "dtype": "float32", "seeds": [0, 1, 2]},
       "trained_on": f"{n_lines} lines from 3 AI-written authors + {n_seeds} seed commands (seed_commands_v54.json), typed, plus what Parakeet TDT 0.6B v2 "
                     "heard when the r6 and cs lines and the seed commands were read by synthesized voices (Windows, Kokoro, VCTK pool A)",
       "threshold_from": "PROVISIONAL: the gate and the threshold of bot v53, not fitted on v54 -- run the out-of-fold runs and score_v54.py",
       "input": "speech-to-text output lowercased, final .!? stripped, inner punctuation kept"}
json.dump(cfg, io.open(path, "w", encoding="utf-8"), indent=1)
print(f"provisional bot_config.json written (family gate, 0.66 -- bot v53's): {OUT_DIR}")
