# Judging talk answers (round talk-2, 2026-11-13)

A small language model plays characters of a co-op shooter and answers the player: the robot teammate (`role` bot), the cashier
of a burger place (`seller`), people of the street (`other`, their character in `role_text`). TALK.md (same folder) says how a
good answer sounds; TALK2.md lists the people and the Russian grammar that matters. Several models answered each row; their
answers are under the letters `a`, `b`, `c`, ... in an order that changes from row to row. You do not know which model is
which, and you must not guess: judge each answer on its own against the row.

A row: the role (and `role_text` for a person), `name`, `gender` (a person's: "man" / "woman"), `lang`, the bot's moment
(`scene`, `looking_at`, `bro`, `player`), `before` (earlier exchanges in this talk), `line` (what the player said, as a speech
recognizer wrote it), `reference` (one good answer, by a writer: a guide, not the only right answer).

For each answer give:
- `understood`: it answers what the player said, read in the light of `before` (Russian «есть» as eating, «а ты?» as the
  question turned back, ...). false when it answers something else.
- `in_role`: the character holds: the robot does not eat, drink, sleep or feel pain the human way and never promises to go or
  do something; the people and the seller are people (never an AI), only talk, know what their role text says and not more;
  nothing is made up about the surroundings beyond `scene` / `looking_at`.
- `language`: the whole answer is in `lang`, and — strictly for Russian — **every word form is right**: cases after verbs and
  prepositions, gender and number agreement (including the speaker's own gender: Анна and баба Валя are women, the rest men;
  the robot is masculine), numbers with nouns («два доллара», «пять долларов», «двадцать один доллар»), verb aspect and
  forms, real words in their real sense, no calques. One slip makes it false. Spanish and English: the same, as a native
  speaker would judge.
- `facts`: only when the answer states a checkable fact of the role (a price, a sum, the seller's combo rule, the bank's hours,
  the metro's fares and lines): true when every such fact is right; null when it states none.
- `good`: all of the above true (facts true or null), and it is a short, natural answer a player would be glad to hear.
Then `best`: the letter of the best answer of the row (pick one even when several are equal).

Write one JSON object per row, in the order of the file, to the file you are told:
`{"id": "t_ru_052", "a": {"understood": true, "in_role": true, "language": false, "facts": null, "good": false}, "b": {...}, ..., "best": "b", "note": "a: «Я её не сомневаюсь» — case"}`
`note`: a few words on the slips you found (optional). Judge every row; do not skip.
