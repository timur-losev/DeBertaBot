# DeBertaBot

A co-op game bot that turns a player's voice order into one of 24 intents plus a place on the map:
three fine-tuned DeBERTa-v3-base models, a rule matcher for the map's named places, and a C++17 engine
checked line by line against the Python bot. Start with [HANDOFF.md](HANDOFF.md) (the current state, in
Russian), [COOP-BOT.md](COOP-BOT.md) (the study) and [cpp/coop_intent/README.md](cpp/coop_intent/README.md).

This repository is the co-op bot part of a larger research folder, `project_synth`; the rest of this file
is that folder's README. The documents FINDINGS.md, MODELS.md, GAME-BOT.md and NPC-DECISIONS.md and the
scripts outside `scripts/coop` that it lists are not in this repository. Model weights are not in git
either (HANDOFF.md, section 1).

---

# project_synth

Research notes and measurement harnesses from one session of evaluating ollaya: how it compares with
a Qwen-based constrained-decoding engine, which model in the catalogue suits which job, and whether a
`laya` model can serve as the natural-language front door for a game bot.

Nothing here is part of the ollaya build. No Rust, no `convert/` dependency, no effect on
`cargo test`, `cargo fmt` or `cargo clippy`. It is an untracked folder of documents and Python
scripts; add it to git or delete it as you see fit.

## Documents

| | |
|---|---|
| [FINDINGS.md](FINDINGS.md) | Every measured number, with the method and the caveats. Includes a table of the claims that were corrected during the session, so earlier figures are not trusted by accident. |
| [MODELS.md](MODELS.md) | Which of the 13 published models to use for what, grouped by how each reads its answer out, plus the traps a newcomer hits. |
| [GAME-BOT.md](GAME-BOT.md) | The game-bot design: the recommendation, the constraints, the test set, and the two designs that were built, measured and rejected. |
| [NPC-DECISIONS.md](NPC-DECISIONS.md) | Can a model make an enemy soldier's tactical decision from game factors? 325 states, three independent judges, 15 factor forms: no (best model 38% vs 58-61% for a hand-written utility AI). Where it helps: reading the overheard player line, 80% on blind lines with keywords + laya:en + a negation guard. |
| [COOP-BOT.md](COOP-BOT.md) | Co-op bot voice orders to one enum (Siege/CS style), 363 blind lines, 7 models, reviewed: decision:eos is the only model that works zero-shot (62% near-correct at 2.2% wrong-family actions); a char n-gram classifier on playtest lines works only as a second key (0.3% wrong family); timing and "the other one" are regex. Fine-tuned DeBERTa-v3-base and a fine-tuned laya (rebuilt in PyTorch, menu still flexible) both reach ~88-90% near-correct. v2 adds TAKE_COVER and OPEN: an ensemble of three fine-tuned DeBERTa-v3-base reaches 90.5% near-correct at 1.9% wrong family; deberta-v3-large collapsed on this data. v3 adds map places: a dictionary matcher gives the planner the target (88% exact on 150 blind lines before any tuning, 94% on the held-out author after), and re-training lifts intent accuracy on place lines from 83% to 91%. |
| [DEBERTA-BOT.md](DEBERTA-BOT.md) | The co-op bot on fine-tuned DeBERTa-v3-base, on CPU (~70 ms): how to run it and a step-by-step walkthrough of how it was made, evaluated and calibrated, with the traps we hit (in Russian). |
| [cpp/coop_intent/README.md](cpp/coop_intent/README.md) | The co-op bot as a C++17 engine for UE5: own tokenizer (no ICU), ONNX Runtime backend with ensembles, the bot logic. The shipped v2 bot (24 intents incl. TAKE_COVER and OPEN, three DeBERTa-v3-base models) is identical to the Python bot on 762 golden lines (probabilities within 3.3e-6), 8931 tokenizer/regex lines, 2338 gate decisions, every branch of the bot's logic and a 66-line conversation; ~60 ms per line on 3 CPU cores, 2.3 GB. |

