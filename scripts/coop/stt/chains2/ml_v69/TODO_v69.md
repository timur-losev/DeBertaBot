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

### Run 3's results (trained 09:25-12:34, measured by 13:02): not deployed

| | v68s2 (deployed) | v69s2 | v69s3 |
|---|---|---|---|
| owner test, with held / at once | 18 / 17 of 47 | 45 / 43 | 44 / 42 |
| test67 intent / + target / + means | 75.0 / 66.7 / 62.5 | 77.5 / 72.1 / 67.5 | 77.9 / 71.7 / 67.5 |
| test66, game's path | 93.2 | 94.3 | 93.2 |
| v68 things | 87.8 / 80.5 / 78.9 | 87.8 / 81.3 / 79.7 | 87.8 / 81.3 / 79.7 |
| timer, with held: whole / time / intents | 97.9 / 99.2 / 98.8 | 97.1 / 98.8 / 98.3 | 98.8 / 99.6 / 98.8 |
| memory scenarios, wrong steps (of them the three stale scenarios') | 0 | 27 | 19 (14) |
| owner's 495 real lines, intents other than v68s2's | - | 94 | 95 |

The five wrong steps that are not the stale scenarios' (`memory_tests_v69s3.log`):
- ru_rooms «Выйди из гаража» (the brain writes the taught name as «Выйди из door») -> "leave door", not read (v68s2: "Leave
  through the door.").
- ru_it_after_what «Запрыгни на него.» after «Что это?» at the white table -> "jump on the red table" (named two lines before).
- ru_undo_last «Ях.» (a word whose lesson was taken back) -> "lie down on the sofa", a question; «Этот ящик зелёный.» then answered
  it ("Ясно. Ложусь.") and no colour was kept, so «Забудь это.» had nothing to forget. (v68s2 read «Ях.» as "get back up", an
  order with no question, and so passed.)
- ru_go_back_words «Вернись к камню.» -> "go back to the rock", GO_BACK with no place. Fixed in the brain (below), not the decoder.

The real lines, read by hand (`talk_diff_v68s2_v69s3.txt`): about 30 better (every «сядь на стул/диван» is a sit, «ляж/лях на диван»
a lie-down, «слезь со стула» a getting off, «через стену перепрыгни» a jump, «иди сюда, вот сюда» come here, «вылези отсюда» out of
the room, «когда я скажу давай, …» three orders on the go), about 20 worse, the rest recognizer junk that both make something of.
Worse, among others: «Используя коробку залезть на синий стол.» -> "come back to me using the box"; «Иди ко мне сюда.» -> "come
here | stay here"; «Тимур, иди сюда.» -> "go here"; «Когда я скажу прыгает, ты прыгнешь.» -> "jump when i jump" (at once); «Давай.»
after it -> "Go ahead and jump.", and after a queued line -> "Go. | jump onto the rock"; «No.» after a sit -> "sit down"; «Sto» ->
"Go."; «Получилось?» -> "did it" (GO_NOW); «Встань сюда.» -> "stand up here" (asked again); «Поднимись по ней наверх.» -> "Go up the
ladder."

How much of that is a new run's noise: v68s (round v68's first run, the same recipe) against v68s2 reads 83 of the 495 lines
with other intents and fails 10 memory steps (ru 3, ru_what 1, ru_it_after_what 4, ru_callout 1, ru_colour_order 1). The memory
scenarios were written on v68s2, the deployed decoder, so another decoder fails some of them for its wording alone. A failed step
is still read by hand: it counts against a candidate unless the behaviour is right and only the scenario's wording is v68s2's.

## Run 4 (v69s4), training from 13:11

`make_rows_v69.py` run 4 = run 3 + KINDS_4, for what run 3 harmed: `here_named` («Тимур, иди сюда», «иди ко мне сюда» -> "come
here"), `stand_here` («встань сюда» -> "stay here"), `using_climb` («используя коробку, залезь на X», «с помощью ящика …» -> "climb onto
X using the box"), `go_after_queued` (a go word after an order on the go -> "go"), `on_go_word` («когда я скажу прыгай, ты прыгнешь»
-> "on my go jump"), `short_en_after` («No.», «OK.» after an order -> themselves; «получилось?» -> "did it work?", no order),
`named_door_words` («выйди из door» -> "leave through the door"). 4,442 new rows kept; 83,713 in all.

Run 4 was stopped at 13:58 (step 4303 of 15699) for the owner's answers below; its rows are run 5's but for them.

## The owner's answers (2026-11-04 ~14:00) and run 5 (v69s5), training from 14:04

- «Поставь ящик и залезь на…»: «сначала поставить ящик. но если будет команда "используя его" (ящик, камень, стул и тд - пока носить
  можно только ящик, но потом можно будет носить всё), то надо будет следовать команде».
- «Стой»: «это "жди"» (WAIT: it stops, «иди» goes on).
- «Иди впереди меня»: «пока не важно».

What run 5 changes for them:
- `put_then` (340 rows, ru/es/en): «поставь / положи / опусти X (у / возле / рядом с / к Y) и <order>», «pon / deja / coloca X (junto
  a Y) y …», "put X (by / next to Y) and …" -> "put X down" (DROP) or "put X next to Y" (DELIVER at Y), then the order; with «используя
  его» / «с его помощью» -> "put X down | climb onto Z using X". X is the crate or the box mostly, and the chair, the spool and the rock
  (carried later, the owner).
- `drop_put_using`: 344 of v68s2's rows that read a plain putting as the means («Поставь ящик и лезь на аптечку» -> "climb onto the
  medkit using the crate", «pon la silla y súbete a la cama», "put the car by the white stairs and climb through it": rule set v9's
  generator) are left out. Kept as the step: «подставь X» (177 rows), «под окно», «debajo de», "under": these words say the thing is
  put as a step. `means_from`'s Spanish «pon X (junto a Y) y súbete» rows are left out too.
