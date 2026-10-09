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

  These four come from a slow run. Re-measured on 2026-10-04 on the same machine: 39.7 ms with one
  thread each and 56.8 ms in turn with 4 threads (section v3, Cost).

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

Players use these names in orders ("hold the north door") and in callouts ("two on red stairs"). More
names will follow.

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
  leave), `not` (negated or corrected), `status` ("blue is clear"). A place with a role is not a
  destination.
- **Primary** is the first target without a role. If every target has a role, primary is the first
  target and the line gives the bot no destination ("get off the roof": roof, role `from`). The
  planner must read the primary's role.
- **Flags:**
  - `unknown_modifier`: the player singled out one object in a way the map has no name for ("the back
    door", "the door on the left", "the blue door"). The planner must not fall back to the nearest one.
  - `other`: "take the other door", "I've got the north door, you take the other one".
  - `unsure`: a lone colour or "main" before a word the vocabulary does not know ("the white fence").
    Most flagged names are real places (6 of 8 in the first blind lines), so the flag means low
    confidence, not "no place".
- **A queued order keeps its places and its "other" slot.** "smoke the west window on my go", then
  "go", executes at the west window.
- **Callouts still get a record.** Under NONE the places are contacts for the planner, not orders.

**Decisions taken for the owner** (written into [spec_v3.json](scripts/coop/blind/spec_v3.json)):
- "Go to the roof" without rope words is MOVE_TO, not RAPPEL.
- Three zones were added beyond the owner's list because players say them: `up` / `down`
  ("upstairs", "downstairs": relative to the bot) and `floor_2`. The planner maps them per map.
- "First floor" and "ground floor" are one zone.

**How it was built and measured** ([make_spec_v3.py](scripts/coop/make_spec_v3.py),
[eval_v3.py](scripts/coop/eval_v3.py), hash log [frozen.txt](scripts/coop/frozen.txt)):
1. **Design critique before any test line existed.** Three agents attacked the first matcher with
   about 600 lines of their own. On one critic's 254 lines (144 adversarial, 110 ordinary) the first
   version chose a wrong primary on 78; the rules frozen as v1 choose a wrong one on 5. Those lines are
   the developer's regression set ([locations_dev.json](scripts/coop/locations_dev.json),
   `python locations.py --dev`). It is tuning material, not a test.
2. **Frozen before the test lines:** the vocabulary, rule set v1, the spec, and 150 templated seed
   commands ([seed_commands_v3.json](scripts/coop/seed_commands_v3.json)): 50 order templates, each
   filled with 3 places sampled from its list. That is 150 of the 486 template × place combinations,
   not every name in every kind of order.
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

   Two annotators per author labelled the intent and the target, and all 150 intents and targets came
   out unanimous. That is weaker than it sounds:
   - the two r6 annotation files are byte-identical;
   - an independent re-reading of the r6 lines on 2026-10-04
     ([reann_r6.json](scripts/coop/annot/v3/reann_r6.json)) gives the author's intent and target on
     all 50 and drops an accepted alternative on 3;
   - on every line the truth is the author's own label.

**A. The matcher: primary target against the readers' target** (150 lines)

- *exact*: object, qualifier and zone all equal.
- *usable*, on the 123 order lines: exact, and the primary carries no role and no `unsure` flag, so
  the planner gets a destination it may act on.

| rule set | exact | usable on orders | r6 / cs / stt (exact of 50) | |
|---|---|---|---|---|
| v1, frozen before the lines | 88.0% (132) | 83.7% (103) | 43 / 44 / 45 | **blind** |
| v2, after reading the r6 and cs lines | 96.7% (145) | 91.1% (112) | 48 / 50 / 47 | fitted to these lines |
| v3, after the review of v2 | 98.0% (147) | 99.2% (122) | 49 / 50 / 48 | fitted to these lines |

- **The blind numbers are 88.0% and 83.7%.** With rule set v1, plain orders with a place were 93%
  (56/60), two-place lines 67% (10/15), and chatter using a vocabulary word in another sense 0/6.
