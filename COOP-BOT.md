# Co-op bot voice orders → one enum: which model, measured

The task: a co-op AI teammate in a Siege / Counter-Strike style shooter. The player pings markers and
gives English voice orders ("go through the window", "breach here", "flank via the ping", "hold that
angle", "hold the other angle"). The language layer only picks the enum; the bot's planner decides how
to carry it out. The game's owner accepts a literal, slightly dumb bot: **BREACH for ENTRY is fine**.
Not fine: an action from the wrong family, acting on something that was not an order, or acting early
on an order given "on my go".

**Answer, on 363 held-out lines from three blind authors.** Only NONE counts as "doing nothing"; every
other pick is an action. "Novel" = the 200 lines with no close copy in another author's set (see the
caveats).

| Situation | Use | Near-correct | Wrong family | Acts on a non-order | Near on novel lines | Latency |
|---|---|---|---|---|---|---|
| Day one, no labels, GPU | `decision:eos`, descriptions, threshold 0.52 | 62% | **2.2%** | 5.9% | **64%** | 244 ms GPU |
| Same, threshold fitted on labelled lines (0.36–0.40) | `decision:eos`, descriptions | **72%** | 5.8% | 11.8% | **70%** | 244 ms GPU |
| ~240 labelled lines, safety first, GPU | **family key**: logreg and decision:eos must name the same family | 63% | **0.3%** | 3.9% | 54% | 244 ms GPU + 0.7 ms |
| ~240 labelled lines, CPU only | **DeBERTa-v3-base fine-tuned** on them, out-of-fold threshold | 75.5% | 4.8% | 13.7% | 66% | 67 ms CPU |
| same, safety first | family key: logreg and gliclass:large | 49% | **0.3%** | 2.0% | 42% | ~190 ms CPU |
| No labels, CPU only | `gliclass:large`, phrase labels, threshold 0.38 | 57% | 5.8% | 11.8% | 57% | 189 ms CPU |
| "on my go" / "the other one" | a regex, not a model | 21/24 kept, 288/288 not invented / 26/30 found, 0/282 false (upper bounds) | | | | 0 |

Anything that is not near-correct and not an action is the bot doing nothing: in play, a "say again?"
bark.

- **decision:eos is the only model that works zero-shot**, and it holds on novel phrasings.
- **A char n-gram classifier trained on the studio's own lines is not a replacement for it.** It
  scores 97% near on lines that closely copy a training line and 66% on novel ones (decision:eos: 70%),
  and on the speech-to-text author it acts on 29% of non-orders. As a second key it is excellent: the
  pair makes one wrong-family action in 363 lines.
- **laya:en is the wrong tool here**: 64% near, but 27% wrong-family actions, and it acts on 49% of the
  callouts and chatter. With a threshold it keeps 40% near and still acts on 24%.
  laya:multilingual is last; Qwen 1.5B is next to last.

All code and data: [scripts/coop/](scripts/coop/).

## Setup

| | |
|---|---|
| Enum | 21 orders + NONE ([intents.json](scripts/coop/intents.json)) |
| Families (near misses) | assault (BREACH, ENTRY, VAULT_WINDOW, RAPPEL), utility (FLASH, SMOKE, FRAG), hold (HOLD_POSITION, HOLD_ANGLE, HOLD_OTHER_ANGLE, COVER_ME), move (FOLLOW_ME, MOVE_TO, FLANK), objective (PLANT, DEFUSE); DRONE, REVIVE_ME, FALL_BACK, WAIT, GO_NOW, NONE on their own. Fixed after the first test run, on the owner's instruction; `ok` (exact intent accepted) is reported alongside |
| Slots | timing (now / on my signal), reference (this / the other one / none) |
| Test lines | 3 blind authors × 121: a Siege diamond player (dense slang), a CS2 player (CS vocabulary), speech-to-text output of mixed players incl. non-native speakers ("beach" for breach, "repel" for rappel). Each wrote 4 per order, 8 "on my signal", 6 "the other one", 8 enemy callouts, 5 chatter, 6 negated orders, 4 compound orders, seeing only [blind/spec.json](scripts/coop/blind/spec.json) |
| Truth | the author's label + two annotators per author who never saw it: majority on 363/363, unanimous on 357 |
| Frozen before any test line existed | model vocabulary, dev sets, spec (sha256 in [frozen.txt](scripts/coop/frozen.txt)) |
| Models | laya:en, laya:multilingual, von:1.1, gliclass:large, nli (deberta-v3-large), decision:eos (pulled for this), Qwen2.5-1.5B via constrained decoding; a char 2–5-gram tf-idf logistic regression as the no-model control |

Metrics:
- **near** = two of three readers accept the pick, or it is in the same family as their majority.
- **wrong family** = the bot acted (anything but NONE) and it is neither accepted nor in the family.
- **acts on a non-order** = of the 51 lines whose majority reading is NONE (24 callouts, 15 chatter,
  11 negations, 1 other), the share where the bot picked anything but NONE.

**Caveats that shape every number.**
- All authors and annotators are agents of one model family. Their 98% unanimity is higher than human
  raters would reach.
- They repeat each other. 163 of the 363 test lines have a char-ngram cosine ≥ 0.5 to another author's
  line, 22 are exact copies, and 15 repeat the experimenter's dev lines verbatim although no author saw
  them. Anything trained on some authors' lines is therefore flattered on the others. Real players
  repeat callouts too, but by how much is unknown. This is why every table below also reports the 200
  **novel** lines.
- The spec shown to the authors names "on their call / when they say go / on three", which primes the
  exact phrases the timing regex keys on.

## Zero-shot: every model, 363 test lines

| Config | ok | near | wrong family | acts on non-order | near, novel | GPU ms | CPU ms |
|---|---|---|---|---|---|---|---|
| decision:eos, descriptions, argmax | 66 | 71 | 28.9 | 92.2 | 65 | 244 | 2 473 |
| **decision:eos, descriptions, thr 0.52** | 60 | 62 | **2.2** | 5.9 | 64 | 244 | 2 473 |
| nli, phrase labels, argmax | 63 | 69 | 28.1 | 25.5 | 69 | 28 | 1 256 |
| nli, phrase labels, thr 0.26 | 50 | 53 | 8.3 | 2.0 | 56 | 28 | 1 256 |
| laya:en, phrase labels, argmax | 55 | 64 | 27.3 | 49.0 | 58 | 20 | 226 |
| laya:en, phrase labels, thr 0.98 | 39 | 40 | 8.0 | 23.5 | 36 | 20 | 226 |
| **gliclass:large, phrase labels, thr 0.38** | 53 | 57 | 5.8 | 11.8 | 57 | 15 | 189 |
| von:1.1, phrase labels, argmax | 50 | 55 | 25.6 | 15.7 | 50 | 18 | 186 |
| Qwen2.5-1.5B, phrase choices, argmax | 42 | 55 | 29.5 | 37.3 | 57 | 179 | |
| laya:multilingual, phrase labels, argmax | 38 | 48 | 48.8 | 78.4 | 44 | 16 | |

