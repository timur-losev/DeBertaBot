"""
Checks the exported model in ONNX Runtime against the PyTorch golden probabilities and measures it on
CPU -- before any C++ exists, so a C++ mismatch can only be the port.

  model.onnx must reproduce golden.jsonl (same argmax, probabilities within ~1e-4)

The engine runs this fp32 model. Plain dynamic int8 quantization (quantize_dynamic, QInt8) broke it
(85/592 same argmax), so none is shipped.

    python check_onnx.py [BOT_DIR]       # jev environment, onnxruntime (CPU)
"""
import io, json, os, statistics, sys, time

import numpy as np
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.normpath(os.path.join(sys.argv[1], "cpp") if len(sys.argv) > 1 else
                     os.path.join(HERE, "..", "..", "models", "coop-deberta-v3-ens3-v2", "cpp"))


def session(path, threads=4):
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])


def run(sess, ids):
    x = np.array([ids], dtype=np.int64)
    logits = sess.run(["logits"], {"input_ids": x, "attention_mask": np.ones_like(x)})[0][0]
    e = np.exp(logits - logits.max())
    return e / e.sum()


def main():
    golden = [json.loads(l) for l in io.open(os.path.join(D, "golden.jsonl"), encoding="utf-8")]
    files = json.load(io.open(os.path.join(D, "intent_config.json"), encoding="utf-8")).get("members", ["model.onnx"])
    sessions = [session(os.path.join(D, f)) for f in files]
    diffs, agree, ms = [], 0, []
    for g in golden:
        t0 = time.perf_counter()
        p = np.mean([run(s, g["ids"]) for s in sessions], axis=0)   # an ensemble averages its members
        ms.append((time.perf_counter() - t0) * 1000)
        ref = np.array(g["probs"])
        diffs.append(float(np.abs(p - ref).max()))
        agree += int(p.argmax() == ref.argmax())
    res = {"agree": agree, "lines": len(golden), "max_diff": max(diffs), "median_ms": statistics.median(ms),
           "size_mb": sum(os.path.getsize(os.path.join(D, f)) for f in files) / 2**20, "members": files}
    print(f"fp32, {len(files)} model(s): same argmax as PyTorch on {agree}/{len(golden)} lines, max |dp| "
          f"{max(diffs):.5f}, median {statistics.median(ms):.1f} ms/line on CPU (4 threads, members one after "
          f"another), {res['size_mb']:.0f} MB")
    json.dump(res, io.open(os.path.join(D, "onnx_check.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
