# decider-2b against DeBERTa v61: split seed 0, fold 0

2186 held-out lines: owner's lines 96, typed 368, unseen voices 246, Russian voices 246, all heard 1722

## owner's lines (96 lines, 95 orders)

| reader | accuracy | macro P | macro R | macro F1 | acting P @0.66 | acting R @0.66 | wrong acts | R @ P>=97% | R @ P>=99% |
|---|---|---|---|---|---|---|---|---|---|
| DeBERTa seed 0 | 91.7 | 96.9 | 93.9 | 94.6 | 93.5 | 91.6 | 6.2 | 84.2 | 71.6 |
| DeBERTa ensemble | 92.7 | 96.5 | 93.5 | 94.0 | 95.6 | 90.5 | 4.2 | 80.0 | 61.1 |
| decider zero-shot | 47.9 | 47.2 | 45.3 | 40.1 | 73.0 | 28.4 | 10.4 | 6.3 | 6.3 |
| decider LoRA bf16 | 91.7 | 88.6 | 89.5 | 87.5 | 92.3 | 88.4 | 7.3 | 76.8 | 47.4 |
| decider Q4_K_M | 90.6 | 86.4 | 88.8 | 85.7 | 94.4 | 88.4 | 5.2 | 73.7 | 34.7 |
| decider Q8_0 | 90.6 | 86.2 | 88.8 | 85.6 | 92.3 | 88.4 | 7.3 | 76.8 | 43.2 |
| decider bf16 | 91.7 | 88.6 | 89.5 | 87.5 | 92.3 | 88.4 | 7.3 | 76.8 | 46.3 |
| DeBERTa ensemble + decider LoRA | 93.8 | 97.4 | 94.2 | 95.0 | 96.5 | 87.4 | 3.1 | 87.4 | 52.6 |

Accuracy, decider LoRA bf16 minus DeBERTa ensemble: -1.0 points (95% bootstrap -6.2 .. +4.2)

## typed (368 lines, 340 orders)

| reader | accuracy | macro P | macro R | macro F1 | acting P @0.66 | acting R @0.66 | wrong acts | R @ P>=97% | R @ P>=99% |
|---|---|---|---|---|---|---|---|---|---|
| DeBERTa seed 0 | 93.2 | 90.4 | 94.1 | 91.5 | 93.7 | 92.4 | 5.7 | 87.6 | 65.3 |
| DeBERTa ensemble | 94.6 | 92.1 | 94.7 | 92.8 | 96.6 | 91.8 | 3.0 | 91.8 | 65.6 |
| decider zero-shot | 48.4 | 48.0 | 51.4 | 45.3 | 76.6 | 32.6 | 9.2 | 10.6 | 9.7 |
| decider LoRA bf16 | 93.8 | 90.6 | 93.3 | 91.2 | 94.6 | 93.5 | 4.9 | 92.1 | 40.6 |
| decider Q4_K_M | 94.0 | 91.6 | 93.9 | 92.0 | 94.4 | 94.1 | 5.2 | 92.4 | 77.6 |
| decider Q8_0 | 93.8 | 90.6 | 93.3 | 91.2 | 94.4 | 93.5 | 5.2 | 91.5 | 37.4 |
| decider bf16 | 93.8 | 90.6 | 93.3 | 91.2 | 94.6 | 93.5 | 4.9 | 91.2 | 37.4 |
| DeBERTa ensemble + decider LoRA | 95.4 | 93.6 | 94.6 | 93.7 | 97.8 | 93.5 | 1.9 | 95.3 | 69.1 |

Accuracy, decider LoRA bf16 minus DeBERTa ensemble: -0.8 points (95% bootstrap -3.5 .. +1.9)

## unseen voices (246 lines, 228 orders)

