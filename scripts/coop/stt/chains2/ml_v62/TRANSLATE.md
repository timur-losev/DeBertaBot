# Translating the player's lines into Russian or Spanish (training data, round v62)

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
