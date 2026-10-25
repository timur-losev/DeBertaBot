# Translating the player's lines into Russian or Spanish (training data, round v64)

## The game

A tactical co-op shooter (think Rainbow Six Siege / Counter-Strike), now with farming and building too. The player gives
voice orders to an AI teammate, "the bot", through push-to-talk. The bot is getting a translator in front of it, a small
language model: a Russian or Spanish player speaks, and the model writes the orders in English.

## Your job

Translate the **player's English lines** into your language (`lang` in the file: `ru` = Russian, `es` = Spanish). Write each
line the way a native player would actually SAY it into voice chat in the middle of a game: spoken, short, natural. Do not
write it like a written translation.

The English answer the model must learn stays English. So the translation must keep **exactly the same meaning**:
- **The same orders, in the same order.** Two orders in English are two orders in your line; add none and drop none.
- **The same places:**
  - doors, windows, stairs, roof, basement, hatch, walls, floors, cars, crates;
  - colours, compass words, floor numbers ("red stairs" → «красная лестница» / «la escalera roja»; "north window" →
    «северное окно» / «la ventana norte»; "second floor" → «второй этаж» / «el segundo piso»);
  - "my pin / my marker / my ping" → «моя метка» / «мой пин» / «mi marcador» / «mi marca».
- **The same conditions and timing:** "on my go / on my mark / when I say" → «по моей команде», «по сигналу», «когда
  скажу» / «a mi señal», «cuando te diga». "Once it pops", "after you…", "first… then…" stay as they are.
- **The same negations:** "don't", "never", "no, not that one".
- **The same items** in farming and building: carrots, wheat, wall, fence, eggs, wood. "Build a pillar" is still a
  pillar.

Make it sound like players:
- **Russian:** informal «ты», imperatives. Use the slang players really say, **about half of the time**, and the plain
  word the other half, so that both appear:

  | Plain | Slang |
  |---|---|
  | кинь светошумовую | кинь флешку / флеш |
  | поставь дым | кинь смок |
  | кинь гранату | граник / гранату туда |
  | заходи и зачисти | пушь / штурмуй / рашь |
  | держи угол | держи / смотри за окном |
  | подави огнём | зажми их |
  | запусти дрон | продронь |
  | спустись по верёвке | ропни / на верёвку |
  | пробей стену зарядом | брич |
  | установи бомбу | плант / ставь бомбу |
  | обезвредь | дефузь |
  | подними меня | подними / рес |

- **Spanish:** «tú», imperatives. Neutral; mix Spain and Latin America freely. Players' words:

  | Plain | Players' word |
  |---|---|
  | lanza una granada cegadora | tira una flash |
  | pon humo | tira humo |
  | tira una granada | granada ahí |
  | entra y limpia la sala | entra / pushea / rushea |
  | vigila el ángulo | cubre esa ventana |
  | dispara de supresión | supresión |
  | lanza el dron | dronea |
  | baja en rápel | rapelea |
  | abre brecha | vuela el muro |
  | planta la bomba | |
  | desactiva | defusea |
  | levántame | |

- **Fillers** ("uh", "man", "bro", "dude") become your language's fillers («э», «слушай», «бро» / «eh», «tío», «bro»), or
  drop them.
- **Game names** ("Bandit", "Valk cam", "Echo", "AWP", "C4") stay as players say them.
- **Farm and build verbs:**
  - Russian: посади, полей, собери урожай, вспаши / прополи, покорми, собери, принеси / отнеси, построй, почини, снеси;
  - Spanish: planta / siembra, riega, cosecha, ara / desyerba, alimenta / da de comer, recoge, trae / lleva, construye,
    repara, derriba / tira abajo.
- **Speech-to-text slips** in the English line (for example "repel" for "rappel"): translate what the player meant.

## New in round v64: the bot that talks, carries, fights hand to hand and feels

The lines now also cover these orders and questions. Keep the meaning exactly; here is how players say them:

