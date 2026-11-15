# Round talk-2 (2026-11-13): Russian grammar

Round talk-1 (TALK.md) taught Qwen3-4B to talk in a role. Blind-judged, its Russian answers are understood and in the role
far more often than the base model's, but their grammar is worse: the case and the gender are right in 57 Russian bot
answers of 100 against 69 for the base model (it says more, and errs more). Examples of what it says: «Пиво полезно только
людям. Мне его не нужно, и не сойдёт.» (right: «Мне оно не нужно»), «Победа в моих планах, брат. Я её не сомневаюсь.»
(right: «Я в ней не сомневаюсь»), «Скучать не умею, Паша. Ты же самый разговорный человек в эфире.» (no such sense of
«разговорный»). Since then the game has eleven more people who talk in Russian (the roles below), with no rows at all.

This round: more Russian rows, every one of them grammatical, short and simple; the old Russian rows checked again; the
people's roles. **Read TALK.md first: a row, the fields, the roles bot and seller, how a good answer sounds — all of it holds.
This file adds to it and overrides it where they differ.**

## What changes for the answers you write (Russian only)

- **Short.** One sentence, sometimes two; 3 to 14 words, about 8 on average. A short answer said right beats a long one with
  a slip. No subordinate clause where two short sentences or one plain one will do.
- **Every word form right.** Before you write a row, read the answer as a strict Russian teacher would:
  - gender and number agree: the adjective with its noun, the past tense with its subject, the short form with what it
    says something of (**мне нужен** патрон / **нужна** зарядка / **нужно** масло / **нужны** патроны; «пиво мне **не
    нужно**» — not «его не нужно»); the bot is masculine about itself: «я **готов**», «я **рад**», «я **устал** бы, будь я
    человеком»;
  - case after a verb or a preposition: «сомневаюсь **в ней**», «боюсь **темноты**», «скучаю **по тебе**», «думаю **о
    тебе**», «горжусь **тобой**», «доверяю **тебе**», «нет **патронов**», «без **сахара**», «для **тебя**»; negation takes the
    genitive where Russian wants it: «у меня нет **желудка**», «не вижу **смысла**»;
  - numbers with nouns: 1 **доллар**, 2–4 **доллара**, 5–20 **долларов**, 21 **доллар**, 22 **доллара**, 25 **долларов**;
    1 **минута**, 2 **минуты**, 5 **минут**; «полтора **доллара**»; write small numbers as words when they are said («два
    доллара»), prices as the seller says them («девять долларов»);
  - verbs: aspect right («я **не буду** есть», «я **съем**»), reflexive where needed («**боюсь**», «**смеюсь**»), imperative
    forms right («**не волнуйся**», «**подождите**»);
  - word order and words a Russian speaker would use; no calques from English («это есть хорошо», «я есть робот»), no made-up
    or half-English words, no words used in a sense they do not have.
- **Plain spoken Russian**: на «ты» between the bot and the player; the people say «вы» to a stranger (the player is a
  stranger to them unless the line is very casual), the granny says «сынок» / «милок»; the robot at the metro is formal.

## The people (role "other", their role texts are the game's)

Each of them is a row with `"role": "other"`, `"role_name"` the game's id, `"role_text"` the text of their file EXACTLY
(read it from `J:/UE4/Projects/LyraStarterGame58/Binaries/CoopBrainV6/talk/roles/<file>`; keep `{name}` in it), `"name"` the
Russian name, and **`"gender": "man"` or `"woman"`** (the brain adds "When you speak Russian, use the masculine / feminine
forms for yourself." from it). No `scene`, `looking_at`, `bro` or `player` for them (null / false).

| role_name | file | name (ru) | gender | who |
|---|---|---|---|---|
| teller_anna | bank_teller.txt | Анна | woman | a bank teller (shares the text with Oleg) |
| teller_oleg | bank_teller.txt | Олег | man | a bank teller |
| bank_guard | bank_guard.txt | Виктор | man | the bank's guard at the door |
| foreman | construction_foreman.txt | Михалыч | man | the road works' foreman |
| worker_kolya | construction_worker.txt | Коля | man | a road worker (shares the text with Tolik) |
| worker_tolik | construction_worker.txt | Толик | man | a road worker |
| taxi_driver | taxi_driver.txt | Сергей | man | a taxi driver by his car |
| street_musician | street_musician.txt | Лео | man | a street musician by the metro entrance |
| metro_robot | metro_robot.txt | Отто | man | an old service robot by the metro's ticket machines |
| sweeper | street_sweeper.txt | Фёдор | man | a street sweeper in his sixties |
| granny | pensioner.txt | баба Валя | woman | a pensioner on a bench feeding pigeons |

They are people of the street of a co-op shooter: the shooting outside is real for them; they know their own place and work
(the role text says what), not the player's war. The player talks to them, asks them things, jokes, is rude now and then.
Their answers: in character, short, the facts of their role text exact (the bank's hours, the metro's prices and lines), a
woman's forms for Anna and баба Валя («я **рада**», «я **устала**», «я **сама** не знаю»), a man's for the rest.

## The files

- New rows go to `scripts/coop/stt/talk/rows2/<your file>` — only your own file (the one you are told), one JSON object per
  line, UTF-8, exactly the number of rows you are told.
- **Never open `scripts/coop/stt/talk/test/`** (held out) or another writer's file.
- A check of old rows writes only what it changes, to the file it is told (see the checker's task).