Thresholds come from the experimenter's 56-line dev set, which was easier than the blind authors
(laya:en: 66% exact on dev, 55% on test). Every config, including code labels and descriptions, with
these columns: [results_coop_test.json](scripts/coop/results_coop_test.json).

What decides these numbers:

- **Callouts are the trap.** "two pushing through B apps" → ENTRY, "that wall's soft btw, they can
  spray through it" → BREACH: a callout contains an order's words, and the model reads the topic, not
  the speech act. Argmax decision:eos acts on 92% of the non-order lines; only the threshold makes it
  quiet.
- **Negations flip.** "don't breach, they got Bandit on it" → BREACH. Same cause.
- **Descriptions help only decision:eos.** For laya:en, von, gliclass and nli the one-line
  descriptions cost 15–26 near points; phrase labels alone are best, as in [GAME-BOT.md](GAME-BOT.md).
  laya:multilingual does not care either way.
- **Qwen with the menu in its context gets worse**: 46 near, acting on 98% of the non-orders.

## With playtest data: leave one author out

Two authors' lines (242) play the part of playtest recordings; the third author is the players you
ship to. Thresholds are fitted on the two, scored on the third, three times over
([crossval.py](scripts/coop/crossval.py), [combine.py](scripts/coop/combine.py),
[robustness.py](scripts/coop/robustness.py)).

| Method | near | wrong family | acts on non-order | near, novel | wrong family, novel | near, with a copy |
|---|---|---|---|---|---|---|
| logreg on char n-grams, threshold | **80** | 5.8 | 17.6 | 66 | 8.0 | **97** |
| decision:eos, descriptions, threshold | 72 | 5.8 | 11.8 | **70** | 6.5 | 75 |
| decision:eos, descriptions + 8 examples each, threshold¹ | 58 | 0.8 | 3.9 | 48 | 1.5 | 71 |
| **family key**: logreg + decision:eos (descriptions) | 63 | **0.3** | 3.9 | 54 | 0.5 | 75 |
| same-intent key: logreg + decision:eos | 59 | 0.3 | 3.9 | 50 | 0.5 | 71 |
| family key: logreg + gliclass:large | 49 | 0.3 | 2.0 | 42 | 0.5 | |
| family key: logreg + laya:en | 48 | 1.4 | 7.8 | 39 | 2.0 | |
| gliclass:large, threshold | 53 | 4.1 | 7.8 | 50 | 4.5 | |
| nli, threshold | 52 | 6.3 | 2.0 | 53 | 4.5 | |
| laya:en, threshold | 47 | 14.0 | 35.3 | 40 | 17.0 | |

¹ Its threshold is fitted only on the ~60 training lines not quoted in its own descriptions. Fitting
it on all training lines, as the first write-up did, scores the model on its own examples.

Per author, same metrics (near / wrong family / acts on non-order):

| Method | Siege player | CS player | speech-to-text |
|---|---|---|---|
| decision:eos, thr 0.52 (zero-shot) | 62 / 0.0 / 0.0 | 65 / 1.7 / 11.1 | 60 / 5.0 / 5.9 |
| decision:eos, fitted threshold | 74 / 5.8 / 6.2 | 75 / 5.0 / 11.1 | 67 / 6.6 / 17.6 |
| logreg, threshold | 82 / 5.8 / 6.2 | 78 / 1.7 / 16.7 | 79 / **9.9 / 29.4** |
| family key, logreg + decision:eos | 65 / 0.0 / 0.0 | 65 / 0.0 / 5.6 | 60 / 0.8 / 5.9 |

Learning curve of the logreg alone, threshold fitted by an inner 2-fold split of each training subset
(5 random draws each):

| Labelled lines | 66 | 110 | 176 | 242 |
|---|---|---|---|---|
| near | 36 | 46 | 60 | 75 |
| wrong family | 1.9 | 2.5 | 2.9 | 3.9 |
| acts on non-order | 9.0 | 12.5 | 13.3 | 17.6 |
| near, novel lines | 29 | 35 | 46 | 57 |

What this says:

- **The logreg's lead is recall of phrasings it has seen.** It is 97% near where a close copy exists
  and 66% where none does. On novel lines decision:eos is ahead (70 vs 66) with fewer wrong actions.
  On the speech-to-text author, the one closest to a real input pipeline, the logreg acts on 29% of
  the non-orders.
- **Examples in decision:eos's descriptions make it memorise.** Near on novel lines falls from 70 to
  48. They help only where the test line repeats an example.
- **The family key is the best safety point at useful coverage.** It uses decision:eos with
  descriptions only (244 ms, not the ~740 ms of the examples variant) and the 0.7 ms logreg. One
  wrong-family action in 363 lines, but 54% near on novel phrasings: the rest become "say again?".
  The same-intent key is not safer here (1 line against 1 line) and loses 4 points of coverage.
- **decision:eos (with examples) and the logreg differ on callouts and negations by one or two
  lines** (22/24 vs 20/24, 17/18 vs 16/18). They are not a meaningful split.
- **An "is this an order?" gate** adds nothing on top of a thresholded decision:eos (its AUC for orders
  vs non-orders is 0.93, but the threshold already does that job). In front of laya:en a decision:eos
  gate cuts actions on non-orders sharply, but decision:eos alone is better than that pair.
- **A negation word list** adds almost nothing once a threshold is in place.

## The classic approach: a fine-tuned BERT classifier

The decision models put the options in the input. The classic alternative puts them in the weights:
a BERT-family encoder with a 22-way output layer, fine-tuned on the studio's labelled lines. Same
protocol: two authors train, the third is scored. Hyperparameters were fixed in advance (20 epochs,
batch 16, lr 5e-5 base / 2e-5 large, max 64 tokens), 3 seeds each, no search. The confidence
threshold comes from 5-fold out-of-fold predictions over the 242 training lines, trained for the same
number of optimizer steps ([train_bert.py](scripts/coop/train_bert.py),
[eval_bert.py](scripts/coop/eval_bert.py)). Strict count; brackets are the range over seeds.
"Score" is the owner's criterion, near − 2 × wrong family.

| Method | near | wrong family | acts on non-order | score | novel: near | novel: wrong family | novel: score | latency |
|---|---|---|---|---|---|---|---|---|
| zero-shot decision:eos, thr 0.52 | 62.3 | 2.2 | 5.9 | 57.9 | 63.5 | 2.0 | **59.5** | 244 ms GPU |
| decision:eos, threshold fitted on labels | 72.2 | 5.8 | 11.8 | 60.6 | **69.5** | 6.5 | 56.5 | 244 ms GPU |
| logreg on char n-grams, threshold | **79.6** | 5.8 | 17.6 | **68.0** | 65.5 | 8.0 | 49.5 | 0.7 ms CPU |
| **DeBERTa-v3-base, fine-tuned, threshold** | 75.5 [74–77] | 4.8 [3–7] | 13.7 | 65.9 | 66.0 | 6.5 | 53.0 | **67 ms CPU** |
| DeBERTa-v3-base, no threshold | 83.3 [81–85] | 14.1 | 28.1 | 55.0 | 75.7 | 20.8 | 34.0 | 67 ms CPU |
| ModernBERT-base, no threshold | 75.6 [72–78] | 17.4 | 26.8 | 40.7 | 65.3 | 23.8 | 17.7 | 33 ms CPU |
| ModernBERT-large, no threshold | 73.7 [71–77] | 19.8 | 18.3 | 34.1 | 64.5 | 26.3 | 11.8 | 80 ms CPU |
| family key: DeBERTa + decision:eos | 60.8 | 0.5 | 3.3 | 59.9 | 52.7 | 0.3 | 52.0 | 244 ms GPU |
| family key: logreg + decision:eos | 63.4 | **0.3** | 3.9 | 62.8 | 54.0 | 0.5 | 53.0 | 244 ms GPU |

