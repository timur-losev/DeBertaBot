# coop_intent: the co-op bot in C++

The fine-tuned DeBERTa co-op bot ([DEBERTA-BOT.md](../../DEBERTA-BOT.md)) as a C++17 engine. It
covers the tokenizer, the model call (one model or an ensemble), and the bot's decision logic. It is
checked line by line against the Python bot, and it is laid out so the core can move into UE5
unchanged.

The default bot is **v31** ([COOP-BOT.md](../../COOP-BOT.md), sections "v2" and "v3";
`COOP_MODEL_DIR` in `CMakeLists.txt`):
- 24 intents, including TAKE_COVER (the bot hides; the planner picks the spot) and OPEN (open a door
  or window without going through);
- three DeBERTa-v3-base models with their probabilities averaged, re-trained with lines that name
  map places and seed set v31;
- the family gate, threshold 0.62;
- the map's named places found in every line and handed to the planner as a record (`locations.h`,
  rule set v3). The matcher does not depend on the model.

Model weights are not in git. On a machine without the v31 weights CMake makes the v2 bot the
default and says so.

Other bots run with `--model-dir`:
- `../../models/coop-deberta-v3-ens3-v2/cpp`: v2, the default until 2026-10-04: no place lines in
  training (family gate, 0.58);
- `../../models/coop-deberta-v3-ens3-v3/cpp`: v3, re-trained with place lines and the first seed set
  (family gate, 0.60; trained on the Mac). It carries out smoke and "clear" callouts as orders;
- `../../models/coop-deberta-v3-base/cpp`: v1, 22 intents, no place vocabulary in its config;
- `../../models/coop-deberta-v3-ens3-v4/cpp`: v4, the bot for the voice chain: the v31 data plus what the
  Parakeet speech recognizer heard of it, 12 epochs (top gate, 0.50; `scripts/coop/stt/README.md`). The
  engine still takes text: speech recognition is not part of it yet. Checked against the Python bot on
  2026-10-09: 1259 golden lines (within 2.2e-6), 9428 tokenizer lines, 20204 place records, 3332 gate
  decisions, 140 decision steps, the 77-line conversation; 40.0 ms per line on 3 cores;
- `../../models/coop-deberta-v3-ens3-v51/cpp`: v51, the voice-chain bot with 29 intents (family gate,
  0.62): v4's recipe plus ATTACK, OPEN_FIRE, HOLD_FIRE, LOOK_AT and LOOK_AT_ME, and the first bot
  exported with rule set v4 of the place matcher, so its place records carry a direction
  ("go down by stairs" -> stairs + down, "the left window" -> window + left, "go left" -> left only).
  Checked on 2026-10-09: the column "v51 bot" below; 38.8 ms per line on 3 cores;
- `../../models/coop-deberta-v3-ens3-v52/cpp`: v52, the voice-chain bot with 32 intents (family gate,
  0.60): v51 plus HELP, CHECK and SUPPRESS, added after the owner's first test with a real voice, and
  examples of things the bot has no order for. Known fault: "check fire" (stop shooting) is picked as
  CHECK; v51 had it right. Checked on 2026-10-09: the column "v52 bot" below; 39.5 ms per line on 3 cores;
- `../../models/coop-deberta-v3-ens3-v53/cpp`: v53, the voice-chain bot with 33 intents (family gate,
  0.66): v52 plus JUMP (jump, drop or climb without a rope or a window; the direction or the object is in
  the place record), "check fire" back under HOLD_FIRE, both sides of "the other angle". Known faults:
  "check the fire escape" is picked as HOLD_FIRE, "drop in through the hatch" as VAULT_WINDOW. Moved to
  rule set v5 of the place matcher on 2026-10-10 without retraining (`export_cpp.py --config-only`): its
  place records carry a pointer ("stay at my pin" -> `@pin`, "check that room" -> `@this`), and "on my
  mark" no longer queues the order for a go. The column "v53 bot" below; 39.2 ms per line on 3 cores;