| reader | accuracy | macro P | macro R | macro F1 | acting P @0.66 | acting R @0.66 | wrong acts | R @ P>=97% | R @ P>=99% |
|---|---|---|---|---|---|---|---|---|---|
| DeBERTa seed 0 | 79.7 | 81.6 | 84.8 | 79.9 | 82.2 | 78.9 | 15.9 | 45.2 | 5.3 |
| DeBERTa ensemble | 83.3 | 82.5 | 87.5 | 82.8 | 94.2 | 78.9 | 4.5 | 53.9 | 27.6 |
| decider zero-shot | 36.2 | 40.5 | 42.1 | 36.1 | 68.9 | 22.4 | 9.3 | 7.0 | 7.0 |
| decider LoRA bf16 | 81.3 | 82.1 | 84.6 | 80.9 | 88.0 | 80.3 | 10.2 | 52.2 | 50.4 |
| decider Q4_K_M | 78.0 | 78.8 | 82.8 | 78.2 | 84.9 | 78.9 | 13.0 | 65.4 | 50.9 |
| decider Q8_0 | 80.9 | 80.7 | 84.5 | 80.0 | 87.5 | 79.8 | 10.6 | 53.5 | 50.4 |
| decider bf16 | 81.3 | 81.2 | 84.6 | 80.3 | 88.0 | 80.3 | 10.2 | 53.5 | 50.4 |
| DeBERTa ensemble + decider LoRA | 85.4 | 85.1 | 87.4 | 84.6 | 95.1 | 76.3 | 3.7 | 71.9 | 46.1 |

Accuracy, decider LoRA bf16 minus DeBERTa ensemble: -2.0 points (95% bootstrap -7.3 .. +2.8)

## Russian voices (246 lines, 228 orders)

| reader | accuracy | macro P | macro R | macro F1 | acting P @0.66 | acting R @0.66 | wrong acts | R @ P>=97% | R @ P>=99% |
|---|---|---|---|---|---|---|---|---|---|
| DeBERTa seed 0 | 72.4 | 72.9 | 74.1 | 69.6 | 75.7 | 71.1 | 21.1 | 17.5 | 9.6 |
| DeBERTa ensemble | 74.4 | 72.6 | 72.4 | 69.5 | 85.6 | 68.0 | 10.6 | 31.6 | 20.6 |
| decider zero-shot | 27.2 | 29.3 | 26.4 | 24.5 | 67.5 | 11.8 | 5.3 | 5.3 | 5.3 |
| decider LoRA bf16 | 69.9 | 69.5 | 70.3 | 66.5 | 80.8 | 68.4 | 15.0 | 47.8 | 9.6 |
| decider Q4_K_M | 69.5 | 66.7 | 70.1 | 65.8 | 82.2 | 66.7 | 13.4 | 4.4 | 4.4 |
| decider Q8_0 | 69.5 | 69.0 | 70.3 | 66.3 | 80.7 | 68.0 | 15.0 | 44.7 | 7.9 |
| decider bf16 | 69.5 | 69.3 | 70.3 | 66.3 | 80.8 | 68.4 | 15.0 | 47.8 | 10.1 |
| DeBERTa ensemble + decider LoRA | 72.8 | 72.3 | 73.7 | 69.9 | 91.2 | 68.0 | 6.1 | 43.0 | 35.1 |

Accuracy, decider LoRA bf16 minus DeBERTa ensemble: -4.5 points (95% bootstrap -8.9 .. +0.0)

## all heard (1722 lines, 1596 orders)

| reader | accuracy | macro P | macro R | macro F1 | acting P @0.66 | acting R @0.66 | wrong acts | R @ P>=97% | R @ P>=99% |
|---|---|---|---|---|---|---|---|---|---|
| DeBERTa seed 0 | 82.7 | 81.5 | 85.3 | 81.6 | 85.3 | 82.6 | 13.2 | 55.1 | 9.5 |
| DeBERTa ensemble | 85.6 | 84.0 | 87.3 | 84.4 | 92.4 | 82.4 | 6.3 | 56.8 | 41.1 |
| decider zero-shot | 39.3 | 47.4 | 40.8 | 38.7 | 75.9 | 23.7 | 7.0 | 7.3 | 7.3 |
| decider LoRA bf16 | 84.0 | 82.0 | 85.8 | 82.7 | 89.1 | 84.1 | 9.5 | 63.0 | 12.7 |
| decider Q4_K_M | 82.8 | 81.5 | 84.9 | 82.0 | 88.5 | 82.7 | 9.9 | 64.2 | 13.3 |
| decider Q8_0 | 83.8 | 81.7 | 85.7 | 82.5 | 89.2 | 83.9 | 9.4 | 62.1 | 13.3 |
| decider bf16 | 83.9 | 81.8 | 85.8 | 82.6 | 89.1 | 84.2 | 9.5 | 62.5 | 13.4 |
| DeBERTa ensemble + decider LoRA | 86.9 | 85.3 | 88.2 | 85.8 | 95.1 | 82.4 | 3.9 | 77.8 | 50.8 |

Accuracy, decider LoRA bf16 minus DeBERTa ensemble: -1.6 points (95% bootstrap -3.4 .. -0.1)