At equal risk (diagnostic only: a threshold swept on the test lines themselves, which flatters every
method alike), best near with at most 6.5% wrong-family actions:

| | all lines | novel lines |
|---|---|---|
| decision:eos (zero-shot) | 74.1 | **70.5** |
| DeBERTa-v3-base, fine-tuned | 79.5 | 67.8 |
| logreg char n-grams | **81.0** | 63.0 |
| ModernBERT-base / -large, fine-tuned | 70.6 / 64.1 | 55.3 / 51.8 |

What this says:

- **Fine-tuned DeBERTa-v3-base is the best classic model**: it beats the n-gram logreg on novel
  phrasings (paired bootstrap on argmax, +7.2 near, 95% CI [0.8, 13.5]) and both ModernBERTs by 10–11
  points. It runs at 67 ms per line on CPU.
- **It does not beat zero-shot decision:eos on phrasings it has not seen.** Raw argmax looks like a
  win (75.7 vs 69.5 on novel lines), but it comes at 20.8% wrong-family actions against 6.5%. At an
  equal risk decision:eos leads on novel lines at every level measured (2%, 4%, 6.5%), and on novel
  order lines at cosine < 0.3 (n = 30) it is 80.0 against 62.2.
- **Where phrasings repeat, labels win.** On all lines, including the ones with a close copy in the
  training authors, the logreg and DeBERTa are 5–7 points above decision:eos at equal risk.
- **ModernBERT under this recipe is weak** — but see the next section: part of that was the recipe.
- **The practical change: on a CPU-only game with a few hundred labelled lines, fine-tuned
  DeBERTa-v3-base replaces gliclass** (75.5 near at 4.8% wrong family, against gliclass's 57 near at
  5.8%), at 67 ms instead of 189 ms.

Traps hit on the way, both fixed and logged in [frozen.txt](scripts/coop/frozen.txt):
- transformers 5 loads `microsoft/deberta-v3-base` in its saved dtype, fp16. AdamW's eps (1e-8) then
  rounds to zero and the first step turns every weight into NaN; the first run predicted one class for
  everything. Loading in fp32 fixes it.
- A threshold fitted on models trained on one author (121 lines, half the steps) comes out far too
  low for the deployed model (DeBERTa: 0.32 against 0.54 out-of-fold), because the small models are
  under-confident. Fit it on out-of-fold predictions of models trained like the one you ship.
- 22 test lines are exact copies of another author's line; they are worth about 1 point on the pooled
  numbers and nothing on the novel slice.

### Each model with its own search

The fixed recipe above is BERT/DeBERTa convention (20 epochs, lr 5e-5/2e-5), while ModernBERT ships with
every dropout at 0.0 and its authors swept the rate and 1–10 epochs. So every model was searched again,
with nothing tuned on the held-out author ([select_bert.py](scripts/coop/select_bert.py)): inside the
242 training lines, 5 folds; for each learning rate one run per fold that predicts the fold after every
epoch; each (rate, epoch) pair is scored by near − 2 × wrong family on its out-of-fold predictions and
the best pair is trained on all 242 lines, 3 seeds. Two grids: the ModernBERT paper's (1e-5 to 8e-5,
≤ 10 epochs), then a wider one (8e-5, 1.2e-4, 2e-4, ≤ 20 epochs) because the first choices sat on its
edge. Weight decay 1e-5 for ModernBERT, 0.01 for DeBERTa.

Best near with at most the given share of wrong-family actions (oracle threshold on the test lines,
swept over every distinct confidence value -- a diagnostic that treats every method alike):

| Model and search | chosen rate / epochs | ≤ 2%: all / novel | ≤ 6.5%: all / novel | CPU |
|---|---|---|---|---|
| decision:eos, zero-shot | — | 58.4 / 64.5 | 74.1 / **70.5** | 2.5 s (244 ms GPU) |
| **DeBERTa-v3-base, wide search** | 8e-5 / 10–18 | **76.0 / 65.5** | **81.5 / 70.7** | 67 ms |
| DeBERTa-v3-base, fixed recipe | 5e-5 / 20 | 70.8 / 57.8 | 79.5 / 67.8 | 67 ms |
| DeBERTa-v3-base, paper grid (≤ 10 ep) | 8e-5 / 9–10 | 57.5 / 48.3 | 69.3 / 60.5 | 67 ms |
| ModernBERT-base, wide search | 1.2e-4–2e-4 / 15–17 | 69.4 / 55.7 | 75.7 / 62.0 | 33 ms |
| ModernBERT-base, paper grid | 8e-5 / 5–9 | 61.8 / 43.7 | 72.2 / 59.2 | 33 ms |
| ModernBERT-base, fixed recipe | 5e-5 / 20 | 60.3 / 44.5 | 70.6 / 55.3 | 33 ms |
| ModernBERT-large, wide search | 8e-5–2e-4 / 7–17 | 62.6 / 55.2 | 72.3 / 64.0 | 80 ms |
| ModernBERT-large, paper grid | 5e-5–8e-5 / 5–9 | 60.8 / 49.0 | 73.0 / 59.8 | 80 ms |
| ModernBERT-large, fixed recipe | 2e-5 / 20 | 55.3 / 44.8 | 64.1 / 51.8 | 80 ms |

Paired bootstrap, DeBERTa-v3-base (wide search) minus the other, at ≤ 6.5% (95% CI):

| | all lines | novel lines |
|---|---|---|
| vs ModernBERT-base, wide search | +5.8 [+0.3, +9.7] | **+8.7 [+2.0, +16.8]** |
| vs ModernBERT-large, wide search | **+9.2 [+3.8, +13.2]** | +6.7 [−0.2, +13.8] |
| vs decision:eos, zero-shot | **+7.3 [+1.5, +14.4]** | +0.2 [−8.5, +9.2] |
| vs DeBERTa-v3-base, fixed recipe | +1.9 [−1.7, +4.9] | +2.8 [−1.7, +7.8] |

What this says:

- **The first run did understate ModernBERT.** A proper search is worth about 5 points for ModernBERT-base
  (from a higher learning rate, 1.2e-4–2e-4, and 15–17 epochs, not from early stopping) and about 8–9
  for ModernBERT-large.
- **It does not close the gap.** With every model searched on the same grids, DeBERTa-v3-base stays
  ahead of ModernBERT-base on novel phrasings (+8.7, CI above zero) and of ModernBERT-large on all lines
  (+9.2), with the novel-line gap to large borderline. On 242 short, noisy lines and 22 classes,
  DeBERTa-v3 is the better backbone; ModernBERT's strengths (8k context, speed) do not come into play.