## Headline results

- `laya:multilingual` answers the same 28-field structured-decision workload **3.5–5.4× faster** than
  the Qwen parallel engine, at **73.4 % against 74.7 %** accuracy on identical ground truth, using
  **1.5 GB of VRAM against 4.3 GB**. `laya:en` is 1.5–2.4× faster but less accurate than either.
- The Qwen engine wins in exactly two places: schemas beyond roughly 57–112 fields, where its flat
  latency overtakes laya's linear growth, and high option counts, where both laya models refuse with
  `422 TOO_MANY_OPTIONS`.
- On CPU `laya:multilingual` costs **zero VRAM**, 1.7 GB of RAM and 170 ms for one question — but
  **165 ms for every additional question**, where on GPU extra questions are nearly free. Schemas
  designed against GPU numbers must be re-costed.
- For the game bot (English only): a single flat `choice` on **`laya:en`** with the option keys written
  as the phrase a player would say reaches **38/46 = 83 %**, 389 ms on CPU, zero VRAM. The label style
  alone is worth +9 to +11 points and costs nothing; the descriptions everyone reaches for first are
  worth +2. The same change on the Qwen engine is worth **+34** (46 % → 80 %). None of it transfers:
  on `laya:multilingual` phrase labels make things worse.
- Every elaboration tried did worse than one flat question: a two-model cascade scored **36 %** because
  its gate rejected 70 % of real commands, and `nli` as a veto behind `laya` scored **57 %** or
  **50 %**. `nli`'s rejection strength failed to transfer to three different roles. The transferable
  lesson: a number measured in one question shape, or on one model, predicts nothing about another.
- Accuracy hides what matters in a shooter. Split by consequence, the Qwen counterpart makes **zero**
  dangerous errors on the same set — every miss is a refusal — while the laya bot makes three.

## Which Python

**Any Python 3.8+.** Every script here imports only the standard library — `json`, `io`, `os`, `re`,
`sys`, `time`, `urllib`, `statistics`, `collections`, `subprocess`, `concurrent.futures`. All the work
happens over HTTP against the ollaya daemon, so there is nothing to install and no virtual environment
to activate. On this machine `python` in PATH resolves to `C:\Users\void\anaconda3\python.exe` (3.11.7)
and that is enough.

The conda environment `D:\Program\anaconda3\envs\jev` (3.11.16) is needed for exactly one thing: it is
where `torch 2.14.0+cu130` lives, so it runs the **Qwen server** that `clean_qwen.py` and
`burst_qwen.py` measure. Those two scripts only speak HTTP to it and do not need torch themselves.

## Running the scripts

They all talk to a local daemon over HTTP and assume the models are pulled.

```powershell
$env:OLLAYA_MODELS = 'G:\Proj\ollaya\install\models'
$env:OLLAYA_DEVICE = 'cpu'          # omit for CUDA
G:\Proj\ollaya\install\bin\ollaya.exe serve

G:\Proj\ollaya\install\bin\ollaya.exe pull laya:multilingual
G:\Proj\ollaya\install\bin\ollaya.exe pull nli          # only for the head-to-head

cd scripts
python .\chat.py laya:multilingual off      # talk to the bot
python .\run_testset.py laya:multilingual   # score it on the 60 cases
```

Paths are absolute: each script resolves its data files from its own directory, so the folder can be
moved, but the scripts that also read the Qwen presets expect that project at
`G:\Proj\Qwen-2.5-1B-RLCD`. Check `ollaya ps` before timing anything — it prints the device and
precision actually in use, and a failed CUDA warm-up silently demotes `auto` to CPU.

## Scripts

Comparison against the Qwen engine:

| | |
|---|---|
| `compare_ollaya.py` | Converts a Qwen preset into an ollaya question set and scores answers with the same rules as the Qwen repo's `score_against_expected`. Imported by several others. |
| `clean.py` / `clean_qwen.py` | Each engine measured alone on a quiet machine: VRAM, latency, accuracy, scaling. |
| `ab3.py` | Three-way interleaved wall-clock A/B over HTTP, which is how the corrected latency ratio was obtained. |
| `scaling2.py` | Latency versus number of questions, 15 repeats, minimum as the uncontended estimate. |
| `burst.py` / `burst_qwen.py` | How VRAM grows with concurrent requests on each engine. |
| `vram_growth.py` | Whether the ONNX Runtime arena grows per request shape. It does not. |
| `style.py` | How much the `noul` phrasing moves accuracy. |
| `cpu_test.py` | CPU mode: accuracy, RAM, latency versus question count. |

Game bot:

| | |
|---|---|
| `chat.py` | **Interactive REPL: talk to the laya bot from a terminal.** Implements the recommended configuration and prints the winning order, its probability and the latency after every reply. `/v` shows the full distribution, `/model` switches model, `/t` moves the threshold, `/veto` toggles the nli second opinion. |
| `qwen_bot.py` | **The same bot on the Qwen engine**, for side-by-side comparison. `--score` runs the test set under both label encodings; `--phrase` / `/enc` switch them live. Needs the Qwen server on :8000. |
| `commands.json` | The command vocabulary: intent name, the label the model is shown, and the description. Single source for the bot and every harness. Its header records what each field is worth. |
| `label_ablation.py` | The 2×2 that found the label style: label as code or phrase × description present or absent, per model. Run it before changing model. |
| `testset.json` | The 60-case set: 15 commands plus `NONE`, STT-style input, confusable pairs, nine kinds of rejection. |
| `run_testset.py` | The flat head-to-head. This is where 62 % comes from. |
| `bot_matrix.py` | 12 prompt configurations: two models × three description styles × two state wrappers. Accuracy ranged 2/11 to 10/11. |
| `cascade.py` | The `nli`-gate + `laya`-pick cascade, with umbrella collapsing and code-side negation. Measured at 36 %. Kept as a closed hypothesis, with the reasoning errors documented in its docstring. |
| `measure_reinforce.py` | The inverse of the cascade: `laya` picks, `nli` may veto with NONE. Two veto shapes against two baselines. Also a closed hypothesis — 62 % plain, 57 % with the full veto, 50 % with the cheap one. |
| `bot_questions.json` | The first schema tried, whose `noul` gate was discarded. Historic. |
| `testset_results.json`, `cascade_results.json`, `ollaya_results.json` | Per-case output of the three runs. |

## reference/

| | |
|---|---|
| `fams.json` | All 11 families characterised from `docs/families/` and the registry manifests: architecture, context, option ceilings, readout mechanism, calibration, licence, gotchas, with file-and-line citations. |
| `workflow-model-catalogue.json` | Raw output of the run that produced `fams.json` and the selection guide. |
| `workflow-qwen-mapping.json` | Raw output of the run that established how the Qwen presets map onto ollaya's question schema, including the live probing of the option-count ceilings. |

## What is not here

The other half of the comparison lives in `G:\Proj\Qwen-2.5-1B-RLCD` as an **uncommitted working
tree**: a pinned CUDA requirements file, a `REQUIRE_CUDA` startup guard, a fixed baseline JSON parser,
exact full-sequence rescoring for fields whose choices share a first token, hand-labelled ground truth
in all four presets with the destroyed monetary figures reconstructed, accuracy reporting with
`--repeat`, and reworked UI badges. That work is described in the session it came from, not here.
One defect was found there and left unfixed: `_gpu_lock` is declared at `core/engine_torch.py:29` and
never used, so the torch backend does not serialise GPU access the way the MLX backend does.

No STT component was measured. ollaya does nothing with speech — there is not a line about it in the
repository — and the end-to-end budget for a voice-driven bot is unknown until that is benchmarked.
