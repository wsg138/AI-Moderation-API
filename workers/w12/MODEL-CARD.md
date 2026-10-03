# W12 Model Card — Enthusia AI Moderation Local Classifier

## Model identity

- **Selected candidate:** baseline-tfidf
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

**Selection rationale:** Baseline decisively outperformed bert-tiny on both aggregate
metrics (24pt accuracy gap) and critical slices (5x better gameplay FP rate).
bert-mini training was attempted but incomplete due to compute/time constraints
(killed after 22min on 2-CPU host). Selection based on complete product risk
profile, not aggregate F1 alone.

## W11 split consumption

- train: 3,269 (ONLY partition used for fitting)
- validation: 385 (ONLY partition used for tuning/calibration/selection)
- test: 410 (frozen, single run after freeze)
- frozen_adversarial: 436 (frozen, single run after freeze)
- owner_golden: 52 fixtures (21 fully-labeled for classifier; acceptance only)

**Contamination statement:** Held-out partitions were NEVER used for training,
tuning, calibration, threshold selection, or candidate choice. Freeze record
created BEFORE running held-out evaluation.

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

- 6 per-head ONNX models (label, action, review_priority, strike, containment, support_flow)
- Total size: 2.3 MB
- SHA-256: see workers/w12/artifacts/onnx/baseline-tfidf-metadata.json
- **Limitation:** ONNX runtime requires en_US.UTF-8 locale (not present on training host).
  Production host must have locale installed, or use sklearn runtime.

## CPU benchmarks (production target)

Host: 2 vCPU (training host; production target is similar)

| Metric | Value |
|--------|-------|
| Cold load time | 6 ms |
| Steady-state RSS (attributable) | 3.6 MB |
| p50 latency | 1.24 ms |
| p95 latency | 1.82 ms |
| p99 latency | 3.59 ms |
| Throughput (batch-1) | 753 req/sec |
| Model size | 1.9 MB (pickle) / 2.3 MB (ONNX) |

Fits comfortably in 2GB budget with massive headroom.

## Known limitations

1. Synthetic training data only; no production chat used.
2. Near-duplicate detection in W11 was lexical, not semantic.
3. **BLACKMAIL has zero training examples** — will not be detected.
4. DOXXING (10) and GROOMING (20) severely underrepresented.
5. Containment duration sparse; adapter returns None, preserves review.
6. Structured memory not in training; adapter is conservative.
7. Calibration poor (ECE 0.168) — model is overconfident. Fail-open runtime mitigates.
8. Adversarial gameplay FP 9.5% — adversarial examples are hard by design.
9. AI does not own bans or final punishments.

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
