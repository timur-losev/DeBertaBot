# Translating the bot's lines (replies_ru.json, replies_es.json)

The bot is an AI teammate in a tactical co-op shooter (also a farm and building game). The player gives spoken orders;
the bot answers in short radio-style lines and calls out what it sees. Until now it only spoke English. A Russian or
Spanish player now hears the bot in their language: the brain matches each English sentence the bot would say to one of
the templates in `catalogue_en.json` and says the template's translation with a Russian or Spanish voice (Piper TTS).

Your job: one table per language, `replies_<lang>.json`, that translates **every** sentence and **every** slot value
of `catalogue_en.json`.

## The voice and the tone

- The lines are spoken by a speech synthesizer to a player in the middle of a fight. Short, clear, natural spoken
  language of a teammate on the radio: what a Russian / Spanish-speaking player would expect a squad mate to say in a
  modern shooter. Not literary, not a word-for-word copy of the English; keep the meaning and the length.
- Address the player informally (ты / tú). Spanish: neutral Spanish that works in Spain and Latin America; avoid strong
  regionalisms.
- The bot is male (Russian past tense and adjectives about himself: masculine: «Понял», «Готов»).
- No abbreviations or symbols the voice would spell out (no «м», «т.е.», «%»): write words. Numbers come only from {n}.
- Where the English has three variants of one answer (kLines), keep three different natural variants.
- Gaming terms: use what players of the language say (Russian «флешка», «граната», «дым», «зачистить»; Spanish «flash»,
  «granada», «humo»). Keep it understandable for a casual player.

## The file format

```json
{
  "language": "ru",
  "sentences": {
    "On you.": "Иду за тобой.",
    "Which {object}?": "{object.which} {object}?",
    "The one {sector}, {n} m?": "{Sector}, в {n} {n:метре|метрах|метрах}?"
  },
  "slots": {
    "object": {
      "window": {"text": "окно", "which": "Какое", "acc": "окно", "gen": "окна"},
      "_other": {"text": "место", "which": "Какое", "acc": "место", "gen": "места"}
    },
    "sector": {"on the right": {"text": "справа"}, "_other": {"text": "там"}}
  }
}
```

- `sentences`: every `en` of `catalogue_en.json` as a key (copy it exactly, character for character), its translation
  as the value. One English sentence may become one or more sentences in your language.
- Slots in a translation:
  - `{slot}`: the slot value's `text` form.
  - `{slot.form}`: a named form of the value that you define (a case, a gender-agreeing word, an article: `{object.which}`,
    `{item.gen}`, `{object.art}`). Every value of that slot, `_other` included, must have every form your templates use.
  - `{Slot}` or `{Slot.form}` with a capital letter: the same, with its first letter made capital (start of a sentence).
  - `{n}`: the number, written as digits; `{n:one|few|many}` (Russian) or `{n:one|other}` (Spanish): the word for that
    number. Russian rules: one = ends in 1 but not 11; few = ends in 2-4 but not 12-14; many = the rest.
  - Use only the slots the English sentence has. You may drop a slot ("The one {sector}, {n} m?" may lose nothing, but a
    {where} you find awkward may go) - never invent one.
- `slots`: for each slot of `catalogue_en.json`, every listed English value as a key, and `_other` (used when the bot says a
  value the list does not have: open slots such as `item` get any word the player said). Each value is an object with at
  least `text`. Russian nouns need the cases your templates use (`acc`, `gen`, `prep`...) and agreeing words ("Какой /
  Какая / Какое / Какие"); Spanish nouns need their article or gender agreement (`ningún` / `ninguna`).
- **Gender across sentences.** A sentence is translated on its own: "Which window?" and "The one on the right, 23 m?"
  are two templates, and the second does not know the object. So a sentence without the slot must not agree with it:
  «Та, что справа?» / «¿La de la derecha?» would be wrong for a window or a car. Pick a wording without agreement:
  «Справа, в двадцати трёх метрах?» -> `"{Sector}, в {n} {n:метре|метрах|метрах}?"`; Spanish `"¿{Sector}, a {n} {n:metro|metros}?"`.
- `{Phrase}` is an order said back as the start of a sentence ("Move there.", "Open fire, on your pin.", "Ready to move
  there."). Translate each phrase as the bot's own short confirmation of that order, so that "{Phrase}." and
  "{Phrase}, {where}." read naturally (Russian: infinitive or first person, your choice, but the same style for all 57;
  "Ready to {phrase}." then needs a form: add `ready` to each phrase, e.g. «Готов {phrase.ready}.»).
- Context for each sentence is in its `source` field (which intent, when it is said). Use it.

## Check before you hand it over

- Every `en` of the catalogue is a key of `sentences`; every slot and every value of it, plus `_other`, is in `slots`.
- Every `{slot.form}` used anywhere exists on every value of that slot.
- Valid JSON, UTF-8, `ensure_ascii` off (real Cyrillic and accents).
- Read 20 random lines aloud in your head with a soldier's voice: short, natural, no tongue-twisters.
