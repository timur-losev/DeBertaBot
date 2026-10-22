# decider-2b as the co-op bot's intent reader: a study (2026-10-21)

The owner asked: "Используя decider 2b, нужно его дообучить до наших датасетов, через лора, наверное, и вообще, если
можно, этот decider использовать квантизированный. И тогда сравнить precision и recall."

**Result, in short:**
- With LoRA, decider-2b reads the bot's orders as well as **one** DeBERTa-v3-base, but slightly worse than the
  three-model ensemble the bot ships.
- On the game's CPU it is 3.5 to 4 times slower, at about 135-150 ms per line against 40 ms.
- Q8_0 loses nothing against bf16, and Q4_K_M loses about 1 point.
- **Averaged with the ensemble, it cuts wrong orders by about a third** at the same recall. This comes from one fold
  without tuning, so it needs confirming before anything is built on it.

## The model

`Mapika/decider-2b` (v10) is Qwen3.5-2B-Base fine-tuned to answer typed questions in one forward pass. It reads its own
LM head at an `Answer: (` slot, restricted to the option-label tokens. Ollaya ships it (`docs/families/decider.md` in
the ollaya repo). The weights are the author's, pinned at commit `9839cc9d`, and live in the git-ignored
`stt/models/hf`.

**The prompt.** It uses upstream's own tokenizer and its schema-first layout: decider v10 was trained on it
(`schema_first_trained`).

```
Question: A player in a co-op shooter gives a voice order to their AI teammate ... Which order did the player give?
Options:
(A) follow me: follow me, stay with me, on me          <- 57 options, the intents' labels and descriptions
...                                                      (intents_v60.json), in a fixed order
(BE) not an order: a callout, chatter, a question, or an order taken back
                                                        <- up to here: the prefix, 1,052 tokens, the same for every line
Context:
should this wall                                        <- the line as the bot gets it
Answer: (                                               <- the slot: logits of the 57 label tokens
```

The prefix is computed once: the attention KV and the delta-net states. After that, each line costs only its own
10 to 25 tokens.

## What was compared

All readers ran on the same held-out lines: the split of build_v61.py's seed 0, fold 0. That is 2,186 lines:
- 96 of the owner's own heard lines;
- 368 typed lines;
- 1,722 heard lines: the same lines spoken by seven voice sets, among them unseen voices (VCTK pool B) and the
  Russian voices.

The readers:

| Reader | What it is |
|---|---|
| DeBERTa ensemble | bot v61 as shipped: three DeBERTa-v3-base models, each out of fold |
| DeBERTa seed 0 | one DeBERTa model trained on exactly this split |
| decider zero-shot | the published model, temperature 1.18 |
| decider LoRA bf16 | the published model plus a LoRA trained on this split's training rows (11,589 rows, the same as DeBERTa's) |
| decider Q8_0 / Q4_K_M / bf16 GGUF | the LoRA merged into the weights, run on llama.cpp b11429 on the CPU, as the game would run it |

**LoRA settings** ([run.py](run.py)):
- r 16 and alpha 32 on every linear layer: attention, delta-net and MLP. That is 16.8 M parameters, 0.9% of the model.
- Cross-entropy over the 57 label logits; AdamW at lr 2e-4 with cosine decay.
- 3 epochs at batch 32.
- **The prefix runs without gradient**, with the current LoRA weights. Only the line's own tokens carry the gradient.
  With the prefix's gradient, a step needed 11 GB at batch 4 and 284 ms per line; without it, 13 GB at batch 32 and
  18 ms per line ([memprobe.py](memprobe.py)).
- Training took 11 minutes on the RTX 4090.

**Metrics** ([compare.py](compare.py)):
- accuracy: the top intent is the labelled one;
- macro precision, recall and F1 per intent;
- **acting precision and recall under the bot's own rule** (family gate, threshold 0.66):
  - precision = orders carried out right / orders carried out;
  - recall = orders carried out right / lines that are orders;
  - wrong orders = orders carried out wrong / all lines;
- the best recall at acting precision of at least 97% or 99%, with the threshold swept on these same lines (a
  comparison, not a deployable setting).

## Results

The full tables are in [results/compare_s0f0.md](results/compare_s0f0.md). Below: accuracy, then acting precision,
acting recall and wrong orders at the bot's threshold.

**The owner's lines (96):**

