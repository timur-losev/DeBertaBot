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

**The matcher follows the vocabulary a bot was exported with.** A config whose word lists include the
`pin_*` and `point_*` lists runs rule set v5: a target may carry a pointer, `pin` (the player's 3D marker:
"my pin", "the ping", "on my mark", "where i marked") or `this` (this / that / here / there). One with a
`"directions"` section and without those lists runs rule set v4, and one without `"directions"` runs
rule set v3 -- each exactly as before, so the bots exported earlier keep their records and their test
files. `export_cpp.py <bot> --config-only` moves a bot to the current vocabulary (rule set v5) and the
current timing pattern ("mark" is the pin, not the go-signal), and `gen_tests.py` refuses a bot whose
config holds an older vocabulary or older regexes.

## Layout

| file | what | into UE5 |
|---|---|---|
| `include/coop_intent/unicode.h`, `src/unicode.cpp`, `src/unicode_tables.inc` | UTF-8, NFC and the character classes, from generated tables (no ICU, no OS calls) | as is |
| `include/coop_intent/tokenizer.h`, `src/tokenizer.cpp` | the HF DebertaV2 tokenizer: added tokens, normalizer, Metaspace, Unigram/Viterbi | as is |
| `include/coop_intent/bot_brain.h`, `src/bot_brain.cpp` | `coop_bot.py` `respond()`: top or family gate, threshold, negation guard, GO_NOW/WAIT, HOLD_FIRE (a bot that has the label: it acts at once and keeps the queued order; with the signal slot it queues OPEN_FIRE), the answers (a bot whose config lists `answer_intents`: YES / NO / MAYBE / DONT_KNOW are the action `answer` -- reported, never queued, the queued order left alone), queued order, regex slots | as is, or swap `SlotPatterns` for `FRegexPattern` |
| `include/coop_intent/locations.h`, `src/locations.cpp` | `LocationMatcher`: the map places in a line (object, side or colour, floor, direction, and whether the line points at it with the pin or with this / that / here / there), whose place each is, which one the bot acts on; a twin of `scripts/coop/locations.py`, no regex and no Unicode tables | as is |
| `include/coop_intent/world.h`, `src/world.cpp` | `Planner` over `BotBrain` (see "The world"): the place record grounded against the game's world state (which door, which pin, where the player looks), the conversation's memory, the question the bot asks when a place is ambiguous or missing and the yes / no / place that settles it, the priors the world puts on the probabilities; a twin of `scripts/coop/world.py` | as is: the game fills `WorldState` from its perception and reads `Order` |
| `include/coop_intent/intent_model.h`, `src/intent_model.cpp` | `ILogitsBackend`, `EnsembleBackend` (averages the members' probabilities, one thread each or in turn), softmax, top-k | as is |
| `src/ort_backend.cpp` | `OrtBackend`: one model in ONNX Runtime (C++ API; it asks the loaded runtime for that runtime's own API level, so the 1.30 build also runs on an older `onnxruntime.dll`) | replaced by an NNE backend |
| `include/coop_intent/speech.h`, `src/speech_text.cpp` | `SpeechTextForClassifier`: the form of a transcript the voice-chain bots were trained on | as is |
| `src/sherpa_speech.cpp` | `SpeechRecognizer`: Parakeet TDT through sherpa-onnx's C API (optional, see "Speech-to-text") | with sherpa-onnx as a third-party library |
| `tools/mic_capture.h`, `tools/mic_capture_win.cpp` | the microphone of `coop_cli --voice` (Windows, waveIn) | no: the game has its own capture |
| `tools/coop_cli.cpp` | terminal chat, the checks, and the bot as a service for a game (`--serve`) | as the game's helper process |
| `tools/tts.h`, `tools/tts_win.cpp` | the bot's voice for `--serve --tts`: the system synthesizer (Windows SAPI, the first English voice) | with the helper process |
| `tools/deploy_brain.ps1` | copies the exe, its DLLs, one bot and the speech model into one folder a game starts the service from | no |
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
build\Release\coop_cli.exe --world-tests      # the planner on 600 worlds and conversations vs world.py (no model)
build\Release\coop_cli.exe --bench --threads 1
build\Release\coop_cli.exe --tokenize "hold the other angle"
build\Release\coop_cli.exe --world ..\..\scripts\coop\world_example.json   # chat with a world state loaded
build\Release\coop_cli.exe --serve --no-spin --threads 1 --tts   # the bot as a service: JSON lines on stdin / stdout
```

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
    "no" stops (`action: "negated"`);
  - *a repeat*: "again", "once more" give the previous order as it was;
  - *a fragment*: a place and no action right after an order ("on my pin", "over there") is that order's new
    place; so is a line under the threshold that ends in "there" or "here" ("Should there." heard for "Shoot
    there").
  The frame lives while the game says the bot is busy and `CONTEXT_SECONDS` (8) after. The world state carries
  `time` and `bot.busy`; a game that sends no time gets no context.
- **Checked:** `gen_world_tests.py` writes 600 random worlds (entities with twins at similar distances, pins,
  gazes, stances) and conversations of orders, answers and narrowing places through the Python planner;
  `coop_cli --world-tests` compares action, words, grounding, order, question, queue and memory step by step.
  With the rules for a world without named places and for the short context (the world moves on before every
  line: time, the pin, the crosshair, an enemy under it; the lines include bare orders, repeats, corrections,
  fragments and misheard pointers): 5338/5338 on bot v54 and on its three distilled students, 5343/5343 on the
  v53 bot (33 labels, no answer intents); 12 worlds to refuse or accept. The three scripted checks of `world.py`
  (`DEV`, `DEV_BARE` for the unmarked world, `DEV_TALK` for the owner's lines of the first live test) are the
  first three scenarios of the file.

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
- A stdout line that does not start with `{` is a log line. The service ends when its stdin closes: it never
  outlives the game.
- `--no-stt`: no recognizer and no microphone, typed lines only (headless tests). `--tts`: `say` speaks.
- Measured through the pipes from Python: 0.5 ms over the classifier's own time per typed line; a 3 s clip
  recognized in about 260 ms; ready in 5 s without speech and 7 to 12 s with it.
- `tools/deploy_brain.ps1 -Target <dir>` writes the folder a game needs: `coop_cli.exe`, `onnxruntime.dll`,
  `sherpa-onnx-c-api.dll`, `bot/` (one bot's `cpp/` files), `stt/` (the Parakeet export): 2.7 GB for bot v54.

**In Lyra (UE 5.8).** The first game it runs in: `J:\UE4\Projects\LyraStarterGame58`, `Source/LyraGame/CoopBot/`
(Perforce depot `//OlivaVanilla58`; its own `README.md` is the reference). The client component builds the
world from level markers, the pin and the crosshair, sends each line to this service and turns the reply into
an order RPC; the server's AI controller carries the order out; the pawn and the pins replicate. Checked end
to end with a dedicated server and a client process. On a map without markers the client gives the planner the
crosshair's point under a new id with every line (`gaze_<n>`) and keeps the ones the reply still names
(`last_entity`, `pending_entity`), so a queued order goes where the player pointed then.

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

- **Setup.** CMake looks for `third_party/sherpa-onnx-1.13.8-win-x64/` and builds without speech when
  it is not there (the directory is not in git). Its three files are the ones the Python package
  carries: after `pip install sherpa-onnx==1.13.8`, copy from `site-packages/sherpa_onnx/`
  `include/sherpa-onnx/c-api/c-api.h` to `include/sherpa-onnx/c-api/`, and `lib/sherpa-onnx-c-api.dll`,
  `lib/sherpa-onnx-c-api.lib` and `lib/onnxruntime.dll` to `lib/`. The model is read from
  `scripts/coop/stt/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` (`--stt-model DIR` for another
  place; the download link is in the stt README). `--stt-threads N` (default 2).
- **Two forms of one transcript.** The classifier gets `SpeechTextForClassifier(transcript)`:
  lowercased, the final `.!?` stripped, punctuation inside kept, as in training. `BotBrain::Decide`
  gets the transcript itself: the regex slots and the place matcher read it as the recognizer printed it.
- **Push-to-talk.** The microphone is open while `--voice` runs, so a clip starts 0.2 s before the key
  went down and ends 0.15 s after it came up; nothing else is kept. The key press is read from the
  console (it does nothing while another window has the keyboard). A press shorter than 0.2 s is ignored.
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
- **Cost.** About 0.69 GB of RAM for the recognizer and 2.2 s to load it; a clip of 2.5-3 s is
  recognized in about 230 ms on 2 threads (p95 about 330 ms), then the bot's 40 ms. Waiting costs nothing:
  0.000 cores with the bot loaded and 0.006 with the recognizer loaded and the microphone open.
- **Not there yet.** A microphone on macOS / Linux (`--stt-wav` works wherever sherpa-onnx is found:
  put the platform's files under `third_party/sherpa-onnx-1.13.8-osx` or `-linux`); a choice of input
  device and of the talk key; noise handling; hot words for the game's jargon.

## What was checked

On Windows. The v2, v31, v3 and v1 columns are rule set v3 (2026-10-04) and were re-run unchanged with
the engine that also knows rule sets v4 and v5 (2026-10-10: the same numbers, their files untouched). The
v51 and v52 columns are rule set v4 (2026-10-09; v51's place records were written again after the rule for
"cover my front" was added). The v53 column is rule set v5 since 2026-10-10; under rule set v4 it had
35889/35889 place records. The v3 bot's weights exist only on the Mac, so its two checks
through the model were last run there, before rule set v3 (1062/1062 and 77/77); its other test files
were refreshed on Windows with `gen_tests.py --no-model`.

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
- The planner (world.h): 601 scenarios per bot, 5306 steps on the v53 bot and 5187 on the 41-label scratch
  bot (actions act, ask, answer, resolved, queued, execute, go, wait, negated, say again, ignore; groundings
  by pin, gaze, memory, zone, direction, the only one, the nearest, ambiguous by distance or by an unknown
  modifier, missing), plus 10 worlds the rules refuse and the example world they accept: all equal.

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
