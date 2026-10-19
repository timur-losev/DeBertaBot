# DeBertaBot

DeBertaBot is the brain of a voice-controlled AI teammate for a co-op shooter.
The player speaks an order.
The brain changes the speech into one or more orders that the game can do.
Each order has an intent (for example, MOVE_TO or OPEN_FIRE) and a place on the map.

The brain is a C++17 program (`coop_cli`).
The game starts it as a helper process and sends it JSON lines.
The models are trained and tested with the Python scripts in this repository.

## Status (2026-10-19)

| Part | Version | Note |
|---|---|---|
| Classifier | bot v58 | 47 intents, ensemble of three DeBERTa-v3-base models |
| Router and decoder | chain v59 | DeBERTa-v3-small router, Qwen3-1.7B decoder |
| Speech to text | Parakeet TDT 0.6B v2 (int8) | through sherpa-onnx |
| Voice | Piper, `en_GB-vctk-medium` | through sherpa-onnx |
| Game | Lyra, Unreal Engine 5.8 | in a separate Perforce project, not in this repository |

The engine is built and checked on Windows x64.
An earlier version of the engine was also built on macOS arm64.
The Linux build is not tested.

## How the brain works

The brain does these steps for each line that the player speaks:

1. **Speech to text.** Parakeet TDT changes the audio into text.
2. **Router.** A small classifier finds lines that need the decoder.
   These are lines with two or more orders, and lines that refer to earlier lines.
3. **Decoder.** A language model writes each order as a separate line.
   It uses the last five lines that the player spoke in the last 30 seconds.
   Example: "Get to the car." and then "Get inside of it." becomes "Get in the car."
4. **Classifier.** Three DeBERTa-v3-base models give the intent of each order.
   If the models are not sure, the bot asks the player to say the order again.
5. **Place matcher.** Rules find the places in the order: an object, a side or a colour, a floor, a direction, a pin.
6. **Planner.** The planner compares the places with the world state that the game sends.
   If a place is not clear, the bot asks a question (for example, "Which window?").
7. **Voice.** Piper changes the bot's reply into audio.
   The game plays the audio from the bot's head.

The Python scripts have a copy (a "twin") of each C++ part.
The engine checks compare the C++ result with the Python result, line by line.

## Measured results

Machine: Intel i9-10900K, NVIDIA RTX 4090.

| Item | Result |
|---|---|
| From the release of the talk key to the bot's voice, in the game | median 557 ms, 90th percentile 775 ms (572 spoken lines) |
| Speech to text | approximately 0.09 × the length of the audio (2.4 s of speech in 212 ms) |
| Classifier | 35 ms to 50 ms per order (one thread per model) |
| Router | 11 ms to 16 ms |
| Decoder on the GPU | approximately 30 ms (the first line after the start: approximately 340 ms) |
| Decoder on the CPU | 0.5 s to 0.6 s |
| Voice | approximately 0.09 × the length of the audio (0.6 s of audio in 65 ms) |
| Memory, all parts, decoder on the GPU | 4.9 GB RAM and 1.5 GB VRAM |
| Memory, all parts, decoder on the CPU | 5.6 GB RAM |
| Memory, classifier only | 2.3 GB RAM |
| Real spoken lines of the owner that need the decoder (test set, not used for training) | 45 of 50 give the expected orders |

[COOP-BOT.md](COOP-BOT.md) gives all the results, the methods and the known problems.

## Repository layout

| Path | Contents |
|---|---|
| `cpp/coop_intent/` | The C++17 engine and `coop_cli`: chat, engine checks, service mode for a game |
| `scripts/coop/` | Python: label specifications, training data, the bot, the place matcher (`locations.py`), the planner (`world.py`) |
| `scripts/coop/stt/` | The voice chain: synthesized voices, transcripts, classifier builds, decoder and router rounds |
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
- For speech to text and the voice (optional): the sherpa-onnx C API in `cpp/coop_intent/third_party/`.
- For the decoder (optional): llama.cpp. Run `cpp/coop_intent/tools/setup_llama.ps1` to install it in `third_party/`.

[cpp/coop_intent/README.md](cpp/coop_intent/README.md) gives the exact versions and folders.

Do these steps in `cpp/coop_intent`:

```
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
```

## Get the model weights

The weights are not in git because the files are too large.
Each classifier member is a 739 MB ONNX file.
The decoder is a 1.1 GB GGUF file.

Use one of these procedures:

- Copy the weights from the work machine. [HANDOFF.md](HANDOFF.md), section 1, gives the files and the folders.
- Train the models again with the scripts. The section "Train a new version" gives the scripts.

The base models come from Hugging Face: `microsoft/deberta-v3-base`, `microsoft/deberta-v3-small`, `Qwen/Qwen3-1.7B`.
The speech model and the voice come from the sherpa-onnx releases.

## Run the brain

Start a chat in the terminal with bot v58:

```
build\Release\coop_cli.exe --model-dir ..\..\models\coop-deberta-v3-ens3-v58\cpp
```

Add the router and the decoder:

```
build\Release\coop_cli.exe --model-dir ..\..\models\coop-deberta-v3-ens3-v58\cpp --chain ..\..\models\coop-chain-v59\cpp
```

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

All checks must pass.

### Use the brain in a game

1. Copy the brain into the game folder:
   ```
   pwsh cpp/coop_intent/tools/deploy_brain.ps1 -Target <game>\Binaries\CoopBrain -Bot coop-deberta-v3-ens3-v58 -Chain coop-chain-v59
   ```
2. Start `coop_cli.exe --serve` from the game.
3. Send one JSON command per line on stdin. Read one JSON event per line on stdout.

[cpp/coop_intent/README.md](cpp/coop_intent/README.md), section "The bot as a service for a game", gives the protocol.

## Train a new version

Use a Python environment with PyTorch and CUDA.
The speech tools use their own environment in `scripts/coop/stt/venv`.

To train a classifier (example: v58):

1. Run `scripts/coop/make_spec_v58.py`. It writes the label specification and the seed commands.
2. Run `scripts/coop/stt/export_v58.py seeds`. It writes the list of the new seed commands.
3. Run `scripts/coop/stt/synth_v58.py seeds` and `synth_windows_v58.ps1 seeds`. They make the audio of the new seed commands.
4. Run `scripts/coop/stt/run_build_v58.ps1`. It trains three out-of-fold runs and three final models.
5. Run `scripts/coop/stt/ensemble_bot_v58.py`. It sets the gate, exports the ONNX files and writes the engine test files.
6. Run the engine checks.

To train the router and the decoder (example: chain v59):

1. Write the new rules in `scripts/coop/stt/chains2/spec_context_v59.json`.
2. Put the new training items in `scripts/coop/stt/chains2/`.
3. Run `scripts/coop/stt/run_chains5_v59.ps1`. It voices the items, checks them, trains, exports and scores.
4. Run the chain checks (`--chain-tests`).

## Rules for changes

- Do not put model weights in git.
- If you change a Python twin, change the C++ twin also. All engine checks must pass.
- Do not make a tolerance larger to make a check pass.
- Do not train on a test set. The owner's real lines are test sets only.

## Licence

The code in this repository has the Apache License 2.0 ([LICENSE](LICENSE)).
Each model has its own licence. Read the model card of each model before you use or distribute it.