| Reader | acc. | P | R | wrong |
|---|---|---|---|---|
| DeBERTa ensemble (shipped) | 92.7 | 95.6 | 90.5 | 4.2 |
| DeBERTa, one model | 91.7 | 93.5 | 91.6 | 6.2 |
| decider zero-shot | 47.9 | 73.0 | 28.4 | 10.4 |
| decider LoRA, bf16 (GPU) | 91.7 | 92.3 | 88.4 | 7.3 |
| decider LoRA, Q8_0 (CPU) | 90.6 | 92.3 | 88.4 | 7.3 |
| decider LoRA, Q4_K_M (CPU) | 90.6 | 94.4 | 88.4 | 5.2 |
| ensemble + decider, averaged | 93.8 | 96.5 | 87.4 | 3.1 |

**All heard lines (1,722):**

| Reader | acc. | P | R | wrong |
|---|---|---|---|---|
| DeBERTa ensemble (shipped) | 85.6 | 92.4 | 82.4 | 6.3 |
| DeBERTa, one model | 82.7 | 85.3 | 82.6 | 13.2 |
| decider zero-shot | 39.3 | 75.9 | 23.7 | 7.0 |
| decider LoRA, bf16 (GPU) | 84.0 | 89.1 | 84.1 | 9.5 |
| decider LoRA, Q8_0 (CPU) | 83.8 | 89.2 | 83.9 | 9.4 |
| decider LoRA, Q4_K_M (CPU) | 82.8 | 88.5 | 82.7 | 9.9 |
| ensemble + decider, averaged | 86.9 | 95.1 | 82.4 | 3.9 |

**Typed lines (368):**
- ensemble: 94.6 / 96.6 / 91.8 / 3.0;
- decider LoRA bf16: 93.8 / 94.6 / 93.5 / 4.9;
- averaged: 95.4 / 97.8 / 93.5 / 1.9.

**What this shows:**
- **Zero-shot is not usable.** It gets about 40 to 48% of the 57 intents.
- **With LoRA, decider equals one DeBERTa model and stays below the ensemble.** Its accuracy against the ensemble:
  - -1.6 points on heard lines (bootstrap 95% interval -3.4 to -0.1);
  - -1.0 on the owner's lines (-6.2 to +4.2);
  - -0.8 on typed lines (-3.5 to +1.9).
- **Its confidence is less useful at the top.** At the bot's threshold it acts more often, with more wrong orders
  (9.5% against 6.3% on heard lines). At 99% acting precision its recall collapses: 12.7% against 41.1% on heard
  lines. It is very sure of some of its mistakes. A threshold or temperature fitted for decider would trade some of its
  recall for precision.
- **Quantization.**
  - The llama.cpp bf16 GGUF matches PyTorch on the GPU: 83.9 against 84.0. On the check lines, Q8_0 against PyTorch
    differs by at most 0.38 on logits up to 26, and gives the same top intent on 19 of 20 lines.
  - Q8_0 loses 0.1 to 0.4 points.
  - Q4_K_M loses about 1 point on heard lines and 3 on unseen voices.
- **The two families together.** Averaging the ensemble's probabilities with decider's (equal weights, no tuning):
  - accuracy rises: heard +1.3, owner +1.1, typed +0.8;
  - wrong orders fall by about a third: heard 6.3 -> 3.9%, owner 4.2 -> 3.1%, typed 3.0 -> 1.9%;
  - recall stays about the same.

  They err on different lines. **This is one fold, and the owner's subset is only 96 lines:** confirm on all five folds
  before building on it.

## Speed and memory (i9-10900K, the game's minimum CPU)

Per line, mean (DeBERTa: median):

| Reader | 4 threads | 8 threads | 10 threads | 20 threads | Memory |
|---|---|---|---|---|---|
| DeBERTa ensemble (3 models in parallel) | 39.5 ms with 1 thread per model, 34.5 ms with 4 | | | | 2.3 GB |
| decider Q4_K_M (llama.cpp) | 218 ms | 146 ms | 141 ms | 135 ms | 1.2 GB file |
| decider Q8_0 (llama.cpp) | 225 ms | 156 ms | 160 ms | 134 ms | 1.9 GB file |

- The prefix is computed once, at load: **about 7 s on the CPU alone** (8 threads).
  - The first version of `decider_eval` gave llama.cpp the GPU in its device list. llama.cpp then sent the prefix's
    large products to the GPU, even with 0 layers on it, and showed 1.2 to 1.8 s.
  - The same mix made its check of cached against whole lines differ by up to 0.19.
  - With no device on the CPU, as `llama_rewriter.cpp` does, the check is exact: 0.00000 on 5 lines.
  - The per-line times above barely changed: 147 ms at 8 threads against 150 to 156 ms. The table's accuracy numbers
    come from the first runs; their prefix states were computed partly on the GPU.