- **Rule set v2** was written from the r6 and cs mismatches. Its 94% on the stt author is not an
  independent check: both stt lines it fixes repeat idioms of the other two authors ("ping is through
  the roof", "my main"), and the three misses only stt has did not change.
- **Rule set v3** was written after two reviews of v2 (one on each machine;
  [review_v3/](scripts/coop/review_v3/)). What they found, all confirmed by re-running:
  - roles fired on ordinary orders: "cover me from the east window" (`from`), "stack up on the north
    door" and "put one on the north door" (`them`), "north door is yours, hold it" (`status`), "when i
    breach go through the south door" (`mine`). 6 of the 121 exact order lines had a role on the
    primary and 3 had `unsure`;
  - "on second thought" and "go to second door" were read as the second floor;
  - a floor attached to the next clause's object ("get to the basement, the door is open");
  - `unknown_modifier` was raised on "throw the smoke on window" and missed on "the door on the left";
  - speech-to-text forms without apostrophes ("hes", "theyre") carried no role.
- **Evidence for v3 that is not fitted, and its limits:**
  - Three critics wrote their own lines against v3 while it was being written
    ([rules/critic_v3/](scripts/coop/rules/critic_v3/)). Of 213 everyday orders and callouts written
    before any result was seen, 4 failed (1.9%): each a missing role on a one-place line, none a
    wrong primary. The rules were then changed with the critics' lines, so the final counts are
    in-sample (`python rules/check.py`): everyday 395 lines, 0 wrong primary and 5 wrong roles;
    speech-to-text style 246 lines, 37 wrong primary; adversarial 242 lines, 17 wrong primary and 43
    wrong roles. The last two sets are the known limits of v3.
  - The Mac review's fresh author (80 short lines, one AI author who is also the only labeller; the
    lines had not been read on the machine where v3 was written): exact 76 / 77 / 78 of 80 and usable
    65 / 66 / 68 of 70 orders for v1 / v2 / v3.
  - A blind number for v3 needs a second batch of blind lines. [eval_v3b.py](scripts/coop/eval_v3b.py)
    is ready for it; the lines have not been written.
- **The `unknown_modifier` flag.** The readers mark 12 lines. v1 raised it on 7: exactly the lines
  that reuse the spec's own examples ("the back door", "the left window", "the blue door"). On the 5
  with other wording it raised none, so its blind recall on new wording is 0 of 5. v2 and v3 raise
  it on 12 of 12, in-sample.
- **The 3 lines v3 still gets wrong:** "rough" for roof, "second story", and "a Thermite main since
  year one" (chatter read as the main door).
- **Speed and port:** the matcher takes 2 µs per line in C++ (median; p99 8 µs) and reads only the
  last 128 words of a line. The C++ port gives the same record as Python on 20201 of 20201 lines.

**B. The shipped v2 classifier on the 150 lines** (it never saw them; shipped gate and threshold)

| input | near | exact ok | wrong family | acts on non-order |
|---|---|---|---|---|
| the raw line | 83.3 | 82.0 | 3.3 | 8.3 |
| attached qualifiers stripped ("hold the north door" → "hold the door") | 81.3 | 80.0 | 4.0 | 12.5 |

- **The classifier reads the raw line.** Stripping the names changes 3 answers, all for the worse:
  near − 2 × wrong family goes down by 3.3 [−8.0, +0.0].
- Replacing lone names or zones was dropped at the design stage, because it changes orders: "push
  main" → "push the door" reads as OPEN, and "go to the roof" → "go to there" loses RAPPEL.
- Most raw-line misses are "say again". The systematic wrong action is "get up on the roof" → RAPPEL.

**C. Re-training with the place lines** (leave one author out; training folds get the other authors'
v3 lines and the location seeds; three base seeds averaged; out-of-fold threshold per fold; CUDA)

| | near | exact ok | wrong family | acts on non-order |
|---|---|---|---|---|
| v3 lines, shipped v2 bot (raw line) | 83.3 | 82.0 | 3.3 | 8.3 |
| v3 lines, re-trained ens3, top gate | 90.0 | 89.3 | 1.3 | 4.2 |
| v3 lines, re-trained ens3, family gate | **90.7** | 90.0 | 1.3 | 4.2 |
| the 483 older lines, re-trained, top / family | 89.6 / 91.1 | 89.0 / 90.1 | 1.7 / 2.3 | 4.0 / 6.7 |
| all 633 lines, re-trained, top / family | 89.7 / 91.0 | 89.1 / 90.0 | 1.6 / 2.1 | 4.0 / 6.1 |

- **Re-training helps on place lines, and the gain is one author's.** Paired bootstrap against the
  shipped bot, of the score near − 2 × wrong family: +10.7 [+3.3, +18.7] (top gate), +11.3 [+4.0,
  +19.3] (family gate). Of near alone: +6.7 [+1.3, +12.7] and +7.3 [+2.0, +13.3]. Per author
  (near, top gate; the score with its interval):

  | author | near, v2 bot → re-trained | score |
  |---|---|---|
  | r6 | 78 → 98 | +24.0 [+12.0, +38.0] |
  | cs | 92 → 90 | +6.0 [−8.0, +22.0] |
  | stt | 80 → 82 | +2.0 [−8.0, +12.0] |

  The r6 author's v3 lines are capitalised and punctuated, unlike its earlier lines, which the v2 bot
  was trained on. For the speech-to-text author, the closest to what the bot will hear, re-training
  changes almost nothing.
