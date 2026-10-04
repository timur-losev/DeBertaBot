# coop_intent: the co-op bot in C++

The fine-tuned DeBERTa co-op bot ([DEBERTA-BOT.md](../../DEBERTA-BOT.md)) as a C++17 engine. It
covers the tokenizer, the model call (one model or an ensemble), and the bot's decision logic. It is
checked line by line against the Python bot, and it is laid out so the core can move into UE5
unchanged.

The shipped bot is **v3** ([COOP-BOT.md](../../COOP-BOT.md), sections "v2" and "v3"):
- 24 intents, including TAKE_COVER (the bot hides; the planner picks the spot) and OPEN (open a door
  or window without going through);
- three DeBERTa-v3-base models with their probabilities averaged, re-trained with lines that name
  map places;
- the family gate, threshold 0.52;
- the map's named places found in every line and handed to the planner as a record (`locations.h`).

Earlier bots still run with `--model-dir`: `..\..\models\coop-deberta-v3-ens3-v2\cpp` (v2, no place
lines in training) and `..\..\models\coop-deberta-v3-base\cpp` (v1, 22 intents).

## Layout

| file | what | into UE5 |
|---|---|---|
| `include/coop_intent/unicode.h`, `src/unicode.cpp`, `src/unicode_tables.inc` | UTF-8, NFC and the character classes, from generated tables (no ICU, no OS calls) | as is |
| `include/coop_intent/tokenizer.h`, `src/tokenizer.cpp` | the HF DebertaV2 tokenizer: added tokens, normalizer, Metaspace, Unigram/Viterbi | as is |
| `include/coop_intent/bot_brain.h`, `src/bot_brain.cpp` | `coop_bot.py` `respond()`: top or family gate, threshold, negation guard, GO_NOW/WAIT, queued order, regex slots | as is, or swap `SlotPatterns` for `FRegexPattern` |
| `include/coop_intent/locations.h`, `src/locations.cpp` | `LocationMatcher`: the map places in a line (object, side or colour, floor), whose place each is, which one the bot acts on; a twin of `scripts/coop/locations.py`, no regex and no Unicode tables | as is |
| `include/coop_intent/intent_model.h`, `src/intent_model.cpp` | `ILogitsBackend`, `EnsembleBackend` (averages the members' probabilities, one thread each or in turn), softmax, top-k | as is |
| `src/ort_backend.cpp` | `OrtBackend`: one model in ONNX Runtime 1.30 (C++ API) | replaced by an NNE backend |
| `tools/coop_cli.cpp` | terminal chat and the checks | no |
| `tools/gen_unicode_tables.py` | writes `unicode_tables.inc` from the HF `tokenizers` library itself | no |
| `tools/gen_tests.py` | writes the test files (tokenizer, places, gates, decisions, dialogue) from the Python bot | no |

`scripts/coop/export_cpp.py <bot dir>` writes the model files to `<bot dir>/cpp/`. For the shipped
bot that is `models/coop-deberta-v3-ens3-v3/cpp/`:
- `model0.onnx`, `model1.onnx`, `model2.onnx`: fp32, 705 MB each, opset 17, dynamic sequence length.
  A single-model bot has one `model.onnx`.
- `vocab.tsv`
- `intent_config.json`: labels, families, phrases, threshold, gate, member files, special ids, the
  three regexes and `locations` (the map vocabulary, a copy of `scripts/coop/locations.json`).
- `golden.jsonl`: token ids and PyTorch probabilities per line (the members' average).

## Build and run

Built and checked on Windows (VS 2022 Build Tools, CMake). `CMakeLists.txt` also has macOS and Linux
branches (ONNX Runtime release for the platform under `third_party/`), but the engine has not been
built there yet; see [HANDOFF.md](../../HANDOFF.md).

```
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release

build\Release\coop_cli.exe                    # chat, like coop_bot.py: /why /t 0.6 /q
build\Release\coop_cli.exe --golden           # C++ vs PyTorch on 1062 lines
build\Release\coop_cli.exe --tokenizer-tests  # C++ vs the HF tokenizer and Python re on 9231 lines
build\Release\coop_cli.exe --location-tests   # the place record of 8563 lines vs locations.py (no model)
build\Release\coop_cli.exe --dialogue         # C++ vs coop_bot.Bot on a 77-line conversation
build\Release\coop_cli.exe --gate-tests       # both gates on 1469 probability rows (no model)
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

On the shipped v3 ensemble.

| check | result |
|---|---|
| token ids, 1062 golden lines | 1062/1062 identical |
| probabilities vs PyTorch (ensemble average) | 1062/1062 within 1e-4, max difference 1.4e-6, argmax 1062/1062 |
| normalizer / token ids, 9231 lines | 9231 / 9231 identical |
| regex slots, 9227 lines (+ 4 past std::regex's limit, see below) | 9227/9227 identical |
| place records (targets, roles, flags, primary), 8563 lines: the tokenizer's adversarial lines, the developer's regression lines, the blind v3 lines, the location seeds | 8563/8563 identical |
| intent, confidence, action, queued order and places, 77-line conversation through the models | 77/77 identical |
| both gates on 1469 probability rows: the golden lines, exact ties, the top label outside the top-mass family, random rows | 2938/2938 identical |
| every branch of the decision (negated, say again, ignore, execute, go, wait, queued, act, "other", the threshold boundary) and the places a queued order keeps, both gates, constructed probabilities | 52/52 identical |

The 9231 lines are the golden lines plus lines generated to break a port:
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

Shipped v3 bot, three models (`models/coop-deberta-v3-ens3-v3/cpp/bench.txt`):

| members | intra-op threads per model | threads in all | median | p99 |
|---|---|---|---|---|
| one thread each | 4 | 12 | 35.4 ms | 43.7 ms |
| one thread each | 2 | 6 | 33.3 ms | 42.1 ms |
| one thread each | 1 | 3 | 39.4 ms | 54.0 ms |
| in turn | 4 | 4 | 57.0 ms | 74.7 ms |
| in turn | 2 | 2 | 63.1 ms | 90.7 ms |
| in turn | 1 | 1 | 87.0 ms | 140.6 ms |

- Load: 4.5 s; working set 2.3 GB.
- Tokenizer: ~20 µs per line. Place matcher: 1.7 µs per line.
- `--no-spin` (idle threads sleep, which a game wants) cost nothing measurable: 34.7 ms median at 4
  threads per model.
- The v2 bot measured the same day gives the same latencies (39.9 ms with one thread per model, 57.2
  ms in turn with 4 threads). An earlier v2 run, kept in the v2 bot's `bench.txt`, was about a third
  slower for a reason not identified; machine load is the likely one.

The CPU has 10 cores and 20 hardware threads, so 12 threads do not get 12 cores. For a game, one
thread per member is the natural setting: 3 cores for ~40 ms.

One v1 model for comparison: 25.7 ms at 4 threads, 39.6 ms at 1 thread; 0.8 GB, loaded in 2.0 s.
The raw outputs are in `bench.txt` next to each bot's `intent_config.json`.

- Plain dynamic int8 quantization (`quantize_dynamic`, QInt8) broke the v1 model when the first export
  was checked: 85 of the 592 golden lines of that time kept their argmax. So none is used.
- deberta-v3-large was measured as an alternative and dropped. At the fixed recipe, one seed collapsed
  on two of three folds, and the models that trained were not better than base.

## Porting to UE5 (plan)

- **Core files:** the five core pairs above plus `unicode_tables.inc` go into a runtime module. They
  use no exceptions except `std::regex`'s constructor. `locations.cpp` uses neither regex nor Unicode
  tables and ports as is.
- **Places:** `Decision::places` is the record for the planner.
  - Give the level's actors tags that mirror the vocabulary ids (`Place.Door.North`,
    `Place.Stairs.Blue`, `Zone.Basement`) and resolve the primary target against them.
  - One match: take it. Several (chairs, the same door on two floors): the bot's floor, then the
    nearest, or the ping marker.
  - `unknown_modifier`: do not fall back to the nearest one; use the marker or ask "which one?".
  - `unsure`: confirm.
  - A target with a role (`mine`, `them`, `from`, `not`, `status`) is never a destination; `them`
    targets are contacts for the blackboard.
  - `up` / `down` / `floor_2` are resolved per map.
  - On Execute, use `Decision::executed_places` (the queued order's places), not the GO line's.
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
  workers (~40 ms with one core each); the result comes back to the game thread. `BotBrain` holds the
  queued order, so it stays on one thread.
- **Loading data:** `vocab.tsv` and `intent_config.json` are read with `FFileHelper` and
  `FJsonSerializer`. `DebertaTokenizer::Load` takes the text, not a path. Load the three models
  asynchronously at level start (4.5 s).
- **Game integration:** labels become GameplayTags; the game voices the reply lines itself (the CLI's
  lines are a demo). TAKE_COVER and OPEN carry no target; the planner picks the cover spot or the door
  (the marker, or the nearest one).

## Regenerating

After re-training (PowerShell; `COOP_TAG=v3` selects the data and seed set the shipped model is
trained on, and `train_v2.py final` then writes `models/coop-deberta-v3-ens3-v3`):
```
$env:COOP_TAG = "v3"
python scripts/coop/train_v2.py final ens3                           # three models + bot_config.json
python scripts/coop/export_cpp.py models/coop-deberta-v3-ens3-v3     # ONNX, vocab.tsv, intent_config.json, golden.jsonl
python scripts/coop/check_onnx.py models/coop-deberta-v3-ens3-v3     # ONNX Runtime vs PyTorch, before any C++
python cpp/coop_intent/tools/gen_tests.py models/coop-deberta-v3-ens3-v3   # tokenizer, place, dialogue, gate and decide tests
```
After changing only the map vocabulary (`scripts/coop/locations.json`) or the regexes, no training and
no ONNX export are needed:
```
python scripts/coop/locations.py --dev                                        # the developer's regression lines
python scripts/coop/export_cpp.py models/coop-deberta-v3-ens3-v3 --config-only
python cpp/coop_intent/tools/gen_tests.py models/coop-deberta-v3-ens3-v3
```
Run `tools/gen_unicode_tables.py` only when the `tokenizers` version changes. It checks its tables
against `tokenizers` on 1.3M strings.

## Known model behaviour (not the port)

The model saw only English:
- «прикрой меня» → REVIVE_ME 0.92 → acts (v1 bot);
- "prikroy" → FRAG 0.97 → acts (v1 bot).

The threshold does not catch this, so the game should filter non-English lines or train on them.
