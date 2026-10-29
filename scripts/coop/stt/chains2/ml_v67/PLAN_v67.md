# Round v67: any thing with any order (plan, 2026-10-27)

## The owner's words

- 2026-10-27 ~20:30 (the test range, brain v66, Russian): «Залезай на стол» - "Which table?" - «На белый стол» = JUMP onto
  the white table, "Too high to jump on." though a crate stood by; then «Поставь коробку» = "Put the box down." = DROP,
  "I'm not carrying anything." The owner: «Давай пропускать все фразы через LLM» (in Russian every line already goes
  through the decoder; the cause was the game and the missing means).
- ~20:40: «Речь, чтобы подставить коробку и перелезть, может быть не только про стол, и вообще любой interaction. Можно
  подставить не только коробку, не только к столу и не только подставить, чтобы совершить какое-то действие. Нужно, чтобы
  всё это было обработано.»
- ~20:55: «Подготовь обучение языковой модели версии 67, но я хочу, чтобы не было никаких ограничений, что можно сделать с
  чем. Предмет есть предмет, и можно комбинировать. Если мы потом всем интентам обучим и на каждый интент сделаем
  отдельную комбинацию в тулинге, то не должно быть никаких проблем.»
- Asked what "the tooling" means: the owner chose **the data generator** (the decoder keeps writing English orders, now
  with the means: "climb onto the white table using the crate"; every intent x every object x every means in the
  generator), not tool calls.

Done before the round, the same evening: the JUMP order onto a top beyond the jump goes to the climb planner (a crate as a
step; game, change 203, built); a bare object is the one named last, 30 s fresh by the game's clock (planner rule, Python +
C++, parity equal, deployed 20:5x).

## The order: intent + target + means

An order line the decoder writes is the order's canonical English with an optional means phrase at its end:
"climb onto the white table using the crate", "jump over the fence using the spool", "break the window using the box",
"hide behind the car using the table". No combination is refused by the brain: the intent comes from the verb, never from
the object (the owner: "a thing is a thing"). The game decides how a means serves the order (a step for a top or a fence,
a thing carried or pushed along, a thing to hide behind, ...) and says when it cannot.

- **Rule set v9** (locations.py, C++ twin): a target of role `means` after "using", "with", "standing on", "stepping on"
  and an object word or a pointer ("using it", "with this one"). Never the primary place; never a question (a means the
  world has several of is the nearest, one it lacks is dropped and the game picks its own).
- **Planner** (world.py, world.cpp): the means grounded like a target (crosshair, it, memory, nearest); the order carries
  `means` (entity) and `means_object`.
- **coop_cli / game**: `order.means`, `order.means_object` -> FOVCoopOrder Means; the reach planner takes the named means
  first; other intents: game work after the round.
- **Scene "failed:"**: for 30 s after a refusal the game adds "failed: <the order's English>, <why>" to the scene line, so
  «Поставь коробку», "use the box", «а если по стулу?» become "<the failed order> using the crate / the chair".

## Data (the generator)

1. `lexicon_v67.py`: every object of vocabulary v12 (23) with its English words, Russian forms (nominative, accusative,
   genitive, dative, instrumental, prepositional, gender, pronouns) and Spanish forms (article, gender, a/de
   contractions); every qualifier as an agreeing adjective (Russian cases x genders, Spanish genders).
2. `frames/*.json` (FRAMES.md): per intent, its canonical English forms, spoken English, Russian and Spanish frames with
   case slots, and infinitives (for «используй ящик, чтобы залезть на стол»). Written per intent group.
3. `make_combos_v67.py`: per intent x object x qualifier x means x language rows: the decoder's rows (ru, es, en -> the
   canonical English with "using the X"), the context rows (a failure scene, a bare noun or a pronoun after a named thing),
   multi-order lines; the classifier's English seeds (spoken variants with and without a means). Every canonical English
   line is checked: bot v66 reads the intent (without the means phrase), the matcher finds the target and the means.
4. The held-out test `test_v67.json`, written blind by an agent (never trained on; rows equal to a test item dropped).
5. v66's leftovers (PLAN_v66.md "Left for v67") as hand rows where they are words.

## Models

- Classifier v67 (build_v67.py, v66's recipe, 71 intents, no new intent): + the combinatorial English seeds (a sample voiced
  by Kokoro / VCTK A and heard by Parakeet).
- Decoder v67 (chains11_v67.py on chains10_v66's rows): + the generated rows; SYSTEM_V67 adds the means and the failed
  scene.

## Measures

test_v67 (whole brain, intent + target + means), test66, scene65, the owner's v61 lines per time said at 0.66, the old
decoder sets within a point or two, all engine checks equal.