- **ModernBERT-large is unstable at high rates.** On the wide grid one fold chose 2e-4 and its seeds
  spread from near-collapse to good (near − 2 × wrong family from 1 to 56). The paper grid is the
  safer setting for it.
- **The search adds nothing measurable to DeBERTa** over its fixed recipe (+1.9 / +2.8, both CIs span
  zero), and the paper's 10-epoch cap hurts it: it wants 18–20 epochs on this data.
- **Against zero-shot decision:eos**: ahead on all lines (the repeated phrasings), no detectable
  difference on novel ones (CI about ±9 points). This is an oracle-threshold comparison. At the deployable
  out-of-fold threshold DeBERTa is slightly behind on novel lines, and its STT fold is weak (13.8%
  wrong family against decision:eos's 6.6%), because the selection's tie-break stopped that fold at
  epoch 10 of a 20-epoch schedule.
- **Selection noise is large.** Across seeds the out-of-fold criterion of one (rate, epoch) pair moves
  by more than the differences that decided the rate; averaging it over two or three seeds before
  choosing would make the search more reliable.

## Fine-tuning laya itself

laya keeps the options in its input, so a fine-tuned laya should keep the one thing a classifier with
labels in its weights loses: the menu can still change. To fine-tune it, laya:en was rebuilt in
PyTorch from ollaya's own files ([laya_torch.py](scripts/coop/laya_torch.py)): a ModernBERT-large
encoder, a question-type embedding added at every position, two pre-norm transformer layers over the
whole sequence, and a scorer read at each option's `[MASK]`. All 206 tensors load with none missing or
left over. On 12 co-op requests the copy matches ollaya's probabilities within 0.0035. On the squad
menu, which exercises layout.rs's per-option truncation, it gives the same answer on 45 of 46 lines,
with a maximum gap of 0.035 (fp16 in ollaya, fp32 here).

Fine-tuning ([train_laya.py](scripts/coop/train_laya.py)) uses laya's own format: the question, the 22
phrase labels as options, and the player's line. The loss is cross-entropy over the option logits, and
the option order is shuffled for every example so the model cannot learn "option 9 is breach". The
recipe was fixed in advance: lr 2e-5 (the head is already trained), 10 epochs, batch 16, fp32. The
protocol is the same as for DeBERTa + seeds: leave one author out, 3 seeds, the seed commands in every
training fold. Five held-out lines are verbatim seed commands; that affects both models equally, about
1.4 points.

| | near | wrong family | acts on non-order | ≤ 2%: all / novel | ≤ 6.5%: all / novel | CPU |
|---|---|---|---|---|---|---|
| **laya:en, fine-tuned + seeds** | 88.8 | 8.6 | **13.7** | 74.4 / 64.0 | 87.5 / 82.2 | 220–310 ms |
| DeBERTa-v3-base, fine-tuned + seeds | 89.8 | 8.7 | 24.2 | **82.8 / 76.2** | 89.6 / 82.5 | 67 ms |
| laya:en, zero-shot | 64.2 | 27.3 | 49.0 | 16.3 / 19.5 | 38.6 / 35.5 | 226 ms |
| decision:eos, zero-shot | 71.1 | 28.9 | 92.2 | 58.4 / 64.5 | 74.1 / 70.5 | 2.5 s |

The ≤ columns are the oracle equal-risk diagnostic with an exact threshold sweep.

- **Fine-tuning lifts laya to DeBERTa's level.** At ≤ 6.5% the difference is −2.1 [−7.2, +2.0] on all
  lines and −0.3 [−8.2, +8.5] on novel lines. Against zero-shot laya it gains 49 points.
- **It acts on non-orders almost half as often as DeBERTa** (13.7% against 24.2%, at argmax).
- **It ranks its own errors worse.** The confidence of its wrong actions has a median of 0.962, and
  32% sit above 0.99; DeBERTa's median is 0.640, with none above 0.99. The confidence AUROC for right
  against wrong picks is 0.86 against 0.93. So a threshold removes fewer of laya's errors: at ≤ 2%
  wrong family it keeps 74.4 against 82.8. That gap is a point estimate, with a CI of −8.4
  [−17.2, +1.2]. No temperature closes it, including laya's own calibration: ollaya's temperature for
  11+ options is 0.10, clamped to 0.5, which makes the logits sharper, not softer.
- **The shipped bots are not equally safe.** Measured on the same held-out predictions at their
  configured thresholds, laya at 0.60 gives 87.8 near with 7.2% wrong family, and DeBERTa at 0.78
  gives 84.3 near with 2.5%. To match DeBERTa's risk, laya needs a threshold near 0.99, where it keeps
  about 79 near.
- **The menu stays flexible.** On the squad bot's own menu (16 options with descriptions, never used
  in fine-tuning), per line ([squad_transfer.py](scripts/coop/squad_transfer.py)):

  | squad lines | n | zero-shot | fine-tuned |
  |---|---|---|---|
  | verbatim seed commands | 6 | 6 | 6 |
  | intents the co-op menu does not have (open fire, take cover, sitrep, stealth…) | 18 | 15 | **18** |
  | intents with a co-op counterpart, and NONE | 22 | 17 | 18 (+3, −2) |

  Fine-tuning did not hurt laya on options it never saw, and may have helped: "get behind the
  crates" → TAKE_COVER, "sitrep" → STATUS_REPORT. This is one seed and 18 lines (3 wins, 0 losses);
  the squad test was written by the experimenter.
- **Cost.** 1.7 GB fp32, 3–4× slower than DeBERTa on CPU, because every input carries all 22 options.
  To run inside ollaya, the weights would still have to be exported into ollaya's ONNX external-data
  layout; that was not done.

**When fine-tuned laya is the better choice.** The menu changes, or several menus share one model, and
a changed menu must work without retraining. It also reacts less to callouts. When safety at a strict
threshold or CPU time matters more, choose DeBERTa.

## The two slots: a regex beats every model

| Method | "on my signal" kept | "now" left alone | acts early on an on-signal order | "the other one" found | false "other" |
|---|---|---|---|---|---|
| **regex** | 21/24 | **288/288** | 3/24 | 26/30 | **0/282** |
| decision:eos | 22/24 | 152/288 | 5/24 | 26/30 | 0/282 |
| gliclass:large | 23/24 | 64/288 | 1/24 | 27/30 | 16/282 |
| laya:en | 20/24 | 76/288 | 7/24 | 24/30 | 9/282 |
| von:1.1 | 14/24 | 274/288 | 16/24 | 16/30 | 0/282 |
| nli | 24/24 | 212/288 | 2/24 | 26/30 | 132/282 |
| Qwen | 21/24 | 81/288 | 3/24 | 27/30 | 279/282 |

The patterns ([timing_rule.py](scripts/coop/timing_rule.py)) were written from the dev lines before
any on-signal or other-ref test line was read, but after the test set existed. Given the spec priming
and the dev overlap above, 21/24 and 26/30 are upper bounds. The timing regex misses "once I give the
word", "when I yell go" and "the second I say now".

