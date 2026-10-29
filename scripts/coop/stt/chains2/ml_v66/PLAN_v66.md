# Round v66: the owner's notes of 2026-10-26/27 (plan, 2026-10-27)

The owner, 2026-10-27 03:00: «стартуй v66». The list is TODO_v66.md; this file says what goes into the round, how, and what
was done. The rule-only items of the list ("it" is the thing the talk was about, colours on tables) were done on 2026-10-27
before the round (rule set v8, vocabulary v11, the v65 bot exported again).

## Decisions (mine, where the owner left them open)

- **GIVE_WAY**, a new intent in a family of its own: "move away", "go away", "step aside", "get out of the way", "let me
  through", «отойди», «уйди с дороги», «дай пройти», «apártate», «déjame pasar». The bot steps 2-3 m to the side of the
  player's line of view and movement, then goes on following (the owner, 2026-10-26: "должен идти за мной"). No place from
  the line (NO_PLACE). "Get out" alone stays GET_OUT; "get out of here" stays FALL_BACK.
- **WHAT_IS_IT**, a new intent in the family 'see' with SEE_THING and SEE_ME: "what is that", "what's this", "what am I
  looking at", «что это (такое)», «¿qué es eso?». A question the game answers (state "what"): the thing under the
  crosshair, named as the crosshair debug view names it, in the player's language. NO_PLACE: the crosshair is the thing.
  "What was that" / «что это было» stays SMALL_TALK; "what do you see" stays STATUS_REPORT.
- **Glass is a window**: vocabulary v12 gives the object window the words glass, pane, glass panel, window pane;
  "shoot the glass" is OPEN_FIRE @ window; "break / smash the glass / window" and «разбей стекло» are MELEE @ window (the
  owner: «удар прикладом»). The game: a butt strike on a window's glass breaks it; the crosshair on the glass gives the
  window marker as the gaze. "Butt of your rifle", "with your gun" are no place (vocabulary "ignore").
- **Outside**: vocabulary v12 gets the zone `outside` ("outside", "outdoors", "out of the room", "out of the building"),
  relative like `inside`: no entity, the game finds the nearest navmesh point under open sky. «выходи из комнаты», «выйди
  отсюда», "get out of the room", "go outside" are MOVE_TO outside (the decoder writes "go outside").
- **Corrections keep the thing** (decoder): «нет, оружием / стреляй» after a butt strike on X is "shoot the X"; «нет,
  прикладом» after shooting X is "hit the X with your rifle butt"; «нет, дымом / флешкой / гранатой» after another grenade
  at X is that grenade at X; «нет, подави» after firing at X is "suppress the X". Without such an order before: as today.
- **Holding and a negation** (decoder, with the scene): «не отдавай / не кидай / не спускай / не ставь» holding a thing is
  "keep holding it".