- Bare «стой» after a lie-down or a sit: "wait" (run 3 and 4 had "hold position").
- test67: t67_112 («Pon la caja junto a la mesa blanca, súbete a la mesa y luego salta la valla.»), t67_119 («Agáchate, pon la silla
  junto a la mesa roja y súbete a la mesa.») and t67_175 ("Put the box by the white table, then climb on the table, then jump over the
  fence.") now want DELIVER at the table, then JUMP onto it (were one JUMP using the thing). v68s2 and v69s3 are measured again on it
  as v68s2b and v69s3b.
- In the game the two readings end alike when the table is too high: the box is put by it, and the climb planner takes it as the step.

## The three stale memory scenarios get new unread lines (2026-11-04)

ru_meaning, ru_offer_pattern and ru_offer_reset teach the meaning of a line the bot could not read. «Иди садись на диван» and
«Садись на стул» were such lines for v68s2 only because its classifier was unsure ("Sit on the sofa.": JUMP, GET_IN or CROUCH);
v69s3 reads them as sits, as the owner wants. A made-up verb does not help: both decoders make an order of any line with a thing
in it («Иди тыгыдыкни на диван» -> "go melee the sofa" / "go shove someone on the sofa"). Lines that both v68s2 and v69s3 leave
unread (no intent for resting): «Иди отдохни на диване.» ("go relax on the sofa" / "go take a break using the sofa") and «Иди
помедитируй на стуле.» ("go meditate on the chair" / "go take a deep breath using the chair"). Changed:
- ru_meaning: «Иди садись на диван.» -> «Иди отдохни на диване.» (and «… вон на том.»); «Садись на стул.» -> «Иди помедитируй на
  стуле.»; its read line «Иди к стулу.» -> «Залезь на этот стул.». «стуле» and «стулу» share no start of five letters, so the bot
  would not take them for the same thing; «Иди на стул.» starts as the missed line and is taken for the same order at another place
  (AnotherPlace); «Залезь на стул.» was read by v68s2 as the white table named two lines before.
- ru_offer_reset: «Иди садись на диван.» -> «Иди отдохни на диване.».
- ru_offer_pattern: the same, the pattern «иди отдохни на {x}», used on «Иди отдохни на кровати.».
Every expectation is as before. On today's coop_cli: v68s2 42/42 scenarios; v69s3 4 wrong steps (ru_rooms 1, ru_it_after_what 1,
ru_undo_last 2), none of them these three.

## Fixed in the brain after run 3 (coop_cli, not deployed yet)