- **No net change on the older lines.** Against the v21 study: +0.0 [−3.9, +4.1] (top) and −0.2
  [−4.3, +3.7] (family). The answer changes on 38–39 of the 483 lines; a loss of up to about 4
  points is not excluded.
- **Intent and place together** (the Mac review, rule set v2): near intent and exact place on the
  same line on 132 of 150, against 121 for the v2 bot.
- **The comparison is not like for like in one respect:** the shipped bot runs at its fixed threshold
  (0.58), the re-trained one at thresholds fitted out of fold.
- **Still wrong after re-training** (14 of 150, 12 of them "say again" or a confident NONE): mostly
  speech-to-text lines ("beach west door", "red stares … the other stares"). "get up on the roof,
  I want somebody up top" still goes to RAPPEL.

**The final v3 model** ([train_v2.py](scripts/coop/train_v2.py) `final ens3` under `COOP_TAG=v3`) is
trained on all 633 lines and 383 seed commands. It never became the default bot.
- The model in the repository was trained on the MacBook (MPS): family gate at 0.60 (out-of-fold
  criterion 569 against 560 for top). The work machine trained its own on CUDA (family gate at 0.52,
  565 against 564); that one is not in the repository.
- **Known behaviour, from probes that are not blind** ([probe_v3.py](scripts/coop/probe_v3.py),
  `probe_v3.log`):
  - a smoke callout is carried out as an order: "<place> is smoked" → SMOKE on 47 names of 47 (the v2
    bot: 7 of 47);
  - "<place> clear" without a copula → ENTRY on 27 names of 30 (v2: 19 of 30);
  - the roof: "to / up to the roof" is MOVE_TO, "on / onto the roof" and a bare "roof" stay RAPPEL.
    The seed set kept the v21 seeds "get on the roof" and "go roof" under RAPPEL, against the spec;
  - "take blue" → ENTRY, while "take blue stairs" → MOVE_TO: the sampled seeds have only the stairs
    forms (seen on the CUDA-trained model);
  - the model is case-sensitive and saw mostly lowercase lines.

**v31: the seed set corrected, and the model trained with it**
([make_seeds_v31.py](scripts/coop/make_seeds_v31.py), `COOP_TAG=v31`). The seed set is the v3 set
with its 383 seeds kept (the two roof seeds relabelled MOVE_TO), plus 192 templated seeds (every
order template filled with places of every kind it allows, lone names included; the roof in every
MOVE_TO template), NONE templates for smoke and "clear" callouts, and 5 plain callouts: 580 seeds. It
was written after the blind lines and the probes had been seen, so every number below except the
fresh author's is "after tuning". The model (`models/coop-deberta-v3-ens3-v31`, trained on CUDA on
633 lines and 580 seeds): family gate at 0.62 (out-of-fold criterion 566 against 561 for top). The
owner made it the default bot on 2026-10-04 (`scripts/coop/bots.py`).

- **The probes it was written against** (`probe_v31.log`; a check that the fix took, not an
  evaluation):

  | | v2 bot | v3 (Mac) | v31 |
  |---|---|---|---|
  | "<place> is smoked" carried out as an order | 7 of 47 | 47 of 47 | 0 of 47 |
  | "<place> clear" carried out as ENTRY | 19 of 30 | 27 of 30 | 0 of 30 |
  | roof orders without a rope word → RAPPEL (grid of 42) | 40 | 18 | 0 (MOVE_TO on 33) |
  | "take <colour>" → MOVE_TO | 0 of 12 | not probed | 11 of 12 |
  | the plain order "smoke <place>" carried out | 30 of 30 | not probed | 30 of 30 |
  | the v21 seed commands in ALL CAPS: wrong family | 8 of 233 | 10 of 233 | 12 of 233 |

  Side effects seen on single phrases: "clear main" and a bare "clear" are now read as callouts (the
  v2 bot stormed); "clear the basement", "clear the room", "clear it" and "go clear the north door"
  are still ENTRY. "take main" stays under the threshold.
