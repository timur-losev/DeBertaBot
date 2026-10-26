# Round v66: what to fix (started 2026-10-26)

The owner's notes and what rounds v64/v65 left. Bot v65 readings are from the deployed ensemble
(`models/coop-deberta-v3-ens3-v65`, family gate 0.66).

## The owner's notes, 2026-10-26

"Move away, Go away, step away - бот бывает мешает пройти. Take it/this/that. Throw it away не понимает."

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
  the way", «отойди», «уйди с дороги», «apártate», «quítate»), its own family. The game: the bot steps 2–3 m to the side
  of the player's line of view and movement (the side with navmesh and no wall), then keeps following the player (the
  owner, 2026-10-26: "должен идти за мной").
  The boundary: "go away" as small talk ("go away, I'm busy") is still GIVE_WAY; "get out" stays GET_OUT (car / retreat).
- **Take it / this / that.** COLLECT seeds with a pronoun and no noun ("take it", "take this", "take that", "take this
  one", "grab it", "take it with you"); the crosshair or the last thing names it. Check that "take this way" / "take
  that road" stay MOVE_TO.
- **Throw it.** DROP seeds: "throw it", "toss it away", "chuck it", «выкинь», «выбрось», «tíralo».

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
