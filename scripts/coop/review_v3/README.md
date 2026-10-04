# review_v3: what the v3 write-up cites from the review

## The review

An adversarial review of the v3 work (places on the map: `locations.py`, the re-trained classifier,
the C++ port) ran on 2026-10-03/04, after every v3 blind line had been read and scored.

- Round 1, seven reviewers, one per dimension: freeze and blindness, the numbers, the matcher, the
  C++ port, bot integration, training and evaluation code, data / spec / docs.
- Verification: every finding went to one or two independent verifiers (one to reproduce it, one to
  refute it). Where they corrected a reviewer, the verifier's version is the one the write-up uses.
- Round 2, four gap reviewers, after the final v3 model had been trained on this Mac (MPS): the final
  model's behaviour, its export and C++ parity, a fresh blind author, the matcher on lines that were
  not written to name places.

Everything the review computed is post hoc: slices, joint rates and probes were chosen by people who
knew the results. None of it is a blind measurement. The blind ones remain `eval_v3_rules_v1.log`
(matcher rules v1) and sections B-C of `eval_v3.log`.

## Files here (they cannot be regenerated)

| file | what it is |
|---|---|
| `fresh_author.json` | 80 lines written and labelled by the "fresh blind author" gap reviewer: 60 that name a place (in the mix of the v3 blind sets) and 20 plain orders, 40 typed and 40 STT style, 6 marked arguable in advance |
| `fresh_author.sha256` | the reviewer's stamp, 2026-10-04T00:43:35Z, made before the matcher or a model read the lines. The path in it is the reviewer's scratch file (`author_fresh.json`); the hash is the hash of `fresh_author.json` |
| `fresh_probs_v2.json` | probabilities of the shipped bot (`models/coop-deberta-v3-ens3-v2`, family gate, 0.58) for the 80 lines |
| `fresh_probs_v3.json` | the same for the final v3 model (`models/coop-deberta-v3-ens3-v3`, family gate, 0.60, trained on MPS). A re-trained model gives other numbers: re-run the 80 lines before quoting them for it |

Limits of the fresh author, to be stated wherever its numbers are quoted:

- ONE AI author who is also the ONLY labeller. No second reader, so label noise is not measured.
- Blindness is partial and self-attested: the lines were written from `blind/spec_v3.json` before any
  other project file was opened, but the reviewer's task text carried the claims under review and the
  titles of the round 1 findings.
- Short, seed-like lines: 6.8 tokens per place line against 10.1-12.5 for the project's three authors;
  by the review's count 52 of the 60 place lines are within 0.5 char-n-gram cosine of a v3 training
  text; four of the 80 equal a training text token for token. Every place phrase is in the dictionary.
- The lines were written after the final model existed and have now been seen. They must not be used
  to tune rules, seeds or thresholds; a change they motivate needs new blind lines.

## Reproducing the cited numbers

Both scripts live in `scripts/coop`, are run from there, and say in their first lines that the
numbers are POST-REVIEW, computed after every v3 blind line was seen.

`python eval_v3_review.py > eval_v3_review.log` reads stored files only (no model, the same output
on every run) and writes `results_v3_review.json`:

| section | figures |
|---|---|
| A | shipped v2 against the re-trained ens3 on the 150 v3 lines: near / exact ok / wrong family per author, paired bootstrap of the score and of near alone, the gain without author r6 |
| B | the same on the novel v3 lines (`eval_v2.novelty`, < 0.5) and on the near-copies |
| C | joint rate, intent near and exact place on the same line, with matcher rules v2 and v1 |
| D | the 483 older lines, v21 study against v3 study: counts per gate, fold thresholds, the lines that changed |
| E | raw line against "strip" for the shipped bot: the three lines that change, sign test |
| F | matcher per author under rules v1 and v2; roles and flags of the 150 primaries |
| G | the fresh author: matcher, both bots, joint rate (from the files above) |

`python probe_v3.py ../../models/coop-deberta-v3-ens3-v3 ../../models/coop-deberta-v3-ens3-v2 > probe_v3.log`
loads both bots on CPU through `coop_bot.Bot` (about two minutes) and writes `results_v3_probe.json`.
It appends nothing to `coop_bot_log.jsonl`. The probes are exploratory and not blind; which line is a
callout is the developer's reading, with no annotators:

| probe | lines |
|---|---|
| (a) | smoke-state callouts: `<place> is smoked` and eight other phrasings |
| (b) | clear callouts without a copula (`<place> clear`), and `<place> is clear` as the safe control |
| (c) | roof orders without a rope word, verb x preposition, "top floor" as the control |
| (d) | `take <colour> stairs` against `take <colour>` |
| (e) | the 233 seed commands of `seed_commands_v21.json` in ALL CAPS |
| (f) | controls: `smoke <place>`, `two on <place>` |
