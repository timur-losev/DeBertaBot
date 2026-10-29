# Round v66: what to fix (started 2026-10-26)

The owner's notes and what rounds v64/v65 left. Bot v65 readings are from the deployed ensemble
(`models/coop-deberta-v3-ens3-v65`, family gate 0.66).

## The owner's notes, 2026-10-26

"Move away, Go away, step away - бот бывает мешает пройти. Take it/this/that - не понимал. Throw it away не понимает.
what is that/this/it - не понимает. не понимает как выйти." (the last two: the next section)

| Line | Bot v65 reads | Wanted |
|---|---|---|
| move away | MOVE_TO 0.66 (no place) | step out of the player's way |
| go away | HOLSTER 0.69 | step out of the player's way |
| step away | say again (HOLSTER 0.60) | step out of the player's way |
| move aside | MOVE_TO 0.95 (no place) | step out of the player's way |
| step aside | say again (TAKE_COVER 0.44) | step out of the player's way |
| get out of the way | say again (ROLL 0.60) | step out of the player's way |
| get out of my way, you're in my way | say again (HELP_INTERACTION 0.35, 0.28) | step out of the player's way |
| take it | MOVE_TO 0.84 | COLLECT (take = keep, the owner's choice of 2026-10-25) |
| take this | MOVE_TO 1.00 | COLLECT |
| take that | MOVE_TO 0.85 | COLLECT |
| throw it away | DROP 1.00 (fixed in v65; the owner heard v64) | DROP |
| throw it | say again (DROP 0.60) | DROP |
| throw that away | DROP 1.00 | DROP |

- **Out of the way.** No intent has it. Proposal: a new intent GIVE_WAY ("move away", "go away", "step aside", "get out of
  the way", "let me through", «отойди», «уйди с дороги», «дай пройти», «дай мне пройти», «apártate», «quítate», «déjame
  pasar»), its own family. Today «дай (мне) пройти» was HELP_INTERACTION: the bot walked up to the player and asked
  "What do I do?". The game: the bot steps 2–3 m to the side
  of the player's line of view and movement (the side with navmesh and no wall), then keeps following the player (the
  owner, 2026-10-26: "должен идти за мной").
  The boundary: "go away" as small talk ("go away, I'm busy") is still GIVE_WAY; "get out" stays GET_OUT (car / retreat).
