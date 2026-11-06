# DeBertaBot

A voice-controlled AI teammate for co-op games that runs on the player's own PC.
You talk to it like a friend in your squad.
It understands, answers in its own voice and does what you said.

It was inspired by [PUBG Ally](https://www.youtube.com/watch?v=OdtFL1CDDwc).
One person built it on weekends, vibecoding with AI coding agents run in a Ralph loop.
This repository holds the bot's brain: a C++17 program (`coop_cli`) and the Python scripts that train and test its models.
The game that uses it (Lyra, Unreal Engine 5.8) is in a separate Perforce project and is not here.

## Features

What works today. The numbers come from the section [Measured results](#measured-results).

- **Local, no cloud.** Speech recognition, understanding, memory and the bot's voice all run on the player's machine.
  No account, no internet, no cloud service.
- **Push-to-talk or open mic.** With the open mic, the bot listens only when you call it by its name.
  After its answer, it listens for 8 more seconds without the name.
  A voice activity detector (Silero VAD) cuts speech out of silence.
- **Three languages: English, Russian, Spanish.** In and out: speech, orders, the bot's replies and its voice.
- **71 kinds of lines:** 58 orders, 8 kinds of talk and questions, 4 answers (yes, no, maybe, I don't know), and "not for me".
  - Several orders in one sentence: "Take this box and put it on the yellow bed."
  - Orders on a signal or a timer: "When I say go, open the door.", "In five seconds, jump."
  - New orders while it is busy: they queue or replace the current one. "What are you doing?" gets an answer.
  - Places by object, colour, side, floor, direction, your crosshair or a map pin.
    "It" is the last thing you talked about. Rooms are known by their doors.
    When a place is not clear, the bot asks ("Which window?").
  - Objects: carry, put on top of something, push, roll, open and close doors.
    It climbs and jumps onto, over and down from things, and uses a box as a step.
  - Names: you can give the bot a name and tell it yours.
  - Questions: "What do you see?", "What are you doing?", "Are you hurt?", "How's it going?"
- **Level labels.** A level designer puts labels on objects and markers on places.
  The bot uses them in orders and in its answers ("What do you see?").
- **About 92% of real spoken lines understood.** On 977 English lines that the developer said in the game, as the speech recognizer heard them,
  the classifier gives the right intent 91.7% of the time.
  When it is not sure, it asks you to say it again (4.8%). When it acts, it is right 96% of the time.
- **Fast.** From the end of your speech to the start of the bot's voice, in the game: about 0.6 s typical, under 1 s for 95% of the lines
  (Russian, the language model on the GPU).
  On the CPU only: 0.3 s to 0.7 s in English and 1.0 s to 2.7 s in Russian.
- **Teachable in the game, by voice, with a memory that stays.** You can teach it:
  - names of things ("This is the workbench."), colours, and rooms;
  - what your words mean ("When I say X, it means Y.", "A is the same as B.", "I meant ...");
  - how to say words, what to say instead of its own phrases, and how fast to speak;
  - how to behave ("Keep three metres from me.", "Fire only on my command.");
  - to forget any of it ("Forget ...").

  The memory is one file per player. It stays after a restart.
- **CPU and GPU, part by part.** The language model and the voice can each run on the GPU or on the CPU.
  Each part has its own number of threads.
- **Small footprint.** About 5 GB of RAM and 1.5 GB of video memory with the language model on the GPU.
  About 5.6 GB of RAM and no video memory on the CPU only.
- **The brain does not depend on the game engine.** It is a separate process.
  The game sends one JSON line per spoken line, with a short description of the world.
  The brain sends back orders with places and the reply.
- **Goal planning (GOAP-style, in the game).** The bot finds a way to do an order:
  through doors and switches, by jumping, or by moving a box to climb on.
  When there is no way, it says why ("The door's shut; the switch is 2 m from it.").
- **Voices and personas.** One voice per language, and a "bro" persona with its own lines and voice.

## Not done yet

- **Emotions.** The bot does not hear emotion in your voice and does not speak with emotion.
- **Crafting.** No crafting orders.
- **Farming and building.** The brain understands 10 such orders (plant, water, harvest, till, feed, build, repair, demolish, collect, deliver).
  It refuses things that are not in the build menu.
  In the game, only collect and deliver (carrying things) work. The other orders get "No farming or building on this map yet."
- **Fighting on its own.** The bot fights on your orders (fire, hold fire, suppress, attack, melee, take cover).
  Combat goals that the bot chooses itself are the next phase of the planner.
- **Noise and echo.** No noise suppression and no echo cancellation. Use headphones with the open mic.
- **Self-training.** The bot does not retrain itself while you play.
  Your play logs can be turned into new training data with the scripts here. Training is a separate step that needs a GPU and a few hours.
- **Other engines.** The protocol does not depend on the engine, but the only integration is for Unreal Engine 5 (Lyra), and it is not in this repository.
- **Model weights.** They are not published (see [Get the model weights](#get-the-model-weights)).
- **Test data.** Real speech comes from one speaker, the developer, with an accent. The rest is synthetic voices and lines written by AI authors.
- **Platforms.** Built and checked on Windows x64. An earlier version was built on macOS arm64. Linux is not tested.

## Status (2026-11-06)

| Part | Version | Note |
|---|---|---|
| Classifier | bot v67 | 71 labels, ensemble of three DeBERTa-v3-base models, gate 0.66 |
| Router and decoder | chain v69s5 | DeBERTa-v3-small router, Qwen3-1.7B decoder (QLoRA, Q4_K_M in llama.cpp) |
| Speech to text | Parakeet TDT 0.6B v2 (English), v3 (Russian, Spanish), int8 | through sherpa-onnx |
| Voice activity | Silero VAD v5 | open mic only |
| Voices | Piper and Kokoro | through sherpa-onnx, sentence by sentence |
| Memory | Wick (C++20, Apache 2.0) | one file per player, no embeddings |
| Game | Lyra, Unreal Engine 5.8 | in a separate Perforce project, not in this repository |

## How the brain works

The brain does these steps for each line that the player speaks:

1. **Microphone.** Push-to-talk, or the open mic with the voice activity detector and the bot's name.
2. **Speech to text.** Parakeet TDT changes the audio into text.
3. **Memory.** If the player taught the bot this line or a pattern like it, the taught meaning is used.
   Lessons ("This is the workbench.", "Forget ...") are read here too.
4. **Router.** For English, a small classifier finds lines that need the decoder:
   lines with two or more orders, and lines that refer to earlier lines.
   Russian and Spanish lines always go to the decoder.
5. **Decoder.** A language model writes each order as a separate English line.
   It uses the last five lines that the player spoke in the last 30 seconds, and a scene line
   (what the bot holds, what it stands on, the last thing named).
   Example: "Get to the car." and then "Get inside of it." becomes "Get in the car."
6. **Classifier.** Three DeBERTa-v3-base models give the intent of each order.
   If the models are not sure, the bot asks the player to say the order again.
7. **Place matcher.** Rules find the places in the order: an object, a side or a colour, a floor, a direction, a pin, a time.
8. **Planner.** The planner compares the places with the world state that the game sends.
   If a place is not clear, the bot asks a question (for example, "Which window?").
9. **Reply.** The reply is an English sentence from a catalogue.
   Reply tables give it in Russian or Spanish, and in the words of the persona.
10. **Voice.** Piper or Kokoro changes the reply into audio, one sentence at a time.
    The game plays the audio from the bot's head.

Then the game carries out the orders: it walks the navmesh, opens doors, jumps, carries things and fights.

The Python scripts have a copy (a "twin") of each C++ part.
The engine checks compare the C++ result with the Python result, line by line.

## Measured results

Machine: Intel i9-10900K, NVIDIA RTX 4090, Windows 10. Measured 2026-11-05 and 2026-11-06.

**Understanding.** Classifier v67 on the developer's own English lines from the game, as the speech recognizer heard them.
Each line was read by models that were not trained on it (out of fold, three seeds).

| Set | Lines | Right intent | Asks again | Right when it acts |
|---|---|---|---|---|
| Each time a line was said | 977 | 91.7% | 4.8% | 96.3% |
| Each different line once | 578 | 87.4% | 8.0% | 94.9% |

The decoder v69s5 on 47 lines that earlier versions misread (none of them a training row): 44 of 47 right,
precision 98%, recall 95% (v68s2: 18 of 47).

**Speed in the game.** The developer's spoken Russian lines of 2026-11-04 and 11-05 (335 lines), with decoder v69s5 on the GPU;
the speech to text, the classifier and the voice (mostly the persona's) on the CPU.
From the end of the speech to the start of the bot's voice or action:

| P50 | P90 | P95 | P99 | Max | Under 1 s | Under 1.5 s |
|---|---|---|---|---|---|---|
| 626 ms | 848 ms | 980 ms | 1653 ms | 3138 ms | 95.2% | 98.5% |

The brain's own part (speech to text, decoder, classifier, planner) was 297 ms typical and under 1.5 s for every line.

**Speed by language and device.** The brain as the game starts it, 40 recorded lines of synthetic voices for each row,
the game editor open on the same machine.
From the end of the clip to the first audio of the bot's voice:

| Language | Decoder on | P50 | P95 | Max |
|---|---|---|---|---|
| English | GPU | 379 ms | 639 ms | 724 ms |
| English | CPU | 486 ms | 624 ms | 686 ms |
| Russian | GPU | 675 ms | 992 ms | 1149 ms |
| Russian | CPU | 1850 ms | 2531 ms | 2739 ms |

English is fast on the CPU because most English lines do not need the decoder.
Every Russian and Spanish line goes through the decoder.

**Parts, one line:**

| Part | Time |
|---|---|
| Speech to text (2 threads) | approximately 0.09 × the length of the audio; 173 ms typical in the game |
| Classifier | 35 ms to 120 ms per order |
| Router | 11 ms to 16 ms |
| Decoder on the GPU | 30 ms to 100 ms |
| Decoder on the CPU (4 threads) | 0.5 s to 1.5 s |
| Voice, first sentence | approximately 75 ms (Piper medium voices), 300 ms (the persona's high-quality voice) |

**Memory** (the brain as the game starts it: Russian, the persona, the voice, the open mic):

| Decoder on | RAM (working set) | Video memory |
|---|---|---|
| GPU | 4.7 GB to 5.1 GB | 1.5 GB |
| CPU | 5.6 GB to 5.7 GB | none |

The scripts that make these numbers:

- `scripts/coop/stt/score_owner_oof.py`: understanding (the classifier).
- `scripts/coop/stt/chains2/ml_v69/measure_v69_owner.py`: the decoder on the misread lines.
- `scripts/coop/measure_game_latency.py`: speed in the game, from the game's logs.
- `scripts/coop/measure_brain_cost.py`: speed by language and device, and memory.

[COOP-BOT.md](COOP-BOT.md) gives all the results, the methods and the known problems, version by version.

## What runs inside

| Part | Model | Licence |
|---|---|---|
| Classifier | `microsoft/deberta-v3-base`, fine-tuned | MIT |
| Router | `microsoft/deberta-v3-small`, fine-tuned | MIT |
| Decoder | `Qwen/Qwen3-1.7B` with a QLoRA adapter | Apache 2.0 |
| Speech to text | NVIDIA Parakeet TDT 0.6B v2 and v3 | CC BY 4.0 |
| Voice activity | Silero VAD v5 | MIT |
| Voices | Piper `en_GB-vctk-medium` (CC BY 4.0), `ru_RU-denis-medium` (CC0), `es_MX-ald-medium` (Unlicense), `kk_KZ-issai-high` (CC BY 4.0, the persona); Kokoro v1.0 (Apache 2.0) | as listed |
| Runtimes | ONNX Runtime (MIT), sherpa-onnx (Apache 2.0), llama.cpp (MIT), Wick (Apache 2.0) | as listed |

No part has a non-commercial licence.
Read the model card of each model before you use or distribute it.

## Repository layout

| Path | Contents |
|---|---|
| `cpp/coop_intent/` | The C++17 engine and `coop_cli`: chat, engine checks, service mode for a game |
| `scripts/coop/` | Python: label specifications, training data, the bot, the place matcher (`locations.py`), the planner (`world.py`), memory tests |
| `scripts/coop/stt/` | The voice chain: synthesized voices, transcripts, classifier builds, decoder and router rounds |
| `scripts/coop/replies/` | The reply catalogue and the reply tables (Russian, Spanish, the persona) |
| `models/` | Model configurations, engine test files and training records. The model weights are not in git |
| [COOP-BOT.md](COOP-BOT.md) | The full study, version by version (English) |
| [HANDOFF.md](HANDOFF.md) | The current state and the work procedures (Russian) |
| [DEBERTA-BOT.md](DEBERTA-BOT.md) | A walkthrough of how the classifier was made (Russian) |
| [cpp/coop_intent/README.md](cpp/coop_intent/README.md) | The engine: layout, build, service protocol, checks |
| `reports/`, `research_notes/` | Research reports (Russian) |

## Build the engine (Windows)

You need:

- Visual Studio 2022 Build Tools and CMake.
- The ONNX Runtime 1.30 release for Windows x64 in `cpp/coop_intent/third_party/`.
- For speech to text, the open mic and the voice (optional): the sherpa-onnx C API in `cpp/coop_intent/third_party/`.
- For the decoder (optional): llama.cpp. Run `cpp/coop_intent/tools/setup_llama.ps1` to install it in `third_party/`.
- For the memory (optional): Wick next to this repository (CMake option `WICK_DIR`).

[cpp/coop_intent/README.md](cpp/coop_intent/README.md) gives the exact versions and folders.

Do these steps in `cpp/coop_intent`:

```
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
```

## Get the model weights

The weights are not in git and are not published.
Each classifier member is a 739 MB ONNX file.
The decoder is a 1.1 GB GGUF file.

Use one of these procedures:

- Copy the weights from the work machine. [HANDOFF.md](HANDOFF.md), section 1, gives the files and the folders.
- Train the models again with the scripts. The section [Train a new version](#train-a-new-version) gives the scripts.

The base models come from Hugging Face: `microsoft/deberta-v3-base`, `microsoft/deberta-v3-small`, `Qwen/Qwen3-1.7B`.
The speech models, the voice activity detector and the voices come from the sherpa-onnx releases.

## Run the brain

Start a chat in the terminal with bot v67:

```
build\Release\coop_cli.exe --model-dir ..\..\models\coop-deberta-v3-ens3-v67\cpp
```

Add the router and the decoder:

```
build\Release\coop_cli.exe --model-dir ..\..\models\coop-deberta-v3-ens3-v67\cpp --chain ..\..\models\coop-chain-v69s5\cpp
```

Add `--decoder-cpu` to keep the decoder off the GPU, and `--language ru` or `--language es` for Russian or Spanish.

Run the engine checks. Each check compares the C++ engine with the Python twin:

```
build\Release\coop_cli.exe --model-dir <bot cpp dir> --golden
build\Release\coop_cli.exe --model-dir <bot cpp dir> --tokenizer-tests
build\Release\coop_cli.exe --model-dir <bot cpp dir> --location-tests
build\Release\coop_cli.exe --model-dir <bot cpp dir> --gate-tests
build\Release\coop_cli.exe --model-dir <bot cpp dir> --decide-tests
build\Release\coop_cli.exe --model-dir <bot cpp dir> --dialogue
build\Release\coop_cli.exe --model-dir <bot cpp dir> --world-tests
build\Release\coop_cli.exe --model-dir <bot cpp dir> --chain <chain cpp dir> --chain-tests --decoder-cpu
```

Check the memory and the teaching:

```
python scripts/coop/memory_checks.py --quick
```

All checks must pass.

### Use the brain in a game

1. Copy the brain into the game folder:
   ```
   pwsh cpp/coop_intent/tools/deploy_brain.ps1 -Target <game>\Binaries\CoopBrain -Bot coop-deberta-v3-ens3-v67 -Chain coop-chain-v69s5
   ```
2. Start `coop_cli.exe --serve` from the game.
3. Send one JSON command per line on stdin. Read one JSON event per line on stdout.

[cpp/coop_intent/README.md](cpp/coop_intent/README.md), section "The bot as a service for a game", gives the protocol.

## Train a new version

Use a Python environment with PyTorch and CUDA.
The speech tools use their own environment in `scripts/coop/stt/venv`.

To train a classifier (example: v67):

1. Run `scripts/coop/make_spec_v67.py`. It writes the label specification and the seed commands.
2. Run `scripts/coop/stt/export_v67.py seeds`. It writes the list of the new seed commands.
3. Run `scripts/coop/stt/synth_v67.py seeds` and `synth_windows_v67.ps1 seeds`. They make the audio of the new seed commands.
4. Run `scripts/coop/stt/run_build_v67.ps1`. It trains three out-of-fold runs and three final models.
5. Run `scripts/coop/stt/ensemble_bot_v67.py`. It sets the gate, exports the ONNX files and writes the engine test files.
6. Run the engine checks.

To train the decoder (example: v69):

1. Write the new training rows in `scripts/coop/stt/chains2/ml_v69/make_rows_v69.py`.
   They come from the lines that the bot misread in the game.
2. Run `scripts/coop/stt/run_chains13_v69.ps1`. It trains, makes the GGUF file and exports the chain.
3. Run the chain checks (`--chain-tests`), the memory checks and the measurements in `scripts/coop/stt/chains2/ml_v69/`.

## Rules for changes

- Do not put model weights in git.
- If you change a Python twin, change the C++ twin also. All engine checks must pass.
- Do not make a tolerance larger to make a check pass.
- Do not train on a test set. The developer's real lines are test sets only.
- Use no model or voice with a non-commercial licence.

## Licence

The code in this repository has the Apache License 2.0 ([LICENSE](LICENSE)).
Each model has its own licence (see [What runs inside](#what-runs-inside)).