- **decider's time per line does not depend on the quantization.** bf16, Q8_0 and Q4_K_M all take about 175 ms at
  8 threads in the full runs. So it is not the weights. The time goes to fixed work per line:
  - llama.cpp computes the logits of the whole 248k-token vocabulary for the slot, and 57 are needed;
  - it copies the delta-net state of the prefix;
  - it builds the graph.

  This could be cut, but it is engineering, not part of this study.

## Files

- [common.py](common.py): the prompt, the split, the cached prefix and the gradient patch.
- [check.py](check.py): cached against whole rows; gradients.
- [memprobe.py](memprobe.py): memory and time per batch size.
- [run.py](run.py): `zeroshot`, `train`, `merge`.
- [gguf.py](gguf.py): bf16, Q8_0 and Q4_K_M with `--no-mtp`. decider's config declares a multi-token-prediction layer
  that its checkpoint has no weights for.
- [prep_gguf.py](prep_gguf.py) and [cpp/decider_eval.cpp](cpp/decider_eval.cpp): the GGUF on llama.cpp. The prefix is
  decoded once; per line, the sequence is copied, the suffix decoded and the 57 logits read. `--check K` compares a
  line against a whole decode.
- [compare.py](compare.py): every reader on the same lines.
- [results/](results): logits per line, the comparison, the training log.

Derived weights stay under `stt/models_out/decider`, which is git-ignored: the LoRA adapter, the merged model and the
GGUF files. They are never committed or uploaded.

## In the game: an optional second reader (2026-10-21)

The owner: "а можно десайдер уже подключить, как сайд опцию в Лиру?"

- **The game's model** is trained on all of v61's rows: 14,502 rows, lines, seeds and the owner's lines with their
  transcripts, like DeBERTa's final models. The command is `run.py train --fold -1`, then `merge --fold -1` and
  `gguf.py --fold -1`. Training took 15 min.
- **The folder** comes from [export_game.py](export_game.py): `stt/models_out/decider/game_s0all`. It holds the Q8_0
  GGUF, `decider.json` (the labels, the prompt's token ids, the label ids) and `decider_tests.json` (300 lines).
- **In the brain:** `coop_cli --decider DIR [--decider-mode avg|only] [--decider-threads N]`
  ([decider.h](../../../cpp/coop_intent/include/coop_intent/decider.h), `src/llama_decider.cpp`).
  - It runs on its own thread while the ensemble reads the line. `avg` averages the probabilities; `only` uses the
    decider's.
  - Without the option nothing changes: the 8 engine checks pass as before.
  - A decider that does not load, or a line it cannot read, leaves the ensemble alone.
  - `--decider-tests` on the 300 lines: the line's tokens equal upstream's tokenizer on 300/300, and the top label and
    the probabilities equal `decider_eval`'s on 300/300 (max |dp| 0.0000), at 146 ms per line.
- **In the game:**
  - The setting is `DeciderMode` (0 off, 1 averaged, 2 alone; default 0). `ov.CoopBot.Brain.Decider 0|1|2|-1`
    overrides it and restarts the brain.
  - The folder goes in with `deploy_brain.ps1 -Decider <folder>`, under `Binaries/CoopBrainV6/decider`.
  - `Tests/E2E/decider.txt` passes on a dedicated server and client:
    - off: ready in 5.9 s, 42 ms a line;
    - averaged: ready in 15.8 s, 143 to 181 ms a line;
    - alone: ready in 15.0 s, 179 to 197 ms a line;
    - off again: 42 ms.

    Every line was carried out right in every mode: "should this wall" fires, "kiss him" attacks, "roll there" moves.

## Open

- **Five folds:** the same protocol as DeBERTa's out-of-fold numbers. About 1 h of GPU and 1 h of CPU.
- **A threshold or temperature for decider, fitted out of fold.** The ensemble's 0.66 does not suit it.
- **If the averaging holds over five folds:** decider beside the ensemble in the game. coop_cli already links
  llama.cpp. It costs about 1.9 GB and about 150 ms per line in parallel with DeBERTa, and the per-line overhead
  should be cut first.
- **decider-0.8b:** faster and smaller, not tried.
