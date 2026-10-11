"""A distilled student as a bot the C++ engine runs (HANDOFF.md, "brains"): bot_config.json from the student's own
out-of-fold run (gate and threshold fitted as score_v54.py fits them), export_cpp.py and gen_tests.py for its cpp/
directory, and the int8 question: dynamic quantization of the ONNX model with the argmax and probability drift measured
on the golden lines (the v1 bot broke under it -- cpp/coop_intent/README.md -- so every variant is checked, none assumed).

    python student_bot_v54.py SIZE TAG [SEED]     e.g. python student_bot_v54.py xsmall kd 0
Writes models/coop-deberta-v3-<SIZE>-<TAG>-v54/{bot_config.json, cpp/, cpp_int8/} and prints the drift per variant.
"""
import io, json, os, shutil, subprocess, sys
os.environ["COOP_TAG"] = "v54"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, COOP)
import numpy as np
import coop_v2 as V

size, tag = sys.argv[1], sys.argv[2]
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
PY = sys.executable
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", f"coop-deberta-v3-{size}-{tag}-v54"))
assert os.path.exists(os.path.join(OUT, f"seed{seed}", "model.safetensors")), f"no final student in {OUT}/seed{seed} (distill_v54.py final)"
items = {i["id"]: i for i in V.load_items() if i["maj"]}
spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731

# ---- gate and threshold from the student's out-of-fold probabilities
student = json.load(io.open(os.path.join(HERE, f"kd54_student_{size}_{tag}_s{seed}.json"), encoding="utf-8"))
probs = student["probs"]


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
_, gate, thr_fit = best
# the students are over-confident (their fitted thresholds sit at 0.96-0.98) and gen_tests.py's decision steps are
# built on fixed 0.30 / 0.90 probabilities, so they need a threshold in 0.35..0.89: the bot gets 0.88 and the config
# says what the fit gave. The cost on VCTK B (kd54_student_*_s0.json, family gate): xsmall 54.8 at 0.88 vs 57.0 at
# 0.96; small 59.4 at 0.88 vs 62.8 at 0.98.
thr = min(thr_fit, 0.88)
trained = json.load(io.open(os.path.join(OUT, f"seed{seed}", "trained_on.json"), encoding="utf-8"))
cfg = {"labels": V.INTENTS, "threshold": thr, "gate": gate, "families": V.FAMILY,
       "phrases": {k: v["label"] for k, v in V.I.items()}, "base_model": trained["student"], "members": [f"seed{seed}"],
       "recipe": {"max_len": 64, "batch": 16, "epochs": trained["epochs"], "weight_decay": 0.01, "warmup": 0.1, "lr": trained["lr"], "dtype": "float32",
                  "distillation": {"T": trained["T"], "alpha": trained["alpha"], "teachers": trained["teachers"]}},
       "trained_on": f"the v54 training set ({trained['training_lines']} lines: typed lines, seed_commands_v54.json, Parakeet transcripts), "
                     f"distilled from the three members of coop-deberta-v3-ens3-v54 (soft targets, T={trained['T']}, alpha={trained['alpha']})",
       "threshold_from": "5-fold out-of-fold predictions of the same student recipe (one seed) on the r6 and cs lines as Parakeet heard them "
                         f"from the training voices; criterion near - 2*wrong-family gave {thr_fit:.2f}; clamped to {thr:.2f} because "
                         "gen_tests.py's decision steps need a threshold in 0.35..0.89 (the student is over-confident)",
       "threshold_fitted": thr_fit,
       "input": "speech-to-text output lowercased, final .!? stripped, inner punctuation kept"}
json.dump(cfg, io.open(os.path.join(OUT, "bot_config.json"), "w", encoding="utf-8"), indent=1)
print(f"{OUT}: gate {gate}, threshold {thr:.2f} (fitted {thr_fit:.2f})")

# ---- export and the test files
env = {**os.environ, "HF_HUB_OFFLINE": "1"}
subprocess.run([PY, os.path.join(COOP, "export_cpp.py"), OUT], check=True, env=env)
subprocess.run([PY, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_tests.py"), OUT], check=True, env=env)
subprocess.run([PY, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_world_tests.py"), OUT], check=True, env=env)

# ---- int8: dynamic quantization, checked on the golden lines
import onnxruntime as ort  # noqa: E402
from onnxruntime.quantization import QuantType, quantize_dynamic  # noqa: E402

cpp = os.path.join(OUT, "cpp")
gold = [json.loads(l) for l in io.open(os.path.join(cpp, "golden.jsonl"), encoding="utf-8")]


def run_all(path):
    s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    out = []
    for g in gold:
        ids = np.array([g["ids"]], dtype=np.int64)
        logits = s.run(None, {"input_ids": ids, "attention_mask": np.ones_like(ids)})[0][0].astype(np.float64)
        e = np.exp(logits - logits.max())
        out.append(e / e.sum())
    return np.stack(out)


ref = np.stack([np.array(g["probs"]) for g in gold])
fp32 = run_all(os.path.join(cpp, "model.onnx"))
print(f"fp32 ONNX vs PyTorch golden: same argmax {int((fp32.argmax(1) == ref.argmax(1)).sum())}/{len(gold)}, max |dp| {np.abs(fp32 - ref).max():.2e}")
variants = {
    "int8_all": dict(weight_type=QuantType.QInt8),
    "int8_per_channel": dict(weight_type=QuantType.QInt8, per_channel=True),
    "uint8_matmul_only": dict(weight_type=QuantType.QUInt8, op_types_to_quantize=["MatMul"]),
}
report = {}
for name, kw in variants.items():
    d = os.path.join(OUT, f"cpp_{name}")
    os.makedirs(d, exist_ok=True)
    for f in ("intent_config.json", "vocab.tsv", "golden.jsonl", "tokenizer_tests.jsonl", "gate_tests.jsonl", "decide_tests.jsonl",
              "location_tests.jsonl", "dialogue.jsonl", "world_tests.jsonl"):
        shutil.copy(os.path.join(cpp, f), d)
    quantize_dynamic(os.path.join(cpp, "model.onnx"), os.path.join(d, "model.onnx"), **kw)
    q = run_all(os.path.join(d, "model.onnx"))
    same = int((q.argmax(1) == ref.argmax(1)).sum())
    # the gate's pick with the bot's threshold: what matters in play
    picks_ref = [V.pick(list(r), gate, thr)[0] for r in ref]
    picks_q = [V.pick(list(r), gate, thr)[0] for r in q]
    agree = sum(a == b for a, b in zip(picks_ref, picks_q))
    report[name] = {"same_argmax": same, "same_pick": agree, "max_dp": float(np.abs(q - ref).max()), "mean_dp": float(np.abs(q - ref).mean()),
                    "bytes": os.path.getsize(os.path.join(d, "model.onnx"))}
    print(f"{name}: same argmax {same}/{len(gold)}, same gated pick {agree}/{len(gold)}, max |dp| {report[name]['max_dp']:.3f}, "
          f"mean |dp| {report[name]['mean_dp']:.4f}, {report[name]['bytes'] / 1e6:.0f} MB")
report["fp32"] = {"bytes": os.path.getsize(os.path.join(cpp, "model.onnx")), "max_dp_vs_torch": float(np.abs(fp32 - ref).max())}
json.dump(report, io.open(os.path.join(OUT, "quantization.json"), "w"), indent=1)
