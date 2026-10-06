# W23 Precision-First Ensemble Experiments

Development experiment only. Fit data: W11 train. Comparison data: W11 validation.
W11 test, frozen adversarial, owner golden, and W20 were not used for selection.

## Model comparison

| Model | Semantic accuracy | Macro F1 | BLOCK precision | BLOCK recall | STRIKE precision | STRIKE recall | MUTE precision | MUTE recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| word | 91.43% | 82.81% | 93.75% | 92.18% | 89.61% | 97.18% | 93.33% | 93.33% |
| char | 87.53% | 79.32% | 93.60% | 89.94% | 86.08% | 95.77% | 77.78% | 93.33% |
| combined | 93.25% | 83.22% | 94.32% | 92.74% | 89.61% | 97.18% | 100.00% | 93.33% |
| bert | 88.31% | 77.64% | 91.94% | 95.53% | 95.45% | 88.73% | 100.00% | 73.33% |
| meta | 94.81% | 85.15% | 95.35% | 91.62% | 97.22% | 98.59% | 93.75% | 100.00% |

## Actual paired Word TF-IDF + BERT behavior

| Rule | BLOCK precision | BLOCK recall | BLOCK F1 |
| --- | ---: | ---: | ---: |
| Word+BERT intersection | 96.36% | 88.83% | 92.44% |
| Word+BERT union | 89.85% | 98.88% | 94.15% |

- BLOCK prediction disagreements: 32.
- False positives: word 11, BERT 15, shared 6, union 20.
- False negatives: word 14, BERT 8, shared 2, union 20.

## Selected development operating points

- Screening/review: `union-prob@0.400`.
- BLOCK: `meta@0.550`.
- STRIKE: `meta-strike@0.600+block-gate`.
- Automatic punishment: disabled; calculations are hypothetical only.
- Hypothetical auto STRIKE: `meta-strike@0.600+block-gate`, precision 100.00%, recall 95.77%, recall sacrifice 0.00%; disabled.
- Hypothetical auto MUTE: `combined-argmax`, precision 100.00%, recall 93.33%, recall sacrifice 0.00%; disabled.
- Replace current W12 candidate: `False` (BLOCK precision delta 3.85%, validation recall ratio 98.79%).
- Post-selection evasion gate: `False` (recall ratio 17.00%, floor 97.00%).

## Train-derived evasion probes

Train-derived deterministic probe sample: 512 examples.

| Model/rule | Original BLOCK recall | Worst transformed BLOCK recall |
| --- | ---: | ---: |
| word | 96.95% | 94.27% |
| char | 95.80% | 93.13% |
| combined | 98.47% | 95.42% |
| bert | 97.71% | 93.89% |
| meta | 97.71% | 17.18% |
| selected meta@0.550 | 96.56% | 16.03% |

- Post-selection robustness gate passed: `False`.
- Selected/W12 worst-transformed recall ratio: 17.00% (floor 97.00%).

## Selection contract

- Character and combined TF-IDF grids are selected on W11 validation only.
- Meta-classifier training uses 3-fold W11-train OOF predictions only.
- BLOCK requires the predeclared recall/slice-FPR guard when an eligible rule exists.
- Train-derived evasion probes are not selection data; they act only as a post-selection deployment gate against severe robustness regressions.
- STRIKE is BLOCK-gated and selected with a stricter precision-first objective.
- No production service, punishment behavior, or W20 acceptance evidence is changed.