- **Cross-validation** (leave one author out, ens3, family gate; `eval_v31.log`) against the v3 study:

  | | near | wrong family | acts on non-order | score |
  |---|---|---|---|---|
  | all 633 lines, v3 → v31 | 91.0 → 91.2 | 2.1 → 2.4 | 6.1 → 7.1 | 86.9 → 86.4 |
  | the 150 place lines | 90.7 → 92.0 | 1.3 → 2.0 | 4.2 → 8.3 | 88.0 → 88.0 |
  | the 483 older lines | 91.1 → 90.9 | 2.3 → 2.5 | 6.7 → 6.7 | 86.5 → 85.9 |

  Paired difference v31 − v3 of the score: +0.0 [−6.7, +6.7] on the place lines, −0.6 [−4.6, +3.3] on
  the older lines. No change detected; a loss of up to about 5 points on the older lines is not
  excluded. Against the shipped v2 bot on the place lines: +11.3 [+0.7, +22.7]; per author near
  78 → 100 (r6), 92 → 96 (cs), 80 → 80 (stt).
- **The Mac review's fresh author** (80 lines; `eval_fresh.log`): v31 equals v3, near on 59 of 60
  place lines and on 20 of 20 plain orders, with one wrong-family action where v3 said again.
- **Checks:** ONNX equals PyTorch on 1259 of 1259 golden lines; the C++ engine equals the Python bot
  on 1259 golden lines (within 2.2e-6), 9428 tokenizer lines, 20204 place records, 3332 gate
  decisions, 140 decision steps and the 77-line conversation. 40.8 ms per line on 3 cores.

**Cost.**
- The v3 bot is the same size as v2: three models, 2.3 GB.
- On the work machine (i9-10900K), the CUDA-trained v3: one thread per model (3 cores) 39.4 ms median,
  54.0 ms p99; 4 threads per model 35.4 ms; models in turn, 4 threads, 57.0 ms.
- The v2 bot re-measured on 2026-10-04: 39.7 ms and 56.8 ms for the first and the last setting. The v2
  section's 61 ms and 78 ms came from a slow run (35–55% slower), for a reason not identified.
- The C++ engine with rule set v3 reproduces the Python bot, on the work machine: for the v2 bot,
  762 golden lines (probabilities within 3.3e-6), 8931 tokenizer lines (regex slots on 8927 of them),
  20201 place records, 2338 gate decisions, 140 decision steps and a 77-line conversation; for the
  Mac-trained v3 bot, the checks that need no model (9231 tokenizer lines, 20197 place records, 2938
  gate decisions, 140 decision steps). Its golden lines (1062) and its conversation were last run on
  the Mac, before rule set v3.

**Caveats.**
- The authors and annotators are agents of one model family, and the truth is in effect the author's
  label.
- The spec names the places, so the authors' phrasings are primed by it. A place called by a word
  outside the dictionary is not found.
- Rule sets v2 and v3 have no blind number on the project's own lines.
- Each author has only 2 chatter lines with a vocabulary word in another sense, so false places in
  chatter are barely measured.
- The timing regex reads "on two" as a count, also where a player means the second floor.
- The planner side is not built: resolving a target to an actor, "which one?" questions, relative
  floors.