- "go back to the rock" (the decoder's English for «вернись к камню» since v69s3) is read as "come back to the rock", COME_BACK at
  the rock, as v68s2's English was: GO_BACK is the bot's own history of places and takes no place (`GoBackToPlace`). Only when the
  player's own words say a going back («вернись», «vuelve», …).

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
  - The owner, 2026-11-04: put first; «используя его» makes it the step (run 5).
- «Ко мне, ко мне, снезь ко мне.» -> "back to me back to me | jump down to me" (COME_BACK, JUMP). «снезь» is the recognizer's
  «слезь».

## Not in this round (the owner's call)

- An intent for «иди впереди меня» (the owner, 2026-11-04: «пока не важно»).
- «без коробки».
- «не бери ящик и …».
- Recognizer junk and the mishear option (TODO_v68 5f, 5g).
- «иди на красный стул» after a failure (the means rule).
- The bot's name alone.
- «поднимись» alone.
- «Отнеси коробку наверх».
- The "on the left" answer in Russian mode.

## Deployed 2026-11-04 ~14:15 on the owner's word: v69s3

The owner: «в игру вставить вон тот декодер, который ты обучил, вот последний раз. И вообще все модели. Мозг». Decoder v69s3 (router
unchanged) and coop_cli with GoBackToPlace (md5 17740208); chain tests 220/220 in the game's folder. v68s2's chain is in
`Saved/CoopBrainBackup/v68s2_20261104/chain`, the coop_cli before in `coop_cli.exe.before_goback`. Bot v67, the voices: as before.

### The owner's game at ~15:00 and what it showed

- «Возьми эту коробку, залезть на синий стол, перелезть на белый стол и оставь там коробку.» -> COLLECT, JUMP onto the blue table,
  JUMP onto the white table (all right), then "Leave the box behind." -> DELIVER at the crate marker the box came from: the bot jumped
  down and put the box there, by the player. v68s2 wrote "Leave the box on the white table." Fixed in the brain (coop_cli
  `LeaveItemPiece`: "leave the box" with no place of its own is "put the box down"); the line now reads COLLECT, JUMP, JUMP, DROP.
  Deployed 15:3x as md5 37cb501e beside the running brain (`coop_cli.exe.before_leave`); it is used from the next game start.
- Replayed alone, «Возьми коробку, залезь на синий стол, …» is "climb onto the blue table using the box" for v69s3: the step, though
  the owner says the step only with «используя». Run 3-5's `use_climb` had «возьми эту коробку, залезь на X» -> "using" (my mistake).
  For run 6: `use_climb` without «возьми», and `take_climb` (100 rows: «возьми / бери / подними X, залезь на Y (, перелезь на Z) (и
  оставь там коробку)» -> "pick up X | climb onto Y (| jump onto Z) (| put X down)"). Run 5 (training) keeps its rows.

## Run 5 (v69s5): results, and deployed 2026-11-04 ~21:50 on the owner's word

Trained 14:04-17:59, measured 18:02-18:21 (`measure_all_v69s5.log`). Against v69s3 (test67 on the put answer: v68s2b, v69s3b):

| | v68s2b | v69s3(b) | v69s5 |
|---|---|---|---|
| owner test, with held / at once | 18 / 17 of 47 | 44 / 42 | 44 / 42 |
| test67 intent / + target / + means | 75.4 / 67.1 / 62.9 | 77.5 / 71.2 / 67.1 | 78.8 / 71.2 / 66.7 |
| test66, game's path, intent and place | 93.2 | 93.8 | 95.3 |
| v68 things intent / + target / + means | 87.8 / 80.5 / 78.9 | 87.8 / 81.3 / 79.7 | 89.4 / 82.9 / 81.3 |
| timer, misses of 240 | - | 3 | 6 |
| memory scenarios (42, new triggers), wrong steps | 0 | 4 | 3 |
| owner's 495 real lines, intents other than v68s2's | - | 95 | 85 |

- Memory: v69s3's four (ru_rooms, ru_it_after_what, ru_undo_last x2) pass. The three new ones are all ru_meaning: v69s5 reads
  «Иди отдохни на диване вон на том.» as going to the sofa and «Иди отдохни на диване.» as a lie-down, so the line is no longer
  unread and the offer does not come. The behaviour is a fair reading; the scenario's trigger is stale again.
- Timer: + «открой дверь и подожди там пять секунд» -> HOLD_POSITION 5 s (not WAIT), «ляг на 10 секунд, потом вставай и за мной»
  lost the STAND_UP, «súbete al carro después de 15 segundos» -> JUMP onto the car (not GET_IN), «espérame un segundito» -> a 1 s
  wait; − «слышь, глянь на меня секунды на четыре».
- Real lines, v69s3 against v69s5 by hand (86 differ, `talk_diff_s3_s5.txt` in the scratchpad, from `replay_owner_talk_*.jsonl`):
  about 29 better, 16 worse, the rest recognizer junk or no matter.
  - Better: «Поставь ящик и залезть на жёлтую кровать.» -> "put the crate down | climb onto the yellow bed" (the owner's answer);
    «Используя коробку залезть на синий стол.» -> the step; «Возьми её и залезь на синий стол.» -> "pick it up | climb onto the
    blue table"; «Иди ко мне сюда.» -> "come here" alone; «Давай.» -> "Go."; «No.» -> no; «Встань сюда.» -> "stay here"; «На крышу
    залезь.», «Слезь сюда.», «Отнеси на крышу коробку.»; about ten one-word junk lines ask again instead of jumping or lying down.
  - Worse: «Когда я скажу давай, ты подойдёшь к этой коробке, возьмёшь её и отнесёшь её к красному стулу.» -> the first piece
    "on my go, you approach this box" is asked again and the pick-up and the carrying are done at once (v69s3 held all three for
    «давай»); «Поднимись на жёлтую кровать.» and "Go on top of yellow bed." -> MOVE_TO (v69s3: JUMP); «Тай на ноги.» -> CROUCH;
    «Прыляж.» -> "jump down"; «Бади.» -> "go ahead" (GO_NOW); «Dele vai, eles vai.» -> OPEN_FIRE; «Через стену прям.» -> FLASH;
    «Теперь сядь на тот стул.», «Дальше, дальше, вон туда.», «Теперь и сюда.», «Da.» asked again.
- The owner's line of 15:00 (`probe_leave.py v69s5`): in his order of lines the third and fourth saying read COLLECT, JUMP blue,
  JUMP white, DROP; the second ends "leave the box there" asked again; alone the pick-up is lost ("climb onto the blue table |
  jump over to the white table | leave the box there"). For run 6: `take_climb`, and "leave the box there" after other orders of
  the line (coop_cli `LeaveItemPiece` takes "", behind, where it is, here, down, not "there").

Deployed: `Binaries/CoopBrainV6/chain` decoder.gguf (md5 e9024f9b), chain_config.json (5bb8f2c2), chain_tests.jsonl of v69s5; the
router is the same file (4ea11263). Chain tests 220/220 in the game's folder (CPU, 489 ms a line). v69s3's chain is in
`Saved/CoopBrainBackup/v69s3_20261104/chain`; deployed.json has `chain_v69s3_before_v69s5` and `chain_note_20261104_2150`.
coop_cli unchanged (37cb501e); `coop_cli.exe.replaced_while_running` deleted.

Run 6 candidates: `take_climb` (ready), the long «когда я скажу давай, …» with three orders, «поднимись на X» = climb onto X,
«встань на ноги», «приляг», the bot's name alone is no go word.

## For run 6, from the owner's game of 2026-11-05 15:06

- "take this box and I delivered it onto yellow bed." (his "take this box and deliver it onto the yellow bed"; Parakeet wrote "and
  I delivered it"): the decoder kept the line as it was, the place matcher read "I ... onto yellow bed" as the speaker's own place
  ("yellow bed [mine]"), so DELIVER had no place and the game made it COLLECT. Rows: "take X and I delivered it onto Y", "... and
  I deliver it to Y", "... and I carried it to Y" -> "pick up X | carry it onto Y" (a first-person verb after an order with "and"
  is a misheard imperative), with the same lines that are a statement kept as statements ("I delivered it to the yellow bed." alone).
- The game half (the step crate taking the order's box) is fixed in the game (RestoreOrderCarry, PickUp's reach up and down).
