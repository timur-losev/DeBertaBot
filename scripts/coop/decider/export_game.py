"""The decider for the game's brain (coop_cli --decider DIR, cpp/coop_intent/include/coop_intent/decider.h): a folder with
the GGUF and decider.json (the 57 labels in the bot's order, the prompt's token ids from upstream's own tokenizer, the
label token ids, the temperature), plus decider_tests.json for coop_cli --decider-tests (per line: the text, upstream's
tokens of the line alone and decider_eval's label logits on the same GGUF, pure CPU).

    python export_game.py [--tag s0all] [--quant Q8_0] [--test-lines 300]   -> OUT/game_<tag>/
The folder is derived weights: deploy_brain.ps1 -Decider copies it next to the brain; it is never committed or uploaded.
"""
import argparse, io, json, os, random, shutil, subprocess
import common as C

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="s0all")
ap.add_argument("--quant", default="Q8_0")
ap.add_argument("--test-lines", type=int, default=300)
ap.add_argument("--threads", type=int, default=8)
a = ap.parse_args()
tok = C.tokenizer()
pre, lab, suffix = C.prompt_parts(tok)
labels, _ = C.intents()
ctx_ids = tok.encode("\n\nContext:\n", add_special_tokens=False)
ans_ids = tok.encode("\n\nAnswer: (", add_special_tokens=False)
assert suffix("should this wall") == ctx_ids + tok.encode("should this wall", add_special_tokens=False) + ans_ids
out = os.path.join(C.OUT, f"game_{a.tag}")
os.makedirs(out, exist_ok=True)
gguf = os.path.join(C.OUT, f"decider-lora_{a.tag}-{a.quant}.gguf")
shutil.copyfile(gguf, os.path.join(out, "decider.gguf"))
cfg = {"labels": labels, "model": "decider.gguf", "prefix": pre, "label_ids": lab, "context_ids": ctx_ids, "answer_ids": ans_ids,
       "max_line_tokens": 1536, "temperature": 1.0,
       "source": f"Mapika/decider-2b@9839cc9d + the bot's LoRA ({a.tag}: run.py train --fold -1, all of v61's rows), {a.quant}",
       "question": C.QUESTION}
json.dump(cfg, io.open(os.path.join(out, "decider.json"), "w", encoding="utf-8"), ensure_ascii=False)

# the test lines: a fixed sample of the study's held-out lines (fold 0), every kind of line
_, test = C.split(0, 0)
random.Random(7).shuffle(test)
test = test[:a.test_lines]
rows_path = os.path.join(out, "decider_eval_rows.json")
json.dump({"prefix": pre, "labels": lab, "rows": [{"id": r["id"], "suffix": suffix(r["text"])} for r in test]},
          io.open(rows_path, "w", encoding="utf-8"))
res = os.path.join(out, "decider_eval_out.jsonl")
exe = os.path.join(C.HERE, "cpp", "build", "Release", "decider_eval.exe")
subprocess.run([exe, os.path.join(out, "decider.gguf"), rows_path, res, "--threads", str(a.threads), "--check", "5"], check=True)
got = {r["id"]: r for r in (json.loads(l) for l in io.open(res, encoding="utf-8").read().splitlines()[1:])}
json.dump({"rows": [{"id": r["id"], "text": r["text"], "line_ids": tok.encode(r["text"], add_special_tokens=False),
                     "logits": got[r["id"]]["logits"]} for r in test]},
          io.open(os.path.join(out, "decider_tests.json"), "w", encoding="utf-8"), ensure_ascii=False)
os.remove(rows_path)
print(f"{out}: decider.gguf ({os.path.getsize(os.path.join(out, 'decider.gguf')) / 2**30:.2f} GB), decider.json, "
      f"decider_tests.json ({len(test)} lines)")