- The rest of TODO_v66 that is words: take it / this / that = COLLECT; throw it, toss it away, chuck it = DROP; "you're
  my brother" SMALL_TALK; "how we doing bro" STATUS_REPORT; "press it forward" PUSH; the recognizer's slips of the day; «Прямо
  перед тобой, да» = yes. Not in this round: "a way up to the commander" (the goal-oriented bot's), jumping over every box,
  "the table" alone after naming one (a rule).

## Data and models

1. `make_spec_v66.py`: intents_v66.json (71 intents: GIVE_WAY, WHAT_IS_IT before NONE), seed_commands_v66.json (v65's ids
   kept + the new seeds and boundaries), locations_v66.json (vocabulary v12). The v11 file of the v65 bot becomes
   locations_v65.json.
2. `owner_lines_v66.json`: the owner's English lines heard since bot v65 (the test range, 2026-10-27), labelled from the talk.
3. Voices for the new seeds (Windows, Kokoro, VCTK A) and Parakeet's transcripts (run_voices_v66.ps1).
4. Bot v66 (build_v66.py, build_v65's recipe; three out-of-fold runs for the gate and threshold, three final models).
5. Decoder v66 (chains10_v66.py on chains9_v65's rows): hand_v66.json (the owner's misses with their English) + template rows
   (GIVE_WAY, WHAT_IS_IT, glass, outside, corrections with the line before, holding and a negation) in ru, es, en.
6. A held-out test written blind by an agent (test_v66.json, never trained on): lines in ru, es, en with the order and place
   each must give, measured as the game reads lines (measure_v66.py).
7. Engine (Python + C++, parity): GIVE_WAY and WHAT_IS_IT in NO_PLACE; zone `outside` grounded like `inside`; WHAT_IS_IT's
   state "what"; replies for both in en, ru, es (and the "brat" tables).
8. Game: GIVE_WAY (step aside, keep following), the "what" answer, the zone outside, MELEE on glass, the glass gaze.

## Measures

The held-out v66 test (v65 vs v66), hand_v66 (trained on), the owner's v61 lines per time said, the old decoder sets
within a point or two, all engine checks equal.

## What was done (2026-10-27, the owner: «стартуй v66»)

- Data as planned. The held-out test (test_v66.json) has 200 lines written blind by an agent; 8 of them equal one of the
  owner's trained lines and are left out of its score (192 counted). Template rows equal to a test item in the lines
  before, the scene and the line were dropped.
- Trainings:
  - classifier v66: build_v66.py, 2 h 59 min, three out-of-fold runs and three final models; family gate, threshold 0.76
    by the usual criterion (v65: 0.66), set to 0.66 by the owner on 2026-10-27 (below);
  - decoder v66: 62,669 rows, 5 h 53 min.
- Checks: all eight engine checks equal on bot v66. Chain tests 200/200 on the CPU (196/200 on the GPU), the scene line
  40/40.
- Numbers:

  | Set | v65 brain | v66 brain |
  |---|---|---|
  | test66, 192 lines held out, whole brain as the game reads them (measure_v66_cli.py): intent | 57.3 | **91.1** |
  | the same, intent and place | 45.8 | **90.6** |
  | scene65, 150 lines held out (measure_v65.py, bot v66 with decoder v65 / v66) | 93.3 | 94.0 |
  | owner66, the owner's 71 new English lines (out of fold) | — | 93.0 |
  | hand66, 50 rows (trained on; measure_v66.py) | — | 98.0 |

  - measure_v66.py's own score of test66 is 87.5 (intent and place): it reads an English correction without the
    planner's memory of the line before.
  - The owner's 521 v61 lines, per time said (right / say again / wrong family):
    - v65 at 0.66: 91.6 / 4.9 / 2.6;
    - v66 at 0.76: 88.8 / 8.4 / 2.4;
    - v66 at 0.66: 91.9 / 4.7 / 2.9.

    The criterion's threshold costs the owner's own lines more "say again" than it saves wrong orders: the same
    criterion (near - 2 x wrong family) on these lines gives 0.66 86.1 and 0.76 84.0. The owner chose 0.66
    (2026-10-27, «ставь»): ensemble_bot_v66.py now writes 0.66 and prints the fitted 0.76 beside it. Seen in the game:
    "put it down by the white table" read DROP 0.73, "Come again?" at 0.76. test66 at 0.66 (measure_v66_cli.py,
    with the DROP-by-a-thing rule): the same 91.1 / 90.6; three misses that said again now act wrongly («отвали, не
    мешай пройти» TAKE_COVER, «заложи заряд и взорви дверь» PLANT, «не ставь её на пол» DROP). The 0.76 log is kept as
    measure_v66_cli_v66_t076.log.
  - Old decoder sets (score_chains10_v66.py, read by bot v66), more than the planned "point or two" in places:
    - es held-out 82.6 -> 88.1, en held-out 96.3 -> 97.2;
    - ru held-out 86.2 -> 82.6, ctx_ru 82.7 -> 78.7, ctx_es 84.7 -> 82.0;
    - English decoder sets -0.3 to -2.7;
    - 93 lines won, 111 lost.
- Deployed to Binaries/CoopBrainV6 on 2026-10-27 (bot v66, chain v66, the five reply tables, coop_cli). v65 is kept in
  LyraStarterGame58/Saved/CoopBrainBackup/v65_20261027.
- E2E passed:
  - v66 (test range: what is that, move away, en and ru);
  - v66_glass ("melee the window", "break the glass");
  - v66_outside ("go outside", «выйди отсюда»). It now sends the bot indoors first: the red main hall is partly open
    to the sky.

## Left for v67

- Short corrections that change the place or the thing ("не, северную", «и то же на синюю», «прости, второй этаж»):
  decoder v66 writes some back as heard ("same same but blue", "sorry sorry second floor in the meaning") where v65
  rebuilt the order. The likely cause is the correction rows that say "without an order before, write it as it is".
  Rows with a place or thing correction after an order should balance them.
- English negations while holding a thing ("don't drop it", "don't throw that crate"): the router leaves English lines
  with the classifier, which reads WAIT. Either the scene sends them to the decoder, or a planner rule handles them
  (holding + negated DROP/DELIVER = keep holding).
- test66 misses:
  - «Уйди, брат, не до тебя» GET_OUT;
  - «отвали, не мешай пройти» NONE;
  - «заложи заряд и взорви дверь» PLANT only (the second order lost);
  - «parte esa ventana» FRAG;
  - "nah use your gun" SWITCH_WEAPON after "smash the glass";
  - «стой» HOLD_POSITION (the test wants WAIT; an old disagreement).
- The test harness (measure_v66_cli.py) has only a white table, so "Jump over it." after "the red table" counts as a
  miss.
- MOVE_TO's reply is drawn from three lines, one of them "Moving to the ping." («Иду к метке»), also for an order with
  no ping, such as the zone outside (older than v66; coop_cli kLines and coop_bot.py LINES).
