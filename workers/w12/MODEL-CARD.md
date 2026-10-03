# W12 Model Card — Enthusia AI Moderation Local Classifier

## Model identity

- **Provisional validation-selected candidate:** baseline-tfidf
- **Final W12 selection status:** incomplete until a second pretrained encoder finishes
- **Model version:** w12-baseline-tfidf-v1
- **Policy version:** v1
- **Training date:** 2026-10-03
- **Training hardware:** CPU-only (2 vCPU, 7GB RAM, no GPU)

## Candidates compared

| Candidate | Architecture | Val Acc | Val Macro F1 | License |
|-----------|-------------|---------|--------------|---------|
| **baseline-tfidf** | TF-IDF (1-2gram, 30k) + LogisticRegression | **91.9%** | **0.844** | BSD-3 |
| bert-tiny | prajjwal1/bert-tiny (2L/128H, 4.4M) | 67.8% | 0.443 | MIT |
| bert-mini | google/bert_uncased_L-4_H-512_A-8 (4L/512H, 11M) | incomplete | — | Apache-2.0 |

**Selection rationale:** Baseline decisively outperformed bert-tiny on validation-only
aggregate metrics and critical slices. `bert-mini` was attempted but did not finish.
Therefore the baseline is only the provisional validation-selected candidate; the W12
acceptance requirement of two completed pretrained encoders has not yet been met.

## W11 split consumption

- train: 3,269 (ONLY partition used for fitting)
- validation: 385 (ONLY partition used for tuning/calibration/selection)
- test: 410 (frozen, single run after freeze)
- frozen_adversarial: 436 (frozen, single run after freeze)
- owner_golden: 52 fixtures (21 fully-labeled for classifier; acceptance only)

**Evaluation-protocol status:** Train/validation separation was preserved, but the
test, frozen-adversarial, and owner-golden sets were opened before the mandatory
second encoder comparison finished. Those observed held-outs must not be used for
tuning. If candidate, preprocessing, thresholds, or configuration changes, a new
versioned unseen acceptance set is required for an unbiased final acceptance claim.

## Validation results (n=385, tuning partition)

- Label accuracy: 91.9%, macro F1: 0.844, weighted F1: 0.918
- Block precision: 94.3%, Block recall: 92.7%
- Calibration: ECE=0.168, Brier=0.078 (uncalibrated; fail-open runtime handles uncertainty)

### Critical policy slices (validation)

| Slice | n | Block FP rate | Block recall |
|-------|---|---------------|--------------|
| minecraft_gameplay | 55 | **1.8%** | — |
| real_world_threat | 55 | — | **92.7%** |
| kys_self_harm_instruction | 20 | — | **95.0%** |
| self_harm_disclosure | 20 | 0.0% | — |
| slur | 25 | — | 92.0% |
| sexual_minor | 27 | — | **100%** |

## Final held-out evaluation (single run after freeze)

### Test (n=410, frozen)
- Label macro F1: 0.828
- Block recall: 90.0%, Block precision: (see report)
- Gameplay FP rate: **0.0%**

### Frozen adversarial (n=436)
- Label macro F1: 0.790
- Block recall: 93.5%
- Gameplay FP rate: 9.5% (adversarial examples are designed to be hard)

### Owner golden (n=21 fully-labeled)
- Label accuracy: 76.2%, macro F1: 0.271
- Block recall: 75.0%
- Note: Small sample; macro F1 volatile. BLACKMAIL failed (zero training examples).
  31 partial/policy fixtures excluded from classifier metrics.

## ONNX export

- Selected baseline format: six per-head string-input ONNX models plus one checksum manifest.
- Export now forces the ONNX `StringNormalizer` locale to portable `C` instead of relying
  on the failing backend-default locale seen on the training host.
- The runtime adapter consumes this exact six-head manifest format; it no longer assumes a
  BERT tokenizer or a single encoder artifact.
- **Acceptance evidence still outstanding:** regenerate the selected bundle, record its real
  SHA-256/size manifest, validate sklearn↔ONNX parity, compare quantized/non-quantized
  artifacts, and benchmark actual ONNX Runtime inference.
- There is currently no approved durable model-binary publication destination; do not invent one.

## CPU benchmark status

The existing `benchmark-baseline.json` measurements were taken through the sklearn model,
not the selected ONNX bundle. They are useful diagnostics only and are **not** W12 ONNX
acceptance evidence. Actual selected-bundle ONNX load/RSS/p50/p95/p99/throughput and
quantized-vs-nonquantized measurements remain required before acceptance.

## Known limitations

1. Synthetic training data only; no production chat used.
2. Near-duplicate detection in W11 was lexical, not semantic.
3. **BLACKMAIL has zero training examples** — will not be detected.
4. DOXXING (10) and GROOMING (20) severely underrepresented.
5. Containment duration sparse; adapter returns None, preserves review.
6. Structured memory not in training; adapter is conservative.
7. Calibration poor (ECE 0.168) — model is overconfident. Fail-open runtime mitigates.
8. Adversarial gameplay FP 9.5% — adversarial examples are hard by design.
9. The mandatory second pretrained encoder comparison is incomplete.
10. Held-out/golden results have already been observed; they must not influence retuning.
11. Actual selected-bundle ONNX parity/quantization/benchmark evidence is still pending.
12. AI does not own bans or final punishments.

## Reproduction

```bash
# Train baseline
python -m workers.w12.baseline

# Evaluate on validation
python -c "from workers.w12.dataset import load_partition; ..."

# Freeze and run held-out (ONCE)
python -m workers.w12.freeze_eval --candidate baseline --seed 42 \
  --freeze-record workers/w12/reports/freeze-record.json

# Export to ONNX
python -m workers.w12.export_baseline_onnx
```

## Files

- Training code: `workers/w12/`
- Reports: `workers/w12/reports/`
- Runtime adapter: `service/moderation_api/onnx_classifier.py`
- Tests: `tests/test_w12.py`