- Real speech-to-text will produce name variants the vocabulary does not have ("rough", "second
  story"). They have to be harvested from the real engine.

## v4: the voice chain (a speech recognizer, and a bot trained on what it hears)

Until here every number is on typed text. On 2026-10-07/09 the chain was closed with a real recognizer, on
synthesized voices only; the details, every table and the commands are in
[scripts/coop/stt/README.md](scripts/coop/stt/README.md) (in Russian).

- **Engine: NVIDIA Parakeet TDT 0.6B v2 through sherpa-onnx** (the owner's choice; push-to-talk, minimum CPU
  i9-10900K). About 0.7 GB of RAM and about 200 ms after the key is released on 2 threads. With the v31 bot
  on 422 voiced lines (in-sample for the bot, so only the ranking counts) it scores 99 on clean synthetic
  voices and 72 on Piper/VCTK voices with regional accents; the light streaming engines (Moonshine,
  Zipformer) score 93-98 and 54-67.
- **Bot v4** (`models/coop-deberta-v3-ens3-v4`): the v31 data (633 lines, 580 seeds) plus 1456 Parakeet
  transcripts of the r6 and cs lines and the seed commands with their known labels, 12 epochs.
  Out of fold (a line is unseen typed and spoken), near − 2 × wrong family on the r6 and cs lines: 90.0
  typed, 86.0-88.9 through Parakeet from clean synthetic voices, 69.2 from VCTK speakers that are in no
  training set (near 79.1, wrong family 5.0%).
- **What the comparisons said** (one model, VCTK speakers never trained on): transcripts in training help;
  dropping the cs author's lines costs 20-27 points and the stt author's lines 3-5 more; stripping case and
  punctuation before the classifier costs 4-10; 12 epochs are not worse than 20, 8 are.
- **Limits:** synthetic voices only, no real speech; the check is softer than leave one author out; every
  choice was made on these same lines, so the numbers are "after tuning"; the fitted threshold (0.50, top
  gate) lets the bot act on 10-12% of non-orders on clean voices. v31 is still the default bot.

## v5 and v51: fire control, a plain "attack", directions, "look at"

On 2026-10-09 the owner tried the v4 bot in the C++ chat. "open fire", "don't shoot" and "stop shooting" had no
intent; "attack" split between ENTRY and BREACH and was asked again; "go down by stairs" and "go up by stairs"
gave the same place record. The owner's decisions: fire-control intents; "attack" as its own intent, the planner
choosing breach or shooting; all six directions; and, while the training waited for the GPU, the command
"look at ..." ("look at me", "look at sofa", "look at that window"). Done by the project's protocol: spec, seeds
and rules frozen before any test line ([frozen.txt](scripts/coop/frozen.txt)), blind authors and annotators.

- **Intents: 24 -> 29.** v5 adds ATTACK (the way is left to the planner), OPEN_FIRE and HOLD_FIRE, each in a
  family of its own; v51 adds LOOK_AT (a place, an object, the marked thing or a direction) and LOOK_AT_ME (the
  player), in one family. A 27-intent v5 bot was specified and frozen but never trained: v51 replaced it before
  any training. Specs: [spec_v5.json](scripts/coop/blind/spec_v5.json),
  [spec_v51.json](scripts/coop/blind/spec_v51.json).
- **"don't shoot" is an order.** HOLD_FIRE is a safe intent: the leading-negation guard lets it through. It acts
  at once, is never queued and does not drop the queued order; "hold fire until I say" queues OPEN_FIRE for the
  signal. That behaviour, and LOOK_AT_ME as its own intent, are the developer's choices.
- **Directions are the matcher's, not the classifier's: rule set v4.** A target gets a fourth field (up, down,
  left, right, forward, back): an object's ("the left window", "down the stairs", "the door behind you") or a
  target of its own ("go left"). A direction word counts only in listed contexts ("fall back", "right now",
  "two left", "go ahead" are not directions). Three critic agents read the first draft on their own lines
  ([rules/critic_v4](scripts/coop/rules/critic_v4)): missed directions 142 -> 30 of 569 lines, false ones
  211 -> 67 of 460, by the critics' scoring. On the 14,662 lines the project had, the places equal rule set
  v3's except that an unknown_modifier flag may become a direction and a place reported clear may become a
  status.
- **The matcher's blind numbers** (rules frozen first; primary target against the readers'):

  | lines | exact (place and direction) | place | direction where the readers give one | false direction |
  |---|---|---|---|---|
  | 180 v5 lines | 174 (96.7%) | 180 | 47 of 53 | 0 of 127 |
  | 90 v51 lines | 79 (87.8%) | 82 | 15 of 17 | 1 of 73 |

  Rule set v3 on the same lines: 127 and 65. On the v51 lines the stt author's mis-heard words ("so far" for
  sofa) cost most: 21 of 30, against 29 of 30 for each of the other two.
- **Lines.** 3 authors x 60 for v5 and x 30 for v51, two annotators each: all 270 unanimous on intent, place and
  direction -- AI readers of AI lines, weaker than it sounds. Every earlier line was read again under each new
  spec; three got a new intent (two OPEN_FIRE, one LOOK_AT) and were read by two adjudicators among decoys.
- **Bot v51** (`models/coop-deberta-v3-ens3-v51`): v4's recipe on 3768 lines (903 lines and 801 seeds typed,
  2064 Parakeet transcripts), 12 epochs; family gate, threshold 0.62. Out of fold, near - 2 x wrong family on
  the r6 and cs lines (602): 91.0 typed, 88.9-90.7 through Parakeet from clean synthetic voices, 71.9 from VCTK
  speakers in no training set (near 82.2, wrong family 5.1%). On the 422 lines v4 was checked on it is level
  with v4 (89.8 against 90.0 typed, 69.0 against 69.2 on the unseen speakers). The new intents, typed: ATTACK
  16/16, HOLD_FIRE 18/18, OPEN_FIRE 15/18, LOOK_AT 20/20, LOOK_AT_ME 11/12; on the unseen VCTK speakers one
  HOLD_FIRE line was heard as OPEN_FIRE and one the other way round. Tables:
  [scripts/coop/stt/README.md](scripts/coop/stt/README.md).