The models either hear a signal everywhere or nowhere. For "I've got left, you get right" the regex,
decision:eos, gliclass and von miss "the other one"; laya:en and nli catch it. (Qwen also catches it,
but it tags 279 of 282 lines as "the other one".) The planner can resolve such lines from the player's
facing anyway.

"Hold the other angle" as its own enum value or as HOLD_ANGLE + reference=other scored 10/12 and 8/12
on decision:eos, a tie at this sample size. With the regex slot the flat value is not needed.

## v2: the bot covers itself and opens doors (24 intents)

The owner asked for three distinctions the 22 intents could not make:
- "cover me" versus the bot covering itself;
- the bot hiding, with its planner picking the spot;
- opening a door or window without going through it.

Two intents were added, and nothing was removed or renamed:
- **TAKE_COVER**: the bot protects itself — hide, get into cover, get down.
- **OPEN**: the bot opens a door, window, hatch or gate by hand and stays out.

Each has its own family, so mixing them up with COVER_ME / HOLD_* or with BREACH / VAULT_WINDOW
counts as a wrong-family action. That mix-up is exactly what the owner wanted fixed. The shipped v1
bot showed it on the owner's own lines: "open window" → VAULT_WINDOW, "hide there" → HOLD_POSITION.

**Data**, the same protocol as v1 ([make_spec_v2.py](scripts/coop/make_spec_v2.py),
[coop_v2.py](scripts/coop/coop_v2.py)):
- **What was frozen, and when** (hash log [frozen.txt](scripts/coop/frozen.txt)):
  - **Before any v2 test line existed:** [spec_v2.json](scripts/coop/blind/spec_v2.json), with the
    two new intents and sharper COVER_ME and NONE descriptions; the model vocabulary with the new
    families; 16 seed commands and 5 negations for the new intents; `make_spec_v2.py`.
  - **After the lines, before any result:** coop_v2.py (data, gates, scoring) and train_v2.py.
  - **Only after the study:** eval_v2.py. Re-running it reproduces both logs.
- **The same three personas each wrote 40 new lines** ([blind/v2/](scripts/coop/blind/v2/)):
  - 10 TAKE_COVER and 10 OPEN, including on-signal and "other" lines;
  - 10 boundary lines: COVER_ME, HOLD_ANGLE, VAULT_WINDOW, BREACH, ENTRY;
  - 4 callouts, 4 negations and 2 orders the bot has no intent for.
- **Annotation:** two blind annotators per author. There is a majority on 120/120 lines, unanimous
  on 119.
- **Re-reading the old lines:** one fresh annotator read all 363 v1 lines under the v2 spec. It gave
  no line a new intent, and it matched the v1 majority on 360. The adjudication rule for flagged
  lines in coop_v2.py was therefore never used.
- **Test set:** 483 lines. "Novel" = 215 lines whose nearest training line (another author's line or
  a seed command) has a char-n-gram cosine below 0.5.

**Protocol**: v1's, unchanged ([train_v2.py](scripts/coop/train_v2.py),
[eval_v2.py](scripts/coop/eval_v2.py)).
- Leave one author out, 3 seeds, the fixed recipe, all seeds in every training fold (~550 training
  lines per fold).
- The threshold is fitted per fold on 5-fold out-of-fold predictions over the training authors.
- The owner's limits were ≤ 200 ms per line and +2 GB of RAM over the v1 bot (0.8 GB), so three
  candidates were measured:
  - deberta-v3-base;
  - deberta-v3-large (lr 2e-5, the fixed recipe, not searched, no restarts);
  - "ens3": the three base seeds with their probabilities averaged.
- Two gates were measured:
  - "top": the top intent's probability;
  - "family": the mass of the top family, acting on that family's top intent. It was built for
    "break in" = BREACH 0.51 + ENTRY 0.47.

Rows marked v2 use the study's seed set; rows marked v21 use the seed set the shipped model is
trained on (below). Bold marks the best value in each column.

| Method (deployable threshold) | near | exact ok | wrong family | acts on non-order | near − 2×wf | v2 lines: near / wf | novel: near / wf |
|---|---|---|---|---|---|---|---|
| v1 bot as shipped (22 intents, 0.78) | | | | 12.5 (v2) | | 41.7 / 25.8 | |
| v2: base, top gate | 84.7 [83–87] | 83.8 | 2.5 | 8.9 | 79.7 | 86.4 / 2.2 | 79.7 / 3.3 |
| v2: base, family gate | 83.5 [80–86] | 82.3 | 2.7 | 9.8 | 78.1 | 82.8 / 3.1 | 77.8 / 3.9 |
| v2: large, top gate | 58.3 [31–80] | 57.3 | 1.9 | **4.0** | 54.5 | 65.8 / 1.1 | 57.8 / 2.5 |
| v2: ens3, top gate | 90.7 | **90.1** | 2.9 | 6.7 | 84.9 | 89.2 / 1.7 | 87.9 / 3.3 |
| v2: ens3, family gate | 90.1 | 89.4 | **1.0** | 6.7 | **88.0** | 88.3 / **0.0** | 86.5 / **0.9** |
| v21: base, top gate | 85.7 [84–87] | 84.7 | 2.5 | 8.9 | 80.7 | 85.0 / 2.5 | 80.5 / 3.6 |
| v21: ens3, top gate | **91.3** | **90.1** | 2.5 | 6.7 | 86.3 | **91.7** / 1.7 | **88.4** / 2.8 |
| **v21: ens3, family gate (shipped)** | 90.5 | 89.2 | 1.9 | 5.3 | 86.7 | 89.2 / 1.7 | 86.0 / 1.9 |

The v2 lines, at the shipped setting, in % of the lines:

| | shipped v2 bot | v1 bot |
|---|---|---|
| TAKE_COVER lines (n = 30): does it / says again / takes it for "not an order" | **83.3** / 6.7 / 10.0 | 0 / 43.3 / 20.0 (and 10.0 COVER_ME/HOLD) |
| OPEN lines (n = 30): does it / says again / takes it for "not an order" | **90.0** / 6.7 / 3.3 | 0 / 46.7 / 0 (and **43.3 BREACH/VAULT/ENTRY**) |
| COVER_ME lines → TAKE_COVER (n = 9) | 0 | 0 |
| assault-family lines → OPEN (n = 15) | 0 | 0 |
| NONE lines (callouts, negations, out-of-menu orders) → acts (n = 24) | 4.2 | 12.5 |

What this says:
- **The ensemble of three base models is the pick.**
  - Paired bootstrap of near − 2 × wrong family against one base model (top gate):
    - v2 seeds: +5.2 [+1.7, +8.5] on all lines, +8.2 [+2.5, +14.0] on novel lines;
    - v21 seeds: +5.6 [+2.8, +8.4] and +9.5 [+4.8, +14.1].
  - At equal risk (the diagnostic sweep, ≤ 2% wrong family, v21, same gate for both): 88.4 against
    85.8 with the top gate, 90.3 against 85.5 with the family gate.
- **deberta-v3-large, at the fixed recipe, is out.**
  - Seed 0 collapsed on two of the three folds: at argmax it answers NONE on 157 and on 161 of 161
    lines.
  - On the STT author all three large models are weaker: 64–78 near at argmax against base's 83–85;
    at the deployable threshold 39–65 against 76–83.
  - The remaining four models (seeds 1–2 on r6 and cs) are level with base at argmax: 87–94 against
    89–96.
  - Against base: −25.3 [−29.0, −21.6]. Large was not searched or restarted. A tuned large might do
    better, but it would not fit the budget next to an ensemble anyway.
