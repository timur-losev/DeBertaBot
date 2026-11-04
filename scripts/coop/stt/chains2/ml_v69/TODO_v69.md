# Round v69: the decoder on the owner's misread lines (2026-11-04)

The owner, 2026-11-04 ~01:40: «начинай обучение». The round had been held since 2026-11-02. It trains the lines his voice tests
of 2026-10-31 .. 11-04 showed the decoder reading wrong (`../ml_v68/TODO_v68.md` section 5).

## What was made

- `make_rows_v69.py`: the rows. Each kind is listed in its docstring. Every English answer was first read by the deployed brain
  (bot v67, place vocabulary v15), and it gives the intent and place wanted.
  - Run 1: 3,122 rows.
  - Run 2: no `put_climb`, plus `means_from`, 3,321 rows.
- `../../chains13_v69.py`: the training.
  - It starts from v68s2's rows (79,271). The 13 bare «вернись» rows there are changed from "come back" to "go back".
  - Round v69's rows are added, a third of them with a neutral scene.
  - Rows equal to an item of a held-out test are dropped (test67, the timer test, the owner test).
  - The recipe is v68s2's.
  - `V69_RUN=2` selects run 2.
  - The runner is `../../run_chains13_v69.ps1 [-Run 2]`.
- `test_v69_owner.json`: 47 of the owner's own misread lines (the recognizer's spelling) with what each should give. None of
  them is a training row. The scorer is `measure_v69_owner.py TAG`, on the game's path.
  - "At once" counts the reply's turns alone.
  - "With held" also counts each line the chain held back (after an "on my go" order or a question), read later as the game
    reads it.
  - A queued order's place is read from `pending_entity`.
- `measure_all_v69.ps1 -Tag T` runs the owner test, test67, test66 (cli), the v68 things and the timer test. Since run 3 it
  also runs the memory scenarios with the candidate chain (`memory_tests.py --chain`, -> `memory_tests_T.log`) and the owner's
  real lines (`replay_owner_talk.py`, -> `replay_owner_talk_T.jsonl` and `talk_diff_v68s2_T.txt`).
  `queue_measure_v69.ps1 -Tag T` starts it when a training run ends.
- `replay_owner_talk.py`: the owner's 495 real lines of 2026-10-31 .. 11-01 (`../../../owner_talk_v69_candidates.json`) said
  again in order, session by session, at their own times, so the decoder's five-line memory holds what it held in the game.
  `--diff A B` lists the lines whose intents differ.

## Results (coop_cli of 2026-11-04, bot v67, decoder on the CPU)

| | v68s2 (deployed) | v69 (run 1) | v69s2 (run 2, deployed, taken back) |
|---|---|---|---|
| owner test, with held | 18/47 | 44/47 | **45/47** |
| owner test, at once | 17/47 | 42/47 | 43/47 |
| test67 intent / + target / + means | 75.0 / 66.7 / 62.5 | 73.3 / 64.6 / 59.2 | **77.5 / 72.1 / 67.5** |
| test66, game's path, intent and place | 93.2 | 95.3 | 94.3 |
| v68 things intent / + target / + means | 87.8 / 80.5 / 78.9 | 87.8 / 83.7 / 80.5 | 87.8 / 81.3 / 79.7 |
| timer, with held: whole / time / intents | 97.9 / 99.2 / 98.8 | 98.3 / 99.6 / 98.8 | 97.1 / 98.8 / 98.3 |
| memory scenarios (42), wrong steps | 0 | not run | **27** |
| owner's 495 real lines, intents other than v68s2's | - | not run | 94 |

Run 1 was not deployed, because test67 lost 8 items at "+ means", where a thing is the step:
- «со стула залезь на белый стол» lost "from the chair";
- «подставь ящик к белому столу, залезай на стол» became DELIVER + JUMP;
- «pon una caja debajo de la ventana y cuélate» became "climb down off the window".

Two causes:
- The `put_climb` rows («поставь ящик и залезь на X» -> "put the crate down | climb onto X") said the opposite of the earlier
  rounds. Since v67, «поставь X и залезь на Y» and «pon la silla y súbete…» are "climb onto Y using X".
- The `get_off` rows («слезь с X») drew «с X» away from its sense as a step.

Run 2 drops `put_climb` and adds `means_from`. It has 279 contrast rows: «со стула залезь на X», «подставь X к Y и залезь»,
«pon X junto a Y y súbete» -> "climb onto Y using X".

On the timer, run 2 gained 2 lines and lost 4:
- «сорока пяти секунд» was read as 50;
- «unos tres segundos» became "a few seconds";
- «en unos segundos vuelve aquí» became "come here";
- «abre la puerta y espera ahí cinco segundos» lost the wait.

That is -2 of 240, judged run noise as at v68s2's deploy (test66 -2 of 192 then).