| Meaning (`intent`) | Russian (mix plain and slang) | Spanish |
|---|---|---|
| MELEE: beat someone up by hand | отпизди его, дай ему пизды, наваляй ему, втащи ему, отмудохай, врежь ему, ударь прикладом, набей ему морду | dale una paliza, pégale, cáscale, dale de hostias, reviéntalo a golpes, dale un culatazo |
| HOLSTER: put the weapon away, hands free | убери оружие, спрячь ствол, убери пушку, руки свободны, голые руки, без оружия | guarda el arma, enfunda, manos libres, sin armas |
| SWITCH_WEAPON: take a weapon OUT again | достань оружие, доставай ствол, вооружись | saca el arma, desenfunda |
| STATUS_REPORT: what do you see / how are you / sitrep | что видишь?, как обстановка?, доложи, как дела?, как там у тебя?, что там? | ¿qué ves?, ¿cómo va?, ¿cómo estás?, repórtate, ¿qué hay por ahí? |
| BODY_STATE: are you hurt / hot / cold / gas / ammo | ты ранен?, ты цел?, тебе не жарко?, не замёрз?, газом не пахнет?, патроны есть?, сколько патронов? | ¿estás herido?, ¿tienes calor?, ¿tienes frío?, ¿huele a gas?, ¿te queda munición? |
| PUSH: push / shove / slide a thing | толкни ящик, двигай коробку, подвинь ящик, пихни его к стене | empuja la caja, mueve la caja empujando, arrastra la caja |
| ROLL: roll a round thing (a cable spool, a barrel) | откати катушку, покати бобину к двери, прокати бочку | rueda la bobina, haz rodar el carrete hasta la puerta |
| DROP: put down what it carries, where it stands | поставь, брось, положи коробку, опусти ящик, отпусти | suéltalo, déjalo aquí, pon la caja en el suelo |
| COLLECT / DELIVER: pick up / carry a thing | подними коробку, возьми ящик, принеси коробку, отнеси туда, перенеси | recoge la caja, levanta la caja, tráeme la caja, llévala allí |
| SEE_THING / SEE_ME: do you see that / me | видишь это?, видишь меня? | ¿ves eso?, ¿me ves? |
| SMALL_TALK / PRAISE / KILL_YOURSELF | привет, спасибо / молодец, красава / убейся, самоубейся | hola, gracias / bien hecho / muérete, mátate |

- **Boxes:** "box", "crate" → «коробка», «ящик» / «caja». "Cardboard box" → «картонная коробка» / «caja de cartón»; "big box"
  → «большая коробка», «большой ящик» / «caja grande». "Cable spool" / "reel" → «катушка», «бобина», «барабан с кабелем» /
  «bobina», «carrete».
- **Teleport / portal:** «телепорт», «портал» / «teletransportador», «portal».
- Keep the boundaries: "push forward" (the bot moves) is not pushing a box («продвигайся вперёд»), "roll out" is "go" («погнали»,
  «выдвигаемся» / «vamos»), "drop down" is jumping down («спрыгни»), "drop him" is killing («сними его» / «tumbalo»).

## The file kinds

- **`single`:** one line, usually one order (or none: a callout, a question, an answer like "yes"). `intent` tells you
  what it means, so you keep it.
- **`chain`:** one line with several orders. `pieces` shows the separate orders in English, so you keep all of them in
  order. Translate only `en`.
- **`ctx`:** a line that leans on the talk before it. Translate `before` (the player's earlier lines, oldest first) and
  `en` (the line now), consistently, as one player talking. Do **not** translate `bot`: it is the bot's own line, given
  only so that you understand. Keep pronouns that point back ("put a smoke on it", "the other one", "again") as
  pronouns: the model must learn to resolve them.

## Output

Write a JSON file with the same name into `../out/` (the folder next to `in/`). Use the same `lang` and `kind`, and one
object per input item, with the same `id`:

    single, chain:  {"id": "...", "text": "<your translation of en>"}
    ctx:            {"id": "...", "before": ["<translation>", ...], "text": "<translation of en>"}

    {"lang": "ru", "kind": "single", "items": [ {"id": "r6_000", "text": "..."}, ... ]}

Every input id must be there exactly once. Write only the translations: no notes, no English, no alternatives. Write
the file with your file-writing tool, as UTF-8 JSON. Do not change any other file.
