# Round v65: context the networks learn, not rules (plan, 2026-10-25)

The owner, 2026-10-25: "Hide Weapon - Didn't catch that. Добавь в план обучения. ... Хотелось бы решения на уровне
нейросетей, ведь тогда мы покроем большой объём вариантов." Earlier the same day: "держать в голове контекст субъекта и
объекта, с которым он сейчас имеет дело"; "если нет рядом машины, я говорю запрыгни, значит речь идёт не про машину";
"ЗАпрыгнуть, Спрыгнуть, Перепрыгнуть".

Until v65 the game covers these by rules (LyraStarterGame58 `OVCoopCommandComponent::OrderFromReply`, `OVCoop::Says*`;
README "The world reads the line again"). The rules stay as a safety net; the game logs every line where a rule changed
the brain's reading ("the brain read X, the world and the words say Y"), and those lines are the first measure of v65.

## What the networks miss today (all from the owner's own play)

- Words: "hide weapon" (SWITCH_WEAPON 0.66, said again); «слезь» "Get out." (GET_OUT); «запрыгни» GET_IN with no car;
  «запрыгни сверху на катушку» RAPPEL; "put it there" DROP; "take that box" DELIVER (the owner: take = keep); "throw it
  away" DROP 0.55; "press / push it forward" SUPPRESS; «нет, не бросай, просто подними её» a cancel.
- Context: what "it", «её», «эту», "again" refer to (the thing the bot holds, stands on, dealt with last); whether a car is
  near ("jump in" vs "get in"); whether the bot stands on something ("get down" = off it, else take cover).

## Data

1. `owner_lines_v65.json`: 33 of the owner's English lines (35 times said), labelled from the talk (extract_owner_lines_v65.py).
   Into the classifier's training as v61's and v64's owner lines; reported alone.
2. `chains2/ml_v65/hand_v65.json`: 70 rows (Russian, English, Spanish) the decoder v64 got wrong, with their English; its
   "classifier" section: English seeds (JUMP off / onto / over, COLLECT for take / hold / carry, ROLL "the other way").
3. A blind round as v62 and v64 (three authors, two annotators, spec_v65 frozen first): HOLSTER wordings ("hide / stow /
   sling your weapon", «спрячь / убери ствол»); take vs bring vs put; jump onto / over / off and climb down; push / roll
   "it", "again", "the other way"; corrections ("no, pick it up", «нет, держи её»).
4. The new kind of row, context the decoder is given: a `scene` line before the player's line, made by the game:
   `scene: holding cardboard box; standing on spool; car none within 25 m; last thing: box 3 m`. The same line under
   different scenes has different English: «запрыгни» with no car -> "jump up on the box", with a car at 5 m -> "get in the
   car"; "put it there" holding a box -> "put the box there"; «ещё раз» after a jump on the spool -> "jump on the spool
   again"; «слезь» standing on a box -> "get off the box", on the floor -> "take cover". Made by templates over the
   scenes plus blind authors who are given scenes (never the training rows); answers checked by two annotators.

## Models

- Decoder v65 (Qwen3-1.7B QLoRA, chains9_v65.py on chains8_v64's rows): + hand_v65, + the blind round's lines in three
  languages, + the scene rows. The system turn says a scene may come before the line. The decoder writes explicit English
  ("put the box there"), so the classifier and the planner stay as they are.
- Bot v65 (DeBERTa ensemble): + owner_lines_v65, + hand_v65's seeds, + the blind round; the gate and threshold fitted on
  out-of-fold runs as before. No scene input: the decoder carries the context.
- coop_cli: the world JSON gets `bot.holding`, `bot.standing_on`, `bot.last_thing`, `car_near`; the chain passes the scene
  line to the decoder (rewriter.h). Game: BuildWorld fills them (the server's LastThing, StandsOn and the carried thing
  are replicated to the client in the companion's state).

## Measures

- The owner's lines (v61 + v64 + v65), per line and per time said; the lines where a game rule changed the reading.
- hand_v65 (trained on: a check that they are learnt), and a held-out scene test (never trained on): the share where the
  decoder's English, read by the classifier, gives the order the scene calls for.
- The old sets (blind2, ctx, pairs, ru/es dev): within a point or two of v64.

## Cost

DeBERTa ensemble about 2.5 h, decoder about 4.5 h on the RTX 4090; the blind round and the scene rows by agents.

## What was done (2026-10-25/26, the owner: "запускай и померяем точность")

- The blind round of authors (Data 3) was not run: the classifier got make_spec_v65.py's 109 seeds and the owner's lines,
  the decoder the template scene rows of chains9_v65.py and hand_v65. The scene test (scene_test.json, 150 lines) was
  written blind by an agent and never trained on; rows equal to its items in line and scene were dropped (12).
- Trainings: classifier v65 (build_v65.py, 2 h 53 min beside the decoder; family gate 0.66), decoder v65 (59,164 rows,
  5 h 20 min). All eight engine checks equal on bot v65; chain tests 200/200 on the CPU, the scene line 40/40.
- Numbers (measure_v65.py, as the game reads lines; ensemble_bot_v65.log; score_chains9_v65.py):

  | Set | v64 + v64 | v65 + v64 | v65 + v65 |
  |---|---|---|---|
  | owner65, 33 English lines (out of fold for v65) | 75.8 | 87.9 | 87.9 |
  | hand65, 70 rows (trained on) | 57.1 | 70.0 | 100.0 |
  | scene65, 150 lines with a scene (held out) | 70.7 | 76.7 | **93.3** |

  The owner's 521 v61 lines, per time said: v64 91.8 right / 3.1 wrong family, v65 91.6 / 2.6. The old decoder sets
  moved by -2.4 to +5.3 points (v64 held-out en 98.2 -> 96.3, blind2_es 78.0 -> 83.3, pairs en 99.3 -> 97.3).
- Deployed to Binaries/CoopBrainV6 on 2026-10-26 01:09 (bot v65, chain v65). The game sends the scene (BuildWorld).
  E2E v65_scene, v64_jump, v64_context pass.

## Left for v66

(Kept with the owner's notes of 2026-10-26 in chains2/ml_v66/TODO_v66.md.)

- "again" after getting off: the decoder writes «Запрыгни» after «Слезь» as "jump on it again", and the planner's
  "again" takes the last order's way (down). The game reads the words again for now (README); v66 rows should answer
  "jump up on it" there.
- scene65 misses: "Get down, get down!" on a spool written back as it is (cover); "Get in, get in!" MOVE_TO; bare "Again."
  / "Do it again." REPEAT where the test wants the order itself; «Стой» / «Quieto ahí» HOLD_POSITION for WAIT; «¡Al
  suelo!» / «¡Cuerpo a tierra!» PRONE (the test wants TAKE_COVER; prone is a fair reading).
- owner65 misses out of fold: "how we doing bro?", "how would you homie?" (say again, want STATUS_REPORT), "press it
  forward" (SUPPRESS, want PUSH), "come here and put it right there" (two orders: the chain's).
- The bot's word for getting down is drawn from JUMP's lines ("Going over." / «Перепрыгиваю» for «Слезь»).