- **Take it / this / that.** COLLECT seeds with a pronoun and no noun ("take it", "take this", "take that", "take this
  one", "grab it", "take it with you"); the crosshair or the last thing names it. Check that "take this way" / "take
  that road" stay MOVE_TO.
- **Throw it.** DROP seeds: "throw it", "toss it away", "chuck it", «выкинь», «выбрось», «tíralo».

## The owner's play of 2026-10-26 15:00-16:09 (brain v65, Russian; Saved/Logs/LyraStarterGame.log)

The owner's notes: "what is that/this/it - не понимает", "не понимает как выйти". The decoder's English below is the
deployed chain v65 replayed with the scene the game sent (coop_cli --serve, 2026-10-26).

| Line (heard) | Scene | Decoder v65 | Read | Wanted | Kind of work |
|---|---|---|---|---|---|
| «Что это?», «Что это такое?» (×5) | crosshair on a wall | "what is that" | say again (HOLD_ANGLE 0.61) | the bot names what the crosshair is on | words + game |
| «Выходи из комнаты.» (×2) | indoors | "Get out of the room." | say again (FALL_BACK 0.51) | leave the room / building | words + tooling |
| «Выходи отсюда.», «Выйди отсюда.», «Выходи отсюда, иди направо.» | indoors | "Get out of here." | FALL_BACK at the player ("here") | leave the room, then go right | words + tooling |
| «Дай пройти.», «Дай мне пройти.» | the bot in the way | "let them through", "Let me through." | HELP_INTERACTION | GIVE_WAY (above) | words |
| «Не отдавай мне её.», «Не кидай коробку.», «Не спускай коробку.» | holding a cardboard box | "don't give it to me", "don't throw the box", "Don't drop the box." | WAIT (a negation) | keep holding it (COLLECT) | scene rows |
| «Залезь ко мне.», «Залезь ко мне как-нибудь.», «Тебе где-то найти лестницу.», «Найди.» | the owner on a roof 3-4 m up, no navmesh to him | "climb up on me", "you need to find the stairs somewhere" | JUMP ("Point at it."), MOVE_TO | find a way up to the commander | tooling |
| «Прямо перед тобой, да.» | the bot asked "Which crate? Ahead, 3 m?" | (DROP) | DROP | the answer yes | the answer rules |
| «Перепрыгни все коробки.» | boxes around | | asked "Which crate?" | jump over them in turn | low |
| «Ты мой брат.» | | "You're my brother." | say again (SMALL_TALK 0.65) | SMALL_TALK | words |

- **"What is that / this / it"** («что это», «что это такое», «qué es eso»): a question, no order. The brain's reply
  carries state "what"; the game answers with the thing under the crosshair as the crosshair debug view names it ("A
  cardboard box.", "A cable spool.", "That's Tommy.", "An enemy.", "A car.", "Just a wall."), in the player's language
  (reply tables). Boundary: "what is that noise" / «что это было» stay small talk or a report.
- **Getting out of a room** («выходи из комнаты», «выйди отсюда», "get out of the room", "go outside", «выйди на
  улицу», «sal de aquí»): MOVE_TO outside, not FALL_BACK to the speaker. The game has no idea of "outside" yet: the
  nearest navmesh point with open sky above it (a trace up), or the room's door, then go on with the rest of the line
  («...иди направо»). "Get out" alone stays GET_OUT (car / retreat).
- **Holding and a negation** («не отдавай», «не кидай», «не спускай», "don't drop it", "don't give it to me") with
  "holding" in the scene: keep holding it (COLLECT), not WAIT. Decoder rows: scene "holding a ..." + negated
  drop / give / throw -> "keep holding it". Without the scene the v55 rule (a negation is WAIT) stays.
- **A way up to the commander** (the owner on a roof, no navmesh up there): look for stairs, a ladder or things to
  jump up on, else say so ("I can't get up there."). Tooling, not words; see the goal-oriented bot's phase 0 (P4 202,
  the planner's "what if" path).
- **Recognizer slips of the day** (Parakeet v3, Russian): «С меня оружие» (= «Сними / Убери оружие»: decoder "get
  the weapon off me", HOLSTER 0.36), «Залья на коробочку дает» (= «Залезь на коробочку, давай»), "I soda" (= «А
  сюда»), "Catti" (= «Кати»), "Brat." / "Prat." (= «Брат»), "Let's me" (= «Залезь»?). Rows with the heard forms.

## Glass is a window (the owner, 2026-10-27 00:05; Saved/Logs/LyraStarterGame.log lines 51057-51115)

The owner: "окно и стекло не одинаково боту, но ты должен сделать одинаково. И не помечает объект." L_Expanse's four
windows ARE the breakable glass panels in the ramps' floors (OV_GlassPanel_GC_*, markers Place_Window_01..04, object
"window", set at the panel's centre by mark_expanse.py).

| Line (heard) | Crosshair | The brain's gaze | Read | Wanted |
|---|---|---|---|---|
| «Разбей стекло.» | on the glass panel GC_..._1932604427 | window_61 | BREACH 0.87, no place: "No charges on me. Pushing in instead." | OPEN_FIRE @ window (the glass breaks when shot) |
| «Просто прострели его.» | the same panel, the bot in front of it | gaze_27 | OPEN_FIRE aim on the bot | OPEN_FIRE @ that window |
| «Прострелит о стекло.» (= «Прострели то стекло») | on the glass panel GC_..._1932641429 | gaze_30 | OPEN_FIRE at the crosshair point, no object | OPEN_FIRE @ window |

- **Words (training):** "glass" / "pane" / «стекло», «стёкла», «окно» / "vidrio", "cristal", "ventana" name the object window,
  the same as "window": the decoder translates «стекло» to "the window" (or keeps "glass" and the place matcher takes it
  as window), and the place matcher gets "glass" / "pane" as words of window. Rows: «прострели/разбей/выбей/расстреляй
  (это/то) стекло», «стреляй в стекло», "shoot/break/smash the glass", "shoot through that glass", «rompe el vidrio»
  -> OPEN_FIRE @ window, beside the owner's existing "shoot this window" lines (owner_lines_v61). The heard form
  «Прострелит о стекло» as a row. BREACH stays for doors and walls.
- **«Разбей стекло» = MELEE @ window (the owner's choice, 2026-10-27: «удар прикладом»).** «разбей / выбей / разбить
  стекло / окно», "break / smash the glass / window", «rompe el vidrio» -> MELEE @ window; "shoot / прострели" stays
  OPEN_FIRE. Game: MELEE today hits enemies and neutral NPCs only (v63). A butt strike on a window's glass must break it:
  walk up to the panel and strike (the glass is a GeometryCollection; the strike breaks it the way a shot does).
- **A correction keeps the thing: "no, with the weapon" (the owner's question, 2026-10-27).** Replayed on the deployed
  brain v65 (ru), the crosshair on window_61 throughout (scratchpad glass_followup.py):

  | Line 1 | Read | Line 2 | Decoder | Read |
  |---|---|---|---|---|
  | «Разбей стекло.» | BREACH "break the glass" | «Нет, оружием.» | "Use your weapon." | SWITCH_WEAPON: changes weapons |
  | «Разбей стекло.» | BREACH | «Нет, из оружия.» | "Use your gun." | SWITCH_WEAPON |
  | «Разбей стекло.» | BREACH | «Нет, стреляй.» | "Shoot." | OPEN_FIRE, no place: at the crosshair, not the window |
  | «Ударь окно прикладом.» | MELEE 0.59 < 0.66, "Ещё раз?"; window by gaze, "rifle" taken as the place weapon | «Нет, оружием.» | "Use your weapon." | SWITCH_WEAPON |
  | «Ударь окно прикладом.» | MELEE 0.59, "Ещё раз?" | «Нет, стреляй в него.» | "shoot him" | OPEN_FIRE, no place |

  The decoder has the last 5 lines (30 s) but never learned "no, <another way>". Rows (memory = the order before):
  «нет, оружием / из оружия / стреляй / прострели его / выстрелом» after MELEE on X -> "shoot the X"; «нет, прикладом /
  рукой / ногой» after OPEN_FIRE on X -> "hit the X with the butt"; the same for other pairs on one target (FRAG <->
  SMOKE <-> FLASH «нет, дымом», OPEN_FIRE <-> SUPPRESS). Without such an order before, «оружием» alone stays
  SWITCH_WEAPON / "use your weapon" and «нет» alone stays NO. Also: "butt of your rifle" / «прикладом» must not be read
  as the place weapon (the matcher took it: "* window; weapon").
- **Not marking the object (game, not training):** the crosshair was ON the glass panel and the brain got a free point
  (gaze_27, gaze_30) instead of the window. BuildWorld takes a window marker only within GazeAngle (7°) of the marker's
  point at the panel's centre, and close up, aiming at the panel's edge, is more than 7°. Fix: the crosshair hitting
  a window's glass actor (the GeometryCollectionActor whose bounds hold the window marker, or a marker field naming its
  actor) gives that marker as the gaze, the way `Thing` does for crates (OVCoopCommandComponent.cpp BuildWorld).

## "It" is the thing we talked about (the owner, 2026-10-27 01:18-01:20, L_OVTestRange, English brain) -- DONE 2026-10-27

Fixed in the rules, no training (the owner: «делай»): rule set v8 (the "it" pointer, memory first within 30 s, then the
crosshair) and the place vocabulary v11 (locations_v66.json: colours on tables); the v65 bot exported again, all C++ vs
Python checks equal, deployed to Binaries/CoopBrainV6 at 02:4x (cpp/coop_intent/README.md, "Rule set v8"). Left: "the
table" alone after the white table was named still asks "Which table?" (memory is read for pointers, not for a noun).

The owner: "если мы говорим о каком-то столе, а потом я говорю jump over it, то контекст тоже стол, не нужно думать, что
контекст то, куда я показывал." Log: "Can you see the white table?" -> "Which table? The one ahead?" -> "Yes." -> "So jump
over it." -> JUMP with no place; the game took "the thing it dealt with last" (a crate, OVPhysicsProp_2) or said "Point at
it." Replayed on the deployed brain (scratchpad it_table.py), three causes, none of them training:

- **"it" is no pointer.** locations.cpp `point_det` has this/that only: "Jump over that." -> `* @this`, grounded via
  memory to the table (last_entity); "Jump over it." -> no place at all, though the planner's last_entity is the table.
  Wanted: "it" after an order verb or a preposition ("jump over it", "go to it", "open it", "shoot it") = memory first
  (the last thing named or settled, within the decoder's 30 s), the crosshair only without one; "this/that" stay crosshair
  first. Not a place: "do it", "keep it up", "make it quick", "move it", "take it" (COLLECT's own), "drop / throw it".
  Python world.py/locations.py + C++ + parity.
- **Colours on tables.** `locations.objects.table.qualifiers` is empty: blue/red/yellow/white/brown are stairs' only
  (L_Expanse), so "the white table" is `[unknown_modifier]` -> "Which table?" from the nearest; the owner's "Yes" then
  settled the wrong table (asked yellow, got blue, 01:19:37). Colours for table (and crate, door).
- **The decoder only sometimes.** After "Go to the white table." it wrote "Jump over it." as "Jump over the white
  table."; after "Yes." the router (0.39-0.40) did not call it.

## Left from round v65 (chains2/ml_v65/PLAN_v65.md)

- "again" after getting off: the decoder writes «Запрыгни» after «Слезь» as "jump on it again", and the planner's
  "again" takes the last order's way (down). The game reads the words again for now; the rows should answer "jump up
  on it" there.
- Scene test misses: "Get down, get down!" on a spool written back as it is (cover); "Get in, get in!" MOVE_TO; bare
  "Again." / "Do it again." REPEAT; «Стой» / «Quieto ahí» HOLD_POSITION for WAIT; «¡Al suelo!» / «¡Cuerpo a tierra!»
  PRONE.
- The owner's v65 lines missed out of fold: "how we doing bro?", "how would you homie?" (STATUS_REPORT), "press it
  forward" (PUSH; v65 reads SUPPRESS), "come here and put it right there" (two orders: the chain's).
- The bot's words for getting down come from JUMP's lines ("Going over." / «Перепрыгиваю» for «Слезь»).