Checked by hand on v69s2, 35 common Russian orders against v68s2. Changed:
- «стой» is WAIT, not HOLD_POSITION. The game's WAIT stops and pauses a walk, and «иди» resumes it. It was not taught either
  way: one old row.
- «перепрыгни стену» is now "jump over this wall". With the crosshair spot the game sends, it jumps there, as v68s2's "the
  wall" did through the crosshair fallback.
- «ко мне, ко мне» is FOLLOW_ME (was COME_BACK).
- «иди впереди меня» is DRONE "go ahead and scout" (was say again). There is no intent for it yet: the owner's call.

## Deployed 2026-11-04 08:18, taken back at ~09:05

- `Binaries/CoopBrainV6/chain` had v69s2's decoder.gguf and chain_config.json for 45 minutes. The router is the same file
  (md5 4ea11263…). Chain tests were 220/220 equal (CPU).
- It was taken back because the memory scenarios, run after the deploy, failed 27 steps (`memory_tests_v69s2.log`; v68s2:
  42/42 scenarios pass, `memory_tests_v68s2.log`). The teaching the brain does needs the decoder to leave statements alone,
  and v69s2 turned them into orders:
  - «Этот ящик зелёный.» after an order -> "pick up the green crate" (no colour kept);
  - «Это верстак.» -> "climb onto the crate" (no name kept);
  - «Когда я скажу давай, …» lost "on my go": the bot acted at once (ru_on_go 4 of 4 wrong);
  - «Вернись обратно» after «сядь на стул» -> "sit back down".
- The owner's real lines (`talk_diff_v68s2_v69s2.txt`, 94 of 495 with other intents) showed more of the same: «иди сюда» ->
  "go here" (not "come here"), «да» / «стой» after «ляг на диван» -> the lie-down again, «используй эту коробку, залезь …» lost
  "using the box", «забудь про ящик» -> a grenade.
- The game is on v68s2 again (restored from `Saved/CoopBrainBackup/v68s2_20261104`; v69s2's deployed.json is kept there as
  `deployed.json.v69s2_tried`).
- Lesson: the test sets alone do not hold the decoder to the memory. A candidate passes only with the memory scenarios on its
  own chain and a real-line diff read by hand.

## Run 3 (v69s3), training from 09:25

- `make_rows_v69.py` run 3: run 2's rows plus `statement`, `on_go_davai`, `back_after`, `here_bare`, `remark_fail`, `use_climb`,
  `forget_thing`, `short_after` (the readings above, each answer checked through the deployed brain: statements answer as the
  teaching expects, "on my go …", "go back", "come here", "it didn't work", "climb onto Y using X", "never mind the crate", the
  short words as themselves). 4,105 new rows kept; with v68s2's 79,271: 83,376.
- The memory scenarios' own lines are kept out of the new rows only (`chains13_v69.scenario_lines`). Out of the old rows they
  would drop 243 rows like «Да.» and «Давай.», which v68s2 learnt and passes on.
- Three scenarios (ru_meaning, ru_offer_pattern, ru_offer_reset) teach the meaning of «Иди садись на диван», a line the bot
  did not read before. The new decoder reads it ("sit on the sofa", CROUCH), as the owner wanted, so these three need another
  unread line, picked for the decoder that is deployed in the end. The decoder makes up actions for nonsense words, so a line
  that stays unread is hard to find.
- Deploy only if: better on the owner test, not worse on the old sets, the memory scenarios pass (but those three), and the
  real-line diff is read with no new harm.

## Fixed outside the decoder this round (deployed, built)

- coop_cli (RoomOrder): the "in" of a time is not into a room. «Через 5 секунд иди к главной двери» -> "in 5 seconds go to the
  main door" made the bot go into the room by that door. `cpp/coop_intent/README.md`, rooms paragraph.
- Game (OVCoopCommandComponent::OrderFromReply): "go up" whose place is the thing under the crosshair is a jump onto it, as
  "go up" with no place was. «Поднимись наверх» at a table now climbs onto the table when the decoder names it.

## Still wrong on the owner test (v69s2)

- «Поставь ящик и залезь на жёлтую кровать.» -> "climb onto the yellow bed using the crate".
  - Wanted (my reading of his log): DROP, then JUMP.
  - The rounds before teach this frame as "using the crate". Not checked: what the game does with that order when the crate is
    already in the bot's hands.
  - Question for the owner: is that what he meant, or should «поставь X и …» always put X down first?
- «Ко мне, ко мне, снезь ко мне.» -> "back to me back to me | jump down to me" (COME_BACK, JUMP). «снезь» is the recognizer's
  «слезь».

## Not in this round (the owner's call)

- An intent for «иди впереди меня».
- «без коробки».
- «не бери ящик и …».
- Recognizer junk and the mishear option (TODO_v68 5f, 5g).
- «иди на красный стул» after a failure (the means rule).
- The bot's name alone.
- «поднимись» alone.
- «Отнеси коробку наверх».
- The "on the left" answer in Russian mode.