- **The family gate is a coin flip.**
  - On the ensemble it lowered wrong-family actions in both seed sets (2.9 → 1.0 and 2.5 → 1.9).
    The score gain was +3.1 [+0.6, +6.0] with the v2 seeds and +0.4 [−1.7, +2.7] with v21.
  - On one base model the gain was −1.6 with v2 and +1.4 with v21.
  - The shipped model's gate was chosen by its out-of-fold criterion: family 432 against top 429.
- **Seed set v21 was added after the study, and it has a price.**
  - **Why:** base and ens3 sent the owner's "cover from behid" to TAKE_COVER, a wrong-family action
    (the bot hides instead of covering the player); large mostly answered "say again". The TAKE_COVER
    seed "cover yourself" is the likely cause, but that was not tested.
  - **Fix:** [make_seeds_v21.py](scripts/coop/make_seeds_v21.py) adds 8 COVER_ME seeds with a bare
    "cover". Base and ens3 were re-run with them; large was not.
  - **Effect:**
    - base and ens3/top improved;
    - both of the owner's "cover" lines now go to COVER_ME;
    - at the shipped setting (ens3, family gate), wrong-family actions rose from 5 to 9 of 483 lines,
      a v21 − v2 score change of −1.2 [−4.1, +1.7].
  - **The four new mistakes with a clear link to v21:**
    - "plant your feet and quit walking around": HOLD_POSITION → TAKE_COVER;
    - "I'm opening this door, you got me if someone swings?": COVER_ME → OPEN;
    - "lover me lover me im reloading": COVER_ME → REVIVE_ME;
    - "pop a smock on the stairs": SMOKE → OPEN.

    The STT fold's threshold also moved from 0.64 to 0.54, and two v1 lines turned wrong there. Two
    other lines were fixed.
  - **Order:** the re-run finished after the shipped model had been trained. It was a check, not a
    gate.
- **The owner's live-test lines are not a blind check.**
  - "find cover" and "open the door" appear in the owner's chat log and are also v2 seed commands.
  - The other probes are near copies of seeds (cosine 0.78–0.96 to the nearest seed): "go find
    cover", "hide out", "hide there", "open window", "breach window". Under the shipped setting they
    go to TAKE_COVER, OPEN and BREACH.
  - Only "break in" is novel (0.39). It goes to ENTRY.
  - "come here", "go there", "breach" and "dont breach" are v1 seed commands, kept as regression
    probes.
  - The blind evidence for the new intents is the 120 v2 lines.
- **Cost:**
  - three base models: 2.3 GB of working set (v1: 0.8 GB), loaded in 5.6 s;
  - one member per thread, 4 intra-op threads each (12 threads on the 10-core CPU): 45.6 ms median,
    55 ms p99;
  - one thread each (3 cores): 61 ms median, 81 ms p99;
  - in turn, 4 threads: 78 ms;
  - in turn, 1 thread: 123 ms median, 171 ms p99.

  One v1 model: 25.7 ms at 4 threads, 39.6 ms at 1 thread. The C++ engine reproduces the Python bot
  on 762 golden lines (probabilities within 3.3e-6), 8927 tokenizer lines, 2338 gate decisions, every
  branch of the bot's logic and a 66-line conversation ([cpp/coop_intent](cpp/coop_intent/README.md)).
- **Caveats:**
  - The authors and annotators are agents of one model family (119/120 unanimous).
  - ens3 is one realisation, with no spread over seeds.
  - The new intents have 30 test lines each; a 95% interval on 83% is roughly ±13 points.
  - The v1 seed commands were written after the v1 blind lines had been read. They are training-only,
    but the all-line numbers include that. The v2-line and novel columns are the cleaner estimates.

## v3: places on the map (callouts)

The owner's maps all have the same named places:
- a Main door; north, south, west and east doors and windows;
- blue, red, yellow, white and brown stairs;
- chairs, sofas, tables;
- a basement, a 1st floor, a top floor, a roof.