- `../../models/coop-deberta-v3-ens3-v54/cpp`: v54, 41 intents (COME_BACK, CROUCH, PRONE, STAND_UP and the
  answers YES / NO / MAYBE / DONT_KNOW; family gate, 0.68). Trained on the work machine on 2026-10-10 as the
  teacher of the distillation study (`scripts/coop/stt/ensemble_bot_v54.py`: the threshold from the fold
  teachers' out-of-fold run); the MacBook build the owner runs (`HANDOFF.md`, section 5, step 13) replaces its
  `bot_config.json`. Checked: tokenizer 10912/10912, places 50869/50869 (13982 with a pointer), gates 6300/6300,
  decisions 244/244 (the answer branch on a real bot), golden 2743/2743 (1.8e-6), dialogue 77/77, planner
  5198/5198; 39.3 ms per line on 3 cores. On the owner's lines of his v53 test: 19/19 (7/19 live with v53);
- `../../models/coop-deberta-v3-{base,small,xsmall}-kd-v54/cpp`: one-model students of v54 distilled from the
  ensemble (`scripts/coop/stt/distill_v54.py`, `student_bot_v54.py`; family gate, 0.88 clamped from a fitted
  0.96-0.98), the same seven checks equal for each. On one core: base 28.4 ms (808 MB), small 14.1 ms (618 MB),
  xsmall 9.8 ms (355 MB); next to each a `cpp_int8_all` / `cpp_int8_per_channel` / `cpp_uint8_matmul_only`
  directory with the dynamically quantized model (small int8: 8.0 ms, 216 MB, 2738/2743 golden argmax; base and
  xsmall break under int8 except xsmall MatMul-only). What they cost in accuracy is in `COOP-BOT.md`, "Brains":
  the ensemble stays the bot; one base is the cheap option (-1.4 / -5.7 criterion typed / unseen speakers).
- `../../models/coop-deberta-v3-ens3-v55/cpp`: v55, 44 intents (v54 plus GET_IN and GET_OUT for a car, and REPEAT
  for "try again" / "again" / "more"; family gate, 0.64), trained on 2026-10-14 after the owner's play
  (`scripts/coop/make_spec_v55.py`, `stt/build_v55.py`, `stt/ensemble_bot_v55.py`). A negated order ("don't follow
  me", "don't jump down") is WAIT, "don't shoot" stays HOLD_FIRE and "don't move" HOLD_POSITION; "wait here" is
  HOLD_POSITION; "go find ammo" (heard as "armor", "amor"), "get a weapon", "find health" are MOVE_TO with the place
  `ammo` / `weapon` / `health` (`car` for the car), which the planner takes as the nearest one without asking; "on
  my goal" (what the recognizer hears for "on my go") waits for the go. Checked: golden 3049/3049, tokenizer
  11218/11218, places 51332/51332, gates 6912/6912, decisions 244/244, dialogue 77/77, planner 8142/8142.
- `../../models/coop-deberta-v3-ens3-v58/cpp`: v58, v57's 47 intents with 75 more seeds of going on with a way, a
  side or a place ("keep moving forward", "further up", "keep coming back"); a going-on with no way ("keep moving",
  "carry on") is mostly MOVE_TO with no place, which the planner and the game take as the same move a moment ago or
  where the player looks (the owner's choice, 2026-10-18); family gate, 0.66 (`scripts/coop/make_spec_v58.py`,
  `stt/build_v58.py`, `stt/ensemble_bot_v58.py`). Checked: golden 3633/3633, tokenizer 11802/11802, places
  51824/51824, gates 8080/8080, decisions 244/244, dialogue 77/77, planner 8292/8292; with the v58 chain, chain tests
  160/160 (CPU). Deployed with `-Chain coop-chain-v58` (decoder v58, router v55).
- `../../models/coop-deberta-v3-ens3-v57/cpp`: v57, 47 intents (v56 with SWITCH_WEAPON, "switch weapons", "switch to
  your pistol", and RELOAD; a bare "get out" is GET_OUT; family gate, 0.68), trained on 2026-10-17 after the owner's
  play (`scripts/coop/make_spec_v57.py`, `stt/build_v57.py`, `stt/ensemble_bot_v57.py`). The planner gives the two new
  intents no place. Checked: golden 3558/3558, tokenizer 11727/11727, places 51733/51733, gates 7930/7930, decisions
  244/244, dialogue 77/77, planner 8100/8100; with the v55 chain, chain tests 160/160 (CPU).
- `../../models/coop-deberta-v3-ens3-v56/cpp`: v56, 45 intents (v55 without REVIVE_ME; HELP_INTERACTION in its place,
  "let me out", "get me out of here", "press the button for me"; GO_BACK after REPEAT, "go back" to where the bot was;
  family gate, 0.60), trained on 2026-10-15 after the owner's play (`scripts/coop/make_spec_v56.py`,
  `stt/build_v56.py`, `stt/ensemble_bot_v56.py`). Being revived is HELP; COME_BACK is coming back to the player;
  "stand here", "stand on my pin" are HOLD_POSITION; "go down the ramp", "stairs on my pin" are MOVE_TO. Exported with
  the place vocabulary of rule set v7 (the zone `inside`). Checked: golden 3327/3327, tokenizer 11496/11496, places
  51549/51549, gates 7468/7468, decisions 244/244, dialogue 77/77, planner 8389/8389; with the v55 chain, chain tests
  160/160 on the CPU.

**The matcher follows the vocabulary a bot was exported with.** A config whose word lists include the
`pin_*` and `point_*` lists runs rule set v5: a target may carry a pointer, `pin` (the player's 3D marker:
"my pin", "the ping", "on my mark", "where i marked") or `this` (this / that / here / there). One with a
`"directions"` section and without those lists runs rule set v4, and one without `"directions"` runs
rule set v3 -- each exactly as before, so the bots exported earlier keep their records and their test
files. `export_cpp.py <bot> --config-only` moves a bot to the current vocabulary (rule set v5) and the
current timing pattern ("mark" is the pin, not the go-signal), and `gen_tests.py` refuses a bot whose
config holds an older vocabulary or older regexes.

Rule set v7 (bot v56, 2026-10-15) is rule set v5's code with one step more, taken only by a vocabulary with the
zone `inside` (locations.json version 7): "inside" said on the way to a map object is that object's preposition, not
a place of its own ("get inside the car" = the car, "go inside through the west door" = the west door); a bare
"inside", "indoors", "in the building" is the zone. The bots exported before keep their records.

Rule set v8 (2026-10-27, the owner on the test range: "Can you see the white table?" "Yes." "Jump over it." jumped
over a crate the bot had pushed before) adds a third pointer, `it`, taken only by a vocabulary with the `it_*` word lists
(`scripts/coop/locations_v65.json`, version 11, made by `make_locations_v65.py`; the v65 bot was exported again with it,
no training). "it" after an `it_prep` preposition ("jump over it", "get on it", "hide behind it"), an `it_verb` verb
("open it", "shoot it", "pick it up") or "of" after `top` / `front` / `side` is a target of its own and never joins a
place; "do it", "take it", "put it down", "it's" are not. The planner grounds it from the conversation first: the last
thing an order or a settled question named, if the game's clock says it was 30 s ago or less (`world.IT_SECONDS`,
`Memory::last_time`); then the crosshair. An "it" that points at nothing is dropped (`WithoutLostIt`), and the line is
an order with no place, as before. Version 11 also lets a table take the colours (blue, red, yellow, white, brown): "the
white table" was an unknown modifier, and the bot asked "Which table?" from the nearest. Checked on the v65 bot:
places 60988/60988 (with 8000 generated "it" lines), planner 12076/12076 (with 300 conversations about a thing and "it"),
decisions 244/244, dialogue 77/77, gates 11710/11710, items 92070/92070, tokenizer 13617/13617; chain tests 200/200 (CPU).

DROP by a thing (2026-10-27, the owner on the test range: «Поставь его рядом с белым столом» with a crate in hand).
- **What went wrong:** the decoder writes "put it down next to the white table", the classifier reads DROP, and DROP takes
  no place (NO_PLACE). The table was lost, and the bot put the box down where it stood.
- **The rule:** a DROP line whose primary place names a thing in words is DELIVER to it (`world.drops_by_thing`,
  `Planner::DropsByThing`, before NO_PLACE drops the place).
  - The carried thing itself is not the place: "put the box down" stays DROP, as `without_item_place` reads it for
    DELIVER.
  - A pointer ("here", "there", "it", the pin) or a zone ("outside") keeps DROP's own spot.
  - The answer to "Which table?" that the decoder writes as "put it down the white table" now settles the question's
    DELIVER.
- **Tests:** `gen_world_tests.py` adds 150 conversations (`DROP_BY`, seed 8101). On bot v66: planner 12836/12836, the
  other seven checks equal.

## Layout

| file | what | into UE5 |
|---|---|---|
| `include/coop_intent/unicode.h`, `src/unicode.cpp`, `src/unicode_tables.inc` | UTF-8, NFC and the character classes, from generated tables (no ICU, no OS calls) | as is |
| `include/coop_intent/tokenizer.h`, `src/tokenizer.cpp` | the HF DebertaV2 tokenizer: added tokens, normalizer, Metaspace, Unigram/Viterbi | as is |
| `include/coop_intent/bot_brain.h`, `src/bot_brain.cpp` | `coop_bot.py` `respond()`: top or family gate, threshold, negation guard, GO_NOW/WAIT, HOLD_FIRE (a bot that has the label: it acts at once and keeps the queued order; with the signal slot it queues OPEN_FIRE), the answers (a bot whose config lists `answer_intents`: YES / NO / MAYBE / DONT_KNOW are the action `answer` -- reported, never queued, the queued order left alone), queued order, regex slots | as is, or swap `SlotPatterns` for `FRegexPattern` |
| `include/coop_intent/locations.h`, `src/locations.cpp` | `LocationMatcher`: the map places in a line (object, side or colour, floor, direction, and whether the line points at it with the pin or with this / that / here / there), whose place each is, which one the bot acts on; a twin of `scripts/coop/locations.py`, no regex and no Unicode tables | as is |
| `include/coop_intent/items.h`, `src/items.cpp` | `ItemMatcher` (a v60 bot, a config with `"items"`): what the farmer's and the builder's orders act on, as the player said it ("build a pillar" = "pillar"); a twin of `scripts/coop/items.py` | as is |
| `include/coop_intent/world.h`, `src/world.cpp` | `Planner` over `BotBrain` (see "The world"): the place record grounded against the game's world state (which door, which pin, where the player looks), the conversation's memory, the question the bot asks when a place is ambiguous or missing and the yes / no / place that settles it, the priors the world puts on the probabilities; a twin of `scripts/coop/world.py` | as is: the game fills `WorldState` from its perception and reads `Order` |
| `include/coop_intent/intent_model.h`, `src/intent_model.cpp` | `ILogitsBackend`, `EnsembleBackend` (averages the members' probabilities, one thread each or in turn), softmax, top-k | as is |
| `src/ort_backend.cpp` | `OrtBackend`: one model in ONNX Runtime (C++ API; it asks the loaded runtime for that runtime's own API level, so the 1.30 build also runs on an older `onnxruntime.dll`) | replaced by an NNE backend |
| `include/coop_intent/speech.h`, `src/speech_text.cpp` | `SpeechTextForClassifier`: the form of a transcript the voice-chain bots were trained on | as is |
| `src/sherpa_speech.cpp` | `SpeechRecognizer`: Parakeet TDT through sherpa-onnx's C API (optional, see "Speech-to-text") | with sherpa-onnx as a third-party library |
| `tools/mic_capture.h`, `tools/mic_capture_win.cpp`, `tools/mic_capture_mac.mm` | the microphone of `coop_cli --voice` (Windows: waveIn; macOS: an AudioQueue) | no: the game has its own capture |
| `tools/coop_cli.cpp` | terminal chat, the checks, and the bot as a service for a game (`--serve`) | as the game's helper process |
| `tools/tts.h`, `tools/tts_win.cpp` | the bot's voice for `--serve --tts`: the system synthesizer (Windows SAPI, the first English voice); since 2026-10-17 the fallback of the one below | with the helper process |
| `include/coop_intent/voice.h`, `src/sherpa_voice.cpp` | `PiperVoice`: the bot's voice as audio, a Piper (VITS) model through sherpa-onnx's C API, for `--serve --tts-piper` (the game plays it from the bot) and `--tts-demo` | with sherpa-onnx, in the helper process |
| `include/coop_intent/rewriter.h`, `src/rewriter_text.cpp` | the text around the decoder (see "Lines with several orders or with a context"): the turn it is shown, the prompt, its answer as order lines, the router's probability | as is |
| `src/llama_rewriter.cpp` | `Rewriter`: the decoder (a 4-bit GGUF) on llama.cpp's C API, greedy, the prompt's common prefix kept between lines (optional) | with llama.cpp as a third-party library, in the helper process |
| `tools/setup_llama.ps1` | lays llama.cpp out under `third_party/` (headers, the release's DLLs, an import library made from `llama.dll`) | no |
| `tools/deploy_brain.ps1` | copies the exe, its DLLs, one bot and the speech model into one folder a game starts the service from; with `-Chain` the router, the decoder and llama.cpp's DLLs too | no |
| `tools/gen_unicode_tables.py` | writes `unicode_tables.inc` from the HF `tokenizers` library itself | no |
| `tools/gen_tests.py` | writes the test files (tokenizer, places, gates, decisions, dialogue) from the Python bot | no |
| `tools/gen_world_tests.py` | writes `world_tests.jsonl` (worlds and conversations through the Python planner) | no |

`scripts/coop/export_cpp.py <bot dir>` writes the model files to `<bot dir>/cpp/`. For the default
bot that is `models/coop-deberta-v3-ens3-v31/cpp/`:
- `model0.onnx`, `model1.onnx`, `model2.onnx`: fp32, 739 MB (704 MiB) each, opset 17, dynamic
  sequence length. A single-model bot has one `model.onnx`. The weights are not in git (HANDOFF.md,
  section 1).
- `vocab.tsv`
- `intent_config.json`: labels, families, phrases, threshold, gate, member files, special ids, the
  three regexes and `locations` (the map vocabulary, a copy of `scripts/coop/locations.json`).
- `golden.jsonl`: token ids and PyTorch probabilities per line (the members' average).

## Build and run

Built and checked on Windows (VS 2022 Build Tools, CMake) and on macOS arm64 (AppleClang, Ninja;
the commands are in [HANDOFF.md](../../HANDOFF.md), section 3). Linux has a CMake branch and has not
been built.

```
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release

build\Release\coop_cli.exe                    # chat, like coop_bot.py: /why /t 0.6 /q
build\Release\coop_cli.exe --golden           # C++ vs PyTorch on the golden lines (1259 for the v31 bot)
build\Release\coop_cli.exe --tokenizer-tests  # C++ vs the HF tokenizer and Python re (9428 lines)
build\Release\coop_cli.exe --location-tests   # the place records vs locations.py (20204 lines, no model)
build\Release\coop_cli.exe --dialogue         # C++ vs coop_bot.Bot on a 77-line conversation
build\Release\coop_cli.exe --gate-tests       # both gates on 1666 probability rows (no model)
build\Release\coop_cli.exe --decide-tests     # every branch of the bot's decision, both gates (no model)
build\Release\coop_cli.exe --world-tests      # the planner on 906 worlds and conversations vs world.py (no model)
build\Release\coop_cli.exe --item-tests       # a v60 bot: the items of the farmer's and the builder's orders vs items.py (no model)
build\Release\coop_cli.exe --bench --threads 1
build\Release\coop_cli.exe --tokenize "hold the other angle"
build\Release\coop_cli.exe --world ..\..\scripts\coop\world_example.json   # chat with a world state loaded
build\Release\coop_cli.exe --serve --no-spin --threads 1 --tts   # the bot as a service: JSON lines on stdin / stdout
```

- `--language en|ru|es` sets the player's language; the default is en.
  - For ru and es, every line goes to the decoder of `--chain`, and the router is not asked. The chain must be v62 or
    later, trained on the three languages (`scripts/coop/stt/chains6_v62.py`). The decoder writes the line as English
    orders, and the classifier, the place matcher and the planner read them as usual.
  - An answer to the bot's question is read from the decoder's English.
  - The talk memory keeps the player's own lines, as the decoder learned them.
  - Speech: `--stt-model` with Parakeet TDT 0.6B v3 (`sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8`, 25 languages). It has
    the same files and engine as v2, and transcribes Russian word for word on Windows voices.
- `--replies FILE` makes the bot answer in the table's language ([localize.h](include/coop_intent/localize.h)):
  - The table is `scripts/coop/replies/replies_<lang>.json`: 278 English sentence templates from `catalogue_en.json`
    (`make_catalogue.py`), translated by `TRANSLATE.md`, with each slot's words in the forms the translations use.
  - Every reply's `say` is written in the language, and `say_en` keeps the English. A sentence without a template keeps
    the line English (`say_untranslated`) and is logged on stderr.
  - `--voice-local DIR` says the lines written in the language with that voice (Piper, or a Kokoro export with
    `voices.bin`; a `voice.json` in the folder gives its speaker and language). A line the game hands to `say` in English
    is translated first, sentence by sentence: sentences this brain already wrote stay as they are. The `speech` event's
    `text` and `lang` say what was said.
  - `--replies-check FILE` translates every template with every value of each slot: every table (438 templates since
    2026-10-27, the door and climb lines of the GOAP phases added) passes 1361 of 1361.
  - A `say` may bring `terms`: the words of the level's labelled things in the player's language (the open slot `thing`;
    `Localizer::Terms`). A form `*` writes the English words as they came (the English table of the habit below).
- `--replies-bro FILE --bro on|off --bro-relapse SECONDS` (2026-10-24, [bro.h](include/coop_intent/bro.h)): the habit of
  calling the player «брат» / "bro" / "hermano". A word for "brother" in the player's line turns it on; "stop calling me
  bro" and the like turn it off (the reply is the bot's agreement and nothing else is read). While it is on, the lines
  come from FILE (`replies_<lang>_brat.json`, en too); `--bro-relapse 30` (the brat persona) brings it back 30 s after it
  was stopped, with "Sorry, habit.". The reply says `bro` (on/off) and `bro_active`. `--bro-check tools/bro_tests.json`:
  42 lines in three languages and the relapse.
- `state` in a reply (2026-10-24): a question about the bot only the game can answer, with no order and no words: `seen`
  ("what do you see?", also «что видишь?» / «qué ves?» in the player's own words), `how`, `hurt`, `heat`, `cold`, `gas`,
  `ammo` ("got any ammo?" is read as a walk to the ammo: the planner's "Where?" is dropped). `StateQuestion` in coop_cli.cpp.
- `--decider DIR` (a build with llama.cpp) adds an optional second reader of every line beside the ensemble:
  - The model is decider-2b with the bot's LoRA, as a GGUF ([decider.h](include/coop_intent/decider.h)). `DIR` is
    `scripts/coop/decider/export_game.py`'s folder.
  - `--decider-mode avg` (the default) averages the two readers' probabilities; `only` uses the decider's alone.
  - `--decider-threads N` (default 8) and `--decider-gpu-layers N` (default 0, the CPU alone) tune it.
  - It runs on its own thread while the ensemble reads the line. At load it decodes its prompt's fixed 1,052 tokens
    once; per line it computes only the line's own 10 to 25 tokens, about 135 to 220 ms on an i9-10900K.
  - Without the option nothing changes. A decider that does not load, or a line it cannot read, leaves the ensemble
    alone.
  - `--decider DIR --decider-tests DIR/decider_tests.json` checks it: the line's tokens against upstream's tokenizer,
    and the probabilities against `decider_eval`'s on the same GGUF.
  - The study behind it: [scripts/coop/decider/README.md](../../scripts/coop/decider/README.md).
- `--model-dir` picks another exported bot.
- `--world FILE` loads a world state for the chat (`/world FILE` in the chat does the same); without one the
  planner runs on an empty world and asks "where?" for every place it cannot ground.
- `--threads` sets ONNX Runtime's intra-op threads per model.
- `--sequential` runs an ensemble's members one after another instead of one thread each.
- `--no-spin` lets idle worker threads sleep.

`third_party/` holds the ONNX Runtime release (`onnxruntime-win-x64-1.30.0`, from GitHub
releases) and `nlohmann/json.hpp` (the CLI only). The build copies `onnxruntime.dll` next to the
exe, because Windows ships an older `onnxruntime.dll` in System32. With speech-to-text the DLL next
to the exe is sherpa-onnx's 1.28.2 instead (next section); the chat's first lines print which one runs.

## The world (the brain's tier 0, 2026-10-10)

The classifier says *what*; `Planner` (`world.h`) says *where* and *whether*, from a world state the game hands
over before every line (`WorldState`: entities with the vocabulary's object / qualifier / zone ids, bearing in
the player's view, distance, elevation, tags; the player's pin; what the player looks at; the bot's stance and
items; whether the player is down). Nothing here touches the model; a step costs microseconds.

- **Grounding.** Each target of the place record becomes an entity: "the door on the left" is the door in the
  left sector, "stay at my pin" the pin, "check that window" the window under the crosshair, "the other door"
  not the last one, "there" the gaze or else the last place settled. One candidate: resolved. Two doors at
  8 and 11 m: *ambiguous* (one is resolved only when the next is 1.5 times as far). "The back door" (an
  unknown modifier): always ambiguous, never the nearest. Nothing of the kind in sight: *missing*.
- **The question.** On an ambiguous or missing primary target the bot asks instead of acting: "Which door?
  The one ahead, 8 m?". YES takes it, NO offers the next, MAYBE / DONT_KNOW takes the nearest, a place
  that narrows the candidates to one settles it ("the left one", "the north door") -- also when the line is
  under the threshold. Any other order drops the question. An order given "on my go" that is ambiguous is
  asked about first and queued with its entity once settled.
- **Memory.** The last entity settled, the last order, the pending question, the queued order's entity; the
  bot's own pin is set on the entity of every order it takes.
- **A world without named places** (a map nobody has marked: the pin, the crosshair, directions and the two
  people are all there is). The rules are about the words of the line, so they live here and not in the game:
  - *"Here" is where the speaker is*, not what the crosshair is on. A lone this-pointer in a line with "here" and
    no far word ("there", "that", "those", "looking", ...) is grounded `via: "here"` with no entity. "This ..."
    without a far word is near too: the order says `near`, and the game decides ("hold this spot" stays, "check
    this" goes to the crosshair).
  - *A named place that is pointed at.* "That door" where no door is marked is the untyped thing the crosshair
    is on; "the door at my pin" is the pin. Without a pointer the bot asks: "I see no door. Where?".
  - *A floor it cannot find.* A zone with no place on it ("go upstairs", "get to the roof") is missing, not
    resolved: "I can't find the way up. Where?".
  - *"Where?" is answered by pointing*: "there", "over there", "that one", "at my pin", "on the left". The line
    is the place of the order the bot asked about, also where the classifier reads another order into it ("over
    there" alone looks like MOVE_TO): it is short and starts with a place word (`Elliptical`). "Yes" or "go"
    settles it too, once the place the order named is there (the pin was put, the crosshair is on something).
  - *A queued order keeps its place*, "here" included, whatever the crosshair is on at "go".
- **Priors.** Multipliers on the probabilities before the gate (`DefaultPriors()`, the game can pass its own):
  a bot already crouched (`CROUCH`), no window in sight (`VAULT_WINDOW`), no door (`OPEN`), no bomb on the
  bot (`PLANT`), no bomb in sight (`DEFUSE`), the player up (`REVIVE_ME`), no question pending (the four
  answers) -- x0.75 each. They only lower, never renormalize: a prior cannot lift another intent over the
  threshold. Simulated on the v54 teachers' out-of-fold probabilities (`scripts/coop/stt/priors_v54.py`,
  810 lines): a world consistent with the truth gains 0.5 criterion points and changes 2-4 picks; a world
  drawn blind (the game's state wrong) costs 0.1-0.4 points at x0.75 and 4-5 points at the x0.4 ... x0.7 the
  first table had, which is why 0.75 is the default.
- **A short context** (2026-10-11). One frame of the order taken last (intent, place, time) and four readings of
  the next line against it, all rules:
  - *a place not said*: "Shoot!", "move up", "check it" take the standing pin (`via: "pin_default"`, and the bot
    says "Open fire, on your pin."); an order to fire with the crosshair on an enemy (an entity tagged `enemy`)
    takes none, the game has the enemy; the same order again within the window takes the same place; a grenade
    never takes a guessed place;
  - *"here" by the verb*: the speaker for "come here", the crosshair's point for "shoot here", "check here";
  - *a correction*: a line that starts with "no" and names a place is the previous order at that place; a bare
    "no" stops (`action: "negated"`). What follows the "no" (and an "I said" / "I meant") must be a place alone:
    "no, come here" is a new order read as it stands (`AfterNo`, world.py `after_no`, 2026-10-18);
  - *a repeat*: "again", "once more" give the previous order as it was;
  - *a fragment*: a place and no action right after an order ("on my pin", "over there") is that order's new
    place; so is a line under the threshold that ends in "there" or "here" ("Should there." heard for "Shoot
    there").
  The frame lives while the game says the bot is busy and `CONTEXT_SECONDS` (8) after. The world state carries
  `time` and `bot.busy`; a game that sends no time gets no context.
- **Floors by where they are** (2026-10-11). "Upstairs" and "downstairs" were zone ids no entity carried, so the
  planner could not find them even on a map with every floor marked. Now they are any marked place at least
  1.5 m above or below the speaker, narrowed to the nearest floor that way (the places within 1.5 m of the nearest
  one in height: one floor up, not the roof); "the door upstairs" is a door on a floor above. The game still takes
  the nearest of the candidates.
- **Checked:** `gen_world_tests.py` writes 600 random worlds (entities with twins at similar distances, pins,
  gazes, stances) and conversations of orders, answers and narrowing places through the Python planner;
  `coop_cli --world-tests` compares action, words, grounding, order, question, queue and memory step by step.
  With the rules for a world without named places and for the short context (the world moves on before every
  line: time, the pin, the crosshair, an enemy under it; the lines include bare orders, repeats, corrections,
  fragments and misheard pointers): 5509/5509 on bot v54 and on its three distilled students, 5351/5351 on the
  v53 bot (33 labels, no answer intents); 12 worlds to refuse or accept. The four scripted checks of `world.py`
  (`DEV`, `DEV_BARE` for the unmarked world, `DEV_TALK` for the owner's lines of the first live test,
  `DEV_FLOORS` for a building with its floors marked) are the first four scenarios of the file.

What the game provides and gets back is in `world.h`; the rules and their reasons are in `scripts/coop/world.py`.

## The bot as a service for a game (`--serve`, 2026-10-10)

How the bot lives in a game today: the game's CLIENT starts `coop_cli --serve` and talks to it through its two
pipes, one JSON object per line each way. Speech and command recognition are the client's business; what the
game then sends to its server is an order, not this process's output.

```
{"cmd":"text","id":7,"text":"hold the door","world":{...}}     a typed line and the world it is said in
{"cmd":"ptt_down"}  ...  {"cmd":"ptt_up","id":8,"world":{...}}  the talk key: the clip, then recognize, classify, plan
{"cmd":"wav","id":9,"path":"clip.wav"}   {"cmd":"world","world":{...}}   {"cmd":"say","text":"Contact left!"}
{"cmd":"reset"}  {"cmd":"threshold","value":0.7}  {"cmd":"ping"}  {"cmd":"hush"}  {"cmd":"quit"}

{"event":"ready","labels":[...],"gate":"family","threshold":0.68,"stt":true,"mic":true,"tts":true,...}
{"event":"reply","id":7,"heard":"hold the door","intent":"HOLD_ANGLE","prob":1.0,"action":"ask",
 "say":"Which door? The one ahead, 8 m?","order":null,"question":{...},"top":[...],"ground":[...],...}
{"event":"nothing"|"too_short"|"error", ...}
```

- `world` is `WorldState` as JSON (`scripts/coop/world_example.json`); `order` is what the game carries out now:
  `{"intent","entity","candidates","direction","zone","pointer","other","via","near"}`, `entity` being an id of
  the world the game sent, `via` how the place was found ("gaze", "pin", "direction", "here" = where the speaker
  is, ...) and `near` that the line pointed with "this" or "here". `action` is the bot's (act, queued, execute, go, wait, negated, answer, say_again, ignore) or the
  planner's (ask, resolved). The whole protocol is in the comment above `RunServe` in `tools/coop_cli.cpp`.
- **Each order at the moment of its pointer word** (2026-10-26). A spoken reply (`ptt_up`, `wav`) carries the
  recognizer's words with their start times, `"words":[{"w":"Take","t":0.32},{"w":"this","t":0.88},...]`, and
  `"clip_start_s"` (where the clip's second 0 is from the talk key going down: -0.2 for the microphone's pre-roll, 0 for
  a file). The game may send `"talk_trail":[{"t":0.1,"gaze":"crate_26"},{"t":3.1,"gaze":null},...]` in the world: the
  entity under the crosshair while the key was down. The k-th pointer of the heard words ("this", "that", "here",
  "there", «эту», «это», «сюда», «туда», «вон», "aquí", "allí"...; a run of them is one) goes to the k-th order line
  that points; that line is planned with the trail's entity of that moment as `player_gaze` (`Planner::SetGaze`), and
  its turn carries `"at_s"`, the moment in seconds since the key went down, so that the game grounds it with the
  crosshair and the player's place then ("take this box", run, "put it here"). A typed line has no words: nothing
  changes. `SpeechWords` builds the words from Parakeet's token timestamps (SentencePiece's word mark).
- A stdout line that does not start with `{` is a log line. The service ends when its stdin closes: it never
  outlives the game.
- `--no-stt`: no recognizer and no microphone, typed lines only (headless tests). `--tts`: `say` speaks.
- `--tts-piper DIR` (a sherpa-onnx Piper export: `<name>.onnx`, its `.onnx.json`, `tokens.txt`, `espeak-ng-data/`;
  ours is `scripts/coop/stt/tts/vits-piper-en_GB-vctk-medium`, 109 speakers, 22050 Hz), `--tts-speaker p311`,
  `--tts-speed 1.0`: a `say` with an id is answered with the line as audio, and the game plays it where the bot is:
  `{"cmd":"say","id":12,"text":"Contact left!","speaker":"p311","speed":1.0}` ->
  `{"event":"speech","id":12,"text":...,"rate":22050,"audio_s":0.8,"ms":88,"pcm16":"<16-bit mono, base64>"}`. The
  lines are made on a thread of their own, one at a time, three waiting at most (the oldest goes, answered
  `{"event":"hushed","id":..}`, as are the waiting ones at `hush` and `ptt_down`); a warm-up line at start keeps the
  first real one from paying the model's first run (1.7 s; then 70 to 185 ms a line, about a tenth of its length,
  on one core). With `--tts` too, the system's voice speaks when the Piper voice does not load. `ready` says which:
  `"tts_kind":"piper"|"system"` and `"tts_note"` (`piper en_GB-vctk-medium, p311 (38 of 109)`).
- `--tts-piper DIR --tts-demo OUTDIR [--tts-text "..."] [--tts-speaker p254,p311]`: one WAV per speaker saying
  the line, to choose the bot's voice by ear (`scripts/coop/stt/tts_demo_piper/`, all 109, is not in git).
- Measured through the pipes from Python: 0.5 ms over the classifier's own time per typed line; a 3 s clip
  recognized in about 260 ms; ready in 5 s without speech and 7 to 12 s with it.
- `tools/deploy_brain.ps1 -Target <dir>` writes the folder a game needs: `coop_cli.exe`, `onnxruntime.dll`,
  `sherpa-onnx-c-api.dll`, `bot/` (one bot's `cpp/` files), `stt/` (the Parakeet export): 2.7 GB for bot v54;
  `voice/` (the Piper voice, 90 MB) unless `-Voice ''`.

**In Lyra (UE 5.8).** The first game it runs in: `J:\UE4\Projects\LyraStarterGame58`, `Source/LyraGame/CoopBot/`
(Perforce depot `//OlivaVanilla58`; its own `README.md` is the reference). The client component builds the
world from level markers, the pin and the crosshair, sends each line to this service and turns the reply into
an order RPC; the server's AI controller carries the order out; the pawn and the pins replicate. Checked end
to end with a dedicated server and a client process. On a map without markers the client gives the planner the
crosshair's point under a new id with every line (`gaze_<n>`) and keeps the ones the reply still names
(`last_entity`, `pending_entity`), so a queued order goes where the player pointed then.

## Lines with several orders or with a context (`--chain`, optional, 2026-10-13)

The classifier reads one order in a line that stands by itself. With `--chain DIR` two more models sit in front of
it (`include/coop_intent/rewriter.h`; how they were trained and measured:
[the report](../../reports/Дообучение%20языковой%20модели%20и%20цепочки%20приказов.md)):

```
transcript --router--+--> one complete order ----------------------------------> classifier, slots, places, planner
                     +--> several orders, or leans on the talk
                            --decoder(earlier lines, the bot's line, the line)--> order lines, each one ----^
```

- **The router** is a two-class DeBERTa-v3-small in ONNX Runtime (`router.onnx`, 542 MB). It reads the token ids the
  classifier reads; a line goes on to the decoder from a probability of 0.5.
- **The decoder** is Qwen3-1.7B with its LoRA adapter merged in, as a 4-bit GGUF (`decoder.gguf`, 1,056 MB), run by
  llama.cpp b11429 in this process: on the GPU with the Vulkan build (any vendor's card), or on the CPU with
  `--decoder-cpu`. It is shown the player's last five lines (for 30 s) and the planner's own last words, and writes
  the orders the player gives now as lines that stand by themselves: "smoke the north door then go in" becomes
  "smoke the north door" and "go in through the north door"; "no, the other one" after "breach the north door"
  becomes "Breach the other door." Each of those lines then goes through the classifier, the slots, the place
  matcher and the planner as any line does. A line written back as it is stays the player's own line.
- **Round four, for bot v55** (2026-10-14, `scripts/coop/stt/chains3_v55.py`, decoder `pieces4d_final`): "try again",
  "more", "again" are written back as they are (the classifier reads REPEAT and the game repeats), and so is a negated
  order ("don't follow me": WAIT); a fragment with a pointing word completes the last order ("To this wall." after
  "Start shooting." becomes "Start shooting at this wall.", after "Watch the window." "Watch this wall."); a pointing
  answer to "Which window?" is the asked order there ("on my pin" becomes "Shoot at my pin."). The router sends such
  a fragment on (0.80 for "to this wall"); alone, the decoder writes it back and the classifier reads MOVE_TO.
- **How much it remembers** is `memory_lines` and `memory_seconds` in `chain_config.json`: five lines, 30 seconds.
  Five is the owner's choice of 2026-10-14 (two before it). The v54 decoder was trained with none, one or two earlier
  lines; the v55 decoder with up to five, also in front of the lines whose context is their own. What five cost, on
  the 160 lines of `chain_tests.jsonl`, each asked as it is and again with older lines put in front until there are
  five (`scripts/coop/stt/memory_lines_probe.py`: one draw of older lines, the CPU, nothing labelled, the two answers
  compared with each other, capitals and punctuation aside): with the v55 decoder none of the 54 lines with earlier
  lines of their own changes, and 9 of the 63 the router sends on do, most of them reworded ("clear it out" / "clear
  the room out"), two a line about three targets written as "Frag them."; 36 lines of several orders become 37. The
  v54 decoder: 0 of 54, 4 of 68 (37 lines of several orders became 34). Asking the same prompts in another order
  already changes 3 to 6 of the 160, so the effect is small and its size is not known better than that. The longest
  prompt was 197 tokens of the 1,024. The 30 seconds still apply: at a line every ten seconds the decoder sees three
  earlier lines, not five.
- `scripts/coop/stt/export_chain_cpp.py` writes the folder (`models/coop-chain-v54/cpp/`; for v55 `chains3_v55.py
  export` writes `models/coop-chain-v55/cpp/`): `chain_config.json`, `router.onnx`, `decoder.gguf`,
  `chain_tests.jsonl`. Not in git, like every model file.

```
pwsh tools\setup_llama.ps1                       # once: llama.cpp under third_party\ (headers, DLLs, llama.lib)
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 && cmake --build build --config Release

build\Release\coop_cli.exe --model-dir ..\..\models\coop-deberta-v3-ens3-v55\cpp --chain ..\..\models\coop-chain-v55\cpp --voice
build\Release\coop_cli.exe --model-dir ... --chain ... --world ..\..\scripts\coop\world_example.json    # typed chat
build\Release\coop_cli.exe --model-dir ... --chain ... --chain-tests --decoder-cpu                      # the checks
build\Release\coop_cli.exe --model-dir ... --chain ... --serve                                          # the service
```

Under `/why` the chat shows where the line went (`chain: router 1.00 (10 ms), decoder 41 ms: rewritten`) and each
order line before the bot's reply to it; `/chain` switches the two models off and on. A folder without a router
sends every line to the decoder. Without `--chain`, and in a build that did not find llama.cpp, nothing changes.

**How a line goes through** (`Chat::Hear` in `tools/coop_cli.cpp`). These rules are this file's own: the models
were measured line by line, not in a conversation.

- A line the decoder rewrote is kept, for the lines after it, as the orders it wrote; any other line as the
  classifier read it. A line the bot asked to hear again is not kept. The bot's line the decoder is shown is the
  planner's own (a question, "Got it. ..."), never one of the chat's acknowledgements.
- While the planner's question is open, a line its rules for answers are made for goes to the planner as it is:
  one the classifier takes for yes / no / maybe / don't know or for no order, or cannot read ("the left one",
  "over there"). If the planner then cannot read it (say again) and the decoder read one order in it ("the north
  one" after "Which door?" for "open the door" becomes "Open the north door."), that order goes to the planner
  instead. Any other line takes the usual road.
- *A second look* (2026-10-14): a line the router kept from the decoder, which the planner would answer with "Say
  again?", goes to the decoder after all when there is talk to read it by (the bot's question is open, or the
  player spoke within `memory_seconds`). If the decoder writes something else, its first order line goes to the
  planner and the rest follow as above; `/why` shows "a second look". A fallback for what the router misses: in the
  owner's play of 2026-10-14 "on my pin." after "Which window?" got "Come again?"; the v55 router sends that line on
  itself.
- An order line that makes the planner ask stops the rest of its line. They wait and go through after the line
  that settles that order; a line with several orders replaces them, and so does a line about something else.
- The second and later order lines of a line go to the planner as its further orders (`Planner::Step(...,
  continued)`, next paragraph).
- A decoder that fails on a line (longer than its 1,024-token context) leaves it to the classifier.

**Two rules of the planner for such lines** (`world.h`, `scripts/coop/world.py`, "a line of several orders"; in
both twins, checked against each other):

- *The same place.* A place a further order of the line names as the order before it did, in the same words or
  in fewer, is that order's place: "smoke the door then go in" with two doors asks "Which door?" once, and the
  bot goes in through the door that got the smoke. So with no door marked at all ("I see no door. Where?" -
  "there"), with "the door" after "the door on the right" (not the nearest door), and with "the other door" said
  twice (the same door, not the other of the other). A direction or "here" is not carried over.
- *The other one.* In answer to "Which door? The one ahead, 8 m?", "the other door" (the decoder's wording) and a
  bare "the other one", "no, the other one" (which the classifier takes for nothing, for a no, or for the other
  angle) leave out the door the bot just offered: one door left is the answer, several are what is left to
  choose from. This rule works without the decoder too.

**The service.** With `--chain` the reply's own fields stay the first order's, and it gains `turns` (one object per
order line gone through, in the order to carry them out, each with the reply's fields and `line`) and `chain`
(`route`, `decoded`, `rewritten`, `held`, `resumed`, `note`, the two times). `ready` says which chain is loaded.
The game reads `turns`: its client sends the orders as one list and its server carries them out one after another
(LyraStarterGame58, `Source/LyraGame/CoopBot/README.md`, "Several orders in one line").
`tools/deploy_brain.ps1 -Bot coop-deberta-v3-ens3-v55 -Chain coop-chain-v55` adds the two models and llama.cpp's DLLs
to the game's folder (a chain belongs with its bot: v55's decoder writes lines for v55's labels). Bot v56 runs with the
v55 chain (`-Bot coop-deberta-v3-ens3-v56 -Chain coop-chain-v55`): the router and the decoder read and write text, not
labels, and were not trained again; the v55 decoder learned v55's words for "go back" (then COME_BACK) and has never
seen "let me out", so a line of several orders with them is written as v55 would. Bot v58 runs with the v58 chain
(`-Bot coop-deberta-v3-ens3-v58 -Chain coop-chain-v58`): round five's decoder (`scripts/coop/stt/chains4_v58.py`)
with round four's router, which routed the blind sets and the owner's lines better than the one trained with it.
Since the evening of 2026-10-18 the game runs bot v58 with chain v59 (`-Chain coop-chain-v59`): round six's decoder
(`scripts/coop/stt/chains5_v59.py`: a movement and another order are two orders) with its own router v59, which sends
the owner's "go up by these stairs and ..." lines to the model; chain tests 160/160 (CPU).

**Checked** (`--chain-tests`, 160 lines: single orders, chains, lines with a context, typed and in the form a
transcript has): the decoder's turn text 160/160; the router's probability within 1e-4 of PyTorch on 160/160
(largest difference 1.5e-6); the decoder's answers equal to those of llama.cpp's own server on the CPU on 160/160.
On the GPU 157/160: a GPU rounds another way and a close call falls the other way, so there the count is reported
and not required. The engine's other checks give the same numbers with this build. The v55 chain (2026-10-14):
turn text and token ids 160/160, the router within 1e-4 on 160/160 (largest difference 4.8e-6), the decoder on the
CPU 160/160 (474 ms a line, p95 746).

**Speed and memory** (i9-10900K, RTX 4090, no game running): the router 9 to 12 ms a line (17 to 19 ms as a
service on one thread); the decoder on the CPU with 4 threads 450 ms a line (median 432, p95 750). Both models load
in 2.2 s. The service's working set grows from 2.3 GB to 4.1 GB, plus 1.5 GB of video memory; with the decoder on
the CPU to 4.8 GB.

On the GPU the decoder's time depends on what the card was doing a moment before, and the number to plan with is
not the back-to-back one:

| The card | The decoder, a line of two orders | The whole reply |
|---|---|---|
| has just answered another line (the test file; lines under a second apart) | 30 to 38 ms | 120 to 160 ms |
| has had nothing to do for 2 s or more, and nothing else uses it | 250 to 390 ms | 340 to 490 ms |
| the same, with another process keeping it busy | 57 to 111 ms (182 once) | 170 to 300 ms |

A card left alone for two seconds slows down, and the line that wakes it pays for that: every line of a
conversation at human pace, in a chat on an idle desktop and in the game's headless runs (189 to 349 ms there).
One token put through the model beforehand does not help (it takes 1 ms and the next line is as slow). Next to a
game that draws on the same card the idle penalty is not paid: in the owner's session in Lyra (2026-10-13, 120
spoken lines, the editor's play mode) the decoder took 25 to 107 ms, median 61, for the 23 lines it read, the
router 19 ms and the classifier 59 ms an order.

Traps and limits:
- **A Vulkan build with no layers on the GPU is not the CPU.** With a GPU in its device list llama.cpp still sends
  the prompt's large products there, and the answers are neither the CPU's nor the GPU's (151/160 on the test
  file). `--decoder-cpu` therefore gives the model no device at all.
- The release ships no import library: `setup_llama.ps1` makes `llama.lib` from `llama.dll`'s exports.
- An order "on my go" at the end of a line keeps the place only if the decoder wrote it into that order: "go to
  the north door and breach on my go" came out as "go to the north door" and "breach on my go", and the breach
  then has no place of its own.
- A place settled by a direction or by "here" is not carried over to the next order of the line: there the bot
  asks again.
- The decoder's own misses are in the report: on lines heard through the recognizer it loses most when the
  recognizer changed the key word or the pronoun.

## Speech-to-text (optional)

The voice chain in one process: microphone -> NVIDIA Parakeet TDT 0.6B v2 (sherpa-onnx) -> the bot.
The recognizer, the voices it was measured on and the bots trained on its transcripts are described in
[scripts/coop/stt/README.md](../../scripts/coop/stt/README.md) (in Russian).

```
build\Release\coop_cli.exe --voice --model-dir ..\..\models\coop-deberta-v3-ens3-v53\cpp
                                              # hold SPACE and talk, release to send; typing still works; Esc quits
build\Release\coop_cli.exe --mic-test 3       # is the default microphone the right one, and how loud (no bot)
build\Release\coop_cli.exe --stt-wav clip.wav --model-dir ...    # one 16-bit PCM WAV through recognizer and bot
build\Release\coop_cli.exe --stt-tests LIST WAVDIR EXPECTED      # C++ transcripts against the Python package's
build\Release\coop_cli.exe --speech-text-tests ..\..\scripts\coop\stt\norm_tests.json
```

On macOS the modes and options are the same: `./build/coop_cli --voice --model-dir ../../models/coop-deberta-v3-ens3-v53/cpp`.

- **Setup.** CMake looks for `third_party/sherpa-onnx-1.13.8-win-x64/` and builds without speech when
  it is not there (the directory is not in git). Its three files are the ones the Python package
  carries: after `pip install sherpa-onnx==1.13.8`, copy from `site-packages/sherpa_onnx/`
  `include/sherpa-onnx/c-api/c-api.h` to `include/sherpa-onnx/c-api/`, and `lib/sherpa-onnx-c-api.dll`,
  `lib/sherpa-onnx-c-api.lib` and `lib/onnxruntime.dll` to `lib/`. The model is read from
  `scripts/coop/stt/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` (`--stt-model DIR` for another
  place; the download link is in the stt README). `--stt-threads N` (default 2).
- **Setup on macOS.** The directory is `third_party/sherpa-onnx-1.13.8-osx/`, and the files from the same
  place in the Python package are `include/sherpa-onnx/c-api/c-api.h`, `lib/libsherpa-onnx-c-api.dylib` and
  `lib/libonnxruntime.dylib`. Configure again after copying them (`cmake -S . -B build`). The first run
  with a microphone makes macOS ask whether the terminal may use it; a refusal is reported at start and is
  changed in System Settings > Privacy & Security > Microphone.
- **Two forms of one transcript.** The classifier gets `SpeechTextForClassifier(transcript)`:
  lowercased, the final `.!?` stripped, punctuation inside kept, as in training. `BotBrain::Decide`
  gets the transcript itself: the regex slots and the place matcher read it as the recognizer printed it.
- **Push-to-talk.** The microphone is open while `--voice` runs, so a clip starts 0.2 s before the key
  went down and ends 0.15 s after it came up; nothing else is kept. The key press is read from the
  console (it does nothing while another window has the keyboard). A press shorter than 0.2 s is ignored.
- **The talk key on macOS.** A terminal reports that a key went down and never that it came up. The
  release is read from the keyboard state (`CGEventSourceKeyState`), as `GetAsyncKeyState` gives it on
  Windows. Where macOS does not show that state to the process (a remote terminal, secure keyboard entry),
  the spaces the held key goes on typing stand in for it: the clip ends when they stop, about 0.3 s after
  the release, a press cannot be told from a tap, and the chat says once that it works this way. The
  delays follow the keyboard's repeat settings.
- **One ONNX Runtime per process, and the transcripts depend on which.** `sherpa-onnx-c-api.dll` and the
  engine both import `onnxruntime.dll`, and Windows gives a process one module of that name.
  sherpa-onnx 1.13.8 is built with ONNX Runtime 1.28.2. On that runtime the C++ transcripts equal the
  Python package's clip for clip; on the engine's 1.30.0 the same recognizer hears differently:

  | r6 and cs lines, 602 clips per voice set | transcript equal on 1.28.2 | on 1.30.0 | the bot's pick equal on 1.30.0 |
  |---|---|---|---|
  | Windows voices | 602 | 586 | 602 |
  | Kokoro, English voices | 602 | 571 | 602 |
  | Kokoro, other-language voices | 602 | 544 | 600 |
  | VCTK, speakers used in training | 602 | 481 | 598 |
  | VCTK, speakers never in training | 602 | 468 | 591 |

  The differences are mostly spellings of jargon ("rappelle" / "rappell", "sight" / "site"). On the
  unseen VCTK speakers bot v51 picks the line's own intent on 545 clips from the 1.30 transcripts and
  on 550 from the 1.28.2 ones. The bots were trained and measured on the 1.28.2 transcripts, so with
  speech-to-text the build puts sherpa-onnx's `onnxruntime.dll` next to the exe and the bot runs on it
  too: every check of the table below passes on it as well (golden: 1750/1750, 1259/1259 and 762/762,
  within 3.1e-6; 39.7 ms per line). Without `lib/onnxruntime.dll` in the sherpa-onnx directory the
  build keeps 1.30.0 and says so.
- **On macOS the process holds both runtimes.** A library is loaded there by its path, so
  `libsherpa-onnx-c-api.dylib` takes the `libonnxruntime.dylib` next to it (1.28.2, as on Windows) and the
  bot stays on the engine's 1.30.0: the bot's checks do not depend on whether speech is built in. The
  engine's directory also holds a file called `libonnxruntime.dylib`, so the build puts sherpa-onnx's
  directory first in the search path, and the line `speech: ... on ONNX Runtime 1.28.2` prints the runtime
  the recognizer was really given. Forced onto 1.30.0, the recognizer heard 21 of 482 clips differently
  on the Mac as well (the bot's pick changed on 2).
- **Checked** (2026-10-09, Windows, bot v51, 2 threads):
  - transcripts against the Python package's on every voiced set of lines: 3010 clips (the table), all
    equal on 1.28.2 (the seed-command clips were compared on 1.30.0 only: 2991 of 3204 equal there);
  - `SpeechTextForClassifier` against the Python `norm`: 4183/4183 lines
    (`scripts/coop/stt/export_norm_tests.py` writes the file);
  - a clip from file to reply ("Turn around and look behind us..." -> LOOK_AT, `dir=back`);
  - the microphone: opens the default device, 2.00 s asked gives 2.38 s (0.20 s before, 0.15 s after),
    silence gives no text.
  - **The push-to-talk loop and real speech: the owner's tests only** (2026-10-09: 43 utterances with
    bot v51, then bot v52; recognizer and chat worked; what the bots misread led to v52 and v53). Every number above is on
    synthesized voices.
- **Checked on macOS** (2026-10-09, MacBook Pro M5 Pro, macOS 26.5, Terminal, bot v53, 2 threads):
  - transcripts against the Python package's on the same Mac: 482 clips, the 422 + 60 lines of
    `lines.json` and `lines_v53.json` read by four voices of macOS (`say`), all equal
    (`scripts/coop/stt/cpp_stt_parity_macos.log`). The clips of the Windows study are not on the Mac, so
    **the Mac's transcripts have not been compared with the ones the bots were trained on**: copy a
    `wav_*` directory over and run `--stt-tests` with its `out_parakeet-*.json`;
  - `SpeechTextForClassifier`: 4183/4183; the v53, v3 and v2 bots: every check of the table below;
  - the microphone: opens the default device after macOS's question, 2.00 s asked gives 2.32-2.40 s, the
    room's noise at -58 dBFS, and a sentence played from the laptop's own speakers comes back word for word;
  - the chat in a pseudo-terminal, SPACE "held" the way a terminal shows it (its auto-repeat) while the
    speakers talk: three orders heard and carried out; typed lines, backspace, arrow keys, Esc, Ctrl-C and
    Ctrl-D, with the terminal's settings back afterwards; the capture under the thread and address sanitizers.
  - **Not checked: a finger on the key.** The keyboard state can only be read with a real key down, so the
    first way of the two above waits for the owner's test.
- **Cost.** About 0.69 GB of RAM for the recognizer and 2.2 s to load it; a clip of 2.5-3 s is
  recognized in about 230 ms on 2 threads (p95 about 330 ms), then the bot's 40 ms. Waiting costs nothing:
  0.000 cores with the bot loaded and 0.006 with the recognizer loaded and the microphone open.
  On the M5 Pro: 1.76 GB for the recognizer (the Python package takes about as much there; the bot takes 2.3 GB)
  and about 1 s to load it; a clip of 2.6 s in 88 ms (p95 135 ms), then the bot's 13 ms; 0.007 cores waiting.
- **Not there yet.** A microphone on Linux (`--stt-wav` works wherever sherpa-onnx is found: put the
  platform's files under `third_party/sherpa-onnx-1.13.8-linux`); a choice of input
  device and of the talk key; noise handling; hot words for the game's jargon.

## What was checked

On Windows. The v2, v31, v3 and v1 columns are rule set v3 (2026-10-04) and were re-run unchanged with
the engine that also knows rule sets v4 and v5 (2026-10-10: the same numbers, their files untouched). The
v51 and v52 columns are rule set v4 (2026-10-09; v51's place records were written again after the rule for
"cover my front" was added). The v53 column is rule set v5 since 2026-10-10; under rule set v4 it had
35889/35889 place records. The v3 bot's weights exist only on the Mac, so its two checks
through the model are run there (2026-10-10, with this engine: 1062/1062 and 77/77); its other test files
were refreshed on Windows with `gen_tests.py --no-model`.

On macOS arm64 the v53, v3 and v2 columns were run again on 2026-10-10, with this engine in the build
with speech-to-text: the same counts, except that libc++'s `std::regex` compares the regex slots on every
line (10444, 9231 and 8931); golden within 1.5e-6, 1.8e-6 and 2.9e-6.

| check | v2 bot | v31 bot (default) | v3 bot | v1 bot | v51 bot | v52 bot | v53 bot |
|---|---|---|---|---|---|---|---|
| token ids and probabilities vs PyTorch, golden lines | 762/762, max difference 3.3e-6 | 1259/1259, 2.2e-6 | needs the weights | 754/754, 3.1e-6 | 1750/1750, 1.8e-6 | 2019/2019, 1.9e-6 | 2275/2275, 1.3e-6 |
| normalizer / token ids | 8931/8931 | 9428/9428 | 9231/9231 | 8923/8923 | 9919/9919 | 10188/10188 | 10444/10444 |
| regex slots (+ 4 lines past std::regex's limit, see below) | 8927/8927 | 9424/9424 | 9227/9227 | 8919/8919 | 9915/9915 | 10184/10184 | 10440/10440 |
| place records (targets, directions, roles, flags, primary) | 20201/20201 | 20204/20204 | 20197/20197 | no vocabulary | 35454/35454, 9762 of them with a direction | 35623/35623, 9789 with a direction | 50429/50429, 14629 with a direction, 13901 with a pointer |
| conversation through the models | 77/77 | 77/77 | needs the weights | 66/66 | 77/77 | 77/77 | 77/77 |
| both gates on the golden probabilities, exact ties, the top label outside the top-mass family, random rows | 2338/2338 | 3332/3332 | 2938/2938 | 2322/2322 | 4314/4314 | 4852/4852 | 5364/5364 |
| decision steps, both gates (2 of them built in: NaN probabilities are asked again) | 140/140 | 140/140 | 140/140 | 40/40 | 190/190 | 190/190 | 190/190 |

- The place lines: the tokenizer's adversarial lines, the developer's regression lines, the blind v3
  lines, the location seeds of the seed sets, and generated lines: 12000 random sequences of
  vocabulary phrases, rule words and punctuation (some longer than the 128-word cap) and, for rule
  set v4, 16000 lines built from about 100 clause patterns of the direction rules, a third of them
  one edit away from their pattern, and for rule set v5 another 16000 lines in which 108 pointer
  patterns stand among the direction patterns, plus 65 written out. A record carries `"direction"` and
  `"pointer"`; a stored record without a key reads as none (the older bots' files).
- The answer action has no trained bot yet. A scratch bot with the 41 labels of v54 gives 244/244
  decision steps: an answer with nothing queued, with an order queued (it stays queued and executes on
  the next go), with the signal slot (not queued), under the threshold, and behind a leading negation
  ("don't know", "never": the answers are safe intents).
- The decision steps cover every branch (negated, say again, ignore, execute, go, wait, queued, act,
  "other", the threshold boundary in float32 and as a family sum) and the queue case by case: what a
  queued order keeps (its places, its "other" slot), and what drops, replaces or leaves it. A bot
  with a HOLD_FIRE label gets 25 more steps per gate (HOLD_FIRE under and over the threshold, with
  and without the signal slot, with an order already queued, "don't shoot" past the negation guard,
  GO_NOW firing the queued OPEN_FIRE); each of ten single-line mutants of that branch fails them.
  `gen_tests.py BOT_DIR --decide-only` writes just this file and needs only `bot_config.json`.
- The C++ twin of rule set v4 was also run with the v3 vocabulary over the 35,023 lines of a v4-rules
  test file against records from `scripts/coop/rules/v3/locations.py`: equal on all of them.
- The planner (world.h): 906 scenarios per bot since 2026-10-13, 8508 steps on the v53 bot and 8253 on the
  v54 bot and its three students (actions act, ask, answer, resolved, queued, execute, go, wait, negated, say
  again, ignore; groundings by pin, gaze, memory, zone, direction, the only one, the nearest, ambiguous by
  distance or by an unknown modifier, missing), plus 11 worlds the rules refuse and the example world they
  accept: all equal. The last 302 scenarios are lines of several orders (`gen_world_tests.py`, `chain_scenario`,
  with a random generator of its own, so the 604 before them are what they were): on the v54 bot 712 further
  orders of a line, 277 of them given the place of the order before them, and "the other" in answer to
  "Which ...?" 125 times. Each of eleven one-line mutants of the two new rules fails them.

The tokenizer lines are the golden lines plus lines generated to break a port:
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

Three models, measured with the v3 ensemble trained on the work machine (CUDA; the same size and
architecture as the bots in the repository, its files are not in it):

| members | intra-op threads per model | threads in all | median | p99 |
|---|---|---|---|---|
| one thread each | 4 | 12 | 35.4 ms | 43.7 ms |
| one thread each | 2 | 6 | 33.3 ms | 42.1 ms |
| one thread each | 1 | 3 | 39.4 ms | 54.0 ms |
| in turn | 4 | 4 | 57.0 ms | 74.7 ms |
| in turn | 2 | 2 | 63.1 ms | 90.7 ms |
| in turn | 1 | 1 | 87.0 ms | 140.6 ms |

- Load: 4.5 s; working set 2.3 GB.
- Tokenizer: ~20 µs per line. Place matcher (rule set v3): 2 µs per line, p99 8 µs; it reads the
  last 128 words of a line.
- `--no-spin` (idle threads sleep, which a game wants) cost nothing measurable: 34.7 ms median at 4
  threads per model.
- The v31 bot: 40.8 ms with one thread per model, 56.4 ms in turn with 4 threads (its `bench.txt`).
- The v2 bot gives the same latencies: 39.7 ms with one thread per model and 56.8 ms in turn
  with 4 threads (re-measured 2026-10-04, appended to its `bench.txt`). The first block of that file
  is an earlier run that was 35–55% slower, for a reason not identified.

The CPU has 10 cores and 20 hardware threads, so 12 threads do not get 12 cores. For a game, one
thread per member is the natural setting: 3 cores for ~40 ms.

One v1 model for comparison: 25.7 ms at 4 threads, 39.6 ms at 1 thread; 0.8 GB, loaded in 2.0 s.
The raw outputs are in `bench.txt` next to each bot's `intent_config.json`.

- Plain dynamic int8 quantization (`quantize_dynamic`, QInt8) broke the v1 model when the first export
  was checked: 85 of the 592 golden lines of that time kept their argmax. So none is used.
- deberta-v3-large was measured as an alternative and dropped. At the fixed recipe, one seed collapsed
  on two of three folds, and the models that trained were not better than base.

## Porting to UE5 (plan)

**What was done instead (2026-10-10):** the engine did NOT move into the game process. The game starts
`coop_cli --serve` (section "The bot as a service for a game") and keeps only game code: the world state, the
order, the bot's controller. The reason is the last bullet below, "Speech": one process cannot hold the
recognizer's ONNX Runtime and the engine's. The notes below stay as the plan for an in-process port (the
classifier on NNE, the recognizer in a statically linked module); `world.h` is already what the game would feed.

- **Core files:** the five core pairs above plus `unicode_tables.inc` go into a runtime module. The
  only exceptions they rely on are `std::regex`'s: its constructor, and `regex_search`, which throws
  `error_stack` past the recursion limit above (`SlotPatterns` catches it and counts the slot as
  absent). A no-exceptions UE build therefore has to replace `SlotPatterns` (see Regexes).
  `locations.cpp` uses neither regex nor Unicode tables, throws nothing, and ports as is.
- **Places:** `Decision::places` is the record for the planner.
  - Rule set v4: `PlaceTarget::direction` (`PlaceDirectionName`: up, down, left, right, forward,
    back). It is either an object's direction ("the left window", "up the blue stairs", "the door
    behind you") or a target of its own with object, qualifier and zone all -1 ("go left"). The
    primary may be such a direction-only target: check for it before resolving a place. A UE loader
    has to fill `has_directions`, `directions` and `Object::vertical` and make `Init`'s checks.
  - Give the level's actors tags that mirror the vocabulary ids (`Place.Door.North`,
    `Place.Stairs.Blue`, `Zone.Basement`) and resolve the primary target against them.
  - One match: take it. Several (chairs, the same door on two floors): the bot's floor, then the
    nearest, or the ping marker.
  - A target with a role (`mine`, `them`, `from`, `not`, `status`) is not a destination; `them`
    targets are contacts for the blackboard.
  - **Check the primary's role.** The primary is the first target without a role; when every target
    has one, it is the first target and the line gives no destination ("get off the roof": the place
    to leave). Then use the marker, or the intent alone.
  - `unknown_modifier`: do not fall back to the nearest one; use the marker or ask "which one?".
  - `other`: the other object of that kind, not the nearest.
  - `unsure`: low confidence, not "no place": most such names are real places.
  - `up` / `down` / `floor_2` are resolved per map.
  - On Execute, use `Decision::executed`, `executed_places` and `executed_other` (the queued order,
    its places and its "other" slot), not the GO line's.
  - `LocationMatcher::Init` and `coop_cli`'s loader refuse a malformed vocabulary (an unknown or
    missing word list or section, a duplicate key). A UE loader built on `FJsonSerializer` has to
    make the same checks: `scripts/coop/locations.py validate()` is the reference.
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
- **Speech:** `speech.h` moves as is; `sherpa_speech.cpp` needs sherpa-onnx as a third-party library, and
  the runtime question from "Speech-to-text" comes back: NNE embeds its own ONNX Runtime, and a second
  `onnxruntime.dll` cannot be loaded under the same name. Either build sherpa-onnx statically with its
  runtime into its own module, or run it on the engine's runtime -- and then regenerate the training
  transcripts with that exact binary and retrain (28 minutes), because the recognizer's output depends
  on the runtime. Feed it the game's own capture (16 kHz mono float), keep the 0.2 s before the key.
- **Game integration:** labels become GameplayTags; the game voices the reply lines itself (the CLI's
  lines are a demo). TAKE_COVER and OPEN carry no target; the planner picks the cover spot or the door
  (the marker, or the nearest one).

## Regenerating

After training (`COOP_TAG` selects the data and the seed set; under `v31`, `train_v2.py final`
writes `models/coop-deberta-v3-ens3-v31`; HANDOFF.md, section 5, has the whole sequence):
```
COOP_TAG=v31 python scripts/coop/train_v2.py final ens3                # three models + bot_config.json
python scripts/coop/export_cpp.py models/coop-deberta-v3-ens3-v31      # ONNX, vocab.tsv, intent_config.json, golden.jsonl
python scripts/coop/check_onnx.py models/coop-deberta-v3-ens3-v31      # ONNX Runtime vs PyTorch, before any C++
python cpp/coop_intent/tools/gen_tests.py models/coop-deberta-v3-ens3-v31   # tokenizer, place, dialogue, gate and decide tests
```
`export_cpp.py` reads the tag from the bot's `bot_config.json`, so the golden lines are those of the
study the bot was trained in.

After changing only the map vocabulary (`scripts/coop/locations.json`), the rules or the regexes, no
training and no ONNX export are needed. For a bot directory (this also moves a bot exported under
rule set v3 to rule set v4: its place records and its `location_tests.jsonl` change):
```
python scripts/coop/locations.py --dev                             # the developer's regression lines
python scripts/coop/export_cpp.py models/<bot> --config-only
python cpp/coop_intent/tools/gen_tests.py models/<bot>             # --no-model on a machine without the bot's weights
```
Run `tools/gen_unicode_tables.py` only when the `tokenizers` version changes. It checks its tables
against `tokenizers` on 1.3M strings.

## Known model behaviour (not the port)

The model saw only English:
- «прикрой меня» → REVIVE_ME 0.92 → acts (v1 bot);
- "prikroy" → FRAG 0.97 → acts (v1 bot).

The threshold does not catch this, so the game should filter non-English lines or train on them.