- **C++.** The engine got a twin of rule set v4 and of the HOLD_FIRE decision; a config without "directions"
  still runs rule set v3, so the earlier bots keep their files. v51: places 35447/35447 (9755 with a
  direction), decisions 190/190, golden 1750/1750, conversation 77/77.
- **Limits.** Synthetic voices only; the check is softer than leave one author out; the readers are AI; after
  the blind runs their mismatches were seen, so any later rule change is "after tuning". "turn around" gets
  LOOK_AT but no direction from the matcher. v31 is still the default bot.

## v52: "help", "check", "suppress" after the first test with a real voice

On 2026-10-09 the owner talked to bot v51 through the C++ voice chat (push-to-talk, Parakeet): 43 utterances,
the 38 distinct ones kept with the readings he asked for in
[owner_voice_20261009.json](scripts/coop/owner_voice_20261009.json). Speech-to-text and the chat worked. His
remarks were about understanding: REVIVE_ME takes too much and a label HELP is needed ("Help me here." was
REVIVE_ME 1.00); "check <something>" must be an order of its own ("Check that room." was asked again);
"suppress" and "suppressive fire" must be recognised ("Suppressive fire." was HOLD_FIRE 0.98, the opposite
order; "Suppress them." was DEFUSE). The same session showed weak refusals of things the bot has no order for
("Kiss me." 0.58 under a 0.62 threshold, "Be silent." acted on as HOLD_FIRE) and "Sneak into that room." acted
on as VAULT_WINDOW.

- **Intents: 29 -> 32** ([spec_v52.json](scripts/coop/blind/spec_v52.json)). HELP: the player asks for help and
  does not say with what, the planner works it out; a family of its own ("help me up" and "I'm down" stay
  REVIVE_ME). CHECK: the bot checks a place or a thing itself; a family of its own; the line between the
  looking intents is the verb (check / inspect / make sure is CHECK, look / face is LOOK_AT, watch / hold /
  cover is HOLD_ANGLE, a drone or scouting is DRONE). SUPPRESS: suppressive or covering fire, in the family
  "fire" with OPEN_FIRE -- the developer's choice.
- **Seeds: 801 -> 980, and they are not blind.** 179 new ones: the three intents (plain, with places, with
  directions, negated, on a signal), 34 things the bot has no order for under NONE, 6 quiet moves under
  MOVE_TO. One seed keeps its id under another label ("help me": REVIVE_ME -> HELP). They were written with
  the owner's lines on the table and some are near copies; the blind authors' lines that followed are blind.
- **One matcher rule, after tuning:** "cover my front" gives the direction forward. The blind logs of v5 and
  v51 did not change.
- **Lines.** 3 authors x 30, two annotators each: all 90 unanimous on intent, place and direction. Every
  earlier line was read again under the v52 spec; three became CHECK, all three readers agreeing. The matcher
  on the 90 lines, rules frozen first: exact 89, place 90, direction 9 of 10, no false direction.
- **Bot v52** (`models/coop-deberta-v3-ens3-v52`): v4's recipe on 4274 lines (993 lines and 980 seeds typed,
  2301 Parakeet transcripts), 12 epochs; family gate, threshold 0.60. Out of fold on the r6 and cs lines (662):
  90.0 typed, 87.5-89.1 through Parakeet from clean synthetic voices, 70.5 from VCTK speakers in no training
  set. On the 60 lines written for v52: 95.0 typed, 85.0 on the unseen speakers. HELP 12/12, CHECK 15/17,
  SUPPRESS 12/12 typed; 12, 15 and 9 on the unseen speakers.
- **The older lines cost something.** On the 422 lines v4 was checked on, v52 is below v51 on five of the six
  inputs, by 0.7 to 3.3 points (typed 88.6 against 89.8, Windows voices 85.8 against 89.1, unseen VCTK
  speakers 66.8 against 69.0): three more intents to tell apart. On the Windows voices it acts on 12.3% of
  the non-orders (v51: 9.2%). At threshold 0.70 the unseen-speaker criterion is 72.4 instead of 70.4 and the
  bot acts on 4.1% of non-orders instead of 8.2%.
- **The owner's lines:** 38 of 38 as he wants, none acted on wrongly; v51 in his live test had 30 of 38
  ([owner_voice_v52.log](scripts/coop/owner_voice_v52.log)). Not a blind number: the seeds were written from
  these lines.
