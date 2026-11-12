# Round v70 plan: body commands and driving by voice (2026-11-11)

This is a plan only. Nothing has been trained or started yet. Training uses the GPU, so it starts only on the owner's word.

## 1. What the owner asked for

- **2026-11-08, the body.** He asked for basic commands on top of ProceduralBody 2:
  - raise or lower a part and turn it, by an angle with a deviation (left, right, up, down);
  - speed and sharpness;
  - strikes.

  His answers:
  - console first, voice later;
  - every part (arms, head, torso and the whole body, legs);
  - speed and sharpness both in the command and as a general setting;
  - strikes by the left and right hand (straight, hook, uppercut), by the leg and the knee, by the elbow and the head, by the
    rifle butt, each with a force;
  - «чтобы игрок мог обучить связки из базовых движений» ("so that the player can teach combos of the basic moves").

  The console part is built. See `CoopBot/README.md`, section "Body commands and combos".
- **2026-11-11, driving.** «В план обучения нужно добавить команды вождения автомобилем. Чтобы можно было бы сказать ему «Едь
  вперед поверни налево». Там будет просто дорога, будет понятно, что один поворот налево. Только по дороге ехать. Или там «Едь к
  банку». «Едь к какому-то метке там». Там есть ресторан, банк и так далее.» ("Add car-driving commands to the training plan.
  So I can tell him «Drive forward, turn left». There will just be a road, and it will be clear that there is one left turn. Drive
  only on the road. Or «Drive to the bank». «Drive to some marker». There is a restaurant, a bank and so on.")

  His answers the same day:
  - the player rides as a **passenger beside the bot**, so a passenger seat must be made (today the car has only the driver's
    seat);
  - «едь вперёд» ("drive forward") with nothing after it means: drive to the **nearest junction**, stop there and wait for
    where to go next;
  - the first map is **the modern city**, `/Game/Maps/L_OVModernCity` (made by ollaya-c1, not in P4);
  - «едь к банку» ("drive to the bank") said to the bot on foot means: it **gets into the nearest free car and drives**.

## 2. What the brain reads today

Brain: bot v67 with chain v69s5 for Russian, and v69s5all (every line through the decoder) for English. Probes are in the
session scratchpad, `probe/body_probe.py` and `probe/drive_probe.py`.

No intent covers either kind of command. Each line lands on the nearest wrong intent.

**The body:**
- «подними правую руку» ("raise your right arm") -> SWITCH_WEAPON
- «подними руки», «опусти руку», «разведи руки» ("raise your arms", "lower your arm", "spread your arms") -> HOLSTER
- «ударь ногой» ("kick") -> PRONE
- «ударь кулаком», kick, punch -> MELEE, which walks to an enemy and hits it
- «сделай хук левой» ("do a left hook") -> FRAG
- «наклонись вперёд» ("bend forward"), «подними правую ногу» ("raise your right leg") -> MOVE_TO
- «помаши», «кивни» ("wave", "nod") -> say again

**Driving:**
- «едь вперёд» ("drive forward") -> MOVE_TO forward. The bot walks.
- «поверни налево на перекрёстке» ("turn left at the junction"), «на втором перекрёстке направо» ("right at the second
  junction"), «развернись» ("turn around"), "turn around" -> LOOK_AT
- "take the next left", "take the second right" -> MOVE_TO
- «едь к банку», «едь к ресторану», "drive to the bank" -> MOVE_TO with no place: no such word, "Moving to the ping."
- «едь к моей метке» ("drive to my pin") -> MOVE_TO pin (right as a place; it walks)
- «подвези меня к банку» ("give me a ride to the bank") -> DELIVER; "give me a ride to the bank" -> HELP
- «припаркуйся» ("park") -> **KILL_YOURSELF**; "park here" -> HOLD_POSITION
- "stop the car" -> say again GET_OUT; «стоп» ("stop") -> WAIT (right)
- «быстрее» / "faster" -> RELOAD; «помедленнее» / "slow down" -> CROUCH (both say again)
- «садись в машину и едь к ресторану» ("get in the car and drive to the restaurant") -> GET_IN car, then MOVE_TO with no place

## 3. New intents: classifier v70, 71 -> 74 labels

- **BODY_MOVE**: a move of a body part, or a strike in place.
  - The decoder writes the console line of `ov.CoopBot.Body`. The grammar is at the top of `OVBodyStateComponent.cpp`.
  - Examples:
    - «подними правую руку на 90 и чуть влево, быстро» ("raise your right arm 90 and a little to the left, fast") ->
      `raise arm_r 90 left 20 speed 2`
    - «хук левой, сильно» ("left hook, hard") -> `hook left force 1.5`
    - «присядь» ("squat") stays CROUCH. A body squat needs an angle or the word body.
- **BODY_COMBO**: teach, play, forget or list a combo.
  - The decoder writes `teach <name> = step ; step`, `play <name>`, `forget <name>`, `combos`.
  - The name stays in the speaker's own words.
- **DRIVE**: an order for a car, whether the bot is in one already or has to get into one. The decoder writes canonical
  English:
  - "drive forward" (to the next junction);
  - "take the next left", "take the second left" (see section 10: no place words in the canon);
  - "turn around";
  - "drive to the bank", "drive to my pin", "drive there" (the crosshair); "drive me to X" means the same;
  - "park here" / "pull over";
  - "drive faster", "drive slower".

  Slots are set by rules in `world.py` and its C++ twin, which must stay at parity:
  - what: forward, turn, around, to, park, faster or slower;
  - side: left or right;
  - count: next = 1, second = 2;
  - place: as for MOVE_TO.
- **What the game reads from the reply** (built 2026-11-11, `OVCoopCommandComponent.cpp` OrderFromReply):
  - DRIVE: the order's `"drive"` (forward, turn, around, to, park, faster, slower, stop), `"count"` (a number), its usual
    `"direction"` (the side) and its place;
  - BODY_MOVE, BODY_COMBO: the order's `"body"` (the console line). With none, the reply's `"line"` is taken.
  - The console grammar the server runs: `ov.CoopBot.Drive` (AOVCoopBotController::DriveCommand) and `ov.CoopBot.Body`.
- **Chains.** «едь вперёд, поверни налево» ("drive forward, turn left") is two turns: DRIVE forward, then DRIVE turn left. The
  decoder already splits lines like this.
- **What does not change:**
  - GET_IN and GET_OUT;
  - «стоп» stays WAIT. In a car, WAIT means brake and stand.
  - On foot, «повернись налево» ("turn left") stays LOOK_AT unless it names a part or an angle (see section 7).
- **The scene line.** It tells the decoder "you are driving a car" or "the player sits beside you". Then «поверни налево»
  ("turn left") becomes "take the next left" only when the bot is driving.

## 4. Place vocabulary v16

- **New city words:**
  - bank, restaurant, cafe, shop, hotel, pharmacy, gas station, parking, junction or crossroads, traffic light, crosswalk,
    street or road;
  - ollaya-c1's open offer: counter, kiosk, bench, bin, ATM, parasol, menu, kitchen.
- **Trap.** "bank" is in a movement-word list today ("bank left" means veer). Read it as the place only after to, the or a.
- **The map.** L_OVModernCity has its restaurant (Best Burger) labelled, but the pack has no bank building. The only bank-like
  thing is `SM_Bankomat01`, an ATM.
  - First look at the map's shop signs.
  - If none of them is a bank, the owner picks the building that will be the bank.
  - Markers are placed by ollaya-c1's `build_modern_city.py` (OVMC_STAGE=places). Coordinate with ollaya-c1.

## 5. Game work (Lyra58: CoopBot and Vehicle)

Like the body commands, every piece below is first driven from the console (`ov.CoopBot.Drive ...`), so it can be tested
without the brain.

1. **Roads.** A road graph for L_OVModernCity: lanes with right-hand traffic, junctions and dead ends.
   - A headless script builds it from the map's road surfaces (survey them with ollaya-c1).
   - Check the result on a top-down picture.
   - A bend is not a junction.
2. **The driver.** A driving part for the bot's controller while it sits in a car:
   - it keeps to its lane (pure pursuit);
   - the speed follows the road ahead: slower before a turn, a stop at the junction's line;
   - it brakes for a person or a car ahead.

   The car is the AVS blueprint, driven by reflection. `StartEngine` and `SetThrottleInput` are already called in
   `LyraVehicleStatics`; the steering and brake function names still have to be read off the blueprint.
3. **Orders.** Each order ends on an event: a junction reached, the kerb reached, the car stopped. No timers I picked.
   - forward: drive to the next junction, stop, wait (the owner's rule).
   - turn left or right: turn at the next junction. If that junction has no such turn, stop and say so (my recommendation;
     see section 7).
   - second left: count the junctions that have a left.
   - around: a U-turn at a junction or a wide spot.
   - to a place: route on the road graph to the kerb nearest the place's marker, then stop.
   - park: pull over to the kerb and stop.
   - faster or slower: one speed step, within limits.
   - WAIT: brake and stand.
   - GET_OUT: stop first, then get out.
4. **On foot.** DRIVE makes the bot get into the nearest free car (FindVehicle and the GET_IN path), then drive.
   - No car within reach: it says "There's no car here." (my recommendation).
   - The player is at the wheel: the bot gets in beside the player.
5. **The passenger seat.** The second person in a car sits beside the driver.
   - Each car gets a seat socket and a passenger camera. A passenger can only get out; there is no driving input.
   - The player can sit beside the bot, and the bot beside the player.
   - This is in the owner's Vehicle code: `VehicleInteractionComponent` and the enter and exit abilities. Today they possess
     the car, which works for the driver only.
6. **Replies.** "Driving to the bank.", "Turning left at the next junction.", "There's no left turn here.", "There's no car
   here.", "Parking.", "We're here.".
   - Add them to `make_catalogue.py` and the five reply tables, then run `coop_cli --replies-check`.
7. **The body by voice.** A BODY_MOVE or BODY_COMBO order carries the decoder's line to the server. There it goes through the
   same parser as the console, `UOVBodyStateComponent::RunCommand`. A line the parser refuses: the bot says why.
8. **E2E tests:**
   - `drive_city.txt`, each case:
     - forward: stops at the junction;
     - forward, then left;
     - the second right;
     - to the bank;
     - to my pin;
     - park;
     - on foot, "drive to the restaurant";
     - the player as a passenger.
   - `body_voice.txt`.

## 6. Training (after sections 3 to 5)

- **Classifier v70.**
  - Seeds for the three new intents in ru, en and es.
  - Negatives:
    - turns on foot stay LOOK_AT;
    - «стоп» ("stop") stays WAIT;
    - «припаркуйся» ("park") never reads as KILL_YOURSELF;
    - «присядь» ("squat") stays CROUCH.
  - Piper voices, then the out-of-fold models and the finals: several hours of GPU.
- **Decoder v70.** Rows for the body grammar and for the drive lines, in ru, en and es, with a scene (car or no car) and with
  chains. They are added to v69s5's rows, with the v69 recipe.
- **Acceptance:**
  - test66 and test67, the owner test v69, the memory scenarios;
  - the diff of the owner's real lines (no regressions);
  - rule parity (world.py against C++) and the chain tests;
  - new held-out tests for the body and for driving, written blind.

## 7. Open questions for the owner

- «Поверни налево» ("turn left"), but the next junction has no left. Stop and say so (my recommendation), or drive on to the
  first left?
- After a turn, does the bot again drive to the nearest junction and stop? By the forward rule it does.
- Which building is the bank? The pack has none.
- Traffic. My default: the right lane, brake for people and cars, no traffic lights.
- «Повернись налево» on foot. My recommendation: it stays LOOK_AT (look there) unless a part or an angle is named.

## 8. Order of work

1. With ollaya-c1: the road survey and a bank marker on L_OVModernCity.
2. The game, through the console: road graph, driver, orders, passenger seat.
3. Place vocabulary v16, the rules, parity.
4. Rows and seeds, then the training (the owner's word, GPU).
5. Deploy, E2E, the owner's voice test.

## 9. Checklist: what a round that adds intents touches (from v55, v64, v66, v69; mapped 2026-11-11)

Paths are under `scripts/coop/` unless given.

- **The label list.** `make_spec_v70.py`, a copy of `make_spec_v66.py`'s pattern, writes:
  - `intents_v70.json`: the key order IS the label order, NONE last; all probability vectors are positional, so v67's
    out-of-fold files cannot be reused;
  - `seed_commands_v70.json`: seed ids unchanged; NEW_SEEDS, RELABEL_SEEDS, `_relabel_v70`.

  Seeds to re-label: "wave at me" (NONE), MELEE "punch him" / "kick him" (these stay MELEE: a strike at a target), "lower your
  gun" (HOLD_FIRE).
- **`coop_v2.py`.**
  - Add "v70" to every tag tuple V5 … V66 (lines 63-78).
  - Add V70 and NEW70, `_I` → `intents_v70.json`, and FAMILY entries (the assert on line 131 needs one per label).
  - Also SEED_FILE and PLACES.
  - Families: "body" is taken by BODY_STATE. BODY_MOVE needs its own family, and DRIVE must stay out of "move".
- **`coop_bot.py` LINES.** An entry for each new intent; without one, `gen_tests` / `gen_world_tests` raise KeyError.
- **Places.**
  - `locations.py`: add v70 to V60_TAGS (line 472) and to `vocab_file()` (line 486).
  - `make_places_v70.py` writes `locations_v70.json` (v16). Objects are positional in C++: only append.
  - "bank" is already in `words.dir_lead_lateral` and `dir_turn`.
  - A new word-list key needs `locations.cpp` / `.h` too.
- **Export and C++ tests.**
  - `export_cpp.py` (`--config-only` after a vocabulary change).
  - `cpp/coop_intent/tools/gen_tests.py:89` and `gen_world_tests.py:40`: add v70, plus a V70 block of PLAIN/WAYS lines.
- **C++ runtime.**
  - `coop_cli.cpp`:
    - kLines (1065-1141; a missing intent answers "Copy.");
    - Think (4215-4305);
    - kNotOrders (2986);
    - Hear and scene_look (2117-2128);
    - ReplyJson (5124-5202; the order JSON);
    - OrderStr ×2 (566-591; parity);
    - the protocol comment.
  - `src/world.cpp`: kPlaceIntents, kNoPlace, kPinDefault, kCarry (77-91), Fetched.
  - `world.h`: `struct Order` (183).
- **Order fields.**
  - `world.py` `Planner._order` (883-907) and every path that re-issues an order (corrections, answers, the queue, "go") must
    keep `drive` and `count`, as `item` is kept.
  - BODY_* go in NO_PLACE ("left 20" is no direction there). DRIVE goes in PLACE_INTENTS, but not in PIN_DEFAULT or CARRY.
  - A `drive_phrase.py` / `.cpp` twin with parity tests, as `time_phrase` has.
  - `body`: the decoder's line before lowercasing.
  - OrderStr: `/drive:…/count`, behind `o.contains(...)`.
- **Classifier round.** These scripts, named after v67's, become:
  - `export_v70.py` (seeds, lines);
  - `run_voices_v70.ps1` (synth, then Parakeet);
  - `build_v70.py`: COOP_TAG, OUT_DIR, the "_v70" tuples in `heard()`, the accent prefixes, the `finaloof70` names;
  - `run_build_v70.ps1`: out-of-fold ×3 and finals ×3;
  - `ensemble_bot_v70.py`: owner threshold 0.66; it also runs export_cpp and gen_tests.

  `train_v2.py` needs no change: it reads the labels from V.INTENTS.
- **Decoder.**
  - `chains14_v70.py` wraps `chains13_v69` (old rows are regenerated from code with fixed seeds) and appends
    `ml_v70/make_rows_v70.py`. Run it with `run_chains14_v70.ps1`.
  - Keep the new intents OUT of `ml_v67/frames`: that would shift the RNG and change the old rows.
  - The answer is the canon: check it through the brain.
  - The scene ("driving", "passenger") would touch:
    - C++: Scene, SceneLine, SceneFromJson;
    - Python: `chains9_v65.scene_text` / `scene_parts`, `chains11_v67.scene_parts_v67`, `measure_v67_cli.scene_json`.

    "A car 0 m away" already means "in the car".
- **Replies.**
  - Chat lines go in kLines. Game lines go in `replies/make_catalogue.py` GAME (105), whose CONFIG must point at
    `intents_v70` and PLACES at `locations_v70`.
  - Translate into `replies_ru` / `replies_es` / `replies_ru_brat` / `replies_es_brat` / `replies_en_brat`, then run
    `coop_cli --replies-check` on each.
- **Acceptance.**
  - `measure_all_v69.ps1` → v70, with v69s5 as the baseline.
  - `measure_v69_owner.py` and `replay_owner_talk.py`: BOT is hard-coded to ens3-v67.
  - `measure_v67_cli.py`: add BRAINS entries.
  - `measure_v68_time.py`: COOP_BOT.
  - `memory_tests.py`: `--bot` defaults to the deployed brain.
  - New blind tests: `ml_v70/test_v70_drive.json`, `test_v70_body.json`, scored on `order.drive` / `count` / `body`.
  - The C++ checks: `--golden --tokenizer-tests --location-tests --dialogue --gate-tests --decide-tests --world-tests
    --item-tests --time-tests --teach-tests --chain-tests --replies-check`.
  - Then `tools/deploy_brain.ps1`.
- **Traps.**
  - The teaching rules (`src/teach.cpp`: «запомни» / «забудь» / remember / forget) run before the classifier and will catch
    BODY_COMBO's teach and forget lines. The decoder already writes «забудь про X» as "never mind X".
  - The own-word overrides in `Hear()` (BackInOwnWords « назад », « обратно ») would turn «сдай назад» / «едь обратно» into
    GO_BACK.
  - FindTimePhrase cuts "wait 2 seconds" out of a combo line.
  - The game's car rules (`OrderFromReply` CarNear, SaysJump) and `world.py` PRIORS["GET_IN"] / FETCHED "car" meet DRIVE on
    foot.

## 10. The canon (what the decoder writes; decided 2026-11-11, before the rows are written)

The game runs these lines as they are (DRIVE through `DriveCommand`'s words; BODY_* through `UOVBodyStateComponent::RunCommand`),
so the canon IS the console grammar, lower case, numbers as digits.

- **DRIVE** (the order's `drive`, `count`, `direction` come from the canon by rules, `drive_phrase.py` / `.cpp`, parity-tested):
  - "drive forward": «едь вперёд», «прямо», «езжай дальше», "keep going";
  - "take the next left" / "take the next right": «поверни налево», «на перекрёстке направо» (no "junction": since vocabulary v16
    it is a place word, and "the next junction" made the planner ask which; no "car" either, the same way);
  - "take the second left" / "take the third right": «на втором повороте налево», «второй поворот направо»;
  - "make a u-turn": «развернись», «разворачивайся» (in a car; on foot «развернись» stays LOOK_AT);
  - "drive to the bank", "drive to my pin", "drive there": «едь к банку», «подвези меня к банку», «отвези нас к ресторану»;
  - "pull over": «припаркуйся», «встань у обочины», «тормози у тротуара»;
  - "drive faster" / "drive slower": «быстрее», «газуй», «помедленнее», «не гони»;
  - "hit the brakes": «тормози», «останови машину». A bare «стоп» / «стой» stays WAIT, as today (in a car: brake and stand).
  - The scene tells a car apart: "you are driving" (the bot at the wheel) or the player beside it. Without a car in the
    scene, «едь к банку» is still DRIVE (the game gets into the nearest free car), «поверни налево» stays LOOK_AT.
- **BODY_MOVE**, the console line:
  - «подними правую руку» "raise arm_r"; «подними руки вверх» "raise arms 180"; «разведи руки в стороны» "raise arms 90 out 90";
  - «опусти руки» "lower arms"; «поверни голову налево» "turn head left"; «наклонись вперёд» "lower torso";
  - «повернись всем телом направо на 90» "turn body right 90"; «присядь на 90 градусов» "lower body 90" (a bare «присядь» stays
    CROUCH, and so does «встань на колени»: "kneel" is a CROUCH seed); «подними правую ногу» "raise leg_r"; a turn with an angle
    and no part named is the whole body's: «повернись налево на 90» "turn body left 90" (a plain «повернись налево» stays LOOK_AT);
  - strikes in place, with no one to hit: «ударь ногой» "kick", «ударь кулаком» "punch", «хук левой» "hook left", «апперкот»
    "uppercut", «локтем» "elbow", «коленом» "knee", «головой» "headbutt", «прикладом» "butt"; force «сильно» "hard", «слабо» "soft";
    a target («ударь его», "punch him") stays MELEE;
  - manner: «быстро» "speed 2", «медленно» "speed 0.5", «резко» "sharp 1", «плавно» "sharp 0"; «расслабься», «вольно» "relax all".
- **BODY_COMBO**: «запомни связку двойка: джеб, потом прямой правой» "teach двойка = jab ; punch" (the name as said, the steps
  in the console's words); «сделай связку двойка», «покажи двойку» "play двойка"; «забудь связку двойка» "forget двойка";
  «какие связки ты знаешь» "combos". The memory's teaching rules (`teach.cpp`: «запомни», «забудь») must let a line with
  «связк» / "combo" / «комбо» through to the brain; the game's parser takes an optional word "combo" after teach / play / forget.
- **Game lines to translate** (make_catalogue.py GAME, five tables): every Say and Refuse of `OVCoopBotDriving.cpp` and "I can't
  move like that." (listed by grepping `Say(TEXT(` / `Refuse(TEXT(` / `OutSay = ` / `DriveArriveLine = ` there; the side and the
  ordinal are spelt out: "Turning left at the crossroads.", "Turning right at the crossroads.", "There's no left turn here." ...).

## 11. Results (2026-11-11)

All measured on the game's path (coop_cli --serve, the decoder on the CPU and on every line), against the deployed brain
(bot v67 + decoder v69s5, tag v69s5n70). Logs here and in ml_v68 / ml_v69 / stt (measure_all_v70.ps1 -Tag ...).

| | v69s5n70 (deployed before) | v70 (bot v70 + decoder v70) | v70c (bot v70c + decoder v70) |
|---|---|---|---|
| new test (200 lines: drive, body, combos) | - (the old bot has none) | 148/200 = 74.0% | 153/200 = 76.5% |
| owner test (47), with held / at once | 44 / 42 | 42 / 40 | 39 / 37 («сядь на диван» x3: CROUCH 0.59 < 0.66) |
| test67 intent / +target / +means | 80.8 / 74.2 / 70.0 | 78.3 / 72.1 / 69.2 | 78.8 / 72.5 / 69.6 |
| test66 | 96.4 | 93.2 | 93.8 |
| things (test68) | 88.6 / 82.1 / 81.3 | 89.4 / 79.7 / 79.7 | 87.8 / 79.7 / 79.7 |
| timer test, at once / with held (whole) | 92 / 98 | 93.8 / 100 | 93.8 / 100 |
| memory scenarios, the game's way (--decoder-every-line --all-chain) | 15 wrong of 44 | 5 | 5 |
| memory scenarios, round v69's way | 3 | 2 | 2 |
| the owner's 495 real lines vs v69s5n70 | - | 83 otherwise (~13 better, 16 worse) | 85 otherwise (v70 -> v70c: 40, mostly garbled lines) |

- The C++ checks of bot v70 all pass (golden 7361, world 16825, items, time 90, teach 484, replies 4436 x5); chain tests
  220/220 (CPU, 0.47 s a line).
- Game E2E drive_voice.txt (CoopBrainV70, a test folder: -ini override of BrainDirectoryV6): the body lines, the combos, get in,
  forward, left, brake, u-turn, the bank, the restaurant, get out all carried out. Fixed on the way: the bank (106 m from the
  start) was past PlaceRange 80 m, so the brain said "I don't see a bank": place markers have bLandmark now (the city's bank
  and restaurant), offered up to MaxOrderDistance.
- Found: a plain «повернись налево» / "turn left" / «gira a la derecha» on foot read BODY_MOVE "turn left" (the canon: LOOK_AT),
  and the body refused a turn with no part. Fixes: (1) bot v70b, the canon's turns among the seeds (make_spec_v70.py: 15 plain
  turns LOOK_AT, 8 partless turns with an angle BODY_MOVE; only the final models trained again, the gate and the numbers of
  v70's out-of-fold runs kept; the 279 v70 seeds' Kokoro and VCTK audio came out a little different on the second synthesis);
  (2) the game: a turn with no part is the whole body's.
- Found: «Давай к машине.» on foot -> "drive to the car" (DRIVE): run 1's rows made «давай к X», «ve a X», «vamos a X», «ve allí»
  drives in any scene. A decoder run 2 for it was started (11:20) and stopped and deleted at ~12:50 on the owner's word: walk or
  drive is the planner's to decide by where the bot is, not the decoder's (the game, CoopBot/README.md "Walk or drive"): at the
  wheel a walk to a far place or a landmark drives, a turn to a side is the junction's, a turn round the car's; on foot a drive
  to a car is a walk to it. The decoder stays v70 (run 1); «давай к банку» on foot drives (into the nearest car).
- Bot v70b still asked again on the bare "turn left" / "turn right" (the decoder's own words for «повернись налево»): bot v70c
  adds those and four like them as LOOK_AT seeds; the blind test's d_en_016 ("turn left") is no longer blind.
- **Deployed: v70c** (bot v70c + decoder v70 + coop_cli a5da85cf + the v70 reply tables) into Binaries\CoopBrainV6 on the owner's
  word, 2026-11-11 ~14:10 («Поставить в игру»), knowing the old tests' losses above. Backup of the brain before:
  Saved\CoopBrainBackup\v69s5_20261111 (whole: bot, chain, replies, exe, deployed.json). Chain tests 220/220 in place.
- Open: «сядь на диван» -> "Say again?" (the seeds have "sit" CROUCH, "sit down" NONE, "take a seat in X" GET_IN; the body
  seeds weakened it); the owner wanted to teach sitting himself, so no seed without his word. The car brakes hard 2-3 times
  by road 2's kerb barriers after a K-turn (the bumper's arc sweep), then drives on.
