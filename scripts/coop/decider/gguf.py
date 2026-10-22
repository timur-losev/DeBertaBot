"""The merged decider (run.py merge) as GGUF for llama.cpp b11429: bf16 (the runtime's own reference), then Q8_0 and
Q4_K_M from it (--no-mtp: decider has no weights for the multi-token-prediction layer its config declares). Derived weights: kept under stt/models_out/decider (git-ignored), never committed or uploaded.

    python gguf.py [--seed 0 --fold 0]
"""
import argparse, os, subprocess, sys
import common as C

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--fold", type=int, default=0)
a = ap.parse_args()
tag = f"s{a.seed}all" if a.fold < 0 else f"s{a.seed}f{a.fold}"
LL = os.path.join(C.STT, "models", "llama.cpp")
SRC = os.path.join(LL, "src", "llama.cpp-b11429")
merged = os.path.join(C.OUT, f"merged_{tag}")
base = os.path.join(C.OUT, f"decider-lora_{tag}")
env = dict(os.environ, PYTHONPATH=os.pathsep.join([SRC, os.path.join(SRC, "gguf-py")]))
if not os.path.exists(base + "-bf16.gguf"):
    subprocess.run([sys.executable, os.path.join(SRC, "convert_hf_to_gguf.py"), merged, "--outfile", base + "-bf16.gguf",
                    "--outtype", "bf16", "--no-mtp"], check=True, env=env)
for q in ("Q8_0", "Q4_K_M"):
    if not os.path.exists(f"{base}-{q}.gguf"):
        subprocess.run([os.path.join(LL, "b11429-cpu", "llama-quantize.exe"), base + "-bf16.gguf", f"{base}-{q}.gguf", q], check=True)
for f in sorted(os.listdir(C.OUT)):
    if f.endswith(".gguf"):
        print(f"{f}: {os.path.getsize(os.path.join(C.OUT, f)) / 2**30:.2f} GB")