- **A probe after the training** ([probe_v52.log](scripts/coop/probe_v52.log): 29 typed lines by the developer,
  25 of them not seeds). The three intents are picked on new wordings ("check the kitchen", "check six",
  "cover fire", "keep them busy"); "sneak up to the window" and "crawl to the door" are MOVE_TO (v51: RAPPEL);
  "do a backflip" is asked again (v51 acted: FLANK). **One regression:** "check fire" and "check your fire" --
  an order to stop shooting -- were HOLD_FIRE 1.00 in v51 and are CHECK 0.60 in v52. Not fixed.
- **C++.** v52: tokens 10188/10188, places 35623/35623 (9789 with a direction), gates 4852/4852, decisions
  190/190, golden 2019/2019, conversation 77/77; 39.5 ms on three cores.
- **Limits.** Those of v51. The family gate sums probabilities inside a family, so it can act on a weak top
  intent ("Sneak into that room." in v51: VAULT_WINDOW 0.37, family mass 0.78); v52 fixed that line with
  seeds, the gate is unchanged. v31 is still the default bot.

## v53: "jump", "check fire" and "another angle" after the test of v52

The same day the owner talked to bot v52 ([owner_voice_20261009b.json](scripts/coop/owner_voice_20261009b.json)).
"Jump down." was acted on as VAULT_WINDOW -- "not the window label, just jumping down"; "Another angle." was
asked again; "Keep another angle." was a coin toss between HOLD_OTHER_ANGLE and HOLD_ANGLE. The developer's
typed probes ([probe_pre_v53.log](scripts/coop/probe_pre_v53.log)) widened it: every jump, drop or climb that is
not a window or a rope was acted on as VAULT_WINDOW or RAPPEL -- the data had no such move, so the words were
learnt from the window and rope lines alone; "check fire" had become CHECK; "we're taking fire" was acted on as
HOLD_FIRE; "hold this angle i'll take the other one" was HOLD_OTHER_ANGLE, because no HOLD_ANGLE line of the
data had the word "other".

- **Intents: 32 -> 33** ([spec_v53.json](scripts/coop/blind/spec_v53.json)). JUMP: the bot jumps, drops or
  climbs with its own body -- down, up, over or onto something; where to is in the place record ("jump down" =
  direction down, "jump over the sofa" = sofa). The developer's choices: the family "move" with MOVE_TO;
  climbing included; no rope word, no RAPPEL (as "go to the roof" without a rope is MOVE_TO), so "drop down from
  the roof" is JUMP now. VAULT_WINDOW, RAPPEL, MOVE_TO, HOLD_FIRE, CHECK, HOLD_ANGLE, HOLD_OTHER_ANGLE and NONE
  are sharpened against it and against the probes.
- **Seeds: 980 -> 1146, not blind.** JUMP in every form, the orders next to it, "check fire" under HOLD_FIRE,
  both sides of "the other angle", reports of being under fire under NONE.
- **A suggestion withdrawn.** Reading HOLD_ANGLE with the "other" slot as HOLD_OTHER_ANGLE in the planner would
  undo "hold this angle, I'll take the other one": the slot is a regex on a word and does not know whose angle
  it is.
- **Lines.** 3 authors x 30, two annotators each: all 90 unanimous. The 993 earlier lines were read again under
  the v53 spec: none became JUMP and no truth changed. The matcher, unchanged, on the 90 lines: exact 82, place
  85, direction 24 of 27, no false direction.
- **Bot v53** (`models/coop-deberta-v3-ens3-v53`): v4's recipe on 4799 lines (1083 lines and 1146 seeds typed,
  2570 Parakeet transcripts), 12 epochs; family gate, threshold 0.66. Out of fold on the r6 and cs lines (722):
  89.8 typed, 85.3-87.3 through Parakeet from clean synthetic voices, 71.6 from VCTK speakers in no training
  set. The v53 lines by kind, typed / unseen speakers ([score_v53_kinds.log](scripts/coop/stt/score_v53_kinds.log)):
  JUMP 19/20 and 15/20; the orders next to it 16/16 and 14/16; the other angle for the bot 6/6 and 6/6, for the
  player 6/6 and 5/6; cease fire in radio wording 4/4 and 4/4; reports of being under fire 4/4 and 4/4.
