"""The held-out lines as token ids for decider_eval (cpp/): the prefix, the 57 label ids and one suffix per line, all from
upstream's own tokenizer, so that the GGUF sees exactly the tokens the PyTorch model saw.

    python prep_gguf.py [--seed 0 --fold 0]   -> results/gguf_rows_s0f0.json
"""
import argparse, io, json, os
import common as C

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--fold", type=int, default=0)
a = ap.parse_args()
tok = C.tokenizer()
pre, lab, suffix = C.prompt_parts(tok)
_, test = C.split(a.seed, a.fold)
path = os.path.join(C.RES, f"gguf_rows_s{a.seed}f{a.fold}.json")
json.dump({"prefix": pre, "labels": lab, "rows": [{"id": r["id"], "suffix": suffix(r["text"])} for r in test]},
          io.open(path, "w", encoding="utf-8"))
print(f"{len(test)} rows, prefix {len(pre)} tokens -> {path}")
