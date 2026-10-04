# coop_intent: the co-op bot in C++

The fine-tuned DeBERTa co-op bot ([DEBERTA-BOT.md](../../DEBERTA-BOT.md)) as a C++17 engine. It
covers the tokenizer, the model call (one model or an ensemble), and the bot's decision logic. It is
checked line by line against the Python bot, and it is laid out so the core can move into UE5
unchanged.

The shipped bot is **v2** ([COOP-BOT.md](../../COOP-BOT.md), section "v2"):
- 24 intents, including TAKE_COVER (the bot hides; the planner picks the spot) and OPEN (open a door
  or window without going through);
- three DeBERTa-v3-base models with their probabilities averaged;
- the family gate, threshold 0.58.

The 22-intent v1 bot still runs with `--model-dir ..\..\models\coop-deberta-v3-base\cpp`.

## Layout

| file | what | into UE5 |
|---|---|---|
| `include/coop_intent/unicode.h`, `src/unicode.cpp`, `src/unicode_tables.inc` | UTF-8, NFC and the character classes, from generated tables (no ICU, no OS calls) | as is |
| `include/coop_intent/tokenizer.h`, `src/tokenizer.cpp` | the HF DebertaV2 tokenizer: added tokens, normalizer, Metaspace, Unigram/Viterbi | as is |
| `include/coop_intent/bot_brain.h`, `src/bot_brain.cpp` | `coop_bot.py` `respond()`: top or family gate, threshold, negation guard, GO_NOW/WAIT, queued order, regex slots | as is, or swap `SlotPatterns` for `FRegexPattern` |
| `include/coop_intent/intent_model.h`, `src/intent_model.cpp` | `ILogitsBackend`, `EnsembleBackend` (averages the members' probabilities, one thread each or in turn), softmax, top-k | as is |
| `src/ort_backend.cpp` | `OrtBackend`: one model in ONNX Runtime 1.30 (C++ API) | replaced by an NNE backend |
| `tools/coop_cli.cpp` | terminal chat and the checks | no |
| `tools/gen_unicode_tables.py` | writes `unicode_tables.inc` from the HF `tokenizers` library itself | no |
| `tools/gen_tests.py` | writes `tokenizer_tests.jsonl` and `dialogue.jsonl` from the Python bot | no |

`scripts/coop/export_cpp.py <bot dir>` writes the model files to `<bot dir>/cpp/`. For the shipped
bot that is `models/coop-deberta-v3-ens3-v2/cpp/`:
- `model0.onnx`, `model1.onnx`, `model2.onnx`: fp32, 705 MB each, opset 17, dynamic sequence length.
  A single-model bot has one `model.onnx`.
- `vocab.tsv`
- `intent_config.json`: labels, families, phrases, threshold, gate, member files, special ids and the
  three regexes.
- `golden.jsonl`: token ids and PyTorch probabilities per line (the members' average).

## Build and run (Windows, VS 2022 Build Tools, CMake)

```
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release

build\Release\coop_cli.exe                    # chat, like coop_bot.py: /why /t 0.6 /q
build\Release\coop_cli.exe --golden           # C++ vs PyTorch on 762 lines
build\Release\coop_cli.exe --tokenizer-tests  # C++ vs the HF tokenizer and Python re on 8931 lines
build\Release\coop_cli.exe --dialogue         # C++ vs coop_bot.Bot on a 66-line conversation
build\Release\coop_cli.exe --gate-tests       # both gates on 1169 probability rows (no model)
build\Release\coop_cli.exe --decide-tests     # every branch of the bot's decision, both gates (no model)
build\Release\coop_cli.exe --bench --threads 1
build\Release\coop_cli.exe --tokenize "hold the other angle"
```

- `--model-dir` picks another exported bot.
- `--threads` sets ONNX Runtime's intra-op threads per model.
- `--sequential` runs an ensemble's members one after another instead of one thread each.
- `--no-spin` lets idle worker threads sleep.

`third_party/` holds the ONNX Runtime release (`onnxruntime-win-x64-1.30.0`, from GitHub
releases) and `nlohmann/json.hpp` (the CLI only). The build copies `onnxruntime.dll` next to the
exe, because Windows ships an older `onnxruntime.dll` in System32.

## What was checked

On the shipped v2 ensemble; the v1 bot passes the same checks.

| check | result |
|---|---|
| token ids, 762 golden lines | 762/762 identical |
| probabilities vs PyTorch (ensemble average) | 762/762 within 1e-4, max difference 3.3e-6, argmax 762/762 |
| normalizer / token ids, 8931 lines | 8931 / 8931 identical |
| regex slots, 8927 lines (+ 4 past std::regex's limit, see below) | 8927/8927 identical |
| intent, confidence, action and queued order, 66-line conversation through the models | 66/66 identical |
| both gates on 1169 probability rows: the golden lines, exact ties, the top label outside the top-mass family, random rows | 2338/2338 identical |
| every branch of the decision (negated, say again, ignore, execute, go, wait, queued, act, "other", the threshold boundary), both gates, constructed probabilities | 38/38 identical |

The 8931 lines are the golden lines plus lines generated to break a port:
- every kind of whitespace;
- composed, decomposed and reordered combining marks, Hangul jamo, emoji sequences;
- fullwidth and look-alike letters (U+017F, U+212A, U+0130/U+0131);
- typed `[CLS]`/`[MASK]`, U+2581;
- about 800 lines past the 64-token cut, about 5400 with `[UNK]`;
- negations behind newlines and non-ASCII punctuation, and up to 100 filler words before one.

Two traps the tests caught:
- **HF `tokenizers` normalizes with older Unicode tables than Python's `unicodedata` 14.0.** It does
  not decompose U+11938 and gives U+07FD combining class 0. The model was trained on what
  `tokenizers` produces, so `gen_unicode_tables.py` takes decompositions and combining classes from
  its behaviour.
- **MSVC's `std::regex` matches `^` after every `\n`, and there is no flag to turn that off.**
  Python's `re` matches `^` only at the start. A leading `^` is therefore run as `match_continuous`,
  and any other anchor is refused at load.

A limit the tests document: MSVC's `std::regex` recurses once per repetition of a group and gives
up (error_stack) past about 1000 levels. The negation pattern reaches that after ~118 leading filler
words ("uh uh uh ... don't"). There the slot counts as absent instead of crashing, where Python would
still find it. The 4 test lines past the limit check only that nothing crashes.

## Speed and memory (i9-10900K, fp32, ONNX Runtime CPU)

Shipped v2 bot, three models:

| members | intra-op threads per model | threads in all | median | p99 |
|---|---|---|---|---|
| one thread each | 4 | 12 | 45.6 ms | 55.0 ms |
| one thread each | 2 | 6 | 50.7 ms | 64.5 ms |
| one thread each | 1 | 3 | 61.3 ms | 80.6 ms |
| in turn | 4 | 4 | 77.5 ms | 95.0 ms |
| in turn | 2 | 2 | 90.8 ms | 119.9 ms |
| in turn | 1 | 1 | 123.2 ms | 171.4 ms |

- Load: 5.6 s; working set 2.3 GB.
- Tokenizer: ~20 µs per line.
- `--no-spin` (idle threads sleep, which a game wants) costs about 3 ms: 48.5 ms median at 4 threads
  per model.

The CPU has 10 cores and 20 hardware threads, so 12 threads do not get 12 cores. For a game, one
thread per member is the natural setting: 3 cores for ~60 ms.

One v1 model for comparison: 25.7 ms at 4 threads, 39.6 ms at 1 thread; 0.8 GB, loaded in 2.0 s.
The raw outputs are in `bench.txt` next to each bot's `intent_config.json`.

- Plain dynamic int8 quantization (`quantize_dynamic`, QInt8) broke the v1 model when the first export
  was checked: 85 of the 592 golden lines of that time kept their argmax. So none is used.
- deberta-v3-large was measured as an alternative and dropped. At the fixed recipe, one seed collapsed
  on two of three folds, and the models that trained were not better than base.

## Porting to UE5 (plan)

- **Core files:** the four core pairs above plus `unicode_tables.inc` go into a runtime module. They
  use no exceptions except `std::regex`'s constructor.
- **Regexes:** with UE's default no-exceptions build, match the three slots with `FRegexPattern`
  (ICU), but on `SlotPatterns::Shadow(text)`, not on the raw text.
  - On raw text ICU's Unicode `\w` disagrees with Python's `re`: a review ran ICU 64 over the test
    lines and found 242 slot differences, e.g. "on 3²".
  - The shadow maps every character to an ASCII stand-in with Python's word class and case folding.
    On ASCII, ICU, `std::regex` and Python agree, and ICU's `^` matches only at the start.
  - ICU keeps its backtracking stack on the heap, so the MSVC recursion limit above goes away.
  - Keep the check: run the slots in `tokenizer_tests.jsonl` through it in an automation test.
- **Model:** `ILogitsBackend` on NNE's CPU runtime (`NNERuntimeORTCpu`), one `UNNEModelData` asset
  and one model instance per member. Per line, set the input shapes to `{1, N}` for `input_ids` and
  `attention_mask` and run synchronously. The members run in parallel tasks and their outputs are
  averaged in probability space, as `EnsembleBackend` does (keep it: it returns log-mean
  probabilities, so the rest of the pipeline does not change). Check the exact NNE calls against the
  engine version.
- **Threads:** tokenizer and `BotBrain` run on the game thread (microseconds); the models run on
  workers (~60 ms with one core each); the result comes back to the game thread. `BotBrain` holds the
  queued order, so it stays on one thread.
- **Loading data:** `vocab.tsv` and `intent_config.json` are read with `FFileHelper` and
  `FJsonSerializer`. `DebertaTokenizer::Load` takes the text, not a path. Load the three models
  asynchronously at level start (5.6 s).
- **Game integration:** labels become GameplayTags; the game voices the reply lines itself (the CLI's
  lines are a demo). TAKE_COVER and OPEN carry no target; the planner picks the cover spot or the door
  (the marker, or the nearest one).

## Regenerating

After re-training or changing the regexes (PowerShell; `COOP_TAG=v21` selects the seed set the
shipped model is trained on; without it `train_v2.py final` would overwrite the model with a v2-seed
one):
```
$env:COOP_TAG = "v21"
python scripts/coop/train_v2.py final ens3                           # three models + bot_config.json
python scripts/coop/export_cpp.py models/coop-deberta-v3-ens3-v2     # ONNX, vocab.tsv, intent_config.json, golden.jsonl
python scripts/coop/check_onnx.py models/coop-deberta-v3-ens3-v2     # ONNX Runtime vs PyTorch, before any C++
python cpp/coop_intent/tools/gen_tests.py models/coop-deberta-v3-ens3-v2   # tokenizer, dialogue, gate and decide tests
```
Run `tools/gen_unicode_tables.py` only when the `tokenizers` version changes. It checks its tables
against `tokenizers` on 1.3M strings.

## Known model behaviour (not the port)

The model saw only English:
- «прикрой меня» → REVIVE_ME 0.92 → acts (v1 bot);
- "prikroy" → FRAG 0.97 → acts (v1 bot).

The threshold does not catch this, so the game should filter non-English lines or train on them.