- **What it cost.** On the 662 lines v52 was checked on, v53 is 0.6 to 2.5 points lower on typed text and the
  clean voices and level on VCTK; most of the loss is the bot asking again (16 of the 20 typed lines lost),
  and it acts on fewer non-orders (4.1% against 6.1% typed). On the 422 oldest lines the criterion has now
  fallen three versions in a row: typed 89.8 (v51), 88.6 (v52), 87.2 (v53); Kokoro English 89.6, 87.7, 83.9.
- **The owner's lines** (not blind): the three from the v52 test 3/3 (v52: 1/3); the first 38 -- 37/38 (v52:
  38/38), "Go into the room." is asked again at 0.58 under the 0.66 threshold.
- **Probes after the training.** [probe_v53_new.log](scripts/coop/probe_v53_new.log): 48 new wordings with the
  readings wanted, written before any v53 result -- v52 28/48, v53 42/48. **Known faults of v53, not fixed:**
  "check the fire escape" is HOLD_FIRE 1.00 (v52: CHECK -- the mirror of v52's "check fire"); "i'll watch the
  other door you stay on this one" is HOLD_OTHER_ANGLE 0.64; "drop in through the hatch" is VAULT_WINDOW 0.84;
  "can you jump down" is ignored; "jump down and cover me" and "keep your head down" are asked again.
- **C++.** v53: tokens 10444/10444, places 35889/35889 (9866 with a direction), gates 5364/5364, decisions
  190/190, golden 2275/2275, conversation 77/77; 39.2 ms on three cores.
- **Limits.** Those of v52. v31 is still the default bot.

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
  90.5 near at 1.9% wrong family, 2.3 GB, about 40 ms on 3 CPU cores (section v2; re-measured in
  section v3).
  Places on the map come from a dictionary matcher that hands the planner the place, with any
  classifier (section v3). The same ensemble re-trained with lines that name places (v3) carries out
  smoke and "clear" callouts as orders; v31, trained with a corrected seed set, does not, and sends
  roof orders to MOVE_TO. v31 is the default bot since 2026-10-04, by the owner's decision; it has
  no blind number yet.
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
| [locations.json](scripts/coop/locations.json), [locations.py](scripts/coop/locations.py), [locations_dev.json](scripts/coop/locations_dev.json) | v3: the map vocabulary, the place matcher (rule set v3), the developer's regression lines |
| [rules/](scripts/coop/rules/) | rule sets v1 and v2 as they were (v1's vocabulary is a reconstruction: it reproduces the frozen log, its bytes are not the frozen ones); the critics' lines against v3 and `check.py` |
| [make_spec_v3.py](scripts/coop/make_spec_v3.py), [blind/spec_v3.json](scripts/coop/blind/spec_v3.json), [seed_commands_v3.json](scripts/coop/seed_commands_v3.json), [blind/v3/](scripts/coop/blind/v3/), [annot/v3/](scripts/coop/annot/v3/) | v3 spec (target modifier), seed set with location seeds, the 150 blind lines and their annotations |
| [eval_v3.py](scripts/coop/eval_v3.py), [v3_shipped.py](scripts/coop/v3_shipped.py), [shipped.py](scripts/coop/shipped.py), [v3_noharm.py](scripts/coop/v3_noharm.py) | v3 evaluation: matcher (`--rules v1` for the blind rule set), the v2 bot on the place lines, re-training; logs `eval_v3_rules_v1.log` (first blind run), `eval_v3.log` (rule set v2), `eval_v3_rules_v3.log` |
| [review_v3/](scripts/coop/review_v3/), [eval_v3_review.py](scripts/coop/eval_v3_review.py), [probe_v3.py](scripts/coop/probe_v3.py) | the Mac review of v3: findings, a fresh author's 80 lines, post-review slices and probes of the final model (none blind) |
| [make_seeds_v31.py](scripts/coop/make_seeds_v31.py), [seed_commands_v31.json](scripts/coop/seed_commands_v31.json), [annot/v3/reann_r6.json](scripts/coop/annot/v3/reann_r6.json) | `COOP_TAG=v31`: the corrected seed set and the independent re-reading of the r6 lines; logs `train_v31_*.log`, `eval_v31.log`, `eval_v2_v31.log`, `probe_v31.log` |
| [eval_fresh.py](scripts/coop/eval_fresh.py) | a trained bot on the Mac review's fresh author, next to the archived v2 and v3 answers (`eval_fresh.log`) |
| [eval_v3b.py](scripts/coop/eval_v3b.py), [v3b_shipped.py](scripts/coop/v3b_shipped.py) | a second blind batch (`blind/v3b`, not written yet): rule sets v1–v3 and every trained bot on lines none of them was fitted to |
| [bots.py](scripts/coop/bots.py) | the one place that names the default bot |
