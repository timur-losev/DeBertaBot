# Frames v67: how each intent is said (the format)

One file per intent group in `frames/` (`A_move.json`, `B_things.json`, `C_combat.json`, `D_talk.json`), UTF-8, a JSON
object keyed by intent id. The generator (`make_combos_v67.py`) fills the slots with every object and qualifier of the
lexicon, adds the means (shared wrappers, not written here), and writes the decoder's rows (ru / es / en -> the canonical
English) and the classifier's English seeds.

```json
{
  "JUMP": {
    "target": "required",
    "canon": ["climb onto {T}", "jump over {T}"],
    "en": [["get up on {T}", 0], ["hop onto {T}", 0], ["vault over {T}", 1]],
    "ru": [["залезь на {T:acc}", 0], ["заберись на {T:acc}", 0], ["перелезь через {T:acc}", 1]],
    "es": [["súbete {T:a}", 0], ["salta por encima {T:de}", 1]],
    "ru_inf": ["залезть на {T:acc}", "перелезть через {T:acc}"],
    "es_inf": ["subirte {T:a}", "saltar por encima {T:de}"]
  }
}
```

- `target`: `required` (every frame has {T}), `optional` (frames with and without {T}; canon entries likewise), `none`.
- `canon`: the English the decoder writes and the classifier reads, 1 to 4 senses of the intent. Short imperatives in the
  words the bot already knows for the intent (seed_commands_v66.json, the intent's description). Every other list points
  into it by index.
- `en`: spoken English variants (what a player says into the mic), each with the index of its canonical sense. 6-15.
- `ru`: Russian, informal "ты" imperatives as gamers speak (залезай, лезь, давай на..., запрыгни), each with its canonical
  index. 8-20. Colloquial words welcome (тачка for машина is the lexicon's job, not yours).
- `es`: Spanish (Latin American and Spain mixed), informal tú imperatives. 6-12.
- `ru_inf`, `es_inf`: one infinitive frame per canon entry, same order, for «используй ящик, чтобы залезть на стол» /
  «usa el cajón para subirte a la mesa».
- Frames of an intent with `target: none` have no slots; `ru_inf`/`es_inf` still give the infinitive of each canon entry.

## Slots

| Slot | English | Russian | Spanish |
|---|---|---|---|
| {T} | "the white table" | - | "la mesa blanca", "el cajón" |
| {T:nom} {T:acc} {T:gen} {T:dat} {T:ins} {T:prep} | - | «белый стол», «белый стол», «белого стола», «белому столу», «белым столом», «белом столе» (on its own, after the preposition you write) | - |
| {T:a} {T:de} | - | - | "a la mesa blanca" / "al cajón", "de la mesa" / "del cajón" |

Write the preposition yourself: «на {T:acc}», «к {T:dat}», «за {T:ins}» (behind), «через {T:acc}», «в {T:acc}», «у {T:gen}»,
«с {T:gen}» (down from), «в {T:prep}». The lexicon gives the noun phrase only.

Do not write a pronoun for the target (the generator makes «на него», «súbete a ella», "climb onto it" itself), nor a
means ("with the crate", «по ящику»: shared wrappers), nor fillers («брат», "bro", «ну»: added by the generator).