Players use these names in orders ("hold the north door", "take blue") and in callouts ("two on red
stairs"). More names will follow.

**Design: the names are not in the classifier.** The 24 intents do not change. A dictionary with
position rules ([locations.json](scripts/coop/locations.json), [locations.py](scripts/coop/locations.py))
finds the places in the line and hands the planner a record. A new callout is a new line in
`locations.json`, not a re-training.

What the planner gets for "i'll take the north door, you take the south window":

| target | role | primary |
|---|---|---|
| door / north | mine | |
| window / south | | yes |

- **Targets** come in line order, each as {object, qualifier, zone}.
- **Role** says whose place it is: `mine` (the player's), `them` (the enemy's), `from` (the place to
  leave), `not` (negated or corrected), `status` ("blue is clear"). The bot is not sent to a place with
  a role.
- **Primary** is the first target without a role.
- **Flags:**
  - `unknown_modifier`: the player singled out one object with a word the map has no name for ("the
    back door", "the blue door"). The planner must not fall back to the nearest one.
  - `unsure`: a lone colour or "main" followed by an unknown word ("the white van").
  - `other`: "I've got the north door, you take the other one".
- **A queued order keeps its places.** "smoke the west window on my go", then "go", executes at the
  west window.
- **Callouts still get a record.** Under NONE the places are contacts for the planner, not orders.

**Decisions taken for the owner** (written into [spec_v3.json](scripts/coop/blind/spec_v3.json)):
- "Go to the roof" without rope words is MOVE_TO, not RAPPEL.
- Three zones were added beyond the owner's list because players say them: `up` / `down`
  ("upstairs", "downstairs": relative to the bot) and `floor_2`. The planner maps them per map.
- "First floor" and "ground floor" are one zone.

**How it was built and measured** ([make_spec_v3.py](scripts/coop/make_spec_v3.py),
[eval_v3.py](scripts/coop/eval_v3.py), hash log [frozen.txt](scripts/coop/frozen.txt)):
1. **Design critique before any test line existed.** Three agents attacked the first matcher with
   about 600 lines of their own. On one critic's 254 lines the first version chose a wrong primary on
   78; the rules frozen as v1 choose a wrong one on 5. Those lines are now the developer's regression
   set ([locations_dev.json](scripts/coop/locations_dev.json), `python locations.py --dev`). It is
   tuning material, not a test.
2. **Frozen before the test lines:** the vocabulary, the rules v1, the spec, and 150 templated seed
   commands that put every place name into every kind of order
   ([seed_commands_v3.json](scripts/coop/seed_commands_v3.json)).
3. **Blind lines:** the same three personas wrote 50 lines each ([blind/v3/](scripts/coop/blind/v3/)).
   Per author:
   - 20 orders with one place;
   - 5 with an object and its floor;
   - 5 with two places where the bot's place is not the first;
   - 4 on-signal orders and 3 "other" orders;
   - 4 about an object the map has no name for;
   - 5 callouts;
   - 2 chatter lines using a vocabulary word in another sense;
   - 2 negations.

   Two blind annotators per author labelled the intent and the target. All 150 intents and all 150
   targets are unanimous.

**A. The matcher: primary target against the readers' target** (150 lines; exact = object, qualifier
and zone all equal)

| | all | r6 | cs | stt | flag `unknown_modifier` (readers mark 12) |
|---|---|---|---|---|---|
| rules v1, frozen before the lines | 88.0% (132) | 86% | 88% | 90% | raised on 7, all correct |
| rules v2, tuned on r6 and cs only | 96.7% (145) | 96% | 100% | **94%** | raised on 12, all correct |

- **The blind number is 88.0%.** With rules v1, plain orders with a place were 93% (56/60), two-place
  lines 67% (10/15), and chatter using a vocabulary word in another sense 0/6.
- **Rules v2** were written from the r6 and cs mismatches only:
  - relative-floor phrases ("the floor below");
  - "I said X" is not the player's own place;
  - a correction reaches back ("smoke blue, no wait, not blue, white");
  - "the spiral staircase" is flagged;
  - more ignore phrases ("through the roof").

  The stt author is the held-out check for v2: 94%, up from 90%. The r6 and cs numbers for v2 are
  upper bounds.
- **The 5 lines v2 still gets wrong:**
  - 2 chatter lines ("a Thermite main since year one"); both carry the `unsure` flag;
  - "rough" for roof;
  - "second story";
  - one double correction in speech-to-text output.
- **Speed and port:** the matcher takes 1.7 µs per line in C++. The C++ port gives the same record as
  Python on 8563 of 8563 lines.

**B. The shipped v2 classifier on the 150 lines** (it never saw them; shipped gate and threshold)

| input | near | exact ok | wrong family | acts on non-order |
|---|---|---|---|---|
| the raw line | 83.3 | 82.0 | 3.3 | 8.3 |
| attached qualifiers stripped ("hold the north door" → "hold the door") | 81.3 | 80.0 | 4.0 | 12.5 |

- **The classifier reads the raw line.** Stripping the names does not help: −3.3 [−8.0, +0.0].
- Replacing lone names or zones was dropped at the design stage, because it changes orders: "push
  main" → "push the door" reads as OPEN, and "go to the roof" → "go to there" loses RAPPEL.
- Most raw-line misses are "say again". The systematic wrong action is "get up on the roof" → RAPPEL.

**C. Re-training with the place lines** (leave one author out; training folds get the other authors'
v3 lines and the location seeds; three base seeds averaged; out-of-fold threshold per fold)

| | near | exact ok | wrong family | acts on non-order |
|---|---|---|---|---|
| v3 lines, shipped v2 bot (raw line) | 83.3 | 82.0 | 3.3 | 8.3 |
| v3 lines, re-trained ens3, top gate | 90.0 | 89.3 | 1.3 | 4.2 |
| v3 lines, re-trained ens3, family gate | **90.7** | 90.0 | 1.3 | 4.2 |
| the 483 older lines, re-trained, top / family | 89.6 / 91.1 | 89.0 / 90.1 | 1.7 / 2.3 | 4.0 / 6.7 |
| all 633 lines, re-trained, top / family | 89.7 / 91.0 | 89.1 / 90.0 | 1.6 / 2.1 | 4.0 / 6.1 |

- **Re-training is worth it on place lines.** Paired bootstrap of near − 2 × wrong family against the
  shipped bot: +10.7 [+3.3, +18.7] with the top gate, +11.3 [+4.0, +19.3] with the family gate.
- **It costs nothing on the older lines.** Against the v21 study: +0.0 [−3.9, +4.1] (top) and −0.2
  [−4.3, +3.7] (family).
- **The shipped v3 model** ([train_v2.py](scripts/coop/train_v2.py) `final ens3` under `COOP_TAG=v3`)
  is trained on all 633 lines and 383 seed commands. Its out-of-fold fit chose the family gate at
  0.52 (criterion 565 against 564 for top: a tie).
- **The comparison is not like for like in one respect:** the shipped bot runs at its fixed threshold
  (0.58), the re-trained one at thresholds fitted out of fold.
- **Still wrong after re-training** (14 of 150, 12 of them "say again" or a confident NONE): mostly
  speech-to-text lines ("beach west door", "red stares … the other stares"). One "get up on the roof"
  still goes to RAPPEL.

**Cost.**
- The v3 bot is the same size as v2: three models, 2.3 GB.
- One thread per model (3 cores): 39.4 ms median, 54.0 ms p99.
- 4 threads per model: 35.4 ms.
- Models in turn, 4 threads: 57.0 ms.
- The v2 section's latencies were measured about a third slower. Re-measured the same day as v3, the
  v2 bot gives 39.9 ms and 57.2 ms for the same two settings, so that earlier run was slow for a reason
  not identified (machine load is the likely one).
- The C++ engine reproduces the Python bot on 1062 golden lines (probabilities within 1.4e-6), 9227
  tokenizer and regex lines, 8563 place records, 2938 gate decisions, every branch of the decision and
  a 77-line conversation.

**Caveats.**
- The authors and annotators are agents of one model family: 150/150 unanimous targets is more
  agreement than human readers would reach.
- The spec names the places, so the authors' phrasings are primed by it.
- The matcher's rules were tuned once on two authors. Tuning them further needs new blind lines.
- Each author has only 2 chatter lines with a vocabulary word in another sense, so false places in
  chatter are barely measured.
- The planner side is not built: resolving a target to an actor, "which one?" questions, relative
  floors.
- Real speech-to-text will produce name variants the vocabulary does not have ("rough", "stares").
  They have to be harvested from the real engine.

## Recommendation

```
voice ─► STT ─► regex: timing (on my go?)        ─┐
               regex: reference (the other?)     ─┤
               decision:eos, descriptions, thr ───┼─► {intent, timing, reference} ─► planner (+ marker)
               + once labelled: logreg as a       │        disagreement / low confidence ─► "say again?"
                 second key on the family         ┘
```

- **Day one: decision:eos with phrase labels + one-line descriptions and a threshold.** It is the only
  model that is both accurate and quiet zero-shot, and it does not depend on having seen the phrasing.
  It needs a GPU slice: 244 ms on GPU, 2.5 s on CPU.
- **Label from the first playtest, and use the labels for two things:**
  - **fit the threshold** (0.52 → 0.36–0.40 took near from 62 to 72, at 5.8% wrong family);
  - **train the 0.7 ms logreg as a second key.** Act only when both name the same family: 0.3%
    wrong-family actions.

  Do not ship the logreg alone. Its recall depends on having heard the phrasing, and on STT-style
  input it fires on callouts.
- **CPU only:** no measured option is both fast and safe zero-shot. gliclass at 0.38 (189 ms) makes a
  wrong-family action on 5.8% of lines. With labels, fine-tuned DeBERTa-v3-base is the CPU choice
  (75.5 near at 4.8% wrong family, 67 ms); the logreg + gliclass family key reaches 0.3% but answers
  only half the orders. Neither matches zero-shot decision:eos on phrasings nobody has said before.
  With the seed commands and the v2 intents, three DeBERTa-v3-base seeds averaged are the shipped bot:
  90.5 near at 1.9% wrong family, 2.3 GB, 46–123 ms on CPU depending on threads (61 ms on 3 cores; section v2).
  The current bot is v3: the same ensemble re-trained with lines that name map places, plus a
  dictionary matcher that hands the planner the place (section v3). It runs in 40 ms on 3 cores.
- **Timing and "the other one" are code**, then checked by the planner. The models smear a one-word
  modifier across the whole sentence.
- **Do not put playtest lines into the descriptions as examples.** It raises the score on repeated
  phrasings and costs 22 points on new ones.
- **The threshold is the mic-policy dial.** Push-to-talk can run looser. An open mic needs the safe end,
  because most of what it hears is callouts.

## What this does not show

- Real player speech and a real STT engine. The STT author imitates one, and the authors are one model
  family that repeats itself.
- Other languages. laya:multilingual was the weakest model even in English.
- Compound orders ("smoke it and push"). One enum per line can only do the first action: 33–83% near
  on 12 lines, depending on method; the recommended day-one config gets 33%.
- A decision:eos bug that is not about text: on CUDA its runner fails every request that comes after
  more than 10 s of idle ("Scan node ... Subgraph has nodes running on device: <garbage> while
  parent graph node running on device: 1"), and sometimes crashes. It is a use-after-free in ONNX
  Runtime 1.26+: stream collections are pooled per thread, a Scan subgraph keeps a raw pointer to the
  caller's CUDA stream, and tokio retires ollaya's idle blocking threads after 10 s. Measured on the
  installed 0.7.1: 2, 5 and 8 s gaps pass; 12, 15 and 30 s gaps fail 18 of 21 requests. A one-line fix
  in ollaya (`crates/ollaya/src/main.rs`, a runner runtime whose blocking threads never retire)
  passed 18/18 on the same gaps and 134/134 under bursts, model churn and 15–120 s idles, with
  bit-identical probabilities. The first write-up blamed long option descriptions and capped them at
  400 characters; that was a false correlation with idle time. The cap is kept in `crossval.py` only
  so the published numbers reproduce, and successful answers were never affected.

## Corrections after review

Three independent reviewers checked this write-up against the result files, the method and a re-run
([robustness.py](scripts/coop/robustness.py) implements every fix). What changed from the first
version:

| First version said | Now | Why |
|---|---|---|
| logreg on ~240 lines "beats every model", ship it later | a second key only | its lead comes from lines with a close copy (97 vs 66 near); on novel lines decision:eos leads 70–66; 29% false actions on STT input |
| WAIT and HOLD_POSITION counted as doing nothing | only NONE | both are real orders; gliclass's "2% wrong family" was 5.8% under the strict count |
| decision:eos + examples, threshold fitted on training lines | fitted on unquoted lines only | it was scored on its own examples; honest number 58 near, 48 on novel lines |
| family key at 66 near, "244 ms" | 63 near with the 244 ms decision:eos | the first number used the ~740 ms examples variant |
| learning curve "overtakes at 8 lines per order" | 60 near at 176 lines with a threshold, 46 on novel | the curve was argmax only |
| "acts on callouts and chatter" | defined on the 51 NONE-majority lines | the formula never used the 57 kind-labelled lines |
| regex slots "written before the test existed" | before reading those test lines; upper bounds | the test set existed; spec priming, dev overlap |
| "Qwen is last" | laya:multilingual is last | the zero-shot table |
| decision:eos CUDA errors come from option descriptions longer than ~120 tokens | from more than 10 s of runner idle | reproduced by idle gaps alone; root-caused to ONNX Runtime 1.26+ and fixed in ollaya |

## Files

| File | What |
|---|---|
| [intents.json](scripts/coop/intents.json) | the enum as the models see it |
| [blind/](scripts/coop/blind/) | the spec the authors saw; their lines with labels (`author_*.json`) and without (`*_lines.json`) |
| [annot/](scripts/coop/annot/) | two annotators per author |
| [dev.json](scripts/coop/dev.json), [dev_slots.json](scripts/coop/dev_slots.json) | the experimenter's dev lines |
| [run_coop.py](scripts/coop/run_coop.py) | every model zero-shot; `--test` for the held-out numbers; scoring and families |
| [slots_tune.py](scripts/coop/slots_tune.py), [timing_rule.py](scripts/coop/timing_rule.py) | slot question forms per model; the two regex rules |
| [crossval.py](scripts/coop/crossval.py), [combine.py](scripts/coop/combine.py) | leave-one-author-out, examples, gates, combinations (loose count) |
| [robustness.py](scripts/coop/robustness.py) | strict count, novel vs copied lines, per author, honest thresholds, curve with threshold, logreg latency |
| `results_*.json`, `cpu_latency.json` | the numbers; this document's tables come from `results_coop_test.json` (rescored), `results_robustness.json`, `results_cpu_keys.json`, `results_timing_rule.json` |
| [make_spec_v2.py](scripts/coop/make_spec_v2.py), [blind/spec_v2.json](scripts/coop/blind/spec_v2.json), [intents_v2.json](scripts/coop/intents_v2.json), [seed_commands_v2.json](scripts/coop/seed_commands_v2.json) | v2: the 24-intent spec, vocabulary and seeds, frozen before any v2 test line |
| [blind/v2/](scripts/coop/blind/v2/), [annot/v2/](scripts/coop/annot/v2/) | v2 lines (3 × 40) with author labels, two annotators each, and the v2 re-reading of the v1 lines (`old_*_v2ann.json`) |
| [coop_v2.py](scripts/coop/coop_v2.py), [train_v2.py](scripts/coop/train_v2.py), [eval_v2.py](scripts/coop/eval_v2.py), [v1_on_v2.py](scripts/coop/v1_on_v2.py) | v2 data and scoring, training (cv / final), evaluation, the v1 bot on the v2 lines; logs `eval_v2.log` (the study), `eval_v21.log` (seed set v21, shipped) |
| [make_seeds_v21.py](scripts/coop/make_seeds_v21.py), [seed_commands_v21.json](scripts/coop/seed_commands_v21.json) | the post-study COVER_ME seeds with a bare "cover" |
| [locations.json](scripts/coop/locations.json), [locations.py](scripts/coop/locations.py), [locations_dev.json](scripts/coop/locations_dev.json) | v3: the map vocabulary, the place matcher, the developer's regression lines |
| [make_spec_v3.py](scripts/coop/make_spec_v3.py), [blind/spec_v3.json](scripts/coop/blind/spec_v3.json), [seed_commands_v3.json](scripts/coop/seed_commands_v3.json), [blind/v3/](scripts/coop/blind/v3/), [annot/v3/](scripts/coop/annot/v3/) | v3 spec (target modifier), seed set with location seeds, the 150 blind lines and their annotations |
| [eval_v3.py](scripts/coop/eval_v3.py), [v3_shipped.py](scripts/coop/v3_shipped.py), [shipped.py](scripts/coop/shipped.py), [v3_noharm.py](scripts/coop/v3_noharm.py) | v3 evaluation: matcher, the v2 bot on the place lines, re-training; logs `eval_v3_rules_v1.log` (first blind run), `eval_v3.log` |
