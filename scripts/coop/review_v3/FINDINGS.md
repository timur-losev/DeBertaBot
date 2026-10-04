# Review of v3: every finding, as verified

Rendered from `findings.json` (the raw result of the review of 2026-10-03/04; see `README.md`). Each finding is
the reviewer's title followed by what the independent verifiers established: where they corrected the reviewer,
their text is the one to use. "reproduce" re-derived the evidence from scratch, "refute" tried to show the
finding wrong, already documented or irrelevant; minor findings had one verifier doing both. File paths and
scratch directories are those of the Mac the review ran on. The model called "final v3" in the gap round is the
ensemble trained on that Mac (MPS).

`touches frozen: yes` means a fix would change the matcher rules, the vocabulary, the spec, the seeds or the
labels after the blind lines were seen: by the project's rules that needs a record in `frozen.txt` and new blind
lines before a clean number can be quoted.

73 findings; 0 refuted by every verifier. Severity after verification (the most severe verdict among the verifiers who did not refute it):

| severity | findings |
|---|---|
| major | 25 |
| minor | 35 |
| note | 13 |

## Index

| # | reviewer said | verifiers | touches frozen | finding |
|---|---|---|---|---|
| freeze-blindness #1 | major | reproduce: confirmed / major, refute: confirmed / minor | yes | Rules v2 give the target of 'stack up on <place>' the role 'them' (enemy's place); the dev check cannot see role flips |
| freeze-blindness #2 | major | reproduce: confirmed / major, refute: confirmed / minor | yes | Seed set v3 still teaches 'get on the roof' = RAPPEL against spec_v3; re-training did not fix 'get up on the roof' |
| freeze-blindness #3 | major | reproduce: confirmed / major, refute: partly / minor | no | The re-training gain comes almost entirely from one author (r6); HANDOFF's '+10.7' is the score, not the near-rate difference |
| freeze-blindness #4 | major | reproduce: confirmed / major, refute: confirmed / minor | no | '94% on held-out stt' and '96.7% on all': rules v2 are 13 single-line patches, the stt gain is two idiom twins, and the 96.7% is unlabelled in the log |
| freeze-blindness #5 | major | reproduce: confirmed / major, refute: confirmed / minor | no | Matcher figures are upper bounds: the spec hands the authors the dictionary's names, and every phrasing outside the dictionary was missed |
| freeze-blindness #6 | major | reproduce: confirmed / minor, refute: partly / minor | no | The two annotators are not independent readers: one v3 pair is byte-identical and no annotator changes any scored label |
| freeze-blindness #7 | minor | both: confirmed / minor | no | Audit gaps: v1 rule files and the blind workflow prompts are not archived; one unrecorded hash; one stale script |
| freeze-blindness #8 | minor | both: confirmed / minor | no | Wording of two side claims is stronger than the evidence: 'names stripped' and 'older orders not harmed' |
| numbers #1 | major | reproduce: confirmed / major, refute: confirmed / major | no | The whole classifier gain on the v3 lines comes from one author (r6); without r6 the hit-rate gain is +0 / +1 point and the CI spans zero |
| numbers #2 | major | reproduce: confirmed / major, refute: confirmed / minor | yes | seed_commands_v3.json still labels 'get on the roof' and 'go roof' as RAPPEL, against spec_v3; the 'get up on the roof -> RAPPEL' error is not fixed in the cross-validation |
| numbers #3 | major | reproduce: confirmed / minor, refute: confirmed / minor | no | HANDOFF quotes differences of the composite score (near - 2 x wrong family) as if they were hit-rate differences |
| numbers #4 | major | reproduce: confirmed / major, refute: partly / minor | no | Matcher: the held-out 94% is 90 -> 94 on stt (two lines), and both gained lines repeat idioms of the tuning authors; one fix is a literal phrase from an r6 blind line |
| numbers #5 | minor | both: confirmed / minor | no | 'Older lines not harmed' is a null result with a +-4 point interval; by component the top gate loses 1.7 points of hit rate and two BREACH lines become OPEN |
| numbers #6 | minor | both: confirmed / minor | no | '3.3 points worse with names stripped' rests on three lines of one author; the direction is not established and 3.3 is the score, not the hit rate |
| numbers #7 | minor | both: confirmed / minor | no | v3 truth: the two r6 annotator files are byte-identical, the authors give no alternates, and all 150 lines are unanimous on intent and target |
| numbers #8 | note | both: confirmed / note | no | Intent and target are scored separately; the joint rate and the cost of 'near' on v3 lines are not reported |
| matcher #1 | major | reproduce: confirmed / major, refute: partly / minor | yes | Role of the primary target is never scored, and it misfires on ordinary orders: the place the bot must act on is marked from / them / status / mine / not |
| matcher #2 | major | reproduce: confirmed / minor, refute: partly / minor | no | The stt 'held-out' 94% is not an independent check of rules v2: both stt gains are idioms that also occur in the tuning authors' lines |
| matcher #3 | major | reproduce: confirmed / major, refute: confirmed / minor | yes | Wrong primary on plausible two-place lines: the player's own place, a first clause glued to the second, or a corrected place wins |
| matcher #4 | major | reproduce: confirmed / major, refute: partly / minor | yes | Vocabulary entries added in v2 from single blind lines misfire: 'to second' / 'on second', three ignore phrases, 'stack', the 'other' target |
| matcher #5 | major | reproduce: confirmed / minor, refute: partly / minor | yes | unknown_modifier is wrong outside the spec's three examples: rule 1c tests the word before the qualifier, rule 1d treats prepositions as modifiers, post-modifiers are never flagged |
| matcher #6 | minor | both: partly / minor | yes | Floor vocabulary is inconsistent and the spec has gaps: second-floor forms, relative floors, a third floor, split 'up stairs', other senses of colour words |
| matcher #7 | minor | both: confirmed / minor | no | Matcher time grows with the cube of the line length and the bot puts no cap on the line |
| cpp-port #1 | minor | both: confirmed / minor | no | "8570/8570" is true but is weak evidence of rule parity: 84% of the lines name no place, and 20 of 36 seeded port errors pass it unnoticed |
| cpp-port #2 | minor | both: confirmed / minor | no | Vocabulary load fails under a decimal-comma locale on every libc++ platform: tokenizer.cpp takes the strtod branch on macOS |
| cpp-port #3 | minor | both: confirmed / minor | no | coop_cli --decide-tests and --dialogue abort on the v1 bot directory; README says the v1 bot passes the same checks |
| cpp-port #4 | note | both: confirmed / note | no | The '+4 lines past std::regex's recursion limit' skip is decided by the test data, not at run time; on libc++ those lines match Python, so macOS and Windows builds differ on such lines |
| cpp-port #5 | note | both: confirmed / note | no | The matcher has no length cap and is cubic in zones x targets: 4,000 tokens take 1.3 s, 16,000 tokens 80 s on the calling thread |
| cpp-port #6 | note | both: confirmed / note | no | frozen.txt: the unrecorded coop_cli.cpp hash is the 22:00 portability edit, omitted from the 22:26 entry |
| cpp-port #7 | note | both: partly / note | no | LocationMatcher::Init accepts three malformed vocabularies that locations.validate() refuses |
| bot-integration #1 | major | reproduce: confirmed / major, refute: confirmed / major | no | A queued order and its places do not survive the lines players say between "on my go" and "go": "not yet" drops it, a signal reminder can replace it with a misread order |
| bot-integration #2 | major | reproduce: confirmed / major, refute: partly / minor | yes | A primary place that carries a role means "act here" on some lines and "keep away" on others; the 96.7% / 94% exact-target numbers ignore roles and flags |
| bot-integration #3 | major | reproduce: confirmed / minor, refute: partly / minor | no | Intent and place are right together on 88.0% of the v3 lines (78% on author stt); HANDOFF reports only the two separate numbers |
| bot-integration #4 | major | reproduce: partly / minor, refute: partly / minor | yes | annot/v3/author_r6_ann1.json and author_r6_ann2.json are the same file: the r6 v3 lines have one annotator counted twice |
| bot-integration #5 | minor | both: confirmed / minor | no | The "other" slot is not kept with a queued order: at execution the planner gets a bare object |
| bot-integration #6 | minor | both: confirmed / minor | no | The generated decide and dialogue tests miss most queue-and-place regressions; Decision::executed is never compared; the current coop_cli crashes on the v1 bot's test files |
| bot-integration #7 | minor | both: partly / minor | no | Switching the default model as HANDOFF step 3 says leaves an existing build on v2, and coop_cli never prints which model it checked |
| bot-integration #8 | minor | both: confirmed / minor | no | Nothing reconciles the intent with the matcher's target: VAULT_WINDOW at a door, a correction blocked by the leading-negation guard, GO with a place and no order |
| train-eval-code #1 | major | reproduce: confirmed / major, refute: confirmed / minor | yes | Two inherited seeds label going to the roof as RAPPEL against spec_v3; the re-trained ensemble still answers RAPPEL to 'get up on the roof' |
| train-eval-code #2 | major | reproduce: confirmed / major, refute: confirmed / major | no | The gain over the shipped bot comes from one held-out author (r6); on cs and stt the interval includes zero |
| train-eval-code #3 | major | reproduce: confirmed / major, refute: confirmed / minor | no | '+10.7 / +11.3', '0.0 / -0.2' and '3.3 points worse' are differences of the score (near - 2 x wrong family), not of near; 'place names stripped' removes only the qualifier word |
| train-eval-code #4 | minor | both: confirmed / minor | no | Novelty slice for v3 (missing from the write-up): 90 of 150 lines are novel, the gain survives there with the lower bound near zero; 60 are near-copies, 32 of them of another author's v3 line |
| train-eval-code #5 | minor | both: confirmed / minor | no | The final v3 model is being trained on MPS while every v3 number comes from CUDA models; the equivalence check was at argmax, and at the deployable threshold the MPS fold has about twice the wrong-family count |
| train-eval-code #6 | minor | both: confirmed / note | no | v3_noharm.py no longer runs and results_v3_noharm.json is an unreported, pre-freeze artifact |
| train-eval-code #7 | minor | both: confirmed / minor | no | eval_v2.py under COOP_TAG=v3 overwrites results_v3.json, the file eval_v3.py writes; the classifier numbers of sections B and C are stored in no results file |
| train-eval-code #8 | note | both: confirmed / note | no | Author r6's two v3 annotator files are byte-identical, and r6's v3 lines changed surface style |
| data-spec-docs #1 | major | reproduce: confirmed / minor, refute: partly / minor | no | Held-out author stt repeats the tuning authors' idioms: the whole 90% -> 94% gain of rules v2 comes from two dictionary entries copied from r6/cs lines |
| data-spec-docs #2 | major | reproduce: confirmed / major, refute: confirmed / minor | yes | seed_commands_v3.json still labels 'get on the roof' and 'go roof' as RAPPEL, against spec_v3; 'get up on the roof' stays RAPPEL after re-training, although HANDOFF says re-training should fix it |
| data-spec-docs #3 | major | reproduce: confirmed / major, refute: partly / minor | no | The 'difference' figures in HANDOFF section 4 are score (near minus twice wrong-family), not near, and the re-training gain comes from one author |
| data-spec-docs #4 | major | reproduce: confirmed / minor, refute: partly / minor | yes | annot/v3/author_r6_ann1.json and author_r6_ann2.json are the same file, and no annotator ever differs from an author on intent or target |
| data-spec-docs #5 | minor | both: confirmed / minor | no | The blind lines use almost only the canonical place names: 61 of 95 dictionary phrases, all 8 'named' phrases and 5 intents never occur |
| data-spec-docs #6 | minor | both: partly / minor | no | HANDOFF and README statements that are wrong or stale on this machine |
| data-spec-docs #7 | minor | both: confirmed / minor | no | Matcher rules v1, the files behind the 88.0%, are not in the archive |
| data-spec-docs #8 | note | both: confirmed / note | no | The 8570/8570 C++ location parity: 7199 of those lines contain no place |
| gap-final-v3-model-behaviour #1 | major | reproduce: confirmed / major, refute: confirmed / major | yes | Final v3 bot throws a smoke when told a place is already smoked: '<place> is smoked' -> SMOKE on 47 of 47 places (shipped v2: 7 of 47) |
| gap-final-v3-model-behaviour #2 | major | reproduce: confirmed / major, refute: confirmed / major | yes | Final v3 bot pushes in on the callout '<place> clear': ENTRY on 27 of 30 names (v2: 19 of 30); inherited from the seeds and made worse by the v3 templates |
| gap-final-v3-model-behaviour #3 | major | reproduce: confirmed / major, refute: confirmed / major | yes | Final v3 model: 'get up on the roof' is now MOVE_TO only because that blind line is a training row; 'get on / onto the roof' and a bare 'roof' still answer RAPPEL (5 of 27 fresh rope-less roof orders, 18 of 42 on a verb x preposition grid) |
| gap-final-v3-model-behaviour #4 | minor | both: partly / minor | yes | A lone place name changes the intent: 'take blue stairs' is MOVE_TO 1.00, 'take blue' is ENTRY (12 of 12 colours); PER_TEMPLATE = 3 drew no lone name for 'take', and 'every name meets every kind of order' is 31% of the combinations |
| gap-final-v3-model-behaviour #5 | minor | both: confirmed / minor | no | The out-of-fold predictions behind threshold 0.60 and the family gate are not saved: the two numbers in bot_config.json can be checked against the log, not re-derived |
| gap-final-v3-export-parity #1 | major | reproduce: confirmed / major, refute: partly / minor | no | Letter case decides the action: upper-case FLANK / RAPPEL / DRONE make both bots throw a grenade, and on alternating-case lines the v3 bot now throws a frag where v2 asked again (golden edge line 'mIxEd CaSe FlAnK') |
| gap-final-v3-export-parity #2 | minor | both: confirmed / minor | no | For the v3 bot (threshold 0.60) the generated 'at the threshold' step lands on the acting side: decide_tests.jsonl has no 'say again' step under the shipped family gate, and an engine that compares in float32 passes all six checks |
| gap-final-v3-export-parity #3 | minor | both: partly / minor | no | Scripted dialogue, v2 model -> v3 model: 8 of 77 steps change; two are worse ('прикрой меня' now executes REVIVE_ME at 0.604, a bare 'blue' now gets 'say again'), three are better, three end the same |
| gap-final-v3-export-parity #4 | minor | both: confirmed / minor | no | Four v2 defaults survive 'change the default model in CMakeLists.txt and coop_bot.py' (shipped.py, export_cpp.py, check_onnx.py, gen_tests.py), and the golden line set silently follows COOP_TAG |
| gap-final-v3-export-parity #5 | note | both: confirmed / note | no | coop_cli --bench reports 0 MB of memory on macOS; latency of the v3 export equals v2 on this machine |
| gap-fresh-blind-author #1 | major | reproduce: confirmed / major, refute: confirmed / minor | yes | Enemy-place words have no apostrophe-less STT forms: after 'theyre / hes / shes / theyve' the enemy's place gets no role and becomes the bot's target |
| gap-fresh-blind-author #2 | note | both: confirmed / note | no | Fresh blind author, matcher rules v2: exact target 95.0% (57/60) [86.3, 98.3], not below the quoted 94% / 96.7%; holds only for lines that use the dictionary's own names |
| gap-fresh-blind-author #3 | note | both: confirmed / note | no | Fresh blind author, classifier: final v3 is better than shipped v2 on place lines (near 98.3% vs 91.7%, 4 lines better, none worse) and equal on plain orders (20/20 both); the sample is seed-like, so it confirms the direction, not the size |
| gap-fresh-blind-author #4 | note | both: partly / note | no | Fresh blind author, joint rate: intent and target both right on 91.7% (55/60) with final v3, 85.0% with shipped v2; all five v3 misses are two-place or other-sense lines |
| gap-matcher-on-unsteered-lines #1 | major | reproduce: partly / major, refute: partly / minor | no | On the 483 unsteered lines the primary is exact on 89.1% of the lines where the matcher returns one (97.9% on the blind v3 lines), the full record on 85.7%; 11 to 14 older orders now get a record that misdirects a planner |
| gap-matcher-on-unsteered-lines #2 | major | reproduce: confirmed / major, refute: confirmed / minor | no | A role on the primary of an order is wrong about as often as right: 7 of 15 on the unsteered lines, 13 of 21 over all 633 blind lines; 'status' is wrong 8 of 8 and depends on an apostrophe |
| gap-matcher-on-unsteered-lines #3 | minor | both: confirmed / minor | yes | A colour word before any noun outside a 19-word block list becomes an inferred staircase: both spontaneous colour adjectives in the older lines ('red container', 'red car') give stairs / red |
| gap-matcher-on-unsteered-lines #4 | minor | both: confirmed / minor | yes | The 233 older seed commands are clean, but the templated v3 seeds 'cover me from {place}' (3 of 3) get role 'from' on the place the bot must take |
| gap-matcher-on-unsteered-lines #5 | note | both: confirmed / note | no | Spontaneous place mentions are mostly outside the vocabulary: 139 of the 245 older lines that name a place; a map qualifier appears in 3 of 483; the objects of BREACH and TAKE_COVER are almost never expressible |

## Freeze discipline and blindness (`freeze-blindness`)

### freeze-blindness #1: Rules v2 give the target of 'stack up on <place>' the role 'them' (enemy's place); the dev check cannot see role flips

Reviewer: major, matcher. Affects: The PlaceRecord handed to the planner (Python bot and C++ engine) for 'stack up / squad up / awp' orders; not visible in the 'exact target' metric, which ignores role.

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

The finding holds, with three refinements.

**What reproduces.** With the frozen v2 files (locations.py sha b3e9314a, locations.json sha 890d651a), `words.role_them` ends with `awp, awper, stack, squad, camper`. Any of these within 5 tokens before a place, with no punctuation, "you" or other target between, gives that place role `them`. So ordinary orders get role `them` on their only target:
- "stack up on the main door", "stack on blue stairs", "everyone stack up at the south window"
- "squad up at the main door", "take the awp and hold north window"
- also "let's stack the north door", "everybody stack up on blue", "squad move to basement", "grab the awp and get to the roof"

"stack up on the main door" is a developer regression line (locations_dev.json, cat b2, batch ordinary, accept [["door","main",null]]). `locations.py --dev` still reports 5 failures, because run_dev (locations.py:465-482) compares only the (object, qualifier, zone) triple and reads role only when "ROLE" is in accept. The same record is exported to C++: location_tests.jsonl line 8231 expects role `them`, and intent_config.json has locations.version 2 with the same list.

**Refinement 1: it is worse than "role only" on two-place lines.** The reviewer says the effect is invisible to the exact-target metric. That is true for single-place lines and for all 150 blind lines. But because primary is "the first target without a role, else the first target", the wrong role flips the primary whenever the other place also carries a role. On my own probe lines (not blind data):
- "two on red stairs, stack up on the main door" -> primary stairs/red (the enemy's place); without the five words -> door/main
- "get off the roof and stack up on the main door" -> primary roof
- "not the north door, stack up on the south door" -> primary door/north (the negated one)
- "i'm on red stairs, stack up on the main door" -> primary stairs/red (the player's place)
- "stack up on the east door and watch the window" -> primary window

**Refinement 2: "added in v2" is inferred, not read.** The v1 files (9999cc9f / 111d1a76) are not on disk. For `stack` and `awp` the inference is strong: eval_v3_rules_v1.log shows r6v3_029 primary stairs/yellow role=None and csv3_040 primary roof role=None, and the current code reproduces exactly those only with `stack` / `awp` removed. For `squad`, `awper`, `camper` nothing in the 150 blind, 483 older or 254 dev lines exercises them, so only their position at the end of the list suggests v2. None of the five is mentioned in the v2 change lists (locations.json `_note`, locations.py docstring lines 17-19, frozen.txt line 139).

**Refinement 3: context for the single-place harm.**
- A role on a sole primary is not new. Rules v1 words do the same ("someone hold the north door" and "guys hold the north door" -> role `them`).
- 8 blind order lines already have a role-carrying primary that the readers accept, with roles status, from and not. Every `them` primary in the blind set is on a NONE line.
- No code in the repo consumes role (coop_bot.py and bot_brain.cpp only pass the record on). The single-place harm therefore depends on how the game-side planner reads locations.h:46, "the bot is not sent to a place with a role".

**Headline numbers are untouched.** Removing the words changes no stt line (stt stays 47/50). `stack` buys exactly r6v3_029 and `awp` buys exactly csv3_040 (plus the role on csv3_017), which is 2 of the 145/150.

**Blindness.** This is not a blindness violation: both lines are from the tuning authors r6 and cs. It is an overfit lexical rule, a regression check that cannot see roles, and an undocumented v2 edit.

*Recommended action.* **A. Free now (no matcher behaviour change):**

1. In /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md section 4, under the matcher results, add a known-limitation sentence: "Rules v2 also appended awp, awper, stack, squad, camper to words.role_them (from r6v3_029 and csv3_040, one line each). Side effect: orders such as 'stack up on the main door' / 'squad up at X' / 'take the awp and hold X' get role 'them' on their target, and on two-place lines the primary can move to the other place ('two on red stairs, stack up on the main door' -> red stairs). The exact-target metric and locations.py --dev do not check roles."

2. Record the same five-word addition in the v2 comment of scripts/coop/frozen.txt (line 139). It is currently missing from every v2 change list.

3. Reconcile the two contract statements for the planner: locations.h:46 and locations.py:43 ("not sent to a place with a role") against locations.h:60 and locations.py:44 ("primary: the target the bot acts on, even if it carries a role"). Say explicitly what a planner does with a primary that has a role.

4. Make the dev check role-aware by adding an expected role per case in scripts/coop/locations_dev.json and comparing it in run_dev (locations.py:465-482). Do not use the reviewer's blanket "fail when a triple-accepted primary carries a role": it would flag 18 lines, 17 of them correct. Log the new hashes in frozen.txt; this is tuning material and changes no matcher output.

**B. Behavioural fix = rules v3 (touches frozen):**

5. Remove "stack" and "squad" from words.role_them in scripts/coop/locations.json. Then re-export with `export_cpp.py <bot> --config-only` and regenerate location_tests.jsonl with `gen_tests.py`.

6. Cost: r6v3_029 goes back to a mismatch (all lines 144/150 = 96.0%). The stt outputs do not change (47/50), but under HANDOFF section 6 the stt figure must then be labelled "after tuning" and new blind lines are needed for a held-out number.

7. Whether to drop "awp" as well (costs csv3_040, giving 143/150) is the owner's call.

8. Do not replace the words with a pattern fitted to r6v3_029 (for example "stack is sitting") and count it as free.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: yes**

The finding stands on the facts; I could not refute it. I lower the severity because no figure in HANDOFF section 4 changes and nothing consumes the role field yet.

**What holds**
- Rules v2 (locations.json sha 890d651a, version 2) have 'awp', 'awper', 'stack', 'squad', 'camper' at the end of words.role_them.
- 'stack' and 'awp' are provably v2 additions: eval_v3_rules_v1.log prints role=None for the primaries of r6v3_029 and csv3_040, which is impossible with those words in the list.
- Each of the two repairs exactly one tuning line. 'squad', 'awper' and 'camper' change no line among the 150 blind, 483 older and 254 dev lines.
- Ordinary orders now get role 'them' on their only target, including the developer's own regression line 'stack up on the main door' (locations_dev.json, cat b2 / batch ordinary; file hash still the v1-frozen cf6bbf37).
- `locations.py --dev` cannot see this: run_dev (locations.py:471-474) accepts a primary on the (object, qualifier, zone) triple alone and still prints the same 5 failures.

**Worse than reported**
- The role also decides which target is primary. When a second place follows, the primary moves to it: 'stack up on the main door then clear the basement' gives the basement under v2 and the main door without the five words.
- So the effect is not confined to the unscored role field; on that line pattern it changes the scored triple. No blind or older line has the pattern.

**Weaker than reported**
- No section 4 number is affected. Held-out stt is 47/50 with or without the words; the 96.7% is already labelled as tuned on r6 and cs.
- Nothing reads the role today: coop_bot.py only prints it, BotBrain only forwards the PlaceRecord, and the planner is stage 2.
- The comment "the bot is not sent to a place with a role" (locations.h:46, locations.py:43) is already not literally true. On 6 blind order lines the readers' target equals a primary that carries a role (from / status). For a single-place line the practical harm therefore depends on a planner that does not exist yet.
- The same false 'them' already arises from older list words: 'ok guys push the main door' gives role them with or without the five v2 words.
- location_tests.jsonl is a Python-equals-C++ parity file, not a correctness oracle. "Wrong expected value" overstates it; the 8570/8570 claim is untouched.

**Documentation gap**
- The role_them additions are not in the v2 change lists (locations.json _note, locations.py:17-19). frozen.txt:139-141 does record the v2 hashes and the "tuned on r6 and cs" label, so the freeze rule is met at file level.

*Recommended action.* **Now, without touching the rules** (the stt figure stays held out):

1. Add to the v3 write-up (HANDOFF.md section 4 under the matcher table, and the future COOP-BOT.md "v3" section):

   "Rules v2 also added 'awp', 'awper', 'stack', 'squad', 'camper' to role_them. 'stack' and 'awp' each repair one tuning line (r6v3_029, csv3_040). Side effect, not measured by the exact-target metric and not present in any blind line: orders such as 'stack up on the main door' get role 'them' on their target, and when a second place follows, the primary moves to it ('stack up on the main door then clear the basement' -> basement). `locations.py --dev` compares only object / qualifier / zone and does not catch this. Until rules v3, the planner must act on `primary` whatever its role and must not treat role as a veto."

2. Add the five words to the v2 change list in the locations.json "_note" and in locations.py:17-19. This changes text only, but both file hashes change, so record them in frozen.txt as a comment-only edit.

**Deferred to rules v3** (touches frozen material; needs new blind lines before any held-out matcher number is quoted):

3. In scripts/coop/locations.json, remove 'stack' and 'squad' from words.role_them, or gate them on a following state verb; reconsider 'awp'. Expected cost on the current lines: 144/150 (96.0%) without 'stack', 143/150 (95.3%) without 'stack' and 'awp'; stt stays 47/50.

4. In scripts/coop/locations.py run_dev, fail a case whose primary carries a role unless the case lists "ROLE" or an expected role. That needs role expectations added to locations_dev.json: 18 currently passing primaries carry a role, most of them legitimately.

5. Then run `export_cpp.py --config-only` and `gen_tests.py` to regenerate intent_config.json and location_tests.jsonl.

6. Correct the comments at locations.h:46 and locations.py:43, which say the bot is never sent to a place with a role.

### freeze-blindness #2: Seed set v3 still teaches 'get on the roof' = RAPPEL against spec_v3; re-training did not fix 'get up on the roof'

Reviewer: major, data. Affects: HANDOFF.md:111 (expected fix); roof orders in the final v3 model; the two remaining roof errors among the 14 re-trained misses.

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

Every factual part of the finding reproduces. The causal link to the seeds is supported but not proven, because no counterfactual training was run (training is forbidden for reviewers).

1. **The re-training did not fix the line HANDOFF.md:111 names.** In the leave-cs-out fold, csv3_037 "get up on the roof, I want somebody up top" (truth MOVE_TO, three readers unanimous) is still RAPPEL under both gates: ens3 RAPPEL 0.701 / MOVE_TO 0.255, fold threshold 0.58. All three members pick RAPPEL individually (0.59, 0.68, 0.83). csv3_031 "get off the roof and come down to the basement" moved from RAPPEL (shipped, 0.83) to below threshold: MOVE_TO 0.549 / RAPPEL 0.419, so the bot answers NONE.

2. **csv3_037 is one of only two wrong-family actions behind the 1.3% claim.** The other is sttv3_032 (OPEN -> VAULT_WINDOW). The roof error is therefore half of the residual wrong-family rate on the v3 lines.

3. **The failure is specific to the "get (up) on / off the roof" wording.** The other four roof MOVE_TO lines are right after re-training: r6v3_002 0.994, r6v3_038 0.998, sttv3_028 0.945, sttv3_041 0.823. Three of those were NONE in the shipped bot. So "re-training does not fix roof orders" would be too broad.

4. **The seed labels contradict spec_v3.** seed_commands_v3.json keeps "get on the roof" and "go roof" under RAPPEL, inherited unchanged from seed_commands.json, seed_commands_v2.json and seed_commands_v21.json. These were written when RAPPEL was defined as "(go up to the roof, drop down, hang at a window)" (blind/spec_v2.json:11). spec_v3 (blind/spec_v3.json:11) and HANDOFF section 7 (line 192) say that going to the roof without rope words is MOVE_TO. make_spec_v3.py adds "go to the roof", "head to the roof" and "go up to the roof" as MOVE_TO and never relabels the inherited seeds. Its docstring (lines 9-10) shows the author knew the definition changed. No seed text carries two labels verbatim; the conflict is between near-identical constructions.

5. **All training runs use these seeds.** Every cv fold (train_v2.py:148) and the final model (train_v2.py:183) train on all 383 seeds. The final v3 model also gets csv3_037 = MOVE_TO alongside "get on the roof" = RAPPEL, and will most likely answer RAPPEL to the verbatim order "get on the roof".

6. **Extra evidence that the seed label is the outlier.** In the stored 5-fold out-of-fold predictions, when "get on the roof" is itself held out, the models call it MOVE_TO in 8 of 9 runs (0.84-1.00). "go roof" is called MOVE_TO in 6 of 9, ENTRY in 2, RAPPEL in 1. Each seed gets RAPPEL only in a run where the other roof-RAPPEL seed was in training (1 of 3 such runs each; 0 of 6 when both were held out together).

No headline number is wrong; the numbers are what the frozen seeds produce. The defect is a HANDOFF sentence the project's own cv contradicts, plus two seed labels that train the shipped model against a decision listed in section 7.

*Recommended action.* **1. Write-up (touches nothing frozen).** In /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md:111, replace "Её должно починить дообучение" with the measured result:

"Кросс-валидация эту ошибку не починила: при отложенном авторе cs дообученный ансамбль читает csv3_037 «get up on the roof, I want somebody up top» как RAPPEL (0.70 против MOVE_TO 0.26, все три модели), а csv3_031 «get off the roof and come down to the basement» уходит под порог (MOVE_TO 0.55 / RAPPEL 0.42, бот переспрашивает). Остальные четыре приказа «на крышу» читаются верно. csv3_037 — одно из двух действий из чужого семейства в цифре 1.3%."

Add a known-issue line to section 4 or 7 and carry it into the future v3 section of COOP-BOT.md:

"seed_commands_v3.json до сих пор содержит «get on the roof» и «go roof» в RAPPEL (унаследованы из seed-набора v1, когда RAPPEL включал «go up to the roof»). Это противоречит spec_v3 и решению из раздела 7."

**2. Data fix (touches frozen material).**
- In /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/make_spec_v3.py main(), after loading seed_commands_v21.json, move "get on the roof" and "go roof" from RAPPEL to MOVE_TO (or drop them), and regenerate seed_commands_v3.json.
- Record the new hashes of make_spec_v3.py and seed_commands_v3.json in frozen.txt, with a comment that the seeds were changed after the v3 blind lines and the section C results were seen.
- Re-run "COOP_TAG=v3 python train_v2.py cv base" and eval_v3.py. Keep the current 90.0 / 90.7 and 1.3% as the pre-registered numbers and label the new section C as "после подгонки".
- A clean number for roof orders needs new blind lines.

**3. Final model.** The final v3 ensemble now training on mps uses the unfixed seeds. Either retrain it after the seed change, or ship it with the known issue from step 1 written down. Do not describe the roof error as fixed in either case.

**4. Wording of the cause.** Do not state that the two seeds are the proven cause. No counterfactual training was run; the evidence is the label contradiction plus the out-of-fold behaviour of the seeds.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: yes**

Every factual part of the finding holds, and the stored out-of-fold predictions support its causal claim. I downgrade the severity because no reported number is wrong.

**What is true**
- `seed_commands_v3.json` (the frozen file, hash 9e520412…, exactly what `make_spec_v3.py` produces) keeps two seeds inherited from v1/v2/v21 under RAPPEL: "get on the roof" and "go roof".
- The same file adds "go to the roof", "head to the roof" and "go up to the roof" under MOVE_TO.
- `spec_v3` (frozen at the same time) and HANDOFF section 7 say going to the roof without rope words is MOVE_TO. The two inherited seeds contradict that; nothing in the docs or `frozen.txt` says they were kept on purpose.
- They are the only roof-without-rope lines labelled RAPPEL in the training data. Every older blind roof line labelled RAPPEL names a rope, rappel or clip.
- All 9 cross-validation runs trained on these seeds (n_seeds = 383), and the final v3 ensemble now training uses the same file.

**What the cross-validation shows**
- csv3_037 "get up on the roof, I want somebody up top" is still RAPPEL after re-training (0.70 vs MOVE_TO 0.25). It is one of the two wrong-family lines.
- csv3_031 moved from RAPPEL (shipped) to an abstain: MOVE_TO 0.55 is under the 0.58 threshold.
- So the expectation in HANDOFF.md:111 ("re-training should fix it") is not borne out for the exact line it names, and the hand-off never says so.

**Why minor rather than major**
- Both lines are among the 14 listed misses and are already counted in 90.0 / 90.7 near and 1.3% wrong family.
- HANDOFF.md:111 is a forecast written under the section B results, not a claimed result.
- Re-training did fix 3 of the 5 roof orders the shipped bot missed (r6v3_002, sttv3_028, sttv3_041).
- The scope is 2 of 383 seeds and at most 2 of 150 blind lines, with no regression against the shipped bot.

**One correction to the suggested fix**
A re-run of the cross-validation after a seed change is "after tuning" for the whole of section C, not only for the roof line. The change would be prompted by blind cs lines.

It is time-sensitive only because the final model is training on the conflicting seeds now: it will answer RAPPEL to the verbatim seeds "get on the roof" and "go roof".

*Recommended action.* **1. Write-up (touches nothing frozen)**
Replace the second sentence of `/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md:111` ("Её должно починить дообучение") with what section C showed:
- Re-training fixed 3 of the 5 roof orders the shipped bot missed.
- "get off the roof and come down to the basement" now abstains (MOVE_TO 0.55, under the 0.58 threshold).
- "get up on the roof" is still RAPPEL (0.70) and is one of the two wrong-family lines.
- Likely cause: the seeds "get on the roof" and "go roof", inherited from v21, are still labelled RAPPEL against `spec_v3`.

Carry the same sentence into the future "v3" section of COOP-BOT.md, and add a note under HANDOFF section 7 that the seed set contradicts the roof decision.

**2. Seeds (frozen material; owner's decision)**
- Follow the v2 to v21 precedent: do not edit `scripts/coop/seed_commands_v3.json` in place.
- Create a new tagged seed set that removes "get on the roof" and "go roof" from RAPPEL, or moves them to MOVE_TO. This is a small change where `make_spec_v3.py` main() loads the v21 seeds, written to a new file with a new `COOP_TAG`.
- Record it in `scripts/coop/frozen.txt` as changed after the blind v3 lines were seen, prompted by csv3_037 and csv3_031.
- Keep 90.0 / 90.7 near and 1.3% wrong family as the frozen-seed result. Mark any re-run of section C as after tuning in full, not only the roof line.
- Re-train the final v3 ensemble with the new seed set; the one now training uses the conflicting seeds.
- A clean number for roof orders needs new blind lines.

### freeze-blindness #3: The re-training gain comes almost entirely from one author (r6); HANDOFF's '+10.7' is the score, not the near-rate difference

Reviewer: major, evaluation. Affects: HANDOFF.md:113-123: the re-training table, the '+10.7 [+3.3, +18.7]' line and the conclusion that re-training is needed.

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

Every number in the finding reproduces exactly. Two points of interpretation need tightening.

**What holds**
- **Mislabelled quantity.** HANDOFF.md:121 gives "+10.7 [+3.3, +18.7]" (top) and "+11.3 [+4.0, +19.3]" (family) as "the difference on lines with places", directly under a table of near rates (83.3 vs 90.0 / 90.7). Those figures are the score difference (near - 2 * wrong family), which eval_v3.log:82-83 labels "score:". HANDOFF.md never defines the score. The table's own arithmetic gives 90.0 - 83.3 = 6.7.
- **Near difference.** It is +6.7 [+1.3, +12.7] for top (15 fixed, 5 broken, exact McNemar p = 0.041) and +7.3 [+2.0, +13.3] for family (15 fixed, 4 broken, p = 0.019).
- **Wrong family.** 3.3% -> 1.3% is 5 lines -> 2 lines (3 removed, 0 added, p = 0.25).
- **Per author** (50 lines each, shipped -> re-trained):

| author | near, top | near, family | wrong family | score diff, top / family |
|---|---|---|---|---|
| r6 | 39 -> 49 (10 fixed, 0 broken) | 39 -> 49 | 1 -> 0 | +24.0 / +24.0 |
| cs | 46 -> 45 (1 fixed, 2 broken) | 46 -> 46 (1 fixed, 1 broken) | 3 -> 1 | +6.0 / +8.0 |
| stt | 40 -> 41 (4 fixed, 3 broken) | 40 -> 41 | 1 -> 1 | +2.0 / +2.0 |

- **The interval ignores authors and seeds.** eval_v3.py:86-90 resamples the 150 lines as independent, and ens3 is a single realisation. With the three authors as the unit, the near differences are +20 / -2 / +2 (top), so nothing can be inferred at author level. Single base models give stt 40 / 43 / 36 near against shipped 40, and r6 46 / 46 / 49 against shipped 39. The r6 gain is stable across seeds; the stt result is not.

**What needs tightening**
- **"Almost entirely r6" is exact for near, less so for the score.** r6 supplies 10 of the net +10 lines (top) and 10 of the net +11 (family). In score units r6 supplies 12 of 16 (top) and 12 of 17 (family), about 71-75%. The rest is mostly cs, where near is flat but wrong family drops 3 -> 1. "About zero on cs" is therefore true for near only.
- **The per-author comparison is asymmetric.** The shipped bot was trained on all three authors' 483 older lines; each cross-validation fold never sees the held-out author. Two of the three stt lines "broken" by re-training are "beach" (= breach) lines, a mis-hearing that exists only in stt's own older lines. The third hinges on "repel". So +1 line on stt is what the study measured, and it is conservative for a final model trained on all authors. It shows the study has not demonstrated a gain on STT-style input; it does not show re-training cannot give one.

**Effect on the conclusion**
The conclusion "re-training is needed" is not overturned: the pooled near gain excludes zero, no author's score falls, and wrong family never rises. The defect is the mislabelled headline number and the undisclosed concentration in one author.

**Related, same paragraph**
HANDOFF.md:122 ("0.0 / -0.2 [-4, +4]" on the 483 older lines) is also the score. Near there is 441 -> 433 at the top gate (-1.7 [-3.7, +0.4]) with wrong family 12 -> 8, and 437 -> 440 at the family gate (+0.6 [-1.4, +2.7]) with wrong family 9 -> 11.

*Recommended action.* Write-up only; no rule, vocabulary, spec, seed or label changes.

**/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md, lines 116-123**

1. Replace line 121 with text that names the quantity and gives both figures, for example:
   "Разница дообученный − боевой на 150 строках с местами. Попадание: +6.7 [+1.3, +12.7] (top) и +7.3 [+2.0, +13.3] (family); исправлено 15 строк, сломано 5 (top) / 4 (family). Счёт (попадание − 2 × чужое семейство): +10.7 [+3.3, +18.7] и +11.3 [+4.0, +19.3]. Чужое семейство: 5 строк → 2 (3 убрано, 0 добавлено; на таком числе строк разница не значима, p = 0.25)."

2. Add a per-author row or sentence:
   "По авторам (попадание из 50, боевой → дообученный): r6 39 → 49; cs 46 → 45 (top) / 46 (family), чужое семейство 3 → 1; stt 40 → 41 (4 исправлено, 3 сломано). Почти весь прирост попадания — на строках r6. Интервал получен пересэмплированием 150 строк как независимых и не учитывает разброс между авторами (их три) и между сидами (ens3 один)."

3. Add the comparison caveat:
   "Боевой бот обучен на старых строках всех трёх авторов, а дообученный оценивается с исключением автора. Поэтому оценка по авторам консервативна: 2 из 3 сломанных строк stt — это «beach» вместо breach, слово есть только в старых строках самого stt. На STT-подобном вводе прирост этим исследованием не показан."

4. Line 122: say that "0.0 / −0.2 [−4, +4]" is the score, and add the near figures on the 483 older lines: 441 → 433 with wrong family 12 → 8 (top gate); 437 → 440 with wrong family 9 → 11 (family gate).

5. Line 123: keep the conclusion but scope it:
   "дообучение не вредит ни одному автору и старым строкам и заметно помогает на длинных строках r6; обобщение на нового автора по трём авторам не оценить".

**Optional**
- Add a per-author print (near, wrong family, fixed / broken) to section C of scripts/coop/eval_v3.py so the log carries the breakdown. This is analysis code only; record the new hash in frozen.txt.
- frozen.txt:158 repeats "+10.7 ... +11.3" without the word "score". Do not edit the log; append a clarifying line if wanted.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every number in the finding reproduces, but its reading of the cs and stt result is incomplete and the severity is overstated.

What holds:
- HANDOFF.md:121 gives "+10.7 [+3.3, +18.7]" and "+11.3 [+4.0, +19.3]" as "the difference" without naming the quantity. They are the difference in score (near - 2 x wrong family), as eval_v3.log:82-83 correctly labels them. The near difference is +6.7 [+1.3, +12.7] (top) and +7.3 [+2.0, +13.3] (family). HANDOFF.md:122 has the same omission.
- Near-correct per author, shipped -> re-trained (family gate): r6 39 -> 49, cs 46 -> 46 (45 with top), stt 40 -> 41. Net of r6 the near gain is +0.0 [-6, +6] (top) and +1.0 [-5, +7] (family).
- Wrong family is 5 lines -> 2 (3 removed, 0 added, exact p = 0.25).
- Section C of eval_v3.log has no per-author rows, although section A does.

What the finding misses:
- The comparison is asymmetric against the re-trained model. The shipped model was trained on all 483 older lines of all three authors. Each leave-one-author-out fold model never saw a single line of the author it is scored on.
- All four "broken" lines are author-idiolect tokens: stt "beach" (twice) and "repel", cs "molly". "beach" occurs only in stt's own older lines, which the shipped model trained on and the stt fold model did not.
- So "about zero on cs and stt" is a conservative figure for this comparison, not a measured property of place re-training. The pooled gain is conservative for the same reason.

Why it is minor:
- No number is wrong and the source log is labelled correctly.
- The conclusion "re-training is needed" survives on near alone: the interval excludes 0, and McNemar gives 15 fixed / 5 broken, p = 0.041 (top), and 15 / 4, p = 0.019 (family).
- All three single seeds beat the shipped ensemble in point estimate, though only seed 2's interval excludes zero.
- Bootstrap over lines and "ens3 is one realisation" are the project's documented convention (eval_v2.py:229, COOP-BOT.md:440 and :502). HANDOFF does not restate them. With three authors an author-level interval is not estimable anyway.

*Recommended action.* Text-only change in /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md lines 121-122, carried into the planned "v3" section of COOP-BOT.md. No rule, vocabulary, spec, seed or label changes.

Replace line 121 with:

"- Разница на строках с местами по критерию владельца (попадание − 2 × чужое семейство): +10.7 [+3.3, +18.7] для top и +11.3 [+4.0, +19.3] для family. По одному попаданию: +6.7 [+1.3, +12.7] и +7.3 [+2.0, +13.3]. Бутстрэп по строкам; ens3 — одна реализация.
- По авторам (попадание из 50, боевой → дообученный, гейт family): r6 39 → 49, cs 46 → 46, stt 40 → 41. Почти весь прирост — на r6; без r6 разница по попаданию +1.0 [−5, +7].
- Сравнение несимметрично не в пользу дообученной модели: боевая обучена на старых строках всех трёх авторов, а модель фолда не видела ни одной строки отложенного автора. Три потерянные строки stt — «beach» и «repel», которые есть только в старых строках stt.
- Чужое семейство: 5 строк → 2 (3 убрано, 0 добавлено)."

In line 122 add "(тот же критерий)" after "разница".

Optional: add per-author rows to section C in eval_v3.py retrained(). If that is done, record the new hash in frozen.txt as a descriptive addition made after the results.

Do not write "the gain is about zero on cs and stt" without the asymmetry sentence.

### freeze-blindness #4: '94% on held-out stt' and '96.7% on all': rules v2 are 13 single-line patches, the stt gain is two idiom twins, and the 96.7% is unlabelled in the log

Reviewer: major, methodology. Affects: HANDOFF.md:106 and :175; frozen.txt:139; the header of eval_v3.log section A; results_v3.json; the eval_v3.py docstring.

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

The finding holds. No number is wrong, but the v2 matcher figures are not evidence that v2 generalises better than v1.

**Reconstruction of rules v1.** Reverting 14 atomic items in the current rules reproduces section A of eval_v3_rules_v1.log byte for byte. Each item is necessary: keeping any single one breaks the match. The reviewer's "13" is a counting convention (the report-verb check is a fourth code rule); the list itself is right.
- Code: 1d, 5b, 5c and the report-verb check.
- Vocabulary: zones 'to second', 'on second', 'up a floor', 'floor below'; ignore 'through the roof', 'table that'; lone_not_after 'my', 'a'; role_them 'awp', 'stack'.

**Each edit maps to one or two blind lines.**

| v2 item | exact gained |
|---|---|
| 'to second' | csv3_005 |
| 'on second' | csv3_019 |
| 'up a floor' | r6v3_020 |
| 'floor below' | r6v3_017 |
| 'table that' | csv3_041 |
| 'stack' | r6v3_029 |
| 'awp' | csv3_040 |
| 5c | r6v3_019 |
| report verbs | csv3_034 |
| 5b + report verb 'meant' | r6v3_015 |
| 'my' | csv3_035 and sttv3_034 |
| 'through the roof' | sttv3_030 only (r6v3_039 stays wrong on 'west coast') |
| 'a' | none; removes the target of older line cs_067 (120 -> 119) |
| 1d | none; raises the unknown_modifier flag on 5 lines (7 -> 12) |

**In-sample versus held-out.**
- Exact per author v1 -> v2: r6 43 -> 48, cs 44 -> 50, stt 45 -> 47.
- 11 of the 13 gained lines are the lines the edits were written from, so r6 96% / cs 100% are training figures and 96.7% is two-thirds in-sample.
- The stt gain is exactly sttv3_030 and sttv3_034, the same idioms as tuning lines r6v3_039 ('ping is through the roof') and csv3_035 ('my main').
- The three stt-only failures (sttv3_023, 036, 045) are unchanged.
- 47/50 against 45/50: exact McNemar p = 0.5; Wilson 95% for 47/50 is [83.8, 97.9], for 45/50 [78.6, 95.7].

**"Tuned on r6 and cs only" is consistent with the evidence, but stt was held out by discipline, not blindness.**
- Every item is explained by an r6 or cs line, and no stt-only failure was fixed.
- The stt mismatches were printed in the same eval_v3_rules_v1.log (lines 46-55) the tuning was done from.
- The authors share idioms: 'spiral staircase' appears for all three, 'not the north window ... I said' for cs and stt. None of these is in blind/spec_v3.json.

**Labelling.**
- HANDOFF.md:106 and :175 and frozen.txt:139 do disclose the tuning and give 88.0% first.
- eval_v3.log section A and results_v3.json carry no rules version or after-tuning mark.
- eval_v3.py:4 still says "rules frozen before the lines existed", which is false for the rules it now runs.
- Four of the edits ('my', 'a', 'awp', 'stack') appear in no description of v2: the locations.json _note, locations.py:17-19, frozen.txt:139.

**Side effects outside the blind set (corroborates single-line patching).**
- 'stack' turns the developer's own dev line 'stack up on the main door' into role=them. `--dev` cannot see this because it compares only object, qualifier and zone.
- 1d flags 12 older lines, including 'climb in through the open window' and 'throw the smoke on window when I say'.

I could not see the real v1 files (hashes 9999cc9f / 111d1a76 are not on disk). The reconstruction is observationally equivalent on the 633 lines, and 191 vocabulary entries leave no trace on those or the 254 dev lines, so the true v2 diff may be larger.

*Recommended action.* Write-up and log changes only. Do not edit locations.json (including its _note) or locations.py, so the frozen hashes and the C++ parity files stay valid.

1. **HANDOFF.md:105-106, replace the two rows with:**
   - "сопоставитель, правила v1 (заморожены до появления строк) | точная цель 88.0% (132/150, Wilson 95% [81.8, 92.3]) — цифра сопоставителя"
   - "правила v2, ПОСЛЕ ПОДГОНКИ по r6 и cs | r6 48/50 и cs 50/50 — строки, по которым правили (не оценка); отложенный stt 47/50 = 94% (на v1 было 45/50; +2 строки, обе — те же идиомы, что в строках подгонки: «ping is through the roof», «my main»; точный p = 0.5, Wilson [83.8, 97.9]). 96.7% на всех 150 на две трети обучающая цифра; лучше ли v2, чем v1, на новых строках, не показано."

2. **HANDOFF.md:175, add:** "Расхождения stt печатались в том же eval_v3_rules_v1.log, то есть stt отложен по дисциплине, а не вслепую; три автора — персоны одного генератора и делят идиомы."

3. **frozen.txt, append a dated comment under the line-139 block** with the full v2 diff taken from the developer's real v1 files (hashes 9999cc9f / 111d1a76). At minimum:
   - code: 1d, 5b, 5c, report-verb check;
   - zones: 'to second', 'on second', 'up a floor', 'floor below';
   - ignore: 'through the roof', 'table that';
   - lone_not_after: 'my', 'a';
   - role_them: 'awp', 'stack';
   - any sibling entries added with them.

4. **eval_v3.py** (record the new hash in frozen.txt):
   - line 4 docstring: "locations.py; rules v1 were frozen before the lines existed, later versions are tuned — see frozen.txt";
   - line 34 header: print LOC.VOCAB['version'] and, for version >= 2, "AFTER TUNING on authors r6 and cs; stt is the only untuned author";
   - write rules_version and tuned_on into results_v3.json;
   - re-run to refresh eval_v3.log.

5. **The future v3 section of COOP-BOT.md** should quote 88.0% as the matcher figure.

6. Any further rule or vocabulary edit needs new blind lines, preferably from a different generator.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: no**

Every factual element of the finding reproduces; I could not refute it. I downgrade it from major to minor because no number is wrong and the tuning is already disclosed where the claim is made.

What holds:
- Reverting code rules 1d / 5b / 5c plus ten vocabulary groups in the current files reproduces section A of eval_v3_rules_v1.log exactly: the same 18 mismatches with identical target, role and flag, 7 flags, 120 older lines.
- Per author, rules v1 to v2: r6 43 to 48, cs 44 to 50, stt 45 to 47.
- Every exact-outcome gain of v2 traces to an edit that also acts on an r6 or cs mismatch. This is consistent with "tuned on r6 and cs only"; I found no sign that rule was broken.
- The whole stt gain is two lines, each sharing an idiom with a tuning author:
  - sttv3_030 is fixed by the ignore phrase "through the roof", the idiom of r6v3_039. That r6 line itself stays wrong (it becomes qualifier west, flag unsure), so this edit's only exact-outcome effect on the 150 lines is on the held-out author.
  - sttv3_034 is fixed by lone_not_after "my", the "my main" idiom of csv3_035.
- The three stt-specific misses (sttv3_023, 036, 045) are identical under v1 and v2.
- 47/50 has a Wilson 95% interval of [83.8, 97.9]; 2 versus 0 discordant lines gives exact McNemar p = 0.5. So 94% is a correct held-out count but not evidence that v2 beats v1 on unseen phrasing; without the two shared-idiom lines stt is 45/50, the v1 figure.
- Four v2 word-list edits appear in no description of v2: lone_not_after "my" and "a", role_them "awp" and "stack". "my" is the edit behind one of the two stt gains.
- The v1 rule files (hashes 9999cc9f / 111d1a76) are not kept anywhere in the tree, so the v1 to v2 diff can only be audited by this kind of reconstruction.
- eval_v3.log section A and results_v3.json carry no rules version or "after tuning" mark, and eval_v3.py:4 still says "rules frozen before the lines existed". Its hash is unchanged since the pre-line freeze, so the docstring is stale, not edited.

What limits the severity:
- HANDOFF.md:105-106 lists 88.0% first as the pre-look figure and labels the v2 row "edited on authors r6 and cs".
- HANDOFF.md:175-176 says v2 was tuned on r6 and cs only, stt is the held-out check, and further edits need new blind lines.
- frozen.txt:139 says "AFTER the first blind v3 run".
- HANDOFF does not claim a significant v2 gain; only frozen.txt:139 implies one ("94.0%, was 90.0%").
- No decision depends on 94 versus 90: the matcher ships as rules v2 either way, and sections B and C do not use these figures.
- The cross-author repetition caveat already exists for v1 (COOP-BOT.md:57-63, DEBERTA-BOT.md:70-74: authors are one model family and repeat each other, so anything tuned on some authors is flattered on the others). It is simply not attached to the v3 matcher number.

Small inexactnesses in the finding that do not change its conclusion:
- 1d changes only flags (five lines, including sttv3_018), not exact outcomes.
- lone_not_after "a" changes no v3 line, only the older line cs_067.
- r6v3_015 needs 5b and the report verbs together.
- "awp" and the report verbs also change the role on csv3_017 and sttv3_012.

*Recommended action.* Wording and labels only; no change to rules, vocabulary, spec, seeds or labels.

1. HANDOFF.md:106, and the v3 section of COOP-BOT.md when it is written: keep 88.0% (rules v1, before the lines were seen) as the matcher figure. Replace the v2 cell with: "после подгонки по r6 и cs: 98/100 на этих авторах; 47/50 = 94% [84-98] на отложенном stt (было 45/50; обе новые строки повторяют идиомы авторов подгонки: 'ping is through the roof', 'my main'; три собственных промаха stt не изменились); 145/150 = 96.7% на всех, из них две трети — строки подгонки".

2. HANDOFF.md:175: add one sentence that stt is held out from the rule edits but not independent of r6 and cs, because the authors are one model family and repeat idioms (the same caveat as COOP-BOT.md:57-63).

3. frozen.txt: append a dated comment listing the full v2 edit set, including the four undocumented ones (lone_not_after +my, +a; role_them +awp, +stack), and noting that the v1 files were not kept. Put it here rather than in the locations.json _note, so the vocabulary hash 890d651a and the exported intent_config.json stay unchanged.

4. eval_v3.py: change docstring line 4 to say rules v1 were frozen before the lines existed; print LOC.VOCAB["version"] and "after tuning on r6, cs" in the section A header; store the rules version in results_v3.json. Record the new eval_v3.py and eval_v3.log hashes in frozen.txt as an edit made after results.

5. No further rule edits without new blind lines (already HANDOFF.md:176), preferably from a different generator.

### freeze-blindness #5: Matcher figures are upper bounds: the spec hands the authors the dictionary's names, and every phrasing outside the dictionary was missed

Reviewer: major, methodology. Affects: HANDOFF.md:105-106: the 88.0%, 94% and 96.7% matcher figures as statements about how well places are found.

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

Every count in the finding reproduces. No reported number is wrong; the problem is what the 88.0 / 94 / 96.7% matcher figures can be read as. Two sentences of the finding are overstated, and one consequence for the held-out 94% is stronger than the reviewer stated.

**What holds**
- **The spec prints the dictionary's canonical names.** `blind/spec_v3.json` "map" lists the six objects, ten qualifiers and seven zones, and the target text gives 'push main', 'take blue', 'the back door', 'the left window', 'the blue door'.
- **Most place lines stay on the printed names.** 144 of 150 lines have a truth place; 119 (82.6%) use only spec-printed words and 25 use some other form.
- **Rules v1 are weaker off the list.** Exact target is 112/119 (94.1%) on the printed-names lines and 20/25 (80.0%) on the others.
- **Nothing outside the v1 dictionary was found.** Six lines carry the target in a form v1 lacked, and v1 got 0 of 6: 'up a floor', 'the floor below' (the spec's own gloss), bare 'second' twice, 'rough', 'second story'. Two more lines contain 'rough' but are still right (target elsewhere, or self-corrected to 'rooftop').
- **The 18 v1 errors split evenly:** 6 form not in dictionary, 6 dictionary word in another sense (other_sense 0/6), 6 role or choice logic (two_places 10/15).
- **The three authors are not independent.** 'the spiral staircase/stares' appears in 3 of 3 authors, gamer-sense 'main' in 3 of 3, 'ping is through the roof' in 2 of 3.
- **'stares' was in the v1 dictionary without any developer evidence for it.** It is absent from the 254 dev lines, the 483 older lines, the seeds and the spec; the stt author spelled it 'stairs' in older lines and 'stares' in 8 of 50 v3 lines. 'rough' for roof (3 lines) was not anticipated.

**What is overstated or imprecise**
- **'staircase' is printed in the spec** ("stairs": "a staircase: ..."). Counting it as printed gives 123/144 (85.4%) on-list, with v1 exact 116/123 on-list and 16/21 off-list. This strengthens the reviewer's point.
- **"88.0% measures how rarely authors leave the list" is too strong.** Authors left the printed list in 17% of place lines, and v1's own synonyms (couch, stairwell, rooftop, stares) carried 20 of those 25. With the dictionary cut to spec-printed names only, the current rules score 133/150 instead of 145/150.
- **"Every phrasing outside the dictionary was missed" is true by construction** for a dictionary matcher.
- **"Upper bound" is an inference, not a measurement.** The direction is supported (94% on-list vs 80% off-list vs 0% out-of-dictionary), but the size for unprimed speech is unknown.
- **'stares' in v1 is inferred, not read.** The v1 `locations.json` is not on disk; my ablation agrees with the inference.

**Consequence for the held-out 94%**
- Rules v2 changed nothing on stt's 48 place lines: 45/48 under v1 and under v2.
- The whole 90 → 94 gain is two chatter lines, sttv3_030 ('ping is through the roof') and sttv3_034 ('my main').
- Both were fixed by edits prompted by the same idioms in the tuning authors' lines (r6v3_039, csv3_035).
- So 94% is not an independent check of the v2 rules; the stt figure untouched by tuning is 90%.

*Recommended action.* Documentation only; do not edit `locations.json`, `locations.py`, the spec, the seeds or the labels.

**1. `HANDOFF.md`, under the table at lines 103-108, and the same text in the future "v3" section of `COOP-BOT.md` / `DEBERTA-BOT.md`.** Add:

"The blind authors were given the map's names (`blind/spec_v3.json`, 'map'), so the matcher figures are conditional on listed wording and are upper bounds for free player speech. Of the 144 lines with a place, 119 use only names printed in the spec (123 counting 'staircase'). Rules v1 exact: 112/119 (94.1%) on those, 20/25 (80.0%) on lines with any other wording, 0/6 where the target's wording was not in the dictionary ('up a floor', 'the floor below', bare 'second' twice, 'rough', 'second story'). The 18 v1 errors: 6 wording not in the dictionary, 6 a dictionary word in another sense, 6 role or choice of primary."

**2. The same table, row "правила v2 ... 94% на отложенном авторе stt".** Add:

"Rules v2 changed nothing on stt's 48 place lines (45/48 before and after). The 90 → 94 gain is two chatter lines (sttv3_030 'ping is through the roof', sttv3_034 'my main') whose idioms the tuning authors also wrote (r6v3_039, csv3_035). The three authors are not independent; 90% is the stt figure untouched by tuning."

**3. `COOP-BOT.md` "Corrections after review" for v3.** Add one row in the style of line 573: matcher 88.0 / 94 / 96.7 → "upper bounds; conditional on listed names" → "spec prints the names; authors share idioms".

**4. If an unconditional figure is wanted.** Collect new blind lines from authors briefed on the map layout without the name list, or use real transcripts. Adding 'rough' or 'second story' to the dictionary and re-quoting the stt number would be post-hoc tuning on the held-out author and would touch frozen material.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: no**

The facts hold and no document carries the caveat for v3; I could not refute it. Two corrections to the finding's wording and one to its count.

What stands:
- blind/spec_v3.json prints the map's names and tells authors "players use the names in orders and callouts". The authors stayed on them.
- The matcher figures 88.0 / 94 / 96.7 measure role and primary-target logic and other-sense handling on lines worded with listed names. They carry almost no evidence about wording outside locations.json.
- Every truth place worded outside the dictionary was missed: rules v1 0 of 5 ("up a floor", bare "second" twice, "rough", "second story"), plus "the floor below", which is the spec's own gloss.
- Rules v2 added the r6/cs forms. On held-out stt the two out-of-dictionary wordings ("rough", "second story") are still missed, and they are 2 of the 3 stt misses.
- The stt gain from 90 to 94 comes only from sttv3_030 and sttv3_034, idioms the tuning authors also wrote ("ping is through the roof", "my main").
- 61 of the 95 dictionary surface forms never occur in any blind line. The only pre-existing non-spec synonyms exercised are couch, stairwell, rooftop and stares.
- On the plain "place" kind, all 4 of the v1 misses (56/60) are wording misses.

Corrections:
- **Count:** "staircase" is printed in the spec ("stairs: a staircase: ..."). The split is therefore 123 of 144 lines (85%) spec-only wording and 21 other, not 119 / 25. Rules v1 score 116/123 and 16/21; rules v2 score 122/123 and 19/21.
- **"Upper bound" is not shown; "conditional" is.** 90 of the 150 lines are hard kinds by a fixed per-author quota (v1: other_sense 0/6, two_places 10/15), which pulls the other way relative to real traffic.
- **The correlation signs are weaker than stated.** "stares" is ordinary homophone anticipation: "base mint" and "bass mint" are in the dictionary too and no author used them, while "rough" was not anticipated. The identical "spiral staircase" and "my main" items cannot be attributed, because the authors got a brief with kind quotas that is not in the archive.

Why severity is minor, not major: a closed vocabulary is the declared design (locations.py:10-11, HANDOFF.md:88-91), HANDOFF states the figures as results on the 150 blind lines without a coverage claim, no number changes, and the v3 write-up is not written yet (HANDOFF step 5). The project's own precedent (COOP-BOT.md:351-352 and :573) does require this caveat next to the number.

*Recommended action.* Write-up only; do not change locations.json or locations.py.

1. Under the table at /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md:103-108, and in the v3 section of COOP-BOT.md when it is written (HANDOFF step 5), add:

"The blind authors were given the map's names (blind/spec_v3.json), and 123 of the 144 lines that name a place use only those words. The matcher figures therefore hold for a player who uses a listed name. A place worded outside locations.json is missed until a line is added: rules v1 found 0 of 5 such places, and on the held-out author stt rules v2 found 0 of 2 ('rough', 'second story'). 61 of the 95 dictionary forms never occur in the blind lines."

2. Report the split next to the headline figures:

| wording of the truth place | rules v1 | rules v2 |
|---|---|---|
| spec words only | 116/123 | 122/123 |
| other wording | 16/21 | 19/21 |

3. Add a row to "Corrections after review" in the style of COOP-BOT.md:573.

4. Do not "fix" this by adding "rough", "second story" or other blind-line forms to locations.json. That is tuning after the lines were seen and would void the stt held-out number (HANDOFF section 6).

5. For an unconditional figure, write new blind lines with authors who get the map described in prose without the name list, or use playtest logs (coop_bot_log.jsonl). Archive the author brief next to the spec.

### freeze-blindness #6: The two annotators are not independent readers: one v3 pair is byte-identical and no annotator changes any scored label

Reviewer: major, methodology. Affects: The description of v3 truth (HANDOFF.md:98, eval_v3.log header) and any statement that the labels were cross-checked. Scored numbers do not change: I read all 150 labelled lines and found no intent or target I would dispute.

**Verifier (reproduce): confirmed, minor; reproduced: yes; touches frozen: no**

Every factual element of the finding reproduces. Two clauses need tightening, and the problem is a missing caveat, not a wrong number.

What holds:
- annot/v3/author_r6_ann1.json and author_r6_ann2.json are the same file (sha256 07378aece559..., recorded twice at frozen.txt:134-135; mtimes 21:00:21 and 21:00:32).
- On all 150 v3 lines the author, ann1 and ann2 give the same intent, timing and 4-field target. The v3 truth for intent, timing, target and unknown_modifier is therefore the author's label on 150/150 lines. "Unanimous on 150" (eval_v3.log line 1 and the section A header) measures agreement between agents of one model family reading one spec, not label correctness.
- The unscored `reference` field splits by reader, not by line. Convention A ('this' on every order that names an object) is used by the r6 author, both r6 annotators and stt ann1. Convention B ('none') is used by the cs author, both cs annotators, the stt author and stt ann2. 5 of 6 annotators share their own author's convention, which has probability 7/64 = 0.11 under a fair coin, so it is weak evidence and cannot separate "saw the labels" from "same model, same prompt".
- The v1 and v2 write-ups carry the caveat (COOP-BOT.md:57-58 and :501). The v3 text (HANDOFF.md:98 and :174) does not.

Corrections to the finding:
1. "Equals the author's label on every scored field" is not exact. Author files have no `ok` list, so the scored `accept` set (coop_v2.py:96, used by score() at :200) comes from the annotators. It is wider than {author intent} on 19 lines, 14 of them with an intent from another family. This moves the headline numbers by 1-2 lines:

| | near, as reported | near, author intent only | wrong family, as reported | wrong family, author intent only |
|---|---|---|---|---|
| shipped, raw | 83.3 | 82.0 | 3.3% | 4.7% |
| re-trained, top gate | 90.0 | 89.3 | 1.3% | 2.0% |
| re-trained, family gate | 90.7 | 90.0 | 1.3% | 2.0% |

The difference vs shipped stays clearly positive: +12.7 [+4.7, +22.0] (top) and +13.3 [+5.3, +22.7] (family). The one line that helps the re-trained model, r6v3_003 (NONE, ok WAIT), is an r6 line, where the "two readers" behind the 2-of-3 rule are the identical files.

2. The identical r6 pair is not by itself evidence of a leak or a pipeline duplicate.
- The v3 annotation files are script-normalised (indent=1, CRLF), so byte-identical means content-identical and nothing more.
- There is a precedent: annot/v2/author_cs_ann1.json and _ann2.json are content-identical on 40/40 records, including 13 non-empty ok lists, while formatted differently (4286 vs 3489 bytes), so they were written separately.
- The r6 files were written 11 s apart, like the cs pair (10 s) and the stt pair (16 s).
- stt ann1 differs from its author on `reference` on 30/50 lines, so at least that annotator did not copy.

3. "For lines that name a place" should read "for orders that name an object": the r6 readers give 'this' on 29 lines and 'none' on 16 other place-naming lines (zone-only, qualifier-only, callouts).

I read all 150 labelled lines and found no intent or target to dispute, with the limit that I am the same model family. No project rule is shown broken. The workflow journal wf_04800970-338 is not on this machine, so what the annotators were shown cannot be checked here.

*Recommended action.* Write-up only; do not touch annot/v3, blind/v3, the spec or the truth code.

1. /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md, after line 98, add: «Истина v3 фактически равна метке автора: автор и оба аннотатора совпали по приказу, таймингу и цели на 150 из 150 строк. Авторы и аннотаторы — агенты одной модели (как в v1 и v2), а файлы двух аннотаторов автора r6 совпадают полностью, поэтому единогласие не подтверждает правильность меток. Аннотаторы влияют на цифры только списками `ok` (19 строк): без них попадание боевого бота 82.0% вместо 83.3% и чужое семейство 4.7% вместо 3.3%, у дообученного 89.3 / 90.0 и 2.0%.»

2. In the "v3" section of COOP-BOT.md still to be written (HANDOFF step 5), put the same under Caveats, next to the v2 wording at COOP-BOT.md:501: "The truth on the 150 v3 lines is the author's label: author and both annotators give the same intent, timing and target on 150/150. They are agents of one model family and the two r6 annotation files are identical, so unanimity is not a check of the labels. Annotators enter the scores only through `ok` alternates (19 lines, worth 1-2 lines of near)." Do not cite "unanimous on 150" as validation of the matcher truth.

3. On the Windows work machine, open the journal of workflow wf_04800970-338 and confirm that r6 ann1 and r6 ann2 came from two separate agent runs. Record the answer in the write-up.

4. Optional independent check: have a different model or a person label a sample from blind/v3/author_*_lines.json and report the agreement as a new, separately logged measurement. Do not edit annot/v3 or the truth. Changing labels after the lines were seen would touch frozen material and would have to be recorded in frozen.txt, with the numbers marked as after tuning.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every fact in the finding holds, but the inference in its title and the "major" severity do not, and one sub-claim needs correcting.

**What holds**
- `annot/v3/author_r6_ann1.json` and `author_r6_ann2.json` are identical (same sha256, also at `frozen.txt:134-135`).
- Author, ann1 and ann2 agree on intent, timing and the 4-field target on 150/150 lines, so v3 truth on those fields is the author's label.
- The `reference` triples and the v1/v2 agreement rates are as reported.

**What does not hold**
- **Byte-identity is not separate evidence of a duplicate.** All six v3 annotation files are exactly `json.dumps(obj, indent=1)` with CRLF, holding categorical fields only. Identical bytes therefore mean no more than identical labels on 50 records.
- **A fully identical pair has a precedent.** The v2 cs pair is parsed-equal on 40/40 records, including 13 non-empty `ok` lists and 5 lines where both differ from the author on `reference`. Those two files have different serialisations, so they were written separately.
- **The r6 timing is not special.** Its 11 s gap matches the 10 s and 16 s gaps of the other two pairs.
- **The `reference` split carries about one bit per reader.** Within a file it is a fixed function of intent and target: "this" if an order names an object, or always "none". The reviewer's 0.1 figure is correct and weak, as they say. The stt ann1 split on 30 lines shows that reader did not copy the author.
- **No existing text presents unanimity as validation.** `HANDOFF.md:98` and the `eval_v3.log` header give counts only. The one-model-family caveat is already written for v1 and v2 (`COOP-BOT.md:57-58`, `:501`), and the v3 write-up is still a to-do (HANDOFF section 5, steps 4-5).

**Correction to the finding**
The reviewer says scored numbers do not depend on the annotators. They do, through the `ok` lists: `coop_v2.py:96` accepts an alternative intent when two readers list it, and the author has no `ok` field. 19 of the 150 lines carry such an alternative.

The identical r6 pair decides one scored line. On r6v3_003 (truth NONE) all three classifiers answer WAIT, which counts as near only because both r6 files list WAIT.

| truth variant | shipped near / wrong family | re-trained near (top / family) | re-trained wrong family | difference vs shipped |
|---|---|---|---|---|
| as reported | 83.3 / 3.3 | 90.0 / 90.7 | 1.3 | +10.7 [+3.3,+18.7] / +11.3 [+4.0,+19.3] |
| r6 pair counted as one reader | 82.7 / 4.0 | 89.3 / 90.0 | 2.0 | unchanged |
| author label only | 82.0 / 4.7 | 89.3 / 90.0 | 2.0 | +12.7 [+4.7,+22.0] / +13.3 [+5.3,+22.7] |

The matcher numbers (88.0 / 96.7 / 94) do not depend on the annotators at all.

So this is a wording caveat for the v3 write-up plus a sensitivity of at most 0.7 points on the absolute intent numbers. It is not evidence of a broken or leaky annotation step.

*Recommended action.* No change to labels, annotation files, spec, rules or code.

1. **Add the caveat to the v3 write-up.** In the "v3" section still to be written in `/Users/t.losiev/Documents/models_training/project_synth/COOP-BOT.md` (and its `DEBERTA-BOT.md` counterpart), and as one clause at `HANDOFF.md:98`, add: "Truth on the 150 v3 lines is in effect the author's label: author and both annotators agree on intent, timing and target on 150/150, and the r6 annotator pair is identical on all 50 records (frozen.txt:134-135). Authors and annotators are agents of one model family reading the same spec, so this unanimity shows consistency, not correctness."

2. **Add the sensitivity line beside the section B/C table.** "The annotators' only scored input is the `ok` lists (19 lines with an accepted alternative). Counting the identical r6 pair as one reader moves one line (r6v3_003, NONE answered as WAIT): shipped 82.7 near / 4.0% wrong family, re-trained 89.3 / 90.0 near and 2.0%; the differences +10.7 and +11.3 are unchanged."

3. **Do not call the v3 annotators "independent".** `DEBERTA-BOT.md:68` uses «независимых аннотатора» for v1; the v3 text should not repeat it.

Optional and not required: a fresh reading of `blind/v3/author_r6_lines.json` by a different model or a person. Adding it would change v3 truth after the blind lines were seen, so it would have to be logged in `frozen.txt` and reported next to the current numbers, not in place of them.

### freeze-blindness #7: Audit gaps: v1 rule files and the blind workflow prompts are not archived; one unrecorded hash; one stale script

Reviewer: minor, docs. Affects: Reproducibility of the 88.0% claim; the blindness statement in HANDOFF section 6; the hash log's completeness (the 1 of 92 mismatch already known).

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

All four gaps exist as stated. None changes a headline number, but (a) and (b) are slightly worse than the reviewer described, and one part of (b) is overstated.

(a) Rules v1 are gone. No file with sha 111d1a76 / 9999cc9f exists in the tree or in coop-bot-code.tar.gz, and neither locations.py nor eval_v3.py has a rules-version switch. The 88.0% rests only on eval_v3_rules_v1.log (hash recorded at frozen.txt:142).
- Mitigation: a behavioural revert of the current files reproduces that log exactly (132/150; r6/cs/stt 43/44/45; all 18 mismatch rows with the same output, role and flag; unknown_modifier raised on 7; 120 older lines). So the 88.0% is credible as the output of a precursor of today's code.
- New: the revert only works if four word-list entries that no change note names are also removed: role_them 'awp' and 'stack', lone_not_after 'my' and 'a'. Reverting only what locations.py:17-18, the locations.json _note and frozen.txt:139 describe gives 136/150 and 119 older lines. The documented v1 -> v2 delta is therefore incomplete and cannot be audited.
- Nothing contradicts "tuned on r6 and cs only": the trigger lines are r6v3_029, csv3_040 and csv3_035, and the three remaining stt misses are stt-specific.
- Both held-out stt gains (45 -> 47) come from edits whose r6/cs trigger line shares the phrase with the stt line ('ping is through the roof', 'my main').

(b) Authors did get identical per-kind quotas (20/5/5/5/4/4/3/2/2), with kind names absent from spec_v3.json, and no workflow prompt or script is archived for any version.
- Overstated: this is the project's standing, disclosed practice, not a new breach. The v1 and v2 author files show the same identical-quota pattern, and COOP-BOT.md:45 and :386-389 state the quotas next to "seeing only blind/spec.json". HANDOFF.md:174 is shorthand; what is missing is the v3 quota disclosure (the v3 write-up is still a to-do, HANDOFF section 5 item 5).
- I found no evidence that dev lines or rules reached the authors: 'spiral' and 'through the roof' are absent from locations_dev.json, the seeds and the spec.
- New, and the reason the missing prompts matter: annot/v3/author_r6_ann1.json and author_r6_ann2.json are byte-identical (same hash at frozen.txt:134-135). Five of the six annotator files equal the author's labels on all 7 fields for 50/50 lines, including `reference`, where the authors themselves diverge. Whether r6's two readings are independent, or annotators saw labels, cannot be decided without the prompts. Truth is unanimous on 150/150, so no number moves, but "two annotators each" is unverified for r6.

(c) coop_cli.cpp is sha 6f3b83cf on disk; the last recorded hash is 6114308f (frozen.txt:153). Its mtime 22:00:47 sits with CMakeLists.txt (22:00:28) and tokenizer.cpp (22:00:45), but the 22:26:03 block records only those two. The tarball carries the same file and the same omission, so it originated on the Windows machine, not from today's Mac work. Eight other C++/tool files were never recorded at all, including bot_brain.h, edited at 21:06:13 in the "places in the bot" step. None of this is frozen-before-test material.

(d) v3_noharm.py and results_v3_noharm.json (mtime 20:35, before the v1 freeze at 20:55:13) are in no frozen.txt block. The script's third mode hits `assert mode == "strip"` (locations.py:441), so it would crash before writing its JSON. No HANDOFF figure depends on it; the "older lines 0.0 / -0.2" comes from eval_v3.log section C.

*Recommended action.* No edit to locations.py, locations.json, the spec, the seeds or the labels is needed. Keep every correction in the write-up and in frozen.txt comments.

1. HANDOFF.md section 4 (row "сопоставитель, правила v1") and the future v3 section of COOP-BOT.md: add "locations.py / locations.json v1 (sha 111d1a76... / 9999cc9f...) were overwritten and are not archived; 88.0% is documented only by eval_v3_rules_v1.log (sha 1ff6fd96...) and cannot be re-run". If the two files survive on the Windows machine (editor history or backup), add them as scripts/coop/locations_v1.py and locations_v1.json and check them against those hashes.

2. In the same write-up, and as a dated comment block in scripts/coop/frozen.txt, itemise the v2 edits completely. Besides rules 1d, 5b, 5c, the report verbs, the relative-floor phrases, 'to/on second' and the ignore phrases, v2 also added enemy words to role_them (at least 'awp', 'stack') and words to lone_not_after (at least 'my', 'a'). Name the r6/cs trigger line for each. Do not put this list into the locations.py docstring or the locations.json _note: both files are hash-recorded as rules v2.

3. HANDOFF.md:174: replace with "Слепые авторы получают blind/spec_v*.json, роль и квоты по типам строк (v3: place 20, zone_object 5, two_places 5, callout 5, on_signal 4, unnamed 4, other_ref 3, negated 2, other_sense 2); аннотаторы — спецификацию и строки без меток. Промпты и скрипты workflow в архив не вошли." Add the same quota sentence to the v3 section of COOP-BOT.md, as lines 45 and 386-389 do for v1 and v2.

4. Archive the scripts and prompts of wf_04800970-338 and wf_e7746201-bd5 next to scripts/coop/blind/v3 and annot/v3. State in the write-up that annot/v3/author_r6_ann1.json and author_r6_ann2.json are byte-identical, and what the annotators were given. If the prompts cannot be recovered, say that the independence of the r6 annotation is unverified.

5. scripts/coop/frozen.txt: append a dated block recording 6f3b83cfe7a41b11dd33d57f00f052898d3dc0467f49379c71fc9996eabd6fe7 for ../../cpp/coop_intent/tools/coop_cli.cpp, with the note "edited 2026-10-03 22:00:47 in the portability pass; hash omitted from the 22:26:03 block; recorded after the fact". Optionally add first hashes for the never-recorded C++ files (bot_brain.h and the others).

6. scripts/coop/v3_noharm.py and results_v3_noharm.json: delete them, or move them to an attic folder with a note that they are a pre-freeze exploration on the 483 old lines. If the script is kept, drop "strip+zone" from its own mode tuple; do not re-add the mode to locations.py.

### freeze-blindness #8: Wording of two side claims is stronger than the evidence: 'names stripped' and 'older orders not harmed'

Reviewer: minor, numbers. Affects: HANDOFF.md:107-110 (the strip row and its conclusion) and :122 (older lines).

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Both sub-claims reproduce to the digit, and HANDOFF.md does not qualify either sentence. This is a write-up defect only; neither decision changes.

**Root cause shared by lines 108, 121 and 122:** HANDOFF.md never defines the "score" (near − 2 × wrong family; only COOP-BOT.md:168 does). Its tables show near and wrong family, but every "разница / пункта" figure is a score difference. A reader takes them as near differences.

**(1) HANDOFF.md:108–110, "названия вырезаны … хуже на 3.3 пункта"**
- "strip" removes only a qualifier attached to an object; lone qualifiers and zones stay (locations.py:46–49).
- It rewrites 58 of 150 lines (r6 21, cs 16, stt 21) and changes 3 answers, all on author stt.
- Near goes 125 → 122 (−2.0 points), wrong family 5 → 6 (3.3% → 4.0%), score −3.3 [−8.0, 0.0].
- One line, sttv3_011 (a callout that now fires HOLD_ANGLE), accounts for 3 of the 5 lost score points. The other two fall just under the 0.58 threshold.
- All three changes are regressions: per-line deltas are 147 × 0, 2 × −1, 1 × −3. The interval's upper bound of 0.0 is therefore structural.
- The supported statement is "stripping helped on no line", which is enough for "the model reads the raw line". The magnitude 3.3 is a score figure resting on three lines of one author.
- The choice was made after the first blind run (frozen.txt:139 says "raw beats strip"). It keeps the status quo and is conservative: the shipped baseline of 83.3 is the higher of the two, so it does not inflate the re-training gain.

**(2) HANDOFF.md:122, "0.0 / −0.2 [−4, +4], то есть старые приказы не пострадали"**

| gate | score diff | near (v21 → v3) | wrong family | answers changed | fixed / broken |
|---|---|---|---|---|---|
| top | +0.0 [−3.9, +4.1] | 441 → 433 (−1.7 points) | 12 → 8 | 38 | 9 / 17 |
| family (shipped) | −0.2 [−4.3, +3.7] | 437 → 440 | 9 → 11 | 39 | 15 / 12 |

- Under the top gate the near loss is mostly abstention: 14 of the 17 broken lines became NONE, because the out-of-fold thresholds rose from 0.42–0.50 to 0.58–0.62. Author r6 alone goes 151 → 143.
- Under the family gate 8 of the 12 broken lines became NONE and 4 became a wrong action.
- No component differs significantly. Near: top −1.7 [−3.7, +0.4], family +0.6 [−1.4, +2.7]. Wrong family: top −0.8 [−2.3, +0.6], family +0.4 [−0.8, +1.9].
- The accurate wording is "no net change in score; a loss larger than about 4 score points is excluded; about 8% of answers change". "Not harmed" overstates that.
- The project's own precedent is stricter: COOP-BOT.md:466–469 reported a comparable v21 − v2 change (−1.2 [−4.1, +1.7], wrong family 5 → 9) with counts, under the heading "has a price".

**Refutation attempts that failed**
- eval_v3.log:35 and :84–85 carry the intervals and "answers that differ: 3", and locations.py documents what strip does. So the logs are honest, but the HANDOFF sentences under review drop the metric name, the interval and the counts.
- No other document covers it: COOP-BOT.md and DEBERTA-BOT.md have no v3 section yet.

*Recommended action.* Edit the write-up only, in /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md, and carry the same wording into the future v3 section of COOP-BOT.md. No rule, vocabulary, spec, seed or label changes.

1. **Before the table at line 103**, add one line defining the metric: «критерий = попадание − 2 × чужое семейство; все "разницы" ниже — разницы критерия, парный бутстрэп по строкам».

2. **Line 108**, replace the row with: «то же, прикреплённые к объекту квалификаторы вырезаны (переписано 58 строк; меняются 3 ответа, все у автора stt, все в худшую сторону) | попадание 81.3% (−2.0), чужое семейство 4.0%; критерий −3.3 [−8.0, 0.0]».

3. **Line 110**, replace with: «Вывод: вырезание не помогло ни на одной строке, модель читает сырую строку (выбор сделан по слепым строкам, оставлен вариант по умолчанию)».

4. **Line 121**, label the numbers as the criterion and add near: «разница критерия +10.7 [+3.3, +18.7] / +11.3 [+4.0, +19.3]; по попаданию +6.7 / +7.3».

5. **Line 122**, replace with: «На 483 старых строках критерий не изменился: 0.0 [−3.9, +4.1] (top) / −0.2 [−4.3, +3.7] (family), то есть потеря больше ~4 пунктов исключена. top: попадание 441 → 433, чужое семейство 12 → 8; family: 437 → 440, 9 → 11. Ответ меняется на 38–39 строках из 483».

### freeze-blindness: checked and found right

- Chronology in frozen.txt matches the archived mtimes for every v3 block: locations_dev.json 20:54:06, make_spec_v3.py 20:55:11, spec_v3.json and seed_commands_v3.json 20:55:13 (block 20:55:13); first blind file 20:58:00.
- Evaluation code predates the blind files: coop_v2.py 20:56:25, eval_v2.py 20:57:18, v3_shipped.py 20:57:19, eval_v3.py 20:57:21 (block 20:57:31); blind and annotation files 20:58:00-21:00:32 (block 21:00:44). eval_v3.py on disk still has the hash recorded then (521657ba).
- Rules v2 come after the first blind run: results_v3_shipped.json 21:01:16; locations.py, locations.json and eval_v3_rules_v1.log all 21:02:42 (block 21:03:00).
- Places in the bot precede any re-training result: coop_bot.py 21:03:58, locations.h/.cpp and bot_brain 21:04:15-21:06:13, gen_tests.py and export_cpp.py 21:08:28, parity files 21:09:16-17 (block 21:09:54); the cv ran as three parallel processes of about 1890 s ending 22:25:13-25, so it started about 21:53:45.
- The train_v2.py speed-up precedes the cv: pristine train_v2.py has sha 6b46927c and mtime 21:37:13 (block 21:37:53). Each cv log shows one clean run of 18 model loads. Recipe metadata in results_v3_probs_*.json equals the v21 study's (20 epochs, batch 16, lr 5e-5, wd 0.01, warm-up 0.1).
- spec_v3.json and seed_commands_v3.json regenerate identically (modulo CRLF) from the frozen make_spec_v3.py in a scratch copy: 150 templated place seeds, 383 seeds in total.
- The 88.0% run is consistent with rules v2 minus the v2 edits: reverting 13 edits reproduces eval_v3_rules_v1.log exactly (18 mismatches with the same target, role and flag; unknown_modifier 7/7; 120 older lines with a target).
- 'Tuned on r6 and cs only' is consistent with the rules: every v2 edit that changes a blind line's exact outcome is exercised by at least one r6 or cs line, none only by stt lines; the stt-only failures (sttv3_023, 036, 045) are unchanged between the two logs.
- Per-author change between the two logs: r6 43 -> 48 (fixed 015, 017, 019, 020, 029), cs 44 -> 50 (fixed 005, 019, 034, 035, 040, 041), stt 45 -> 47 (fixed 030, 034); r6v3_039 changes its wrong answer.
- The strip comparison is valid under rules v2 as well: strip_text stored in results_v3_shipped.json equals the current rules' normalized(text, 'strip') on 150/150 lines.
- Thresholds are not fitted on test lines: the out-of-fold dictionaries in results_v3_probs_*.json hold 805 ids (422 training lines + 383 seeds) and 0 ids of the held-out author; fold thresholds top 0.62/0.58/0.58, family 0.60/0.58/0.52. The shipped bot's family gate and 0.58 come from its own out-of-fold fit (bot_config.json oof_fits).
- The unlabeled files are unlabeled: blind/v3/author_*_lines.json hold only id and text, in the author file's order, with kinds interleaved; annotator files cover exactly those ids.
- No blind v3 line is a verbatim (normalised) copy of a seed command or of a developer regression line (0/150 each).
- The re-training gain is not an artefact of copied lines: by the project's own novelty measure 90 of 150 v3 lines are novel, and on those the gain is +8.9 [+1.1, +17.8] (top) / +10.0 [+2.2, +18.9] (family) in score.
- Headline classifier numbers reproduce from the stored probabilities: shipped 125/150 near and 5/150 wrong family; re-trained 135 (top) / 136 (family) near and 2/150 wrong family; score differences +10.7 [+3.3,+18.7] and +11.3 [+4.0,+19.3]; older lines +0.0 / -0.2.
- python locations.py --dev in a scratch copy: 254 lines, 5 failures; the reconstructed v1 fails the same 5, so v2 introduced no regression that the dev check can measure.
- HANDOFF.md:106 does disclose that rules v2 were edited on authors r6 and cs.
- Label sanity: I read all 150 v3 lines with their intent and target labels and found none I would dispute against spec_v3.json.

## The numbers (`numbers`)

### numbers #1: The whole classifier gain on the v3 lines comes from one author (r6); without r6 the hit-rate gain is +0 / +1 point and the CI spans zero

Reviewer: major, evaluation. Affects: HANDOFF.md section 4, 'Разница на строках с местами: +10.7 [+3.3, +18.7] ... +11.3 [+4.0, +19.3]' and the conclusion 'дообучение нужно'; eval_v3.log section C (no per-author rows for the classifier)

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

Every number in the finding reproduces from the raw files with my own code. No published number is wrong and the decision to re-train is not overturned; what is missing is the per-author breakdown and the scope of the CI.

**Per author, near-correct of 50 (shipped -> re-trained top / family):**
- r6: 39 -> 49 / 49
- cs: 46 -> 45 / 46
- stt: 40 -> 41 / 41

Wrong family (shipped -> re-trained, family gate): r6 1 -> 0, cs 3 -> 1, stt 1 -> 1.

**Where the gain sits:**
- Hit rate: 10 of the net +11 (family) and 10 of the net +10 (top) lines are r6. All 10 are lines where shipped said NONE and the re-trained model is right.
- Published statistic (score = near - 2 x wrong family): r6 is 12 of 17 line-points (family) and 12 of 16 (top), about 71-75%, not all of it. The rest is mostly cs's wrong-family drop from 3 to 1.
- Per-author score gains: +24 / +8 / +2 (family), +24 / +6 / +2 (top). No author gets a worse score.

**Without r6 (n=100):**
- near: +1.0 [-5.0,+7.0] family (5 up / 4 down), +0.0 [-6.0,+6.0] top (5 / 5)
- score: +5.0 [-3.0,+14.0] family, +4.0 [-4.0,+14.0] top
- The reviewer's upper bound of +15.0 for family score is +14.0 in my run; that is bootstrap noise.

Dropping cs or stt instead leaves the gain intact (+13 and +15/+16 score, CIs above zero).

**The published CI:** eval_v3.py:86-90 resamples the 150 lines with no clustering by author, so [+3.3,+18.7] is a CI over lines of these three authors. A t(2) interval over the three per-author gains is [-16.9,+39.6] (family) and [-18.4,+39.8] (top).

**stt:** 41/50 = 82% near, 4 lines better and 3 worse; intent-near AND target-exact is 39/50 = 78% (shipped 38/50). COOP-BOT.md:144 itself calls the stt author "the one closest to a real input pipeline".

**By intent (shipped -> re-trained, family):** MOVE_TO 13 -> 19 of 22, SMOKE 9 -> 12 of 12, BREACH 5 -> 3 of 5, RAPPEL 6 -> 5 of 6.

**Mitigation, verified and wider than the reviewer stated:**
- The shipped model trained on all 483 older lines of all three authors (bot_config.json "trained_on"). Each fold model saw nothing from its held-out author. The comparison is therefore tilted against the re-trained model in every fold, not only stt.
- "beach" occurs only in 5 older stt lines (stt_008, stt_022, stt_038, stt_074, sttv2_035) and "repel" only in stt_027; neither is in r6, cs or the seeds.
- The three stt regressions are exactly those spellings: sttv3_014 and sttv3_019 (shipped BREACH 0.87 / 0.99; fold model split, top 0.38 / 0.40) and sttv3_038. The other "repel" line, sttv3_025, stays RAPPEL 0.99.

**Three precision points the reviewer did not make:**
- The Fisher p=0.033 (10/0 vs 5/4) is post hoc: r6 was picked as the extreme of three authors, so it is roughly 0.10 after correction. Heterogeneity is suggestive, not established; the non-r6 score CI [-3,+14] still contains the pooled +11.
- HANDOFF line 121 does not name its unit. +10.7 / +11.3 are score differences. The hit-rate differences are +6.7 [+1.3,+12.7] and +7.3 [+2.0,+13.3].
- The authors are AI personas from one model (COOP-BOT.md:542), which further limits any author-level generalisation.

*Recommended action.* **1. HANDOFF.md section 4, line 121 (and the future v3 section of COOP-BOT.md).** Name the unit and the scope of the CI. Suggested wording:

"Разница счёта (попадание − 2 × чужое семейство): +10.7 [+3.3, +18.7] для top и +11.3 [+4.0, +19.3] для family; по попаданию +6.7 / +7.3. Интервал — по строкам этих трёх авторов, не по авторам."

**2. Add a per-author table directly under it.**

| автор | попадание: боевой -> дообученный (top / family) | чужое семейство | разница счёта |
|---|---|---|---|
| r6 | 78 -> 98 / 98 | 2% -> 0% | +24 [+12,+38] |
| cs | 92 -> 90 / 92 | 6% -> 2% | +6 [-8,+22] / +8 [-4,+24] |
| stt | 80 -> 82 / 82 | 2% -> 2% | +2 [-8,+12] |

Followed by: "Без r6 (100 строк): попадание +0 / +1 [-6,+7], счёт +4 / +5 [-4,+14]. Прирост попадания почти целиком на авторе r6 (10 из 10-11 строк)."

**3. Soften line 123.** Replace "Вывод: дообучение нужно" with a statement that the gain is shown on r6-style lines, that on cs and stt there is no measurable hit-rate gain, and that no author's score falls.

**4. Add the leave-one-author-out caveat.** The shipped model trained on the older lines of all three authors; each fold model never saw its held-out author. On stt the three regressions (sttv3_014, _019, _038) are the ASR spellings "beach" and "repel", which occur only in stt's older lines. The stt figure is therefore pessimistic for the final model, but a claim about speech-to-text input needs new stt-style blind lines scored against the final v3 model. The current 150 lines will be training data for that model.

**5. scripts/coop/eval_v3.py, retrained().** Print per-author rows (near, wrong family, score, paired diff vs shipped) for both gates, and the same in shipped(). eval_v3.py is hash-logged (frozen.txt:121), so record the new hash with a note that the per-author rows are a post-hoc reporting addition.

**6. Do not answer this by adding "beach" / "repel" seeds or re-tuning on these lines.** That would edit frozen material after the blind lines were seen.

**Verifier (refute): confirmed, major; reproduced: yes; touches frozen: no**

The finding stands. Every number in it reproduces with the project's own scoring code, it is not documented anywhere, and it is not a threshold artifact. Refutation failed; four refinements narrow it.

What holds (re-trained leave-one-author-out ens3 vs shipped v2, 150 v3 lines):
- Hit rate, the metric of the HANDOFF table (83.3 -> 90.0 / 90.7): r6 39 -> 49 of 50, cs 46 -> 46 (family) or 45 (top), stt 40 -> 41. r6 supplies 10 of the net +11 lines (family) and 10 of +10 (top).
- Without r6 (n=100): near +1.0 [-5, +7] family and +0.0 [-6, +6] top; score +5.0 [-3, +14] family and +4.0 [-4, +14] top.
- The heterogeneity is real, not chance: permuting author labels gives p = 0.008 (family) and 0.004 (top) for near, and about 0.05 for score.
- The published CI resamples lines within these three authors (eval_v3.py bootstrap), while the project's unit of generalisation is the author.
- stt after re-training: 82% near, 4 lines better and 3 worse, 78% for intent-near and target-exact together.

Refinements:
1. "Whole gain" is exact for hit rate only. The published difference is in score (near - 2 x wrong family), where r6 gives 12 of 17 units (family) or 12 of 16 (top), cs 4 or 3, stt 1. The wrong-family drop from 5 to 2 lines is mostly cs (3 -> 1), with r6 1 -> 0 and stt 1 -> 1.
2. The comparison is biased against the re-trained model for all three authors, not only stt. The shipped model trained on every author's 161 older lines; each fold model saw no line of its held-out author. The three stt regressions are 'beach' and 'repel' lines, spellings that occur only in stt's own lines, which the final model will train on.
3. The conclusion "дообучение нужно" survives. No author loses on score (+24 / +8 / +2 family, +24 / +6 / +2 top), r6 alone is +24 [+12, +38], and the older lines are flat. What does not survive is reading +10.7 / +11.3 as the expected gain for a new style: on stt, the author closest to the real input, the gain is +2 [-8, +12].
4. The t-interval over three authors is uninformative by construction; the permutation test is the proper evidence.

The per-author counts can be derived from the miss lists in eval_v3.log, but no summary row or HANDOFF sentence states them. COOP-BOT.md's v1 section did publish a per-author table, and eval_v3.py prints per-author rows for the matcher but not for the classifier.

*Recommended action.* No change to rules, vocabulary, spec, seeds or labels.

1. In /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md section 4, and in the v3 sections still to be written in COOP-BOT.md and DEBERTA-BOT.md, add per-author rows under the classifier table (near / wrong family, n=50 each, family gate):
   - r6: shipped 78 / 2, re-trained 98 / 0, score +24 [+12, +38]
   - cs: shipped 92 / 6, re-trained 92 / 2, score +8 [-4, +24]
   - stt: shipped 80 / 2, re-trained 82 / 2, score +2 [-8, +12]

2. Add this text next to the difference line: "The difference is in score (near - 2 x wrong family) and the interval is a bootstrap over the lines of these three authors, not over authors. Ten of the eleven extra hits are author r6; without r6 the hit rate changes by +1.0 [-5, +7] and the score by +5.0 [-3, +14]. The drop in wrong-family actions (5 -> 2 lines) is mostly cs (3 -> 1). On stt, the style closest to real input, no gain is shown (80 -> 82). The comparison understates the re-trained model: the shipped model trained on the older lines of all three authors, while each fold model saw no line of its held-out author; the three stt lines that got worse are 'beach' / 'repel', spellings found only in stt's own lines. The conclusion that re-training is needed stands: no author's score fell and the older lines are unchanged."

3. In /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/eval_v3.py, retrained(): print per-author rows for the shipped picks and for ens[g] on the v3 lines, as matcher() already does per author, and label the bootstrap lines "95% CI over lines". This is a reporting-only edit that changes no number; record the new hash in frozen.txt as an edit made after the results.

4. A claim about speech-to-text input needs new stt-style blind lines scored against the final v3 model.

### numbers #2: seed_commands_v3.json still labels 'get on the roof' and 'go roof' as RAPPEL, against spec_v3; the 'get up on the roof -> RAPPEL' error is not fixed in the cross-validation

Reviewer: major, training. Affects: HANDOFF.md line 111 ('Её должно починить дообучение'); the final model models/coop-deberta-v3-ens3-v3 being trained from seed_commands_v3.json; wrong-family rate on roof orders

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

Every checkable part of the finding holds; the causal claim is strongly supported but not proven, and one detail is wrong.

1. Seeds contradict spec_v3. seed_commands_v3.json RAPPEL still holds 'get on the roof' (seed_RAPPEL_3) and 'go roof' (seed_RAPPEL_7). spec_v3 RAPPEL says "Just going to a named place, the roof included, is MOVE_TO". make_spec_v3.py adds MOVE_TO seeds 'go to the roof', 'head to the roof', 'go up to the roof' and removes nothing. The file on disk is exactly seed_commands_v21.json plus location_seeds(). This is the only intent definition v3 changed, and the seeds were not brought in line with it.

2. The roof error is not fixed in the cross-validation. csv3_037 'get up on the roof, I want somebody up top' (truth MOVE_TO, 3/3 readers) is answered RAPPEL by all three fold-cs members and by ens3 at both gates. It is one of exactly two wrong-family v3 lines at either gate (the other is sttv3_032 OPEN -> VAULT_WINDOW). Shipped v2 gave RAPPEL 0.99, so re-training only lowered the confidence. csv3_031 went RAPPEL -> NONE and is still not near.

3. Cause: indirect evidence only. In the 6 runs where both RAPPEL roof seeds were out of training, 'get on the roof' is read MOVE_TO 6/6, including the two fold-cs runs where no MOVE_TO near-copy blind line was in training. The single RAPPEL reading is the run where 'go roof'=RAPPEL stayed in training and csv3_037 was absent. No stored prediction shows csv3_037 from a model trained without the two seeds, so proof would need an ablation re-train, which I did not run.

4. Correction to the reviewer: the two seeds were not written under spec_v2. They are already in the v1 seed_commands.json; spec v1 has the same RAPPEL wording ('go up to the roof').

5. The final-model statement is a prediction, not a measurement. train_v2.py final() does train on V.seed_items() from seed_commands_v3.json, and the final ensemble now training on this Mac uses that file. Its training set will hold 'get on the roof'=RAPPEL next to the near-duplicate csv3_037=MOVE_TO. That it answers RAPPEL on the verbatim seed is very likely but unverified; the model does not exist yet.

Numeric impact on the headline is small: 1 of 150 lines (0.67 points of near, half of the 1.3% wrong family). No reported number is miscomputed. Major because HANDOFF line 111 is contradicted by the project's own log, and because the final model is being trained with two labels that contradict the HANDOFF section 7 decision that going to the roof without rope words is MOVE_TO.

*Recommended action.* Two separate actions; only the second touches frozen material.

A. Write-up, no frozen material. In /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md line 111, replace 'Её должно починить дообучение.' with a statement of what the cross-validation shows, for example:
'Дообучение её не починило: в кросс-валидации v3 (eval_v3.log, раздел C) «get up on the roof, I want somebody up top» по-прежнему → RAPPEL на обоих гейтах (ens3 0.70; у боевой v2 было 0.99). Это одна из двух оставшихся ошибок «чужое семейство». Вероятная причина: seed-команды «get on the roof» и «go roof» в seed_commands_v3.json остались с меткой RAPPEL вопреки spec_v3.'
Carry the same sentence into the future v3 section of COOP-BOT.md and DEBERTA-BOT.md.

B. Training data, touches frozen. In /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/make_spec_v3.py main(), move 'get on the roof' and 'go roof' from seeds['RAPPEL'] to seeds['MOVE_TO'], or drop them.
- Follow the project's own v2 -> v21 precedent: write a new seed file under a new COOP_TAG (for example seed_commands_v31.json) so the v3 study files stay as they are.
- Record the change in scripts/coop/frozen.txt as a seed edit made after the v3 blind lines were seen.
- Re-run the leave-one-author-out cross-validation and the final ens3 training with it.
- Mark the resulting numbers 'after tuning'. csv3_037 and csv3_031 can no longer serve as a blind check of roof orders; an honest roof number needs new blind lines.
- The final ensemble currently training (scripts/coop/train_v3_final_ens3.log, started 23:40 on mps) uses the unfixed seed file and would have to be re-trained if B is accepted.

If the owner declines B, say in HANDOFF section 7 that the verbatim commands 'get on the roof' and 'go roof' are trained as RAPPEL, which contradicts the 'Go to the roof ... MOVE_TO' decision listed there.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: yes**

I could not refute it: every fact in the finding reproduces. Only the causal claim is overstated, and no number in HANDOFF section 4 changes.

**What stands**
- `seed_commands_v3.json` keeps two RAPPEL seeds with no rope word, "get on the roof" (RAPPEL[3]) and "go roof" (RAPPEL[7]). They are inherited unchanged from v1/v2/v21, written when the spec listed "go up to the roof" under RAPPEL.
- spec_v3 and HANDOFF section 7 say going to the roof without rope words is MOVE_TO, and `make_spec_v3.py` adds MOVE_TO seeds "go to the roof", "head to the roof", "go up to the roof". These two are the only roof seeds that contradict the spec.
- This is an oversight, not a documented decision. The `make_spec_v3.py` docstring says "every 'roof' line so far was a rope line", which holds for the old blind lines but not for these two seeds. Nothing in frozen.txt, HANDOFF, COOP-BOT.md or DEBERTA-BOT.md mentions them.
- In the leave-one-author-out run, csv3_037 "get up on the roof, I want somebody up top" (three readers: MOVE_TO) is still answered RAPPEL at both gates. It is one of the two wrong-family actions on the 150 lines; the other is sttv3_032.
- HANDOFF line 111 ("Её должно починить дообучение") is therefore not supported by the cross-validation, and the cross-validation block below it never returns to the point.
- The final v3 ensemble is training right now from this seed file. The shipped v2 bot answers both seed phrases RAPPEL at 0.994, so the v3 bot will almost certainly do the same.

**What is overstated**
- "The cause is the two seeds" is plausible but not shown. All nine stored predictions for csv3_037 come from models that had both seeds in training: six say RAPPEL, three do not (the leave-r6-out out-of-fold models give MOVE_TO 0.92, MOVE_TO 0.69, ENTRY 0.92).
- Other rope lines that mention the roof (r6_000, r6_005, r6_078, cs_038, and the seeds "drop down from the roof", "rappel from the roof") also tie roof to RAPPEL. Relabelling the two seeds is not shown to fix csv3_037.
- Re-training did fix most roof errors of the shipped bot: of its five, three are now MOVE_TO (r6v3_002, sttv3_028, sttv3_041) and csv3_031 went from RAPPEL to NONE.

**Why minor rather than major**
- The reported 90.0 / 90.7 near and 1.3% wrong family already include this error, so no claim under review is wrong.
- Scope is 2 of 383 seeds and one, at most two, of 150 blind lines.
- It is still time-sensitive, because fixing the seeds means re-training the final ensemble that is in flight.

*Recommended action.* **1. Write-up (does not touch frozen material)**
- In `/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md` line 111, replace "Её должно починить дообучение." with what the cross-validation shows:
  - of the five roof lines the shipped bot got wrong, three are now MOVE_TO (r6v3_002, sttv3_028, sttv3_041);
  - csv3_031 is NONE;
  - csv3_037 "get up on the roof, I want somebody up top" is still RAPPEL at both gates, one of the two remaining wrong-family actions (`eval_v3.log`, section C).
- Add a known-issue line: `seed_commands_v3.json` still has "get on the roof" and "go roof" under RAPPEL, against spec_v3 and section 7, and a model trained from it answers RAPPEL to those two phrases.

**2. Seeds (touches frozen material; owner's decision before the final model is accepted, since it is training now)**
- Option A: ship the frozen recipe as evaluated and keep the known-issue line.
- Option B: move the two seeds to MOVE_TO or drop them.
  - Change both `scripts/coop/seed_commands_v3.json` and `make_spec_v3.py`, so the generator reproduces the file.
  - Record it in frozen.txt as a seed change made after the blind lines were seen.
  - Re-train the final ens3.
  - Mark any re-run cross-validation number as "после подгонки"; the current 90.0 / 90.7 and 1.3% stay as the pre-change figures.
- Either way, do not write that the seed change fixes csv3_037 unless a re-run shows it; the stored predictions do not isolate the seeds as the cause.

### numbers #3: HANDOFF quotes differences of the composite score (near - 2 x wrong family) as if they were hit-rate differences

Reviewer: major, numbers. Affects: HANDOFF.md section 4: lines 108, 121, 122; frozen.txt line 158; any v3 write-up that copies these numbers

**Verifier (reproduce): confirmed, minor; reproduced: yes; touches frozen: no**

All three unlabelled differences in HANDOFF.md section 4 are differences of the composite score = near - 2 x wrong family, not of the hit rate shown in the table directly above them. The numbers themselves are correct and reproduce exactly; eval_v3.log labels them "score" (lines 82-85, and "strip - raw, score"), and eval_v3.py:82 defines the per-line value as int(good) - 2*int(not good and pick != NONE). HANDOFF.md never defines or names that quantity (no "score"/"счёт" anywhere in the file), whereas the v2 write-up does (COOP-BOT.md:168 and :440).

Re-derived by component on the 150 v3 lines (re-trained minus shipped raw):
- top gate: score +10.7 [+3.3,+18.7]; hit rate 125 -> 135 lines = +6.7 [+1.3,+12.7] (15 lines gained, 5 lost, sign test p=0.041; with 20000 resamples the lower bound is +0.7, i.e. one line); wrong family 5 -> 2 lines = -2.0 [-4.7,+0.0] (3 better, 0 worse, p=0.25).
- family gate: score +11.3 [+4.0,+19.3]; hit rate 125 -> 136 = +7.3 [+2.0,+13.3] with the log's own algorithm (15/4, p=0.019); wrong family 5 -> 2, same as top.
So 4.0 of the quoted 10.7/11.3 points is the 3-line wrong-family change counted twice, and that change is not established on its own. The reviewer's family upper bound of +12.7 is bootstrap grid noise (one line = 0.67 pt); with random.Random(0), 4000 reps it is +13.3.

HANDOFF line 108 "хуже на 3.3 пункта": score -3.3 [-8.0,+0.0]; hit rate is 2.0 lower (125 -> 122), wrong family 5 -> 6; only 3 answers differ (p=0.25), and the interval touches zero.

HANDOFF line 122 "0.0 / -0.2 [-4,+4]" on the 483 older lines is also score. By component, which the reviewer did not give: top gate hit rate 441 -> 433 = -1.7 [-3.7,+0.4] offset by wrong family 12 -> 8; family gate hit rate 437 -> 440 = +0.6 [-1.4,+2.7], wrong family 9 -> 11. So "0.0" at the top gate is a 1.7-point hit-rate drop cancelled by the doubled wrong-family term; no component interval excludes zero, so "old orders not hurt" stands, but not as "nothing changed".

frozen.txt line 158 repeats +10.7/+11.3 and +0.0/-0.2 without the word score (it does cite eval_v3.log section C).

Why minor rather than major: no number is wrong, the source log labels the quantity, and the conclusion "re-training is needed" survives on hit rate alone at both gates (intervals exclude zero), only with a thinner margin than the text suggests. The defect is that a reader takes +10.7 as a hit-rate gain, which contradicts the table (90.0 - 83.3 = 6.7) and overstates the gain by 4 points. The unitless form has already propagated to frozen.txt and to the claim summary this review was given.

*Recommended action.* HANDOFF.md only; no rule, vocabulary, spec, seed or label changes.

1. Before line 121 add a definition: "Счёт = попадание − 2 × чужое семейство (критерий владельца, как в COOP-BOT.md). Разницы ниже — парный бутстрэп по строкам."
2. Replace line 121 with: "Разница на строках с местами, счёт: +10.7 [+3.3, +18.7] для top и +11.3 [+4.0, +19.3] для family. Из них попадание: +6.7 [+1.3, +12.7] (125 → 135 строк) и +7.3 [+2.0, +13.3] (125 → 136); чужое семейство: 5 → 2 строки из 150 (−2.0 [−4.7, 0.0], отдельно не значимо)."
3. Replace line 122 with: "На 483 старых строках разница счёта 0.0 / −0.2 [−4, +4]. Попадание: −1.7 [−3.7, +0.4] для top (441 → 433 при чужом семействе 12 → 8) и +0.6 [−1.4, +2.7] для family (437 → 440, чужое семейство 9 → 11). Значимого ухудшения нет."
4. Line 108: "хуже на 3.3 пункта счёта [−8.0, 0.0]: попадание ниже на 2.0 (125 → 122), чужое семейство 5 → 6; различаются 3 ответа." The conclusion on line 110 should then be worded as "вырезание не помогает", since three lines do not show that it hurts.
5. frozen.txt line 158: do not rewrite it, it is an append-only log. Optionally append a dated comment saying the +10.7 / +11.3 and +0.0 / −0.2 on that line are score = near − 2 × wrong family, per eval_v3.log section C.
6. Optional, not required for the fix: have eval_v3.py print the near and wrong-family differences next to the score difference, so a future write-up cannot drop the unit. That changes only printing, not any prediction.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: no**

The finding stands on the facts; I could not refute it. I rate it minor rather than major, and one of the reviewer's replacement numbers needs a small correction.

**What is wrong.** HANDOFF.md section 4 quotes three differences without naming the quantity, directly beside tables whose columns are hit rate and wrong family:
- line 108: "хуже на 3.3 пункта"
- line 121: "+10.7 [+3.3, +18.7] для top и +11.3 [+4.0, +19.3] для family"
- line 122: "0.0 / −0.2 [−4, +4]"

All three are differences of the composite score = near − 2 × wrong family. The numbers themselves are correct and reproduce exactly. HANDOFF.md never defines the score: there is no occurrence of score, счёт or критерий in the file. A reader of HANDOFF alone will take +10.7 as the hit-rate gain, while the table above it gives 83.3 → 90.0, which is 6.7.

**Decomposition on the 150 v3 lines, re-trained ens3 against shipped (raw input).**

| quantity | top gate | family gate |
|---|---|---|
| score | +10.7 [+3.3, +18.7] | +11.3 [+4.0, +19.3] |
| hit rate (near) | +6.7 [+1.3, +12.7], 125 → 135 lines | +7.3 [+2.0, +13.3], 125 → 136 lines |
| wrong family | −2.0 [−4.7, +0.0], 5 → 2 lines | −2.0 [−4.7, +0.0], 5 → 2 lines |

- The remaining 4.0 score points are the wrong-family change counted twice.
- The wrong-family change is 3 lines fixed, 0 new (sign test p = 0.25), so it is not established on its own.
- **Correction to the reviewer:** the family-gate hit-rate interval is [+2.0, +13.3], not [+2.0, +12.7]. It is stable at 200,000 resamples and with the log's own algorithm.

**The other two unlabelled figures.**
- Strip − raw: score −3.3 [−8.0, +0.0]; hit rate −2.0 (125 → 122 lines); wrong family 5 → 6.
- 483 older lines, top gate: score +0.0 [−3.9, +4.1] is hit rate −1.7 [−3.7, +0.4] (441 → 433) offset by wrong family 12 → 8.
- 483 older lines, family gate: score −0.2 [−4.3, +3.7] is hit rate +0.6 (437 → 440) with wrong family 9 → 11.

**Why minor, not major.**
- The score is the project's declared criterion: COOP-BOT.md:168 ("Score is the owner's criterion, near − 2 × wrong family") and DEBERTA-BOT.md:136.
- The log that HANDOFF cites for these results labels every one of these lines "score".
- No conclusion changes: the hit-rate gain alone excludes zero at both gates (sign test p = 0.041 top, 0.019 family), so "дообучение нужно" holds.
- It is still a real defect, because the v2 write-up always named the quantity (COOP-BOT.md:440, 456, 469), and HANDOFF is the text the v3 section of COOP-BOT.md will be copied from.

**frozen.txt line 158** repeats the two figures without the word score, but points to "eval_v3.log section C", where the label is. HANDOFF.md is not hashed in frozen.txt, and the fix is wording only, so nothing frozen is touched.

*Recommended action.* Edit wording only in /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md section 4. No rule, vocabulary, spec, seed or label changes.

1. **Line 108**, replace the cell "хуже на 3.3 пункта" with: "счёт (попадание − 2 × чужое семейство) ниже на 3.3 [−8.0, +0.0]; попадание 81.3% (−2.0), чужое семейство 4.0%; ответ меняется на 3 строках из 150".

2. **Line 121**, replace with: "Разница по счёту (попадание − 2 × чужое семейство, парный бутстрэп) на строках с местами: +10.7 [+3.3, +18.7] для top и +11.3 [+4.0, +19.3] для family. Из них попадание: +6.7 [+1.3, +12.7] и +7.3 [+2.0, +13.3]; чужое семейство 5 → 2 строки из 150 (3 исправлены, новых нет; отдельно эта разница не значима)."

3. **Line 122**, replace with: "На 483 старых строках разница по счёту +0.0 [−3.9, +4.1] (top) / −0.2 [−4.3, +3.7] (family): попадание 441 → 433 и 437 → 440 строк, чужое семейство 12 → 8 и 9 → 11; ухудшение не обнаружено."

4. Use the same labelled form when the v3 section of COOP-BOT.md and DEBERTA-BOT.md is written (HANDOFF section 5, step 5).

5. Do not rewrite /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/frozen.txt line 158, since it is a historical log entry. If wanted, append a new dated comment line saying the figures in that entry are differences of score = near − 2 × wrong family.

### numbers #4: Matcher: the held-out 94% is 90 -> 94 on stt (two lines), and both gained lines repeat idioms of the tuning authors; one fix is a literal phrase from an r6 blind line

Reviewer: major, matcher. Affects: HANDOFF.md section 4 rows 'сопоставитель, правила v1 / v2' (88.0 / 94 / 96.7); results_v3.json; eval_v3.py docstring

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

All five sub-claims hold. No number is wrong; what changes is what the 94% may be read as.

1. **Like for like.** The HANDOFF table sets 88.0% (rules v1, all 150) beside 94% (rules v2, stt only). On stt alone the matcher went 45/50 to 47/50 (90.0 to 94.0); on the tuned authors r6+cs it went 87/100 to 98/100. Wilson 95%: 132/150 [81.8, 92.3], 45/50 [78.6, 95.7], 47/50 [83.8, 97.9]. frozen.txt line 139 already records "94.0%, was 90.0%", and the HANDOFF row label says the rules were edited on r6 and cs. HANDOFF itself never shows the 90.0.

2. **Held out by author, not by phrase.** The two stt lines gained are sttv3_030 and sttv3_034, and each is fixed by exactly one vocabulary entry that also matches a tuned line:
   - ignore phrase "through the roof" is literal text of r6v3_039 and is the only thing fixing sttv3_030.
   - "my" in lone_not_after fixes csv3_035 ("my main got vac banned") and is the only thing fixing sttv3_034 ("not even my main").
   - Removing both entries puts stt back at 45/50. The reviewer's "Thermite main" (r6v3_045) is the same sense of "main" but not the trigger; the shared bigram is "my main".
   - No other v2 change (1d, 5b, 5c, report verbs, floor phrases) moves any stt line: 0 further gains, 0 regressions. The three remaining stt misses (023, 036, 045) have identical outputs in both logs.
   - So the held-out evidence that rules v2 generalise is zero lines; the only clean held-out result is "no regression on stt".
   - The fixes are phrase-literal. Paraphrases still return a target: "my ping just hit the roof" gives roof, "i main thermite" gives door/main, "we should table it" gives table.

3. **Lines that name no place.** Only 6 of the 150 lines have an empty truth target (all kind other_sense, 2 per author): 0/6 with v1, 4/6 with v2, and r6's own two are still wrong. On the 483 older lines the matcher returns a target on 119 (105 bare object, 9 zone only, 5 object+qualifier). None can be scored: the v1/v2 label files have no target field. Visible false targets there include "red container" and "red car", both read as stairs/red (flagged unsure).

4. **Missing marks.** results_v3.json holds only exact 0.9667 / per_author / in_list, with no rules version or "after tuning" mark. Section A of eval_v3.log has none either. eval_v3.py line 4 still says "rules frozen before the lines existed"; its hash equals the pre-test frozen hash, so it was never updated.

5. **Rules v1 are not on this machine.** There is one locations.json / locations.py, with the v2 hashes, in the tree, in the pristine copy and in coop-bot-code.tar.gz; the exported intent_config.json is version 2. So 88.0% cannot be recomputed from the frozen v1 files.
   - It is corroborated beyond the reviewer's internal-consistency check: a reconstruction of v1 from v2 reproduces section A of eval_v3_rules_v1.log byte for byte (every row, the 18 mismatches with their outputs, 7 flags, 120 older lines).
   - That reconstruction only matches if "awp" and "stack" are removed from role_them and "my" and "a" from lone_not_after. These are literal words of csv3_040, r6v3_029 and csv3_035. This is an inference from the reconstruction, not a diff of the real v1 files.
   - Neither the locations.json _note nor the locations.py docstring lists these word-list additions among the v2 changes.

Severity is major on the lower edge: the project's tuning rule was followed to the letter and the fix is write-up only, but "94% on the held-out author" would be read as generalisation evidence it does not carry.

*Recommended action.* Write-up only. Do not change rules, vocabulary, spec, seeds or labels.

1. **/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md section 4, lines 105-106** (and the future "v3" section of COOP-BOT.md): replace the two matcher rows with
   - "matcher, rules v1 (frozen before the lines existed): exact target 88.0% (132/150, 95% interval [82, 92]); by author r6 86 / cs 88 / stt 90"
   - "matcher, rules v2 (AFTER TUNING on the r6 and cs mismatches): 98/100 on the tuned authors; stt 94.0% (47/50, [84, 98]), was 90.0% with v1. Both gained stt lines share a phrase with a tuned line ('through the roof', 'my main'); no other stt line changed, none regressed. 96.7% on all 150 is a number after tuning."
   - Add below the table: "For new phrasing expect about 88-90% until new blind lines are written. Lines that name no place: only 6 of 150 (0/6 with v1, 4/6 with v2); the false-target rate on chatter is not measured. On the 483 older lines the matcher returns a target on 119, and those lines have no target labels."

2. **HANDOFF.md section 6, line 175:** after "Автор stt — отложенная проверка" add that stt is held out by author, not by phrase: two v2 entries match stt lines through wording shared with r6 and cs.

3. **Archive the v1 rules.** Bring the files with sha256 9999cc9f… (locations.json) and 111d1a76… (locations.py) from the work machine, for example as scripts/coop/rules_v1/, so 88.0% can be recomputed.

4. **Complete the v2 change list** in frozen.txt or the write-up, not by editing locations.json: once the v1 files are available, diff them and record the word-list additions. The reconstruction points to "awp" and "stack" in role_them and "my" and "a" in lone_not_after.

5. **/Users/t.losiev/Documents/models_training/project_synth/scripts/coop/eval_v3.py line 4:** change "rules frozen before the lines existed" to "rules v1 frozen before the lines existed (eval_v3_rules_v1.log); later runs use rules v2, tuned on r6 and cs". Optionally write LOC.VOCAB["version"] and an after-tuning flag into results_v3.json. Log the new eval_v3.py hash in frozen.txt as a comment/metadata-only change.

6. Do not extend the ignore list or word lists to cover the remaining misses or the paraphrases above without new blind lines.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every factual sub-claim holds, but nothing in HANDOFF section 4 is numerically wrong, the protocol was followed and recorded, and two of the reviewer's conclusions are overstated. This is a presentation and caveat problem, not a broken number.

1. **Like-for-like (true, partly documented).** stt went 45/50 to 47/50 (90.0 to 94.0); r6+cs went 87/100 to 98/100. The stt baseline of 90.0% is recorded in frozen.txt line 139 ("94.0%, was 90.0%") and in eval_v3_rules_v1.log, but HANDOFF.md lines 105-106 put 88.0% (v1, all 150) next to 94% (v2, stt only) without it. The v2 row is labelled as edited on r6 and cs, so the tuning mark the project rules require is present there.

2. **Idiom overlap (true, not a protocol breach).** Both stt gains come from v2 entries motivated by tuning-author lines with the same idiom:
   - sttv3_030 is right only because of the ignore phrase "through the roof" (from r6v3_039). That entry gains no exact match on r6 itself, since r6v3_039 still fails via "west coast".
   - sttv3_034 is right only because "my" is in lone_not_after (from csv3_035 "my main got vac banned").
   - Nothing in v2 targets the stt-only misses (023, 036, 045 are unchanged; "second story" and "rough" are still absent), so stt was held out as HANDOFF section 6 promises: by author, not by phrase.
   - The +2 lines are within noise: Wilson 45/50 [78.6, 95.7] against 47/50 [83.8, 97.9]; 2 gained, 0 lost.
   - The reviewer's "quote 88% as the honest figure for new phrasing" is not supported. 88.0% is a different quantity (rules v1, all three authors). The held-out figure for v2 remains 94.0% (47/50) and needs its baseline, its interval and the idiom caveat.

3. **No-place precision (true, benign where it can be eyeballed).** Only 6 lines have a truth with no place (all kind other_sense): 0/6 with v1, 4/6 with v2. The 483 older lines carry no target labels. Of the 119 targets the matcher returns there, 104 come from an object word present in the line, 13 are zone or "other one" targets, and 2 are clear false positives ("red container", "red car"), both flagged "unsure". That is my reading of the lines, not labels.

4. **Marks (true, minor).** results_v3.json and section A of eval_v3.log carry no tuning mark, and the eval_v3.py docstring (line 4) still says "rules frozen before the lines existed". eval_v3.py still has its pre-lines hash 521657ba, so it was never edited. The mark exists in HANDOFF, frozen.txt, the locations.py docstring and the locations.json _note.

5. **Rules v1 files (true, but "cannot be recomputed" is overstated).** The v1 files (9999cc9f, 111d1a76) are absent, so 88.0% cannot be verified against the frozen hashes. Reverting the v2 changes in a scratch copy reproduces every figure in eval_v3_rules_v1.log, including all 18 mismatches with their outputs, roles and flags.

Two v2 word-list additions that the reconstruction needs are not named in the locations.json _note or the locations.py docstring: "my" (and "your" or "a") in lone_not_after, and "awp" and "stack" in role_them. The first is one of the two changes behind the stt gain.

*Recommended action.* Write-up only. Do not change locations.json or locations.py; adding "west coast", "second story" or "rough" now would be fitting to seen blind lines.

1. **/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md lines 105-106**, replace the two matcher rows with:
   - "сопоставитель, правила v1 (до просмотра строк) | точная цель 88.0% (132/150; r6 86.0, cs 88.0, stt 90.0)"
   - "сопоставитель, правила v2 (после подгонки по авторам r6 и cs) | отложенный автор stt: 94.0% (47/50, 95% ДИ 84–98), при v1 было 90.0% (45/50): +2 строки, обе на оборотах, которые есть и у авторов подгонки («through the roof», «my main»); r6+cs 98/100 и 96.7% на всех — цифры после подгонки, не оценка"

   Add one line under the table: "Строк, где в правде нет места, всего 6 (other_sense): 0/6 при v1, 4/6 при v2; на 483 старых строках цель не размечена (сопоставитель находит её в 119)."

   Carry the same wording into the future "v3" section of COOP-BOT.md. Do not replace 94% with 88%.

2. **/Users/t.losiev/Documents/models_training/project_synth/scripts/coop/eval_v3.py line 4**: change "rules frozen before the lines existed" to "rules v2: tuned on the r6 and cs authors after the first blind run; stt is the held-out author; the v1 run is eval_v3_rules_v1.log". Record the new hash in frozen.txt as a docstring-only edit. It is evaluation code, not rules, so the held-out number is unaffected.

3. **Rules v1 files**: bring locations.json (9999cc9f…) and locations.py (111d1a76…) from the work machine into the archive, for example as scripts/coop/rules_v1/. If they no longer exist, say so in frozen.txt and note that reverting the v2 changes reproduces eval_v3_rules_v1.log exactly.

4. **locations.json _note** (optional): it omits two v2 word-list additions, "my / your / a" in lone_not_after and "awp / stack" in role_them. Changing the _note changes the hashed vocabulary file, so it is simpler to record the omission in frozen.txt or HANDOFF.

### numbers #5: 'Older lines not harmed' is a null result with a +-4 point interval; by component the top gate loses 1.7 points of hit rate and two BREACH lines become OPEN

Reviewer: minor, evaluation. Affects: HANDOFF.md line 122 ('На 483 старых строках разница 0.0 / -0.2 [-4, +4], то есть старые приказы не пострадали')

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Every number in the finding reproduces from the stored probability files. HANDOFF.md line 122 ("На 483 старых строках разница 0.0 / −0.2 [−4, +4], то есть старые приказы не пострадали") reads a null result as proof of no harm. The interval is quoted beside it, so precision is not hidden; the over-reading is the "то есть ... не пострадали".

What holds:
- Same 483 lines on both sides (363 v1 + 120 v2; same ids, order, text and truth).
- Score difference 0.0 [-3.9, +4.1] (top) and -0.2 [-4.3, +3.7] (family), SE 2.05 points. A loss of about 4 points is not excluded, and the bootstrap covers line sampling only. Per-seed differences are +3.1 / -0.6 / +1.7 (top) and +1.4 / 0.0 / 0.0 (family), so no systematic loss.
- **Top gate:** near 441 -> 433 (-1.7 [-3.7, +0.4]; 17 lost, 9 gained) against wrong family 12 -> 8.
- **Family gate:** near 437 -> 440, wrong family 9 -> 11, acts on non-order 4/75 -> 5/75.
- **r6 at the top gate:** near 151 -> 143 (-5.0 [-9.3, -0.6]).

Three corrections to the finding:
1. **(b) and (c) are a threshold shift, not a weaker model.** The fold thresholds rose from 0.46 / 0.50 / 0.42 to 0.62 / 0.58 / 0.58. At the v21 thresholds the v3-study models score near 443, wrong family 12 (v21: 441 / 12), and r6 scores 150 / 4 (v21: 151 / 3). The final model fits its own threshold and gate on out-of-fold predictions over all 633 lines, so these fold thresholds do not carry over.
2. **(d) is the only model-level change, and it is stronger than stated.** On the two BREACH hatch lines all six v21 fold-seed members said BREACH (0.78-0.98). In the v3 study three of the six say OPEN at 0.98 or higher and a fourth is a 0.49 / 0.49 tie. The row "assault-family lines -> OPEN (n=15)" that COOP-BOT.md line 435 publishes as 0 becomes 6.7% (1/15) for ens3 at both gates.
3. **(e) is mostly not a confound.** The seed set (233 -> 383), the 100 v3 training lines per fold and the refitted thresholds are the treatment being measured (eval_v3.py line 12: "does adding places cost anything there"). Only the 21:37 speed-up edit (tokenize once, fused AdamW) is an extraneous difference, and frozen.txt records it as "recipe unchanged".

The suggested check on the final model is vacuous for the two hatch lines: `train_v2.py final` trains on all 633 lines, so both are in its training set. The 16 owner probes are never training lines, and in the v3 study they are already all correct in all three fold ensembles at both gates.

The project's own precedent supports the finding: COOP-BOT.md lines 459-477 report the v21 seed change as "it has a price", with the interval, the wrong-family counts and the new mistakes listed.

*Recommended action.* Write-up only; no change to rules, vocabulary, spec, seeds or labels.

1. **/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md line 122**: replace the sentence with:
   "На 483 старых строках разница в счёте (попадание − 2 × чужое семейство) 0.0 / −0.2 [−4, +4]: ухудшение не обнаружено, но потеря до ~4 пунктов не исключена. По частям: гейт top — попадание 441 → 433 строк (91.3 → 89.6), чужое семейство 12 → 8 (пороги по фолдам выросли с 0.46/0.50/0.42 до 0.62/0.58/0.58; на прежних порогах 443 / 12); гейт family — попадание 437 → 440, чужое семейство 9 → 11. Новая ошибка на обоих гейтах: две BREACH-строки про люк («get it open with the thermite», «open up the hatch ... with your explosive») уходят в OPEN."

2. **v3 section of COOP-BOT.md and DEBERTA-BOT.md (HANDOFF step 5)**: report the older-lines comparison the way COOP-BOT.md lines 459-477 report v21, with the interval, per-gate near and wrong-family counts, and the newly wrong lines. State that "assault-family lines -> OPEN (n=15)" goes from 0 to 1/15 in the v3 study. State that the comparison differs from v21 by the seed set, the v3 training lines, the refitted thresholds and the 21:37 training-code speed-up.

3. **Final-model check**: do not present a run of the final v3 model on r6v2_005 and cs_105 as evidence, because both are in its training set. The 16 PROBES are a legitimate non-blind regression check on the final model.

4. **Do not add BREACH or OPEN seeds to fix the hatch lines.** That would change the seed set after the v3 lines were seen, and it would be fitted to test lines. If the owner wants it anyway, it must be logged in frozen.txt and the v3 numbers marked "после подгонки".

### numbers #6: '3.3 points worse with names stripped' rests on three lines of one author; the direction is not established and 3.3 is the score, not the hit rate

Reviewer: minor, numbers. Affects: HANDOFF.md lines 108-110 ('хуже на 3.3 пункта', 'Вывод: модель читает сырую строку')

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Every number in the finding holds. HANDOFF.md line 108 ("то же, названия вырезаны перед классификатором | хуже на 3.3 пункта") overstates what was measured in three ways.

1. Wrong metric for the context. The -3.3 is the composite score (near - 2 x wrong family: 76.7 -> 73.3). The row above it reports hit rate, so a reader derives 80.0%. The actual hit rate is 81.3% (125 -> 122, -2.0 points), and wrong family goes 3.3% -> 4.0% (5 -> 6). HANDOFF never defines "score"; eval_v3.log does label it as score.

2. The effect rests on 3 of 150 answers, all from author stt. Strip rewrites 58 lines (r6 21, cs 16, stt 21) and changes the pick on sttv3_011 (NONE -> HOLD_ANGLE, a new wrong-family action), sttv3_014 (BREACH -> NONE) and sttv3_049 (MOVE_TO -> NONE). Authors r6 and cs score identically raw and strip. The exact sign test on 0 up / 3 down gives two-sided p = 0.25. The project's own interval is [-8.0, +0.0]: it touches zero, and it cannot exceed zero because no line improves. HANDOFF drops this interval while quoting intervals for the other differences.

3. The direction is not established. Two of the three flips are small confidence moves across the 0.58 threshold (0.512 -> 0.616 and 0.601 -> 0.521); only sttv3_014 is a large change (0.889 -> 0.489). On the same stored probabilities the sign reverses at higher thresholds: -3.3 at 0.55 to 0.60, -0.7 at 0.65, +2.0 at 0.70, +2.7 at 0.80. A threshold-free paired check on the 58 rewritten lines shows no shift: mean change in probability mass on the true family is -0.0003, bootstrap CI [-0.023, +0.020], 31 lines up and 27 down.

One further wording point the reviewer did not raise: "названия вырезаны" is loose. Strip removes only the side and colour qualifier words (north, west, east, south, red, blue, yellow, white, brown). The object words (door, window, stairs), zones and "main" stay, as the eval_v3.py docstring says ("attached qualifiers stripped").

Refutation attempts failed. The caveat is not documented anywhere: frozen.txt line 139 repeats "classifier input: raw beats strip", and COOP-BOT.md, DEBERTA-BOT.md and the C++ README have no v3 text. The stored numbers are real model outputs: re-running the three shipped members here matches the stored probabilities.

The design decision is unaffected. Stripping never helped a single line and raw is the simpler input, so "модель читает сырую строку" stands as a default. Only the stated effect size and direction are unsupported.

*Recommended action.* Documentation only; no rule, vocabulary, spec, seed or label change.

1. /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md line 108: replace the row with "то же, слова-уточнения (north / red / ...) вырезаны перед классификатором | изменились 3 ответа из 150, все в худшую сторону и все у автора stt: попадание 81.3% (-2.0), чужое семейство 4.0%, score -3.3 [-8.0, +0.0]; различие не значимо (критерий знаков p = 0.25)".

2. HANDOFF.md line 110: replace with "Вывод: пользы от вырезания не найдено, классификатор по-прежнему читает сырую строку."

3. Carry the same wording into the future "v3" section of COOP-BOT.md and into DEBERTA-BOT.md. State that the differences are in score (near - 2 x wrong family), since HANDOFF section 4 quotes score differences next to hit-rate columns without saying so.

4. Do not edit frozen.txt line 139 (the log is append-only). If a correction is wanted, append a dated comment that "raw beats strip" means 0 lines better / 3 worse, not significant.

5. Optional: have eval_v3.py shipped() also print the near difference and the count of lines up/down beside the score difference. That changes a hashed script, so record the new hash in frozen.txt; no number changes.

### numbers #7: v3 truth: the two r6 annotator files are byte-identical, the authors give no alternates, and all 150 lines are unanimous on intent and target

Reviewer: minor, data. Affects: HANDOFF.md line 98 ('по 2 аннотатора на автора'); the meaning of 'unanimous on 150' in eval_v3.log line 1 and of the matcher's 'readers agreed' row

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Every fact in the finding reproduces. Two of its inferences need tightening.

**What holds**
- `annot/v3/author_r6_ann1.json` and `author_r6_ann2.json` are byte-identical, on disk and inside `coop-bot-code.tar.gz`, and `frozen.txt` lines 134-135 log the same hash twice with no comment.
- Intent is unanimous on 150/150 v3 lines and the whole target on 150/150, against 476/483 for intent on the older lines.
- Authors list no alternates, so an alternate is accepted only when both annotators give it; 19 v3 lines have one (r6 7, cs 6, stt 6).
- `coop_v2._target_truth` (`coop_v2.py:76-85`) takes a per-field majority and turns a three-way split into None; this yields a target no reader gave on 0 v3 lines.

**Correction 1: "one reading counted twice" is not established**
- The two r6 files were written 11 s apart (21:00:21 and 21:00:32). The cs pair is 10 s apart and the stt pair 16 s, in varying order, which looks like one write per returning annotator rather than one output saved twice.
- There is a precedent: `annot/v2/author_cs_ann1.json` and `_ann2.json` agree on 40/40 records in every field while being serialised differently (4286 vs 3489 bytes), so they are separate outputs.
- The other v3 pairs are almost as close: cs agrees on 48/50 whole records, and stt on 48/50 once the `reference` field is set aside.
- The files cannot settle it either way; the workflow run `wf_04800970-338` is not on this machine.

**Correction 2: "effect on the headline numbers: none" is exact only if the second reading is real**
- If it is a copy, the 7 r6 alternates rest on one annotator. Exactly one scored line depends on them: `r6v3_003` (NONE, WAIT accepted), where the shipped bot and both re-trained gates pick WAIT.
- Dropping the r6 alternates gives shipped 82.7 near / 4.0 wrong family and re-trained 89.3 / 90.0 near with 2.0 wrong family.
- The differences stay at +10.7 [+3.3,+18.7] and +11.3 [+4.0,+19.3]; the out-of-fold thresholds and all picks are unchanged.
- The matcher numbers cannot move: author and both annotators agree on all four target fields on every r6 line.

**Not a v3 defect**
- Authors giving no alternates is the design since v1: no author file in v1, v2 or v3 has an `ok` field, and the scoring is documented as "accepted by two of three readers".
- `COOP-BOT.md` lines 57 and 501 already carry the caveat that authors and annotators are agents of one model family, for v1 and v2. `HANDOFF.md` section 4 does not repeat it for v3, and nothing mentions the identical r6 files.

**One addition (weak signal, not proof of leakage)**
- `reference` is the one field where readers visibly chose a convention for an order that names an object: "this" (r6 author, both r6 annotators, stt ann1) or "none" (cs author, both cs annotators, stt author, stt ann2).
- 5 of 6 annotators landed on their own author's side; that is about an 11% chance if each were an independent coin flip.
- `reference` is not scored in any v3 number.

*Recommended action.* Write-up and provenance only; do not replace or add any v3 label file as a fix.

1. **`HANDOFF.md` section 4, after line 98, and the future v3 section of `COOP-BOT.md`** — add:
   "Authors and annotators are agents of one model family, as in v1 and v2. On the v3 lines all three readers agree on intent and on the whole target on 150/150; this shows the labels are consistent under spec_v3, not that they were independently confirmed. The two r6 annotator files are byte-identical (same sha256 in frozen.txt). If that is one reading saved twice, one scored line (r6v3_003, NONE with WAIT accepted) rests on a single annotator: near would be 0.7 points lower and wrong family 0.7 higher for the shipped and the re-trained bot alike (82.7 / 4.0 and 89.3 / 90.0 / 2.0), with the differences unchanged."

2. **`scripts/coop/frozen.txt`** — append a dated comment (no hash change) saying that `annot/v3/author_r6_ann1.json` and `_ann2.json` carry the same hash, and whether run `wf_04800970-338` on the Windows machine shows two separate annotator outputs for r6. That check cannot be done on this Mac.

3. **Next blind round** — store each annotator's raw output with its agent or run id, so identical label files can be told apart from a duplicated write.

The reviewer's proposal of a fresh second reading for r6 would change labels after the lines and the results were seen. It would have to be logged as such, and it buys at most one line; that route does touch frozen material.

### numbers #8: Intent and target are scored separately; the joint rate and the cost of 'near' on v3 lines are not reported

Reviewer: note, evaluation. Affects: How the v3 result is summarised (HANDOFF section 4; the future 'v3' section of COOP-BOT.md)

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

Every number in the finding reproduces exactly, and no joint (intent AND target) rate appears in eval_v3.py, eval_v3.log, results_v3.json (matcher block only) or any of the documents. No reported number is wrong; this is a reporting gap for the v3 write-up that is still to be written (HANDOFF section 5, step 5).

Joint = intent near AND matcher target exact, 150 v3 lines, rules v2 (so after tuning):
- shipped v2 bot: 121/150 = 80.7% [73.6, 86.2]
- re-trained ens3, top gate: 131/150 = 87.3% [81.1, 91.7]
- re-trained ens3, family gate: 132/150 = 88.0% [81.8, 92.3]; per author r6 47/50, cs 46/50, stt 39/50

near / exact ok / pick equals majority: 83.3 / 82.0 / 80.0 (shipped), 90.0 / 89.3 / 88.7 (top), 90.7 / 90.0 / 89.3 (family). csv3_004 is the only re-trained line that is near without being accepted: truth ENTRY, pick VAULT_WINDOW, matcher target door / north.

Corrections and additions to the finding:
1. **"Exact ok" is already in the log.** eval_v3.log prints it next to near on every B and C row; only HANDOFF section 4 drops it. COOP-BOT.md:43 states the convention that `ok` is reported alongside near, so the edit needed for that half is in the write-up, not in eval_v3.py.
2. **The untuned joint is about 9 points lower.** With rules v1 (frozen before the blind lines; mismatch ids taken from eval_v3_rules_v1.log) the joint is 110/150 = 73.3% shipped, 118/150 = 78.7% top, 119/150 = 79.3% [72.2, 85.0] family. On the held-out author stt with rules v2 it is 39/50 = 78.0% [64.8, 87.2].
3. **Most of the near-to-joint drop is on lines where the bot does nothing.** Of the 4 lines lost (136 to 132), three have truth NONE and pick NONE (r6v3_039, r6v3_045, sttv3_036). On the 126 order lines, family is 112 near and 111 joint. The only order executed at a wrong target is sttv3_045 (ENTRY, zone floor_2 missed).
4. **Intent and target errors look independent.** The product of the two marginals is 87.6% against the measured 88.0%, so the separate numbers do not hide a correlation.
5. **The re-training gain survives in the joint measure.** Paired bootstrap on the 0/1 joint: +7.3 [+2.0, +13.3] family and +6.7 [+1.3, +12.7] top against shipped.
6. **"All three seeds" is slightly off for csv3_004.** The argmax is VAULT_WINDOW on all three seeds, but seed 2 under the top gate abstains (0.799 against a fold threshold of 0.82). The ensemble gives VAULT_WINDOW 0.897.
7. **Nothing in the bot catches the incoherent pair.** coop_bot.py decide() (lines 152-186) has no intent/object compatibility check, so "on three ..." queues VAULT_WINDOW with place door / north.
8. **Two different quantities both read "88.0%".** The family joint (132/150) and the rules-v1 matcher exact rate (132/150) coincide; the write-up must label them.

Side observation outside this finding: annot/v3/author_r6_ann1.json and author_r6_ann2.json are byte-identical (same sha256, also visible in frozen.txt lines 134-135). I did not investigate what that does to the r6 truth.

*Recommended action.* No number in HANDOFF section 4 needs correcting. Two additions:

1. scripts/coop/eval_v3.py, in retrained() (and in shipped() for the shipped row): print one line per classifier, "intent near AND target exact", for all 150 lines, per author, and for the 126 lines whose truth is not NONE. Reuse the per-line `exact` flags from matcher(), which today returns only aggregates. Store the counts in results_v3.json. No change to "exact ok" is needed in the script: it is already printed. Because eval_v3.py is hash-logged in frozen.txt as written before any v3 line was read, record the edit there as a metric added after the results were seen.

2. Write-up (HANDOFF section 4 table and the future "v3" section of COOP-BOT.md): put "exact ok" next to near, as COOP-BOT.md:43 promises (82.0 shipped, 89.3 top, 90.0 family), and add a sentence along these lines:

"Приказ целиком (намерение near и точная цель): 88.0% (132/150) [81.8, 92.3] для дообученного ансамбля с гейтом family против 80.7% (121/150) у боевого v2, разница +7.3 [+2.0, +13.3]. Это после подгонки правил v2. На отложенном авторе stt — 78.0% (39/50) [64.8, 87.2], с правилами v1 — 79.3% (119/150). Из 4 строк, потерянных между near и «целиком», три — NONE-строки, где бот ничего не делает; исполненный приказ с неверной целью один (sttv3_045). Near без accept — одна строка (csv3_004: VAULT_WINDOW на north door)."

Label this 88.0% clearly so it is not confused with the rules-v1 matcher exact rate, which is also 132/150 = 88.0%.

### numbers: checked and found right

- Data loading: my own loader gives 633 lines = 363 v1 + 120 v2 + 150 v3, 50 v3 lines per author, kind quota identical for the three authors (place 20, zone_object 5, two_places 5, callout 5, unnamed 4, on_signal 4, other_ref 3, negated 2, other_sense 2); v3 intent counts equal eval_v3.log line 1; no v1 line is flagged for re-reading.
- Matcher, rules v2 (current locations.py run from a scratch copy): exact 145/150 = 96.7%; r6 48/50, cs 50/50, stt 47/50; object / qualifier / zone 148 each; unknown_modifier raised 12, readers 12, both 12; the five mismatches are the ones in eval_v3.log; 119 of 483 older lines get a target. Equal to eval_v3.log and results_v3.json.
- Matcher, rules v1: eval_v3_rules_v1.log is internally consistent (18 listed mismatches = 150 - 132; per author 7 / 6 / 5 = 43 / 44 / 45 of 50) and its sha256 equals the frozen.txt entry 1ff6fd96...; not recomputable, the v1 rule files are not in the archive.
- Shipped bot on the v3 lines (family gate, 0.58), from results_v3_shipped.json with my own gate and scoring: raw near 125/150 = 83.3%, exact ok 82.0%, wrong family 5/150 = 3.3%, acts on non-order 2/24, score 76.7; strip 81.3 / 80.0 / 4.0 / 3 of 24 / 73.3; 3 answers differ. Equal to the log.
- The stored shipped probabilities are real: re-running the three members of models/coop-deberta-v3-ens3-v2 one at a time on CPU here gives max abs difference 2.8e-06 on raw and strip, and identical picks on all 300 inputs.
- Re-trained ens3 (leave one author out): top gate v3 near 135/150 = 90.0, ok 89.3, wrong family 2/150 = 1.3, score 87.3; family gate 136/150 = 90.7, 90.0, 1.3, 88.0; all 633 lines 89.7 / 1.6 (top) and 91.0 / 2.1 (family); older lines 89.6 / 1.7 and 91.1 / 2.3; single seeds at the top gate 88.0 / 89.3 / 87.3 near. All equal to eval_v3.log section C.
- ens3 averaging is the arithmetic mean of the three seeds' class probabilities, for both the held-out predictions and the out-of-fold predictions (reproduced with numpy; every ens3 and single-seed number matches).
- Thresholds: each fold's threshold is fitted on out-of-fold predictions of the two training authors only (422 lines; no held-out author id and no seed id among the fitted keys; the test keys are the held-out author's 211 lines plus 16 probes). Thresholds found: top r6 0.62, cs 0.58, stt 0.58; family r6 0.60, cs 0.58, stt 0.52. No gate is selected on test lines: both gates are reported, the shipped side uses its own fixed family / 0.58.
- The v3 result does not hinge on the threshold: over every combination of near-tied out-of-fold thresholds (within 1 line of the best) v3 near stays 135 (top) and 136-137 (family) with 2 wrong-family lines; in a diagnostic sweep the re-trained ensemble beats the shipped one at every threshold from 0.0 to 0.9 (for example at 0.0: near 92.0 / wrong family 4.7 against 86.0 / 11.3).
- Bootstrap: the log's five intervals are replicated exactly with its own algorithm (strip-raw -3.3 [-8.0,+0.0]; +10.7 [+3.3,+18.7]; +11.3 [+4.0,+19.3]; older +0.0 [-3.9,+4.1] and -0.2 [-4.3,+3.7]). They are stable: over 20 RNG seeds x 4000 reps the lower bound for top is +3.3 every time, for family +4.0..+4.7; 200k reps give [+3.33,+18.67] and [+4.00,+19.33].
- The direction of the pooled gain is established at line level: score 17 lines better / 5 worse (top, sign test p=0.017) and 17 / 4 (family, p=0.007); it also holds for exact-ok (+7.3 / +8.0) and for pick equals majority intent (+8.7 / +9.3), and on the 90 v3 lines with no close copy among other authors' lines or seeds (score +8.9 [+1.1,+17.8] top, +10.0 [+2.2,+18.9] family).
- The 483 older lines are the same ids in both studies (all v1+v2 lines), with the same held-out authors and seeds 0-2; my v21 recomputation equals eval_v21.log (ens3/top 91.3 / 90.1 / 2.5 / 6.7 / 86.3, mean threshold 0.46; ens3/family 90.5 / 89.2 / 1.9 / 5.3 / 86.7, mean threshold 0.57).
- HANDOFF transcription: 88.0 (rules v1, all 150), 94 (rules v2, stt), 96.7 (rules v2, all 150), 83.3 / 3.3, 90.0 / 90.7 / 1.3, +10.7 [+3.3,+18.7], +11.3 [+4.0,+19.3], 0.0 / -0.2 [-4,+4] all match the logs, and each matcher figure is attached to the right rule version and author subset; the v2 line '90.5% / 1.9%, threshold 0.58, family gate' matches eval_v21.log, COOP-BOT.md line 426 and bot_config.json.
- Training bookkeeping: each train_v3_cv_*.log shows 18 model loads (3 seeds x (1 full + 5 out-of-fold)) and three 'done' lines; results_v3_probs_*.json _meta has n_items 633, n_seeds 383 and the fixed recipe (20 epochs, batch 16, lr 5e-5); 150 of the 383 seeds are new against v21.
- Strip input is the same under the rules now on disk: locations.normalized(text, 'strip') equals the stored strip_text on 150/150 lines (58 lines rewritten), so section B does not depend on the rule version.

## The Python place matcher (`matcher`)

### matcher #1: Role of the primary target is never scored, and it misfires on ordinary orders: the place the bot must act on is marked from / them / status / mine / not

Reviewer: major, matcher. Affects: HANDOFF section 4 'exact target 96.7% / 94% stt' (needs the caveat that role and flag are not part of it); locations.py rule 5 / 5b / rule 2; locations.json role_* and status_next lists; locations.h PlaceRole / primary contract

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

The finding holds. The 96.7% / 94% numbers are correct as defined (object, qualifier, zone of the primary), but the role on the primary is never measured, and the written contract for it contradicts itself.

**What is not scored**
- `eval_v3.py:40-45` compares only (object, qualifier, zone). The readers' labels have no role field (`coop_v2.py:69-73`), and `blind/spec_v3.json` defines the target without one.
- `run_dev` (`locations.py:471-474`) never requires the role to be empty; "ROLE" in `accept` only adds an extra way to pass.
- Role is checked indirectly only where it picks the primary among several targets. On the blind order lines all 25 roles on non-primary targets look right by my reading.
- A role on the primary itself only happens through the fallback at `locations.py:423`. On blind order lines that is always a single-target line.

**The contract contradiction**
- `locations.h:46` and `locations.py:42-43` say the bot is not sent to a place with a role.
- `locations.h:61` calls the primary "the target the bot acts on".
- The dev set uses both readings: "they breached the west door, fall back" accepts [None, "ROLE"], while "stack up on the main door" (role=them), "after i open the main door flash it" (mine) and "watch the long hallway from the east door" (from) accept the role-carrying place as the target.

**Blind lines**
- 126 order lines, 124 exact, 8 with a role on the primary.
- Two are correct negations (WAIT: r6v3_027, sttv3_039).
- Six are misfires on the place the readers unanimously say the bot must act on: r6v3_000 and csv3_027 (from, via "off"); r6v3_021, csv3_048, csv3_039 and sttv3_040 (status).
- Counting those as wrong gives 139/150 = 92.7% (r6 46/50, cs 47/50, stt 46/50 = 92%).
- A planner that ignores the role on the primary keeps 145/150 on these lines, but would then act on enemy or own places in lines like the dev "fall back" case.

**Corrections to the reviewer's wording**
- "Flag is not scored anywhere" is too broad: `eval_v3.log` reports the unknown_modifier flag (raised 12, readers 12, both 12). Only `unsure` and `other` are unscored.
- Four exact order lines carry flag=unsure, not three: r6v3_035, csv3_044, sttv3_003, plus csv3_014 (a WAIT line). That is 4 of 18 order lines whose primary is a lone qualifier.
- In the reviewer's own `probe2.json`, 6 of the 7 conditional "I + verb" lines get role=mine (6 of 10 in the whole group), not 5 of 7.
- "Misfires on ordinary orders" needs a trigger word. My 20 plain control orders got no role. The realistic rate is about 5% of place-naming orders (6/126 blind; 5/147 in the developer's own v3 seeds, e.g. "cover me from the east window", "rappel from the roof"). The 30/151 figure comes from a deliberately adversarial set.
- `role_not` is not "the opposite" of the leading-only negation rule. It is a 5-token window that stops at punctuation, and it was right 3 of 3 times on blind primaries. The double-negative and rule 5b / rule 2 failures are real but appear only on constructed lines.

*Recommended action.* **Now, without changing rules, vocabulary, spec, seeds or labels**

1. In the v3 write-up (HANDOFF section 4 table and the future COOP-BOT.md "v3" section), add next to "exact target 96.7% / 94% stt" a sentence like:

   "Exact = object, qualifier and zone of the primary target. The role on the primary and the unsure / other flags are not scored. On 6 of the 124 exact order lines (r6 2, cs 3, stt 1) the place the readers name as the bot's target carries role from or status. If the planner obeys 'not sent to a place with a role', the usable rate is 139/150 = 92.7% (stt 46/50 = 92%). This count was made after the blind lines were seen. 4 of the 18 lone-qualifier order lines carry flag=unsure."

2. Resolve the contradiction between `cpp/coop_intent/include/coop_intent/locations.h:46` ("the bot is not sent to a place with a role") and `:61` ("the target the bot acts on"), and the matching text at `scripts/coop/locations.py:42-44`. State explicitly what the planner does when `Primary()->role != None` (the fallback at `locations.py:423`). Do this before stage 2 (UE planner). Record the header edit in `frozen.txt`. Any planner rule chosen from these six lines must be marked "after tuning".

**Deferred, because it touches frozen material**

- Do not edit `role_from` / `role_them` / `role_mine` / `status_next`, the 5-token window, rule 5b or rule 2 against the current blind lines.
- To fix and measure role, add a role (or "bot acts here: yes/no") field to the spec, write new blind lines with that label, and extend `eval_v3.py` and `run_dev` to require role == None on the bot's own target.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

The reviewer's counts reproduce, but the framing is overstated in four places and no reported number is wrong.

What stands:
- "Exact target" compares only (object, qualifier, zone) of the primary (eval_v3.py:40-45). The readers never labelled a role (blind/spec_v3.json has only object, qualifier, zone, unknown_modifier), so the role value and the "unsure" flag are unmeasured.
- The contract contradicts itself. locations.h:46 and locations.py:43 say the bot is not sent to a place with a role; locations.h:61 and locations.py:44/423 make such a place the primary ("the target the bot acts on") when every target has a role. No document resolves this: cpp/coop_intent/README.md does not mention locations, and COOP-BOT.md has no v3 section.
- On the blind lines, 8 of 126 order lines have a primary with a role. Two are true negations (intent WAIT). Six are places the readers say the bot must act on: 2 "from" ("smoke off X", a word-list misfire) and 4 "status" ("east door's boarded ... blow it", "west is yours bot"; the label describes the line correctly, the "not sent" reading is what is wrong).
- By author: r6 2, cs 3, stt 1. So 96.7% is the number for a planner that acts on Primary() whatever its role; a planner written literally to locations.h:46 would get 139/150 (92.7%), stt 46/50.

What does not stand:
1. "Role is never scored" is wrong for its main job. Roles move the primary off the first target on 22 blind lines, 21 of them exact; with roles ignored, exact falls from 145 to 124. That selection is inside the 96.7%.
2. "Flag is not scored anywhere" is wrong for unknown_modifier: eval_v3.py:59-61 and eval_v3.log report raised 12 / readers 12 / both 12. Only "unsure" is unmeasured. It is documented design (locations.py:31-36) and sits on 7 blind lines: 2 of the 5 real matcher mismatches and 5 correct targets, 4 of them orders.
3. "A planner cannot tell 'enemy at the north window' from 'someone watch the north window'" ignores that the planner also gets the intent (NONE vs HOLD_ANGLE; bot_brain.h:55 "under Ignore they are contacts").
4. "role_not does the opposite of coop_bot.py:41-45" is inaccurate. The lookback is local (5 tokens back, stops at punctuation); the example from that comment, "hold that door, don't let anyone through", gets no role with or without the comma.

Also:
- The fallback to the first target is deliberate. The spec asks for "the place the line is about" on callouts, and 9 exact NONE lines depend on it.
- Nothing consumes role today: coop_bot.py and bot_brain.cpp pass the record through, and the planner is stage 2.
- The 30/151 adversarial figure comes from lines written to trip the rule (categories F_role_false_*), so it is not a rate.
- The "I + verb" on-signal pattern occurs on 0 of the 12 blind on_signal lines.

Net: a documentation and contract gap plus an unmeasured output field, to be settled before the stage-2 planner is written. It is not an error in the 96.7% / 94% claim.

*Recommended action.* Documentation only; do not touch the role word lists, ROLE_WINDOW, rule 5b or rule 2.

1. **HANDOFF.md section 4, under the matcher table, and the future COOP-BOT.md "v3" section.** Add: "Exact target = object, qualifier and zone of the primary. Readers did not label roles; roles enter the number only through the choice of primary (22 of 150 lines, 21 right; without roles 124/150). The role value and the 'unsure' flag are not scored; unknown_modifier is (12/12). On 8 of 126 order lines the primary itself carries a role because every place in the line had one; on 6 of them it is the place the bot must act on (2 'from': 'smoke off X'; 4 'status'). 96.7% assumes the planner acts on the primary whatever its role; a planner that refuses a primary with a role would get 139/150 (stt 46/50). 'unsure' sits on 4 correct order targets and on 2 of the 5 mismatches."

2. **cpp/coop_intent/include/coop_intent/locations.h:46 and the role paragraph of the locations.py docstring (line 43).** Replace "the bot is not sent to a place with a role" with the real contract: a role demotes a target when the primary is chosen; if the primary itself has a role, every place in the line had one, and the intent decides (Ignore: a contact; Act or Queued: still the order's place, the role is a hint). Put the same rule in the stage-2 plan in cpp/coop_intent/README.md. Both files are hash-tracked, so record the new hashes in frozen.txt as "comment only, rules unchanged; --dev and --location-tests unchanged".

3. **Next blind round.** Add a "bot is sent here / role" field to the spec so the role can be scored. Any edit to role_* / status_next, the 5-token window, rule 5b or rule 2 before then is a rules edit after the blind lines were seen and must be marked as after tuning.

### matcher #2: The stt 'held-out' 94% is not an independent check of rules v2: both stt gains are idioms that also occur in the tuning authors' lines

Reviewer: major, methodology. Affects: HANDOFF section 4: '94% on held-out author stt', '96.7% on all 150', 'unknown_modifier 12/12' in eval_v3.log; frozen.txt:139 'stt is the held-out author for v2 (94.0%, was 90.0%)'

**Verifier (reproduce): confirmed, minor; reproduced: yes; touches frozen: no**

Every factual part of the finding reproduces; the conclusion needs one qualification.

**What holds**
- stt is 45/50 under rules v1 and 47/50 under v2. The two gained lines are sttv3_030 ('bro my ping is through the roof again sorry') and sttv3_034 ('this is not even my main ...'), both of kind other_sense.
- Each repeats an idiom of a tuning-author line: r6v3_039 ('My ping is through the roof tonight ...') and csv3_035 ('my main got vac banned ...').
- The two v2 entries responsible are the ignore phrase 'through the roof' and 'my' in lone_not_after. Removing both puts stt back at 45/50.
- 'through the roof' changes the score of no r6 or cs line: r6v3_039 stays wrong because of 'west coast'. Its only scored effect is the held-out line.
- The three stt misses with no counterpart in r6/cs (sttv3_023, sttv3_036 'the rough', sttv3_045 'second story') are identical under v1 and v2.
- The unknown_modifier flag follows the same pattern: 7/12 under v1, 12/12 under v2, entirely through rule 1d. The 12 lines are exactly the 4 'unnamed' lines per author. They cover five modifier types: back door x3, colour door x3, left(-hand) window x2 (the spec's three examples), spiral staircase x3 (once per author) and broken window x1. stt's only flag gain is sttv3_018 'spiral stares', again a twin.
- All three authors have identical kind quotas, and the 6 other_sense lines use 3 idioms.
- Author, ann1 and ann2 give the same intent, timing and target on 150/150 lines; r6 ann1 and ann2 are byte-identical. So 'unanimous on 150' means the truth is the author's label, not three independent readings.
- Rules v1 are not on disk or in either archive, so 88.0% cannot be re-run.

**Qualification**
- The 94% is a procedurally clean hold-out. Nothing indicates stt lines were used: three stt misses, one of them a one-entry vocabulary fix ('second story'), were left alone, even though eval_v3_rules_v1.log prints the stt mismatches beside the r6/cs ones.
- The weakness is author independence, not leakage. stt behaves like a replicate of r6/cs (same brief, same quotas, same idioms), so the v1 to v2 gain on stt measures idiom repetition, not generalisation to new phrasing.
- That gain is 2 lines of 50 (exact two-sided p = 0.5; Wilson 95% 83.8-97.9 for 47/50 against 78.6-95.7 for 45/50).
- HANDOFF already labels the v2 numbers as edited on r6 and cs and shows v1's 88.0% next to them. No number is wrong; the reading of 94% as a generalisation figure is unsupported.
- Near-zero reader disagreement is not new to v3: the v2 round had 1 intent difference on 120 lines. Only v1 had 1-3 per author.

I rate it minor: a wording and archive issue with an effect of at most 2 lines.

*Recommended action.* Write-up and archive only; no rule, vocabulary, spec, seed or label change.

1. HANDOFF.md section 4, the table row 'сопоставитель, правила v2 (правлены по авторам r6 и cs) | 94% на отложенном авторе stt; 96.7% на всех' (and the same row in the future v3 section of COOP-BOT.md and DEBERTA-BOT.md). Reword to say:
   - stt is 47/50 (94%) under v2 and was 45/50 (90%) under v1.
   - Both added lines (sttv3_030 'ping is through the roof', sttv3_034 'my main') repeat idioms of r6v3_039 and csv3_035, the lines the rules were edited on.
   - The three stt misses without a twin (sttv3_023, _036, _045) are not fixed.
   - 96.7% is after tuning on 100 of the 150 lines.
   - The figures fixed before the lines existed are 88.0% (all) and 90% (stt); 94% is not a generalisation estimate (n=50, Wilson 95% 84-98).

2. Same section, add one sentence on the blind set: the three authors wrote to one brief with identical per-kind quotas, and the 6 other_sense lines use 3 idioms, so stt is a replicate rather than an independent author.

3. Wherever the flag result is quoted (eval_v3.log 'raised on 12 ... both 12'): say it was 7/12 under v1, that the 12 lines are 4 per author by quota with five modifier types (three of them the spec's examples), and that it is an after-tuning figure.

4. Wherever 'readers agree on 150, unanimously on 150' is quoted: say the annotators never differ from the author on intent, timing or target, and that r6 ann1 and ann2 are byte-identical, so the truth is the author's label.

5. Archive: bring the v1 locations.json (9999cc9f...) and locations.py (111d1a76...) from the Windows machine into the tree, for example as scripts/coop/rules_v1/, so eval_v3_rules_v1.log can be re-run. In the write-up, list the v2 word-list additions the _note omits ('my' in lone_not_after, 'stack' and 'awp' in role_them, and whichever change accounts for 120 against 119 older lines).

6. Next blind round: authors without a shared brief or fixed per-kind quotas, so the next held-out number is independent.

Fixing the three stt misses or rule 1d's false flags would touch frozen material and needs new blind lines first.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every fact in the finding reproduces. The conclusion drawn from them is too strong, and one sub-claim is weaker than stated.

**What stands**
- stt is 45/50 with rules v1 and 47/50 with v2. The two gained lines are sttv3_030 ("ping is through the roof") and sttv3_034 ("my main").
- Each is fixed by one v2 vocabulary entry written from a tuning-author line with the same idiom: the ignore phrase "through the roof" (r6v3_039) and "my" in lone_not_after (csv3_035). Removing both entries returns stt to 45/50.
- Everything else v2 changes on stt also has an r6/cs counterpart: the new flag on "spiral stares" (sttv3_018; "spiral staircase" in r6v3_040 and csv3_036) and two role changes from the "I said" rule (sttv3_012, sttv3_023; csv3_034).
- The three stt misses (sttv3_023, 036, 045) are unchanged.
- The 12 unknown_modifier lines are exactly the 12 "unnamed"-kind lines (4 per author) and use five modifier types: back, a stairs colour on a door, left, spiral, broken. The first three are the spec's examples.
- All three authors have identical kind quotas; the 6 other_sense lines use 3 idioms.
- Author, ann1 and ann2 agree on intent, timing and all four target fields on 150/150 lines. The r6 ann1 and ann2 files are byte-identical.
- The v1 rule files are not on disk.

**What does not stand**
- "Not an independent check" is overstated. No stt line was used for tuning, and all three stt-only misses were left wrong although each is a one-line vocabulary fix. stt independently shows no regression on 50 unseen lines and no false flag from rule 1d. 94% is a correct held-out figure for authors of this generator.
- What the finding really shows is the project's standing caveat applied to the matcher: the authors are one model family and repeat each other (COOP-BOT.md:57-62, 501, 542-543; DEBERTA-BOT.md:72). That caveat is not restated for v3.
- The project's own novelty filter does not catch it: the two twin lines have char-n-gram cosine 0.32 and 0.21 to their twins, so they count as novel. stt is 42/45 on novel lines.
- The clean pre-tuning number (88.0%) is already the first row of the HANDOFF table, and frozen.txt:139 already records "94.0%, was 90.0%".
- "88.0% is supported by its log alone" is weaker than stated. Reverting the documented v2 changes reproduces section A of eval_v3_rules_v1.log row for row on the 150 lines. Only the older-lines count differs (119 vs 120), which means one further v2 word-list edit is undocumented: "a" in lone_not_after or "wall" in lone_block.
- Byte-identical r6 annotator files follow from identical labels under one serializer, not necessarily a copy. In v2, cs ann1 and ann2 also agree on every field of all 40 lines. The 150/150 unanimity is printed in eval_v3.log lines 1 and 3.
- Fixed per-kind quotas are the same stratified design as v1 and v2. For v3 they are simply not written down yet.

**Net**
No number is wrong and no protocol rule was broken. HANDOFF section 4 puts 88.0% (all authors, v1) next to 94% (stt, v2) without the like-for-like 90%, and without saying the +2 lines come from idioms shared with the tuning authors. The difference is 2 lines of 50 (Wilson 95%: 47/50 is 83.8-97.9%, 45/50 is 78.6-95.7%) and no decision depends on it.

*Recommended action.* Write-up only. Do not change rules, vocabulary, spec or labels, and do not fix the three stt misses.

1. **HANDOFF.md section 4, table row 2, and the v3 section of COOP-BOT.md when it is written.** Give the like-for-like figure and the caveat, for example:

   "Rules v2 (edited from the r6 and cs mismatches): stt, not used for tuning, 94% (47/50); with rules v1 it was 90% (45/50). Both gained lines (sttv3_030 'ping is through the roof', sttv3_034 'my main') repeat an idiom of a tuning-author line (r6v3_039, csv3_035). The three stt misses with no counterpart in r6/cs are unchanged. All 150: 96.7%, after tuning. The clean figure is rules v1: 88.0% on all, 90% on stt."

2. **v3 caveats in the same section.**
   - The three authors are one model family writing to the same per-kind quotas: 20 place, 5 zone_object, 5 two_places, 5 callout, 4 unnamed, 4 on_signal, 3 other_ref, 2 negated, 2 other_sense.
   - The readers are unanimous on 150/150, and the r6 annotator files are identical.
   - The 12 unknown_modifier lines use 5 modifier types, 3 of them the spec's examples.
   - The char-n-gram "novel" split does not expose idiom-level repeats for the matcher (stt novel 42/45).

3. **Archive.** Copy the v1 rule files (frozen.txt:110-111, hashes 9999cc9f... and 111d1a76...) from the work machine as locations_v1.json and locations_v1.py. If they are gone, add a frozen.txt note that reverting the documented v2 changes reproduces section A of eval_v3_rules_v1.log on the 150 lines, and that one further v2 word-list edit ("a" in lone_not_after or "wall" in lone_block) is undocumented.

New blind lines are needed only if the rules are edited again, as HANDOFF section 6 already says.

### matcher #3: Wrong primary on plausible two-place lines: the player's own place, a first clause glued to the second, or a corrected place wins

Reviewer: major, matcher. Affects: locations.py rules 2, 3, 4, 5 and ROLE_WINDOW; locations.json role_mine, report_verb, role_not; the docstring example at locations.py:6

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

Every matcher output the reviewer quoted reproduces on the frozen rules v2, and the C++ engine returns the same records. No HANDOFF number is wrong. What holds is a coverage gap: the 96.7% / 94% were measured on blind lines that do not contain these forms.

Sub-claims, in the reviewer's numbering:

- **(i) Player's own place becomes primary — confirmed, the serious part.** `role_mine` is only i / im / ill / ive, searched at most 5 tokens back (`ROLE_WINDOW`, locations.py:57, 388), and "I'm" costs two tokens. "I'm going to take / going to hold / about to push / moving up to / rotating over to the north door, you take the south window" all give primary door/north with no role. So do "let me take", "we take", "me on", "my side is". The v2 report verbs want / need cancel the role (locations.py:397), so "I want the north door, you take…" and "I need to hold the north door, you take…" fail too. This contradicts the spec's own target rule ("I'll take the north door, you take the south window" -> window/south).
- **(ii) Object not carried over — confirmed, but it is a lost object, not a wrong place.** "i'll take the north door, you take the south" and "…the south one" give [door/north mine, *None/south/None]. Rule 2 attaches a later qualifier only across `after_fill` words, so any verb between breaks it; it is not specific to "mine" ("hold the north door then the south one" does the same). The docstring at locations.py:6 states "then door south: primary" for this exact line, which is false. Blind miss sttv3_023 is this class.
- **(iii) Clauses glued — confirmed.** "go to the basement, the north door is open" returns one target, door/north/basement with role=status, as primary; the ordered zone exists only as that target's zone field. The same happens with no punctuation at all, which is how the stt author's lines look, so only a typed full stop separates the clauses.
- **(iv) Self-corrections without "not" keep the first place — confirmed.** Rule 5b only fires on a "not" role.
- **(v) Lone qualifier before a zone is dropped — confirmed, but it is the documented rule** (docstring "lone" paragraph; locations.py:343). "take blue upstairs" gives zone up only.
- **(vi) Rule 2 takes a qualifier that belongs to a following noun — confirmed.** "close the door in the south hallway" gives door/south; `lone_block` is consulted only in rule 3. The dev set's known failure "window north of the main door" is the same family.
- **(vii) avoid / stay out of / keep clear of / nobody / no one give no role — confirmed, but the primary's object/qualifier/zone are what a reader would label.** Only the role is missing, so "wrong primary" does not describe it. "stay away from", "keep off", "don't go near" do get roles.
- "before you go to the roof, check the basement" -> roof is confirmed.

Not verified: the harm statement ("the bot walks to…"). It depends on the classifier's intent for these lines and on a planner that does not exist yet; I did not load the ensemble.

*Recommended action.* Do not edit the rules now.

1. **Docstring, comment only.** /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/locations.py line 6: replace the example with one the code satisfies, e.g. `"i'll take the north door, you take the south window" -> door north (role mine), then window south: primary`. The file hash changes, so add a frozen.txt line saying "docstring only, rules and C++ unchanged".

2. **Write-up.** In the v3 section of COOP-BOT.md and under the matcher table in HANDOFF.md section 4, add a limits paragraph along these lines:
   "Exact target 96.7% / 94% is measured on lines where the player's own place has I / I'm / I'll at most 4 tokens before it (8 lines), with one self-correction (rules v2 were tuned on it) and no order + status clause pairs. Roles are not scored: on the 6 negated lines the primary carries role=not on 3. On reviewer-written probes the matcher takes the player's own place as the target for 12 of 30 first-person lead-ins ('I'm going to take…', 'let me take…', 'I want / need…', 'we take…'), merges 'go to the basement, the north door is open' into one status target, keeps the first place in 'north door no wait south door', and returns a bare direction for '…you take the south one'. The planner must not act on a primary whose role is set."

3. **Rule fixes belong to rules v3, with new blind lines.** Candidates: a clause-based or wider "mine" search plus me / we / let me; want / need out of `report_verb` or limited to "I want you…"; object carry-over to "the X one"; clause separation for zone-before and qualifier-after that does not depend on punctuation; correction markers; `lone_block` check in rule 2; avoid-type words in `role_not`. Write the new blind lines from the unchanged spec before quoting any matcher number, and score role as well as object / qualifier / zone in eval_v3.py. Any number produced after such edits on the current 150 lines must be marked "after tuning".

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: yes**

Every quoted line reproduces on the frozen rules v2, and none of it is written up as a limitation anywhere. The finding stands as a real set of matcher limits, but it changes no reported number and some of its counts and harm statements are overstated. I rate it minor (upper end), not major.

**What holds**
- **(i) Player's own place.** "mine" is set only when i / im / ill / ive is within 5 tokens before the place. An apostrophe costs one token: "im going to take the north door, you take the south window" gives primary window/south, but the same line with "I'm" gives primary door/north. "I've got eyes on the north door, ..." and "I need / I want to ..." also fail. The reviewer's 7 long forms fail 6 of 7 on my re-run, not 5 of 7.
- **The bot does act on these.** The shipped v2 classifier returns HOLD_OTHER_ANGLE at 0.99 on all of them, so the planner is handed the player's own door.
- **(ii) "the south one" / bare "south".** After another place the object is lost and only the direction remains. The docstring at locations.py:6 claims "door south: primary" for exactly this line and is false; the C++ header has the correct example.
- **(iii) Comma glue.** "go to the basement, the north door is open" gives one target door/north/basement with role status, and the bot acts (MOVE_TO 0.81).
- **(iv) Corrections without "not".** The first place stays primary. With a verb the bot acts on it: "smoke north door no wait south door" gives SMOKE at door/north (5 of 5 such lines).
- **(v) Lone qualifier before a floor word** is dropped: "smoke red downstairs" gives zone down only.
- **(vi) Rule 2** attaches a qualifier that belongs to a following noun: "open the door to the east room" gives door/east, and the bot acts (OPEN 1.00).
- **(vii) avoid / stay out of / keep clear of** set no role. In two-place lines this gives a wrong primary: "avoid the main door, go through the east window" gives door/main with VAULT_WINDOW acting (3 of 3).

**What is overstated**
- **(ii) harm.** The primary is still the bot's side with the right direction, not the player's door. Bare "south" as qualifier-only is what the spec and the dev set accept ("i've got north, you take south" expects [None, south, None]). The one blind instance, sttv3_023, is already counted as a miss in the 94%.
- **(iii) "8/8 probes".** One of the eight ("basement, north door") is correct by design, and two ("hold the stairs, blue is pushing", "take the window, east side is clear") are ambiguous.
- **(iv) the three quoted lines** have no verb, and the shipped classifier does not act on them (WAIT / NONE / say again).
- **(vii) single-place lines.** The primary is the same place with or without a role, and the spec's truth for a negated line is that place. Whether the bot goes there is the classifier's call: on v2, two of four act as TAKE_COVER, one is ignored, one is "say again".
- **Frequency.** The probes were written by someone who had read the rules, so "3/3" and "4/4" are not rates. In blind data all 17 "mine" lines (8 in v3, 9 older) are short forms, and the 8 v3 ones are all matched. A qualifier directly before a floor word occurs in 0 of 887 dev and blind lines. All three blind corrections contain "not".

**What the numbers already say**
The 96.7% / 94% headline stands. On blind two-place lines the exact target was 10/15 with rules v1 and 14/15 with rules v2, of which 10 lines were tuned on; held-out stt is 4/5 under both rule versions. HANDOFF quotes only the aggregate.

The want / wanted / need report verbs change the output on 0 of those 887 lines, so they are untested in either direction. The rule-2 class in (vi) was already a known dev failure ("window north of the main door").

*Recommended action.* Do not change the rules or the vocabulary now.

1. **scripts/coop/locations.py line 6 (docstring only).** Replace the example with the one the code and the C++ header actually satisfy: `"i'll take the north door, you take the south window" -> door north (role mine), then window south: primary`. Record the new hash in scripts/coop/frozen.txt with a note "docstring only, find() unchanged"; `locations.py --dev` and section A of eval_v3.log must stay identical.

2. **Write-up (HANDOFF.md section 4 under the matcher table, and the future "v3" section of COOP-BOT.md).** Add:
   - "By line kind: on two-place lines the exact target was 10/15 with rules v1 and 14/15 with rules v2 (10 of those lines were tuned on); on held-out author stt, 4/5."
   - "Known limits of the primary target, found by reviewers' probes and not measured on blind lines:
     (a) the player's own place is recognised only when i / im / ill / ive is within 5 tokens before it, an apostrophe costs one token, and it is cancelled after want / need — "I'm going to take the north door, you take the south window" gives the north door as primary;
     (b) "the south one" or a bare "south" after another place keeps only the direction;
     (c) a comma does not end a clause for floors and after-qualifiers — "go to the basement, the north door is open" gives the north door in the basement;
     (d) a correction without "not" keeps the first place;
     (e) a colour or side word directly before a floor word is dropped ("take blue upstairs");
     (f) "the door in the south hallway" gives the south door;
     (g) avoid / stay out of / keep clear of are not read as negations.
     The planner must read the whole target list and the roles, not only the primary."

3. **Next rules round.** Queue the rule fixes: count i'm / i'll / i've as one token for the role window or search to the clause start; carry the object over to "the X one"; treat a comma as a clause break for zones; add correction markers; add avoid-type negators. These are rule and vocabulary edits after the blind lines were seen, so any number quoted after them needs new blind lines; the stt 94% stops being held-out the moment they go in.

### matcher #4: Vocabulary entries added in v2 from single blind lines misfire: 'to second' / 'on second', three ignore phrases, 'stack', the 'other' target

Reviewer: major, matcher. Affects: locations.json zones.floor_2, ignore, words.role_them; locations.py mention loop (lines 222-233) and rule 5c; the dev line 'stack up on the main door'

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

Every behavioural claim reproduces on locations.py / locations.json as frozen (rules v2, sha 890d651a / b3e9314a) and on the built C++ engine. One attribution in the finding is not supported: 'off the table' is most likely a v1 entry, not a v2 one.

No headline number changes: 88.0% (v1), 96.7% (after tuning) and 94% (stt held-out) stand as labelled. What changes is how 96.7% may be read, and what the shipped matcher does on ordinary orders.

What holds:

1. 'to second' / 'on second' (zone floor_2) fire on any "to/on second <word>". The mention loop (locations.py:222-233) takes the longest phrase at the leftmost token and jumps past it, so the ignore phrase 'second thought' is never reached in "on second thought". That ignore entry is in fact dead everywhere: removing it changes no output on the 150 blind, 483 older or 254 dev lines. Result: "on second thought, hold the north door" gives primary None/None/floor_2 with door/north second. "go to second window" gives window/None/floor_2 with no unknown_modifier flag, while "go to the second door" is flagged.

2. 'stack' in role_them marks the place of the order "stack up on <place>" as an enemy place (role=them). On a two-place line the primary moves to the other place. This is a v1-to-v2 regression on the developer's own "ordinary" dev line 'stack up on the main door'. run_dev() cannot see it because it compares only object/qualifier/zone. The C++ parity file enshrines role=them for that line. 'squad' behaves the same ("squad push the north door" gives role=them).

3. Ignore phrases 'through the roof' and 'table that' delete literal places: "go in / breach / rappel down through the roof" gives no place; "the table that is ..." / "table that's ..." loses the table, and a later object becomes primary.

4. Rule 5c (locations.py:418-421) appends an object/None flag=other target whenever all named places have role mine or status and any later token is other/another/opposite, in any sense ("the other way", "any other ideas", "another route", "another smoke").

5. Each patch buys one line. The 13 lines gained from v1 to v2 (132 to 145) map one-to-one to individual patches. By ablation: 'to second' buys csv3_005, 'on second' csv3_019, 'table that' csv3_041, 'stack' r6v3_029, 'awp' csv3_040, 'my' csv3_035 and sttv3_034, 'through the roof' sttv3_030, rule 5c r6v3_019. So 96.7% is a fit, not an estimate.

6. The _note in locations.json, the locations.py docstring and frozen.txt do not list the role_them additions or 'my' in lone_not_after among the v2 changes. That 'stack', 'awp' and 'my' are v2 additions follows from eval_v3_rules_v1.log. No v1 vocabulary file exists on disk, so 'awper', 'squad', 'camper' cannot be checked.

What does not hold: 'off the table' as a v2 entry from a blind line. It buys 0 blind lines, it protects the dev line "that's off the table" from the v1-frozen dev set, and it sits before the appended v2 entries in the ignore list. Its literal misfire ("grab the kit off the table" gives nothing) is real but is not a v2 regression.

Frequency in real play is unmeasured. Across the project's own 887 lines only the one dev line is affected. The planner that consumes roles is not built yet.

*Recommended action.* Without touching frozen material (do this in any case):

1. In the v3 write-up (the future "v3" section of COOP-BOT.md and the rules-v2 row of the table in HANDOFF.md section 4), state that the 13 lines gained by rules v2 map one-to-one to individual patches, so 96.7% is a fit. The only estimates are 88.0% (v1, n=150) and 94% (stt, n=50).

2. In the same place, add a "known misfires of rules v2" list:
   - "on second thought ..." and "to/on second <noun>" give floor_2, primary or attached, with no unknown_modifier flag;
   - "stack up on <place>" and "squad ... <place>" give role=them;
   - a literal "through the roof" gives no place;
   - "table that ..." loses the table;
   - rule 5c fires on any later other/another/opposite.

3. Record in frozen.txt, under the rules-v2 entry, the v2 vocabulary additions the _note omits: role_them 'awp' and 'stack' (and 'awper', 'squad', 'camper' if they were also v2), and lone_not_after 'my'.

4. Make run_dev() in scripts/coop/locations.py able to check a role, and add dev lines for these cases. locations_dev.json is hash-logged, so record the change.

If the behaviour is fixed (this edits rules and vocabulary after the blind lines, including stt, were read; it must be logged in frozen.txt, and the stt figure stops being held-out for the new rules until new blind lines from a new author exist):

- locations.py:222-233: let an ignore phrase starting at token i+1 pre-empt a shorter non-ignore phrase at i. Or drop 'to second' / 'on second' from zones.floor_2 in locations.json in favour of a rule that takes a bare 'second' as a floor only at the end of a clause.
- locations.json words.role_them: remove 'stack' and 'squad', or accept them only as a subject noun ("stack is", "whole stack").
- locations.json ignore: narrow 'through the roof' and 'table that' to their idioms.
- locations.py:418-421 (rule 5c): require the other-word to be followed by a tail word or an object word.
- Then regenerate intent_config.json and location_tests.jsonl (export_cpp.py --config-only, gen_tests.py) and rerun coop_cli --location-tests.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: yes**

The matcher behaviour the reviewer reports is real and identical in Python and the C++ port, but two sub-claims are overstated and no reported number is affected.

HOLDS
1. 'to second' / 'on second' (zones.floor_2, added in v2 for csv3_005 and csv3_019) read any "to/on second <word>" as floor_2.
   - "on second thought hold the north door" gives primary floor_2, with the north door second.
   - The ignore phrases 'second thought', 'a second', 'one second' never act as a guard: the mention loop is leftmost-first, so 'on second' is consumed before 'second thought' is tried. Removing all three changes no record on 8570 parity lines, 150 blind lines or 254 dev lines.
   - 'a second' only does harm: "get to a second floor window" loses floor_2 and is flagged unknown_modifier (spec_v3 words floor_2 as "a second floor").
   - Article-less ordinals lose the v1 safety flag: "go to second window" gives window/None/floor_2 with no unknown_modifier.
2. 'through the roof' and 'table that' (v2 ignore) drop literal places. Measured gain: one NONE line each (sttv3_030, csv3_041); r6v3_039 stays wrong either way.
3. 'stack' in role_them (v2, buys r6v3_029) gives the dev line "stack up on the main door" role=them.
   - locations.h:46 says "the bot is not sent to a place with a role".
   - run_dev compares only object/qualifier/zone, so the dev set still passes; the wrong role is also the expected value in location_tests.jsonl:8231.
   - With a second place the primary moves: "stack up on the north door and watch the stairs" gives primary stairs.
4. The locations.json _note does not itemise the role_them additions (awp, stack) or 'my' in lone_not_after. The v1 log shows all three are v2 additions.

DOES NOT HOLD OR IS OVERSTATED
- 'off the table' is not a v2 entry taken from a blind line. No blind line contains it; it serves the v1 dev line "that's off the table" (removing it takes dev failures from 5 to 6). I could not diff directly because no copy of the v1 vocabulary (hash 9999cc9f) survives.
- Rule 5c is documented (_note and the locations.py docstring) and is right on all 6 hand-written lines where it fires (r6v3_019, cs_073, cs_119, stt_000, stt_003, one dev line). Its misfires need a non-referential "other" after a line whose only places are the player's or status places, where the fallback primary would be unusable too.
- Tuning v2 on single r6/cs lines is itself disclosed (HANDOFF sections 4 and 6, frozen.txt 2026-10-03T21:03), and 96.7% is labelled as after tuning. frozen.txt records the file-level edit as the project rule requires; the missing itemisation is a documentation gap, not a freeze violation.
- Impact is narrower than "breaks ordinary speech": none of the 633 blind or annotated lines triggers any of these misfires, so every HANDOFF section 4 number stands. The only hand-written line affected is the one dev line, and only in its role. The planner that would consume primary, role and flag does not exist yet.

*Recommended action.* Do not edit locations.json or locations.py now: any such edit spends the stt held-out number.

1. Write-up (free, touches nothing frozen). Add a "known misfires of rules v2" paragraph to the v3 section of COOP-BOT.md that HANDOFF step 5 calls for, and one line under the matcher table in HANDOFF.md section 4:
   "Rules v2 were fitted to single r6/cs lines and have costs outside the 150 lines. 'to second' / 'on second' read any 'to/on second <word>' as floor_2: 'on second thought ...' gives primary floor_2, and 'go to second window' loses the unknown_modifier flag. The ignore phrases 'second thought', 'a second', 'one second' never fire as guards, and 'a second' removes the zone from 'a second floor'. 'through the roof' and 'table that' (v2) and 'off the table' (v1) drop literal places. 'stack' in role_them marks 'stack up on <place>' as an enemy place. Rule 5c takes any later other / another / opposite. None of these occurs in the 633 test lines; the dev runner does not check roles."

2. frozen.txt: add a comment line (no hash change) listing the v2 word-list additions the locations.json _note omits: role_them + awp, stack; lone_not_after + my.

3. Queue for the next rules revision, to be scored only on new blind lines:
   - locations.py mention loop (222-233): let an ignore phrase that starts at token i+1 beat a shorter non-ignore phrase at i; or replace 'to second' / 'on second' with a rule that accepts bare 'second' as a floor only at line end, before punctuation or before a lone_follow word;
   - drop the inert 'second thought', 'a second', 'one second';
   - remove 'stack' from role_them, or exempt 'stack up / stack on';
   - let run_dev assert a role, and give the dev line 'stack up on the main door' a no-role expectation;
   - before the UE planner is written, settle the contract for a primary that carries a role (locations.h:46 against the primary rule).

Rule 5c and 'off the table' need no action beyond the write-up sentence.

touches_frozen is true because every item under 3 changes rules or vocabulary; items 1 and 2 do not.

### matcher #5: unknown_modifier is wrong outside the spec's three examples: rule 1c tests the word before the qualifier, rule 1d treats prepositions as modifiers, post-modifiers are never flagged

Reviewer: major, matcher. Affects: locations.py rules 1b, 1c, 1d and the cut list used by normalized(); locations.json unknown_modifier, determiner, neutral_modifier; the eval_v3.log line 'unknown_modifier flag: raised on 12 lines, the readers mark 12; both 12'

**Verifier (reproduce): confirmed, minor; reproduced: yes; touches frozen: yes**

All five mechanisms and the reviewer's counts reproduce exactly on the unmodified locations.py / locations.json (byte-identical to the project files). The framing and the severity are too strong.

What holds:
(a) Rule 1c tests the word before the whole target phrase, not before the object. locations.py:272 moves t["first"] to the qualifier, and 1c (lines 286-289) reads words[t["first"]-1]. So back / near / left / right / second / next / last / far standing before a fully named place flags it: "fall back north door" -> door/north + unknown_modifier. A comma or one word between ("fall back to north door", "pull back, north door") avoids it. Named phrases behave the same ("come back front door" -> door/main + flag). The C++ port does the same (locations.cpp:313-317).
(b) Rule 1b (lines 282-284) flags two adjacent qualifiers even when they are the same word ("north north door", "red red stairs").
(c) Rule 1d (lines 293-302) flags any unqualified object that has a determiner 2 or 3 tokens before it with non-vocabulary words between, so prepositions and nouns count as modifiers when the article before the object is dropped ("throw a flash through window", "keep an eye on stairs"). With "the" directly before the object there is no flag.
(d) Nothing after the object is examined ("the door on the left", "door number two"), and without a determiner an unknown pre-modifier is not flagged ("hold garage door", "hold northeast window"), while "hold the garage door" is. "the first door" is never flagged ("first" is in neutral_modifier) although "the second door" is.
(e) A flagged target can keep a qualifier ("north west door" -> door/west + flag; "the red door on the north side" -> door/north + flag), against spec_v3.json line 32 ("give the object and leave the qualifier null"). normalized("hold the north west door", "strip") returns "hold the north door", a different valid place.

What needs correcting in the finding:
1. 26 of 225 is the error count on the reviewer's own adversarial lines, not a natural rate. On natural lines by the same three authors (the 483 older lines, written before any v3 rule), the matcher raises 16 flags. By my own single reading (not blind-annotated), 14 are right, 2 are false and at least 2 are missed. Both false flags are type (c): cs_099 "throw the smoke on window when I say" and r6_101 "watch that vert above stairs". Both misses are type (d): r6v2_013 "open window on the left, hop through it" and cs_044 "vault in there, the window on your left". That is about 4 flag errors in 107 bare-object targets, or 4 of the 18 lines where the flag matters. Types (a) and (b) do not occur in any natural line (0 of 64 qualified said-object targets in the blind and older lines), and type (e) occurs in no blind line.
2. "Wrong outside the spec's three examples" overstates it. Rule 1d correctly flags determiner + unknown word + object on the older lines (garage door, double doors, bathroom door, closet door, van door, open window).
3. No headline number in HANDOFF section 4 is affected. "Exact target" in eval_v3.py compares object / qualifier / zone only; the flag is scored separately (eval_v3.py:59-61). No blind line triggers 1b or carries a flagged target with a cut, so the strip experiment is untouched too.

What the 12/12 line in eval_v3.log is worth: 8 of the 12 flagged blind lines repeat the spec's own examples (back door x3, left / left-hand window x2, coloured door x3). The other 4 (spiral staircase x3, broken window x1) plus the left-hand window line are caught only by rule 1d, which was added after the r6 and cs lines were seen (rules v1: 7 of 12). The held-out author stt contributes one 1d line, with the same word "spiral". The blind set has only 2 unflagged bare-object lines without a determiner directly before the object, and neither meets 1d's false-flag condition, so 0 false flags in 138 says little about precision.

Why minor rather than major: the flag is a secondary field handed to a planner that does not exist yet. A false flag degrades to "do not pick the nearest one"; a missed flag is the pre-v3 behaviour. The natural frequency is low, and no claim under review changes. The fix does change frozen rules.

*Recommended action.* Do not edit the rules now. Every code fix below changes matcher rules or word lists after the blind lines were seen and would turn the stt number into an after-tuning number.

1. Write-up. In the v3 section still to be written in COOP-BOT.md / DEBERTA-BOT.md, and wherever the eval_v3.log line "unknown_modifier flag: raised on 12 lines, the readers mark 12; both 12" is quoted, add:
"The unknown_modifier flag agrees with the readers on 12 of 12 blind lines, but this is not a held-out estimate. 8 of the 12 repeat the spec's own examples (back door, left window, coloured door). The other 4 (spiral staircase x3, broken window) are caught by rule 1d, written after the r6 and cs lines were seen (rules v1: 7 of 12). Known failures: (i) an article-less object with a determiner 2-3 words earlier is flagged ('throw the smoke on window'); (ii) back / near / left / right / second before a fully named place flags it ('fall back north door'); (iii) a repeated qualifier is flagged ('north north door'); (iv) modifiers after the object ('the window on your left') or without a determiner ('hold garage door') are not flagged; (v) a flagged target can keep a qualifier ('north west door' -> door/west), unlike spec_v3. On the 483 older lines: 16 flags, 2 false, at least 2 missed (developer's reading, not blind-annotated)."

2. Planner contract, no frozen material. In cpp/coop_intent/include/coop_intent/locations.h:54 and the stage 2 plan in cpp/coop_intent/README.md, state what UnknownModifier means when qualifier >= 0. Until the rules are fixed, the planner should honour the flag only when the qualifier is empty, and should treat it as "confirm", not "refuse".

3. Queue for the next rules version, to be measured on new blind lines (scripts/coop/locations.py, mirrored in cpp/coop_intent/src/locations.cpp, recorded in frozen.txt):
- 1c: test the word before the object token (t["obj"]["first"]), or apply 1c only when no qualifier was attached.
- 1b: skip q1["value"] == q["value"].
- 1d: do not count function words (prepositions, and / or / of) as modifiers.
- Add a post-object check for left / right / back / number.
- On any flag, clear t["qualifier"] and t["cut"].
- Correct the comment at locations.py:285 to match the code.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: yes**

The five mechanisms are real and undocumented, but the scope, the severity and one suggested fix do not hold.

What stands (all reproduced on the current locations.py, rules v2):
- (a) Rule 1c tests the word before t["first"], which rule 1 has already moved onto the qualifier. So back / near / left / right / second directly before an article-less named place flags it: "stay near north window", "fall back north door", "he's near north door".
- (b) Rule 1b flags a repeated qualifier: "north north door".
- (c) Rule 1d flags an article-less unqualified object when a determiner stands 2-3 tokens earlier: "throw a smoke on stairs", "keep an eye on stairs".
- (d) Nothing after the object is checked, and an unknown word without a determiner is not flagged: "the door on the left", "hold garage door", "the first door".
- (e) A flagged target can keep a qualifier: "north west door" gives door/west + flag.
- The reviewer's 26 of 225 (11 missed, 15 false) reproduces exactly.
- No document, code comment or frozen.txt entry mentions any of this. The 254 developer lines contain only "the <word> <object>" flag cases.

What does not stand:
1. **The title is too broad.** On author-written lines the flag is right well outside the spec's three examples: garage / bathroom / closet / van / double / side / second door, spiral, broken, left-hand. The failures are confined to article-less objects, post-modifiers and particles before article-less named places.
2. **26 of 225 is not a rate.** Those lines were built to break the rules. On the 633 author-written blind lines (150 v3 + 483 older), by my own reading:
   - 28 lines are flagged; 2 are false, both class (c), and 1 is debatable ("the open window").
   - 2 lines that should be flagged are not, both post-modifiers ("on the left", "on your left").
   - Class (a) occurs on 0 of 57 article-less qualified or named places; class (b) on 0 of 633.
   - The older lines have no reader truth for the flag, so these counts are my judgment.
3. **No claim under review changes.** Exact target is object / qualifier / zone and does not include the flag. HANDOFF section 4 makes no flag claim. The eval_v3.log line "raised on 12, readers mark 12; both 12" is correct as computed.
4. **That 12/12 is narrow evidence, though.** All 12 are kind "unnamed" lines of the form "the <word> <object>". 7 come from the frozen v1 rules and 5 need rule 1d: 4 from the tuning authors r6 / cs, and 1 from held-out stt ("spiral stares", a modifier r6 and cs also used).
5. **The harm is prospective.** No code consumes the flag: coop_bot.py and BotBrain pass the record through, and the planner is stage 2. normalized() is used only by the strip experiment (v3_shipped.py); no blind line has a flagged target with a qualifier, so no reported number moves.
6. **The suggested 1c fix is not correct as worded.** Testing the word before the object token falsely flags "hold the north side door" ("side" is both a before_fill and an unknown_modifier word) and un-flags "the second north door". It changes 0 of 254 developer outcomes and 0 of 633 blind records, so existing data cannot choose between the two designs.

There is a genuine contract ambiguity behind (a) and (e). locations.h:54 says UnknownModifier means "do not fall back to the nearest one". If the planner lets a resolvable qualifier win, "north west door" sends the bot to the west door. If the flag wins, "stay near north window" is refused.

*Recommended action.* Do not edit the rules now. Under HANDOFF section 6 a third rule version after the lines were seen has no honest number until new blind lines exist. touches_frozen is true for any behaviour fix; steps 1 and 2 below touch nothing frozen.

1. **Write-up.** In the v3 section still to be written in /Users/t.losiev/Documents/models_training/project_synth/COOP-BOT.md, and as a bullet in HANDOFF.md section 4 or 7, add:

   "The unknown_modifier flag matched the readers on the 12 blind lines that have one (12 raised, 12 marked). All 12 are 'the <word> <object>' lines of the 'unnamed' kind; 5 depend on rule 1d, which was added after the r6 / cs lines, and only 1 of those 5 is from the held-out author. Known wrong cases, not covered by the blind or developer lines: (i) an article-less object after 'a/the <noun> <preposition>' is flagged ('throw the smoke on window'); (ii) back / near / left / right / second directly before an article-less named place flags it ('stay near north window'); (iii) a modifier after the object ('the window on your left', 'door number two') or an unknown word without a determiner ('hold garage door') is not flagged; (iv) a flagged target may keep a qualifier ('north west door' gives door/west + flag). On the 633 author-written lines this is about 2 false and 2 missed flags."

2. **Planner contract.** In /Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/include/coop_intent/locations.h:54 and in the stage-2 plan in cpp/coop_intent/README.md, state what a planner does with flag=unknown_modifier when the qualifier is set. Today the two readings fail on different lines ("north west door" against "stay near north window"), so the owner has to choose one.

3. **Rules v3, together with new blind lines.** The new lines should include article-less and post-modifier "unnamed" lines. Candidate edits:
   - Apply 1c to a qualified target only when a determiner precedes the modifier. Do not use the reviewer's "word before the object token" as worded: it flags "north side door".
   - Skip identical neighbours in 1b.
   - In 1d, skip words that are in the rule lists (prepositions, conjunctions).
   - Add a post-object check for left / right / back / number.
   - Clear the qualifier when 1b flags.

### matcher #6: Floor vocabulary is inconsistent and the spec has gaps: second-floor forms, relative floors, a third floor, split 'up stairs', other senses of colour words

Reviewer: minor, matcher. Affects: locations.json zones and lone handling; blind/spec_v3.json map.zones (no floor above the second); HANDOFF section 7

**Verifier (both): partly, minor; reproduced: yes; touches frozen: yes**

Every probe result reproduces, but four parts of the framing are wrong or by design, and none of it changes the HANDOFF section 4 numbers.

**What holds**
- **floor_2 is thinner than its neighbours.** floor_1 has 11 forms and top_floor 6, including level / story forms; floor_2 has only "second floor", "2nd floor", "floor two", "floor 2", "to second", "on second". On a full order the object is still found but the floor is dropped with no flag: "second story north window" gives window/north with no zone.
- **This is already measured blind.** Under the frozen v1 rules, 6 of 48 floor-naming blind lines used a form the vocabulary lacked. The v2 additions fixed all 4 on the tuned authors (r6, cs) and 0 of 2 on held-out stt ("second story", "the rough"). Both stt misses are inside the reported 94% / 96.7%.
- **Relative floors are narrow.** Three phrasings per direction plus upstairs / downstairs are covered, not two as the finding says. "up one floor", "one level up", "up a level", "a floor up" give nothing.
- **Homophones.** 0 of 7 recognised. Only "rough" has blind evidence: it appears in 3 of 50 stt lines and is never recognised.
- **Other senses.** 17 of the reviewer's 34 lines are wrong. The blind other_sense kind is 4/6 (0/6 under v1), and the dev set fails 4 other-sense lines plus 1 two-objects line, not 5 of this class.

**What is by design or overstated**
- **No third floor is the owner's list**, not an inconsistency ("a basement, a 1st floor, a top floor, a roof"; HANDOFF section 7 says floor_2 / up / down were added beyond it). The consequence is real: "third floor" gives no place, and "north window on the third floor" gives window/north with no zone and no flag.
- **"go down stairs" giving stairs is accepted by the dev set.** Only the compound form ("the up stairs window" gives flagged stairs as primary, window without zone) is uncovered. The project's own STT-style author never split the word (0 of 4).
- **"Silent in all cases" is false.** Of the 17 other-sense errors, 6 carry "unsure" and 3 carry a role; 8 are unflagged. The split-stairs compounds, "blew / read stairs" and "the third floor window" carry unknown_modifier.

**Sharper instance found while verifying**
- "on second thought, hold the north door" gives primary = zone floor_2, unflagged, ahead of door/north. The v2 zone phrase "on second" is matched at "on" before the ignore phrase "second thought" can fire, so that ignore entry is dead for the idiom.

*Recommended action.* **Now, write-up only (touches nothing frozen).** In the COOP-BOT.md "v3" section still to be written, and in HANDOFF.md section 7, add a "known limits of the place vocabulary" paragraph along these lines:

"Floors are recognised only in the listed forms. Under the frozen v1 rules 6 of 48 blind floor-naming lines used a form the vocabulary lacked; after v2 the held-out author still loses 2 of 16 ('second story', 'the rough'). An unrecognised floor leaves the object target without a zone and without a flag. There is no numbered floor above the second (owner's list). Lone colour / 'main' / compass words in another sense still yield a place (blind other_sense 4/6; 4 dev lines fail). 'on second thought' yields floor_2."

**Do not edit locations.json or blind/spec_v3.json against the current blind set.** Queue the following for vocabulary version 3, record it in scripts/coop/frozen.txt as edited after the stt lines were seen, and quote a matcher number only from new blind lines:
- **floor_2 forms:** add "level two", "level 2", "second level", "2nd level", "second story", "second storey", "2nd story".
- **Relative forms for up / down:** add "up one floor", "down one floor", "one level up", "one level down", "up a level", "down a level", "a floor up", "a floor down".
- **Idiom guard:** add the ignore phrase "on second thought" (3 tokens, within MAX_PHRASE_TOKENS) so the idiom outranks the zone phrase "on second".
- **Owner decision:** whether to add a third / numbered floor to spec map.zones and locations.json.

After any such edit, run "python locations.py --dev", "export_cpp.py --config-only" and "gen_tests.py" so the C++ port stays equal.

### matcher #7: Matcher time grows with the cube of the line length and the bot puts no cap on the line

Reviewer: minor, matcher. Affects: locations.py find(); cpp/coop_intent/src/locations.cpp Find(); a stuck speech-to-text stream or pasted text would stall the game thread

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The finding holds in both languages; three details need correcting, and no figure in HANDOFF section 4 is affected.

**What holds**
- `find()` / `Find()` take time cubic in the number of place mentions once a line mixes zones with objects/qualifiers, or leaves free qualifiers ahead of later objects.
- Lines with only objects, only zones, only qualifiers or no places are linear.
- Nothing bounds the line before the matcher. The classifier is cut to 64 tokens (`coop_bot.py:126`, `tokenizer.cpp:210`), while the matcher gets the full text (`coop_bot.py:155`, `bot_brain.cpp:176`).
- It is not documented anywhere. `cpp/coop_intent/README.md:146` plans `BotBrain` on the game thread as "microseconds", and README:94-97 documents the analogous `std::regex` limit but nothing for the matcher.
- The parity set never exercises it: the longest of the 8570 lines has 301 matcher tokens and 0 targets, and no line has more than 5 targets.

**Corrections to the finding**
1. `brk()` is not part of the cubic term. It is only reached after the gap test passes (`locations.py:262, 278, 315, 360, 365`; `locations.cpp:283, 348, 400, 406`). `gap()` is the full-distance scan.
2. C++ has a second cubic term that Python does not have. `other_between` (`locations.cpp:404-405`) scans all targets for every (zone, target) pair before the gap test. The reviewer's suggested fix (stop the gap scan at the rule's limit) therefore leaves C++ cubic on "the north and south door in the basement, " lines.
3. C++ is about 55 times faster than Python in-process, not 40. With an early exit the growth becomes quadratic, not linear.

**Practical exposure**
- Voice-length lines are unaffected: the 150 blind lines have at most 17 matcher tokens.
- In C++ a single line must reach about 5 KB of nothing but place words, or about 10 KB of ordinary speech (roughly 2400 words in one utterance), before the matcher costs one 16 ms frame.
- This is input hardening for the UE5 port, not a defect in any reviewed number.

*Recommended action.* Either fix works; neither changes a rule, the vocabulary, the spec, the seeds or a label.

**A. Bound the line in the callers (touches no hash-logged matcher file)**
- Hand the matcher at most the first N matcher tokens at `scripts/coop/coop_bot.py:155` and `cpp/coop_intent/src/bot_brain.cpp:176`, or in the UE5 layer before `Decide`.
- N = 64 changes none of the 8570 parity records.
- Regenerate the parity files with `gen_tests.py` afterwards.

**B. Output-preserving early exit in the matcher**
- `scripts/coop/locations.py:239-240`: give `gap()` a limit and stop once the count passes it (1 for rules 1, 1b, 2b and zone-before; `AFTER_MAX` for rule 2; `ZONE_AFTER_MAX` for zone-after).
- `cpp/coop_intent/src/locations.cpp:237-246`: the same limit in the `gap` lambda.
- `cpp/coop_intent/src/locations.cpp:404-407`: evaluate `other_between` only after the gap and brk tests pass. Without this, C++ stays cubic.
- `locations.py` and `locations.cpp` are hash-logged in `frozen.txt` (lines 141 and 150). Record the new hashes with a "no behaviour change" note, backed by a byte-identical `eval_v3.log`, an unchanged `locations.py --dev` and `--location-tests` at 8570/8570. On that basis the held-out 94% stands.

**With either fix**
- Add two long place-dense lines to `location_tests()` in `cpp/coop_intent/tools/gen_tests.py`, for example "door basement " x200 and "the north and south door in the basement, " x100, so parity on such lines is covered.
- Add this to the "Threads" bullet of `cpp/coop_intent/README.md` and to the v3 write-up: "The place matcher takes microseconds on voice-length lines (C++ about 7 µs at 19 tokens, 0.4 ms at 600), but its pair scans grow with the cube of the number of place words: one 11 KB line of place words takes 79 ms in C++ and 4.5 s in Python. The caller must bound the transcript."

### matcher: checked and found right

- locations.py and locations.json on disk are rules v2 as recorded: sha256 b3e9314a... and 890d651a... equal frozen.txt:140-141; locations_dev.json cf6bbf37... equals frozen.txt:112
- 'python locations.py --dev' on a scratch copy: 254 dev lines, 5 misses, exactly the five known ones (next door, a window, white van, hit the floor, window north of the main door)
- No crash and no exception on 30,319 lines: my 285 adversarial lines, 30 edge cases (empty string, punctuation only, NUL, newline, non-ASCII, zero-width space, single rule words), 30,000 random lines built from every vocabulary and rule-list word with mixed punctuation, 4 long lines; normalized(strip) also ran on all of them
- Deterministic: the sha256 over all 30,319 records is identical under PYTHONHASHSEED 0, 1 and 12345 (e33bec4e...)
- C++ port equals Python: my own out-of-tree build reproduces 8570/8570 on the shipped location_tests.jsonl and gives 30,319/30,319 on my lines, of which 22,035 name a place (the shipped file has 1,371 lines with a place)
- The 'locations' block in models/coop-deberta-v3-ens3-v2/cpp/intent_config.json equals locations.json without the _note (dict comparison True)
- HANDOFF section 7 against locations.json and spec_v3.json: 'first floor', '1st floor', 'ground floor', 'main floor' all give floor_1; zones up, down, floor_2 exist ('go upstairs' -> up, 'go downstairs' -> down, 'second floor' -> floor_2); 'two on red stairs' -> stairs/red with role them, so the callout's place is found and marked as a contact; spec_v3.json RAPPEL / MOVE_TO text makes 'go to the roof' without a rope MOVE_TO
- 22 of the 23 examples in the locations.py module docstring behave as written (the exception is line 6, reported)
- Control, plural/possessive, case and punctuation lines: 37 of 39 right (upper case, hyphen, curly apostrophe, en dash, 'door's', 'stairs'', repeated commas); the 2 failures belong to reported classes
- Word boundaries and longest match: 'secondary' is not 'second', bare 'steps' is not stairs, 'first, floor' is not a zone, 'two steps' / 'few steps' / 'a second' / 'one second' are ignored, 'main hall' and 'yellow ping' give nothing
- Zone attachment inside one noun phrase: 19 of 19 (zone before and after the object, 'I'm upstairs' -> role mine, 'he's on second' -> role them, 'the north window on the second floor of the east side')
- Every v2 change I could trace maps to an r6 or cs mismatch in eval_v3_rules_v1.log, and the three stt-only mismatches (sttv3_023, 036, 045) are still mismatches under v2: consistent with the statement that stt lines were not used for tuning
- eval_v3.log section A on the blind lines reproduced through my own script: exact r6 48, cs 50, stt 47, total 145/150; unknown_modifier raised on 12, marked by readers on 12, both 12
- A typical 15-token line takes about 23 microseconds in Python

## The C++ port (`cpp-port`)

### cpp-port #1: "8570/8570" is true but is weak evidence of rule parity: 84% of the lines name no place, and 20 of 36 seeded port errors pass it unnoticed

Reviewer: minor, cpp. Affects: HANDOFF.md section 4 line 'C++-порт ... Совпадает с Python на 8570 из 8570 строк' and frozen.txt entry 2026-10-03T21:09:54; protection of the port against future rule edits (v3 final export, later vocabulary/rule changes)

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The claim "C++ locations port equals Python on 8570/8570" is true, and the port has no defect I could find: with my own harness the unmutated locations.cpp equals locations.find() on the 8570 shipped lines and on 287,109 new lines (228,114 random + 58,995 constructed), including first/last.

What the 8570 lines prove is narrower than the HANDOFF sentence suggests:
- **Composition:** 7199 of the 8570 lines (84%) name no place. Of the 1371 that do, 845 are golden or tokenizer-stress lines (615 of them only a bare object) and 526 are purpose-written (dev 240, blind 144, seeds 142). There are 337 distinct records in total.
- **Rule coverage:** qualifier-after-object fires on 14 lines, the twin rule on 5, coordinated objects on 2, a named phrase on 2. The "target already has a zone" branch (locations.py:357, locations.cpp:398) is never executed, and no twin ever has an owner with a zone.
- **Vocabulary coverage:** 49 of 105 phrases never occur. That includes all five "<colour> steps" (the reviewer wrote four of five) and 7 of the 8 named phrases.
- **Sensitivity to port errors:** of my own 50 single-point mutants of locations.cpp, 2 are equivalent under the current word lists. Of the other 48, the shipped file notices 25 and misses 23; 9 of the noticed ones are caught by only 1-2 lines. All eight examples the reviewer named are among the missed. The reviewer's 20-of-36 is the same picture with a different mutant set.
- **first/last:** PlaceTarget.first/last are not in location_tests.jsonl and not in coop_cli's comparison string, so the parity check cannot see them. Nothing in bot_brain.cpp reads them today.

Not hidden by the tooling: coop_cli itself prints "8570 lines (1371 name a place)". HANDOFF.md:95 and the frozen.txt entry of 2026-10-03T21:09:54 dropped that qualifier. Nothing in HANDOFF, COOP-BOT.md, DEBERTA-BOT.md or cpp/coop_intent/README.md documents the coverage limits; the C++ README does not mention places at all yet.

No reported number is wrong. The exposure is the next hand port of a rule edit (v2 already added 1d, 5b, 5c by hand) and the UE5 port, which will use this file as its acceptance test.

*Recommended action.* 1. **Write-up wording.** In HANDOFF.md:95, and in the v3 sections of COOP-BOT.md, DEBERTA-BOT.md and cpp/coop_intent/README.md when they are written, replace "Совпадает с Python на 8570 из 8570 строк" with: "Совпадает с Python на 8570 из 8570 строк; место названо в 1371 из них, остальные — строки для токенизатора. В ревью: 0 расхождений ещё на 287 тыс. сгенерированных строк с местами, включая first/last." Do not edit the old frozen.txt entry; append a new one.

2. **cpp/coop_intent/tools/gen_tests.py, location_tests().** Append a seeded generator of place constructions, 30-60k lines (under 1 s in C++):
   - object, qualifier, named, zone and ignore phrases from locations.json;
   - 0..6 filler words drawn from each rule's own list (after_fill, before_fill, zone_after_fill, zone_before_fill, role lists, tail, other);
   - "and" / "or" / comma twins;
   - punctuation between tokens: `,` `.` `.,` `,.` `;` `:` `!` `?`.

   Random recombination alone is not enough: my random fuzz missed kAfterMax, kZoneAfterMax and the two gap-length mutants, and only the constructed lines caught them. Also write each target's first/last into the row, taken from LOC.find() inside gen_tests.py, so locations.py stays byte-identical.

3. **cpp/coop_intent/tools/coop_cli.cpp.** Add first/last to both PlacesStr overloads (lines 201-222), or to a location-tests-only variant if decide/dialogue rows do not carry positions.

4. **Bookkeeping.** Regenerate location_tests.jsonl for the shipped v2 dir and for the v3 export, and append the new gen_tests.py and coop_cli.cpp hashes to frozen.txt.

None of this changes rules, vocabulary, spec, seeds or labels, so no reported number is invalidated.

### cpp-port #2: Vocabulary load fails under a decimal-comma locale on every libc++ platform: tokenizer.cpp takes the strtod branch on macOS

Reviewer: minor, portability. Affects: cpp/coop_intent/src/tokenizer.cpp DebertaTokenizer::Load on macOS/Linux and in the planned UE5 port on non-MSVC platforms; no v3 number changes

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The mechanism is real and undocumented, but the exposure is narrower than the finding says and half of its suggested fix does not build.

**What holds**
- `/Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/src/tokenizer.cpp:61-71` picks `std::from_chars` only under `_MSC_VER` or `__cpp_lib_to_chars >= 201611L`. Apple's libc++ 21 (`_LIBCPP_VERSION` 210106) leaves that macro undefined in C++17, 20 and 23, so the Mac build always takes the `std::strtod` branch.
- `strtod` follows `LC_NUMERIC`. Once the host process has a decimal-comma locale, `DebertaTokenizer::Load` rejects the shipped vocabulary at the first row with "vocab line 1: bad score". All 128000 scores contain a '.', so every row would be rejected.
- The failure is loud (`Load` returns false), never a silent mis-tokenization.
- Nothing in the project triggers it today. `coop_cli` never calls `setlocale`, so it stays in the C locale whatever the environment says, and the six parity checks and every v3 number are unaffected.
- In the C locale the `strtod` branch is exact: bit-identical doubles to `from_chars` on all 128000 scores.

**Corrections to the finding**
1. **Suggested fix (a) is not portable.** Calling `std::from_chars(double)` when `_LIBCPP_VERSION >= 200000` fails to compile on Apple's libc++ for any deployment target below macOS 26.0: "error: 'from_chars' is unavailable: introduced in macOS 26.0". It compiles here only because `CMAKE_OSX_DEPLOYMENT_TARGET` is empty and defaults to the host OS.
2. **The UE5 exposure is overstated.** By a web search result (an Epic forum bug report, not verified against engine source), UE's Linux entry point `CommonUnixMain` forces `LC_NUMERIC=en_US`. Realistic exposure is non-UE hosts that call `setlocale(LC_ALL, "")` or `std::locale::global` on a de/ru/fr/tr system, such as Qt or GTK tools.
3. **The code comment is wrong.** Line 65 says "older libc++ on macOS", but current libc++ takes this branch too.

**Documentation status**
No project document mentions the locale dependence. `frozen.txt:158` says only "strtod fallback ... not built outside Windows", and HANDOFF.md section 3 says the macOS build was not verified.

*Recommended action.* **Code: `/Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/src/tokenizer.cpp`, lines 65-70**
- Replace the `std::strtod` fallback with a parse that ignores the process locale. Either option below rejected 0 of 128000 scores under `de_DE` and `ru_RU` and gave bit-identical doubles:
  - one `std::istringstream` imbued with `std::locale::classic()`, created before the loop and reused per row (standard C++, no platform headers);
  - `strtod_l` with a `locale_t` from `newlocale(LC_ALL_MASK, "C", nullptr)` on POSIX.
- Do not widen the `from_chars` condition to `_LIBCPP_VERSION >= 200000` as the finding suggests. On Apple platforms that fails to compile for any deployment target below macOS 26.0.
- Correct the comment on line 65: libc++ never defines `__cpp_lib_to_chars`, so this is the branch for current libc++, not only "older libc++ on macOS".

**Test**
- Add a `coop_cli` check, or a step inside `--tokenizer-tests`, that calls `setlocale(LC_ALL, "de_DE.UTF-8")`, reloads `vocab.tsv` and re-encodes a few lines. It should skip when the locale is not installed.

**Bookkeeping**
- Record the new `tokenizer.cpp` hash in `scripts/coop/frozen.txt`.

**Write-up, if the code is left as is**
- Add one sentence to HANDOFF.md section 3 and to the "Porting to UE5" list in `cpp/coop_intent/README.md`: "On non-MSVC builds `DebertaTokenizer::Load` parses scores with `strtod`; the host must keep `LC_NUMERIC` at "C" or another decimal-point locale while loading, otherwise `Load` fails with 'vocab line 1: bad score'."

No v3 number, rule, vocabulary, spec, seed or label changes.

### cpp-port #3: coop_cli --decide-tests and --dialogue abort on the v1 bot directory; README says the v1 bot passes the same checks

Reviewer: minor, cpp. Affects: cpp/coop_intent/README.md lines 14 and 65 (v1 claims), the v1 regression checks; not the v2/v3 bot

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The finding holds, with two corrections.

1. Crash on the v1 directory: confirmed. cpp/coop_intent/tools/coop_cli.cpp reads r["places"], r["executed_places"] (lines 332-333) and s["places"], s["executed_places"], s["pending_places"] (lines 424-426) with nlohmann's const operator[]. The stored v1 test files in models/coop-deberta-v3-base/cpp (dated Sep 29 19:18, before the Oct 3 places change) do not have those keys. The current CLI therefore aborts on `--decide-tests` and `--dialogue` for v1 before printing any result. `--golden`, `--tokenizer-tests` and `--gate-tests` still pass on v1, and chat on v1 still works, so README:14 ("still runs") is true. README:65 ("the v1 bot passes the same checks") is false today for 2 of the 5 applicable checks. Nothing in HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md, frozen.txt or code comments mentions this.

2. It is a stale-test-data and harness problem, not an engine regression. With the three keys added as null to copies of the stored v1 files, the same binary gives 38/38 and 66/66.

3. Correction to the reviewer's fix: regenerating the v1 tests with gen_tests.py alone does not work. The Python bot always computes places from scripts/coop/locations.json, while v1's intent_config.json has no "locations". The result is no crash but 38/52 on decide and 52/77 on dialogue, and `--location-tests` refuses. `export_cpp.py --config-only` has to run first; then all six checks pass on v1.

4. Correction on the Release behaviour: with NDEBUG the absent-key read is undefined behaviour. On this machine it surfaced as an uncaught type_error (305 for the test files, 302 for "lone"); other compilers may behave differently.

5. Stale README numbers: confirmed (lines 47/73 say 66, line 75 says 38/38; the v2 files now hold 77 and 52, and frozen.txt:146 records 52/52 and 77/77). This part is already a known to-do: HANDOFF section 5 step 5 lists updating cpp/coop_intent/README.md. The README also has no `--location-tests` row.

6. The "lone" crash at LoadConfig line 170: reproduced, but negligible. It needs an intent_config.json that Python's validate() already refuses, and the shipped config has "lone" on 10/10 qualifiers. The CLI has no try/catch anywhere, so any malformed config aborts the same way. One small related fact: export_cpp.py copies locations.json verbatim without calling validate() (its line 83 comment says "validated by locations.py"), so the refusal comes only from locations.py --dev or gen_tests.py.

No v2 or v3 number in HANDOFF section 4 is affected.

*Recommended action.* Pick one of two fixes, then correct the README.

**(a) Harness fix, no data change.** In cpp/coop_intent/tools/coop_cli.cpp lines 332-333 and 424-426, read the three optional records through find(): an absent key gives a null json, which PlacesStr already maps to "-1:". Allow the fallback only when `!m.cfg.has_locations`, so a v2/v3 test file that lacks the keys still fails. On the stored v1 files this gives 38/38 and 66/66. Record the new coop_cli.cpp hash in scripts/coop/frozen.txt.

**(b) Bring the v1 directory up to date.** Both steps are needed; gen_tests.py alone leaves 38/52 and 52/77:
```
python scripts/coop/export_cpp.py models/coop-deberta-v3-base --config-only
python cpp/coop_intent/tools/gen_tests.py models/coop-deberta-v3-base
```
In scratch this gave 52/52, 77/77, 8570/8570, 2322/2322, 8923/8923/8919 and 754/754. It also makes the v1 C++ bot emit places.

**README (cpp/coop_intent/README.md):**
- Line 65: until (a) or (b) is done, replace with "On the shipped v2 ensemble. The v1 bot passed the same checks as of 2026-09-29; its test files predate the places records and `--decide-tests` / `--dialogue` no longer run on them."
- Lines 47 and 73: 66 -> 77. Line 75: 38/38 -> 52/52.
- Add the `--location-tests` row (8570/8570).
- The same "66-line conversation" appears in README.md:21 and COOP-BOT.md:499; update those when the v3 section is written.

Optional, low priority: wrap LoadConfig and the Run* functions in main() in a try/catch for json::exception that prints the message and returns 2, and read "lone" with find(), so a bad config is refused rather than aborting.

### cpp-port #4: The '+4 lines past std::regex's recursion limit' skip is decided by the test data, not at run time; on libc++ those lines match Python, so macOS and Windows builds differ on such lines

Reviewer: note, portability. Affects: coop_cli --tokenizer-tests output on macOS/Linux; the documented MSVC limit in cpp/coop_intent/README.md (it is MSVC-specific, not a std::regex property)

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

The skip of the 4 "regex limit" rows is driven by a flag in the test data, not by what the regex engine did. gen_tests.py:282-283 writes "regex_limit": true into the 4 REGEX_LIMIT rows, and coop_cli.cpp:265 skips the slot comparison for any row carrying it, on every platform, without looking at SearchErrors().

On this Mac (AppleClang 21, libc++) nothing is past a limit:
- The C++ slots equal Python on all 4 flagged rows and on all 8931 rows.
- SlotPatterns gave up on 0 searches.
- A leading negation is still found behind 20,000 filler words and in lines of 150,000-300,000 characters.

So on macOS the printed text "+4 lines past std::regex's recursion limit, not compared" is inaccurate, although the same line also prints "it gave up on 0 slot searches". The test also leaves 4 rows uncompared that would pass.

Two parts of the finding need scoping:
- **MSVC half not re-derived here.** That MSVC drops the negation after ~118 leading filler words rests only on cpp/coop_intent/README.md:94-97 and the comment at bot_brain.cpp:82-84; there is no MSVC on this machine. If that is right, the Windows and macOS coop_cli builds differ on such lines: Windows does not cancel the order, macOS does.
- **Already documented as MSVC's.** README.md:94-97, bot_brain.h:82-83 and gen_tests.py:63 all attribute the limit to MSVC, and README:138 says it disappears with ICU in UE5. Only three places word it as a general std::regex property: the README table row (line 72), the comment at coop_cli.cpp:265 and the message at coop_cli.cpp:279.

Practical relevance is nil. The longest leading filler run in any real project line (762 golden lines plus the blind line files) is 3 words, against a limit of about 118. No v2 or v3 number depends on this. libc++ does have its own limit (error_complexity, regex header lines 4871-4872), but nothing I ran reached it. Linux/libstdc++ was not tested (no GCC here).

*Recommended action.* No change to the bot, the model or any number. Two optional clean-ups, both outside the frozen rules, vocabulary, spec, seeds and labels:

1. **cpp/coop_intent/tools/coop_cli.cpp, RunTokenizerTests (lines 262-281).** Read SearchErrors() before and after slots.Match(). Skip the comparison of a regex_limit row only if the counter rose on that row; otherwise compare it like any other row. Reword the message to something like "regex slots A/B equal (K lines not compared: std::regex gave up on them; MSVC only)". On macOS it would then report 8931/8931 with 0 skipped. Record the new coop_cli.cpp hash in scripts/coop/frozen.txt; that file already does not match its latest recorded hash.

2. **Write-up.**
   - cpp/coop_intent/README.md:72: change "+ 4 past std::regex's limit" to "+ 4 past MSVC std::regex's limit".
   - After README.md:97 add: "With libc++ (macOS, AppleClang 21) there is no such limit: all 8931 lines, including these 4, give Python's slots and no search is given up, so the Windows and macOS coop_cli differ on a line with more than ~118 leading filler words before a negation (Windows does not cancel the order, macOS does). The longest such run in the project's lines is 3 words. libstdc++ was not tested."
   - HANDOFF.md section 3: say that on the Mac the --tokenizer-tests line reports "gave up on 0 slot searches" and that this is expected.

### cpp-port #5: The matcher has no length cap and is cubic in zones x targets: 4,000 tokens take 1.3 s, 16,000 tokens 80 s on the calling thread

Reviewer: note, cpp. Affects: BotBrain::Decide latency on abnormal input (C++ and Python alike); no v3 number

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

The finding holds, and all of the reviewer's timings reproduce. It affects no v3 number.

- **No cap exists.** `BotBrain::Decide` passes the whole line to `LocationMatcher::Find` (`bot_brain.cpp:176`), and `coop_bot.py:155` does the same with `LOC.record(text)`. Only the classifier input is cut at 64 tokens (`coop_bot.py:126`, `tokenizer.h:29`). Neither caller limits the line (`coop_cli.cpp:120` uses `getline`, `coop_bot.py:200` uses `input()`).
- **The cost is cubic, and it is step 4.** The zone loop (`locations.cpp:393-418`, `locations.py:352-371`) runs zones x targets, and each pair walks every token between them in `gap()` with no early exit. C++ also scans all targets for `other_between` unconditionally. Step 4 is 99.3-99.8% of the time on the slow lines.
- **Precision the finding lacks: the cubic path needs many zone mentions and many object or qualifier targets in the same line.** The 1.3 s / 80 s figures are a constructed worst case (alternating zone and object words).
  - Filler-only, object-only and zone-only loops are linear: under 0.6 ms even at 80 KB.
  - A qualifier+object loop ("north door") is quadratic: 3.3 ms at 22 KB.
  - A repeated real order with a zone ("hold the north door in the basement") costs 1.8 ms at 1000 tokens and 104 ms at 4000 tokens.
- **Normal lines are unaffected.** A 7-token order costs 0.8 us. The longest of the 1899 blind-file lines is 17 matcher tokens / 92 bytes; the longest parity-test line is 301 tokens.
- **Not documented anywhere.** `cpp/coop_intent/README.md:146-148` says BotBrain runs on the game thread in "microseconds"; that was written for v2 and does not mention places. HANDOFF, COOP-BOT.md, DEBERTA-BOT.md, the code comments and `frozen.txt` say nothing about input length or matcher complexity. No STT engine has been chosen (`README.md:129-130`), so no upstream bound can be assumed.
- **The rest of Decide is linear.** The regex slots cost about 0.3 us per byte (6.3 ms at 20 KB), so the matcher is the only super-linear part.

*Recommended action.* Keep it as a note; no v3 number changes.

1. **Write-up.** When `cpp/coop_intent/README.md` is updated for v3 (HANDOFF section 5, step 5), amend the "Threads" bullet (lines 146-148) with: "BotBrain::Decide is microseconds only for order-length lines. The regex slots are linear (about 0.3 us per byte). LocationMatcher::Find is cubic in the worst case, a line with many zone and many object mentions: 64 tokens 16 us, 300 tokens 0.7 ms, 1000 tokens 22 ms, 4000 tokens 1.3 s on an M5 Pro; the Python matcher is about 30-50x slower. The caller must cap the transcript before Decide()." Put the same sentence in the planned v3 section of COOP-BOT.md.

2. **Code, outside the matcher.** Cap the line identically in both callers: in `scripts/coop/coop_bot.py` `Bot.respond()` before `classify`/`decide`, and in the game-side caller before `BotBrain::Decide` (in `cpp/coop_intent/tools/coop_cli.cpp`, the chat loop around lines 519-540).
   - A cap of the first 512 bytes, cut at a token boundary, bounds the worst case to roughly 50 us in C++.
   - It changes none of the 1899 blind lines (maximum 92 bytes) and none of the dialogue test lines (maximum 51 bytes).
   - `coop_bot.py` and `coop_cli.cpp` are hash-logged in `frozen.txt`, so record the edit there. Add one over-long line to `dialogue.jsonl` via `gen_tests.py` so parity covers the cap.

3. **Do not put the cap or an early exit inside `locations.py` / `locations.cpp`.** An early exit in `gap()` would give identical results, but it edits the frozen, hash-logged matcher files and would need a `frozen.txt` entry plus a re-run of the 8570-line parity check.

### cpp-port #6: frozen.txt: the unrecorded coop_cli.cpp hash is the 22:00 portability edit, omitted from the 22:26 entry

Reviewer: note, docs. Affects: scripts/coop/frozen.txt completeness (hash log); no number

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

The hash log is incomplete for one file, and the omission was made on the Windows machine, not on the Mac.

- **What is on disk:** `cpp/coop_intent/tools/coop_cli.cpp` has sha256 `6f3b83cfe7a41b11…` and mtime 2026-10-03 22:00:47 +02:00. That hash appears nowhere in `scripts/coop/frozen.txt`.
- **What the log has:** the last recorded hash is `6114308f…` under the 21:09:54 entry (frozen.txt:153). The 22:26:03 entry (frozen.txt:157-164, "C++ made portable (CMake for macOS/Linux, strtod fallback), not built outside Windows") lists only `CMakeLists.txt` (mtime 22:00:28) and `src/tokenizer.cpp` (mtime 22:00:45). The 23:40:26 Mac entry does not add it either.
- **Where it happened:** the file inside `coop-bot-code.tar.gz` has the same hash `6f3b83cf…` and the same 22:00 mtime, and the archived `frozen.txt` already lacks it.
- **Which CLI produced the Windows counts:** the "8570/8570, decide 52/52, dialogue 77/77" in the 21:09:54 entry necessarily came from the pre-edit CLI, since the test files were generated at 21:09:16-17 and the edit is 51 minutes later. No Windows re-run after the edit is recorded anywhere.
- **Effect on numbers:** none. The on-disk file, built on macOS at 23:25:22, gives the same counts.

Two parts of the reviewer's wording are inference, not established:
- **That the 22:00:47 edit was only the `#ifdef _WIN32` guards.** The pre-edit file is not in the archive. Stripping the four guard pairs (16 combinations, LF and CRLF, with and without an adjacent blank line) did not reproduce `6114308f…` or the older `847a1541…`. The guard idiom also predates this edit: `src/ort_backend.cpp:29` has one, with mtime 2026-09-29.
- **That it is "the portability edit".** This rests on the 20-second mtime adjacency to the two recorded files and on the four guards present (lines 34, 88, 97, 582). It is plausible but not provable from what is in the tree.

This is not a freeze-rule violation under HANDOFF section 6: `coop_cli.cpp` is the check tool, not spec, seeds, matcher rules, vocabulary or labels.

*Recommended action.* Append one entry to `/Users/t.losiev/Documents/models_training/project_synth/scripts/coop/frozen.txt`. Do not rewrite the old entries. Suggested text:

"# correction to the 22:26:03 entry: tools/coop_cli.cpp was also edited on the Windows machine at 2026-10-03 22:00:47 (same session as CMakeLists.txt and tokenizer.cpp) and its hash was not recorded; the Windows counts in the 21:09:54 entry (8570/8570, decide 52/52, dialogue 77/77) were produced by the previous file 6114308f…, and no Windows re-run after the edit is recorded. The file below, built on macOS arm64 (AppleClang 21, Release, ONNX Runtime 1.30.0), passes all six checks with the same counts (location 8570/8570, decide 52/52, dialogue 77/77, plus tokenizer, gate, golden)"

followed by the line:

`6f3b83cfe7a41b11dd33d57f00f052898d3dc0467f49379c71fc9996eabd6fe7 *../../cpp/coop_intent/tools/coop_cli.cpp`

In the v3 write-up (HANDOFF.md section 3 / line 95, or the future COOP-BOT.md v3 section), attribute "C++ = Python on 8570/8570" to the on-disk sources built on macOS, not only to the Windows run. Do not state that the 22:00 edit consisted only of `#ifdef _WIN32` guards unless the pre-edit file (`6114308f…`) is recovered from the Windows machine and diffed.

### cpp-port #7: LocationMatcher::Init accepts three malformed vocabularies that locations.validate() refuses

Reviewer: note, cpp. Affects: robustness of loading a hand-edited or future vocabulary in C++/UE; no parity number

**Verifier (both): partly, note; reproduced: yes; touches frozen: no**

The counts reproduce exactly, but the attribution and the risk example are wrong, and the list is incomplete. No v3 claim or parity number is affected.

**What holds.** On the reviewer's 16 malformed vocabularies, Python refuses all 16. The real C++ path (coop_cli LoadConfig + LocationMatcher::Init) refuses 12 with a message, accepts 3 and aborts on 1 (missing "lone").

**Correction 1: only one of the three is Init's.**
- An extra word list is the only case Init itself can see and accepts: locations.cpp:184-191 looks up the 21 kWordLists names and never checks other keys of `v.words`.
- An unknown top-level section cannot be represented in `LocationVocab`; it is dropped by the CLI loader (coop_cli.cpp:162-174), which cpp/coop_intent/README.md lists as not going into UE5.
- `"lone": ""` is accepted because the struct encodes "no lone object" as an empty string (locations.h:29, "empty: none (a direction)"), and the CLI loader maps both null and "" to it (coop_cli.cpp:170).

**Correction 2: the risk example does not happen.** A misspelled word-list name ("tail" written as "tails") is refused by C++ too, with "missing word list tail", because Init requires all 21 names. Only an additional list next to all 21 is ignored. No rule reads such a list, so matching cannot change.

**Correction 3: the class is larger than three.**
- Missing "version": Python refuses, C++ accepts.
- Duplicate JSON key: Python refuses (`_no_duplicate_keys`), C++ accepts (nlohmann does not reject duplicate keys).
- Any missing key the loader reads ("ignore", an object's "qualifiers") aborts like the missing "lone". The message reports a garbage type ("type must be array, but is number"): const `operator[]` on an absent key is undefined behaviour with NDEBUG.

**Why it stays a note.**
- Every accepted case still gives 8570/8570 on --location-tests.
- In the documented workflow (HANDOFF section 5; export_cpp.py:83 "validated by locations.py") C++ only reads intent_config.json written after locations.py validated the file at import.
- No document says the divergence is intended. locations.h:67 only says Init "refuses a malformed vocabulary", and the locations.json note names only locations.py as the validator.

*Recommended action.* Keep as a note; nothing in HANDOFF section 4 changes. Reword the finding to: "C++ load-time validation is a subset of locations.validate(): Init ignores word lists it does not know; the CLI loader drops unknown sections, "version" and duplicate keys, reads `"lone": ""` as null, and aborts on a missing key. A misspelled list name is still refused (missing list)."

Code changes, none of which alter Find() on a valid vocabulary:
1. cpp/coop_intent/src/locations.cpp, in Init after the kWordLists loop (lines 184-191): refuse any key of `v.words` that is not in kWordLists ("unknown word list X"). This is the only one of the three the UE-bound code can catch.
2. cpp/coop_intent/tools/coop_cli.cpp, LoadConfig lines 162-174 (belongs with the separate coop_cli crash finding):
   - read keys with `contains()`/`at()` inside a try/catch so a missing key returns an error string instead of aborting;
   - refuse keys of "locations" outside {version, objects, qualifiers, named, zones, ignore, words};
   - refuse a "lone" that is absent or a non-null empty string.
3. Afterwards re-run `coop_cli --location-tests` (expect 8570/8570) and append the new locations.cpp and coop_cli.cpp hashes to scripts/coop/frozen.txt.

Alternatively, or in addition, add one sentence to the "Loading data" bullet of cpp/coop_intent/README.md and to the v3 write-up: "LocationMatcher::Init checks less than locations.validate(): unknown sections or word lists, "version" and duplicate keys are not checked. intent_config.json must come from export_cpp.py, which validates through locations.py; the UE loader must map only JSON null to an empty `lone` and must refuse missing keys."

touches_frozen is false: no matcher rule, vocabulary entry, spec, seed or label changes, and the held-out stt number is untouched.

### cpp-port: checked and found right

- Place matcher, differential fuzz: 210,695 new lines (60,000 vocabulary soup, 60,000 rule templates, 40,000 mutations of dev/seed/blind lines, 30,000 with Unicode noise incl. curly apostrophes, accents, Cyrillic look-alikes, emoji, NBSP, combining marks, fullwidth forms, 600 long lines up to 1200 tokens, 95 edge cases incl. empty/whitespace-only/100,000-byte lines, 20,000 raw byte strings with invalid UTF-8 and NUL); 183,796 name a place, 129,013 have 2+ targets, 99,991 distinct records. C++ output is byte-identical to locations.record() on all 210,695 (cmp of fuzz_py.txt and fuzz_cpp_rel.txt). None of these lines is in the shipped 8570.
- Same fuzz through the official path: a scratch model dir with intent_config.json, vocab.tsv and a 190,695-line location_tests.jsonl (the valid-Unicode lines) -> 'coop_cli --location-tests --model-dir ...': 190695/190695, Release and ASan/UBSan builds.
- Vocabulary as data: 60 random valid vocabularies (random phrases up to 4 tokens, words shared between lists) x 3,000 lines = 180,000 lines, 120,199 naming a place: C++ (ASan/UBSan harness) equals Python on all.
- Token positions PlaceTarget.first/last (not compared by coop_cli): equal to Python find() on 150,000 fuzz lines / 413,056 targets.
- locations.cpp read line by line against locations.py: tokenizer, longest-phrase mentions, rules 1, 1b, 1c, 1d, 2, 2b, 3, 4, 5, 5b, 5c, primary and the stable sorts correspond one to one; no difference found by reading either.
- ASan + UBSan build (-fsanitize=address,undefined -O1 -g, out of tree): all six checks pass with no sanitizer report: tokenizer 8931/8931 ids and normalizer, 8927/8927 slots; location 8570/8570; gate 2338/2338; decide 52/52; golden 762/762 (max |dp| 2.86e-06); dialogue 77/77. The fuzz file and the random-vocabulary run are also clean under ASan/UBSan.
- ThreadSanitizer build: --dialogue with the three members on parallel threads: 77/77, 0 warnings.
- -Wall -Wextra -Wpedantic -Wconversion -Wshadow: 28 warnings in project sources, all -Wsign-conversion / int-to-double in coop_cli.cpp, unicode.cpp, intent_model.cpp; none in locations.cpp, bot_brain.cpp, tokenizer.cpp; every flagged index is guarded (intent >= 0, pending >= 0, labels >= 3). clang --analyze on the five core files: no report.
- Char signedness: core rebuilt with -funsigned-char (as on Linux aarch64): places identical on the 210,695 fuzz lines, token ids 8931/8931, slots 8931/8931.
- Locale: with the global C and C++ locale set to tr_TR.ISO8859-9, tr_TR.UTF-8, de_DE.ISO8859-1, ru_RU.KOI8-R, de_DE.UTF-8 the regex slots equal Python on 8927/8927 and the place records do not change (only the vocabulary load is affected, see finding).
- Regex slots on libc++: 113,955 lines (fuzz lines plus slot-word recombinations with Unicode whitespace, U+0130/U+0131/U+017F/U+212A, NUL, newlines, 300 long lines): 0 differences from Python re, 0 searches given up; the 4 regex_limit rows also equal Python.
- CRLF / binary reading: all test and config files converted to CRLF, and to pure LF, in scratch copies: tokenizer, location, gate and decide checks give the same counts (files are read with std::ios::binary; a trailing \r is tolerated).
- Integer widths: unicode_tables.inc DecompEntry.offset is uint16_t and the largest offset is 3403 of 3405 entries; sizes are size_t / int32_t / int64_t throughout, no long.
- The exported vocabulary is current: intent_config.json 'locations' equals scripts/coop/locations.json section by section (version 2); 'export_cpp.py --config-only' run in scratch reproduces vocab.tsv byte for byte and intent_config.json modulo CRLF.
- location_tests.jsonl is reproducible without the model: rebuilding gen_tests.py's text list (random.Random(7), Python 3.11 on macOS) gives the 8931 tokenizer texts exactly and location_tests.jsonl byte for byte (8570 lines, 1371 naming a place); all 8570 stored records equal what locations.py returns today.
- bot_brain.cpp Decide against coop_bot.Bot.decide by reading: same branch order; places computed for every line; a queued order stores its places, GO returns them as executed_places and the GO line's own places do not replace them; negation and WAIT drop both.
- coop_cli negative control: one expected record altered in a copy of location_tests.jsonl -> the diff is printed, 8569/8570, exit code 1 (the check is not vacuous).

## Bot logic, export and test tooling (`bot-integration`)

### bot-integration #1: A queued order and its places do not survive the lines players say between "on my go" and "go": "not yet" drops it, a signal reminder can replace it with a misread order

Reviewer: major, bot-logic. Affects: HANDOFF section 4: the statement that a queued ("on my go") order keeps its place and executes at it; coop_bot.py decide(), bot_brain.cpp Decide(); the expected output in dialogue.jsonl. Part (a) holds for any model, because the seeds label "not yet" lines WAIT; part (b) was measured on the v2 model and the v3 seeds add no reminder lines.

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

All three parts hold on the shipped v2 bot; I re-derived them through the Python/torch bot, a different path from the reviewer's C++/ONNX run, and the numbers coincide.

(a) WAIT is a single intent covering pause and cancel, and decide() cancels the queue on every WAIT.
- The frozen spec says so itself: blind/spec_v3.json WAIT = "the bot pauses: stop what you are doing, hold up, do not act yet, cancel the last order"; intents_v2.json WAIT = "hold up, pause, do not act yet, cancel that".
- The 19 WAIT seeds in seed_commands_v3.json mix 'not yet', 'hold on', 'wait for it', "don't breach yet" with 'cancel that', 'never mind', plus six v3 place seeds such as "don't open the north door yet".
- coop_bot.py:173-175 and bot_brain.cpp:194-196 clear the pending order and its places on any WAIT.
- Result: "breach the north door on my go" -> "don't breach yet" / "not yet" / "hold on" / "wait" / "wait for it" -> "go" gives action "go" ("Going!") with executed_places None. The queued order never runs.
- This is a deliberate, tested choice, not an accident: gen_tests.py:151 "wait: drops it", :163 "the queued places go too". It predates v3.

(b) The on-signal branch (coop_bot.py:176-178, bot_brain.cpp:197-200) never looks at the existing pending order.
- Any line matching ON_SIGNAL whose pick is not NONE / WAIT / GO_NOW and reaches the 0.58 threshold overwrites the queue and its places.
- ON_SIGNAL was written to match "wait for my ...", "hold for my ...", "on three", so a bare reminder with no order in it is forced into one of the 24 intents.
- With the v2 model, 4 of my 20 regex-matching reminders became a new queued order that the next "go" executed with no place (FRAG, ENTRY, ENTRY, HOLD_ANGLE instead of SMOKE at north door). 5 of 20 were read as WAIT and dropped it. 11 left it intact.
- The same lines queue an order out of nothing when no order is pending.
- Bare reminders are absent from training: ON_SIGNAL matches 0 of 383 v3 seeds, and none of the 36 matching lines among the 633 has truth WAIT / NONE / GO_NOW (all are full orders).
- The Python record has no pending / dropped / replaced field; the C++ Decision struct has none either.

(c) models/coop-deberta-v3-ens3-v2/cpp/dialogue.jsonl rows 34-36 record exactly this: PLANT queued, "wait for my call" -> FRAG 0.727 queued, "execute" -> execute. It is a parity file (C++ must equal Python), not a statement of desired behaviour, but the misread sat there unflagged.

Scope:
- No v3 number is affected: eval_v3.py, v3_shipped.py and v3_noharm.py never call decide().
- HANDOFF.md lines 96-97 ("a queued order keeps its place and executes at it") is true only for order -> callouts -> go, which is the one path the tests cover.
- Sequence behaviour has never been measured on blind data. My reminder lines are developer-written, so 4/20 and 5/20 are illustrations, not rates.
- The v3 model does not exist here. Part (a) follows from the seeds for any model; part (b) is measured on v2 only.

Caveat on the reviewer's fix: by my reading about 15 of the 28 WAIT-truth lines among the 633 are cancels with varied wording ('scrap the rappel, call it off', 'nah forget the flake', "nvm don't bother getting behind cover") and about 13 are pauses. "Pause unless a cancel regex matches" therefore swaps a missed order for executing a cancelled order whenever the regex misses, and the project weighs a wrong action at twice a miss.

*Recommended action.* Write-up: HANDOFF.md section 4, lines 96-97, and the future "v3" section of COOP-BOT.md. Qualify the sentence "a queued order keeps its place and executes at it" with three points:
- It holds only when nothing between the order and the signal is read as WAIT or as another on-signal order.
- Every WAIT ('not yet', 'hold on', 'wait for my go') cancels the queue and its place by design, and a bare signal reminder ('wait for my call', 'on three') can replace it with an order the player never gave.
- Multi-line sequences have not been measured on blind data.

Code, in decide() only: scripts/coop/coop_bot.py:173-178 and cpp/coop_intent/src/bot_brain.cpp:194-200.
1. In the on-signal branch, do not queue a line that is nothing but filler plus the ON_SIGNAL match. Keep the existing pending order and return a distinct action (e.g. "reminder"). This also stops such a line creating an order when nothing is queued.
2. Add pending_before and dropped / replaced to the Python record and the C++ Decision, so the log and the planner can see a lost order.
3. Leave the pause-versus-cancel choice for WAIT to the owner. Do not present "pause unless a cancel regex matches" as free: it executes a cancelled order whenever the regex misses, and a regex written while reading the 28 WAIT-truth blind lines is tuned on them. Any number for it needs new blind multi-line dialogues.
4. Add the sequences to cpp/coop_intent/tools/gen_tests.py decide_tests (queue -> WAIT -> GO; queue -> bare reminder -> GO; queue -> second on-signal order -> GO), regenerate dialogue.jsonl and decide_tests.jsonl, and record the new hashes of coop_bot.py, bot_brain.cpp and gen_tests.py in scripts/coop/frozen.txt.

The decide()-only changes touch no spec, seed, label, matcher rule or vocabulary and no reported number. Splitting WAIT into pause and cancel, or adding reminder seeds, would change frozen labels and seeds and would need new blind lines.

**Verifier (refute): confirmed, major; reproduced: yes; touches frozen: no**

The finding stands: I could not refute any of (a), (b) or (c). Its framing and its suggested fix need correcting.

What holds:
- The queue is a single slot keyed only on the intent label of the next line. Any WAIT clears the order and its places; any on-signal line that passes the gate overwrites them; NONE and "say again" leave them.
- WAIT merges pause and cancel by specification, not by accident. blind/spec_v3.json: "do not act yet, cancel the last order"; intents_v2.json: "do not act yet, cancel that". The seeds include "not yet", "hold on", "wait for it" and "don't breach yet".
- Clearing on WAIT is deliberate. gen_tests.py:151 says "wait: drops it" and :163 says "wait: the queued places go too". dialogue.jsonl rows 8-9 have shown "flank left on my call" then "don't push yet" leaving nothing queued since v2.
- So pause lines between "on my go" and "go" lose the order. The bot replies "Standing by." and then "Going!" with action go and nothing executed.

What the finding gets wrong or leaves out:
- **Part (b) is not a queue-replacement bug.** The classifier turns an order-less signal phrase into an order. With nothing queued, "wait for my call" then "go" still throws a frag, and "on three" then "go" still pushes in. A fix that only protects an already queued order does not remove the wrong action.
- **Part (a) fails safe; the opposite case does not.** A take-back that the spec labels NONE leaves the queue intact: "breach the north door on my go", "don't breach", "go" executes BREACH at the north door. So a pause clears the order and a take-back keeps it.
- **The suggested fix is partial and partly unsafe.** Keeping the queue on WAIT unless the line matches "cancel / never mind / scratch that" matches only 7 of the 28 WAIT-majority blind lines. By my reading about 15 of the 28 are take-backs, so roughly 8 taken-back orders would stay queued and fire on the next "go".
- **"Nothing in the record" is literally true but the state is observable.** C++ exposes BotBrain::Pending() and PendingPlaces(); Python has bot.pending. Only the per-line record lacks it.

Scope:
- No number in HANDOFF section 4 changes; all are per-line scores.
- The sentence that a queued order keeps its place and executes at it remains true of the mechanism, but is unqualified.
- The behaviour predates v3 (rows 1-66 of the dialogue file are the v2 conversation). It is not described as a decision or a limitation in HANDOFF, COOP-BOT.md, DEBERTA-BOT.md or cpp/coop_intent/README.md.
- Part (b) and the take-back runs were measured on the v2 model only. The v3 seeds add no signal-only lines and keep "don't breach" as NONE, but the v3 model itself is untested.

*Recommended action.* **1. Write-up (smallest action, nothing frozen changes)**
- /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md section 4: after the bullet that a queued order keeps its place and executes at it, add the qualifier:
  - the queue is one slot;
  - any WAIT line, including "not yet", "hold on" and "wait for it", clears the order and its place;
  - a later line with a signal phrase that passes the gate replaces it;
  - a take-back read as NONE ("don't breach") does not clear it;
  - lines that are only a signal phrase are in neither the seeds nor the 633 lines.
- HANDOFF.md section 7: list this as a default decision the owner can change.
- /Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/README.md, "Known model behaviour": add "wait for my call" read as FRAG 0.73, queued and executed on "go" (dialogue.jsonl row 35), and "on three" read as ENTRY 0.66.

**2. Code (owner's design decision; do not apply the reviewer's fix as written)**
Change coop_bot.py decide() lines 159-180 and bot_brain.cpp Decide() lines 182-203 together:
- A line where ON_SIGNAL fires but which carries no order content must neither create nor replace a queued order, including when nothing is queued.
- Decide the clearing rule as a whole. A take-back of the queued order must clear it, which it does not today when the classifier says NONE. Whether a pause keeps it is the owner's call. Do not key "keep on WAIT" to a three-phrase cancel pattern.
- Put pending-before and pending-after, or dropped / replaced, into the record and into Decision.
- Add these sequences to the decide script in /Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/tools/gen_tests.py and regenerate the parity files: order, "not yet", go; order, "don't <same order>", go; order, signal-only line, go; signal-only line, go.
- Record the change in frozen.txt. Any score of a new cancel or reminder pattern on the 633 lines is "after tuning".

**3. Root fix (touches frozen material)**
Signal-only seeds (for example "on three" or "wait for my call" as NONE) or splitting WAIT into pause and cancel changes seeds, labels and spec, and needs new blind lines before any held-out number is quoted.

touches_frozen is false for actions 1 and 2 and would be true for action 3.

### bot-integration #2: A primary place that carries a role means "act here" on some lines and "keep away" on others; the 96.7% / 94% exact-target numbers ignore roles and flags

Reviewer: major, bot-logic. Affects: HANDOFF section 4 rows "точная цель 96.7% / 94% на stt" (and 88.0% for rules v1, scored the same way); the PlaceRecord contract in locations.h and locations.py; the UE planner that receives PlaceRecord as is (section 5 step 6).

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

The finding holds, with three counting corrections.

**The contradiction.** The PlaceRecord contract says two incompatible things about a primary that carries a role:
- locations.py:43 and locations.h:46 say a place with a role is one "the bot is NOT sent to".
- locations.py:44/423, locations.cpp:472-474 and locations.h:61 make the first target the primary ("the target the bot acts on") when every target has a role.
- Neither the Python nor the C++ bot interprets roles; they pass the record on (coop_bot.py:155, bot_brain.cpp:176).

**What the headline number measures.** eval_v3.py:40-42 compares only (object, qualifier, zone) of the primary. Roles and the flags `unsure` / `other` are never scored. The `unknown_modifier` flag is scored separately (12 raised, 12 marked, 12 both), so "ignores roles and flags" is slightly too broad.

**On the 150 blind lines** (145 exact: r6 48, cs 50, stt 47):
- 18 primaries carry a role.
- Of the 123 acting orders (majority intent neither NONE nor WAIT), 6 have a role-bearing primary, and in all 6 it is exactly the readers' unanimous target:
  - `from`: r6v3_000 and csv3_027 ("smoke off yellow / east window"; "off" is in the role_from word list).
  - `status`: r6v3_021, csv3_048, csv3_039, sttv3_040.
- A planner that obeys "not sent to a place with a role" therefore gets 139/150 = 92.7% (r6 46, cs 47, stt 46/50 = 92%).
- Also excluding acting orders whose correct primary is flagged `unsure` (r6v3_035, csv3_044, sttv3_003) gives the reviewer's 136/150 = 90.7% (45 / 46 / 45). An `unsure` target is still the right place and only costs a confirmation, so 92.7% is the firm figure and 90.7% the strict one.

**Corrections to the reviewer's counts.**
- Among the 126 non-NONE lines, 8 (not 6) have an exact role-bearing primary. The two extra are WAIT lines with role `not` (r6v3_027, sttv3_039), where the contract gives the right behaviour.
- Four (not 3) have an exact `unsure` primary; the extra is csv3_014, also WAIT.
- The 136 figure only reproduces with WAIT excluded from "orders"; with all 126 it would be 133.

**What the blind set does not test.** No acting order in the blind set names only a place to avoid. Where a place to leave appears, a second role-free target becomes primary (csv3_031, sttv3_028). So a planner that ignores the role scores 145/150 here, and the "keep away" case is unmeasured. That case exists in the developer's own lines and live:
- locations_dev.json accepts null/ROLE for "stay away from the windows" (`from`) and "they breached the west door, fall back" (`them`).
- It accepts the place itself for the other 18 role-bearing primaries, including "watch the long hallway from the east door" (`from`) and "white stairs are clear, move up" (`status`).
- The shipped v2 bot acts with RAPPEL on "get off the roof" with primary roof [from], and with FALL_BACK on "fall back from the north door" with primary north door [from].

The same role value therefore means "act here" on some lines and "avoid" on others, and the record gives the planner nothing to tell them apart. The 96.7% / 94% / 88.0% figures are correct as defined but are an upper bound on what a planner can use.

*Recommended action.* **(a) Write-up, no frozen item touched.** In HANDOFF.md section 4 (rows 88.0% / 94% / 96.7%) and in the future v3 section of COOP-BOT.md, add:

"Exact target = object, qualifier and zone of the primary match the readers; the role and the unsure / other flags are not scored. On 6 of 123 acting orders the correct primary carries a role (from: r6v3_000, csv3_027; status: r6v3_021, csv3_048, csv3_039, sttv3_040) that the documented contract says the bot is not sent to. Without them: 139/150 = 92.7%, stt 46/50 = 92%. A further 3 need confirmation (unsure): 136/150 = 90.7%, stt 45/50 = 90%. The blind set contains no order whose only place is one to avoid ('get off the roof'), so that case is unmeasured."

Optionally print the same two tallies from eval_v3.py `matcher()`. That is a reporting-only edit and should be logged in frozen.txt as post-hoc.

**(b) Contract text, comments only.** Resolve the contradiction between locations.h:46 and :61, and between locations.py:43 and :44. State that a role describes how the place was mentioned, and that when the primary carries a role the planner must decide from the intent. Write the per-role table (them / status may be the action target; not is never one; from / mine are not a destination) into cpp/coop_intent/README.md before HANDOFF step 6. Mark it as untested on blind lines. Log the changed hashes in frozen.txt as comment-only.

**(c) Matcher change, touches frozen rules.** Emit primary = -1 or a separate avoid list when the only targets are not / from / mine, and stop treating "off" after a utility verb as `from`. This changes locations.py / locations.cpp and the parity files after the blind lines were seen. The stt number would then need new blind lines, and those should include single-place leave / avoid orders. Do not do this as a free fix.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every fact in the finding reproduces. What does not hold is the proposed replacement number (90.7% / 90%) and the severity.

CONFIRMED
- eval_v3.py:40-42 scores only (object, qualifier, zone) of the primary. Its docstring (lines 4-7) defines "exact" that way, so 96.7% / 94% / 88.0% are correct as place-identity numbers and say nothing about role or flag. Readers never annotated roles (spec_v3.json target = {object, qualifier, zone, unknown_modifier}).
- 18 of 150 blind primaries carry a role: them 6, status 5, not 3, from 2, mine 2.
- On 6 action orders the role-bearing primary is exactly the readers' target:
  - status x4: r6v3_021, csv3_048, csv3_039, sttv3_040.
  - from x2: r6v3_000 and csv3_027 ("smoke off yellow / east window"; "off" is in role_from).
- The written contract contradicts itself. locations.py:43 ("places the bot is NOT sent to") and locations.h:46 say one thing; locations.py:44/423 and locations.h:61 ("primary: the target the bot acts on", first target when all have roles) say the other.
- The contract also contradicts the developer's own pre-test regression set: 20 of 254 dev lines have a role-bearing primary, 18 accept that place as the target, and only 2 accept null/ROLE ("stay away from the windows", "they breached the west door, fall back").
- So a role describes how the line mentions the place; it is not a "do not go" verdict. Nothing in HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md, cpp/coop_intent/README.md or frozen.txt tells a planner how to read a role-bearing primary.
- The 483 older lines show the same pattern: 26 of 119 primaries carry a role (status on "that door's boarded up, blast it"; from on "get off that window line").

OVERSTATED
- 136/150 = 90.7% (stt 45/50) is the floor under the strictest reading (every role means do not go, every unsure means unusable), not the corrected number.
- Only the 2 "from" lines contradict the readers under the spec's own definition (target is "NOT the place to leave"). That gives 143/150 = 95.3% (r6 47, cs 49), with held-out stt unchanged at 47/50 = 94%.
- The literal "role = not sent" reading gives 139/150 = 92.7% (stt 46/50). The status role contradicts only the code comment, not the readers and not the dev set.
- "unsure" means confirm, by design (locations.h:54). It is a cost on 3 correct action-order targets, not an error, and it also sits on 2 of the 5 misses (r6v3_039, r6v3_045), so honouring it removes wrong targets too.
- Nothing shipped acts on places: coop_bot.py and bot_brain.cpp only carry and print the record, and the planner does not exist yet. No freeze rule was broken and the classifier claims are untouched.
- One role error the reviewer did not list: csv3_021 "I hear steps on yellow" gets role mine on an enemy callout.

*Recommended action.* No change to rules, vocabulary, spec, seeds or labels.

1. Write-up: in HANDOFF.md section 4 under the matcher rows, and in the future COOP-BOT.md v3 section, add: "«Точная цель» = у основной цели совпали object, qualifier и zone. Роли и пометы читатели не размечали, они не оценивались. Из 145 совпавших строк у 6 приказов основная цель несёт роль (status 4; from 2 — «smoke off yellow / east window», здесь роль from ошибочна), у 3 приказов — помету unsure. Без противоречия роли читателям: 95.3% (143/150), stt 94%. Если планировщик читает любую роль как «не идти», а unsure как «цели нет»: 90.7% (136/150), stt 90%."

2. Contract: in cpp/coop_intent/include/coop_intent/locations.h:46 and :61, and in the Game integration part of cpp/coop_intent/README.md, replace "the bot is not sent to a place with a role" with a per-role contract:
   - A role says how the line mentions the place; it lowers that place's priority when another place has no role.
   - When the primary itself has a role, the planner decides by intent.
   - status and them are context; the place may still be the target.
   - not means do not act there.
   - mine and from are not a destination for movement intents; from is unreliable on throwables ("smoke off X").
   - unsure means confirm.
   This is a comment-only edit. Record the new locations.h hash in frozen.txt as comment-only. Leave the locations.py docstring (line 43) alone, or edit it comment-only with the same frozen.txt note and a re-run of "locations.py --dev" and "coop_cli --location-tests".

3. Reporting: put the role / flag breakdown (145 / 143 / 139 / 136, per author) in a separate script such as scripts/coop/v3_roles.py. Do not edit eval_v3.py, so eval_v3.log stays byte-reproducible.

4. Do not now remove "off" from role_from, or make primary = -1 when every place is not / from / mine. That is a rule change after all three authors' lines, stt included, were seen; it would need new blind lines before any held-out number is quoted. Queue it for the next blind round, together with role annotation in the spec.

### bot-integration #3: Intent and place are right together on 88.0% of the v3 lines (78% on author stt); HANDOFF reports only the two separate numbers

Reviewer: major, evaluation. Affects: HANDOFF section 4 tables (matcher 96.7 / 94, classifier 90.0 / 90.7): each is right on its own (reproduced from the stored files), but neither is the rate at which the bot does the right thing at the right place.

**Verifier (reproduce): confirmed, minor; reproduced: yes; touches frozen: no**

Every number in the finding reproduces. It is a reporting gap, not an error: no published figure is wrong and no conclusion changes, so I rate it minor rather than major.

**What holds**
- Re-trained ens3 (leave-one-author-out, family gate, per-fold OOF thresholds r6 0.60 / cs 0.58 / stt 0.52) with matcher rules v2: intent near-correct AND primary equal to the readers' exact place on 132/150 = 88.0%.
- Per author: r6 47/50, cs 46/50, stt 39/50 = 78.0%.
- Order lines (truth != NONE, n=126): near 112, exact 124, both 111 = 88.1%.
- Shipped v2 (raw line, family gate, 0.58): 121/150 = 80.7%.
- Top gate (not in the finding): 131/150 = 87.3%.
- HANDOFF.md section 4 (lines 100-123) and eval_v3.py sections A/B/C give only the two component numbers. eval_v3.log section C has no per-author classifier row for the v3 lines, so stt's classifier near (41/50 = 82%) is not published anywhere.
- On-signal slot: the readers mark 12 v3 lines on_signal (unanimous). The ON_SIGNAL regex finds 10, with 0 false hits on the other 138. It misses r6v3_012 ("the second I say so") and csv3_010 ("the moment I call it"). On both, the re-trained pick is an order above threshold (VAULT_WINDOW mass 0.69 vs 0.60; FRAG 0.99 vs 0.58), so coop_bot.decide returns "act", not "queued". The shipped model does the same.
- OTHER regex: 9/9 found, 0 false.
- csv3_004: three readers say ENTRY (accept = {ENTRY}), target door/north. Both models pick VAULT_WINDOW (re-trained family mass 0.975, shipped 0.997). The matcher gives door/north. It counts as near only through the assault family.

**Qualifications the write-up needs**
- The overall joint is almost the product of the published marginals (0.907 x 0.967 = 87.7%). Only one line (sttv3_023) fails both, so there is no hidden correlation. The 18 joint failures are 14 intent misses plus 5 place misses minus that overlap.
- 12 of the 14 intent misses are NONE picks ("say again?" or ignore); 2 are wrong actions (csv3_037 RAPPEL, sttv3_032 VAULT_WINDOW). Three of the 18 failures are non-order lines where the bot does nothing and the wrong place is only a contact (r6v3_039, r6v3_045, sttv3_036).
- stt is held out only for the matcher; the classifier is leave-one-author-out for all three authors. stt's 78% is mostly the classifier on STT-garbled lines: 9 of its 11 joint failures are intent misses, and the matcher is 47/50 there. It is the only author held out for both components, but the gap to r6/cs is persona difficulty, not a tuning effect.
- 39/50 has a Wilson 95% interval of [64.8, 87.2]. stt stays at 39/50 at any fixed family threshold from 0.52 to 0.62.
- With the only pre-registered matcher (rules v1) the joint is 119/150 = 79.3% (r6 42, cs 40, stt 37), so the 88.0% all-author figure is after tuning on r6 and cs.
- "Re-training is needed" survives jointly: re-trained minus shipped on the joint indicator is +7.3 points [+2.0, +13.3] (paired bootstrap, 4000 reps).

**The conditional figures (124 and 122)**
- 124/150 = 82.7% reproduces only under this reconstruction: the line fails when the bot's pick is not NONE and the matcher's primary carries a role.
- It drops 8 lines: r6v3_000 and csv3_027 (SMOKE, role from); r6v3_021 and csv3_048 (BREACH, role status); csv3_039 (ENTRY, role status); r6v3_003, r6v3_027 and sttv3_039 (WAIT, role not).
- The three WAIT lines need no place: decide's WAIT branch only clears the queue. Without them it is 127/150 = 84.7%.
- The figure also depends on which sentence of locations.h a planner follows: line 46 ("the bot is not sent to a place with a role") or line 61 ("primary: the target the bot acts on"). It is a conditional number, not a measured one.
- 122/150 = 81.3% is that 124 minus the two early-acting on-signal lines; near and exact with timing only is 130/150 = 86.7%.
- The on-signal miss rate is not new: results_timing_rule.json shows 21/24 kept on the v1 lines.

*Recommended action.* Reporting only; change no rule, vocabulary, spec, seed, label or the ON_SIGNAL regex.

1. **scripts/coop/eval_v3.py**: add a section "D. JOINT (defined after the v3 results were seen; nothing tuned on it)". For re-trained ens3 (top and family gate) and shipped raw, print near AND matcher-exact for all lines, per author, and on the 126 order lines. Add the count where ON_SIGNAL (timing_rule.py) also agrees with the readers' timing. Add per-author near rows to section C. Store these in results_v3.json. Log the new eval_v3.py and eval_v3.log hashes in frozen.txt with a comment that the joint metric is post-hoc.

2. **HANDOFF.md section 4, after the cross-validation table, and the future "v3" sections of COOP-BOT.md and DEBERTA-BOT.md**: add this sentence.
"Intent (near) and exact place on the same line: 88.0% (132/150) for the re-trained ensemble with matcher rules v2, 80.7% (121/150) for the shipped v2 bot, difference +7.3 [+2.0, +13.3]. Per author r6 94 / cs 92 / stt 78 (39/50, 95% CI 65-87). stt is the only author held out for both the matcher rules and the classifier, and its gap is mostly the classifier on STT-garbled lines (near 82%). With the pre-registered rules v1 the joint is 79.3% (119/150). 12 of the 14 intent misses are 'say again', 2 are wrong-family actions. The on-signal regex finds 10 of the 12 on-signal v3 lines; on r6v3_012 and csv3_010 the bot acts at once."

3. **Do not print 124/150 or 122/150 as measured rates.** They depend on the unresolved planner contract for role-carrying primaries (locations.h lines 46 vs 61, the other finding). If they are quoted, state the definition and exempt WAIT picks (127/150 = 84.7%).

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

The arithmetic stands; the weight and part of the framing do not.

**What holds**
- Re-trained CV ens3 (family gate) with matcher rules v2: intent near-correct AND primary equal to the readers' place on 132/150 = 88.0% (r6 47, cs 46, stt 39 of 50 = 78.0%); order lines 111/126 = 88.1%.
- Shipped v2 classifier: 121/150 = 80.7%.
- The ON_SIGNAL regex finds 10 of the 12 on-signal v3 lines; on r6v3_012 and csv3_010 the pick is an action, so the bot would act at once.
- csv3_004 is counted near with pick VAULT_WINDOW against truth ENTRY at the north door.
- HANDOFF section 4 and eval_v3.log give no joint row and no per-author classifier row.

**Why it is not major**
1. No number in HANDOFF is wrong and none is presented as an end-to-end rate. HANDOFF is a snapshot; the v3 write-up is still to do (section 5, step 5).
2. The joint follows from the two failure lists eval_v3.log already prints with ids: 150 - (5 + 14 - 1) = 132, stt 50 - (3 + 9 - 1) = 39. Only sttv3_023 is on both lists.
3. The two error sets are independent: 90.7% x 96.7% = 87.6% against 88.0% observed. The stt 78% is the classifier's 41/50 = 82% on stt times the matcher's 47/50.
4. "Not both right" is mostly not "acts at the wrong place". Of the 18 failures:
   - 12 are orders the bot does not act on;
   - 2 are wrong-family actions, already reported as 1.3%;
   - 3 are place errors on non-order lines where the bot does nothing (r6v3_039, r6v3_045, sttv3_036);
   - 1 is an order executed with no place found (sttv3_045).
5. The timing misses are a documented limit of a v1 component that v3 did not change. COOP-BOT.md "The two slots" gives 21/24 kept, acts early on 3/24, and lists "the second I say now" among the misses; r6v3_012 is "the second I say so". v3 makes no timing claim.
6. The 82.7% and 81.3% figures depend on another finding's reading of the role / unsure contract and count a "confirm" as a failure. They reproduce under that definition (132 - 8 = 124, - 2 = 122) but are conditional.

**A correction to the finding's own headline**
The 88.0% joint uses rules v2, which were tuned on r6 and cs, so by section 6 it is an after-tuning number. With the frozen rules v1 the joint is 119/150 = 79.3% (r6 42, cs 40, stt 37). The only untuned joint with rules v2 is stt, 39/50 = 78% (n=50, roughly 65-87%).

*Recommended action.* Reporting only; no rule, vocabulary, spec, seed or label change.

**Smallest action:** add one row and one sentence to HANDOFF.md section 4 and to the future "v3" section of COOP-BOT.md, taken from the existing logs:

"Intent and place both right on the same line (a post-hoc metric, defined after the lines were read): 132/150 = 88.0% with matcher rules v2 and the cross-validated re-trained ens3, family gate. This is after tuning for r6 and cs (47/50, 46/50). On the held-out author stt it is 39/50 = 78% (classifier 41/50, matcher 47/50; n=50, roughly 65-87%). With the frozen rules v1 it is 119/150 = 79.3%; with the shipped v2 classifier, 121/150 = 80.7%. Of the 18 failures, 12 are orders the bot does not act on, 2 are wrong-family actions, 3 are place errors on non-order lines and 1 is an order executed with no place found. The timing regex (unchanged since v1) misses 2 of the 12 on-signal v3 lines, 'the second I say so' and 'the moment I call it'; those orders would execute at once."

**Optional:** add a per-author row for the classifier on the v3 lines (98 / 92 / 82 near) and the joint row to section C of /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/eval_v3.py. That file is hashed in frozen.txt as written before any v3 line was read, so the edit must be logged there as a post-hoc reporting addition.

Do not use 82.7% or 81.3% as headline numbers until the role / unsure planner contract (the other finding) is settled.

### bot-integration #4: annot/v3/author_r6_ann1.json and author_r6_ann2.json are the same file: the r6 v3 lines have one annotator counted twice

Reviewer: major, data. Affects: HANDOFF section 4 "3 автора по 50 строк, по 2 аннотатора на автора"; the absolute v3 intent numbers by at most one line each (83.3 -> 82.7 and 90.7 -> 90.0 near; wrong family 3.3 -> 4.0 and 1.3 -> 2.0); the +10.7 / +11.3 differences are unchanged.

**Verifier (reproduce): partly, minor; reproduced: yes; touches frozen: yes**

Every measurable part of the finding holds; the causal label "one annotator counted twice" is not established.

What holds:
- annot/v3/author_r6_ann1.json and author_r6_ann2.json are byte-identical (11014 bytes, SHA-256 07378aec...a7166). frozen.txt lines 134-135 record that hash twice at the 2026-10-03T21:00:44 freeze, so it has been this way since before any v3 result.
- coop_v2._item accepts an intent when 2 of 3 reads contain it. The r6 author gives no "ok" list, so on the 50 r6 lines every annotator "ok" enters the accept set only because the same content is read twice.
- 7 accept sets are wider for that reason: r6v3_003, 012, 019, 025, 027, 043, 046.
- Only r6v3_003 changes a score (truth NONE, pick WAIT in the shipped bot and in both re-trained gates).
- Majority intent, target truth, unknown_modifier, timing and reference do not change (author equals annotator on all 50). Training uses only the majority intent. So the matcher numbers (88.0 / 96.7 / 94) and the trained models are unaffected.

Worst case, if the r6 annotator is counted once (accept = author ∩ annotator):

| | as reported | counted once |
|---|---|---|
| shipped, raw line | 125/150 = 83.3%, 5 wrong family (3.3%) | 124/150 = 82.7%, 6 (4.0%) |
| shipped, names stripped | 81.3% | 80.7% |
| re-trained ens3, top gate | 135/150 = 90.0%, 2 (1.3%) | 134/150 = 89.3%, 3 (2.0%) |
| re-trained ens3, family gate | 136/150 = 90.7%, 2 (1.3%) | 135/150 = 90.0%, 3 (2.0%) |

The reviewer did not give the top-gate row. Out-of-fold thresholds do not move and no pick changes. The differences stay +10.7 [+3.3,+18.7] and +11.3 [+4.0,+19.3]; strip minus raw stays -3.3 [-8.0,+0.0].

What does not hold as stated:
- The files cannot show whether one reading was written twice or two annotators agreed on everything. All six v3 annotation files share one serialisation, so byte identity only means content identity.
- The two r6 files have different write times (21:00:21 and 21:00:32), like the cs pair (10 s apart) and the stt pair (16 s apart). That fits two separate completions at least as well as a copy.
- The other two v3 pairs differ on only 2 of 50 lines each, apart from one stt annotator's systematic "reference" reading (30 lines). At that 96% per-line rate a fully identical pair has roughly a 13% chance.
- "Only this pair" is true for hashes only. annot/v2/author_cs_ann1.json and ann2 parse to the same dict on 40/40 lines (13 non-empty ok lists) but are formatted differently (4286 vs 3489 bytes), so a hash scan cannot see them. This is a precedent for full agreement between two separately written files; if it is instead the same defect, counting it once costs one older line (v21 cross-validation family gate 437/483 = 90.5% to 436/483 = 90.3%).
- So 82.7 / 89.3 / 90.0 are a lower bound, not a correction. On the two analogous negated lines by the other authors, the second annotator agreed with "ok: WAIT" once (sttv3_012) and not once (csv3_008).

No workflow log for wf_04800970-338 exists on this machine to settle the cause. No headline conclusion changes, hence minor.

*Recommended action.* 1. Settle the cause first. On the machine that ran workflow wf_04800970-338, check its transcript for whether two separate annotator agents returned for author r6 or one result was written to both file names.

2. Disclose, with no label change:
- HANDOFF.md section 4, after line 98, add: "For author r6 the two annotator files are byte-identical (sha256 07378aec...; frozen.txt lines 134-135), so the r6 accept sets rest on one distinct reading besides the author. If that reading is counted once, the v3 intent numbers are: shipped 82.7% near / 4.0% wrong family; re-trained 89.3 / 90.0 near (top / family) and 2.0% wrong family. The differences (+10.7 / +11.3 and their intervals), the matcher numbers and the trained model do not change." Report the two result tables as ranges: 82.7-83.3, 89.3-90.0 / 90.0-90.7, wrong family 3.3-4.0 and 1.3-2.0.
- scripts/coop/frozen.txt: append a dated comment line stating the same, and that annot/v2/author_cs_ann1.json and ann2 are content-identical on 40/40 lines (lower bound for the v21 cross-validation: 90.3% instead of 90.5%).

3. Only if step 1 shows a single annotator: have one fresh annotator read blind/v3/author_r6_lines.json under blind/spec_v3.json, replace annot/v3/author_r6_ann2.json, record the new hash in frozen.txt as written after the v3 results were seen, and re-run "COOP_TAG=v3 python eval_v3.py".
- This can only narrow accept sets on the 7 listed lines.
- It cannot change any majority intent or target truth, because the author and ann1 already agree on all 50. The matcher numbers, including the held-out stt 94%, cannot move.

4. Do not change coop_v2.py scoring, the rules, the spec or the seeds for this.

On touches_frozen: set true because step 3 replaces a hashed label file after results were seen. Step 2 alone touches nothing frozen.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

The facts hold; the interpretation and the size do not.

TRUE:
- annot/v3/author_r6_ann1.json and author_r6_ann2.json are byte-identical, and were already identical in the archive from the Windows machine.
- frozen.txt lines 134-135 record the same hash twice with no remark. No document mentions it.
- For the 50 r6 v3 lines the second annotation therefore adds no information: all 7 extra "ok" intents enter the accept sets on one reading.
- Worst case is exactly one line, r6v3_003 (truth NONE, both models pick WAIT).

NOT ESTABLISHED: "the same file, one annotator counted twice". The tree cannot tell a duplicated annotator from two same-model annotators that agreed on every field.
- All six v3 annotation files come from one serializer (json.dump indent=1, CRLF), so identical content gives identical bytes.
- The two r6 files were written 11 s apart, like the cs pair (10 s) and the stt pair (16 s). That fits two separate completions better than one result stored twice.
- There is a precedent: the v2 cs pair agrees on every field of all 40 lines, including 13 non-empty ok lists, in two differently formatted files (4286 vs 3489 bytes). The v3 cs pair agrees on 48/50 lines.
- Using the other pairs' per-line agreement, the chance of 50/50 from independent annotators runs from about 0 to 13%. So duplication is plausible but unproven; the workflow record (wf_04800970-338) is not on this machine.

OVERSTATED: the reviewer's recount is a lower bound, not the corrected number.
- It applies "author + one annotator, both must accept". Authors never give ok lists (0 non-empty in all nine author files), so this drops every alternative on r6 lines, a stricter rule than the other 100 v3 lines get.
- In the other 8 pairs a second annotator confirms 192/236 ok entries (81%), and 34/36 (94%) of the "NONE, ok WAIT" kind that r6v3_003 depends on. The expected effect is well under one line.

UNAFFECTED either way:
- Intent majority and target truth on all 50 r6 lines (author and annotation agree on every field except ok), so the matcher numbers 88.0 / 96.7 / 94 stand.
- Training, which uses only the majority label.
- The out-of-fold thresholds (recomputed, unchanged).
- The differences +10.7 [+3.3,+18.7] and +11.3 [+4.0,+19.3], the strip-vs-raw -3.3, and the older-lines comparison.

The one unsupported sentence is HANDOFF.md line 98, "по 2 аннотатора на автора", which is unverified for r6. The general caveat that annotators are agents of one model family is documented for v1/v2 (COOP-BOT.md lines 57 and 501) but not yet for v3.

*Recommended action.* Documentation only; no change to labels, rules, vocabulary, spec or seeds.

1. scripts/coop/frozen.txt: append a dated comment: "annot/v3/author_r6_ann1.json and author_r6_ann2.json are byte-identical (07378aec...). Not checked at freeze time whether wf_04800970-338 ran two annotators that agreed on all 50 lines or stored one output twice. Worst case (r6 ok lists dropped): shipped 82.7 near / 4.0 wrong family; re-trained 89.3 / 90.0 near, 2.0 wrong family; differences unchanged."

2. HANDOFF.md line 98, and the v3 section of COOP-BOT.md when it is written: replace "по 2 аннотатора на автора" with a sentence saying that the two r6 annotation files are byte-identical, so r6 accept sets rest on one reading; that the bound is one line (r6v3_003: 83.3 -> 82.7, 90.0 / 90.7 -> 89.3 / 90.0, wrong family +0.7 point each); and that the differences and matcher numbers are unaffected. Carry the "agents of one model family" caveat into the v3 section.

3. On the Windows machine, open the wf_04800970-338 record and check whether the two r6 annotator runs are distinct. If they are, say so and nothing else changes.

4. Only if step 3 shows a duplicate: either state that r6 has one annotator, or have one more blind annotator read blind/v3/author_r6_lines.json under spec_v3.json, record the new hash in frozen.txt as changed after results were seen, and re-run COOP_TAG=v3 python eval_v3.py. That option replaces a label file, so it does touch frozen material; it does not touch the held-out stt matcher number.

I set touches_frozen to false because steps 1-3 change no frozen material.

### bot-integration #5: The "other" slot is not kept with a queued order: at execution the planner gets a bare object

Reviewer: minor, bot-logic. Affects: coop_bot.py decide() record, bot_brain.h Decision at Action::Execute; the planner contract for queued orders.

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The finding holds as stated, in both the Python bot and the C++ engine.

- **What is lost.** The queue keeps the intent and the PlaceRecord only (`self.pending, self.pending_places = intent, places` at coop_bot.py:177; `pending_` / `pending_places_` at bot_brain.cpp:198-199). The regex slot "other" is recomputed per line (coop_bot.py:158, bot_brain.cpp:98) and never stored.
- **What the planner sees on Execute.** `other` is the GO line's own slot (false), and `executed_places` is the queued PlaceRecord, whose target has flag null because the regex slot is never written into places. For "open the other window on my go" followed by "go", that is `[window, no qualifier, no flag]`.
- **The asymmetry is real.** When the matcher's rule 5c fires ("i got north door, you take the other one on my go"), the "other" target is inside the PlaceRecord and survives the queue.
- **Partial mitigation the reviewer did not mention.** "Hold / watch / take the other X" is classified as the flat intent HOLD_OTHER_ANGLE, which the queue does keep (dialogue rows 14-15 and 39-40). The loss affects only other intents, which are 29 of the 41 lines where the OTHER regex fires.
- **Not documented as intended.** bot_brain.h says only that "other" "is reported as a slot for the planner" and that "a queued order keeps its places and executes with them". HANDOFF.md:96-97 says the same about places. COOP-BOT.md:512 defines the planner input as {intent, timing, reference}. Nothing says the reference is dropped at Execute or that the game must cache it from the Queued decision.
- **Not introduced by v3.** The queue has only ever stored the intent; v3 added places and left the slot out.
- **No reported number moves.** 0 of 633 lines (and 0 seeds in all four seed files) combine on-signal with "other", and eval_v3.py, v3_shipped.py and v3_noharm.py do not import coop_bot.
- **Consequence is a contract gap, not a measured error.** The planner does not exist in this repo, so "opens the nearest window" is what the documented default implies (cpp/coop_intent/README.md:153-154: "the marker, or the nearest one"), not something observed.

*Recommended action.* **Fix in the bot layer only**
- `scripts/coop/coop_bot.py`: add `self.pending_other`. Set it with `pending` and `pending_places` at line 177, clear it wherever they are cleared (lines 160, 170, 174), and return it on execute as `rec["executed_other"]`. While there, also return the executed intent (`rec["executed"]`): the Python record has only intent=GO_NOW, whereas C++ has `Decision::executed`.
- `cpp/coop_intent/include/coop_intent/bot_brain.h` and `src/bot_brain.cpp`: add `bool pending_other_`. Set it at lines 198-199, clear it in `drop_pending` and `Reset()`, and add `bool executed_other` to `Decision`, filled at line 192.
- `cpp/coop_intent/tools/gen_tests.py`: add to the `decide_tests` script ("open the other window on my go", OPEN=0.9) then ("go", GO_NOW=0.95), plus one rule 5c on-signal line, and emit `executed_other`.
- `cpp/coop_intent/tools/coop_cli.cpp`: compare `executed_other` in `RunDecideTests` (about line 423) and in the dialogue check (about line 331).
- Regenerate `decide_tests.jsonl` and `dialogue.jsonl`, and record the new hashes of coop_bot.py, bot_brain.{h,cpp}, gen_tests.py and coop_cli.cpp in frozen.txt.

**Do not** implement the reviewer's alternative (setting flag "other" on the primary target) inside locations.py or locations.cpp. That is a matcher rule change after the blind lines were seen, and it would change the 8570 location records.

**If the code is not changed before the UE port**, add this sentence to the v3 write-up and to the `Decision` comment in bot_brain.h: "On Execute, `other` is the GO line's own slot. The queued order's 'other' slot is not kept unless it came from the matcher (flag "other" in `executed_places`) or the intent is HOLD_OTHER_ANGLE; the game must remember `Decision.other` from the Queued decision. No test line combines on-signal with 'the other one' (0 of 633), so this path is unmeasured."

### bot-integration #6: The generated decide and dialogue tests miss most queue-and-place regressions; Decision::executed is never compared; the current coop_cli crashes on the v1 bot's test files

Reviewer: minor, cpp. Affects: The strength of "C++ equals Python on all checks" for the v3 queue and place logic (the code is right today: my 88 steps agree); cpp/coop_intent/README.md statements about the v1 bot.

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

All three headline claims hold; the code itself is correct today, so this is a test-coverage and documentation gap, not a defect in the v3 numbers.

(1) The shipped decide_tests.jsonl (52 steps) and dialogue.jsonl (77 lines) cover every branch of Decide once, but not the combinations of branch x queue state x places. My own mutation run: 6 of 8 behaviour-changing edits to BotBrain::Decide still pass 52/52 and 77/77. The shipped decide script has, under both gates, 0 re-queues, 0 "say again" while an order is queued, 0 negated lines while places are queued, 0 negated lines under the threshold, 0 GO lines naming a place with nothing queued. The shipped dialogue has 0 rows with action "negated" at all, its only say_again (row 75) comes with nothing queued, and no "go" row names a place.

(2) Decision::executed (bot_brain.h:51, set at bot_brain.cpp:191) is read nowhere: coop_cli's chat uses its own pending_before = brain.Pending() (coop_cli.cpp:539,548), no check compares it, and the Python record (coop_bot.py:183-185) has no field for the order that fired, so the test files cannot carry it and a coop_bot_log.jsonl "execute" line names only GO_NOW and executed_places. After Decide() the brain's Pending() is already -1, so Decision::executed is the only way a game integration learns which order fires, and it is the one output no check exercises.

(3) coop_cli built from the current source aborts (exit 134) on --decide-tests and --dialogue with models/coop-deberta-v3-base/cpp. Those test files are dated Sep 29 and have no places / executed_places / pending_places keys; coop_cli.cpp:332-333 and 424-426 read them through nlohmann's const operator[], which for a missing key is undefined behaviour in a Release build (json.hpp:22187-22189, the assert is compiled out). Here it shows up as an uncaught type_error.305; the first dialogue row even printed "ok" from garbage before the abort. README.md:65 "the v1 bot passes the same checks" is therefore false for two of the checks.

Corrections to the reviewer's wording:
- The shipped dialogue does contain one re-queue (row 33 "plant the bomb on my count" queued PLANT, row 34 "wait for my call" queued FRAG, row 35 "execute"). Neither line names a place, so replacement of the queued intent is covered and replacement of the queued places is not.
- README.md:14 says the v1 bot "still runs", which is true: v1 chat, --golden (754/754), --tokenizer-tests and --gate-tests all work. Only line 65 is wrong.
- The "negated keeps stale places" mutation is visible only through the public BotBrain::PendingPlaces() accessor while Pending() is -1, never in a Decision; the other four detectable mutations change Decision outputs.

Not documented anywhere as known or intended: HANDOFF.md section 5 step 5 lists a README update as pending, but nothing in HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md, the cpp README or frozen.txt mentions the v1 test files or these coverage limits. frozen.txt:146 records only "decide 52/52, dialogue 77/77". The gen_tests.py and README wording "every branch of the decision" is accurate as written. The same gaps will carry into the test files generated for the v3 model (HANDOFF section 5 step 3) and into the UE5 automation test that reuses them.

*Recommended action.* No change to rules, vocabulary, spec, seeds or labels. Record the edits below in scripts/coop/frozen.txt as test and tooling changes, and make them before generating the v3 model's test files (HANDOFF section 5 step 3).

1. cpp/coop_intent/tools/gen_tests.py, decide_tests(): add sequences for
   - a negated order while an order with a place is queued;
   - a second "on my go" order naming a different place, then GO;
   - a sub-threshold line while an order with a place is queued, then GO;
   - a leading-negation line under the threshold while an order is queued;
   - a GO line naming a place with nothing queued.
   My sequences are in SCRATCH/myseq.py (list "extra").

2. scripts/coop/coop_bot.py:183: add the fired order to the record, e.g. "executed": the pending intent on action "execute", else None. Write it into the decide and dialogue rows in gen_tests.py, and compare it with Decision::executed in RunDecideTests and RunDialogue in cpp/coop_intent/tools/coop_cli.cpp.

3. cpp/coop_intent/tools/coop_cli.cpp:332-333 and 424-426: do not read optional or newer keys through const operator[]. Use contains() or at() inside a try block and print "test file predates places: regenerate with gen_tests.py", returning 1.

4. Either regenerate the v1 bot's files (python scripts/coop/export_cpp.py models/coop-deberta-v3-base --config-only; python cpp/coop_intent/tools/gen_tests.py models/coop-deberta-v3-base) and re-run the checks, or change cpp/coop_intent/README.md:65 to: "On the shipped v2 ensemble. The v1 bot's test files predate the place fields: its tokenizer, gate and golden checks pass; its decide and dialogue files must be regenerated with gen_tests.py before those checks run."

5. In the v3 write-up, wherever "decide 52/52, dialogue 77/77" is cited for the queue and place logic, say what those tests cover: each branch once, plus one queued-with-place, callout, GO path and one WAIT drop. They do not cover re-queueing, say-again or negation while a place is queued.

### bot-integration #7: Switching the default model as HANDOFF step 3 says leaves an existing build on v2, and coop_cli never prints which model it checked

Reviewer: minor, portability. Affects: HANDOFF section 5 step 3 and the vocabulary-change recipe; the risk of reporting v2 parity results as v3.

**Verifier (both): partly, minor; reproduced: yes; touches frozen: no**

The core finding holds; one sub-point and one suggested fix need correcting. Nothing here changes a v3 number in HANDOFF section 4: it is a trap in the next steps (section 5).

**What holds**
- **Stale CMake cache.** `COOP_MODEL_DIR` is a CACHE variable without FORCE (`cpp/coop_intent/CMakeLists.txt:24`) and is compiled into `coop_cli` as `COOP_DEFAULT_MODEL_DIR` (line 60). In a build directory configured earlier, editing the default changes nothing: the cache and the binary keep the v2 path.
- **This machine is in that state.** `cpp/coop_intent/build/CMakeCache.txt:205` already caches the v2 path.
- **No success path names the model.** `coop_cli` prints `m.dir` only in the LoadConfig error (`tools/coop_cli.cpp:609`). The check summaries and the chat "ready" line (line 513) do not name the bot. The Python bot does print the directory name at start (`coop_bot.py:193`).
- **Consequence.** After the switch in step 3, the six commands as written in HANDOFF section 3 (lines 64-69, no `--model-dir`) pass against the v2 files in an existing build. Only the line counts tell the bots apart.
- **Not documented.** HANDOFF line 150 says only to change the default in `CMakeLists.txt` and `coop_bot.py`. No document mentions `-DCOOP_MODEL_DIR` or a fresh build directory.
- **Mitigation already in the recipe.** HANDOFF line 149 tells the reader to run the six checks with an explicit `--model-dir` before the switch, so the documented order is safe.

**Correction: `shipped.py` must not follow the switch**
- The v2 default is hard-coded in `export_cpp.py:37`, `check_onnx.py:19`, `gen_tests.py:31` and `shipped.py:14`, as the reviewer says.
- `shipped.py` is different from the other three: it is the v2 baseline behind `results_v3_shipped.json` (which records model `coop-deberta-v3-ens3-v2`) and so behind the 83.3% and +10.7 / +11.3 figures.
- Pointing it at v3, as "take the default from one place" would do, makes `v3_shipped.py` overwrite that baseline with a model trained on the same 150 lines.
- Only its docstring ("the model directory coop_bot.py uses") goes stale after the switch.
- The other three, run without an argument after the switch, write into the v2 bot's `cpp/` directory. Every documented recipe passes the directory explicitly.

**`COOP_TAG` and the golden lines**
- `export_cpp.py:115-116` takes the golden lines under `COOP_TAG`: 754 lines with no tag, 762 with `v21` (the shipped file), 1062 with `v3`.
- An untagged export of the v3 bot leaves out the 150 place-naming study lines and the 150 location seeds. This reduces parity coverage; it does not produce a wrong result.
- The script already prints the golden line count; it does not print the tag.
- HANDOFF step 3 carries `COOP_TAG=v3` on all three commands, so the recipe as written is correct.

**`locations.py --dev`**
- It prints "254 dev lines, 5 with a primary target the line's author would not accept" and exits 1.
- No document, log or `frozen.txt` entry records 5 as the baseline.
- The three lines of the vocabulary-change recipe (HANDOFF 162-164) are not chained, so the exit code blocks nothing. A reader still cannot tell a regression from the shipped state.

*Recommended action.* No fix was applied. None of the items below touch the matcher rules, vocabulary, spec, seeds or labels.

1. **`HANDOFF.md` section 5 step 3 (line 150).** Replace the sentence with: "Затем поменять модель по умолчанию в `CMakeLists.txt` и в `coop_bot.py`. В уже сконфигурированной папке сборки значение `COOP_MODEL_DIR` остаётся в кэше: пересобрать с `cmake -S . -B build -DCOOP_MODEL_DIR=<...>/models/coop-deberta-v3-ens3-v3/cpp` либо удалить `build`. `shipped.py` не менять: это базовая модель v2 для `v3_shipped.py` / `results_v3_shipped.json`." Add the same cache note to the "Regenerating" section of `cpp/coop_intent/README.md`.
2. **`cpp/coop_intent/tools/coop_cli.cpp`.** After LoadConfig succeeds (line 609), print one line in every mode with `m.dir`, the label count, gate and threshold. Record the new hash in `frozen.txt`.
3. **Default bot directory.** Have `export_cpp.py:37`, `check_onnx.py:19` and `gen_tests.py:31` take the default from `coop_bot.MODEL_DIR`, or require the directory argument. Do not include `shipped.py:14`: keep it pinned to v2 and change its docstring to say it is the v2 baseline of the v3 study, not "the directory coop_bot.py uses".
4. **`scripts/coop/export_cpp.py:123`.** Add `COOP_TAG` (`V.TAG`) and the count of v3 study lines to the final print. Optionally warn when `bot_config.json` `trained_on` names a different seed file than `V.SEED_FILE`.
5. **`locations.py --dev` baseline.** Add a sentence to HANDOFF after line 165 and to the `locations.py` docstring: "the shipped rules fail 5 of 254 dev lines (4 other-sense, 1 two-objects) and `--dev` exits 1; a vocabulary change must not add to that list." Do not edit `locations_dev.json` or the rules to make it exit 0: that would touch frozen material.

### bot-integration #8: Nothing reconciles the intent with the matcher's target: VAULT_WINDOW at a door, a correction blocked by the leading-negation guard, GO with a place and no order

Reviewer: minor, bot-logic. Affects: What the planner must handle on its own; the "near" score counts a wrong-object action as correct on csv3_004. The live examples are from the v2 model; the final v3 model does not exist here.

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

All three parts reproduce, and no document says what the planner does when intent and target disagree. No reported number changes.

Bot.decide (coop_bot.py:152-186) and BotBrain::Decide (bot_brain.cpp:169-204) return the classifier's intent and the matcher's PlaceRecord independently. HANDOFF.md:157 only says the PlaceRecord goes to the planner "as is"; COOP-BOT.md, DEBERTA-BOT.md and cpp/coop_intent/README.md have no v3 or planner-contract text.

**(1) Intent contradicts the object.**
- On the blind lines this is 1 of 150 for the leave-one-author-out re-trained ensemble: csv3_004, VAULT_WINDOW 0.90 with primary door north, truth ENTRY. The shipped model has 2: csv3_004 and csv3_031 (RAPPEL at basement, already counted wrong-family).
- csv3_004 is "near" only through the documented family rule. The "exact ok" column in eval_v3.log (89.3 / 90.0 re-trained, 82.0 shipped) already excludes it.
- Counting it as a miss gives near 89.3 / 90.0 against 82.7, so the reported differences do not move.
- The live examples are real but come from the v2 model, which never saw place lines. "breach the sofa" and "rappel to the basement" are nonsensical orders, not model errors; they only show that no sanity check exists.
- Whether the final v3 model still reads "through the X door" as VAULT_WINDOW is unverified, because that model is not on this machine. The v3 seeds have "go through the {side} window" under VAULT_WINDOW and no "through the ... door" line under ENTRY.

**(2) The negation guard cancels corrections.**
- The guard is deliberate, tested and fail-safe, and predates v3: coop_bot.py:41-45, DEBERTA-BOT.md:260-265, and gen_tests.py:142 pins "don't worry, breach it" as "negated: drops the queued order".
- What is new in v3 is that the matcher is built to resolve "don't X, take Y" to Y (locations_dev.json:612), so the two layers now encode opposite readings of the same line.
- The guard runs before the threshold (coop_bot.py:159 vs 162; bot_brain.cpp:182 vs 185), so a low-confidence negated line also drops the queue.
- The classifier itself also drops such corrections: "don't smoke red stairs, smoke blue" gives NONE 0.99. Relaxing the guard alone would not make them work.
- On the 633 study lines, 14 start with a negation (truth NONE 11, WAIT 3; 2 are v3 lines). The guard fires on 0 for the re-trained ensemble under both gates, using the unthresholded pick as the bot does. score() never applies the guard anyway.
- No blind line is a "don't X, do Y" correction; the four v3 corrections start with "not", "no" or "forget".

**(3) GO with a place and nothing queued.**
- GO_NOW with an empty queue returns action "go" plus the line's places.
- No blind line with truth or pick GO_NOW has a matched place. The decide-tests cover GO plus a place only when an order is queued.

*Recommended action.* No reported number needs to change. Write the gap into the planner contract.

**1. Add a "Planner contract / known limits" paragraph** to the v3 section still to be written in /Users/t.losiev/Documents/models_training/project_synth/COOP-BOT.md (HANDOFF step 5), and to the "Game integration" bullet in /Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/README.md. Suggested text:

"The bot returns the intent and the PlaceRecord independently and does not reconcile them. The planner must:
(a) treat an intent whose object type contradicts the primary target (VAULT_WINDOW at a door, BREACH at furniture, RAPPEL at the basement) as a confirmation or re-map it within the family. On the blind lines this happens on 1 of 150 (csv3_004, counted near by the family rule, not exact).
(b) know that a line starting with don't / never / no need to is cancelled by the negation guard even when it carries a correction ("don't go through the main door, take the east window" gives action negated with primary east window), and that the guard is checked before the threshold, so such a line also drops a queued order. The guard fired on 0 of the 633 study lines; no blind line is a "don't X, do Y" correction, so this case is unmeasured.
(c) define action "go" with a place and nothing queued (ignore the place, or treat as MOVE_TO)."

**2. Add one line to HANDOFF.md section 7** (default decisions): corrections phrased "don't X, do Y" currently stand down.

**3. If the owner wants code instead of documentation**, change only decide() in /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/coop_bot.py (lines 159-172) and BotBrain::Decide in /Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/src/bot_brain.cpp (lines 182-193). Then regenerate the decide and dialogue parity files with gen_tests.py and record the new hashes in frozen.txt.
- Note that the classifier alone also reads such corrections as NONE, so a guard change is not sufficient.
- Do not fix (1) by adding "through the ... door" ENTRY seeds or by touching the matcher: that changes frozen material.
- Any score recomputed with a reconciliation rule derived from csv3_004 must be marked "after tuning".

### bot-integration: checked and found right

- Python Bot.decide and C++ BotBrain::Decide agree on my own 15 multi-step dialogues under both gates (88 steps; intent, confidence within 1e-12, action, queued order, other, places, executed places, queued places): 'decide tests, 88 steps over both gates: ... 88/88' (SCRATCH/seq.py -> SCRATCH/modeldir/cpp/decide_tests.jsonl -> scratch-built coop_cli --decide-tests)
- In both engines: a say-again line that names a place leaves the queued order and its places intact; a NONE callout with places leaves them intact; GO executes with the queued order's places, not the GO line's; a queued line naming two places keeps both targets and the primary; a negated order clears the queue and its places; WAIT clears both (seq.py output, C++ equal)
- C++ LocationMatcher equals locations.record on 300,094 generated place-heavy lines (2 seeds x 150,047; about 135k name a place, 97k more than one; every role and flag occurs): 150047/150047 twice (SCRATCH/fuzz_loc.py + coop_cli --location-tests)
- C++ token positions first/last (not compared by the shipped tests) equal Python's on 150,047 fuzz lines and on 40,000 targeted "other one" / correction lines, 9,236 of which carry the 'other' target (patched scratch coop_cli; SCRATCH/fuzz_other.py): all equal
- The shipped location_tests.jsonl has 8570 lines; 1371 name a place and 196 more than one; 8025 are the tokenizer stress lines (counted from the file)
- export_cpp.py --config-only on a scratch copy of the v2 bot dir, with and without COOP_TAG=v3, reproduces the shipped intent_config.json (identical after stripping CR) and vocab.tsv byte for byte: the shipped C++ config matches the current locations.json and regexes
- The whole step-3 pipeline runs on this Mac under COOP_TAG=v3 on a single-member scratch bot (v2 seed0): export_cpp.py (ONNX export works with torch 2.14.1, 1062 golden lines) -> check_onnx.py (same argmax 1062/1062, max |dp| 9.2e-6) -> gen_tests.py -> six coop_cli checks: tokenizer 9231/9231, location 8563/8563, gate 2938/2938, decide 52/52, golden 1062/1062 (max |dp| 9.18e-06), dialogue 77/77
- gen_tests.py run on the Mac writes a decide_tests.jsonl byte-identical to the shipped one (cmp)
- gen_tests.py, check_onnx.py and export_cpp.py --config-only do not depend on COOP_TAG (only the golden line set of a full export does); no label count is hard-coded: labels, families, threshold and gate come from bot_config.json
- The bot's leading-negation guard fires on 0 of the 633 lines with the cross-validated re-trained ensemble under either gate, so the classifier-only scores in eval_v3.log section C are what the bot does at the decision level (SCRATCH/endtoend.py: near 136 / wrong family 2 on v3 with and without the guard)
- On the 150 v3 lines the ON_SIGNAL regex finds 10 of 12 on-signal lines with 0 false hits and the OTHER regex finds 9 of 9 with 0 false hits (SCRATCH/interplay.py)
- Stored files reproduce the headline counts I built on: shipped near 125/150, re-trained family gate near 136/150 (top 135/150), matcher exact 145/150 (r6 48, cs 50, stt 47)
- The order of the decision branches is the same in coop_bot.py:159-180 and bot_brain.cpp:182-203 (negation, threshold, NONE, GO_NOW, WAIT, on-signal, act), by reading and by the 88-step replay
- No other pair of annotation files under annot/ is byte-identical (duplicate-hash scan); v1 and v2 lines show the same level of intent unanimity (98-100%) as v3, so 150/150 unanimous on v3 is not out of line for this project

## Training and evaluation code, seeds (`train-eval-code`)

### train-eval-code #1: Two inherited seeds label going to the roof as RAPPEL against spec_v3; the re-trained ensemble still answers RAPPEL to 'get up on the roof'

Reviewer: major, training. Affects: HANDOFF section 4 ('known error ... re-training should fix it'); wrong family 1.3% on v3 lines (csv3_037 is 1 of the 2); the final v3 model, which is trained to answer RAPPEL to 'get on the roof' / 'go roof' against the owner's decision in section 7

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

The finding holds on every point I re-derived. No headline number in HANDOFF section 4 changes; the defect is in the training data and in one sentence of the write-up.

1. **Seed labels against the spec.** seed_commands_v3.json keeps "get on the roof" (line 132) and "go roof" (line 136) in the RAPPEL list. They are inherited unchanged from seed sets v1, v2 and v21: make_spec_v3.py:113-119 loads seed_commands_v21.json and only appends, and every v21 list is a prefix of its v3 list. The same script sharpens the spec (make_spec_v3.py:52-56; blind/spec_v3.json RAPPEL: "Just going to a named place, the roof included, is MOVE_TO") and adds "go to the roof", "head to the roof" and "go up to the roof" as MOVE_TO. HANDOFF.md:192 records the owner decision that going to the roof without rope words is MOVE_TO. The seed file has carried this contradiction since it was frozen (frozen.txt:115, hash equals the file on disk), before the blind lines existed.

2. **Re-training did not fix the known error.** HANDOFF.md:111 says re-training should fix "get up on the roof" -> RAPPEL. In the leave-one-author-out study csv3_037 ("get up on the roof, I want somebody up top", read MOVE_TO by 3 of 3 readers) is still RAPPEL: 0.59 / 0.68 / 0.83 for seeds 0 / 1 / 2, ensemble 0.70, picked under both gates. It is one of exactly two wrong-family v3 lines behind the 1.3% (the other is sttv3_032).

3. **Re-training helped the other roof lines.** Of the six v3 lines that send the bot to or off the roof as MOVE_TO, the shipped bot gets 1 right and the re-trained ensemble 4. csv3_031 moves from RAPPEL to an abstain (MOVE_TO 0.55, below the 0.58 threshold).

4. **The rest of the training data disagrees with both seed labels.** Held out inside the 5-fold OOF of the 9 runs, "get on the roof" is predicted MOVE_TO in 8 of 9 (mean MOVE_TO 0.86, RAPPEL 0.12). "go roof" is not RAPPEL in 8 of 9 (MOVE_TO 6, ENTRY 2, RAPPEL 1).

5. **The causal link is an inference, not an ablation.** That these two seeds are what pulls csv3_037 to RAPPEL is strongly suggested: the seed is the nearest RAPPEL-labelled training line. But legitimate rope lines with the same wording are also in training (r6_005 "get on the rope and climb up to roof"). Training was not allowed, so no model without the seeds was tested.

6. **One imprecision in the reviewer's text.** "Every older roof line labelled RAPPEL names a rope or rappel" is not literal: r6_000 is "clip onto the roof edge and go inverted on bedroom" and stt_027 says "repel". All five are rope actions, so the point stands.

7. **The final model inherits the defect.** train_v2.py:183 trains the final model on items + seeds, so it is trained to answer RAPPEL to "get on the roof" and "go roof". A final v3 training run is in progress on this machine now with this seed file (train_v3_final_ens3.log, device mps, started 23:40:36).

8. **Secondary point: docstring overstatement only.** PER_TEMPLATE=3 samples 150 of 486 template-place combinations. "yellow" is in 3 templated seeds (2 intents); upstairs, downstairs, second floor and ground floor are in none of the 383 seeds, and the first three are not in the ZONE template list at all. This shows no cost in cross-validation: yellow 8/8, upstairs 7/7, downstairs 2/2, second floor/story 5/5, ground floor 3/4 near.

*Recommended action.* **1. Write-up, no frozen material touched.** In HANDOFF.md replace line 111 with a statement of what cross-validation showed, for example: "Known error: «get up on the roof» → RAPPEL. Re-training did NOT fix it in cross-validation: csv3_037 is still RAPPEL (0.70, both gates) and is one of the two wrong-family lines behind the 1.3%. Of the six roof MOVE_TO lines the shipped bot gets 1 right and the re-trained ensemble 4. Cause to check: seed_commands_v3.json still holds the inherited seeds "get on the roof" and "go roof" under RAPPEL, against spec_v3 and the decision in section 7." Carry the same sentence into the future "v3" section of COOP-BOT.md and DEBERTA-BOT.md.

**2. Behaviour, touches frozen material.** Write a new seed file (for example seed_commands_v31.json, with a new COOP_TAG entry in coop_v2.py:49) in which "get on the roof" and "go roof" move from RAPPEL to MOVE_TO or are dropped. "drop down from the roof" and "rappel from the roof" stay RAPPEL. Record it in frozen.txt as edited after the v3 blind lines were seen, then re-run the cross-validation and the final training. The final model now training on this machine uses the uncorrected seed file and would have to be re-trained. Every number that includes the roof lines (csv3_031, csv3_037, r6v3_002, r6v3_038, sttv3_028, sttv3_041) is then "after tuning" until new blind lines with roof orders are written. Until that is done, the 90.0 / 90.7 and 1.3% figures stand as they are.

**3. Docstring.** In make_spec_v3.py:14-16 and the comment at :58, replace "sees every place name in every kind of order" / "every name meets every kind of order" with "3 sampled places per template (150 of 486 combinations); upstairs / downstairs / second floor / ground floor are not in the templates". Editing the file changes its frozen hash (frozen.txt:113), so log it as a comment-only edit, or put the correction in the write-up instead.

**4. Optional, same root cause.** intents_v2.json:34 still describes RAPPEL as "use the rope, go up to the roof or drop down outside".

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: yes**

Every fact in the finding reproduces; I could not refute it. What I contest is the certainty of the cause and the severity.

What holds:
- seed_commands_v3.json keeps the v1 seeds "get on the roof" and "go roof" under RAPPEL. The file is exactly seed set v21 plus 150 appended templated lines; no v21 line was moved.
- spec_v3 and HANDOFF section 7 say going to the roof without a rope is MOVE_TO, and the same seed file has "go to the roof", "head to the roof" and "go up to the roof" under MOVE_TO. So "go roof" (RAPPEL) and "go to the roof" (MOVE_TO) contradict each other inside one training set.
- The conflict is not documented anywhere (HANDOFF, COOP-BOT.md, DEBERTA-BOT.md, both READMEs, frozen.txt, code comments), and the bot has no post-processing of RAPPEL.
- HANDOFF.md:111 ("re-training should fix it") is contradicted by the project's own cross-validation: the re-trained ens3 answers RAPPEL 0.70 to csv3_037 under both gates. It is one of the two wrong-family lines behind the 1.3%; the other is sttv3_032.
- The final v3 model trains on these two seeds as RAPPEL, and the final run now in progress on this machine uses this seed file. The shipped v2 model, same recipe, answers RAPPEL 0.994 to both phrases, so the v3 model will too.

What is weaker than the finding states:
- **No reported number is wrong.** The 1.3% already counts csv3_037, and eval_v3.log:91 lists it openly.
- **The cause is supported, not shown.** No model exists that predicted csv3_037 without both seeds in training, so there is no ablation. Of the nine models that never saw the line, six answer RAPPEL and three do not, so the seeds do not force RAPPEL by themselves. The genuine rope lines r6_005 and cs_038 ("grab the rope and get up on the roof") are plausible co-causes. The seed change would certainly fix the two literal phrases; it is not shown to fix "get up on the roof".
- **Scope is narrow.** Five of the 150 blind lines are orders to go to or leave the roof; in cross-validation three are right, one abstains and one is wrong family. In the final model csv3_037 and csv3_031 are themselves training lines labelled MOVE_TO.
- **One detail is loose.** r6_000 ("clip onto the roof edge and go inverted") names neither a rope nor rappel literally, though it is a rope action.

Secondary claim, also true: there are 150 templated seeds from 51 templates, three sampled places each. "yellow" is in 3 lines across 2 intents; upstairs, downstairs, second floor and ground floor are in none. The docstring "sees every place name in every kind of order" overstates this. No measured harm is attributable to it; it is a note.

Severity is minor rather than major: one forecast sentence in the write-up is wrong, and two of 383 training labels contradict the spec, giving a certain wrong-family answer on two canonical phrases. No headline claim changes.

*Recommended action.* 1. **Write-up, no frozen material touched.** Replace the second sentence of HANDOFF.md:111 ("Её должно починить дообучение.") with a statement of what the cross-validation showed, for example: "In leave-one-author-out cross-validation re-training did not fix it: ens3 gives RAPPEL 0.70 on csv3_037 (eval_v3.log:91), one of the two wrong-family lines behind the 1.3%. Likely cause, not checked by ablation: the seeds 'get on the roof' and 'go roof', inherited from v1, are still RAPPEL in seed_commands_v3.json against spec_v3 and section 7. A final model trained on this seed set will answer RAPPEL to both phrases; shipped v2 gives 0.994." Carry the same sentence into the future v3 section of COOP-BOT.md as a known limitation.

2. **Behaviour, owner's decision, touches frozen material.** Do not edit seed_commands_v3.json. If the owner wants section 7 to hold for "get on the roof" and "go roof", create a new seed set the way v21 was made: a new file and COOP_TAG value with the two lines moved to MOVE_TO or dropped, its hash and the reason logged in frozen.txt as made after the v3 blind lines were seen. Then re-run the cross-validation and the final training.
   - The current numbers (90.0 / 90.7 near, 1.3% wrong family) stay as the clean result for seed set v3.
   - Any number from the new seed set is "after tuning", at least on csv3_031, csv3_037, r6v3_038, sttv3_028 and sttv3_041, until new blind roof lines are written.
   - The final v3 run now in progress (train_v3_final_ens3.log) uses seed_commands_v3.json. If the seeds change, that model must be re-trained before export.

3. **Docstring, note level.** Do not edit make_spec_v3.py, since its hash is in frozen.txt. State in the v3 write-up that the templated seeds are three sampled places per template (150 lines), not every place in every order, and that upstairs, downstairs, second floor and ground floor have no templated seed.

### train-eval-code #2: The gain over the shipped bot comes from one held-out author (r6); on cs and stt the interval includes zero

Reviewer: major, evaluation. Affects: HANDOFF section 4: the '+10.7 / +11.3' line, '90.0 / 90.7', and the conclusion 're-training is needed'

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

Every number in the finding reproduces. The pooled figures in HANDOFF section 4 are arithmetically correct, but the gain is concentrated in one held-out author and the write-up does not show that.

Per held-out author, shipped v2 bot -> re-trained ens3 (family gate), near-correct of 50 (wrong-family count):
- r6: 39 (1) -> 49 (0)
- cs: 46 (3) -> 46 (1)
- stt: 40 (1) -> 41 (1)

So "90.7% near" is 98 / 92 / 82 by author, and on the STT-style author it is 82% against the shipped bot's 80%.

Score difference (near - 2 x wrong family), same bootstrap recipe as eval_v3.py:
| slice | family gate | top gate |
|---|---|---|
| r6 | +24.0 [+12.0,+38.0] | +24.0 [+12.0,+38.0] |
| cs | +8.0 [-4.0,+24.0] | +6.0 [-8.0,+22.0] |
| stt | +2.0 [-8.0,+12.0] | +2.0 [-8.0,+12.0] |
| cs+stt (100 lines) | +5.0 [-3.0,+14.0] | +4.0 [-4.0,+14.0] |
| all 150 | +11.3 [+4.0,+19.3] | +10.7 [+3.3,+18.7] |

- r6 supplies 12 of the 17 pooled score points and 10 of the 11 net near-correct lines (family gate: gained 10 r6 / 4 stt / 1 cs, lost 1 cs / 3 stt).
- Dropping cs or stt instead leaves the interval above zero (+13 [+5,+22] and +16 [+7,+26]); only dropping r6 removes it.
- The pattern is the same for each single seed (r6 46-49, cs 44-47, stt 36-43 against shipped 39 / 46 / 40), and it is not a threshold effect: r6's fold threshold is 0.60-0.62 against the shipped 0.58.
- The pooled interval resamples 150 lines as independent (eval_v3.py:86-90), so it is conditional on these three authors. Section C of eval_v3.log has no per-author rows, although section A has them for the matcher.

Three refinements to the reviewer's text:
1. **Low power alone does not explain cs and stt.** A subset of 50 lines would often include zero even under a uniform effect. The stronger evidence is the 100-line estimate without r6 (near 86 -> 87) and a permutation test of r6 against the rest (p = 0.023 family, 0.016 top, with r6 picked post hoc).
2. **The reviewer's "supported claim" of fewer wrong-family actions (5 -> 2) is not statistically supported either.** It is 3 lines removed and 0 added (exact sign test p = 0.25), so it should be reported as a count.
3. **Formatting explains part of the r6 gap, not most of it.** All 50 of r6's v3 lines are capitalised and end with punctuation; r6's own v1/v2 lines (8/121 and 4/40 capitalised, 0 and 1 with end punctuation), the other authors and the seeds (2/383 capitalised) are not. The reviewer's variant holds (shipped 41/50 on r6, pooled unchanged). With full STT-like normalisation the shipped bot reaches 43/50 on r6 and the pooled difference drops to +9.3 [+2.0,+18.0] top / +10.0 [+2.7,+18.7] family. This check is one-sided: the fold models are not saved, so the re-trained side could not be re-run on reformatted text.

No number in HANDOFF is wrong. The conclusion "re-training is needed" rests on an interval that excludes zero only because of r6.

*Recommended action.* Write-up only; no change to rules, vocabulary, spec, seeds or labels.

**1. /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md, section 4, under the cross-validation table.** Add a per-author table, near of 50 (wrong family):

| | r6 | cs | stt |
|---|---|---|---|
| shipped v2 | 39 (1) | 46 (3) | 40 (1) |
| re-trained ens3, family gate | 49 (0) | 46 (1) | 41 (1) |
| re-trained ens3, top gate | 49 (0) | 45 (1) | 41 (1) |
| score difference, family gate | +24.0 [+12,+38] | +8.0 [-4,+24] | +2.0 [-8,+12] |

**2. Same section, replace the "+10.7 / +11.3" bullet and the conclusion** with a statement along these lines (in the document's language):

"Pooled over 150 lines the difference is +10.7 [+3.3,+18.7] (top) / +11.3 [+4.0,+19.3] (family). The interval is over lines and is conditional on these three authors. The gain comes from author r6 (39 -> 49 of 50). On cs and stt there is no measurable change (86 -> 87 of 100; score +5.0 [-3,+14]), and on STT-style lines it is 80% -> 82%. Wrong-family actions go 5 -> 2 of 150 (3 removed, 0 added; too few to test). r6's v3 lines are the only capitalised, punctuated ones; with them lower-cased and unpunctuated the shipped bot gets 43/50 and the pooled difference is +9.3 / +10.0. Conclusion: re-training does no harm on old lines and helps on one author's style; a general gain on place-naming lines is not shown and needs blind lines from further authors."

**3. /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/eval_v3.py, retrained() (lines 149-158).** Print the same per-author rows for the shipped and re-trained picks, with the per-author and without-r6 bootstrap, so eval_v3.log carries them. This is an evaluation-code edit made after the test lines were seen, so record the new eval_v3.py and eval_v3.log hashes in frozen.txt.

**4. Carry the same table and wording into the future "v3" section of COOP-BOT.md and DEBERTA-BOT.md.**

**Verifier (refute): confirmed, major; reproduced: yes; touches frozen: no**

The finding stands; every number in it reproduces from the stored probabilities. It is a write-up problem only: no number in HANDOFF is wrong and the decision to re-train is unaffected.

**What holds**
- The pooled "+10.7 [+3.3,+18.7] / +11.3 [+4.0,+19.3]" is arithmetically right, but it is a line-level interval over three fixed authors. Resampling within author gives nearly the same interval ([+4.0,+18.7] / [+4.7,+19.3]); it says nothing about a new author.
- Its exclusion of zero rests on r6. Shipped -> re-trained ens3/family, near of 50 (wrong family):

| held-out author | shipped | re-trained | score diff, family gate | score diff, top gate |
|---|---|---|---|---|
| r6 | 39 (1) | 49 (0) | +24.0 [+12,+38] | +24.0 [+12,+38] |
| cs | 46 (3) | 46 (1) | +8.0 [-4,+24] | +6.0 [-8,+22] |
| stt | 40 (1) | 41 (1) | +2.0 [-8,+12] | +2.0 [-8,+12] |
| cs + stt | 86 (4) | 87 (2) | +5.0 [-3,+14] | +4.0 [-4,+14] |

- Near for the re-trained ens3 is 98 / 92 / 82 by author, so "90.7" is 82% on the STT-style author against the shipped bot's 80%. On the older lines the same folds give 91.9 / 92.5 / 88.8, so the spread across authors is much wider on the v3 lines.
- All ten r6 gains are lines where the shipped bot answered NONE (under threshold).
- None of this is stated in HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md or the summary lines of eval_v3.log. The per-author counts can only be derived by counting id prefixes in the log's per-line miss lists. The v1 write-up did give a per-author table and calls the STT author "the one closest to a real input pipeline".

**What the reviewer missed (softens the reading, not the facts)**
- The comparison is not like for like, and it is biased against the re-trained model. The shipped bot was trained on all 483 older lines, including the held-out author's 161; each re-trained fold saw none of that author's lines.
- All three lines lost on stt are "beach" / "repel" lines. Those mis-hearings occur only in stt's own older lines (5 "beach", 1 "repel"), never in r6, cs or any seed.
- So "no measurable change on cs and stt" is a lower bound for a model trained on all authors. There are no held-out lines to measure that model on.
- The direction is non-negative on all three authors and wrong family does not rise on any (5 -> 2 pooled).
- With three authors no author-level interval can exclude zero (t with 2 df: about +/-28), which was equally true of the v2 study.

The supportable conclusion is "re-training is harmless on old orders, cuts wrong-family actions, and gives a large gain on one author"; a general +11 points or 90.7% on STT-like input is not supported.

*Recommended action.* Write-up change only, in `/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md` section 4 (after line 121) and in the future v3 section of COOP-BOT.md.

1. Add the per-author table next to the pooled line: shipped -> re-trained ens3/family, near of 50 (wrong family) and score difference: r6 39 (1) -> 49 (0), +24.0 [+12,+38]; cs 46 (3) -> 46 (1), +8.0 [-4,+24]; stt 40 (1) -> 41 (1), +2.0 [-8,+12]; cs + stt +5.0 [-3,+14].

2. Add these sentences: "The pooled interval resamples lines; the three authors are fixed, so it does not cover a new author. The gain is measured on r6 only (ten 'say again' lines recovered); on cs and stt the interval includes zero. Near by author is 98 / 92 / 82, so on STT-style input expect about 82%, not 90.7%. The comparison is conservative: the shipped bot was trained on every author's older lines, each fold on none of the held-out author's, and the three lines lost on stt are 'beach' / 'repel' lines, mis-hearings found only in stt's own older lines."

3. Replace the conclusion on line 123 ("дообучение нужно") with the supported claim: re-training does not hurt the older orders (0.0 / -0.2 [-4,+4]), lowers wrong-family actions from 5 to 2 of 150, and gives a large gain on one author of three. A general gain needs blind lines from further authors.

If a per-author printout is also added to section C of eval_v3.py, record the new hash in frozen.txt as a reporting-only change made after the results. No rule, vocabulary, spec, seed or label changes.

### train-eval-code #3: '+10.7 / +11.3', '0.0 / -0.2' and '3.3 points worse' are differences of the score (near - 2 x wrong family), not of near; 'place names stripped' removes only the qualifier word

Reviewer: major, numbers. Affects: HANDOFF.md:108 (strip row), :110 (conclusion), :121, :122; frozen.txt:158 repeats the numbers without the metric

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

Every number in the finding holds except one ancillary count. No number in HANDOFF.md is wrong and no decision changes; the defect is in the write-up only.

**Unnamed metric.** The three differences at HANDOFF.md:108, :121 and :122 are differences of the criterion "near − 2 × wrong family". HANDOFF.md never names or defines that criterion, and the numbers sit directly under tables whose columns are near and wrong family. Read against those tables, they overstate the near gain by 4 points.

| Comparison | Score (what HANDOFF quotes) | Near | Wrong family |
|---|---|---|---|
| Re-trained ens3/top − shipped, 150 v3 lines | +10.7 [+3.3, +18.7] | +6.7 [+1.3, +12.7] (125 → 135) | −2.0 [−4.7, 0.0] (5 → 2) |
| Re-trained ens3/family − shipped, 150 v3 lines | +11.3 [+4.0, +19.3] | +7.3 [+2.0, +13.3] (125 → 136) | −2.0 [−4.7, 0.0] (5 → 2) |
| v3 study − v21 study, top, 483 older lines | +0.0 [−3.9, +4.1] | −1.7 [−3.7, +0.4] (441 → 433) | 12 → 8 lines |
| v3 study − v21 study, family, 483 older lines | −0.2 [−4.3, +3.7] | +0.6 [−1.4, +2.7] (437 → 440) | 9 → 11 lines |
| Strip − raw, shipped bot, 150 v3 lines | −3.3 [−8.0, 0.0] | −2.0 [−4.7, 0.0] (125 → 122) | 5 → 6 lines |

- The near gain on v3 lines still excludes zero, so "re-training is needed" stands.
- On the older lines 38 (top) and 39 (family) answers differ. "Old orders did not suffer" is true only as "no change detected within about ±4 score points"; at the top gate 8 fewer lines are near-correct, offset in the criterion by 4 fewer wrong-family actions.

**Strip row.** "Names cut out before the classifier" (HANDOFF.md:108) is not what was run.
- `locations.normalized(text, "strip")` removes only a compass or colour word attached to a place noun. Its own docstring says so (locations.py:46-49, 437-438).
- It rewrites 58 of 150 lines. The 61 removed words are north, west, east, south, red, blue, yellow, white and brown, and nothing else.
- All 58 rewritten lines still carry their place object or zone afterwards. The matcher finds a place in 144 of 150 lines both before and after stripping.
- Only 3 answers change, all from author stt, and all three get worse (sttv3_011, sttv3_014, sttv3_049). The interval reaches zero.
- "Conclusion: the model reads the raw line" (HANDOFF.md:110) is therefore a default that was kept, not a measured win. An experiment that actually removes place names was never run.

**Not reproduced:** the reviewer's "136 of 150 stripped lines still contain a place word". I get 144 (matcher finds a target), 141 (a target with an object or zone) or 132 (crude noun regex), depending on definition. The point it supports holds more strongly than stated.

*Recommended action.* Edit four lines of HANDOFF.md; no re-run is needed and nothing frozen changes.

1. **HANDOFF.md:108**, replace the row with: «то же, но слово-уточнение (north / red …) вырезано перед классификатором: изменено 58 строк из 150, само место (door, stairs, roof) остаётся | критерий (попадание − 2 × чужое семейство) −3.3 [−8.0, 0.0]; попадание −2.0 [−4.7, 0.0]; ответ меняется на 3 строках, все у автора stt».
2. **HANDOFF.md:110**, replace with: «Вывод: вырезание уточнений не помогает (разница неотличима от нуля), классификатору оставлена сырая строка. Полное удаление названий мест не проверялось.»
3. **HANDOFF.md:121**, replace with: «Разница на строках с местами по критерию «попадание − 2 × чужое семейство»: +10.7 [+3.3, +18.7] для top и +11.3 [+4.0, +19.3] для family. По попаданию: +6.7 [+1.3, +12.7] и +7.3 [+2.0, +13.3]; чужое семейство −2.0 [−4.7, 0.0].»
4. **HANDOFF.md:122**, replace with: «На 483 старых строках разница по критерию 0.0 [−3.9, +4.1] / −0.2 [−4.3, +3.7]. По попаданию: top −1.7 [−3.7, +0.4] (441 → 433 строк, чужое семейство 12 → 8), family +0.6 [−1.4, +2.7] (437 → 440, 9 → 11); ответ меняется на 38 / 39 строках. Ухудшение не обнаружено в пределах примерно ±4 пунктов критерия.»

Optional:
- Have eval_v3.py (lines 112, 158, 166) print the near difference next to the score difference. That changes eval_v3.log, so its new hash must be recorded in frozen.txt.
- Do not edit frozen.txt:158 or :139 ("raw beats strip"); they are log history. Append a new dated line stating that those numbers are the criterion near − 2 × wrong family.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: no**

The finding stands on the facts; I could not refute it. I rate it minor rather than major, because no number is wrong and no conclusion changes.

**Unnamed metric.** HANDOFF.md:108, :121 and :122 (and frozen.txt:158) give differences of the project's criterion, near − 2 × wrong family, without naming it. They sit directly under tables whose columns are near and wrong family. `eval_v3.py:77-83` (`per_item`) and `:86-90` (`bootstrap`) compute exactly that criterion, and eval_v3.log labels every one of these lines "score:".

| Comparison | Score (as reported) | Near | Wrong family |
|---|---|---|---|
| v3 lines, re-trained − shipped, top | +10.7 [+3.3, +18.7] | +6.7 [+1.3, +12.7] | −2.0 [−4.7, +0.0] |
| v3 lines, re-trained − shipped, family | +11.3 [+4.0, +19.3] | +7.3 [+2.0, +13.3] | −2.0 [−4.7, +0.0] |
| 483 older lines, v3 − v21 study, top | +0.0 [−3.9, +4.1] | −1.7 [−3.7, +0.4] (441 → 433 lines) | 12 → 8 lines |
| 483 older lines, v3 − v21 study, family | −0.2 [−4.3, +3.7] | +0.6 [−1.4, +2.7] (437 → 440 lines) | 9 → 11 lines |
| shipped bot, strip − raw | −3.3 [−8.0, +0.0] | −2.0 [−4.7, +0.0] (83.3 → 81.3) | +0.7 (3.3 → 4.0) |

**"Names stripped" is over-described.** `locations.normalized(text, "strip")` removes only the attached qualifier word.
- It rewrites 58 of 150 lines, with 61 cuts, all compass or colour words.
- Object nouns, "main" and floor/zone words are never cut.
- The matcher still finds a target in 144 of 150 stripped lines, the same count as on raw lines.
- Only 3 answers change, all from author stt, all for the worse; the interval touches zero.

**What holds in the write-up's favour.**
- The criterion is the project's declared one: COOP-BOT.md:168 ("Score" is the owner's criterion) and DEBERTA-BOT.md:136 define it, and the v2 write-up reports its paired differences the same way (COOP-BOT.md:437-440, :456), but always names it. HANDOFF.md is the only place that drops the label.
- "Re-training is needed" holds on near as well: both near intervals exclude zero.
- "Older orders are not harmed" holds on both metrics: every interval includes zero. The 0.0 at the top gate does hide a trade of 8 fewer near-correct lines against 4 fewer wrong-family lines.
- Raw input is the right default: strip helped on no line, and `coop_bot.py:155` feeds the raw line to the classifier. But "the model reads the raw line" (HANDOFF.md:110) and "raw beats strip" (frozen.txt:139) are a kept default, not a measured win.

The cost of leaving it as is: a reader takes the near gain to be 4 points larger than it is (10.7 against 6.7) and takes "strip" for removal of the whole place name. The task's own claim summary already reads both that way.

*Recommended action.* Wording only; no rule, vocabulary, spec, seed or label changes.

**`/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md`**
1. Line 108, replace the row with: "то же, но слово-уточнение (сторона света или цвет) вырезано перед классификатором: переписано 58 строк из 150, ответ изменился на 3 (все у автора stt) | попадание 81.3% (−2.0), чужое семейство 4.0% (+0.7); критерий «попадание − 2 × чужое семейство» −3.3 [−8.0, +0.0]".
2. Line 110, replace with: "Вывод: классификатору оставлена сырая строка. Вырезание не помогло ни на одной строке; разница (3 строки) в пределах шума."
3. Line 121, replace with: "Разница на строках с местами по критерию «попадание − 2 × чужое семейство»: +10.7 [+3.3, +18.7] (top) и +11.3 [+4.0, +19.3] (family). По попаданию: +6.7 [+1.3, +12.7] и +7.3 [+2.0, +13.3]; чужое семейство −2.0 [−4.7, 0.0]."
4. Line 122, replace with: "На 483 старых строках критерий 0.0 [−3.9, +4.1] / −0.2 [−4.3, +3.7]; попадание −1.7 [−3.7, +0.4] (top: 441 → 433 строк, чужое семейство 12 → 8) и +0.6 [−1.4, +2.7] (family: 437 → 440, 9 → 11). Все интервалы включают ноль."

**`scripts/coop/frozen.txt`**
- Do not rewrite lines 139 or 158. Append one dated note: the numbers on :158 are differences of near − 2 × wrong family, and "raw beats strip" on :139 is 3 changed answers, score −3.3 [−8.0, +0.0].

**Optional**
- Have `eval_v3.py` print the near and wrong-family differences next to each "score:" line. This is a new frozen.txt hash entry; no existing number changes.

**Later**
- Carry the same wording into the future "v3" section of COOP-BOT.md.

### train-eval-code #4: Novelty slice for v3 (missing from the write-up): 90 of 150 lines are novel, the gain survives there with the lower bound near zero; 60 are near-copies, 32 of them of another author's v3 line

Reviewer: minor, evaluation. Affects: HANDOFF section 4 cross-validation table (no novel column, unlike the v2 table in COOP-BOT.md)

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The finding holds and every number in it reproduces, except a rounding nit (Q3 of the similarity is 0.56, not 0.55). No HANDOFF section 4 number is wrong; what is missing is the novel slice that the project's own standard asks for (COOP-BOT.md:58-62: "This is why every table below also reports the ... novel lines").

With eval_v2.novelty() under COOP_TAG=v3 (identical per line to my own computation), 90 of the 150 v3 lines are novel (< 0.5) and 60 have a near-copy in their fold's training data.

| slice | n | shipped near / wrong family | ens3 top | ens3 family | score diff, top | score diff, family |
|---|---|---|---|---|---|---|
| all v3 | 150 | 83.3 / 3.3% | 90.0 / 1.3% | 90.7 / 1.3% | +10.7 [+3.3,+18.7] | +11.3 [+4.0,+19.3] |
| novel | 90 | 82.2 / 2.2% | 88.9 / 1.1% | 90.0 / 1.1% | +8.9 [+1.1,+17.8] | +10.0 [+2.2,+18.9] |
| near-copy | 60 | 85.0 / 5.0% | 91.7 / 1.7% | 91.7 / 1.7% | +13.3 [+0.0,+28.3] | +13.3 [+0.0,+28.3] |

- **Novel lines:** the gain survives in score. In near-correct it is +6.7 [+0.0,+14.4] (top) and +7.8 [+1.1,+14.4] (family); 9 lines fixed against 3 (top) or 2 (family) broken.
- **Robust to the cut:** from 0.35 to 0.60 the score difference stays between +8.7 and +13.6, with lower bounds from +0.0 to +2.7. Stripping place names before measuring similarity gives 97 novel lines and +9.3 [+2.1,+17.5] / +10.3 [+3.1,+18.6].
- **Not carried by templated seeds:** on the 130 lines with no templated seed at 0.5 or above, the difference is +10.0 [+2.3,+18.5] / +10.8 [+3.1,+19.2].

The twin caveat is sharper than the reviewer's "overstates novelty somewhat":
- The 32 lines are 16 mutual cross-author pairs; 13 pairs share the majority intent. The other 3 pairs only share place words.
- On those 32 lines the shipped bot is 78.1 near and the re-trained one 93.8, a score difference of +28.1 [+9.4,+53.1]. Five of the 15 fixes sit there, none broken.
- On the 118 lines without such a twin the difference is +5.9 [-0.8,+13.6] (top) and +6.8 [+0.0,+13.6] (family). This split is my own post-hoc slice.

So the gain is positive on every slice, but outside the twin lines its lower bound is at zero. The headline interval includes lines whose near-twin by another author was in the training fold.

Not documented for v3 anywhere: HANDOFF.md, the docs and frozen.txt have no novel or near-copy statement for v3, and COOP-BOT.md has no v3 section yet (HANDOFF step 5). eval_v2.py under COOP_TAG=v3 does print a novel column, but over all 633 lines (299 novel), not for the v3 lines and not against the shipped bot; no log of that run is in the tree.

*Recommended action.* Write-up only; no rule, vocabulary, spec, seed or label changes.

1. **HANDOFF.md section 4**, under the cross-validation table (and the same in the future "v3" section of COOP-BOT.md, as the v2 table has a novel column): add two rows and one caveat.
   - Row "novel v3 lines (n=90, nearest training line or seed < 0.5 cosine)": shipped 82.2 / 2.2%; re-trained top / family 88.9 / 90.0, 1.1%.
   - Row "v3 lines with a near-copy (n=60)": shipped 85.0 / 5.0%; re-trained 91.7 / 91.7, 1.7%.
   - Sentence: "On the 90 novel lines the difference is +8.9 [+1.1, +17.8] (top) and +10.0 [+2.2, +18.9] (family). 32 v3 lines (16 pairs, 13 with the same intent) have a near-twin written by another author that was in the training fold. On those the difference is +28.1; on the other 118 lines it is +5.9 [-0.8, +13.6] / +6.8 [+0.0, +13.6]. The gain is positive on every slice, but outside the twin lines its lower bound is at zero. The slice is post hoc; the 0.5 cut is the v2 definition (eval_v2.novelty), not chosen on v3 lines."

2. **Where the numbers come from:** put the computation in a new script, for example scripts/coop/v3_novel.py, rather than editing eval_v3.py, and record its hash in frozen.txt as a post-hoc analysis added after the v3 results. If eval_v3.py is edited instead, record the new hash and say so in the same line.

### train-eval-code #5: The final v3 model is being trained on MPS while every v3 number comes from CUDA models; the equivalence check was at argmax, and at the deployable threshold the MPS fold has about twice the wrong-family count

Reviewer: minor, portability. Affects: Whether the cross-validation numbers in HANDOFF section 4 describe the model that will ship; frozen.txt:166 wording

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Every reviewer number reproduces exactly. The final v3 ensemble is being trained on MPS (train_v3_final_ens3.log line 1: "device: mps"; out-of-fold for seed 0 finished at 23:55, no fit printed yet), while all v3 cross-validation numbers in HANDOFF section 4 come from CUDA fold models. The only training-equivalence check (scratchpad/mps_train_check.py) scores at argmax (V.picks(probs, "top", 0.0)), and frozen.txt:166 does say "ens3 at argmax" in its parenthesis.

At the stt fold's deployable thresholds (fitted on the CUDA out-of-fold predictions: top 0.58, family 0.52), on the 211 stt lines:

| gate | device | near | wrong family | acts on non-order |
|---|---|---|---|---|
| top | CUDA | 181 | 4 (1.9%) | 3.0% |
| top | MPS | 180 | 8 (3.8%) | 6.1% |
| family | CUDA | 184 | 6 (2.8%) | 3.0% |
| family | MPS | 183 | 10 (4.7%) | 6.1% |

On the 50 stt v3 lines wrong family is 1 vs 4 under both gates. Lines wrong-family under one device only: MPS 5 vs CUDA 1 (top, exact sign test p=0.22) and 6 vs 2 (family, p=0.29).

What this does and does not show:
- **Not significant.** One fold, three seeds per device. Treating the six models as exchangeable, the all-MPS ensemble ranks 19th of the 20 possible three-model ensembles on wrong family (top gate); the best achievable one-sided p is 0.05-0.10.
- **Direction is consistent.** Mean wrong-family count rises with the number of MPS members: 4.0 / 4.4 / 6.2 / 8.0 (top) and 6.0 / 7.6 / 9.7 / 10.0 (family). MPS wrong family is at or above CUDA at every threshold I swept except 0.70, where both are 3.
- **Not a calibration shift.** Mean top probability per model is 0.937 / 0.929 / 0.921 on CUDA and 0.920 / 0.943 / 0.921 on MPS, so using the CUDA threshold is not obviously unfair to the MPS models. The caveat remains that no MPS out-of-fold fit exists for this fold, and final() fits its threshold on its own MPS out-of-fold predictions.
- **The frozen.txt wording is over-stated for wrong family.** "Inside the seed-to-seed spread" is supported by the argmax agreement counts only (same-seed CUDA vs MPS 200-204 of 227, against CUDA seed pairs 195-199). On wrong family at argmax, single models give 19 / 20 / 17 on CUDA and 25 / 19 / 21 on MPS: two of three MPS seeds are above the CUDA maximum. Two MPS seeds also miss a probe that every CUDA seed gets.

Already in place: the edit changes no hyperparameter (diff against the pristine train_v2.py shows only the device choice, cache freeing and config text), and bot_config.json will record recipe.device, so the model is labelled at config level. Not in place: HANDOFF.md lines 126 and 141-142 still say the final model trains on the work machine and that train_v2.py has no MPS support, and nothing warns that the 90.0 / 90.7 near and 1.3% wrong family were measured on CUDA-trained models.

So the precise problem is that equivalence of MPS training at the operating point is unverified, with a weak signal in the unfavourable direction on the double-weighted metric. It is not a demonstrated defect.

*Recommended action.* No code change and nothing frozen is touched.

1. **frozen.txt**: append a new dated entry rather than editing line 166. Suggested text: "The MPS training check of 23:40 was at argmax only. At the stt fold's CUDA out-of-fold thresholds (top 0.58 / family 0.52) the MPS-trained leave-stt-out ens3 has near 180 vs 181 and wrong family 8 vs 4 of 211 (top), 183 vs 184 and 10 vs 6 (family); 5 vs 1 discordant wrong-family lines, sign test p=0.22, one fold, not significant. 'Inside the seed-to-seed spread' holds for argmax agreement only: single-model wrong family at argmax is 19/20/17 on CUDA and 25/19/21 on MPS."

2. **HANDOFF.md**: replace line 126 ("На момент снимка обучается на рабочей машине") and lines 141-142 ("Поддержки MPS в нём нет...") with the fact that the final model was trained on MPS on the Mac. In section 4, next to the cross-validation table, add one sentence: the 90.0 / 90.7 near and 1.3% wrong family were measured on CUDA-trained fold models; the shipped ensemble is MPS-trained, and equivalence was checked at argmax on one fold only. Carry the same sentence into the future v3 section of COOP-BOT.md.

3. **When final() finishes**: read oof_fits in models/coop-deberta-v3-ens3-v3/bot_config.json (criterion over 633 out-of-fold lines) and record it in frozen.txt. For scale, the CUDA cross-validation folds give 82-86 per 100 lines and the shipped v2 config gives 89 per 100. If the work machine's final v3 folder can be brought over, compare its oof_fits (same lines, same fold splits) and prefer that model if the MPS criterion is clearly lower, as HANDOFF.md:142 already advises.

### train-eval-code #6: v3_noharm.py no longer runs and results_v3_noharm.json is an unreported, pre-freeze artifact

Reviewer: minor, evaluation. Affects: scripts/coop/v3_noharm.py, results_v3_noharm.json; no reported number

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

Every factual part of the finding reproduces, with two refinements; it affects no reported number and no shipped behaviour.

1. **The script is dead.** `scripts/coop/v3_noharm.py:26` loops over `("raw", "strip", "strip+zone")`. The current `locations.py:441` (`assert mode == "strip", mode`) rejects the third mode, so the script raises `AssertionError: strip+zone` before its `json.dump` at line 42.

2. **The result file is stale and its matcher version is unidentifiable.** `results_v3_noharm.json` (mtime 2026-10-03T20:35:30+0200) predates the first v3 entry in `frozen.txt` (20:55:13) by 20 minutes. It records strip changed_lines 7 and strip+zone 13; the current matcher rewrites 3 of the 483 older lines and has no strip+zone mode.
   - Refinement: "earlier, unhashed matcher" is an inference. Rules v1 (hash 111d1a76...) is not on disk, so it cannot be shown whether the 20:35 matcher was v1 or a pre-freeze draft. What is provable is that it is not the current file.

3. **Neither file is recorded or cited.** Neither appears in `frozen.txt`, HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md, README.md or cpp/coop_intent/README.md. The only reference is the docstring of `shipped.py:4`, which is itself hash-logged at `frozen.txt:123`.

4. **Refinement: the conclusion still holds, only the counts are stale.** Under the current rules the shipped ensemble gives the same answer for raw and strip on all 3 rewritten lines, so "0 flips with strip" remains true.

Why this is a note rather than a defect in the claims:
- The check is on the 483 lines the shipped bot was trained on; the script's own docstring says it is not a quality measurement.
- It predates the blind lines, so no freeze rule is broken.
- The product does not use the rewrite: HANDOFF section 4 concludes the model reads the raw line, and `coop_bot.py` never calls `normalized`.
- HANDOFF's "old orders not harmed" (0.0 / -0.2 on 483 lines) comes from `eval_v3.log` section C, not from this file.

The only real risk is that the still-unwritten v3 section of COOP-BOT.md cites this JSON.

*Recommended action.* Housekeeping only; no reported number changes.

**Option A (simplest):** delete `/Users/t.losiev/Documents/models_training/project_synth/scripts/coop/v3_noharm.py` and `/Users/t.losiev/Documents/models_training/project_synth/scripts/coop/results_v3_noharm.json`. Optionally drop "v3_noharm.py" from the docstring at `shipped.py:4`; that file is hash-logged at `frozen.txt:123`, so append its new hash with a one-line comment.

**Option B (keep the check):** in `v3_noharm.py` change line 26 to `for mode in ("raw", "strip"):` and fix the docstring at line 3, then re-run. Expected under the current rules: strip rewrites 3 lines (r6_040, r6v2_027, r6v2_028), 0 answers changed. Append to `frozen.txt` something like: "v3_noharm.py + results_v3_noharm.json: no-flip check of the shipped v2 bot on the 483 lines it was trained on, raw vs strip, locations.py b3e9314a (rules v2); not a quality number; replaces the pre-freeze 20:35 run made with a matcher draft that had a strip+zone mode".

**Either way:**
- Do not restore a "strip+zone" mode in `locations.py` to make the script run. That would change the hash-logged matcher file and the baseline of the C++ parity check.
- When the v3 section of COOP-BOT.md is written, do not cite the 7 / 13 counts from the current `results_v3_noharm.json`.

### train-eval-code #7: eval_v2.py under COOP_TAG=v3 overwrites results_v3.json, the file eval_v3.py writes; the classifier numbers of sections B and C are stored in no results file

Reviewer: minor, evaluation. Affects: results_v3.json; reproducibility of the section B / C numbers from a machine-readable file

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Both halves of the finding hold, and neither affects a number under review.

1. Name collision. Two supported entry points write scripts/coop/results_v3.json with incompatible schemas, and whichever ran last wins silently.
- eval_v3.py:180 writes {"matcher": {...}} (4 numbers, rules v2).
- eval_v2.py:260 writes results_{V.TAG}.json, which is the same path under COOP_TAG=v3, with keys table / new_intents / equal_risk / bootstrap / probes / slices.
- Running eval_v2.py under the v3 tag is an anticipated use: eval_v2.py:175-176 adds a v3 slice inside main() with the comment "COOP_TAG=v3", and frozen.txt:117 lists "eval_v2.py (v1 slice by version, v3 slice)". It is also the only way to get the v3 study's probe, equal-risk and new-intent tables.
- results_v2.json and results_v21.json are eval_v2.py outputs, so the on-disk results_v3.json (matcher only) breaks the results_<tag>.json convention.

2. Sections B and C are not machine-readable. The file on disk holds only the matcher summary. The classifier numbers (83.3 / 3.3, strip -3.3, 90.0 / 90.7 / 1.3, +10.7 [+3.3,+18.7], +11.3 [+4.0,+19.3], 0.0 / -0.2) exist only as text: eval_v3.log, the frozen.txt:158 comment and HANDOFF.md. The raw-input 83.3 / 3.3 line is also in eval_v3_rules_v1.log.

Why the impact is limited:
- Nothing reads results_v3.json: no script loads it, no write-up cites it, and frozen.txt does not hash it. train_v2.py final fits gate and threshold from out-of-fold predictions directly (train_v2.py:175-177).
- The documented recipe (HANDOFF section 5, step 1) runs only eval_v3.py, so the documented flow never triggers the overwrite.
- The B and C numbers are fully determined by hashed inputs (results_v3_probs_{r6,cs,stt}.json at frozen.txt:160-162, results_v3_shipped.json at :144) and recompute in 1.4 s.
- eval_v3.py on disk still has the hash recorded at frozen.txt:121 ("written before any v3 line was read"), so matcher-only output was the original design, not a later omission.

Side observation: the eval_v2 schema does carry the section C levels (ens3/top v3 90.0 / 1.3, ens3/family v3 90.7 / 1.3), so the two scripts agree. It does not carry the comparison against the shipped bot or the comparison against v21 on the older lines.

*Recommended action.* Preferred fix, in /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/eval_v3.py:
- Line 180: write to a name eval_v2.py cannot produce, e.g. "results_v3_places.json".
- Have shipped() and retrained() return their numbers and dump them alongside the matcher: {"matcher": m, "shipped": {raw, strip, strip_minus_raw}, "retrained": {gate: {all, v3, older}}, "bootstrap": {vs_shipped: {top, family}, vs_v21_older: {top, family}}}.
- This edits evaluation code after the blind lines were seen, so by HANDOFF section 6 it needs a frozen.txt entry: the new eval_v3.py hash plus a comment that only the output file changed and the regenerated eval_v3.log is byte-identical to hash 90881556... (frozen.txt:159). No number changes, so nothing needs an "after tuning" mark.

Minimum if the code is left alone, one sentence for the v3 write-up (COOP-BOT.md section v3 / HANDOFF section 4): "results_v3.json is written both by eval_v3.py (matcher summary only) and by `COOP_TAG=v3 python eval_v2.py` (study tables), last run wins; the numbers of record for sections B and C are in eval_v3.log (hash in frozen.txt) and recompute from results_v3_probs_{r6,cs,stt}.json and results_v3_shipped.json with `COOP_TAG=v3 python eval_v3.py`."

### train-eval-code #8: Author r6's two v3 annotator files are byte-identical, and r6's v3 lines changed surface style

Reviewer: note, data. Affects: Wording 'author + 2 annotators' for r6 v3; wrong family 1.3% by one line; 'unanimous on 150'

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

Every checkable statement in the finding holds, but "one reading counted twice" is an inference the tree cannot settle, and the 2.0% / 4.0% figures are a worst-case bound, not a corrected value.

1. Identical files. annot/v3/author_r6_ann1.json and author_r6_ann2.json are the same bytes. All six v3 annotation files are script-serialised (indent 1, same key order), so byte identity means "all 50 entries equal". That is two entries more agreement than cs v3 (48/50). cs v2 already had 40/40 equal entries in two differently formatted files, which were demonstrably separate writes. The r6 files were written 11 s apart, the same pattern as cs (10 s) and stt (16 s), which fits two separate annotator runs rather than one result saved twice. What is established is that the second r6 reading adds no information; whether it is a copy or full agreement is unknown.

2. How alternatives get accepted. No author file in v1, v2 or v3 has an "ok" field, so the author's accept set is always just the intent. An alternative intent is therefore accepted only when both annotators list it. For r6 v3 that happens automatically on 7 lines (003, 012, 019, 025, 027, 043, 046). With two distinct annotators, cs and stt get 6 such lines each, with one further line from each annotator alone, so the r6 widening is the normal mechanism at 7/7 instead of about 6/8.

3. Effect on scores. Only r6v3_003 changes a verdict (truth NONE, both bots answer WAIT with p about 0.97). With the r6 annotation counted once:
   - re-trained ens3: near 89.3 / 90.0 (top / family) instead of 90.0 / 90.7; wrong family 3/150 = 2.0% instead of 1.3%;
   - shipped: near 82.7 instead of 83.3; wrong family 6/150 = 4.0% instead of 3.3%;
   - the differences stay +10.7 [+3.3, +18.7] and +11.3 [+4.0, +19.3], because both bots lose the same line;
   - out-of-fold thresholds do not move.
   Intent truth, target truth and training labels are unaffected: the author equals the annotation on intent, target, timing and reference on 50/50, and training uses the majority intent. An independent second annotator would probably also have listed WAIT: both distinct stt annotators did on the analogous sttv3_012, and the spec defines WAIT as "cancel the last order".

4. Style. All 50 r6 v3 lines start with a capital and end with a full stop. r6 v1 has 8/121 capital starts and 0 final stops; r6 v2 has 4/40 and 0; the 383 v3 seeds have 2 and 0; cs v3 has 3/50 and 0; stt v3 has 0 and 0. For the shipped model this style is not what drives the r6 result: with the first letter lowercased and the final stop removed, r6 goes from 39/50 near with 1 wrong family to 41/50 with 2, so near minus 2 x wrong family is unchanged. The re-trained leave-r6-out fold could not be tested because those models are not on this machine.

5. Documentation. COOP-BOT.md carries the general caveat for v1 and v2 that authors and annotators are agents of one model family. Nothing mentions the identical r6 v3 pair, and HANDOFF.md line 98 says only "2 annotators per author".

Context that makes the r6 block matter more than a one-third share: the whole re-training gain sits on r6 (shipped 39/50 to re-trained 49/50), while cs goes 46 to 45/46 and stt 40 to 41.

*Recommended action.* Write-up only; do not re-annotate.

1. In the v3 section still to be written in COOP-BOT.md, under caveats, and as a clause on HANDOFF.md line 98, add:
"For author r6 the two annotator files are identical (all 50 entries; cs 48/50), so the second r6 reading adds no information. Authors give no 'ok' list, so an alternative intent is accepted only when both annotators list it; for r6 that is automatic (7 lines). Counting the r6 annotation once changes one line (r6v3_003, NONE, both bots answer WAIT): wrong family 2.0% instead of 1.3% for the re-trained bot and 4.0% instead of 3.3% for the shipped one, near 89.3 / 90.0 and 82.7; the differences +10.7 and +11.3 and their intervals do not change."

2. In the same caveat list add:
"All 50 r6 v3 lines are written as sentences (capital first letter, final full stop), unlike r6's v1 and v2 lines (12/161 and 0/161) and the seeds (0/383 with a final stop). For the shipped model, removing the capital and the stop changes 3 r6 picks (39/50 to 41/50 near, 1 to 2 wrong family), the same near minus 2 x wrong family."

3. Wherever "unanimous on 150" from eval_v3.log is quoted, say that for r6 it means the author equals one annotation.

4. Do not replace author_r6_ann2.json. That would change labels after the blind lines were seen and would have to be logged in frozen.txt, with both numbers reported; the measured worst case is one line.

5. For the next blind round, record a run id per annotator so that agreement can be told apart from duplication.

### train-eval-code: checked and found right

- batcher() equals the tokenizer call: 1200 of 1200 random batches (sizes 1, 5, 16, 64; three line pools) give identical input_ids, attention_mask and token_type_ids, same dtype, as tok(batch, truncation=True, max_length=64, padding=True, return_tensors='pt'); the longest of the 1032 lines is 24 tokens, so truncation never triggers; the hub tokenizer and the shipped model's tokenizer give the same ids on all lines (scratch h_batcher.py)
- Step and warm-up counts: each fold trains on 805 lines = 51 steps x 20 epochs = 1020 steps, warm-up 102; out-of-fold sub-folds 644 lines = 41 steps x 25 epochs = 1025 steps (0.5% off), warm-up 102; final: 1016 lines, 1280 steps, sub-folds 1275. The scheduler steps once per optimizer step and the loop count equals the scheduled total
- Seeding and shuffling: random.seed and torch.manual_seed are reset inside every train_predict; the out-of-fold split uses its own Random(1000+seed); data order is the same as train_bert.py's recipe; torch.manual_seed also reseeds the MPS generator (same dropout mask twice)
- Fold composition in results_v3_probs_{r6,cs,stt}.json, all 9 runs: test = the held-out author's 211 lines + 16 probes; out-of-fold = 422 lines of the other two authors + 383 seeds; the held-out author is never in the out-of-fold set; seed ids equal the current seed file; _meta says 633 items, 383 seeds and the fixed recipe; 9288 probability rows have 24 values, no NaN, sum to 1 within 3e-7
- Thresholds come from out-of-fold predictions only: eval_v2.load_runs drops 'seed_' keys, deploy() fits per fold on the two training authors and applies to the held-out author (top 0.62 / 0.58 / 0.58, family 0.60 / 0.58 / 0.52 for r6 / cs / stt); final() excludes seeds from fitting (train_v2.py:174) and picks the gate by the same criterion, ties to top
- Headline classifier numbers reproduced with independent code from the stored probabilities: shipped 125/150 near, 5 wrong family; re-trained ens3 top 135/150, 2; family 136/150, 2; paired bootstrap of the score +10.7 [+3.3,+18.7] and +11.3 [+4.0,+19.3]; older 483 lines score 86.3 vs 86.3 (top) and 86.5 vs 86.7 (family)
- The shipped bot's probabilities on the 150 v3 lines reproduce on this Mac (CPU): v3_shipped.py in the scratch copy gives max |dp| 2.8e-6 against results_v3_shipped.json, 0 picks differ, raw and strip; the stored strip texts equal what the current (v2) rules produce on all 150 lines, so section B is valid for the current matcher
- The seed generator is in the repo and reproducible: make_spec_v3.py (random.Random(3)) regenerates seed_commands_v3.json and blind/spec_v3.json identical after parsing; bytes differ only by CRLF; 150 templated seeds over 19 intents as the file's note says; disk hashes equal frozen.txt (9e520412..., 746899c2..., 52d124bb...)
- Seed label consistency apart from finding 1: no seed text appears twice, none carries two labels; all 150 templated seeds are predicted to their own label out-of-fold; no v3 blind line equals a seed or an older line; no duplicate v3 lines
- The comparison is conservative in one respect: the shipped bot was trained on the held-out author's v1 and v2 lines, the re-trained fold model on none of that author's lines
- Older lines: no measurable harm with either gate (score 0.0 and -0.2, near -1.7 [-3.7,+0.4] and +0.6 [-1.4,+2.7]); on the 119 older lines where the matcher finds a place, near 90.8 / 92.4 (v3 study) vs 92.4 / 89.9 (v21 study)
- The 16 probes are test-only and all 16 are near-correct in every v3 fold (ens3, family gate)
- eval_v3.ens_preds re-import: it removes coop_v2 and eval_v2 from sys.modules before each import, so TAG, the seed file, the results glob and ITEMS are rebuilt per tag (v3: 633 lines, 3 files; v21: 483 lines, 2 files); no cross-tag state found
- Today's train_v2.py edit against the pristine copy: only pick_device / free_cache, 'device' added to the recorded recipe and the v3 wording in trained_on; hyperparameters, shuffling, schedule and the fused flag (CUDA only) are unchanged; nothing reads recipe or trained_on from bot_config.json; the edit is recorded in frozen.txt at 23:40:26 and the hash there (14e1ef1f...) equals the file on disk
- MPS forward path through train_v2.batcher, one member of the shipped ensemble, 166 lines: max |dp| CPU vs MPS 6.7e-6, 0 argmax changes, no NaN (scratch l_mps.py)
- Output directory under COOP_TAG=v3 is models/coop-deberta-v3-ens3-v3 (train_v2.py:167), as HANDOFF section 5 says; 18 trainings = 3 seeds x (5 out-of-fold + 1)
- The gain is not a casing or punctuation artifact: with r6's capital first letter and final period removed the shipped bot scores 41/50 instead of 39/50 on r6 and the pooled score difference stays +10.7 / +11.3 (scratch r_format.py)

## Data, spec and documents (`data-spec-docs`)

### data-spec-docs #1: Held-out author stt repeats the tuning authors' idioms: the whole 90% -> 94% gain of rules v2 comes from two dictionary entries copied from r6/cs lines

Reviewer: major, methodology. Affects: HANDOFF section 4 row '94% на отложенном авторе stt', section 6 'Автор stt — отложенная проверка', and 'unknown_modifier 12 of 12' in eval_v3.log

**Verifier (reproduce): confirmed, minor; reproduced: yes; touches frozen: no**

Every factual part of the finding reproduces.

- **The stt gain.** Rules v2 move stt from 45/50 to 47/50. The two lines that move are sttv3_030 ("bro my ping is through the roof again sorry") and sttv3_034 ("this is not even my main i play on my brother account").
- **What fixes them.** Each is fixed by exactly one v2 vocabulary entry: ignore "through the roof" and lone_not_after "my". The same phrases stand in tuning-author lines of the same kind (other_sense): r6v3_039 "My ping is through the roof tonight..." and csv3_035 "my main got vac banned...".
- **stt's own misses.** None of the three moved: sttv3_023 ("east one"), sttv3_036 ("rough"), sttv3_045 ("second story").
- **unknown_modifier flag.** It goes from 7/12 to 12/12 through rule 1d alone. On stt it goes from 3/4 to 4/4; the gained line is sttv3_018 "the spiral stares". r6v3_040 and csv3_036 both say "the spiral staircase", which the rule 1d comment at locations.py:291 quotes.
- **other_sense.** The 6 lines are "through the roof" x2, "main" as a noun x3 and "table that" x1.

So the +4 points on stt come entirely from lines that repeat idioms of the tuning authors. The 94% is not an independent estimate of how rules v2 do on unseen content. The pre-look figure is 88.0% (stt 90%).

Three qualifications to the reviewer's reading:

1. **The held-out check is not empty.** The v2 additions (4 code rules and at least 10 vocabulary entries) break no stt line. That is real no-harm evidence on an author they were not tuned on. What is missing is evidence that v2 handles new kinds of miss: 0 of 3 fixed.
2. **The "tuned on r6 and cs only" claim is supported.** None of stt's own misses was touched. But stt was held out by discipline, not by blindness: its mismatches are printed in the same eval_v3_rules_v1.log (lines 46-55) the rules were edited from.
3. **"through the roof" changes exact-match on no r6/cs line.** r6v3_039 stays wrong under v2; it only changes from zone roof to qualifier west with flag unsure. The entry's only exact-match effect in the 150 lines is the stt line.

Why minor and not major:

- The numbers are correct as measured, and no project rule was broken.
- HANDOFF already gives 88.0% as the before-look figure and says v2 was tuned on r6/cs.
- The size is 2 lines of 50. Wilson 95% intervals are 78.6-95.7 for 45/50 and 83.8-97.9 for 47/50.
- No model, code or shipping decision depends on it.

What needs to change is the label on one table figure and one sentence in section 6.

A likely cause, not verified: the three authors look like same-model agents working to an identical per-kind quota (each has exactly 20 place, 5 callout, 2 other_sense, and so on; the files were written within a minute of each other). The kinds are defined nowhere in blind/spec_v3.json, so the author prompt is not in the tree.

*Recommended action.* Write-up changes only. No rule, vocabulary, spec, seed or label change.

1. **/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md, section 4, line 106.** Replace "94% на отложенном авторе stt; 96.7% на всех" with: "96.7% на всех (после подгонки); на stt 94% (было 90%): обе добавившиеся строки (sttv3_030 «ping is through the roof», sttv3_034 «my main») повторяют обороты строк r6/cs, по которым правились правила; три собственные ошибки stt (east one, rough, second story) не исправлены; регрессий на stt нет. Слепая цифра сопоставителя — 88.0% (stt 90%)."

2. **HANDOFF.md, section 6, line 175.** After "Автор stt — отложенная проверка." add: "Он отложен по автору, но не по содержанию: обороты у авторов повторяются (through the roof ×2, main как существительное ×3, spiral staircase ×3), а ошибки stt были напечатаны в том же eval_v3_rules_v1.log. Поэтому 94% — цифра «после подгонки», а не слепая."

3. **scripts/coop/frozen.txt.** Append a dated comment line with the same qualification to the entry at line 139. Append only; do not edit the existing line.

4. **The future "v3" section of COOP-BOT.md and DEBERTA-BOT.md.**
   - Give 88.0% (132/150; stt 45/50) as the blind matcher number.
   - Give unknown_modifier 7/12 as blind and 12/12 as after tuning.
   - Give 96.7% and stt 94% as after tuning, with the sentence from item 1.
   - Add a caveat that the authors are agents of one model family writing to the same per-kind quota, so author hold-out does not hold out content.

5. A blind number for rules v2 needs new lines from fresh authors, as HANDOFF section 6 already says for any further edit.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every factual claim in the finding held when I re-derived it. What does not hold is the severity, one inference, and half of the suggested fix.

What stands:
- Rules v2 moved stt from 45/50 to 47/50 through exactly two lines, sttv3_030 and sttv3_034.
- Each depends on one v2 vocabulary entry: ignore "through the roof" and lone_not_after "my".
- Both trigger phrases stand in tuning-author lines of the same kind that were v1 mismatches (r6v3_039, csv3_035).
- None of stt's own three misses moved (sttv3_023, sttv3_036, sttv3_045).
- The unknown_modifier flag went from 7/12 to 12/12 through rule 1d alone; stt's one gain is "the spiral stares", and both r6 and cs wrote "the spiral staircase".
- The three authors have identical kind quotas (2 other_sense, 4 unnamed, 20 place, ...), and the kinds are not defined in blind/spec_v3.json. So stt is in-distribution with r6 and cs: held out by author, not by content.
- The +4 points on stt therefore do not show that the v2 additions carry to unseen wording. stt's differently worded analogues ("second story" against the added "to second" / "on second"; "i said east one" against the report-verb and 5b fixes) stayed wrong.

What is overstated:
- **"Report 88.0% as the blind number" is already done.** HANDOFF.md:105 gives 88.0% as the before-look figure on the row above, HANDOFF.md:106 marks v2 as edited on r6 and cs, and frozen.txt records "94.0%, was 90.0%". Only the idiom overlap is undisclosed.
- **"94% is not evidence that rules v2 generalise" is too absolute.** It is valid held-out evidence of no harm: 0 of stt's 45 right lines regressed, and there are 0 false unknown_modifier flags on stt's 50 lines.
- **The flag sub-claim is weaker than "the same pattern".** Rule 1d is structural, not keyed on "spiral": it fires on words that stand in no blind line and stays silent on plain or neutral ones. "my" is likewise a one-token generic entry; only "through the roof" is a verbatim idiom.
- **Major is too high.** The gain is 2 lines of 50 (exact McNemar p = 0.5; Wilson 95% intervals 78.6-95.7 for 45/50 and 83.8-97.9 for 47/50). No number is wrong, and no classifier, C++ or shipping claim depends on the 94%.

The protocol itself looks honoured: stt's three remaining misses are one-entry fixes that were not made.

*Recommended action.* Write-up only; no rule, vocabulary, spec, seed or label change.

1. /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md, section 4, under the table (row at line 106), add: "94% у stt — это +2 строки к 90% (sttv3_030 «ping is through the roof», sttv3_034 «my main»). Обе повторяют обороты строк r6/cs, по которым правился словарь (r6v3_039, csv3_035). Три собственных промаха stt («east one», «rough», «second story») не исправлены. Слепая цифра сопоставителя — 88.0% (stt 90%). 94% показывает, что правка не навредила чужому автору (0 ухудшений из 45, 0 ложных флагов), а не что новые правила переносятся на новые формулировки. Флаг unknown_modifier: 7 из 12 до правки, 12 из 12 после."

2. Same file, section 6, line 175, append: "Все три автора писали по одной инструкции с одинаковыми видами строк, поэтому stt отложен по автору, а не по содержанию. Слепая цифра для правил v2 требует новых строк от новых авторов."

3. Carry the same two sentences into the future "v3" sections of COOP-BOT.md and DEBERTA-BOT.md: headline the matcher as 88.0% blind and 96.7% after tuning, with stt 94% as a no-harm check rather than a blind figure.

### data-spec-docs #2: seed_commands_v3.json still labels 'get on the roof' and 'go roof' as RAPPEL, against spec_v3; 'get up on the roof' stays RAPPEL after re-training, although HANDOFF says re-training should fix it

Reviewer: major, data. Affects: HANDOFF section 4 sentence about the known v2 error; the section 7 default 'Go to the roof -> MOVE_TO'; what the final v3 model answers to 'get on the roof'

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

Every factual part of the finding reproduces.

**Seeds against the spec.** `seed_commands_v3.json` (hash equals the frozen.txt entry at line 115, frozen before the v3 blind lines) has 'get on the roof' and 'go roof' under RAPPEL. `blind/spec_v3.json` says "Just going to a named place, the roof included, is MOVE_TO". `make_spec_v3.py` only appends templated seeds to the v21 set, so the two old seeds were carried over next to the new MOVE_TO seeds 'go to the roof', 'head to the roof', 'go up to the roof'. The docstring remark "every roof line so far was a rope line" is true for the older blind lines but not for these two seeds.

**Re-training does not fix the line HANDOFF names.** In the leave-one-author-out run, csv3_037 'get up on the roof, I want somebody up top' (MOVE_TO by all three readers) is still RAPPEL at both gates. It is one of only two wrong-family errors behind the reported 1.3%. csv3_031 'get off the roof and come down to the basement' changes from RAPPEL (shipped) to a refusal. Three other roof lines are fixed (r6v3_002, sttv3_028, sttv3_041). So HANDOFF line 111 "Её должно починить дообучение" is contradicted by section C of the log HANDOFF itself cites.

**The seed labels are the outlier.** Held out in the 5-fold out-of-fold pass, 'get on the roof' is read MOVE_TO in 8 of 9 runs and 'go roof' as MOVE_TO in 6 of 9.

**Final model.** `train_v2.py final` trains on `items + seeds` from the same file, so the final v3 model learns 'get on the roof' = RAPPEL next to csv3_037 = MOVE_TO, against the HANDOFF section 7 default.

**Limits of the evidence.**
- That the two seeds cause the csv3_037 error is strongly suggested, not proven; proving it needs a re-train. With the seed in the training folds, csv3_037 came out MOVE_TO in 2 of 3 leave-r6-out out-of-fold runs.
- The reviewer's line references for `make_spec_v3.py` are off: CHANGED is at lines 52-56 and the MOVE_TO templates at 67-68.
- The headline numbers are not affected; they already include this error.

**Smaller parts, also true.**
- `intents_v2.json` still describes RAPPEL as "use the rope, go up to the roof or drop down outside". Only the old LLM-side scripts read `description`; the DeBERTa path uses `label` only.
- No v3 blind line contains "take" in any form. The only 'take <place>' seeds are MOVE_TO ('take yellow / white / brown stairs'), HOLD_OTHER_ANGLE has no place seeds, and the spec uses 'take' for holding. How the bot reads 'take <place>' is untested. This is a coverage note, not a measured error.

*Recommended action.* **1. HANDOFF.md line 111 (documentation only, touches nothing frozen).** Replace "Её должно починить дообучение." with: "Дообучение её не починило: в кросс-валидации csv3_037 «get up on the roof…» остаётся RAPPEL (ens3 0.70 против MOVE_TO 0.25, оба гейта) — это одна из двух ошибок «чужое семейство»; csv3_031 «get off the roof…» стала отказом (MOVE_TO 0.55 < 0.58). Три другие строки про крышу исправлены. Вероятная причина: в seed_commands_v3.json остались seed-команды «get on the roof» и «go roof» с меткой RAPPEL, что противоречит spec_v3."

**2. HANDOFF.md line 192 (section 7).** Add: "Пока seed-команды «get on the roof» / «go roof» размечены как RAPPEL, финальная модель v3 на эти фразы ответит RAPPEL."

**3. Seed fix (owner's decision; touches frozen material).** In `scripts/coop/make_spec_v3.py`, after loading `seed_commands_v21.json`, remove 'get on the roof' and 'go roof' from RAPPEL (move them to MOVE_TO or drop them) and regenerate `seed_commands_v3.json`. Record the change in `scripts/coop/frozen.txt` as made after the v3 blind lines were read. Re-run the v3 cross-validation and the final training, and mark the roof result and the re-trained classifier numbers as "после подгонки" until new blind lines exist. The final v3 training now running uses the old seed file: either retrain, or ship it with this recorded as a known deviation.

**4. intents_v2.json (low priority).** Bring the RAPPEL description in line with spec_v3 when it is next regenerated. The classifier does not read it.

**5. 'take <place>'.** Ask the owner whether "you take the south window" is HOLD_ANGLE / HOLD_OTHER_ANGLE and "take blue" is MOVE_TO. Until new blind lines cover it, state in the v3 write-up that it is untested. Any new seed for it is also a frozen-material change.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: yes**

Every fact in the finding reproduces; my defence only lowers the severity and narrows the fix.

**What holds**
- `seed_commands_v3.json` keeps two rope-less roof seeds under RAPPEL: 'get on the roof' (seed_RAPPEL_3) and 'go roof' (seed_RAPPEL_7). They are inherited unchanged from v1/v21, where the spec still listed "go up to the roof" under RAPPEL.
- `make_spec_v3.py` sharpened the spec ("Just going to a named place, the roof included, is MOVE_TO") and added the MOVE_TO seeds 'go to / head to / go up to the roof' in the same frozen step, but did not revisit the two old seeds.
- These two seeds are the only training lines that say roof = RAPPEL with no rope word. All five older RAPPEL study lines that mention the roof carry a rope word (rope, rappel/repel, clip...inverted).
- In the leave-one-author-out run, csv3_037 'get up on the roof, I want somebody up top' (three readers MOVE_TO) is RAPPEL in all three seeds; ens3 gives RAPPEL 0.70 / MOVE_TO 0.25.
- csv3_031 gives MOVE_TO 0.55 / RAPPEL 0.42, below 0.58, so the bot refuses.
- The HANDOFF.md:111 forecast ("Её должно починить дообучение") is therefore false for the very line it quotes, and section 4 never revisits it after reporting the cross-validation as done.
- The final v3 model trains on the same seed file (`train_v2.final` -> `V.seed_items()` -> `seed_commands_v3.json`).
- The 'take' point is also true: no v3 blind line contains the word, and the only place seeds with it are three 'take <colour> stairs' MOVE_TO lines.

**What limits it**
- No reported number is wrong. csv3_037 is already one of the two wrong-family lines behind 1.3%, and csv3_031 is already a miss inside 90.0 / 90.7.
- Re-training did fix most of the class. Of the six v3 lines that name the roof with truth MOVE_TO, the shipped v2 bot gets 1 right (2 RAPPEL, 3 refused); the re-trained ensemble gets 4 right (1 refused, 1 RAPPEL).
- The literal section 7 example holds: the seed 'go to the roof' is MOVE_TO in 9 of 9 out-of-fold runs. The contradiction is confined to 'get on the roof', 'go roof' and close paraphrases.
- Moving the two seeds is not shown to be sufficient. 'roof' also co-occurs with RAPPEL in legitimate rope lines such as 'get on the rope and climb up to roof', and I ran no training to test it.
- The old seeds were not kept on purpose: no document says so, and `frozen.txt` line 109 only says "seed set v3 (v21 + templated location seeds)".

This is an oversight at freeze time with a narrow effect: one place, one phrase family, 1 of 150 blind lines as a wrong-family action. Hence minor, not major. The 'take <place>' gap is a coverage note, not a defect.

*Recommended action.* **1. Write-up only (no frozen material touched)**
- Replace `HANDOFF.md:111` with the measured result: "Известная ошибка модели v2: «get up on the roof» → RAPPEL. Кросс-валидация её не починила: csv3_037 остаётся RAPPEL (0.70), csv3_031 — отказ (MOVE_TO 0.55 < 0.58). Из шести строк «крыша как место» верно 4 (у боевой v2 — 1). Вероятная причина: в `seed_commands_v3.json` под RAPPEL остались seed-команды «get on the roof» и «go roof» без слова про верёвку, вопреки `spec_v3`."
- Narrow `HANDOFF.md:192` (section 7) to say the default holds for «go to / head to / go up to the roof», while «get on the roof» and «go roof» are still trained as RAPPEL.
- Carry the same two sentences into the future "v3" section of `COOP-BOT.md`.

**2. Seed change (optional, owner decision, touches frozen material)**
- Do not edit `seed_commands_v3.json` in place. Follow the v21 precedent (`make_seeds_v21.py`, `frozen.txt` line 83).
- Write a new generator and a new seed file under a new `COOP_TAG` that moves 'get on the roof' and 'go roof' to MOVE_TO, or drops them.
- Hash both into `frozen.txt` with a comment that the change was made after the v3 blind lines were read.
- Re-run the leave-one-author-out cross-validation under the new tag and report the roof lines and any changed totals as "после подгонки", leaving the v3 study files as they are.
- Do not promise that this fixes csv3_037; it is untested.
- Until this is done, the final v3 model will most likely answer RAPPEL to 'get on the roof', and the write-up should say so.

**3. 'take <place>'**
- Add one sentence to the v3 limitations: no blind line tests it, and the only place seeds with the word are 'take <colour> stairs' = MOVE_TO.
- Any new 'take' seeds belong in the same post-blind seed set as item 2, or should wait for new blind lines.

**4. `intents_v2.json`**
- Leave the RAPPEL description as is; the classifier does not read it. Mention it only if the file is touched for another reason.

### data-spec-docs #3: The 'difference' figures in HANDOFF section 4 are score (near minus twice wrong-family), not near, and the re-training gain comes from one author

Reviewer: major, numbers. Affects: HANDOFF section 4, second table and the bullets under it; the conclusions 'дообучение нужно' and 'модель читает сырую строку'

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

Every number in the finding reproduces. The HANDOFF section 4 figures are copied correctly from eval_v3.log, but the log labels them "score" (near - 2 x wrong family) and HANDOFF drops the label, next to a table that shows only near and wrong family.

**Unit of the differences (150 v3 lines)**

| comparison | score | near |
|---|---|---|
| re-trained ens3/top - shipped | +10.7 [+3.3, +18.7] | +6.7 [+1.3, +12.7] (125 -> 135) |
| re-trained ens3/family - shipped | +11.3 [+4.0, +19.3] | +7.3 [+2.0, +13.3] (125 -> 136) |
| strip - raw (shipped bot) | -3.3 [-8.0, +0.0] | -2.0 [-4.7, +0.0] (125 -> 122) |

- Wrong family goes 5 -> 2 with re-training and 5 -> 6 with strip.
- Strip rewrote 58 of the 150 lines and changed the answer on 3, all author stt, all worse for strip. The reviewer's [-8.0, +0.0] is the score interval, not the near interval.
- HANDOFF line 108 ("хуже на 3.3 пункта") and line 121 ("Разница ... +10.7 / +11.3") name no metric. HANDOFF never defines score; COOP-BOT.md names it every time (lines 168, 416, 440).

**By held-out author (50 lines each; near / wrong-family counts)**

| author | shipped | ens3 top | ens3 family | score diff top / family |
|---|---|---|---|---|
| r6 | 39 / 1 | 49 / 0 | 49 / 0 | +24.0 [+12, +38] both |
| cs | 46 / 3 | 45 / 1 | 46 / 1 | +6.0 [-8, +22] / +8.0 [-4, +24] |
| stt | 40 / 1 | 41 / 1 | 41 / 1 | +2.0 [-8, +12] both |

- cs and stt together (100 lines): near +0.0 [-6, +6] / +1.0 [-5, +7]; score +4.0 [-4, +14] / +5.0 [-3, +14].
- r6 supplies all 10 of the net near gain with the top gate, 10 of 11 with the family gate, and about three quarters of the score gain (12 of 16 units top, 12 of 17 family).
- The rest of the score gain is cs wrong family dropping 3 -> 1; its interval includes zero.
- Near-correct flips: 15 fixed (10 r6, 1 cs, 4 stt); 4 broken with the family gate, 5 with top.
- Broken lines, all now refused: csv3_000, sttv3_014 and sttv3_019 ("beach"), sttv3_038 ("repel"), plus csv3_049 with the top gate only.

**Where the reviewer's wording needs tightening**

- sttv3_038: the shipped bot picked VAULT_WINDOW for a RAPPEL line. That is near-correct by family only, not exact.
- "Comes from one author" is exact for near and about 3/4 for score.
- "Not established for cs or stt" means not shown, not shown absent: 50 lines per author gives wide intervals.
- The comparison is tilted against re-training. The shipped model was trained on all three authors' 483 older lines; each fold model never saw its held-out author.

The decision to train the final v3 model is not overturned: the pooled intervals exclude zero for both near and score, and the older lines show no harm. What changes is the strength and the unit of the written claim.

*Recommended action.* Text-only changes in /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md section 4, carried into the future v3 section of COOP-BOT.md and DEBERTA-BOT.md. No rule, vocabulary, spec, seed or label changes.

1. Line 108, replace "хуже на 3.3 пункта" with: "не лучше: попадание 81.3% (−2.0), чужое семейство 4.0%; критерий (попадание − 2 × чужое семейство) −3.3 [−8.0, +0.0]; из 58 переписанных строк ответ изменился на 3, все у автора stt".

2. Line 110, replace the conclusion with: "Вывод: вырезание названий пользы не даёт (разница в пределах шума, 3 ответа из 150), поэтому классификатор получает сырую строку."

3. Line 121, name the metric and give both: "Разница по критерию «попадание − 2 × чужое семейство»: +10.7 [+3.3, +18.7] (top) и +11.3 [+4.0, +19.3] (family). Само попадание: +6.7 [+1.3, +12.7] и +7.3 [+2.0, +13.3]."

4. Under it, add the per-author rows:
   - r6: 39 -> 49 из 50, критерий +24.0 [+12, +38].
   - cs: 46 -> 45 (top) / 46 (family), чужое семейство 3 -> 1, критерий +6.0 [−8, +22] / +8.0 [−4, +24].
   - stt: 40 -> 41, критерий +2.0 [−8, +12].
   - Then the sentence: "Прирост попадания целиком даёт автор r6; на cs и stt вместе (100 строк) попадание +0.0 / +1.0, критерий +4.0 [−4, +14] / +5.0 [−3, +14], то есть не показан. Дообучение теряет строки, которые боевой бот брал (теперь отказ): csv3_000, sttv3_014, sttv3_019, sttv3_038 (у боевого — VAULT_WINDOW, верно только по семейству), при гейте top ещё csv3_049."

5. Add the caveat: "Сравнение смещено против дообучения: боевой бот обучен на старых строках всех трёх авторов, а модель каждого фолда отложенного автора не видела."

6. Line 123, soften the conclusion to: "Вывод: дообучение не вредит старым приказам и даёт прирост на одном авторе из трёх; финальная модель v3 — следующий шаг."

Optional: have scripts/coop/eval_v3.py retrained() and shipped() print the near difference beside the score difference and the per-author rows. That is evaluation code only; record its new hash as a new entry in frozen.txt, with the metric named, rather than editing line 158.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every number in the finding reproduces. Two of its inferences do not hold: the conclusions it says are affected survive, and the "three stt lines lost by re-training" cannot be attributed to re-training.

**What stands**
- **Metric not named.** HANDOFF.md:121 ("Разница на строках с местами: +10.7 ... / +11.3 ...") and :108 ("хуже на 3.3 пункта") are differences in the owner's criterion, near − 2 × wrong family. They sit under tables whose columns are near and wrong family, and HANDOFF never names the criterion.
- **It is documented elsewhere.** eval_v3.log:35 and :82-83 print the word "score"; COOP-BOT.md:168 and DEBERTA-BOT.md:136 define it. This is a wording omission in HANDOFF, not a wrong number.
- **Near differences.** +6.7 [+1.3, +12.7] for top (125 → 135 of 150) and +7.3 [+2.0, +13.3] for family (125 → 136). Both intervals exclude zero.
- **Raw against strip.** 3 of 150 answers differ (58 lines had their text changed), all three against strip. Near is −2.0 [−4.7, +0.0], score −3.3 [−8.0, +0.0], exact sign test p = 0.25. That is "strip is not better", not a measured 3.3-point loss.
- **Gain concentrated in r6.** With the family gate, 15 lines are fixed and 4 broken; 10 of the 15 are r6.

| author | near, shipped → re-trained (family gate) | score difference |
|---|---|---|
| r6 | 39 → 49 of 50 | +24.0 [+12, +38] |
| cs | 46 → 46 (45 with top) | +8.0 [−4, +24] (top: +6.0 [−8, +22]) |
| stt | 40 → 41 | +2.0 [−8, +12] |
| cs + stt | 86 → 87 of 100 (86 with top) | +5.0 [−3, +14] (top: +4.0 [−4, +14]) |

A permutation test on the per-author spread gives p ≈ 0.01–0.02 for near and ≈ 0.06–0.07 for score, so the heterogeneity is unlikely to be chance. On cs + stt, wrong family goes 4 → 2.

**What does not stand**
- **"дообучение нужно" is not overturned.** The pooled gain excludes zero in either metric, wrong family goes 5 → 2, and the 483 older lines are unchanged. The per-author rows are a post-hoc split with 50 lines each, and cs had only 4 lines left to gain.
- **"модель читает сырую строку" is not overturned.** The decision only needs strip not to be better: 0 lines fixed, 3 broken.
- **The three lost stt lines are confounded.** Section C compares a final model trained on all three authors' 483 older lines (train_v2.py:15 "final: train on every line + seeds") with leave-one-author-out folds that never saw the held-out author. That asymmetry works against the re-trained model.
  - The mis-hearings "beach" and "repel" occur only in stt's older lines (5 and 1 lines; 0 in the seeds).
  - The v21 leave-one-author-out study, with no places at all, also refuses stt's "beach" lines: stt_008 and sttv2_035 on both gates, stt_022 on top.
  - On sttv3_014 and sttv3_019 the shipped model gives BREACH 0.87 and 0.99; the leave-stt-out fold has family confidence 0.42 on both.
  - On sttv3_038 the shipped bot did not have it right: it picked VAULT_WINDOW for RAPPEL, which counts as near only through the family.
  - The final v3 model is not on this machine, so whether it keeps these lines is untested.

Severity is minor: a one-line labelling fix plus a missing breakdown, with no conclusion or decision changed.

*Recommended action.* Documentation only; no rule, vocabulary, spec, seed or label changes.

1. **HANDOFF.md:121** — replace with: "Разница по критерию владельца (попадание − 2 × чужое семейство), парный бутстрэп: +10.7 [+3.3, +18.7] для top и +11.3 [+4.0, +19.3] для family. По одному попаданию: +6.7 [+1.3, +12.7] и +7.3 [+2.0, +13.3]."
2. **HANDOFF.md, new bullet after it** — "По авторам (family): r6 39 → 49 из 50, cs 46 → 46, stt 40 → 41. Из 15 исправленных строк 10 принадлежат r6; на cs и stt вместе попадание 86 → 87 из 100, чужое семейство 4 → 2. Сравнение несимметрично: боевой бот обучен на старых строках всех трёх авторов, дообученный оценён leave-one-author-out, поэтому три потерянные строки stt («beach», «repel») нельзя относить на счёт дообучения до проверки на финальной модели."
3. **HANDOFF.md:108** — change the cell to "критерий −3.3 [−8.0, +0.0]; попадание 83.3 → 81.3; отличаются 3 ответа из 150, все три в минус".
4. **HANDOFF.md:110** — change to "Вывод: вырезание названий не помогает, модель читает сырую строку."
5. **Future v3 section of COOP-BOT.md and DEBERTA-BOT.md** (HANDOFF step 5) — carry the same wording.
6. **When models/coop-deberta-v3-ens3-v3 arrives** — run it on sttv3_014, sttv3_019 and sttv3_038 and report whether they are kept.
7. **Optional, scripts/coop/eval_v3.py** — print the near difference and per-author rows next to the score difference in sections B and C. It is evaluation code hashed in frozen.txt:121, so record the new hash there; it changes no frozen material.

### data-spec-docs #4: annot/v3/author_r6_ann1.json and author_r6_ann2.json are the same file, and no annotator ever differs from an author on intent or target

Reviewer: major, data. Affects: HANDOFF section 4 'по 2 аннотатора на автора'; the truth of the 50 r6 lines (in practice one line, r6v3_003, where a WAIT answer counts as right through the 'ok' list); how 'unanimous 150/150' may be read

**Verifier (reproduce): confirmed, minor; reproduced: yes; touches frozen: yes**

Every factual sub-claim reproduces. I rate it minor, not major, because the worst-case effect is one line of 150 and no comparison moves.

1. **Identical files.** `annot/v3/author_r6_ann1.json` and `author_r6_ann2.json` are byte-identical (sha256 07378aec...), and `frozen.txt` lines 134-135 record that same hash twice in the 2026-10-03T21:00:44 block. They were identical when frozen.

2. **Loaded as two readers.** `coop_v2.load_items` (lines 143-147) only asserts that two files exist, so the r6 reading is counted twice. `accept` (line 96) is "listed by at least 2 readers", so the r6 annotator's `ok` list alone widens the accepted set on 7 r6 lines. Six of those seven alternatives are in a different family from the majority intent.

3. **One annotator or two?** The files cannot settle this. All six v3 annotation files come from the same serializer (CRLF, indent 1, no trailing newline), so byte identity only proves identical content. The two r6 files were written 11 s apart (21:00:21 and 21:00:32), like the other pairs. Identical content from two independent readers has a precedent: the v2 cs pair agrees on 40/40 records. Either way the third r6 reader adds no independent information, and "2 annotators per author" (HANDOFF.md:98, frozen.txt:125) cannot be shown for r6.

4. **Agreement with the author.** Over all 150 lines every annotator file equals the author on intent, whole target, unknown_modifier and timing. The v3 truth (intent and target) is therefore the author's own label on every line, and "unanimous on 150" (eval_v3.log:1 and :3) carries no label-quality information beyond same-family agreement.
   - The only departure is `reference`: stt ann1 says "this" on 30 lines where the author says "none".
   - That field is not used by any v3 score, and spec_v3 is ambiguous for a named place.
   - I found no sign of label leakage: the r6 "this"/"none" split follows a simple rule (NONE lines get "none").

5. **Numeric impact (worst case).** If the duplicated reader contributed no `ok` alternatives, exactly one line flips in each headline row: r6v3_003 (truth NONE, bot answers WAIT).

   | row | as reported (near / wrong family) | worst case |
   |---|---|---|
   | shipped, raw input | 83.3 / 3.3 | 82.7 / 4.0 |
   | re-trained ens3, top gate | 90.0 / 1.3 | 89.3 / 2.0 |
   | re-trained ens3, family gate | 90.7 / 1.3 | 90.0 / 2.0 |

   - Unchanged: matcher numbers, raw-vs-strip gap, +10.7 [+3.3,+18.7] and +11.3 [+4.0,+19.3], and the older-lines 0.0 / -0.2.
   - A genuinely independent second reader might well also list WAIT there: sttv3_012 has it from both annotators, csv3_008 from one of two.
   - The single-model seed 2 row moves by two lines; it is not a headline number.

*Recommended action.* **1. Write-up (touches nothing frozen).** In HANDOFF.md line 98, and in the future v3 section of COOP-BOT.md, replace "по 2 аннотатора на автора" with a statement along these lines:

"Two annotators per author for cs and stt. For r6 the two annotation files are byte-identical (same hash twice in frozen.txt), so r6 effectively has one independent annotator. No annotator differs from the author on intent or target on any of the 150 lines, so the v3 truth is the author's label, and 'unanimous 150/150' is agreement between agents of one model family, not a label-quality measure. Counting the r6 annotator once changes one line (r6v3_003, NONE answered WAIT): shipped 83.3/3.3 -> 82.7/4.0, re-trained 90.0/90.7 -> 89.3/90.0 near and 1.3 -> 2.0 wrong family; the differences against the shipped bot and all matcher numbers are unchanged."

Add a one-line note to frozen.txt recording that the r6 pair is identical.

**2. Code (reporting only).** In `scripts/coop/coop_v2.py` `load_items`, next to the `assert len(anns) == 2` at line 145, add a check that the two annotation files differ, or at least print a warning, so a duplicate cannot enter silently again.

**3. Optional re-annotation (this is the part that touches frozen labels).** Have one fresh blind annotator read `blind/v3/author_r6_lines.json` with `blind/spec_v3.json` only.
- Store it as a new file and keep the original; do not silently overwrite ann2.
- Record it in frozen.txt as done after the results were seen.
- Report the re-scored numbers as "after re-annotation".
- This affects r6 lines only. The stt held-out matcher number (94%) is untouched unless target labels change, and r6 was already a tuning author for rules v2.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

The facts hold; the inference and the severity are overstated.

TRUE:
- annot/v3/author_r6_ann1.json and author_r6_ann2.json are byte-identical, and frozen.txt:134-135 records the same sha256 for both in the 21:00:44 block, so they were identical when frozen.
- coop_v2.py:143-147 loads them as two readers. On 7 r6 lines (003, 012, 019, 025, 027, 043, 046) an `ok` intent enters `accept` only because both files list it; the author files carry no `ok` field.
- All six v3 annotation files agree with the author on intent, whole target, unknown_modifier and timing on 150/150 lines. The v3 truth is therefore the author's label on every line.
- The cs pair differs in two `ok` entries only. stt ann1 says reference 'this' on 30 lines where the author says 'none'. The r6 author says 'this' on 29 lines; the cs and stt authors never do.
- The spec is ambiguous for a named place: 'this' = points at a specific thing, 'none' = names no object.

NOT ESTABLISHED:
- "The same file / one annotator counted twice" is an inference. The tree cannot distinguish one output saved twice from two same-model runs that agreed on everything; the workflow transcript wf_04800970-338 is not on this machine.
- Two things make the second reading live. In v2 the cs pair parses to equal JSON on 40/40 records in two differently formatted files (4286 vs 3489 bytes), so separate annotators have produced identical labels before. The reviewer's "no v1/v2 pair was byte-identical" is true only because of formatting.
- The two r6 files were written 11 s apart (21:00:21, 21:00:32), like the cs pair (10 s) and the stt pair (16 s), each pair about a minute after its author file. All six v3 files share one serialization, so equal labels give equal bytes.
- Either way, the second r6 file adds no information beyond the first.

IMPACT (bounded, small):
- If the r6 `ok` lists are not counted, exactly one line changes: r6v3_003, a negated order where both bots answer WAIT.
- Shipped raw goes from 83.3 near / 3.3% wrong family to 82.7 / 4.0%.
- Re-trained ens3 goes from 90.0 / 90.7 near and 1.3% to 89.3 / 90.0 and 2.0%.
- Unchanged: +10.7 [+3.3,+18.7], +11.3 [+4.0,+19.3], strip minus raw -3.3, the older-line comparison, and every matcher number (targets agree on 150/150).
- Training labels use `maj` only (train_v2.py:89-91, 123), so no model changes.
- No v3 number reads reference or timing truth.
- Accepting WAIT on a negated order matches the project's own probes (coop_v2.py:64-65) and sttv3_012, where two distinct annotators both list it.

DOCUMENTATION:
- "Unanimity is agreement inside one model family" is a standing caveat for v1 and v2 (COOP-BOT.md:57 and :501). The v3 write-up does not exist yet (HANDOFF section 5, items 4-5).
- HANDOFF.md:98 "по 2 аннотатора на автора" and eval_v3.log:1 "unanimous on 150" carry neither the caveat nor the r6 identity.

*Recommended action.* Documentation only; no label, spec, rule or seed change is needed for any reported number.

1. In the v3 section of COOP-BOT.md (still to be written), and as a clause on HANDOFF.md:98, add:
"Truth: the author's label plus two annotation files per author. The two r6 files are byte-identical (same sha256 in frozen.txt), so the 50 r6 lines have in effect one annotator. No annotator differs from an author on intent, target, timing or unknown_modifier on any of the 150 lines: the truth is the author's label, and 'unanimous 150/150' is agreement inside one model family, not a measure of label quality. If the r6 `ok` lists are not counted, one line (r6v3_003, WAIT on a negated order) flips for both bots: shipped 82.7 near / 4.0% wrong family, re-trained 89.3 / 90.0 near and 2.0%. The differences (+10.7 and +11.3 with their intervals), the matcher numbers and the older-line comparison do not change. Reference labels are inconsistent between readers for named places (the spec does not say whether a named place is 'this' or 'none') and are not used in any v3 number."

2. Append a dated comment to scripts/coop/frozen.txt: review found that the two r6 v3 annotation hashes are equal; no file changed.

3. Optional, and not required for any number: have a fresh blind annotator read blind/v3/author_r6_lines.json. Store it as a new file, keep the old ann2, and log it in frozen.txt as written after the results. This variant does change label material and would count as touching frozen data. At most the 7 r6 `ok` entries can move, which is one line under the current predictions.

touches_frozen is false for items 1-2 and would be true for item 3.

### data-spec-docs #5: The blind lines use almost only the canonical place names: 61 of 95 dictionary phrases, all 8 'named' phrases and 5 intents never occur

Reviewer: minor, data. Affects: Scope of the matcher figures 88.0% / 96.7% / 94%: they measure the rules on canonical names, not the synonym lists. Scope of the 90.0 / 90.7 near: 19 of 24 intents.

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Every count in the finding reproduces, and no project document states the limitation. No reported number is wrong; this is a scope caveat on what the v3 figures measure.

**Dictionary coverage.** Of the 95 object, qualifier, named and zone phrases in locations.json (version 2), 34 occur in the 150 blind lines: object 11/28, qualifier 10/18, named 0/8, zone 13/41, and 3 of 10 ignore phrases. Of the 61 unused phrases, 48 are also absent from the developer set locations_dev.json and none is in the v3 seeds. At least 4 of the 34 used ones ("up a floor", "floor below", "to second", "on second") are in the dictionary only because r6 and cs lines used them and failed under rules v1.

**What the matcher figures measure.** spec_v3.json lists only the canonical names, so 88.0 / 96.7 / 94 measure the rules on spec-primed wording. Where a target was worded outside the dictionary it was missed: 6 of 6 such lines under rules v1, and the two held-out stt lines ("second story", "the rough") still fail under v2. Precision on places outside the map is tested by 6 chatter lines only: the reader target is all-null on just the 6 other_sense lines.

**Author quota and brief.** Each author has the identical kind quota 20/5/5/5/4/4/3/2/2. The kind names occur nowhere except blind/v3/author_*.json and the two eval logs. No brief is in the tree; frozen.txt names only "workflow wf_04800970-338". The same was true for v1 and v2, but there COOP-BOT.md stated the quota in prose (lines 45 and 386-389) and listed "the spec primes the phrases" as a caveat. No such text exists for v3.

**Intent coverage.** By reader majority FOLLOW_ME, HOLD_POSITION, COVER_ME, REVIVE_ME and GO_NOW have zero v3 lines; four of them are not accepted by any single reader. HOLD_OTHER_ANGLE, FALL_BACK, PLANT and WAIT have 3 lines each and DEFUSE has 2. The v3-slice 90.0 / 90.7 therefore covers 19 of 24 intents. The missing five are scored only on the 483 older lines, without place names.

**A concrete consequence the blind set cannot show.** The three new COVER_ME seeds ("cover me from the couch / the table / the east window") get role "from" from the matcher. locations.py defines that role as the place to leave, one the bot is not sent to.

**Corrections to the report.**
- "Almost only canonical" is slightly overstated: stares x9, staircase x4, couch x4, ground floor x4, rooftop x2 and stairwell x1 do occur.
- floor_1 has "level" forms but no "story" forms ("first story" gives no target); only top_floor has both.
- "third floor" is not a matcher gap: the spec has no such zone.
- The unarchived brief is not new to v3.

*Recommended action.* Documentation only; do not edit locations.json, locations.py, the spec, the seeds or the labels.

1. **/Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md, section 4**, under the table of results on the 150 blind lines, add (in Russian, like the rest of the file):
   "Scope of these figures. The authors saw the canonical names in spec_v3.json, and 34 of the 95 dictionary phrases occur in the lines (none of the 8 'named' phrases, none of the -ern / -side forms, 2 of 11 first-floor phrases). The figures measure the rules on canonical wording, not the synonym lists and not places worded outside the dictionary: all 6 such targets were missed under rules v1, and 'second story' and 'the rough' are still missed in the held-out author. Each author wrote the same quota: place 20, zone_object 5, two_places 5, callout 5, on_signal 4, unnamed 4, other_ref 3, negated 2, other_sense 2. FOLLOW_ME, HOLD_POSITION, COVER_ME, REVIVE_ME and GO_NOW have no v3 line, and PLANT, HOLD_OTHER_ANGLE, WAIT, FALL_BACK and DEFUSE have 2-3 each, so 90.0 / 90.7 covers 19 of 24 intents. The seeds 'follow me to X' and 'cover me from X' are not tested by any blind line; the matcher gives 'cover me from X' the role 'from'."

2. **Same file, section 6**, bullet "Слепые авторы и аннотаторы видят только blind/spec_v*.json": add that the authors also received a persona and a quota by kind, and that this brief is not in the archive (frozen.txt records only the workflow id wf_04800970-338).

3. **The v3 section of COOP-BOT.md** (still to be written, HANDOFF section 5 step 5): carry the same caveats, the way the v1 section states the quota (line 45) and "the spec primes the phrases" (lines 64-65).

4. **Next blind round** (needed anyway for rules v2):
   - Save the author brief as a file under scripts/coop/blind/ and record its hash in frozen.txt before the lines exist.
   - Ask for non-canonical wording and for place-naming lines of the five missing intents.
   - If the v3 brief can be recovered on the work machine, archive it and log it as "added after the fact".

5. **Do not add** "second story", "second level", "level two" or "up one floor", and do not change the "from" role for "cover me from X", without new blind lines. Each of those changes touches frozen material and would invalidate the held-out stt figure.

### data-spec-docs #6: HANDOFF and README statements that are wrong or stale on this machine

Reviewer: minor, docs. Affects: HANDOFF sections 2, 3, 4, 5; cpp/coop_intent/README.md; README.md; COOP-BOT.md line 499

**Verifier (both): partly, minor; reproduced: yes; touches frozen: no**

Every factual sub-claim reproduces. None touches a v3 number in HANDOFF section 4. Five sub-items are real, undocumented doc/tooling defects; three are true but already accounted for.

Real and undocumented:
- (a) The pip line in HANDOFF section 2 lacks sentencepiece, yet the same section says one environment with those packages is enough. `train_v2.py:85` loads the tokenizer by hub name (`microsoft/deberta-v3-base`), whose snapshot has only `spm.model`. Without sentencepiece it fails with "ValueError: `tiktoken` is required to read a `tiktoken` file". The bot, `shipped.py` and `export_cpp.py` load `tokenizer.json` from the model dir and work without it. Training also needs the HF Hub or a warm cache, which HANDOFF does not say.
- (b) `python locations.py --dev` on the frozen tree prints "254 dev lines, 5 with a primary target the line's author would not accept" and exits 1 (4 of 16 other-sense, 1 of 6 two-objects). No document, docstring, the `_note` in `locations_dev.json`, or frozen.txt says five failures are the baseline. `locations_dev.json` still has its pre-blind hash. The rules v1 `locations.py` is not on disk, so whether rules v2 changed the dev count cannot be checked.
- (c) `v3_noharm.py` is dead code. Its third mode calls `LOC.normalized(text, "strip+zone")`, and `locations.py:441` asserts `mode == "strip"`. The script would crash before writing, so the "strip+zone" entry in `results_v3_noharm.json` cannot be regenerated. Both files are dated 20:35, before the first v3 freeze entry, and neither is in frozen.txt. No document cites them; only the `shipped.py:4` docstring does. The "483 older lines" claim comes from `eval_v3.py` section C, not from this script.
- (d) HANDOFF section 5 item 6 says the UE5 plan is in `cpp/coop_intent/README.md` and lists places as GameplayTags on level actors and `PlaceRecord` passed to the planner. That README has no word on places, locations or `PlaceRecord`, and lines 152-154 still say "TAKE_COVER and OPEN carry no target". The places part of the plan exists only as those two HANDOFF bullets.
- (g) `export_cpp.py:37`, `check_onnx.py:19` and `gen_tests.py:31` also default to coop-deberta-v3-ens3-v2; HANDOFF step 3 names only `CMakeLists.txt` and `coop_bot.py`. Impact is low because every documented command passes the model dir explicitly. `shipped.py:14` must stay on v2.

True but already accounted for:
- (e) The parity files now hold 77 dialogue lines and 52 decide steps; the cpp README, `COOP-BOT.md:499` and `README.md:21` still say 66 and 38/38. The cpp README also lacks `--location-tests` and `locations.cpp` and has only a Windows build. `coop_bot.py:33` cites a COOP-BOT.md "v3" section that does not exist. frozen.txt records 52/52 and 77/77, and HANDOFF section 5 item 5 lists these doc updates as pending.
- (f) README.md links four absent documents and names 26 absent files; COOP-BOT.md links the absent GAME-BOT.md. HANDOFF section 1 says the archive excludes the laya/Qwen/ollaya experiments and the other scripts folders. README's "Python 3.8+, standard library only" is about the ollaya HTTP harness scripts, not scripts/coop. Only the four missing .md files are unmentioned.
- (h) "На macOS сборка не проверялась" and "Поддержки MPS в нём нет" were correct when HANDOFF was written (22:26). They went stale through today's Mac work; the MPS change is already in the frozen.txt 23:40 entry.

*Recommended action.* Documentation and tooling only; no matcher rule, vocabulary, spec, seed or label changes.

1. HANDOFF.md section 2: add `sentencepiece` to the pip line. Add one sentence: "train_v2.py берёт токенизатор и веса microsoft/deberta-v3-base с HF Hub (нужен интернет или прогретый кэш); без sentencepiece загрузка токенизатора падает. Боту sentencepiece не нужен."
2. HANDOFF.md sections 4 and 5, next to `python locations.py --dev`: state the baseline: "на замороженных правилах v2: 254 строки, 5 известных промахов (4 other-sense, 1 two-objects), код возврата 1; регрессия — это любое изменение этого списка". Do not edit `locations.py` or `locations_dev.json` to make it exit 0: that is a change to frozen material. Also say that the rules v1 dev result was not recorded.
3. `scripts/coop/v3_noharm.py` and `results_v3_noharm.json`: add a line to frozen.txt and HANDOFF saying they are a pre-freeze exploration (20:35) of the dropped "strip+zone" mode, not reproducible with the current `locations.py` and not cited. Alternatively remove both and fix the `shipped.py:4` docstring.
4. HANDOFF.md section 5 item 6: reword so it does not claim the places plan is already in the cpp README, e.g. "План в cpp/coop_intent/README.md (модель через NNE, регэкспы через ICU по ASCII-тени); про места там пока ничего нет — дописать: GameplayTags на акторах уровня, PlaceRecord планировщику как есть".
5. When the cpp README is rewritten (step 5), fix: lines 152-154 "carry no target"; 66 to 77 and 38/38 to 52/52 (also `COOP-BOT.md:499`, `README.md:21`); add `--location-tests` (8570/8570); add `locations.h`/`locations.cpp` and location_tests to the layout and `gen_tests.py` rows; add the macOS/Linux build. The `coop_bot.py:33` reference resolves once the COOP-BOT.md "v3" section exists.
6. HANDOFF.md section 5 step 3: extend the sentence to "поменять модель по умолчанию в CMakeLists.txt, coop_bot.py, export_cpp.py:37, check_onnx.py:19 и gen_tests.py:31; shipped.py:14 оставить на v2 (это база раздела B в eval_v3.py)".
7. HANDOFF.md section 3 and section 5 step 2: replace "На macOS сборка не проверялась" and "Поддержки MPS в нём нет" with the 2026-10-03 Mac results (arm64 build with all six checks passing; `train_v2.py` device choice per the frozen.txt 23:40 entry).
8. Optional: add to HANDOFF section 1 that README.md describes the wider project, and that FINDINGS.md, MODELS.md, GAME-BOT.md, NPC-DECISIONS.md and the ollaya scripts are not in the archive.

### data-spec-docs #7: Matcher rules v1, the files behind the 88.0%, are not in the archive

Reviewer: minor, methodology. Affects: The claim 'matcher exact target 88.0% with rules v1, frozen before the blind lines existed'

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The core of the finding holds; one supporting sentence needs correcting.

Core (confirmed):
- frozen.txt:110-111 records rules v1 as locations.json 9999cc9f... and locations.py 111d1a76... at 20:55:13, before the blind lines (21:00:44).
- No file with either hash exists in the project tree, in coop-bot-code.tar.gz, in coop-bot-models.tar or in the session scratchpad. The archive holds one locations.py and one locations.json, both v2 (890d651a..., b3e9314a...).
- The 88.0% therefore rests on eval_v3_rules_v1.log alone. It cannot be re-run, and nobody can check from the archive that the rules behind it are the ones hashed before the blind lines existed.
- The log's hash was first recorded in the v2 block (21:03:00). Its mtime, 21:02:42, is the same second as the v2 rule files, so file times do not order the v1 run before the v2 edit; only frozen.txt's own text does.
- No document says the v1 files were dropped. Seeds, by contrast, are kept per version (seed_commands_v2 / v21 / v3).

Correction to the reconstruction sentence:
- Undoing only the documented v2 changes gives 136/150 (90.7%), not 132/150. "Documented" means the locations.json _note and the locations.py docstring: rules 1d, 5b, 5c, report verbs, relative-floor phrases, "to second" / "on second", ignore phrases "through the roof" and "table that".
- Reaching the log's 132/150 with the same 18 lines needs three more removals that are documented nowhere: "stack" and "awp" from role_them, "my" from lone_not_after. So the v2 change list is incomplete.
- The 119 vs 120 gap on older lines closes with one further removal, either "wall" from lone_block (r6_050) or "a" from lone_not_after (cs_067). Each then reproduces all 54 lines of section A verbatim.
- So an exact behavioural reconstruction exists, but it is not unique and cannot match the frozen hash. The log pins down v1 behaviour on 633 lines, not the v1 files.

Net: nothing suggests 88.0% is wrong, and the line-for-line reconstruction corroborates it. What is unverifiable is "frozen before the blind lines existed", plus re-running. Severity stays minor.

*Recommended action.* Do not edit locations.py or locations.json (that would change frozen hashes). In order of preference:

1. Recover the originals. On the Windows work machine (editor local history, backups, the agent workflow transcript), find the two files whose sha256 are 9999cc9f656430a9b0c2c27d111073365528932e6dc9686a23c13a12f46d7e7a (locations.json) and 111d1a760364d31368e133d7c861e14f8e79541989b6c684ff8c31fb4c17f2c7 (locations.py). Add them as scripts/coop/locations_v1.json and scripts/coop/locations_v1.py, and append a frozen.txt entry saying these names carry the 20:55:13 hashes. eval_v3_rules_v1.log then becomes re-runnable.

2. If they cannot be recovered, add this to HANDOFF.md section 4 under the row "сопоставитель, правила v1 (до просмотра строк) | 88.0%", and to the future v3 section of COOP-BOT.md:
"The v1 rule files were overwritten by v2 and are not in the archive. 88.0% is the figure in eval_v3_rules_v1.log, which cannot be re-run, and the v1 hashes in frozen.txt cannot be checked against a file. Removing the v2 additions from the current files reproduces section A of that log line for line; this is a reconstruction, not the frozen files."

3. Record the full v2 change list in a frozen.txt comment or the write-up, not in the rule files. Beyond what the locations.json _note and the locations.py docstring list, v2 also added "stack" and "awp" to role_them, "my" to lone_not_after, and either "wall" to lone_block or "a" to lone_not_after.

4. From now on, when a frozen rule or vocabulary file is superseded, keep the old one under a versioned name, as is already done for seed_commands_v2 / v21 / v3.

A reconstructed file must not be named or presented as v1.

### data-spec-docs #8: The 8570/8570 C++ location parity: 7199 of those lines contain no place

Reviewer: note, cpp. Affects: HANDOFF section 4 'Совпадает с Python на 8570 из 8570 строк'

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

The 8570/8570 parity claim is true, and every count in the finding reproduces exactly. Only 1371 of the 8570 lines yield at least one place: 1175 with one target, 185 with two, 10 with three, 1 with five (196 with two or more), 1580 targets in total. Flags: none 1376, unsure 115, unknown_modifier 77, other 12.

Two refinements to the reviewer's wording:

1. "The lines that exercise the port number 1371" is slightly low. 25 of the 7199 no-place lines still contain a vocabulary phrase (16 a suppressed lone qualifier, 9 an "ignore" phrase), so 1396 lines reach any matcher rule. The other 7174 test only the byte tokenizer and the no-hit path; 358 of them contain no ASCII token at all. That is their stated purpose (gen_tests.py:187, "any bytes must be safe"), and they do guard against spurious C++ matches.

2. Of the 1371 place lines, 702 are random word-salad lines from the tokenizer generator. 669 are natural lines: 143 golden, 240 developer regression, 144 blind v3, 142 seed-only.

The port is nonetheless well exercised. The 1371 place lines execute every traced line of Python find(); the two else: lines and one continue reported as unexecuted are consistent with a tracing artefact, and I did not check them further. The 7199 no-place lines add no line coverage. So the equality claim stands and only the denominator overstates the effective test size, by about 6x.

It is not documented in any write-up. HANDOFF.md:95 and frozen.txt:146 give only "8570". No .md, .txt or .log in the tree contains "1371" or "name a place". The number appears only in tool stdout (gen_tests.py:290, coop_cli.cpp:397). The project's own v2 standard does state composition for the other parity sets (cpp/coop_intent/README.md:71-77), so the omission is a real, if small, write-up gap.

*Recommended action.* Documentation only; no change to code, rules, vocabulary or test files.

1. /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md:95 — replace "Совпадает с Python на 8570 из 8570 строк." with: "Совпадает с Python на 8570 из 8570 строк; место названо в 1371 из них (в 196 — два и больше), остальные 7199 — строки токенизаторного набора без мест (проверка, что C++ не находит место там, где его нет, и не падает на любых байтах)."

2. Carry the same wording into the pending v3 sections (HANDOFF.md:152): COOP-BOT.md "v3", DEBERTA-BOT.md, and the parity table in cpp/coop_intent/README.md. Suggested table row: "map places, 8570 lines (1371 name a place: 669 natural lines from golden/dev/blind v3/seeds + 702 generated; 7199 without a place) | 8570 / 8570 identical".

3. Optionally append "(1371 name a place)" to the note at scripts/coop/frozen.txt:146 as a new dated line; do not rewrite the existing one.

When gen_tests.py is re-run for the v3 model, the counts will change. Take the new figure from the "N name a place" line the tools already print.

### data-spec-docs: checked and found right

- spec_v3.json agrees with locations.json on every id: objects, qualifiers and zones are the same sets; spec intents equal the 24 keys of intents_v2.json
- spec_v3 differs from spec_v2 only in RAPPEL, MOVE_TO and the new target modifier (field-by-field comparison)
- HANDOFF section 7 defaults are in the spec: roof without a rope is MOVE_TO; zones up / down / floor_2 exist; floor_1 is 'the 1st (ground) floor'; locations.json maps both 'first floor' and 'ground floor' to floor_1
- Older test lines do not conflict with the sharpened RAPPEL: every v1/v2 roof line labelled RAPPEL has a rope word (r6_000, r6_005, r6_078, cs_038, stt_027); the conflict is in the seeds only
- blind/v3/*_lines.json hold only id and text, with the same texts as the author files; annotation ids match; every label value is legal (intent, object, qualifier, zone, timing, reference; no qualifier together with unknown_modifier; qualifier allowed for its object)
- No v3 line is an exact copy of another line of any version, of a developer regression line or of a seed; 6 seeds of three or more words occur inside a blind line
- On-disk hashes of spec_v3.json, seed_commands_v3.json, make_spec_v3.py, locations_dev.json, the 6 blind and 6 annotation v3 files and locations.json / locations.py v2 equal frozen.txt
- I read all 150 lines against the spec and found no majority intent or target I would overturn; the 15 callouts are NONE with the place as target, as section 7 says; 'watch <place>' is HOLD_ANGLE in seeds and blind lines alike
- Per author: 4 on_signal labels = 4 lines of kind on_signal, 4 unknown_modifier = 4 unnamed, 3 reference 'other' = 3 other_ref
- HANDOFF numbers equal the logs: 88.0 (132/150), 96.7 (145/150), stt 94 (47/50), shipped 83.3 / 3.3, strip score -3.3, re-trained 90.0 / 90.7 and 1.3, +10.7 [+3.3, +18.7], +11.3 [+4.0, +19.3], older lines +0.0 [-3.9, +4.1] / -0.2 [-4.3, +3.7], v2 90.5 / 1.9 (eval_v21.log:8), threshold 0.58 with the family gate (bot_config.json)
- The 88.0% is corroborated: v2 with the documented changes undone gives 132/150, the same 18 mismatches, 7 flags and 43 / 44 / 45 per author
- Rules v2 did not regress the developer set: the same 5 failures under the reconstructed v1 and under v2
- The 'ok' lists hardly matter: scoring on the majority intent or its family alone gives 123 / 134 / 135 near (shipped / top / family) instead of 125 / 135 / 136
- The re-training gain is not a copy effect by the project's own measure: 90 of the 150 v3 lines are novel (cosine below 0.5 to the nearest other-author line or seed); there shipped is 82.2 near and re-trained 88.9 / 90.0. Cross-author overlap of v3 lines (median max cosine 0.35) is lower than in v1 (0.47) and v2 (0.39)
- All 150 templated location seeds keep their label when held out (9 runs); 21 older seeds do not, among them the two roof seeds
- The 'locations' block of models/coop-deberta-v3-ens3-v2/cpp/intent_config.json equals locations.json v2
- coop_bot.py does what HANDOFF says: a 'place:' line under the reply, and a queued order keeps and executes with its own places (pending_places, executed_places)
- 'the other window' is not lost: the regex slot sets other=true in the bot's record; the place flag 'other' fires on 1 of the 9 other_ref lines, and the matcher's 'exact' does not test it
- Paths in HANDOFF section 5 resolve: export_cpp.py, check_onnx.py and gen_tests.py take the bot directory relative to the working directory; train_v2.py final under COOP_TAG=v3 writes models/coop-deberta-v3-ens3-v3; the CMake default generator on macOS gives ./build/coop_cli
- The bot's tokenizer loads without sentencepiece (tokenizer.json is in the model directory) and gives the same ids as the base tokenizer on a probe line

## Gap round: behaviour of the final v3 model (`gap-final-v3-model-behaviour`)

### gap-final-v3-model-behaviour #1: Final v3 bot throws a smoke when told a place is already smoked: '<place> is smoked' -> SMOKE on 47 of 47 places (shipped v2: 7 of 47)

Reviewer: major, training. Affects: HANDOFF.md section 7, first decision (informational callouts stay NONE); the 'acts on non-order 4.2%' of eval_v3.log section C does not cover this kind of line; behaviour of models/coop-deberta-v3-ens3-v3 compared with the shipped v2 bot

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

The core claim holds, re-derived with my own place lists, frames and scripts.

The final v3 ensemble (models/coop-deberta-v3-ens3-v3, family gate, 0.60; trained on this Mac, recipe.device = mps) answers SMOKE to the status callout "<place> is smoked" on 48 of 48 places (24 dictionary, 24 outside), confidence 0.98-1.00, all three members 48/48. The shipped v2 bot acts on 13 of 48, confidence 0.59-0.64, and on 0 of 8 when the line is capitalised with a full stop (NONE 0.95-0.99), where v3 is still 8/8 SMOKE.

- **Reviewer's nine phrasings x 8 places:** v3 acts on 71/72, v2 on 11/72.
- **My own 12 smoke-state phrasings x 8 places:** v3 70/96, v2 25/96.
- **All 208 smoke-state probe lines together:** v3 acts on 181 (87%), v2 on 47 (23%); 134 are v3-only, 0 are v2-only.
- **No place in the line:** "it's smoked" SMOKE 0.73, "site is smoked" 1.00, "it's already smoked" 0.99. v2 does not act on any of them (NONE 0.88, "Say again?" at 0.51, NONE 0.95).
- **End to end:** the real coop_bot.Bot.respond gives action act, intent SMOKE 1.00, reply "Smoke out." for "north door is smoked", while the matcher hands over that door as primary with role=status. locations.py:42-43 says such places are ones the bot is not sent to; decide() never looks at the role.
- **Controls are clean in both models:** orders ("smoke X" etc.) 24/24 SMOKE; callouts ("X is clear", "two on X" etc.) 40/40 NONE.

Corrections to the finding as written:

1. **Not new in v3, but much wider.** v2 already acts SMOKE on some smoke callouts: "enemy smoke on X" 8/8, "my smoke is on X" 8/8, "smoke's already down on X" 7/8, "nice smoke", "good smoke".
2. **Not tied to the token "smoked".** v3 also acts on "there's smoke on X" 8/8 and "X is full of smoke" 8/8 (v2: NONE 8/8 on both), and on "their smoke is fading" and "who threw that smoke".
3. **The causal link to the two rows is unproven** (no training allowed). What is verifiable: of 1016 training rows, the only two with "smoked" are r6v3_041 and csv3_007, both SMOKE by all three readers. Every NONE row containing "smok" is a negation. No non-negated smoke-state callout is labelled NONE anywhere.
4. **"None of the 24 NONE lines is a state callout of this kind" is true for smoke and flash only.** r6v3_011 "They hard breached west door, it's wide open now." is exactly this kind for BREACH. Consistently, v3 reads "X is breached" as NONE 8/8 where v2 gives BREACH 4/8.
5. **The twins reproduce only on the two quoted frames.** "X is flashed": FLASH 6/8 (v2 2/8). "X is blown open": BREACH 6/8 (v2 2/8). Across more frames it is not a general regression: flash 8/32 vs v2 4/32, breach 12/40 vs v2 10/40.
6. **The reviewer's second fix is unsafe.** On the project's 1016 labelled rows, "every place is role=status" matches 13 rows and 8 of them are real orders (e.g. r6v3_021 BREACH "East door's still barricaded, slap a charge on it and blow it.", csv2_030 ENTRY "door's open, push site and clear it"). It would also stop only 51 of the 181 wrongly acted probe lines.

The probe is exploratory and not blind: the NONE reading is the reviewer's and mine, with no annotators. None of the HANDOFF section 4 numbers is invalidated; the gap is that "acts on non-order 4.2%" (1 of 24) does not cover this class.

*Recommended action.* 1. **Write-up.** In HANDOFF.md section 7 (first bullet) and in the future "v3" section of COOP-BOT.md, add: "The final v3 model answers SMOKE to smoke-state callouts ('<place> is smoked': 48 of 48 places, confidence 0.98-1.00; shipped v2: 13 of 48, confidence up to 0.64). The 24 blind NONE lines contain no such line, so 'acts on non-order 4.2%' does not cover them. Exploratory probe, not blind."

2. **Do not switch the default model yet.** Leave MODEL_DIR in scripts/coop/coop_bot.py:39 and the default in cpp/coop_intent/CMakeLists.txt on v2 (HANDOFF section 5 step 3) until this is fixed, or ship v3 with the issue listed as known.

3. **Fix, as a new version.** Create a new seed file under a new COOP_TAG rather than editing seed_commands_v3.json. Add NONE seeds for non-negated utility-state callouts: "<place> is smoked", "<place> is already smoked", "they smoked <place>", "smoke's on <place>", plus flash, breach and drone analogues. Hash it in scripts/coop/frozen.txt, then have blind authors write new lines that include a state-callout kind, then re-train. Any number measured on the current 150 lines after that change must be marked "after tuning".

4. **Do not adopt the reviewer's second suggestion as written.** Declining to act when the only place is role=status would block 8 real orders among the labelled lines and covers only 51 of 181 probe failures.

**Verifier (refute): confirmed, major; reproduced: yes; touches frozen: yes**

The finding stands; I could not refute it on facts, documentation, coverage by reported numbers, or practical relevance.

**What holds**
- The ensemble at /Users/t.losiev/Documents/models_training/project_synth/models/coop-deberta-v3-ens3-v3 (family gate, 0.60) reads a bare state callout with "smoked" as SMOKE at about 1.00, with all three members agreeing. `coop_bot.Bot.decide` returns action "act" ("Popping smoke.") while the matcher marks the place role=status.
- The shipped v2 bot does not act on these lines. On lowercase lines it mostly falls under its threshold (say again); on capitalised, punctuated lines ("North door is smoked.") it answers NONE at 0.89-0.99 on 24 of 24, where v3 answers SMOKE at 0.97-1.00 on 24 of 24. The contrast is sharper than the reviewer's lowercase-only probe shows.
- On my own 8 compound lines, v3 lets "smoked" override a real order that follows on 5 (v2 on 2). Example: "red stairs is smoked, flash it" is FLASH 0.85 in v2 and SMOKE 1.00 in v3. This is a small sample with my own lines and readings.
- The NONE reading is consistent with the spec ("not an order to the bot") and with how all three readers labelled the analogous blind lines r6v3_011 and sttv3_024.
- The phrase is natural: two different blind authors wrote "X is already smoked" unprompted.
- Nothing in HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md or cpp/coop_intent/README.md documents this. COOP-BOT.md only has the generic zero-shot note that callouts are a trap. It contradicts the HANDOFF section 7 default (informational callouts stay NONE) for this class.
- No reported number covers it: the only held-out NONE line the leave-one-author-out ensemble acts on is r6v3_003 (WAIT). No section 4 number changes.

**Corrections to the finding**
1. "None of the 24 NONE lines is a state callout of this kind" is too strong. r6v3_011 ("They hard breached west door, it's wide open now.") and sttv3_024 ("main is trapped...") are state callouts, held out as NONE at 0.66 and 0.99. None is about smoke or flash.
2. The second suggested fix is unsafe. Of the 10 authored corpus lines whose every matcher target has role=status, 8 are real orders (4 BREACH, 2 ENTRY, VAULT_WINDOW, HOLD_ANGLE). An example is "window's already open, just climb in". Declining on role=status would suppress them.
3. The twins are marginal: "is flashed" and "is blown open" sit at 0.63-0.85, and on no line do all three members act.
4. The model examined was trained on this Mac on MPS (bot_config recipe.device = "mps"). The working-machine CUDA model was not examined. The cause is in the data, so the same behaviour is expected there.

**Cause (inferred, not proven without re-training)**
- The only two training rows with "smoked" are r6v3_041 and csv3_007, both SMOKE; no NONE row has the word.
- These two rows are among v3's cross-validation wins: held out, each is SMOKE 0.99, where shipped v2 gave NONE 0.53 and HOLD_OTHER_ANGLE 0.68. The gain and the misfire are the same learned association.
- Corroboration: for "is breached", where training has a NONE row (r6v3_011), v3 acts on 0 of 8 and v2 on 3 of 8.

*Recommended action.* **1. Write-up (touches nothing frozen).** Add to the v3 section of COOP-BOT.md and to HANDOFF.md section 4 under "Финальная модель v3":

"Known regression of the re-trained model: a state callout with 'smoked' ('north door is smoked', 'i smoked blue stairs', 'it's already smoked') is read as SMOKE at about 1.00 (47 of 47 places; the shipped v2 bot answers NONE or asks again), also when a different order follows ('red stairs is smoked, flash it'). The only two training rows with 'smoked' are SMOKE orders (r6v3_041, csv3_007). The 24 blind NONE lines contain no smoke-state callout, so 'acts on non-order 4.2%' does not cover this. The probe is exploratory, not blind."

Also qualify HANDOFF section 7, first bullet, with this exception.

**2. Do not make v3 the default.** Leave `MODEL_DIR` in /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/coop_bot.py and shipped.py, and the default in cpp/coop_intent/CMakeLists.txt, on v2 until the owner accepts the limitation or it is fixed.

**3. If fixing (touches frozen seeds).**
- Do not edit seed_commands_v3.json in place. Add a new seed file and tag (for example seed_commands_v31.json under a new COOP_TAG entry in `coop_v2.SEED_FILE`).
- Its extra NONE seeds: "<place> is smoked", "<place> is already smoked", "i smoked <place>", "<place> is flashed", "<place> is blown open".
- Record it in frozen.txt as written after the v3 blind lines were seen.
- Re-run the leave-one-author-out cross-validation and confirm r6v3_041 and csv3_007 stay SMOKE. Mark those numbers "after tuning".
- Write new blind lines that include state-callout NONE lines before quoting a clean number.

**4. Drop the second suggested fix.** Declining to act in `coop_bot.decide` when the only place has role=status would suppress 8 real orders already in the corpus.

### gap-final-v3-model-behaviour #2: Final v3 bot pushes in on the callout '<place> clear': ENTRY on 27 of 30 names (v2: 19 of 30); inherited from the seeds and made worse by the v3 templates

Reviewer: major, training. Affects: HANDOFF.md section 7 (callouts stay NONE, the place is passed as a contact); the most common status callout of the genre; models/coop-deberta-v3-ens3-v3 and, to a smaller degree, the shipped v2 bot

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

The core claim holds on my own probe, with my own name lists, and through the real bot code.

The model examined is the final v3 ensemble now on disk at /Users/t.losiev/Documents/models_training/project_synth/models/coop-deberta-v3-ens3-v3 (trained on this Mac on MPS, written 00:28-00:33 today; family gate, threshold 0.60). The task text saying it does not exist yet is outdated.

**What the final v3 bot does on "<place> clear" (no "is")**
- It acts (ENTRY) on 17 of 20 dictionary names and 10 of 10 unseen room names of my choosing, 27 of 30 in total; 19 of those at confidence >= 0.9.
- By type: doors 5/5, windows 4/4 (0.97-0.98), floors/roof/upstairs 6/6, stairs 2/5.
- The three it does not act on are stairs: "white stairs clear" is NONE 0.87 (ignored); "yellow stairs clear" (NONE 0.57) and "brown stairs clear" (ENTRY 0.47) fall under the threshold and get "say again".
- Every confidence the reviewer quoted reproduced to two decimals.

**Shipped v2 bot on the same lines**
- It acts on 11 of 20 dictionary names (2 at >= 0.9) and 10 of 10 of my unseen names, so 21 of 30 against the reviewer's 19 of 30. The gap is only the choice of unseen names.
- Windows are 0/4 and stairs 0/5 in v2.

**Where v3 is worse than v2, and where it is not**
- The regression is confined to dictionary names: 11 to 17 of 20 acting, and 2 to 13 of 20 at >= 0.9.
- On unseen and generic names v2 is already as bad or worse: "room clear" is ENTRY 0.99 in both bots, as are "door clear", "area clear" and "building clear".
- With the article, on 24 non-dictionary names v2 acts on 24 and v3 on 21. On the 20 dictionary names it is 10 (v2) against 17 (v3).
- The reviewer's "42 vs 30 of 47" with the article is therefore name-set dependent; my equivalent is 38 vs 34 of 44.

**Phrasing**
- Safe in v3: "X is clear", "the X is clear", "X's clear", "X looks clear", "X is clear, nobody there", "X is all clear" — 0 of 30 each.
- Unsafe in v3: "X clear" 27/30, "clear on X" 29/30, "X clear, moving up" 18/30, "X cleared" 12/30, "X all clear" 6/30.
- Capitalised, it still acts on 18 of 20 dictionary names; with a trailing period, 11 of 20.

**Training data**
- Of 1016 training rows, 16 contain "clear": 13 are orders and 3 are NONE seeds of the form "<place> is clear". No row is a "<place> clear" callout.
- The reviewer's "5 blind lines are ENTRY" is a slip: 8 blind rows contain "clear", 7 with majority ENTRY and 1 FLASH, plus 5 ENTRY seeds.
- None of the 24 NONE-majority v3 blind lines is a status callout with "clear", so the 1.3% wrong-family figure does not cover this form at all.

**Bot path**
- coop_bot.Bot.respond returns action "act", intent ENTRY, with a reply drawn at random from "Pushing in!" / "Taking the room." / "Entry, entry!".
- The matcher already tags the place role=status and still reports it as primary.

**Not established**
- That the v3 templates are the cause. Only the v2-to-v3 difference is measured; the v3 data also adds 150 blind lines, two of them ENTRY lines with "clear".
- The NONE reading of "<place> clear" is the reviewers' own; no three-reader annotation exists for these probes.

**The suggested guard is not free**
- "No ENTRY when the only place has role=status" would block two real ENTRY orders that the leave-one-author-out ensemble gets right at 0.99: csv2_030 "door's open, push site and clear it" and csv3_039 "basement is all you, go in hard and check every corner".
- It does nothing for unseen names such as "kitchen clear" or "room clear" (no place matched), nor for "X cleared" and "clear on X" (role is null).

*Recommended action.* **1. Write-up (HANDOFF.md section 4 after the v3 table, section 7 first bullet, and the future "v3" section of COOP-BOT.md).** Add:

"Status callouts of the form '<place> clear' (without 'is') are not in the blind test (0 of the 24 NONE lines of v3; no such row among the 1016 training rows), so the 1.3% wrong-family figure does not cover them. On a developer probe the final v3 ensemble answers them ENTRY on 17 of 20 dictionary names (13 at >= 0.9; all four windows at 0.97-0.98) and on unseen room names; the shipped v2 bot does so on 11 of 20 dictionary names and on 'room clear' (0.99). Forms with a copula ('X is clear', 'X's clear') stay NONE. Probe, not a blind number."

State this before the default model is switched to v3 in cpp/coop_intent/CMakeLists.txt and scripts/coop/coop_bot.py.

**2. Fix (touches frozen material).**
- In /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/make_spec_v3.py, add to TEMPLATES["NONE"]: ("{} clear", ANY + ZONE), ("{} cleared", ANY + ZONE), ("{} clear, moving up", ZONE + DOOR), plus hand-written NONE seeds "room clear", "door clear", "area clear".
- Write these to a new seed file under a new COOP_TAG (for example seed_commands_v31.json) so the v3 study stays reproducible.
- Record the change in frozen.txt as made after the v3 blind lines and this probe were seen.
- Re-train, then measure on new blind lines that include status callouts. The existing 150 lines cannot measure it, and the probe lines are now seen.

**3. Do not adopt the guard as worded.**
- "No ENTRY when the only place has role=status" would block two correctly understood ENTRY orders already in the blind data (csv2_030, csv3_039).
- It misses unseen names ("kitchen clear", "room clear") and the forms "X cleared" / "clear on X".
- If a no-retraining guard is still wanted, narrow it to "the place is directly followed by 'clear' and nothing but filler follows", implement it identically in coop_bot.py decide() and cpp/coop_intent/src/bot_brain.cpp, and report its effect only on new blind lines.

**4. Correct the finding's own text.** "5 blind lines are ENTRY" should read "7 blind lines are ENTRY and 1 is FLASH". "Made worse by the v3 templates" should read "worse in the final v3 model on dictionary names (11 to 17 of 20); cause not isolated".

**Verifier (refute): confirmed, major; reproduced: yes; touches frozen: yes**

The behaviour is real and every count in the finding reproduces exactly from my own forward passes through coop_bot.Bot (classify + decide) on both ensembles. I could not refute it; three parts of the finding need correcting.

What holds:
- **Bare "<place> clear":** the v3 ensemble on this Mac (models/coop-deberta-v3-ens3-v3, trained on MPS, family gate 0.60) acts with ENTRY on 27 of 30 names (17/20 dictionary, 10/10 new), 18 of them at confidence >= 0.9. The shipped v2 bot acts on 19 of 30, 6 at >= 0.9.
- **With the article:** v3 acts on 42 of 47 (15 at >= 0.9), v2 on 30 of 47 (11 at >= 0.9).
- **Windows and stairs:** windows went from 0/4 (v2) to 4/4 (v3, 0.97-0.98). Stairs depend on the colour in v3: blue 0.65 and red 0.68 act, white is NONE 0.87, yellow and brown fall under the threshold.
- **Which forms are safe:** only forms with a copula or an explicit "nobody" stay NONE in both bots ("X is clear", "X's clear", "X looks clear", "X is clear now", "X clear, nobody here", "checked X, it's clear": 0/8 each). My own natural callout forms are worse in v3 than in v2: "okay X clear" 8/8 (v2 3/8), "X clear, you can come up" 8/8 (v2 5/8), "X clear guys" 6/8 (v2 1/8).
- **Bot path:** neither coop_bot.py decide() nor BotBrain::Decide looks at the place role, so the result is action "act" while the matcher marks the place role=status.
- **Not covered by any reported number:** 0 of the 99 NONE-majority blind lines (633 lines) contain "clear", and no blind NONE line draws an ENTRY pick in the cross-validation. The 4.2% "acts on non-order" in eval_v3.log cannot see this class.
- **Not documented, and status is the project's own reading:** "clear" appears nowhere in HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md or the C++ README. locations.json lists "clear" under status_next, locations_dev.json has "white stairs clear" as an ordinary callout case, and HANDOFF section 7 says callouts stay NONE.

Corrections:
1. **Not specific to v3 or to place names.** The shipped v2 bot already answers ENTRY at 0.89-0.99 on "clear", "room clear", "door clear", "stairs clear", "window clear", "site clear" and "hallway clear". v3 widens the defect to dictionary names (windows, some stairs) and raises confidence.
2. **"Made worse by the v3 templates" is not isolated.** The v3 training set also adds 150 blind lines and 12 ENTRY seeds. Red and brown stairs, which have a NONE seed "<stairs> is clear", still moved towards ENTRY. No ablation exists, so only "worse in the v3 ensemble" is supported.
3. **The suggested no-retrain guard is wrong as stated.** The matcher's role=status means "place followed by is / 's / are / clear", not "the line is a callout". Of the 10 blind lines whose only place has role=status, 8 are orders. On the leave-one-author-out predictions the guard turns two correct ENTRY orders into NONE (csv2_030 "door's open, push site and clear it", csv3_039 "basement is all you, go in hard and check every corner"): v3 lines 136 to 135 of 150, older lines 440 to 439 of 483. It catches no blind NONE line, and it cannot see "kitchen clear", "room clear" or "clear" because they name no dictionary place.

Minor: 7 blind lines with "clear" have ENTRY majority (plus one FLASH), not 5. The probe is templated, not blind, and read by one reader. No number in HANDOFF section 4 is invalidated.

*Recommended action.* 1. **Write-up, no frozen material touched.** In HANDOFF.md section 4, next to the known «get up on the roof» → RAPPEL error, and in the future "v3" section of COOP-BOT.md, add: "Status callouts without a copula ('<place> clear', 'room clear', 'clear') are executed as ENTRY: the shipped v2 bot on 19 of 30 place names, the final v3 ensemble on 27 of 30 (18 at confidence >= 0.9); only 'X is clear / X's clear / X looks clear' stay NONE. The blind test has no such line (0 of 99 NONE lines contain 'clear'), so 'acts on non-order 4.2%' does not cover it. Exploratory templated probe, one reader." Qualify HANDOFF section 7 ("callouts stay NONE") with the same exception.

2. **Fix, touches frozen material.** In scripts/coop/make_spec_v3.py, TEMPLATES["NONE"], add copula-less status templates ("{} clear", "{} cleared", "{} clear, moving up" over ANY + ZONE) and a few bare NONE seeds ("room clear", "door clear", "clear left"). Regenerate seed_commands_v3.json, record the change in frozen.txt as made after the blind lines were seen, and re-run the cross-validation and the final training. Report the new numbers as after a seed change, and put copula-less status callouts into the next blind set; spec_v3's NONE text ("callout about enemies") steered authors away from them.

3. **Do not adopt the guard** "skip ENTRY when the only place has role=status" in coop_bot.py or bot_brain.cpp. On the existing blind lines it suppresses two correct ENTRY orders (csv2_030, csv3_039), catches no NONE line, and misses "kitchen clear", "room clear" and "clear". A narrower guard would be a new rule fitted after the blind lines were seen and needs fresh blind lines to be scored.

4. **Wording.** Drop "made worse by the v3 templates" from the title; say "worse in the v3 ensemble (cause not isolated)".

### gap-final-v3-model-behaviour #3: Final v3 model: 'get up on the roof' is now MOVE_TO only because that blind line is a training row; 'get on / onto the roof' and a bare 'roof' still answer RAPPEL (5 of 27 fresh rope-less roof orders, 18 of 42 on a verb x preposition grid)

Reviewer: major, training. Affects: HANDOFF.md:111 (the known v2 error that re-training should fix) and HANDOFF.md section 7, second decision ('go to the roof' without a rope word is MOVE_TO); spec_v3 RAPPEL / MOVE_TO definitions; models/coop-deberta-v3-ens3-v3

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

Every number in the finding reproduces exactly with my own inference code (single-line, unpadded, the coop_bot.Bot.classify path) on models/coop-deberta-v3-ens3-v3 (trained on this Mac, recipe.device=mps, family gate, threshold 0.60).

The final v3 bot still acts RAPPEL at 0.92-1.00 on rope-less "get on / onto the roof", "<verb> roof" and bare "roof" orders. It answers MOVE_TO on "to the roof" / "up to the roof" wordings. spec_v3 and HANDOFF section 7 say all of these are MOVE_TO. RAPPEL (assault) vs MOVE_TO (move) is a wrong-family action that no threshold catches.

The "known v2 error" at HANDOFF.md:111 is fixed only in-sample:
- 'get up on the roof' is MOVE_TO 0.91 in the final model, but csv3_037 is one of its 633 training rows.
- The project's own leave-one-author-out result, which the reviewer did not cite, shows the re-trained ensemble still answering RAPPEL on csv3_037 when cs is held out: family mass 0.72, all three members RAPPEL (eval_v3.log:91). The held-out evidence already contradicted line 111 when the snapshot was written.

Likely cause, consistent with the data but not proven (proof needs re-training):
- make_spec_v3.py:113-119 copies seed_commands_v21.json verbatim and only appends templates.
- The RAPPEL seeds 'get on the roof' and 'go roof' were written under spec v1/v2, where "go up to the roof" was a RAPPEL example. They stayed RAPPEL although make_spec_v3.py:8-10 redefines roof-going as MOVE_TO.
- The RAPPEL / MOVE_TO split follows the seed wording: 'to' and 'up to' forms 0/14 RAPPEL, 'on' and bare forms 12/14.

Corrections to the reviewer's framing:
1. "The only bare place name of 47 on which v3 acts" is true only with the article as listed. With "the" dropped, v3 acts on 9 of 47: roof RAPPEL 0.98, attic RAPPEL 0.68, basement ENTRY 0.62, six window names VAULT_WINDOW 0.61-0.65. The roof is the only high-confidence one.
2. The swap count 43/139 vs 33/1116 holds only under the coop_v2.pick convention (under threshold = NONE). The 43 come from 8 of 35 source lines, 35 of them from four lines. Only 1 of 22 floor-to-roof swaps becomes RAPPEL, and that one is the seed 'go roof'. By source lines it is 8/35 vs 11/133.
3. The grid's 18/42 includes 4 'climb' lines, where a human could accept RAPPEL, and 2 seed rows. It is 14/36 without 'climb' and 16/37 without the 5 seeds.
4. The cosine between 'go to the roof' and 'go roof' is 0.89 with the project's vectorizer, not 0.88. Immaterial.

The effect is not an artefact of the reviewer's lines: my own lines and my own verb grid show the same pattern, and the 'top floor' and 'basement' controls do not.

*Recommended action.* 1. Write-up only (no frozen material touched)

Replace the second sentence of /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md:111 ("Её должно починить дообучение") with the measured state, and carry the same text into the future "v3" section of COOP-BOT.md:

"Re-training did not fix this line when held out: in leave-one-author-out the re-trained ensemble still answers RAPPEL on csv3_037 (family mass 0.72, eval_v3.log:91). The final model answers MOVE_TO 0.91 on 'get up on the roof' only with csv3_037 in its training set. Rope-less 'get on / onto the roof', '<verb> roof' and a bare 'roof' are still RAPPEL at 0.92-1.00: 5 of 27 fresh roof orders, 18 of 42 on a verb x preposition grid against 2 of 42 with 'top floor'. 'to the roof' and 'up to the roof' are MOVE_TO."

Qualify HANDOFF.md:192 (section 7) the same way: the decision holds in the model only for 'to the roof' wordings.

2. Fix (touches frozen material; do not apply silently)

- In /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/seed_commands_v3.json, move "get on the roof" (line 132) and "go roof" (line 136) from RAPPEL to MOVE_TO, or drop them. Preferably do it as an explicit relabel step in make_spec_v3.py where the v21 seeds are copied (lines 113-119), so the seed set agrees with spec_v3.json:11.
- Record the edit in frozen.txt as made after the v3 blind lines were seen.
- Re-run COOP_TAG=v3 train_v2.py cv and final. Mark the re-computed v3 numbers "after tuning".
- Measure the roof behaviour on newly written blind roof lines, with and without a rope word. csv3_031, csv3_037 and sttv3_041 no longer count as held-out for this question.

**Verifier (refute): confirmed, major; reproduced: yes; touches frozen: yes**

The finding stands; I could not refute it, and my own lines make it somewhat worse.

1. Numbers reproduce exactly. On the reviewer's 30 rope-less roof orders the final v3 ensemble acts RAPPEL on 7 (v2: 23), MOVE_TO on 21, under threshold on 2. Without the three seed rows it is 5 of 27 RAPPEL: 'roof, go' 0.99, 'take the roof' 0.92, 'get on the rooftop' 0.99, 'bot, get on the roof' 1.00, 'get onto the roof' 1.00, all three members agreeing. The grid gives 18 of 42 RAPPEL (per form 0 / 6 / 5 / 1 / 0 / 6) against 2 of 42 with 'top floor'. Bare 'roof' is RAPPEL 0.98 and 'the roof' 0.87.

2. It is not a held-out fix. The project's own log already shows this: eval_v3.log:91 lists csv3_037 'get up on the roof, I want somebody up top' as MOVE_TO -> RAPPEL for the leave-one-author-out re-trained ens3 (stored probabilities: RAPPEL 0.70, 3 of 3 members). The final model trains on that line and answers MOVE_TO 1.00 (0.91 on the short form). HANDOFF.md:111 ("re-training should fix it") is therefore contradicted by section C of the same evaluation.

3. The cause is a label conflict in frozen training material. seed_commands_v3.json inherits the v2.1 RAPPEL seeds 'get on the roof' and 'go roof', written when RAPPEL meant "use the rope, go up to the roof or drop down outside" (intents_v2.json). They were not relabelled when spec_v3 made rope-less roof orders MOVE_TO, while make_spec_v3.py added 'go to / head to / go up to the roof' as MOVE_TO. With the seed held out, 8 of 9 CV models call 'get on the roof' MOVE_TO and 6 of 9 call 'go roof' MOVE_TO; the final model answers RAPPEL 1.00 on both. Nothing in HANDOFF, COOP-BOT.md, DEBERTA-BOT.md, the C++ README or frozen.txt says these two seeds were kept on purpose.

4. My own 20 rope-less 'on / onto the roof' orders, written and hashed before I ran any model: final v3 acts RAPPEL on 10, MOVE_TO on 2, TAKE_COVER on 1, under threshold on 7 (v2: RAPPEL 19). The same wording with 'top floor' gives RAPPEL 0, MOVE_TO 9. RAPPEL is in the assault family and MOVE_TO in move, so each is a wrong-family action, the class the project weighs double.

What limits it:
- No reported number is wrong. csv3_037 is one of the two wrong-family lines behind the reported 1.3%, so the CV figures (90.0 / 90.7) already count it.
- v3 is better than the shipped v2 on every roof slice (7 vs 23 of 30; 10 vs 19 of 20). 'to / up to / up on the roof' are now MOVE_TO.
- Bare 'roof' -> RAPPEL is inherited from v2 (0.79; 'the roof' 0.96), not a v3 regression.
- 18 of 42 overstates the natural case: it includes 7 non-English bare-noun rows ('get roof', 'climb roof') and 7 'climb' rows, where the top-floor control also goes RAPPEL twice. Without them it is 9 of 30, all in 'on / onto the roof' (9 of 12).
- The problem is confined to the one zone 'roof'. Lines that put the bot on the roof were 3 of the 150 blind lines; 1 of those 3 went RAPPEL held-out.

*Recommended action.* 1. Write-up only (touches nothing frozen). Replace HANDOFF.md:111 and carry the same text into the future v3 section of COOP-BOT.md: "Known error: 'get up on the roof' -> RAPPEL. Re-training does not fix it held-out: with author cs left out, csv3_037 is still RAPPEL (eval_v3.log section C; it is one of the two wrong-family lines in the 1.3%). The final model answers MOVE_TO only because that line is in its training set. 'to / up to / up on the roof' are MOVE_TO; 'get on / onto the roof' and a bare 'roof' still answer RAPPEL (5 of 27 fresh rope-less roof orders; 9 of 12 on/onto lines of the grid), because the seeds 'get on the roof' and 'go roof' were inherited from v2.1 with the label RAPPEL." In HANDOFF section 7, second bullet, add that the decision currently holds only for 'to the roof' wordings.

2. Owner decision, touches frozen. If the section 7 decision stays: in scripts/coop/seed_commands_v3.json (through make_spec_v3.py) move 'get on the roof' and 'go roof' from RAPPEL to MOVE_TO, or drop them. Record the edit in frozen.txt as made after the blind v3 lines were seen, re-run the v3 CV and the final ens3, and report the roof result only on newly written blind roof lines; until then any roof number is "after tuning". If the owner instead wants 'get on the roof' to mean roping up, change spec_v3 and section 7 and relabel csv3_037; that also needs new blind lines.

### gap-final-v3-model-behaviour #4: A lone place name changes the intent: 'take blue stairs' is MOVE_TO 1.00, 'take blue' is ENTRY (12 of 12 colours); PER_TEMPLATE = 3 drew no lone name for 'take', and 'every name meets every kind of order' is 31% of the combinations

Reviewer: minor, data. Affects: scripts/coop/make_spec_v3.py:58 (comment) and the same sentence in seed_commands_v3.json / the planned v3 write-up; the intent on lone-name orders such as 'take blue', 'take main'

**Verifier (both): partly, minor; reproduced: yes; touches frozen: yes**

The facts reproduce; the scope and the cause are overstated.

TRUE
1. Coverage claim is overstated. make_spec_v3.py:58 ("template x place, so every name meets every kind of order") and its docstring lines 14-16 ("sees every place name in every kind of order") describe a full cross. The code draws PER_TEMPLATE = 3 places per template: 51 templates, 486 template x place combinations, 150 drawn (30.9%); 109 of 279 distinct intent x place pairs (39%). Five intents have no place template (HOLD_POSITION, HOLD_OTHER_ANGLE, DEFUSE, REVIVE_ME, GO_NOW). In the final training data (633 lines + 383 seeds) seeds cover 94 of 504 place x intent cells (19%), lines + seeds 154 (31%). Per name: 'blue stairs' and 'yellow stairs' meet 1 intent of 11 offered, lone 'main' 1 of 7.
2. 'take {}' (MOVE_TO template, offers 5 lone colours + 5 '<colour> stairs') drew yellow/white/brown stairs and no lone name. Lone names drawn: ENTRY 5, FRAG 3, NONE 3, WAIT 2, HOLD_ANGLE 1, SMOKE 1, MOVE_TO 0.
3. Final v3 model (models/coop-deberta-v3-ens3-v3, family gate, threshold 0.60): 'take <colour> stairs' is MOVE_TO 1.00 for 11 of 11 colours I tried (5 dictionary + 6 not), while 'take main/blue/red/yellow/white/brown' is ENTRY 0.98/0.89/0.77/0.68/0.88/0.86 and green/black/orange/purple/pink/grey are ENTRY 0.64-0.97. The bot acts: 'take blue' -> act, ENTRY 0.89, primary place stairs/blue; the reply is one of three random ENTRY lines ('Taking the room.' is one of them).
4. This is a v2 -> v3 change from asking to acting: shipped v2 answers 'say again' on take blue/red/brown (0.53/0.55/0.44 < 0.58) and acts ENTRY on main/yellow/white; over the 12 names v2 acts ENTRY on 4, v3 on 12.

NOT TRUE / OVERSTATED
a. "The same sentence in seed_commands_v3.json": it is not there. Its _note_v3 only says "+ templated seed commands with map places". The sentence exists only in make_spec_v3.py (lines 14-16 and 58). HANDOFF.md, COOP-BOT.md, DEBERTA-BOT.md and both READMEs do not repeat it.
b. "12 of 12 in another family than the template's label": the template offers LONE[1:] only, so it labels 5 of those 12 names. 'main' is deliberately excluded from 'take {}', and the six other colours are in no template. Correct statement: 5 of 5 template-offered lone forms.
c. The title ("a lone place name changes the intent") and the cause (PER_TEMPLATE drew no lone name) are not supported. Lone names are right in every other templated frame: hold/watch/smoke/flash/nade/push/rush/one on/contact/don't push..yet = 120 of 120 at 0.99-1.00, including 'watch {}' and 'flash {}', which also drew zero lone names. 'go to / move to / get to / head to <lone>' is MOVE_TO 24 of 24. The shipped v2, trained with no place seeds, already has ENTRY as top intent on 9 of the 12 'take <lone>' lines. The driver is the verb: the training data has 'take the room' (ENTRY seed), 'take site, check every corner' and two '...take the room' blind lines (ENTRY 3/3), and the only 'take' -> MOVE_TO rows all contain the word 'stairs'. Whether one lone 'take' seed would flip it was not tested (no training allowed).
d. The expected MOVE_TO is the developer's template label, not a blind truth. None of the 150 v3 blind lines has the form 'take <lone name>'; spec_v3 uses 'take blue' only as a target example (stairs / blue) and does not give its intent. ENTRY ("pushes into the room / site and clears it") is a defensible reading of 'take X'. With more words the model is right: 'take blue to the top floor', 'take blue and go upstairs', 'take blue down to the basement' are MOVE_TO 0.99-1.00.

No number in HANDOFF section 4 depends on this. The target is still correct, so the planner is sent to the right stairs, with an assault intent instead of a move intent.

*Recommended action.* 1. Write-up (the planned "v3" section of COOP-BOT.md and DEBERTA-BOT.md): do not carry over "every name meets every kind of order". Use: "Place seeds: 51 templates over 19 of the 24 intents, 3 places sampled per template (random.Random(3)) = 150 of 486 template x place combinations (109 of 279 distinct intent x place pairs); HOLD_POSITION, HOLD_OTHER_ANGLE, DEFUSE, REVIVE_ME and GO_NOW have no place template."

2. Leave scripts/coop/make_spec_v3.py as it is (hashed in frozen.txt at 2026-10-03T20:55:13). If the comment at line 58 and the docstring at lines 14-16 are corrected anyway, append the new hash to frozen.txt with a note that it is a comment-only edit and that location_seeds() still reproduces seed_commands_v3.json.

3. Add to the known-errors list (HANDOFF.md section 4, next to "get up on the roof", and the v3 write-up): "'take <colour>' without the word 'stairs' ('take blue') is read as ENTRY by the final v3 model (0.68-0.89; the shipped v2 said 'say again' on blue/red/brown); the target is still stairs / <colour>. No blind line has this form, so the 90.0 / 90.7 figures do not measure it."

4. Owner decision for HANDOFF.md section 7: is 'take blue' MOVE_TO (as the 'take {}' template labels it) or is ENTRY acceptable. Only if MOVE_TO: in the next seed revision make location_seeds() emit at least one lone and one full form for templates that offer both. That changes seed_commands_v3.json after the blind lines were seen, so it needs a frozen.txt entry, a re-train, and new blind lines before any number is quoted as held-out. Not to be done as a patch to the current v3.

### gap-final-v3-model-behaviour #5: The out-of-fold predictions behind threshold 0.60 and the family gate are not saved: the two numbers in bot_config.json can be checked against the log, not re-derived

Reviewer: minor, training. Affects: bot_config.json threshold 0.60 / gate family / oof_fits 560 and 569 of the final v3 bot; the project rule that threshold and gate come from out-of-fold predictions (HANDOFF.md section 6)

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The finding holds: the final v3 bot's threshold 0.60, gate "family" and criteria 569 / 560 exist only as one log line and the `oof_fits` field of `bot_config.json`. The out-of-fold probabilities behind them were never written, so they cannot be recomputed without repeating the 15 fold trainings (2671 s on MPS per the log). I found no sign that either number is wrong.

- **Code:** `train_v2.final()` averages the three members' out-of-fold predictions in memory, fits both gates and stores only the two (threshold, criterion) pairs. `cv()` does store its `oof`. No file under the project or the model dir holds the final out-of-fold probabilities.
- **Not a v3 regression:** the pristine `train_v2.py` behaves the same, so the shipped v2 bot's 0.58 / 432 vs 429 (quoted in COOP-BOT.md:458) has the same status. No document states this limitation.
- **Reviewer's sub-claims (a), (b), (c), (e):** all reproduce.
- **Sub-claim (d), one correction:** the thresholds and criteria reproduce, but "within 0-1 point of its optimum at 0.60" is true only for the family gate (0, 0, 0 points). For the top gate with r6 held out, 0.60 is 3 points below the optimum (350 vs 353).
- **Practical weight is low:** on the stored CUDA held-out predictions, one fixed family threshold anywhere in 0.50-0.64 gives a criterion of 546-553 of 633. Family vs top at 0.60 is 550 vs 549.
- **The gate margin cannot be examined:** the final run's 9-point margin (569 vs 560) is larger than the CUDA fold margins (-7, +6, +2), and that is the one thing a reader might want to check.
- **Hash log:** neither the v3 `bot_config.json` nor `train_v3_final_ens3.log` is recorded in `frozen.txt`, whose last entry (23:40:26) predates the training. The v2 config was hashed (`frozen.txt:107`).
- **MPS repeatability:** `frozen.txt:166` records MPS-vs-CPU inference parity and one MPS fold inside the CUDA seed spread, but no repeat-run check. I did not test this (training is forbidden for reviewers).

*Recommended action.* Do not retrain the current model just for this.

1. **Code:** in `/Users/t.losiev/Documents/models_training/project_synth/scripts/coop/train_v2.py`, `final()`, right after the fit at line 175 and before the members are trained, dump the per-member out-of-fold probabilities, e.g. `json.dump({"_meta": {"labels": LABELS, "n_items": len(items), "n_seeds": len(seeds), "device": device}, "oof": {str(s): o for s, o in zip(members, oofs)}}, io.open(os.path.join(HERE, f"results_{V.TAG}_final_oof.json"), "w", encoding="utf-8"))`. Record the edit in `frozen.txt` as "recipe unchanged". It takes effect the next time a final model is trained.

2. **Write-up** (v3 section of COOP-BOT.md / DEBERTA-BOT.md, and HANDOFF section 4 when the final model is described), a sentence such as: "Threshold 0.60 and the family gate of the final v3 model come from 5-fold out-of-fold predictions over the 633 lines, trained on MPS (criterion family 569, top 560; train_v3_final_ens3.log, 00:25:07). The out-of-fold probabilities were not stored, so these are log values and cannot be recomputed without repeating the 15 fold trainings. The same is true of the v2 bot's 0.58 / 432 vs 429. On the stored CUDA leave-one-author-out folds the family optimum is 0.52-0.60, and the held-out score is flat (546-553 of 633) for thresholds 0.50-0.64."

3. **Hash log:** append the sha256 of `models/coop-deberta-v3-ens3-v3/bot_config.json` and `scripts/coop/train_v3_final_ens3.log` to `scripts/coop/frozen.txt`, as was done for the v2 config at `frozen.txt:107`, so the log value is at least pinned.

### gap-final-v3-model-behaviour: checked and found right

- bot_config.json of the final v3 bot matches its log: threshold 0.60 for both gates, criteria 560 (top) / 569 (family), gate family, device mps; train_v3_final_ens3.log 00:25:07, exit code 0, 18 trainings in 3198 s
- trained_on text is right: COOP_TAG=v3 load_items() gives 633 lines (363 v1 + 120 v2 + 150 v3, unique ids, majority on all 633) and seed_items() 383; labels / families / phrases / members / base model identical to the v2 config and to coop_v2
- Threshold 0.60 is inside what CUDA produced: stored two-author out-of-fold predictions give family thresholds 0.60 / 0.58 / 0.52, and 0.60 is within 0-1 criterion points of each optimum (audit_cfg.py)
- Members are three distinct weight files (3 sha256), no NaN, rows sum to 1 within 3e-7; v2 and v3 tokenizer.json differ only in the saved 'padding' setting and give identical ids on 8082 of 8082 lines
- The padded-batch forward pass I used equals coop_bot.classify (one line, no padding): max |dp| 1.3e-6, 0 argmax flips on 189 lines, both ensembles
- Fit on own training data, family / 0.60: each of the three v3 members and the ensemble get 633/633 lines in the accepted set and 383/383 seeds, 0 under threshold; lowest ensemble confidence 0.981. So there is no training line the ensemble cannot fit, and no identical text with two labels; v2 likewise 483/483 + 233/233
- No v3 member is an outlier against the CUDA-trained v2 members on 516 unseen lines (locations_dev + adv_lines minus training rows): pairwise pick agreement v3 79.7 / 76.9 / 83.3% vs v2 74.2 / 70.7 / 69.6%; under threshold v3 7.9 / 8.5 / 5.2% vs v2 9.5 / 10.5 / 7.6%; sure NONE v3 14.9 / 25.2 / 23.4% vs v2 23.4 / 22.7 / 16.7%; mean confidence v3 0.913 / 0.918 / 0.936 vs v2 0.891 / 0.883 / 0.900; ensembles under threshold 17.2% vs 16.5%
- The higher confidence of the v3 members is not a device effect: on the same training set (without stt) and the same 227 lines, CUDA members have mean confidence 0.946 / 0.942 / 0.938 and MPS members 0.937 / 0.951 / 0.933; under 0.60: 5.3 / 4.8 / 6.2% vs 4.8 / 3.1 / 7.5%
- Owner's lines: coop_v2.PROBES accepted 16/16 by both bots; on the 33 unique lines of coop_bot_log.jsonl the two bots differ on 2 ('kill them all' FRAG -> ENTRY, 'seek and destroy' FRAG -> say again)
- Roof lines with a rope word: RAPPEL 10/10 in v2 and v3; roof lines of other intents (hold, watch, drone, fall back, follow, smoke, callouts): v3 right 10/10 with 0 RAPPEL, v2 9/10
- Place invariance holds for full names in the final v3 bot: 72 frames written before any run, 2480 substitutions; in 67 frames none of 2301 substitutions (1132 dictionary names, 1169 new names) leaves the accepted intent or falls under the threshold; pick differs from the frame's usual pick in 26/1220 (2.1%) known and 24/1260 (1.9%) new, against 8.0% / 8.5% for v2
- New names are not worse than dictionary names (the 'one line in locations.json, no re-training' claim, classifier side): not accepted 69/1260 (5.5%) new vs 71/1220 (5.8%) known; under threshold 45/1260 vs 52/1220; mean confidence 0.9896 vs 0.9893
- Seen vs unseen (intent, place) pairs make no difference in v3: not accepted 39/629 (6.2%) for pairs present in training vs 32/591 (5.4%) for pairs absent
- All 140 v3 failures on the frames sit in 5 frames and are about the frame, not the place: 'i need you at {}' 47/47 under threshold (both bots), 'retreat to {}' 47/47 (MOVE_TO or under threshold; the only 36 wrong-family acts, v2 has 128), 'position yourself at {}' 21/37 (MOVE_TO 0.44-0.65 around the threshold), 'cover {} for me' 16/28 (COVER_ME instead of HOLD_ANGLE, same family, split by place type), 'clear {}' 9/20 ('clear red stairs' NONE 0.63 but 'clear the red stairs' ENTRY 1.00)
- Place word swapped inside 146 unseen one-place lines (1255 variants): v3 pick changes on 35/551 (6.4%) known and 41/704 (5.8%) new, v2 on 10.3% / 14.1%; without the roof v3 33/1116 (3.0%), mostly threshold crossings between 0.5 and 0.7, v2 93/1116 (8.3%)
- Swapping the place inside 65 blind v3 lines (now training rows; 536 variants) never changes the v3 pick (0/536), so the model did not tie those lines to their place word
- Pre-registered callout and negation frames (two at, is clear, there's a guy near, he's behind, they're pushing from, i'm at, don't go to, don't smoke, don't push yet, don't open yet, hold off on): v3 acts wrongly on 0 of 415, v2 on 2
- Status frames that do NOT misfire in v3 (0 of 47 or 0 of 8 each): '{} is open', '{} is already open', "i'm holding {}", 'they breached {}', 'enemy drone at {}', '{} is breached', '{} is covered', "they're holding {}", "i'm pushing {}", "i'm droning {}"
- Nothing under /Users/t.losiev/Documents/models_training/ was created or modified by this review (find -newermt over the project tree returns nothing); all runs used a scratch copy of scripts/coop with PYTHONDONTWRITEBYTECODE=1

## Gap round: export and C++ parity of the final v3 model (`gap-final-v3-export-parity`)

### gap-final-v3-export-parity #1: Letter case decides the action: upper-case FLANK / RAPPEL / DRONE make both bots throw a grenade, and on alternating-case lines the v3 bot now throws a frag where v2 asked again (golden edge line 'mIxEd CaSe FlAnK')

Reviewer: major, bot-logic. Affects: Behaviour of the shipped v2 bot and of the final v3 bot on any transcript that is not lower case (typed chat, STT engines that emit capitals); the golden answer of edge line 'mIxEd CaSe FlAnK'; cpp/coop_intent/README.md 'Known model behaviour'

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

Every number in the finding reproduces, by a different route (PyTorch ensembles called as coop_bot.Bot.classify does, not the reviewer's ONNX runs). No number in HANDOFF section 4 is affected; this is a robustness and documentation gap, mostly inherited from v2.

**Cause.** The tokenizer is cased (tokenizer_config.json `do_lower_case: false`; the normalizer is Replace + NFC + Strip, no Lowercase). Neither coop_bot.py (`text = input().strip()`, then `self.tok([text], ...)`) nor the C++ engine lower-cases the classifier input; only the place matcher and the three regexes fold case. `▁FLANK`, `▁RAPPEL` and `▁DRONE` are not vocabulary pieces (they split into `▁FLA NK`, `▁RAP PEL`, `▁DR ONE`), while `▁BREACH` is, which is why 'UPPERCASE BREACH NOW' still works.

**(1) Upper case, both bots (inherited).** Family gate at 0.58 (v2) / 0.60 (v3):

| line | v2 | v3 |
|---|---|---|
| FLANK | FRAG, utility mass 0.987, acts | FLASH, 0.990, acts |
| FLANK LEFT | FLASH, 0.662, acts (top label FLANK 0.31) | FLASH, 0.987, acts (FLASH/SMOKE/FRAG 0.33 each) |
| RAPPEL | FRAG 0.973, acts | FRAG 0.988, acts |
| DRONE IT | FRAG 0.735, acts | FRAG 0.654, acts |

On upper-cased copies of the 233 seed_commands_v21.json lines (both bots 233/233 right as written):

| | right | same family | nothing | wrong-family action |
|---|---|---|---|---|
| v2 | 220 | 2 | 3 | 8 |
| v3 | 218 | 0 | 5 | 10 |

v3 is worse than v2 on 8 lines and better on 3. The damage is concentrated in short commands built on FLANK, RAPPEL, DRONE (and REVIVE in v3). On upper-cased full training lines it is small: the 483 older lines give 3 (v2) and 2 (v3) wrong-family actions, and the 150 v3 lines give 149/150 near and 0 wrong family for v3. These are training lines, so this is not a held-out measurement.

**(2) Alternating case, new in v3.** 'mIxEd CaSe FlAnK' goes from say-again (v2, FRAG mass 0.430) to an executed FRAG (v3, utility mass 0.881). On the reviewer's 7 lines v2 acts on 1 and v3 on 6, always FRAG, with the confidences quoted. It is systematic: on alternating-case copies of all 233 seeds, v3 takes a wrong-family action on 124 (lower-first) and 132 (upper-first) against 62 and 95 for v2, and v3's wrong action is FRAG in 124/124 and 129/132.

Two qualifications on (2):
- Alternating case is not a realistic transcript.
- It is not a general regression of v3 on unseen tokens. On 60 lines of my own (typos, keyboard mash, non-English, operator names) the bots are level: utility actions 18 (v2) vs 17 (v3).

**(3) Sentence case is largely fine, with one correction.** 'Capitalised.' copies: v2 226 right / 0 wrong family, v3 228 right / 1 wrong family ('Rappel.' → FRAG 0.829). Without the full stop, 'Rappel' is a FRAG action in both bots (v2 0.732, v3 0.958), so "not affected" slightly overstates it; v2 escapes only because the full stop tips it to NONE.

**Other details that hold.**
- 'naïve flank': v2 FLANK 0.868 acts, v3 NONE 0.579 say-again. 'naive flank': v2 FLANK 0.692 acts, v3 NONE 0.644 ignores.
- Golden edge lines: 3 of 30 differ as picks (the reviewer's definition). Counting say-again vs ignore and the label under the threshold, 7 differ; the extra 4 never act.
- Lower-casing the 165 (v3) / 100 (v2) training lines that contain a capital keeps an accepted pick on all of them.
- No document mentions case. The training text has no fully upper-case line, and the stt author is all lower case with no punctuation, so the input contract is implicitly lower case but is written nowhere.

**Wider context from my own probe.** Case is one face of a behaviour both bots share: a short line of pieces the model has not seen as an order word goes to FRAG at high confidence. Examples (v2 / v3): 'flnak' 0.92 / 0.93, 'rapel' 0.97 / 0.98, 'braech' 0.99 / 0.99, 'dorne it' 0.99 / 0.99, 'blorp' 0.99 / 0.99, 'Thermite' 0.98 / 0.98, 'Sledge' 0.98 / 0.97. Lower-casing fixes only the case part of this.

**Severity.** Major as product behaviour: a wrong-family action at 0.97–0.99 on three bare canonical commands, which the threshold cannot stop, with the STT engine still unchosen and both existing interfaces accepting typed text in any case. It is not a v3 blocker and not a v3 regression in its main part. Part (2) on its own would be minor.

*Recommended action.* **1. Write-up now (touches nothing frozen).** In /Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/README.md, section 'Known model behaviour (not the port)', add next to the non-English lines:

"The classifier is cased and the engine does not change the case of the line. It was trained on lower-case text (no training line is fully upper-case). Upper-case orders can become a wrong-family action that the threshold does not catch: FLANK → FRAG/FLASH 0.99, RAPPEL → FRAG 0.97–0.99, DRONE IT → FRAG 0.65–0.73 (v2 and v3); 'Rappel' with a capital → FRAG (v2 0.73, v3 0.96). On upper-cased copies of the 233 canonical commands, 8 (v2) / 10 (v3) are wrong-family actions. More generally, a short line of unseen pieces (typos such as 'flnak', 'rapel'; names such as 'Thermite') goes to FRAG at 0.9+. The caller must pass lower-case transcripts until the engine normalizes case itself."

Put the same sentence about the input contract (lower-case transcripts, as the stt author writes them) in the 'v3' section of COOP-BOT.md and in HANDOFF.md section 4 or 7 when they are written, and in the stage-2 UE plan next to "regexes via ICU over the ASCII shadow".

**2. Code, as a separate measured step.** Lower-case the text before the tokenizer in scripts/coop/coop_bot.py Bot.classify and in the C++ caller (BotBrain / coop_cli), and in train_v2.py so training and inference see the same input. Then:
- re-run the leave-one-author-out cross-validation and the threshold fit;
- regenerate golden.jsonl and the test files;
- record the change in frozen.txt.

Do not carry the section-4 classifier numbers (83.3; 90.0 / 90.7; 1.3%) over to the lower-cased pipeline. 65 of the 150 v3 blind lines contain capitals (all 50 of author r6), so those numbers must be re-measured. Report both rather than choosing the variant by its blind score. The "costs nothing" check (165/165 and 100/100) is on training lines only.

**3. When the v3 export is generated,** expect 'mIxEd CaSe FlAnK' in golden.jsonl to be an executed FRAG (utility mass 0.88) under the v3 config. That is a model behaviour, not a port error.

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

Every number in the finding reproduces, and no document mentions letter case. The finding still needs four corrections, and it changes none of the HANDOFF section 4 claims.

**What holds**
- The classifier is cased and nothing normalises case before it. `coop_bot.py:126` passes the raw line to the tokenizer, `tokenizer_config.json` has `do_lower_case: false`, and the C++ model path has no case folding.
- Upper-case bare commands become confident wrong-family actions in both bots: 8 of 233 seed commands for v2 and 10 of 233 for v3.
- The damage sits in a few words whose capitals split into rare pieces: FLANK (`▁FLA NK`), RAPPEL (`▁RAP PEL`), DRONE (`▁DR ONE`), REVIVE.
- The mechanism (unknown pieces give a confident action the threshold cannot stop) is documented only for non-English lines, in `cpp/coop_intent/README.md:171-177`.

**Corrections**
1. **No reported number is affected.** None of the 1016 v3-tag lines (633 study lines + 383 seeds) is all upper case, and the STT-style author wrote 209 of 211 lines in pure lower case.
2. **Upper case is not a v3 regression.** 10 against 8 wrong-family actions is a two-line difference. On full lines the effect is small: upper-case copies of the study lines give 3 of 483 wrong-family for v2 and 2 of 633 for v3. "UPPERCASE BREACH NOW" is BREACH in both.
3. **The alternating-case part is real but unreachable.** It is systematic: on alternating-case copies of the 233 seeds v3 throws a FRAG on 124 and v2 acts wrongly on 62. But the specified input is an STT transcript, and no engine emits alternating case. The edge line exists to break a tokenizer port (`export_cpp.py:41-48`), and `golden.jsonl` is regenerated per model, so a changed golden answer is not a defect.
4. **"Sentence case is not affected" is slightly wrong.** "Rappel" with a capital R and no full stop becomes FRAG in both bots (v2 0.732, v3 0.958).

**The suggested fix is not free**
- Lower-casing changes the text of 65 of the 150 blind v3 lines.
- With the shipped v2, which never trained on them, 5 picks move: near goes from 125 to 126 and wrong-family from 5 to 7 (3.3% to 4.7%).
- So unconditional lower-casing needs a re-train and a re-run of the cross-validation; it is not a patch.

The v3 figures belong to the ensemble trained on this Mac with MPS (`train_v3_final_ens3.log` line 1, `bot_config.json` threshold 0.60). A Windows-trained ensemble will differ in the decimals.

*Recommended action.* **1. Document it (smallest action).** In `cpp/coop_intent/README.md`, section "Known model behaviour", next to the non-English lines, and in the v3 write-up under "what this does not show", add:

"The classifier is cased and was trained and tested only on lower-case and sentence-case transcripts. A transcript in ALL CAPS can become a confident wrong-family action: FLANK gives FRAG or FLASH at 0.99, RAPPEL gives FRAG at 0.97-0.99, DRONE IT gives FRAG; this is 8 of 233 seed commands for v2 and 10 of 233 for v3. A bare capitalised 'Rappel' gives FRAG in both. The threshold does not catch this. The game must pass transcripts in the case style of the training data."

**2. Optional guard, safe for the reported numbers.** In `coop_bot.Bot.classify` and the C++ caller, lower-case a line only when it contains no lower-case letter. This changes none of the 1016 evaluated lines and fixes all 233 upper-case seed commands in both bots.

**3. Do not adopt unconditional lower-casing as a patch.** It alters 65 of the 150 blind lines and moves held-out picks (wrong family 5 to 7 with v2). If it is wanted, it needs a re-train on lower-cased text and a re-run of the cross-validation, recorded in `frozen.txt` as a pipeline change made after the blind lines were seen.

**4. Leave the golden edge line alone.** "mIxEd CaSe FlAnK" is a tokenizer-port probe; its changed answer needs no action.

### gap-final-v3-export-parity #2: For the v3 bot (threshold 0.60) the generated 'at the threshold' step lands on the acting side: decide_tests.jsonl has no 'say again' step under the shipped family gate, and an engine that compares in float32 passes all six checks

Reviewer: minor, cpp. Affects: cpp/coop_intent/tools/gen_tests.py decide_tests for every bot whose threshold rounds up in float32 (the v3 bot's 0.60); the README statement about the threshold boundary; the planned UE5 port, where the threshold is likely to become a float

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

The finding holds as a test-coverage gap; the engine itself is correct.

**What is wrong.** `cpp/coop_intent/tools/gen_tests.py:166` builds the "at the threshold" step as float32(thr) and its comment asserts `float32(thr) < thr`. That is true for 0.58 (0.5799999833) and false for the v3 bot's 0.60 (0.6000000238). The v3 threshold is real: `models/coop-deberta-v3-ens3-v3/bot_config.json` has threshold 0.6, gate family (`train_v3_final_ens3.log:353`).

**Consequence for the v3 files.** The `decide_tests.jsonl` that HANDOFF section 5 step 3 will generate has both boundary steps on the acting side under both gates. Under the shipped family gate it contains no `say_again` step at all; the v2 file has exactly one, and it is this step. This contradicts the generator's own docstring (`gen_tests.py:14-16`) and `cpp/coop_intent/README.md:75`, which both list "say again" and "the threshold boundary" as covered for both gates. The generator prints the action sets but does not assert them. Nothing in HANDOFF, COOP-BOT, DEBERTA-BOT, the C++ README or `frozen.txt` records this as known or intended.

**What is not wrong.** `bot_brain.cpp:185` compares double against double, exactly like `coop_bot.py:162`. On my own boundary set the unmodified engine equals `Bot.decide` on every step, including family sums within 1e-9 of the threshold and exact equality at 0.50. No golden or dialogue line of the v3 model is within 1e-3 of 0.60.

**Corrections to the reviewer's statement.**
- **Grid count:** 22 of 50 grid thresholds round up, and 0.00 and 0.50 are exactly representable, so 24 of 50 give no under-threshold step.
- **The nextafter half of the fix is not enough for 0.60.** With a single label at threshold 0.60, no float32 value distinguishes a float32 comparison from the double one: 0.59999996 says again and 0.6000000238 acts either way. Taking the largest float32 below the threshold restores the `say_again` step and catches the "family gate never says again" mutant, but it cannot catch the float32-compare mutant. Only a family-sum step can (two float32 values of one family whose double sum is less than half a float32 ulp below the threshold).
- **Partial mitigation:** the model-based dialogue check still has 4 `say_again` lines under the family gate and catches the gross mutant (73/77). Nothing catches the float32-compare mutant, whose behavioural window is about 2.4e-8 wide.
- **Not yet in the project tree:** `models/coop-deberta-v3-ens3-v3` has no `cpp/` directory yet, so this is what step 3 will produce, not an existing file.

*Recommended action.* Fix the generator before step 3 of HANDOFF section 5 writes `models/coop-deberta-v3-ens3-v3/cpp`. No engine change: `bot_brain.cpp:185` is correct.

In `cpp/coop_intent/tools/gen_tests.py`, `decide_tests()`, lines 166-167:
1. Build the "at the threshold" value as the largest float32 strictly below the threshold: f32(thr) if f32(thr) < thr, otherwise `numpy.nextafter(numpy.float32(thr), numpy.float32(0))`. Fix the comment `# float32(thr) < thr`.
2. Add one family-sum step: two labels of one family whose double sum is below the threshold by less than half a float32 ulp, with the family's other labels set to 0.0. The current `probs()` helper spreads the rest over every other label, including the same family, so it cannot be used as is. This is the only step that can catch a float32 comparison when the threshold rounds up, as 0.60 does.
3. Before writing the file, assert for both gates that `say_again` is in the action set, that the under-threshold steps have prob < thr and action `say_again`, and that "just over it" is `act`.

Then:
- Log the new `gen_tests.py` hash in `scripts/coop/frozen.txt`; the file is hash-logged at line 149.
- Regenerate the v2 parity files with the same generator.
- When writing the v3 section of `cpp/coop_intent/README.md`, update line 75: "38/38" is stale (now 52 steps), and "the threshold boundary" should only be claimed once the fix is in.

If the generator is left as is, the v3 write-up must say: "for threshold 0.60 the no-model decide tests contain no say-again step under the family gate; say again is exercised only by the 4 dialogue lines that need the model."

### gap-final-v3-export-parity #3: Scripted dialogue, v2 model -> v3 model: 8 of 77 steps change; two are worse ('прикрой меня' now executes REVIVE_ME at 0.604, a bare 'blue' now gets 'say again'), three are better, three end the same

Reviewer: minor, bot-logic. Affects: What the v3 write-up can say about scripted behaviour; cpp/coop_intent/README.md 'Known model behaviour' (its 'прикрой меня' entry is for v1); the dialogue parity check, whose closest step is now 0.004 from the threshold, so a runtime with slightly different arithmetic (NNE, fp16) can flip it

**Verifier (both): partly, minor; reproduced: yes; touches frozen: no**

Every number in the finding reproduces; two of its interpretations do not hold as stated.

**What holds**
- Same 77 lines, v2 (family gate, 0.58) against the v3 model now in models/coop-deberta-v3-ens3-v3 (family gate, 0.60; trained on this Mac with MPS on 2026-10-04, recorded in frozen.txt). Exactly 8 steps change: 17, 34, 37, 60, 61, 64, 71, 75.
- Places, executed places and the "other" slot are identical on 77/77.
- The C++ engine equals the Python bot on 77/77 for v3.
- Bare place words: v2 ignore 9 / say again 7 / act 4, v3 ignore 7 / say again 9 / act 4, with the same four lines changing as reported.
- Nearest step to the threshold: 0.0041 in v3 ("прикрой меня"), 0.0174 in the v2 file.

**Corrections to "two are worse"**
- **Step 37 "прикрой меня" is seed noise on an input the README already declares unsupported.** The v3 members read REVIVE_ME 0.826 / COVER_ME 0.639 / REVIVE_ME 0.648; the v2 members read REVIVE_ME 0.883 / COVER_ME 0.965 / COVER_ME 0.832. It is a 2-of-3 vote that went the other way, not an effect of the v3 data. Other Russian lines move in other directions: "за мной" goes from say again to FOLLOW_ME act (correct), "держи позицию" from say again to HOLD_ANGLE 0.984 act, "prikroy" is FRAG act in both. The README's "Known model behaviour" documents the class with this very line, but only for v1.
- **Step 64 "blue" is a real v3 effect, but "worse" rests on an inference.** In v2 all three members read NONE (0.70 / 0.99 / 0.73); in v3 they read HOLD_ANGLE 0.805 / NONE 0.986 / ENTRY 0.479. The cause is consistent with the new qualifier-only seeds ("push blue", "rush blue", "smoke blue", "nade blue", "hold red"). However, spec_v3.json never says a bare place word is NONE. gen_tests.py lines 104-107 list "blue" among the "vague lines (the 'say again' branch)". The seed note says bare nouns were left out of training on purpose. The place "blue stairs" is still handed to the planner; only the spoken reply changes.
- **Bare place words are unevaluated.** The 150 blind v3 lines contain no line of three words or fewer, so no number under review covers them.

**Correction to the flip risk**
- The claim that NNE or fp16 arithmetic can flip step 37 is speculative. The planned runtime is NNERuntimeORTCpu in fp32. ONNX and PyTorch differ by 1.55e-6 on this line, about 2,600 times less than the 0.0041 margin. The docs do not plan fp16 on CPU.
- The real fragility is re-training: any other training run, such as the Windows one HANDOFF mentions, can flip steps 37, 61, "basement" and "south window", because the members disagree on them.

**Additions the reviewer did not make**
- Under v2 the script never reached the "negated" action and reached "say again" once. Under v3 it reaches "negated" twice (steps 60, 61) and "say again" four times, so those lines now exercise the branches their comment says they are for.
- On steps 60 and 61 the v3 classifier is right (FLANK, GO_NOW) and the leading-negation guard is what stops the bot.
- Step 71 "go to the roof" is an exact v3 training seed, so it is not evidence of generalisation. The unseeded "get up on the roof" (HANDOFF's known v2 error) does move from RAPPEL 0.996 to MOVE_TO 0.910.

No claim in HANDOFF section 4 is contradicted; this concerns the v3 write-up that is still to be written and a stale README section.

*Recommended action.* Documentation only; no change to rules, vocabulary, spec, seeds or labels.

1. **COOP-BOT.md, new "v3" section (and its DEBERTA-BOT.md counterpart).** Add a paragraph along these lines: "Scripted 77-line conversation, v2 → v3 model: 8 steps change; places and the 'other' slot are identical on 77/77. 'go to the roof' RAPPEL → MOVE_TO (this line is a training seed; the unseeded 'get up on the roof' also moves, RAPPEL 0.996 → MOVE_TO 0.910). 'wait for my call' no longer overwrites a queued PLANT with FRAG. 'frag out on three' and a bare 'blue' go from ignore to 'say again?'. 'never mind the wall, flank left' and 'no need to wait, go go go' are now read correctly (FLANK, GO_NOW) but the leading-negation guard still answers 'standing down'. 'take blue on my go' still gets 'say again?'. The Russian 'прикрой меня' flips from COVER_ME 0.62 to REVIVE_ME 0.604 and acts; the three members disagree on it in both versions, so this is seed noise on unsupported input. Bare place words are not in the blind set (no line of three words or fewer). On 20 probes the bot acts on 4 in both versions (v3: 'roof', 'the roof', 'basement', 'south window') and asks 'say again?' on 9 (v2: 7)."

2. **cpp/coop_intent/README.md, "Known model behaviour".** Replace the v1-only entries with per-version answers: «прикрой меня» v1 REVIVE_ME 0.92, v2 COVER_ME 0.62, v3 REVIVE_ME 0.604, all act; "prikroy" FRAG acts in v1, v2 (0.77) and v3 (0.97). Add a line that a bare place word can trigger an action (e.g. "roof" → RAPPEL 0.98 in v3). Update "66-line conversation / 66/66" at lines 47 and 73 to 77 when the v3 export is committed.

3. **Do not write that the parity check is at risk from NNE.** If a sentence on fragility is wanted, use: "dialogue.jsonl is regenerated per model; steps within about 0.02 of the threshold (v3: 'прикрой меня' +0.004, 'no need to wait, go go go' +0.016) will change with any re-training."

4. **Owner decision.** Whether "say again?" (rather than a silent acknowledgement) on a bare place word is acceptable, and whether the game should suppress actions on lines that are only a place. This is a game-side filter using the matcher output and needs no re-training. Adding bare-place NONE seeds instead would change the seeds and would need new blind lines.

5. **Housekeeping, not mine.** /Users/t.losiev/Documents/models_training/project_synth/models/models is a stray self-referencing symlink created 2026-10-04 02:22 inside the read-only tree by some other process.

### gap-final-v3-export-parity #4: Four v2 defaults survive 'change the default model in CMakeLists.txt and coop_bot.py' (shipped.py, export_cpp.py, check_onnx.py, gen_tests.py), and the golden line set silently follows COOP_TAG

Reviewer: minor, evaluation. Affects: HANDOFF section 5 step 3 (last sentence); eval_v3.py section B and v3_shipped.py if re-run after the switch; cpp/coop_intent/README.md 'Regenerating'

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: no**

Every factual statement in the finding holds. No number in HANDOFF section 4 is affected, and the commands exactly as HANDOFF step 3 writes them (COOP_TAG=v3 plus an explicit bot directory) give a correct export. What is wrong is the last sentence of step 3 and the README recipe.

1. Six places hold the v2 path, not two. Besides CMakeLists.txt:24 and coop_bot.py:39 there are shipped.py:14, export_cpp.py:37, check_onnx.py:18-19 and gen_tests.py:30-31. The docstrings at export_cpp.py:19 and gen_tests.py:24 call that default "(shipped)", which becomes false after the switch. Run without an argument, export_cpp.py and gen_tests.py then rewrite the v2 directory's cpp/ files.

2. shipped.py's docstring says it uses "the model directory coop_bot.py uses", but it has its own constant. For the v3 study that constant must stay v2, because it is the baseline of eval_v3 section B. The risk is latent, not present:
- v3_shipped.py names ens3-v2 in its docstring and stores the model name, and eval_v3.py prints it. The "it never saw" header would only become false if someone edited shipped.py to v3 and re-ran v3_shipped.py.
- v3_noharm.py neither prints nor stores the model name, so after the switch its "shipped bot" is silently v2.
- eval_v3.py itself only reads the stored results_v3_shipped.json.

3. Only export_cpp.py depends on COOP_TAG (lines 115-116). check_onnx.py and gen_tests.py do not import coop_v2; they inherit the set through golden.jsonl. The golden set is 754 lines with the tag unset, 762 with v21 and 1062 with v3. A v21 export contains 0 of the 150 v3 lines and 0 of the 150 place seeds. Nothing compares the tag with bot_config "trained_on"; export_cpp.py prints the line count but not the tag.

4. A wrong-tag export weakens only the tokenizer and model parity checks. location_tests.jsonl always carries the 150 v3 lines and 150 place seeds, because gen_tests.py reads those files directly, so the matcher parity is unaffected.

5. cpp/coop_intent/README.md:158-166 still gives the v21 recipe with the v2 directory. HANDOFF step 5 already lists the README update as pending, but does not say the recipe's tag must change.

6. The v3 model now exists on this machine: models/coop-deberta-v3-ens3-v3 has bot_config.json (Oct 4 00:33, threshold 0.6, family gate, trained_on names seed_commands_v3.json) and no cpp/ yet. Step 3 is therefore the immediate next action.

Not run: "all six checks pass on a wrong-tag export" is by construction. Each check compares C++ with whatever Python wrote, and the v2 directory with its 762-line golden passes all six. I did not export the v3 ensemble under v21 to demonstrate it.

*Recommended action.* 1. **HANDOFF.md section 5 step 3, last sentence.** Replace "Затем поменять модель по умолчанию в CMakeLists.txt и в coop_bot.py" with the full list: CMakeLists.txt:24, coop_bot.py:39, export_cpp.py:37 (and docstring :19), check_onnx.py:19, gen_tests.py:31 (and docstring :24). Add: "shipped.py:14 stays on coop-deberta-v3-ens3-v2: it is the baseline of the v3 study (v3_shipped.py, eval_v3.py section B, v3_noharm.py); do not re-run v3_shipped.py against the v3 model."

2. **Acceptance check for step 3.** Add to the same step: models/coop-deberta-v3-ens3-v3/cpp/golden.jsonl must have 1062 lines; 762 or 754 means the export ran under the wrong COOP_TAG.

3. **scripts/coop/shipped.py:2-3.** Change the docstring to say the directory is pinned to the v2 bot as the v3 study's baseline, not "the directory coop_bot.py uses". Alternatively pass model_dir explicitly in v3_shipped.py:20.

4. **scripts/coop/v3_noharm.py.** Print the model name and store it in results_v3_noharm.json.

5. **scripts/coop/export_cpp.py.** After loading cfg, print V.TAG and V.SEED_FILE, and refuse to write golden.jsonl when V.SEED_FILE is not named in cfg["trained_on"]. Skip the check under --config-only, which the HANDOFF recipe runs without a tag.

6. **cpp/coop_intent/README.md:158-166.** In the step 5 update, rewrite "Regenerating" for the v3 bot (COOP_TAG=v3, models/coop-deberta-v3-ens3-v3) and state that only export_cpp.py reads the tag.

7. **frozen.txt.** Record the new hashes of every edited file that is logged there (shipped.py, v3_shipped.py, export_cpp.py, check_onnx.py, gen_tests.py). Leave results_v3_shipped.json as it is.

None of this changes matcher rules, vocabulary, spec, seeds or labels.

### gap-final-v3-export-parity #5: coop_cli --bench reports 0 MB of memory on macOS; latency of the v3 export equals v2 on this machine

Reviewer: note, portability. Affects: models/<bot>/cpp/bench.txt for a bot benchmarked on a Mac; the memory figures in cpp/coop_intent/README.md

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

Both halves of the finding hold, and neither is a defect in the v3 claims.

1. Memory. `WorkingSetMb()` in `cpp/coop_intent/tools/coop_cli.cpp:87-93` has a body only under `_WIN32` and otherwise returns 0. Every `--bench` run on macOS therefore prints "working set +0 MB (0 MB total)". Nothing documents this: there is no comment at the function, and no mention in `cpp/coop_intent/README.md` or `HANDOFF.md`. HANDOFF section 3 only says the macOS build was never checked.

Two refinements to the reviewer's wording:
- The memory figure can be measured here from outside the tool. Sampled `ps` RSS is about 3.24 GB for both v2 and v3 in every configuration. `/usr/bin/time -l` on v2 gives 3.49e9 bytes maximum RSS and 3.47e9 bytes peak footprint. So the README's "working set 2.3 GB" is a Windows figure and does not carry over to this Mac, where the same three models sit at about 3.2 GB resident.
- The README states the machine (section title "Speed and memory (i9-10900K, ...)"); `bench.txt` itself does not. The README's Windows figures stay valid; only a `bench.txt` produced on a Mac would carry the false 0.

2. Latency. v3 equals v2 on this machine, as expected for the same architecture, 24 labels and a byte-identical `vocab.tsv`. On the same 762 lines the v3 models are within 0.2 ms of v2 in all five configurations. The reviewer's one visible gap (in turn, 4 threads: 21.3 against 19.1 ms) is run-to-run noise on a shared machine; my run gives 19.5 against 19.0, and 19.2 for v3 on v2's lines. The slightly higher v3 p99 on its own bench set comes from longer lines (8.9 against 8.2 tokens). Absolute numbers are not comparable with `bench.txt` (Windows i9-10900K: 45.6 / 61.3 / 123.2 ms; load 5.6 s against about 0.85 s here).

HANDOFF section 5 does not ask for a v3 bench, so this only matters when step 5 (the README update) is written.

*Recommended action.* No change is needed to any v3 number.

1. `cpp/coop_intent/tools/coop_cli.cpp`, `WorkingSetMb()` (lines 87-93): add non-Windows branches. On macOS use `task_info(mach_task_self(), MACH_TASK_BASIC_INFO, ...)` and return `resident_size / 1048576.0`; on Linux read the resident pages from `/proc/self/statm`. If that is not wanted, have `RunBench` (line 460) print "working set n/a" when the value is 0 instead of "+0 MB (0 MB total)". Record the new `coop_cli.cpp` hash in `scripts/coop/frozen.txt`; this is tooling and does not affect the held-out numbers.

2. When step 5 of HANDOFF is done (the v3 update of `cpp/coop_intent/README.md`, and any v3 `bench.txt`): put the machine name in the first line of `bench.txt`, and add a sentence such as: "v3 has the same architecture and label count as v2, so latency and memory are unchanged. On an Apple M5 Pro (ONNX Runtime 1.30.0 CPU, arm64), one thread per member: 13 ms median and 17 ms p99 for both v2 and v3; members in turn on one thread: 22 ms median; load 0.85 s; about 3.2 GB resident, measured with ps because coop_cli reports memory only on Windows. The 45.6 to 123 ms and 2.3 GB figures above are from the i9-10900K Windows machine and are not comparable across machines."

### gap-final-v3-export-parity: checked and found right

- HANDOFF step 3 works as written on this machine for the real three-member v3 model (run in a scratch mirror of the project layout, relative paths as in HANDOFF): COOP_TAG=v3 export_cpp.py -> 'wrote ...: 3 ONNX model(s), vocab 128000 pieces, golden 1062 lines' in 91 s (legacy TorchScript exporter on torch 2.14.1, DeprecationWarning only); check_onnx.py in 22 s; gen_tests.py in 9 s; all exit 0
- ONNX against PyTorch for the v3 ensemble: same argmax on 1062/1062 golden lines, max |dp| 1.73e-06 (onnx_check.json; v2 was 3.4e-06 on 762 lines); each modelN.onnx is 738696515 bytes, the same size as the v2 files
- Golden line set: 1062 = 633 study lines (v1 363, v2 120, v3 150) + 383 seeds + 16 probes + 30 edge lines, in that order; all 150 v3 lines and all 383 seeds of seed_commands_v3.json are present
- intent_config.json: threshold 0.6, gate family, members model0..2.onnx, max_len 64; the locations block equals locations.json without its underscore keys; the only key that differs from the v2 intent_config.json is threshold (0.58 -> 0.6); labels and families equal coop_v2.INTENTS and FAMILY
- vocab.tsv is byte-identical to the v2 one; the v3 members' tokenizer.json differs from v2 only in the saved 'padding' field (model, normalizer, pre_tokenizer and added_tokens are equal); token ids are equal on all 741 texts the two golden files share
- Six coop_cli checks, out-of-tree Release build (AppleClang, arm64), --model-dir <scratch v3 bot>/cpp, all exit 0: tokenizer tests 9231 lines (normalizer 9231/9231, ids 9231/9231, regex slots 9227/9227, +4 lines not compared, 0 searches given up); location tests 8563/8563 (2235 name a place); gate tests 1469 rows x 2 gates 2938/2938; decide tests 52/52; golden 1062/1062 ids, 1062/1062 argmax, 1062/1062 within 1e-4, max |dp| 1.76e-06 ('café'); dialogue 77/77
- The same six checks on a -fsanitize=address,undefined build: identical counts, zero sanitizer reports in any log
- The location parity set regenerated for the v3 bot is 8563 lines, not HANDOFF's 8570 (that count belongs to the v2 directory), and it is richer: 2235 lines name a place (v2 set: 1371), 526 name more than one (196), 658 carry a role (407), 512 a flag (201)
- Threshold boundary, Python against C++: the unmodified engine equals coop_bot.Bot.decide on 104/104 constructed boundary steps (thresholds 0.60, 0.58, 0.50, 0.62; both gates; one float32 step under / at / over; family sums within 6e-9 of the threshold), Release and sanitizer builds
- No golden line (1062) and no dialogue step (77) has a confidence within 1e-3 of 0.60 under either gate; the nearest is 'прикрой меня' at 0.6041, so float32 against double cannot flip act / say_again on any generated line
- Older training data, golden answers under each bot's own gate and threshold (v2 family 0.58, v3 family 0.60): on the 483 older lines and the 233 older seeds the three-way outcome (intent plus act / ignore / say again) differs on 0 of 716; both bots give an accepted intent on all of them; lowest confidence 0.987 (v2) and 0.981 (v3). Also 0 differences with each bot's top-gate threshold (0.48 / 0.60)
- All 233 seeds of seed_commands_v21.json are in seed_commands_v3.json with the same label; the final v3 bot answers all 1016 of its training lines (633 + 383) with an accepted intent; no text carries two different majority labels
- The 16 probes: v2 and v3 pick the same, accepted intent on all 16
- Dialogue v2 against v3: places, executed places and the 'other' slot are identical on 77/77 steps (they depend only on locations.json and the regexes)
- gen_tests.py does not touch coop_bot_log.jsonl: dialogue() redirects coop_bot.LOG to <bot>/cpp/_dialogue_log.jsonl and removes it; the scratch copy's coop_bot_log.jsonl has the same sha256 before and after (c0d14edb...)
- Latency: no change from v2 to v3 on this machine (11.8 against 11.7 ms median per line at --threads 4)
- The project tree was not modified: no file under project_synth (outside .venv) is newer than the start of this review, models/coop-deberta-v3-ens3-v3 still holds only bot_config.json and seed0..2, the existing models/models link was left alone and not followed

## Gap round: a fresh blind author (`gap-fresh-blind-author`)

### gap-fresh-blind-author #1: Enemy-place words have no apostrophe-less STT forms: after 'theyre / hes / shes / theyve' the enemy's place gets no role and becomes the bot's target

Reviewer: major, matcher. Affects: Matcher primary target on STT-style two-place lines (Python locations.py and C++ locations.cpp); a caveat to the 96.7% / 94% exact-target figures in HANDOFF section 4; bot behaviour: an order executed at the enemy's place.

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: yes**

The finding holds on every point I re-derived, and the gap is wider than the pronoun list.

**Root cause.** The matcher's tokenizer splits on the apostrophe, so "they're" becomes 'they' + 're' and "awp's" becomes 'awp' + 's'. The role and status word lists hold only the split pieces for the enemy and status cases. `locations.json` `words.role_them` has they/he/she but none of theyre/hes/shes/theyve (nor theres/theyll/whos). The same file does carry fused forms for the player and negation: `role_mine` = i, im, ill, ive; `role_not` has dont; `after_fill` has thats.

**Effect.** When an enemy or status place comes first in a transcript without apostrophes, it gets role None and becomes primary, with no flag. Python and the C++ port behave identically.

**Fresh blind line c04.** For 'theyre pushing east window fall back to white stairs' the matcher gives primary window/east with role None; the truth is stairs/white. The final v3 ensemble answers FALL_BACK at 0.993 and `Bot.decide` returns action "act", so the planner would be handed the window the enemy is pushing. With "they're" the primary is stairs/white. The shipped v2 classifier does not act on this line (TAKE_COVER 0.50, say_again).

**The 150 project blind lines cannot see this.**
- r6 and cs contain no apostrophe-less they/he/she/there form; their contractions carry apostrophes (29 and 25 lines of 50 have one).
- stt has no apostrophe in any of its 50 lines; its only such token is 'theres', on a line where Main gets role status from the following 'is'.
- stt's one pronoun-triggered "them" role uses the uncontracted 'they all sitting in basement ...'.
- So the 96.7% and the held-out 94% are correct as measured but do not exercise this case.

**Wider than the reviewer stated.** Removing apostrophes from the 150 project blind lines drops exact target from 145/150 to 142/150 (r6 48 to 47, cs 50 to 48, stt unchanged). The three lines that flip:
- csv3_033: 'theyre all stacked on brown ... east door' gives stairs/brown.
- csv3_040: 'awps up on the roof ... behind the table' gives the roof ('awps' is not in `role_them`).
- r6v3_007: 'West windows got a trap ... other window' gives window/west (the status 's' is lost).

The final v3 bot acts on all three stripped lines at 0.997 to 0.999 confidence; it was trained on the original lines, so that confidence is not a held-out result.

**How often it bites.** It depends on whether the game's speech-to-text keeps apostrophes, which the project has not fixed. The project's own stt persona drops them: 4 of its 211 lines carry one, and its older lines contain theyre/hes/theres 6 times. Measured rates under apostrophe-less input: 1 of 60 fresh place lines (1 of 6 two-place lines) and 3 of 150 project lines.

**Severity.** I keep major. The size is about 2 points, but the error is a silent, confident order executed at the enemy's place, in the input style COOP-BOT.md calls closest to the real pipeline. I could not verify that the fresh author was written blind; that rests on the file's own statement.

*Recommended action.* Do not edit the vocabulary silently; the fix touches frozen material.

**1. Write-up now.** Add a known limitation to the v3 section of `COOP-BOT.md` (and `HANDOFF.md` section 4, `DEBERTA-BOT.md`), next to the 96.7% / 94% figures:

"The matcher recognises an enemy or status place through words split at the apostrophe (they're, he's, awp's, window's). In a transcript without apostrophes (theyre, hes, awps, windows) that place gets no role and becomes the bot's target. None of the 150 blind lines tests this: r6 and cs write apostrophes, stt has no such line. With apostrophes removed from the 150 lines, exact target is 142/150 instead of 145/150, and a fresh blind line ('theyre pushing east window fall back to white stairs') sends FALL_BACK to the east window. The figures therefore hold for transcripts that keep apostrophes, or that avoid contractions."

**2. Fix as rules v3, recorded in `frozen.txt` as made after blind lines were seen.**
- `scripts/coop/locations.json`, `words.role_them`: add theyre, theyve, theyll, theyd, hes, shes, plus the fused 's forms of the nouns already there (awps, snipers, campers, …).
- Decide how a fused status 's ('windows got', 'doors clear') is handled.
- Check `role_stop` (youre) and `role_mine` (id) for the same asymmetry.
- Then run `python locations.py --dev`, `export_cpp.py <bot> --config-only`, `gen_tests.py <bot>`, and the C++ `--location-tests`.

**3. Measurement.** Report the new exact-target number only on newly written blind lines that include apostrophe-less callout + order lines. Until then, mark any number from the 150 lines or the fresh 80 as after tuning.

**4. Pipeline decision.** Record whether the game's speech-to-text keeps apostrophes. If it does, state that in the write-up as the condition under which this limitation does not bite.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: yes**

The finding stands on every fact I checked; I could not refute it, only narrow its weight.

**Mechanism.** The matcher's tokenizer splits on every non-alphanumeric byte, so "they're" becomes they + re and the role is found from "they". Without the apostrophe the single token theyre / hes / shes / theyve is in no word list. The enemy's place then gets role None and, being first in the line, becomes the primary target. Python and the C++ port behave identically.

**It is an omission, not a decision.**
- The same vocabulary already carries apostrophe-less forms for the player and for negation (role_mine: im, ill, ive; role_not: dont; after_fill: thats).
- The project's own stt persona writes without apostrophes: 0 of 50 v3 stt lines contain one, with "dont" five times and "theres" once.
- Earlier stt blind files, which predate locations.json, already contain the fused forms: "hes" in blind/author_stt.json, and "theyre" twice plus "hes" once in blind/v2/author_stt.json.
- No document, code comment, spec or frozen.txt entry mentions apostrophes. The only related caveat is the general one at COOP-BOT.md:542 ("Real player speech and a real STT engine. The STT author imitates one").

**Scope is slightly wider than reported.** The same apostrophe dependence hits noun + 's forms: "awp's" becomes "awps" (role them lost), "window's got" loses its status role, and "main's" becomes "mains", which drops the place entirely.

**No reported number is wrong.**
- The held-out 94% (47/50) is unaffected: no stt line contains a fused enemy contraction. The one stt line of this shape, sttv3_033 "they all sitting in basement smoke the brown stares...", uses a bare "they" and passes.
- The fresh author's 57/60 (95%) is consistent with 94%.
- The 96.7% does lean on the apostrophes the r6 and cs authors wrote. Deleting every apostrophe from the 150 lines gives 142/150 (94.7%): r6 48 to 47, cs 50 to 48, stt unchanged.
- Only one of those three lost lines is the pronoun class: csv3_033 "they're all stacked on brown, so loop around east door...".

**Why minor rather than major.**
- It bites only if the game's speech-to-text drops apostrophes; the project has not chosen an engine.
- Observed frequency is about 1 in 60 to 1 in 150 place lines.
- When it does hit, the outcome is the costly kind: on c04 the final v3 bot acts (FALL_BACK 0.99) with an unflagged, role-less primary at the enemy's window. The shipped v2 bot would have asked again (0.50, below 0.58).
- So it needs a known-limitation sentence and a recorded vocabulary fix, but it does not invalidate the section 4 claims.

Two trivial corrections to the finding: it lists six probe pairs, not five (all six behave as stated), and the 150 project lines do contain the pattern once with an apostrophe (csv3_033), where it passes.

*Recommended action.* **1. Write-up (touches nothing frozen).** Add a known limitation under the matcher table in HANDOFF.md section 4 and in the v3 section of COOP-BOT.md when it is written (HANDOFF step 5):

"Roles depend on apostrophes. The matcher finds whose place it is from the word before it. In a transcript without apostrophes the fused forms theyre / hes / shes / theyve, and noun + s forms such as 'awps up on the roof', 'west windows got a trap' and 'mains smoked', are in no word list. The enemy's or status place then gets no role and, when it comes first, becomes the primary target ('theyre pushing east window fall back to white stairs' gives window east). None of the 50 held-out stt lines contains such a form, so the 94% does not measure this. With all apostrophes deleted the 150 blind lines score 142/150 (94.7%) instead of 145/150. Which form the game's speech-to-text emits must be settled before the matcher is used in the game."

**2. Fix (touches frozen: a vocabulary change after blind lines were seen).**
- In /Users/t.losiev/Documents/models_training/project_synth/scripts/coop/locations.json, add "theyre", "hes", "shes", "theyve" to words.role_them.
- Review the 's forms separately; they need a rule, not a word.
- Add apostrophe-less cases to locations_dev.json.
- Re-export: export_cpp.py --config-only, then gen_tests.py.
- Record it in frozen.txt as a new vocabulary/rules version made after the blind lines and after this fresh line.
- The edit leaves the 150-line and 483-line records unchanged (0 records differ), so 96.7% and 94% stay numerically the same. Any claim that the class is handled still needs newly written blind lines, per HANDOFF section 6.

### gap-fresh-blind-author #2: Fresh blind author, matcher rules v2: exact target 95.0% (57/60) [86.3, 98.3], not below the quoted 94% / 96.7%; holds only for lines that use the dictionary's own names

Reviewer: note, evaluation. Affects: HANDOFF section 4, row 'matcher, rules v2: 94% on held-out author stt; 96.7% on all': supported by one independent sample for lines written with the spec's names; says nothing about phrasing outside the dictionary.

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

Every number in the finding reproduces exactly, and nothing in the docs already covers it; it is a supporting measurement, not a defect.

On the reviewer's 80 fresh lines, the matcher at the frozen v2 hashes gives:
- **Exact primary target, 60 place lines:** 57/60 = 95.0%, Wilson [86.3, 98.3].
- **Without the 6 arguable lines:** 52/54 = 96.3% [87.5, 99.0].
- **By style:** STT 28/30, typed 29/30.
- **All 80:** 77/80 = 96.2% [89.5, 98.7]; no target at all on the 20 plain orders.
- **unknown_modifier flag:** raised on all 5 lines that need it, plus one false raise (i01).
- **Role:** 49 of 50 acted-on orders carry no role; a18 "smoke off the main door for me" gets role "from". Callouts 6/6 targets, 5/6 with role "them"; negated 2/2 with role "not".
- **Target + flag + role:** 56/60 = 93.3% [84.1, 97.4]; 51/54 without arguable.
- **Misses:** c04, i01, i02.
- **v2 rule additions switched off (v2 vocabulary kept):** 56/60; only g02 changes.

Corrections and limits the write-up sentence needs:
1. **Title wording.** 95.0% is above the held-out stt figure (94.0%) but below the all-150 figure (96.7%). It is "not below" only in the sense that the differences are not significant (Fisher p = 1.0 vs 47/50, 0.69 vs 145/150).
2. **Low power.** A true rate of 90% would still give at least 57/60 in 14% of samples, and 88% in 6%. The sample rules out a rate far below about 86%; it cannot separate 90% from 97%, nor rules v1 (132/150) from v2 (p = 0.20).
3. **Closer to the matcher's tuning set than disclosed.** The reviewer's novelty check compared only against classifier training texts. Against locations_dev.json, 2 fresh lines are token-identical ("two on red stairs", "take the other door"), 8/60 have similarity ≥ 0.8 and 23/60 ≥ 0.6. Similarity to the r6/cs blind lines is low (median 0.36, none ≥ 0.8).
4. **Easier sample.** Lines average 6.8 tokens against 12.5 / 10.5 / 10.1 for r6 / cs / stt, and every non-null truth target is in the matcher's list (58/58), so only dictionary names are tested.
5. **Other-sense 0/2 is the informative part.** The two stt other-sense lines that v2 fixed use the same idioms as tuned-on lines ("through the roof" in r6v3_039, "my main" in csv3_035). The fresh idioms ("short window", "went south") both fail, and the dev regression already lists the time sense of "window" as an open failure.
6. **Blindness is self-attested.** File times are consistent with it (lines 02:43:30, hash 02:43:35, scripts copy 02:43:41, first matcher run 02:44:08), but they cannot show which project files were read before writing.

The fresh labels follow the same conventions as the project's readers ("the other X" is object only with unknown_modifier false; "back/left door" is object only with unknown_modifier true), and the exact criterion is the one eval_v3.py uses.

*Recommended action.* No code, rule, vocabulary, spec, seed or label change.

In the v3 write-up (the future "v3" section of /Users/t.losiev/Documents/models_training/project_synth/COOP-BOT.md, and under the matcher table in section 4 of /Users/t.losiev/Documents/models_training/project_synth/HANDOFF.md), add one row or sentence next to the stt figure:

"Review check, one more author (an AI reviewer who is also the only labeller; 60 place lines + 20 plain orders written from blind/spec_v3.json and hashed before the matcher was run; short lines, 6.8 tokens against 10-12.5; dictionary names only): rules v2 exact target 57/60 = 95.0% [86.3, 98.3], against 47/50 = 94.0% [83.8, 97.9] on held-out stt. No place found on the 20 plain orders. With the flag and role also required: 56/60. Both 'place word in another sense' lines failed (0/2, new idioms). n = 60 does not separate 90% from 97%, and the figure says nothing about place names outside locations.json."

Do not word it as "not below 96.7%".

Keep /private/tmp/claude-501/-Users-t-losiev-Documents-models-training/0bf8b430-1f44-4ab7-af53-de801211b9f7/scratchpad/review/gap-fresh-blind-author/author_fresh.json out of tuning. If it is ever copied into scripts/coop, record its hash in frozen.txt as review lines already seen. Any later matcher edit motivated by c04, i01, i02 or a18 needs new blind lines before a held-out number is quoted.

### gap-fresh-blind-author #3: Fresh blind author, classifier: final v3 is better than shipped v2 on place lines (near 98.3% vs 91.7%, 4 lines better, none worse) and equal on plain orders (20/20 both); the sample is seed-like, so it confirms the direction, not the size

Reviewer: note, evaluation. Affects: HANDOFF section 4: 're-training is needed, the final v3 model is the next step' and 'older orders not harmed'. Both are supported on a fresh author for short, seed-like orders; in hit-rate terms the gain here is +6.7 points (score +10.0), and the evidence on novel phrasing is 8 lines.

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

The finding holds as stated. On the reviewer's 80 fresh lines the v3 ensemble in models/coop-deberta-v3-ens3-v3 beats shipped v2 on the 60 place lines and ties it on the 20 plain orders, each at its own bot_config gate.

**Place lines (60)**
| | shipped v2 (family 0.58) | final v3 (family 0.60) |
|---|---|---|
| exact | 53/60 (88.3%) | 58/60 (96.7%) |
| near | 55/60 (91.7%) | 59/60 (98.3%) |
| wrong family | 1/60 | 0/60 |
| say-again on orders | 3/52 | 1/52 |
| acts on a non-order | 1/8 | 0/8 |

- **Paired difference:** near +6.7 [+1.7, +13.3] with 4 lines better and 0 worse (sign test p = 0.125); exact +8.3 [+1.7, +16.7] with 5 better and 0 worse (p = 0.0625).
- **Plain orders:** 20/20 exact for both, no pick changes, lowest gate confidence 0.977 (v2) and 0.989 (v3).
- **Without the 6 arguable lines (54):** near 54/54 vs 51/54, exact 53/54 vs 49/54.
- **All 80:** near 79/80 vs 75/80.
- **Only v3 misses:** c01 goes to HOLD_OTHER_ANGLE (same family, both models) and c02 is say-again at 0.400 (ENTRY 0.394, HOLD_ANGLE 0.252, MOVE_TO 0.224).

**Corrections and additions to the reviewer's statement**
1. **Score interval.** The exact percentile-bootstrap upper bound for the score difference is +23.3, not +21.7; the reviewer's value is a Monte-Carlo edge at 4000 resamples (P(S<=13/60) = 0.9736 < 0.975).
2. **The lower bound is structural.** With k lines better and 0 worse, a percentile bootstrap excludes zero whenever k >= 4 (probability of a resample with no discordant line is 1.6%). The +1.7 lower bound is therefore not evidence beyond the sign test.
3. **Two of the four near gains sit at a threshold, one on each side.** The reviewer named a08 (v3 FRAG mass 0.611 against 0.60; one of three members says NONE 0.94). The other is a21 "okay head up to the roof": shipped v2's raw pick is already MOVE_TO at 0.5665 against its 0.58 threshold (one member says RAPPEL 0.94). Over v2 thresholds 0.50-0.66 and v3 thresholds 0.50-0.70 the near gain is 2 to 5 lines and never negative.
4. **How seed-like the sample is.** By the project's eval_v2.novelty() measure, 60 of the project's own 150 v3 lines are at or above 0.5 (median 0.45), against 52 of 60 fresh place lines (median 0.62). For 38 of those 52 the nearest training text is a seed. Fresh place lines average 6.7 words against 10.0-11.8 for the project's v3 authors. If the tf-idf is fit on training texts only, the split is 54/6 rather than 52/8.
5. **"Final v3" is the Mac-trained model.** It was trained on this machine on MPS (train_v3_final_ens3.log line 1 "device: mps", finished 00:33 on Oct 4), not the RTX 4090 run HANDOFF section 4 refers to. A re-train on another device gives different weights, and a08 at 0.611 could flip.

**Refutation attempts that failed**
- Not already documented: HANDOFF, COOP-BOT.md and frozen.txt contain no fresh-author check and no final-v3 measurement.
- Labels on the five discordant lines are unambiguous under blind/spec_v3.json (roof is MOVE_TO, a callout is NONE, "push in ... clear it out" is ENTRY, "Nade" is FRAG, "fall back to" is FALL_BACK).
- final() trains on items + seeds, 633 lines including all 150 v3 lines, so the "unseen place lines" framing is correct.

**Cannot be verified:** that the fresh lines were written from the spec alone. The hash stamp (00:43:35Z) precedes the reviewer's probability files by about a minute but postdates the model by about two hours.

*Recommended action.* No code or data change. Add one paragraph to the v3 write-up (the "v3" section of COOP-BOT.md and the table in HANDOFF.md section 4), worded as a direction check:

"Fresh-author check (review): 60 place lines + 20 plain orders written from blind/spec_v3.json by one AI author who is also the only labeller. Model: models/coop-deberta-v3-ens3-v3 as trained on the Mac (MPS), family gate 0.60, against shipped v2 at family 0.58. Place lines: near 98.3% (59/60) vs 91.7% (55/60), wrong family 0 vs 1; 4 lines better, 0 worse (sign test p = 0.125). Two of the four sit within 0.015 of a gate threshold (v2 'head up to the roof' 0.567 < 0.58; v3 'Nade the sofa' 0.611 >= 0.60), so the gain is 2 to 5 lines for nearby thresholds and never negative. Plain orders: 20/20 for both, no pick changed. The lines are short and seed-like: 6.7 words against 10-12 for the project's v3 lines, and 52/60 at cosine >= 0.5 to a v3 training text (38 of them to a templated seed, 2 verbatim) against 60/150 for the project's own v3 lines. This confirms the direction of the leave-one-author-out result, not its size (+10.7 / +11.3), and says nothing about long or novel place lines (8 lines: 7/8 vs 6/8)."

Three conditions on how it is reported:
- Do not quote the bootstrap lower bound (+1.7) as significance, and give the score interval as [+1.7, +23.3].
- If the model is re-trained on another device, re-run the 80 lines before quoting these numbers.
- If the 80 lines are brought into the project, record their hash in frozen.txt as "written after final v3 existed, scored once", and do not use them to tune thresholds, seeds or rules.

A claim about novel phrasing needs new lines written to be unlike the seeds, by an author who has not seen them, with two annotators.

### gap-fresh-blind-author #4: Fresh blind author, joint rate: intent and target both right on 91.7% (55/60) with final v3, 85.0% with shipped v2; all five v3 misses are two-place or other-sense lines

Reviewer: note, evaluation. Affects: The v3 write-up: HANDOFF section 4 reports intent and target separately; this is the joint figure on lines the final model has not seen.

**Verifier (both): partly, note; reproduced: yes; touches frozen: no**

Every number in the finding reproduces exactly, but the figure is optimistic and should not stand as the write-up's joint rate on its own.

**What holds (final v3 + matcher rules v2, the reviewer's 60 fresh place lines):**
- Exact intent and exact target: 55/60 = 91.7% [81.9, 96.4]; same-family intent and exact target: 56/60 = 93.3% [84.1, 97.4]; with flag and role also right: 54/60 = 90.0%.
- Shipped v2: 51/60, 53/60, 50/60.
- Without the 6 arguable lines: v3 51/54, 52/54, 50/54; v2 47/54, 49/54, 46/54.
- All 80 lines: v3 75/80, v2 71/80.
- The five v3 misses are c01 (same-family intent), c02 (say-again), c04 (wrong primary), i01 and i02 (spurious target, flagged unknown_modifier / unsure); the intent misses and target misses are disjoint.
- Slot regexes: 5/5 on-signal, 4/4 other, no false hit; f01..f05 are queued.
- The bot acts with a wrong or contradictory place on a18 (role=from, because "off" is a role_from word), c04, i01, i02.
- The fresh file's hash matches, and it was written at 02:43, after the final model finished at 00:33.

**Three corrections:**
1. **Not all lines are unseen.** a05 and a09 (place) and p02 and p18 (plain) are verbatim copies of training texts (seed_VAULT_WINDOW_9, seed_TAKE_COVER_16, seed_MOVE_TO_6, stt_118). 52 of the 60 place lines are near-copies of a training text (char n-gram cosine >= 0.5). The joint rate is 50/52 on the near-copies and 5/8 exact (6/8 near) on the 8 novel lines. Without the two verbatim lines it is 53/58 = 91.4%.
2. **The c01 miss is label strictness.** The project's own truth accepts both HOLD_ANGLE and HOLD_OTHER_ANGLE for the same pattern (csv3_049 "I'm holding main, you go stare at south window"). Under that convention the comparable figure is 56/60 = 93.3%, with two-place lines at 4/6.
3. **The fresh lines are easier than the project's blind lines** (6.7 vs 10.6 words per line). The same joint rate on the project's own 150 blind v3 lines appears in no log or document:

| bot (matcher rules v2) | lines | near intent and exact target |
|---|---|---|
| re-trained ens3, leave one author out, family gate | all 150 | 88.0% (132/150) [81.8, 92.3] |
| same, top gate | all 150 | 87.3% (131/150) |
| same, either gate | held-out author stt | 78.0% (39/50) [64.8, 87.2] |
| shipped v2 | all 150 | 80.7% (121/150) |

By kind on the 150 (family gate): two_places 12/15, other_sense 4/6, on_signal 9/12, place 52/60, all other kinds 55/57. Two-place and other-sense lines are weak in both data sets, but "every other category is perfect" is true only of the easy fresh set.

Nothing in the project is wrong here; this is a missing figure in the write-up.

*Recommended action.* Write-up only; no change to rules, vocabulary, spec, seeds or labels.

1. **HANDOFF.md section 4 and the future "v3" section of COOP-BOT.md**: add a row "intent (near) and exact target both right" taken from the project's own blind lines:
   - re-trained ens3, leave one author out, family gate, matcher rules v2: 88.0% (132/150) [81.8, 92.3], marked "r6 and cs after matcher tuning";
   - held-out author stt: 78.0% (39/50) [64.8, 87.2];
   - shipped v2: 80.7% (121/150).
2. **scripts/coop/eval_v3.py**: add a short section D that prints this joint rate (E.deploy picks combined with LOC.find exact target, by author and by kind) so the row is reproducible, and record the new hash in frozen.txt.
3. **Fresh-author figure**: quote it only as a secondary line, worded: "final v3 on 60 place lines written during review after the model was trained (one AI author who is also the only labeller; short lines, 6.7 words against 10.6; 52/60 near-copies of training texts, 2 identical to seed commands): intent (near) and target both right 93.3% (56/60) [84.1, 97.4], exact intent 91.7% (55/60)". Do not write "lines the final model has not seen".
4. **Weak kinds**: name two-place lines (12/15 on the project's lines, 3-4/6 fresh) and other-sense lines (4/6, 0/2) as the weak kinds, and list the lines where the bot acts on a wrong or contradictory place: "smoke off the main door" (role=from), "theyre pushing east window fall back to white stairs" (enemy's window as target), "short window", "went south".

The "theyre" and "off" causes are matcher vocabulary. Changing them would touch frozen material and need new blind lines, so they are not part of this action.

### gap-fresh-blind-author: checked and found right

- Phase 1 order of work: only blind/spec_v3.json was read before the 80 lines were saved and hashed (S/author_fresh.json, sha256 2b53eddc7c10fd9c6d6cbdc307372a844a8a68a0267d8c0688af4af21c06e27b, 2026-10-04T00:43:35Z, file made read-only); HANDOFF.md, locations.py and everything else were opened afterwards. No label was changed after any prediction was seen.
- Composition as assigned: 24 one-place, 6 floor, 6 two-place, 6 callouts, 5 unknown-modifier, 5 on-signal, 4 'other', 2 negated, 2 other-sense, 20 plain; 40 typed / 40 STT style (30/30 and 10/10); 6 lines marked arguable (c02, c04 intent; g01 intent and flag; g02 target and flag; g03, g04 flag only).
- The matcher that was measured is rules v2 as frozen: sha256 of the scratch copies of locations.py (b3e9314a...) and locations.json (890d651a...) equal frozen.txt lines 140-141; vocabulary version 2.
- Matcher exact target on the fresh author: 57/60 place lines (95.0%, Wilson 86.3-98.3), 77/80 with the plain orders; no target invented on any of the 20 plain orders (S/score.log).
- unknown_modifier flag raised on 5 of 5 lines that single out an object by a word the map lacks (back, right, metal, far, side); one false raise ('a short window').
- Callouts: 6 of 6 exact targets, 5 with role 'them'; negated orders: 2 of 2 exact with role 'not'; final v3 answers NONE on all 9 non-orders (shipped v2 acts on 1: 'sniper on the roof watch out' -> HOLD_ANGLE).
- C++ locations port equals Python on the 80 fresh lines: 'coop_cli --model-dir S/cppdir --location-tests' -> 'location tests, 80 lines (60 name a place): the C++ record equals the Python record on 80/80' (existing macOS build, scratch model dir holding intent_config.json, vocab.tsv and a location_tests.jsonl generated from locations.record; the exported vocabulary equals locations.json).
- Final v3 (family gate, 0.60) is not worse than shipped v2 (family gate, 0.58) on any of the 80 fresh lines: 5 picks change, all in v3's favour; plain orders 20/20 exact for both.
- Timing and 'other' regexes on the fresh lines: on_signal 5 of 5, other 4 of 4, no false hit in 80 lines; Bot.decide queues all 5 on-signal orders with either model.
- shipped.Predictor (batched, padded) and the bot's own single-line classify agree for final v3 on all 80 lines: max probability difference 1.8e-6, same pick and gate outcome everywhere (S/botpath.log).
- Joint rate is close to the product of the separate rates (91.7% against 96.7% x 95.0% = 91.8%): intent errors and target errors fall on different lines.
- Project tree untouched: every script ran from the scratch copy under S; 'find project_synth -newer S/author_fresh.sha256' (outside .venv) lists nothing; the scratch copy of coop_bot_log.jsonl is byte-identical to the project's.

## Gap round: the matcher on lines not written to name places (`gap-matcher-on-unsteered-lines`)

### gap-matcher-on-unsteered-lines #1: On the 483 unsteered lines the primary is exact on 89.1% of the lines where the matcher returns one (97.9% on the blind v3 lines), the full record on 85.7%; 11 to 14 older orders now get a record that misdirects a planner

Reviewer: major, evaluation. Affects: HANDOFF.md section 4, matcher rows (96.7% / 94% exact target); eval_v3.log line 30; the stage-2 plan 'PlaceRecord is passed to the planner as is'

**Verifier (reproduce): partly, major; reproduced: yes; touches frozen: no**

Every number in the finding reproduces, but two of its readings are overstated.

**What holds**
- eval_v3.py:69-70 prints only a count for the older lines (eval_v3.log:30, "finds a target in 119"). Role and the unsure/other flags are scored on no test set; only unknown_modifier is counted, on the v3 lines.
- I labelled the 483 older lines myself from the spec_v3 "target" definition before running the matcher. My labels match the reviewer's on all 483 lines (target and unknown_modifier), with 108 targets expected.
- Among the 119 lines with a primary, (object, qualifier, zone) is exact on 106 (89.1%, Wilson 82.2-93.5). The whole record is right on 102 (85.7%).
- Recall is 106/108 (misses: "winder", "2F"). On eval_v3's own metric over all 483 lines it is 468/483 = 96.9%.
- Roles, flags and the 6 multi-target lines are as the reviewer reported.
- On the blind v3 lines: 141/144 exact among returned, 25 multi-target lines, and whole record 129-131/144 depending on how negated WAIT lines are treated (reviewer: 130).

**Overstated: the 89.1% vs 97.9% gap (p = 0.0035)**
- 7 of the 13 non-exact lines name only the player's place, the enemy's place or the place to leave, and the matcher marks them with the fitting role. By the matcher's own contract that record is right; eval_v3's metric counts it wrong.
- The blind v3 set contains no such line.
- Counting those 7 as right gives 113/119 = 95.0% against 141/144, Fisher p = 0.31. There is no evidence the matcher extracts worse on unsteered lines; the evidence is that the blind set and the metric do not cover this line type or the role field.

**Overstated: "11 to 14 older orders get a record that misdirects a planner"**
- 11 records are wrong in some field, plus 3 arguable. That is 10 orders and one callout (sttv2_021 is NONE).
- Six would change planner behaviour against pre-v3, about 1.2% of 483:
  - cs_060: door returned for a window vault.
  - stt_050: "red container" becomes stairs/red [unsure].
  - sttv2_021: a false contact at red stairs.
  - cs_099: "the smoke on window" raises unknown_modifier through rule 1d, which was added in rules v2.
  - r6_101: the same rule; I consider this one arguable.
  - cs_073: an invented other staircase.
- The other five (r6v2_039, csv2_007, sttv2_035 status; cs_022 from; sttv2_034 not) have the right, unqualified object as primary with a wrong role. That is a wrong field, but not a shown behavioural regression: a planner that drops a place with a role falls back to what it did before v3.

**Why it still matters**
- The same role misfire sits inside the blind 96.7%, on qualified places. Six order lines counted exact carry a role: r6v3_021 and csv3_048 (east door, status, BREACH), csv3_039, sttv3_040, r6v3_000 and csv3_027 ("smoke off X" gives from).
- Four correct "main" orders carry unsure (r6v3_035, csv3_044, sttv3_003, csv3_014).
- The status role lands on a place the bot must act on in 7-8 of its 10 firings on primaries across both sets.
- locations.h:46 says the bot is not sent to a place with a role, while locations.h:61 calls the primary the target the bot acts on, and locations.py:423 makes a role-carrying target primary when every target has a role.

Both labellers are the same model family and had read the rules, so these labels are a regression set, not a blind test.

*Recommended action.* No matcher rule or vocabulary change for this finding.

1. **HANDOFF.md section 4, matcher table, and the future "v3" section of COOP-BOT.md.** Add next to the 96.7% / 94% rows:
   "Exact target compares only (object, qualifier, zone) of the primary; role and the unsure / other flags are not scored. With role and flag counted, the record is right on about 130 of 144 blind lines with a record (90%). Six blind orders with an exact target carry a role and four carry unsure. On the 483 older lines, written without the place vocabulary, the matcher returns a record on 119. By reviewer labels (a regression set, not a blind test) the target is exact on 106/119, or 113/119 counting the 7 lines whose only named place is not a destination and is marked with a role; the whole record is right on 102/119; 11 lines get a record with a wrong target, role or flag (cs_060, stt_050, sttv2_021, cs_099, r6_101, cs_073, r6v2_039, cs_022, csv2_007, sttv2_034, sttv2_035)."
   Do not present 89.1% vs 97.9% as a gap in extraction quality.

2. **scripts/coop/eval_v3.py, matcher().** On the v3 lines, also print how many exact-target order lines (majority intent not NONE or WAIT) have a primary with a role, and how many carry unsure. For the older lines, print each returned record, not just the count. Record the new hash in frozen.txt as a metric added after the blind lines were seen.

3. **cpp/coop_intent/include/coop_intent/locations.h:46 and :61, and the docstring at locations.py:40-44.** State what a planner does when the primary carries a role. Today one comment says the bot is not sent there and the other says it is the target the bot acts on.

4. **Queue for the next rules revision.** That revision needs new blind lines under HANDOFF section 6. Items: status role on orders ("X's boarded up, blast it"), "off" as from in "smoke off X" and "hang off", rule 1d on "the smoke on window", and a lone colour before a non-map noun ("red container").

**Verifier (refute): partly, minor; reproduced: yes; touches frozen: no**

The reviewer's counts hold, but two of the three conclusions drawn from them do not.

1. The 89.1% vs 97.9% contrast (p = 0.004) does not show the matcher finds places worse on unsteered lines. Seven of the 13 non-exact lines are orders whose only named place is the player's, the enemy's or the one to leave. The matcher returns that place with a role, which is what locations.py:43-44 documents; the (object, qualifier, zone) metric ignores role and scores it wrong. Counting those right gives 113/119 = 95.0% (Wilson 89-98) against 141-142/144 blind, p = 0.31 / 0.15. What the old lines do show is a coverage hole: the blind set has no such order. Its truth target is empty on only 6 lines, all chatter.

2. The role and flag deficit is not specific to unsteered lines. On the blind lines the full record is right on 130/144 (90.3%), or 134/150 (89.3%) over all lines, against 85.7% on the old ones (p = 0.34). Six blind orders carry a role on the place to act on, all with a named place (e.g. "East door's still barricaded, slap a charge on it" gives door/east [status]; "Smoke off yellow" gives [from]). Five more have a right target flagged unsure. So the 96.7% in HANDOFF section 4 is true as an exact-target figure but is not the rate at which a planner gets a usable record.

3. The role contract contradicts itself. The comments say the bot is not sent to a place with a role, while primary is "the target the bot acts on" and falls back to a role-bearing target. The developer regression set accepts role-bearing primaries as the target (e.g. "stack up on the main door" gives [them]). On the old lines, role-bearing sole primaries on orders split 7 "not a destination" against 5 clear + 2 arguable "act here", so neither reading is right for all.

4. "11 to 14 older orders are misdirected" is overstated. Those records are wrong by their own documented semantics, but 9 of the 11 clear ones are bare door / window / stairs with no qualifier or zone, so there is no named place to be sent to; a planner resolves them by marker or nearest as before v3. The two with a name (stt_050, sttv2_021, both stairs/red) carry unsure, documented as "confirm", and sttv2_021 is NONE. The one unflagged wrong object is cs_060. Three more (stt_050, r6_101, cs_099) cost a needless confirmation or blocked fallback; cs_073 is arguable. The planner does not exist, so the practical effect is not measurable.

5. The old-line labels are one reviewer's, written after reading the rules, and 98 of the 108 expected targets are bare objects. The set tests whether the matcher stays out of the way, not the named places v3 added. No HANDOFF number is false; nothing in HANDOFF, COOP-BOT.md or the C++ README says role and flag are unscored.

*Recommended action.* No rule, vocabulary, spec, seed or label change.

1. **HANDOFF.md section 4, under the matcher table** (and the future v3 section of COOP-BOT.md), add: "Exact target compares only object, qualifier and zone of the primary; role and the unsure / other flags are not scored. Counting them, the record is right on 130 of the 144 blind lines with a primary (90.3%): 6 orders carry a role on the place to act on (status x4, from x2) and 5 right targets are flagged unsure. On the 483 older lines (one reviewer's non-blind labels; 98 of 108 targets are a bare object) the primary is exact on 106 of 119 (89.1%), or 113 of 119 (95.0%) when a sole place returned with a non-destination role counts as right. The blind set contains no such order."

2. **scripts/coop/eval_v3.py, matcher():** print role and flag consistency. It is derivable from existing labels: exact target, intent not NONE or WAIT, and a role set; or unsure on an exact target. Log the edit in frozen.txt as a metric added after the blind lines were seen.

3. **Before stage 2,** settle in locations.py:43-44 and locations.h:46/61 what a role on the primary means, and write it into cpp/coop_intent/README.md. Changing the status / from rules themselves would touch frozen material and need new blind lines.

4. **In the review write-up,** replace "11 to 14 older orders now get a record that misdirects a planner" with: "11 (+3 arguable) of 483 older lines get a record that is wrong by its own documented semantics; 9 are bare objects, the 2 named ones carry unsure, and 1 (cs_060) is an unflagged wrong object." Do not present 89.1% vs 97.9% as a drop in matcher accuracy.

### gap-matcher-on-unsteered-lines #2: A role on the primary of an order is wrong about as often as right: 7 of 15 on the unsteered lines, 13 of 21 over all 633 blind lines; 'status' is wrong 8 of 8 and depends on an apostrophe

Reviewer: major, matcher. Affects: PlaceRole contract in locations.h and the locations.py docstring ('These are places the bot is NOT sent to'); what the UE planner does with a primary that has a role; the exact-target figures, which count all 13 lines as correct

**Verifier (reproduce): confirmed, major; reproduced: yes; touches frozen: no**

The finding holds; every count reproduces, with two corrections that do not change the conclusion.

**What is true.** When every place in a line carries a role, `locations.py:423` falls back to the first target as primary. The record then says two contradictory things: `locations.h:61` calls primary "the target the bot acts on", while `locations.h:46` and `locations.py:43` say a place with a role is one "the bot is NOT sent to". This happens on 44 of 633 blind lines (18 v3, 26 older), of which 21 are orders (6 v3, 15 older).

On those 21 orders the primary is the place the bot must act on in 13 by the reviewer's count:

| role | acted on / orders | lines acted on |
|---|---|---|
| status | 8 of 8 | r6v2_039, csv2_007, csv2_030, sttv2_035, r6v3_021, csv3_039, csv3_048, sttv3_040 |
| from | 3 of 7 | cs_022, r6v3_000, csv3_027 |
| not | 1 of 1 | sttv2_034 |
| mine | 1 of 4 | r6_057 |
| them | 0 of 1 | none |

- **v3 lines:** 6 of 6 have primary equal to the readers' agreed target, which `spec_v3.json` defines as "the place the BOT must act on".
- **Older lines:** 7 act-on against 8 where the role is right.
- **Status and the apostrophe:** "door's" tokenises to door + s and gets status; "doors" is the plural object word and gets no role. Both natural pairs in the data reproduce.
- **Role is never scored.** `eval_v3.py` compares only object, qualifier and zone. The developer set `locations_dev.json` also accepts role-carrying primaries as the place to act on (for example "white stairs are clear, move up", "after i open the main door flash it").

**Corrections to the reviewer.**
1. "The exact-target figures count all 13 lines as correct" is overstated. Only the 6 v3 lines are inside the 96.7% / 94% figures; the 7 older lines have no target labels and are not scored for target at all.
2. On r6_057 the role is right: the left door is the player's. The defect there is a missing target ("the right one" is not in the record). Strictly role-wrong is therefore 12 of 21, or 11 without the arguable csv2_030.

The "86 older orders that name the place to act on" is the reviewer's own labelling. My count is 99 older orders with a matcher target, 84 of them role-free, about 88 by my reading, so the share is still about 8%.

**Consequence for the headline.** No number in HANDOFF section 4 is numerically wrong. But "exact target" ignores role. If the planner follows the documented contract and does not send the bot to a role-carrying primary on an order, the share of v3 lines where the bot ends up with the readers' place falls:

| slice | exact as reported | under the documented contract |
|---|---|---|
| all 150 lines | 96.7% (145) | 92.7% (139) |
| held-out stt | 94.0% (47/50) | 92.0% (46/50) |
| the 123 orders | 98.4% (121) | 93.5% (115) |

Status is still useful for choosing the primary when a second place exists: on 4 v3 other_ref lines (r6v3_007, r6v3_041, csv3_007, sttv3_005) it correctly demotes the first place. So the defect is the "not sent to" meaning on a sole target, not the status rule's existence.

**Wider than status.** Removing apostrophes changes the record on 14 of 169 apostrophe-bearing blind lines. On 3 v3 lines the primary becomes a wrong place (r6v3_007, csv3_033, csv3_040), because "theyre" and "awps" are not in `role_them` and "windows" / "mains" lose status.

No shipped code consumes the role today: `coop_bot.py:228` only prints it and `bot_brain.cpp:176` passes the record through. The harm lands when the UE planner is built on the header's contract.

*Recommended action.* No rule change; three text and reporting changes.

**1. Contract text.**
- `/Users/t.losiev/Documents/models_training/project_synth/cpp/coop_intent/include/coop_intent/locations.h:46`: replace "whose place: the bot is not sent to a place with a role" with wording that the role is a hint used to choose the primary among several places. When the primary itself carries a role (every place in the line has one), the role is advisory. Status in particular describes the place and is not a ban.
- `locations.h:61`: say that primary is the matcher's best candidate and may carry a role.
- `/Users/t.losiev/Documents/models_training/project_synth/scripts/coop/locations.py:43-44`: the same change in the docstring.
- Record the comment-only hash change in `frozen.txt`, with a check that `find()` output is identical on all lines.

**2. Write-up** (HANDOFF section 4 and the future v3 section of COOP-BOT.md). Add: "Exact target compares object, qualifier and zone only; the role field is not scored. On 44 of 633 blind lines (21 orders) every place carries a role and the primary falls back to the first one. On those orders the primary is the place to act on in 13 of 21 (6 of 6 on v3 lines, 7 of 15 on older lines; status 8 of 8). If the planner refused role-carrying primaries on orders, exact target would be 92.7% on all lines and 92.0% on stt, not 96.7% and 94.0%. Status depends on the apostrophe in the transcript (door's against doors)."

**3. Evaluation.** Have `eval_v3.py` print, for orders, how many exact lines have a role on the primary, by role. This needs no new labels.

**Limits.** Any per-role planner policy picked from these 21 lines (for example "ignore status, obey mine / them") is tuned on seen lines and must be marked as after tuning. Any change to the status, from or look-back rules, or to the word lists, changes rules after the blind lines were seen and needs new blind lines. Those new lines should include orders whose only named place is the player's, the enemy's or the one to leave, and apostrophe-free transcripts.

**Verifier (refute): confirmed, minor; reproduced: yes; touches frozen: no**

The finding's facts hold; its reach is narrower than stated. No reported number is wrong and no matcher rule misbehaves against its own design. The defect is one sentence of contract plus an output field that was never scored.

**What stands**
- On orders (intent not NONE / WAIT) whose primary carries a role, the place is the one to act on in 13 of 21 over all 633 lines, and in 7 of 15 on the 483 older lines.
- By role: status 8 of 8, from 3 of 7, not 1 of 1, mine 1 of 4 (r6_057, arguable), them 0 of 1.
- 'status' depends on the apostrophe: "window's already open" gives status, "the windows already open" gives no role. The same holds for "door's" / "doors" and "door is" / "doors".
- The blind v3 set has no order whose only named place is the player's, the enemy's or the one to leave. Its 6 truth-none lines are all other_sense chatter, so that case is untested there.
- The contract contradicts itself when every target has a role. `locations.h:46` and `locations.py:43` say the bot is not sent to a place with a role; `locations.h:61` says primary is the target the bot acts on; `locations.py:44` makes a role-carrying target primary.

**What does not stand**
- "The exact-target figures count all 13 lines as correct" is wrong. Only 6 of the 13 are among the 150 scored lines. Exact target compares the primary's object, qualifier and zone only (`eval_v3.py:40-42`), and on those 6 the primary equals the readers' target. The 7 older lines have no target truth and are in no figure. 88.0 / 96.7 / 94 stay as they are.
- The matcher behaviour is intended. The fallback is documented at `locations.py:44`, and the developer's regression set (frozen before any blind line) has 20 lines whose primary carries a role; 18 of them accept that place as the target. A role was built as a tie-breaker among several targets, not as a ban.
- Nothing shipped consumes the role. `coop_bot.py:227-228` prints it and `bot_brain.cpp:176` stores it; the planner is stage 2 and does not exist yet.
- "Ignoring the role sends the bot to 8 places that are not its own" is overstated. Of those 8 older orders, 2 are COVER_ME and 1 is FOLLOW_ME (no place argument), and 2 are RAPPEL "from the roof", where the roof is where the rappel starts. The 3 TAKE_COVER lines would be harmed.

**The caveat the write-up lacks**
- 96.7% and 94% hold only for a planner that acts on the primary regardless of its role. Read literally, `locations.h:46` gives 139/150 = 92.7% overall and 46/50 = 92% on held-out stt.
- HANDOFF section 4 lists the roles without 'status', and no document says how a planner treats a primary that has a role.

The "86 older orders that name the place to act on" denominator is the reviewer's own labelling and I could not reproduce it. The checkable figure is 7 of 99 older orders with a matcher target.

*Recommended action.* No rule, vocabulary, spec, seed or label change.

1. **Comment-only edit, logged in `frozen.txt` as "comment only, rules unchanged".**
   - `cpp/coop_intent/include/coop_intent/locations.h:46`: replace "the bot is not sent to a place with a role" with: "a role says what the line states about the place (not / from / mine / them / status). It lowers the target's priority when primary is chosen. If every target has a role the first is still primary, and it may be the place to act on; 'status' is information about the place, never a ban."
   - `scripts/coop/locations.py:43`: replace "These are places the bot is NOT sent to." with the same statement.
   - Afterwards `python locations.py --dev` and `coop_cli --location-tests` (8570/8570) must be unchanged.

2. **Sentence for the v3 write-up** (COOP-BOT.md section "v3", and the HANDOFF section 4 table note):
   "Exact target scores the primary's object, qualifier and zone; the role field was not scored. 96.7% (94% on stt) assumes the planner acts on the primary whatever its role. 18 of the 150 primaries carry a role, 6 of them on orders, and all 6 are the place to act on (4 status, 2 'smoke off X'). A planner that refused them would get 139/150 = 92.7% (stt 46/50). The blind set has no order whose only named place is the player's, the enemy's or the one to leave. On the 483 older lines there are 15 orders with a role on the primary: 7 are the place to act on, 8 are not. 'status' depends on the transcript keeping the apostrophe."

3. **UE plan in `cpp/coop_intent/README.md`:** add that the planner must not treat a role on the primary as a ban, and that role handling is unvalidated until roles are annotated and scored on blind lines.

Any change to status_next, to 'off' in role_from, or to the 5-token look-back is a rule change after the blind lines were seen. It needs new blind lines and would be touches_frozen=true.

### gap-matcher-on-unsteered-lines #3: A colour word before any noun outside a 19-word block list becomes an inferred staircase: both spontaneous colour adjectives in the older lines ('red container', 'red car') give stairs / red

Reviewer: minor, matcher. Affects: PlaceRecord for orders and callouts that describe an object by colour (cover behind a car, a container, a van); the 'other_sense' row of eval_v3.log does not cover this class

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: yes**

The finding holds as stated, with two small imprecisions and one wrong suggestion.

**What reproduces**
- Rule 3 of the matcher (`locations.py:335-348`, same in `locations.cpp:372-381`) turns a free colour word into an inferred staircase flagged `unsure`, unless the next word is in `lone_follow`, in the 19-word `lone_block`, or a zone phrase.
- On the 483 older lines, 7 contain a qualifier word: 3 are real map names (all author r6), 4 are another sense. The two "main" cases yield nothing; both colour cases yield stairs / red, `unsure`, `inferred`, and that target is the primary.
- `stt_050` (MOVE_TO, readers' reference "this"): the planner now gets a primary red staircase competing with the pointed-at spot.
- `sttv2_021` (NONE callout): the contact is placed at red stairs with role `them`.
- These are the only `unsure` or inferred targets on the older lines, so on unsteered lines the flag is wrong 2 of 2 times. On the blind v3 lines it is right 6 of 8, on the dev set 3 of 4.
- No blind v3 line tests the class: no colour word there is followed by a non-vocabulary noun, except "the red push" (`csv3_014`), which really is the stairs.

**Corrections to the finding**
- `r6v3_039` is not only a "roof" idiom; its mismatch comes from "west coast", a compass word. Still no colour case among the six.
- The behaviour is deliberate at code level, not an oversight. The comment at `locations.py:345` names "the white van" as an `unsure` example, the docstring (lines 31-36) describes it, and `locations.h:54` says "Unsure: confirm".
- It is not carried into any write-up. HANDOFF, COOP-BOT.md, DEBERTA-BOT.md and the C++ README never mention `unsure`, nor that `locations.py --dev` exits 1 with 5 unaccepted lines, including "throw it at the white van" (accept None only).
- The suggested fix is not free. Dropping the target for a lone colour before an unknown word loses `csv3_014` (blind exact 145 -> 144 of 150) and two dev lines the developer accepts ("hold blue tight", "go red quietly").

**Scope**
- No section 4 number changes. This is a coverage gap: the matcher's false-target rate on lines not steered to name places is unmeasured, because the older lines carry no target labels and `eval_v3.log` reports only "finds a target in 119".
- Observed rate is 2 of 483 lines (0.4%). The older lines were written before colour-named stairs existed, so the live rate is unknown.

*Recommended action.* Do not change rule 3 or `lone_block` now. Any such edit is tuning after all 150 blind lines were seen, and the naive version costs a blind line and two dev lines.

**1. Write-up (the pending "v3" section of COOP-BOT.md and the HANDOFF section 4 matcher table)** — add:
"The matcher's false-target rate on lines not written to name places is not measured. The blind `other_sense` kind has 6 lines (4/6 exact) and none describes an object by colour. On the 483 older lines, both spontaneous colour adjectives ('the red container', 'the red car') produce an inferred staircase flagged `unsure`, as primary target or as enemy contact. `python locations.py --dev` reports 5 unaccepted lines, including 'throw it at the white van'."

**2. Planner contract (`cpp/coop_intent/README.md` "Porting to UE5", and `locations.h:54`)** — state that an `unsure` + `inferred` target is a hypothesis, never a destination:
- when the order has a marker or pointing reference, the planner uses the marker;
- under NONE, an `unsure` contact is not placed on the map.
This needs no matcher change.

**3. Next blind set** — add a colour + object kind (cover behind a coloured car, container or van; enemy by a coloured object) alongside true lone-colour orders ("hold blue tight"). Revisit rule 3 only against those lines, and record the edit in `frozen.txt`.

Items 1 and 2 touch no frozen material. Any change to `locations.py` rule 3 or `locations.json` does.

### gap-matcher-on-unsteered-lines #4: The 233 older seed commands are clean, but the templated v3 seeds 'cover me from {place}' (3 of 3) get role 'from' on the place the bot must take

Reviewer: minor, matcher. Affects: PlaceRecord for COVER_ME / HOLD_ANGLE orders that name the bot's own position; the three COVER_ME place seeds in seed_commands_v3.json; the dev check in locations.py run_dev

**Verifier (both): confirmed, minor; reproduced: yes; touches frozen: yes**

Every number in the finding reproduces, and the problem is slightly wider than reported.

1. Seeds. On the 233 v21 seeds the matcher returns a record on 26 (roles: none 23, from 1, them 1, not 1; no flags, no multi-target lines) and misses no seed that names a place. All 150 v3-only templated seeds get a target. The three COVER_ME seeds ("cover me from the couch / the table / the east window") return the right object/qualifier/zone as primary, but with role "from".

2. Why that is wrong. The role rule is purely lexical: any of from / off / leave / leaving within 5 tokens before a place gives role "from". It cannot tell a firing position from a place to leave. The documented contract for a role is "These are places the bot is NOT sent to" (locations.py:43) and "the bot is not sent to a place with a role" (locations.h:46). The same header says primary is "the target the bot acts on" (locations.h:61). For these lines the two statements contradict each other.

3. It is not caught anywhere. The primary rule falls back to the first target when every target has a role (locations.py:44, :423), so the triple stays right. run_dev (locations.py:471-474) and eval_v3.py (:40-45) compare only object, qualifier and zone, and spec_v3 has no role field. Role correctness is therefore unmeasured, and the 88.0 / 96.7 / 94 % figures say nothing about it.

4. It also happens on the blind lines. Of the 145 exact primaries, 17 carry a role. Six of those are orders whose readers' target is that very place:
   - "Smoke off yellow..." and "smoke off east window..." give role from (SMOKE);
   - "East door's still barricaded, slap a charge on it" and "east door's boarded, put a charge on it" give status (BREACH);
   - "basement is all you, go in hard" gives status (ENTRY);
   - "west is yours bot" gives status (HOLD_ANGLE, held-out author stt).
   A planner that honours "role = do not send" would mis-serve 6 of 150 lines (4%) that are counted as exact hits.

5. What limits the severity. No headline number changes. No consumer of the role exists yet: coop_bot.py and BotBrain only pass the record through, and the UE planner is stage 2. The primary index is correct in every case. The seeds are classifier training data, so the matcher's output on them affects nothing in training.

6. Not a tuning leak. The role-from rule, the dev set and the "cover me from {}" template were all frozen together at 2026-10-03T20:55:13, before the blind lines existed. No document (HANDOFF sections 4 and 7, COOP-BOT.md, DEBERTA-BOT.md, cpp README) says what a planner should do with a primary that carries a role.

*Recommended action.* Do not change locations.py rules, locations.json or locations_dev.json now. That would be a post-blind rule edit and would invalidate the stt held-out 94% until new blind lines are written.

1. Add this to the v3 write-up (the COOP-BOT.md "v3" section still to be written, HANDOFF.md section 4 or 7, and the stage-2 plan in cpp/coop_intent/README.md next to the PlaceRecord line):
"Exact target compares object, qualifier and zone only; roles are not scored by eval_v3.py or by locations.py --dev, and the spec has no role field. A primary can carry a role (when every target has one, the first is primary). On the 150 blind lines 17 of the 145 exact primaries carry a role, and 6 of them are orders whose target is that very place ('smoke off yellow' -> from; 'east door's boarded, put a charge on it' -> status). The seeds 'cover me from {place}' get role from on the position the bot must take. The planner must therefore act on PlaceRecord.primary even when it carries a role, and must read role 'from' by intent: under COVER_ME / HOLD_ANGLE it is the position to take, under MOVE_TO / RAPPEL / FALL_BACK the place to leave. 'The bot is not sent to a place with a role' holds only for non-primary targets."

2. Correct the two comments that state the unconditional contract, locations.py:43 and cpp/coop_intent/include/coop_intent/locations.h:46. Both files are hashed, so record the edit in frozen.txt as comment-only.

3. Defer the behavioural fix to the next blind round: either no role or a distinct role for "from <place>" after cover / watch / hold / shoot verbs and for "smoke off <place>"; make run_dev compare the role; add a role field to the spec so readers annotate it.

seed_commands_v3.json needs no change. The seeds are correct classifier training data.

### gap-matcher-on-unsteered-lines #5: Spontaneous place mentions are mostly outside the vocabulary: 139 of the 245 older lines that name a place; a map qualifier appears in 3 of 483; the objects of BREACH and TAKE_COVER are almost never expressible

Reviewer: note, data. Affects: How far the 96.7% / 94% figures carry to play without the place list in hand; the scope sentence for the v3 write-up; HANDOFF section 4 'a new callout is a line in this file'

**Verifier (both): confirmed, note; reproduced: yes; touches frozen: no**

The finding holds as a scope note, not a defect. Three of its counts are off by one or two, and its "spontaneous speech" framing needs one caveat.

**What the two line sets look like**

| | 150 blind v3 lines (authors had the place list) | 483 older lines (authors had no list) |
|---|---|---|
| target with a qualifier | 72 (truth) | 3 real, all author r6 (r6_040, r6v2_027, r6v2_028) |
| target with a zone | 48 (truth) | 9 (matcher) |
| lines with several matcher targets | 25 | 6 |
| lines with an out-of-vocabulary place noun | 3 | about 141 to 157 |

- **Matcher output on the older lines:** it returns a primary on 119 of 483. Of these, 105 are a bare door / window / stairs / sofa, 9 are a floor or roof, and 5 carry a qualifier.
- **False qualifier readings:** 2 of those 5 are wrong: stt_050 "red container" and sttv2_021 "red car" both give stairs/red flagged "unsure".
- **Out-of-vocabulary lines:** the reviewer's 139 comes exactly from their own labels. They missed csv2_028 "blow that hatch open" and r6_095 "nade the room", which makes 141. Counting generic words (default, back, sill, outside) as well gives 157.
- **Top out-of-vocabulary nouns:** hatch 21 (not 20), room and wall about 15 each, site 7, car 6 to 7, kitchen 4, long 4, gate 4.

**By intent**

- **BREACH (27):** 23 lines name only hatch 12 / wall 7 / barricade 2 / floor 2 and get no target (the reviewer said 22, with hatch 11). 4 name a door.
- **TAKE_COVER (30):** 15 name a cover object (car 5, truck 2, pillar 2, van, counter, bar, bed, boxes, wall), none in the vocabulary. The reviewer's 17 appears to include r6v2_012 "long" and r6v2_029 "soft wall", which are the danger, not the cover. The matcher's only outputs on TAKE_COVER lines are 3 non-destination places (from / them).
- **OPEN (30):** exact as reported: 19 in (door 14, window 5), 10 out, 1 none. 8 of the 14 doors are flagged unknown_modifier (garage, double, bathroom, closet, van door).
- **MOVE_TO (15):** exact as reported: 3 stairs, 7 out, 5 ping or mark.
- **Furniture:** once (stt_116 "couch"). Qualifier words appear in 7 lines, as reported.

**Why it is not a defect**

- The vocabulary being the owner's list is stated in the `_note` of `locations.json`, the docstring of `make_spec_v3.py` and the map note in `blind/spec_v3.json`.
- The spec's target definition says the target is null for "a marker, 'here', 'there', 'that wall'".
- `cpp/coop_intent/README.md` lines 153-154 say TAKE_COVER and OPEN carry no target and the planner picks by marker or nearest.
- The same spec does name hatch, wall, gate and shutter as objects of BREACH and OPEN, while `locations.json` has only door, window, stairs, chair, sofa, table. That part of the finding is correct.

**What is missing**

HANDOFF section 4 has no scope sentence, and neither COOP-BOT.md nor DEBERTA-BOT.md has a v3 section yet.

**Caveat on the framing**

The older lines are not a sample of play on the owner's maps. Their authors were never told the names, so "3 of 483 use a qualifier" is true by construction. It does not estimate how often players who know the callouts will use them. What it does show is that the 96.7% / 94% figures say nothing about lines written without the list.

*Recommended action.* Documentation only; do not change `locations.json`, `locations.py` or the spec.

1. **COOP-BOT.md, the "v3" section still to be written (HANDOFF section 5, step 5), next to the matcher table or in a "What this does not show" bullet.** Add:

   "The matcher figures (88.0% rules v1; 96.7% all / 94% held-out author stt, rules v2) are measured on lines whose authors were given the map's place list (blind/spec_v3.json): 72 of the 150 targets carry a qualifier and 48 a floor, and 3 lines name a place outside the list. The vocabulary is the owner's list only (doors and windows by compass side, Main door, stairs by colour, chairs / sofa / table, floors). Hatches, walls, gates, shutters, rooms and cover objects (car, pillar, counter) are not in it; for those the matcher returns no target and the planner uses the marker or the nearest one, as in v2. On the 483 older lines, written without the list, the matcher returns a place on 119: a bare door / window / stairs on 105, a floor or the roof on 9, a real map qualifier on 3 (all author r6), and a false 'red' reading flagged unsure on 2 ('red container', 'red car'). 23 of the 27 BREACH lines and all 15 TAKE_COVER lines that name their cover get no target. These lines were written by authors who did not know the names, so this is not an estimate of how often players who know the callouts use them."

2. **HANDOFF.md section 4, one line under the 150-line results table.** Add:

   "Авторы слепых строк v3 видели список мест (spec_v3.json). Словарь — только список владельца: люки, стены, ворота и укрытия в него не входят и остаются за маркером. На 483 старых строках сопоставитель отдаёт место в 119, из них с квалификатором 5 (3 настоящих, 2 ложных «red» с пометкой unsure)."

3. **If the owner later wants hatch / wall / gate / cover objects as targets.** That is a vocabulary and spec change after the blind lines were seen. It must be recorded in `scripts/coop/frozen.txt`, the matcher numbers marked "after tuning", and new blind lines written, because the current truth labels cannot express those objects. It is not part of this fix.

### gap-matcher-on-unsteered-lines: checked and found right

- Assignment hints confirmed: stt_050 gives stairs / red flag unsure; csv2_007 and sttv2_035 give door role status; r6_057 gives one target door role mine; of the 119 primaries 26 carry a role and 22 a flag (16 unknown_modifier, 4 other, 2 unsure).
- eval_v3.log line 30 reproduced: locations.record returns a primary on 119 of the 483 older lines (scratch copy, locations.py and locations.json shasum-identical to the project files).
- On eval_v3's own metric (exact object / qualifier / zone of the primary, no role, no flag) the 483 older lines score 468/483 = 96.9% against labels written before the matcher was run; the blind figure is 96.7%.
- Recall on unsteered lines: 106 of 108 expected targets returned exactly as primary (98.1%); the two misses are 'winder' (STT for window) and '2F'.
- The 233 v21 seed commands: 26 records, all correct in target, role and flag; 25 of 25 expected targets found; no canonical older seed has a wrong record.
- Zones on unsteered lines are right in every case: roof x4 (r6_000, r6_005, cs_038, stt_062), floor_2 (stt_084), up (stt_061, sttv2_031).
- 'main' in other senses on the older lines yields no target: r6_050 'main wall' and cs_067 'A main' both return nothing.
- Choice of primary on older lines with several real targets: 2 lines (stt_009, stt_021), both right; the other 4 multi-target lines are the synthetic 'other' twin.
- Removing , . ; : ! ? from the 100 punctuated blind v3 lines (authors r6 and cs) changes no primary in target, role or flag (0 of 100); exact stays 48/50 and 50/50.
- All 483 older lines are in models/coop-deberta-v3-ens3-v2/cpp/location_tests.jsonl with the same records as Python (spot-checked 5 lines), so the C++ engine returns the records analysed here.
- The project tree was not modified: no file outside .venv and models is newer than my label file.
