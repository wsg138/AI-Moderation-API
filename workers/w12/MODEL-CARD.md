# W12 Model Card — Enthusia AI Moderation Local Classifier

## Model identity

- **Selected candidate:** baseline-tfidf
- **Model version:** w12-baseline-tfidf-v1
- **Policy version:** v1
- **Training date:** 2026-10-03
- **Selection data:** W11 train + validation only
- **Production deployment:** not authorized / not performed

## Candidates compared

| Candidate | Architecture | Immutable source | Val Acc | Val Macro F1 | Gameplay BLOCK FP | Threat BLOCK recall | License |
|---|---|---|---:|---:|---:|---:|---|
| **baseline-tfidf** | TF-IDF (1–2 gram, 30k cap) + LogisticRegression heads | repository training code / seed 42 | **91.9%** | **0.844** | **1.8%** | 92.7% | scikit-learn BSD-3 |
| bert-tiny | 2L / 128H BERT | `prajjwal1/bert-tiny@6f75de8b60a9f8a2fdf7b69cbd86d9e64bcb3837` | 67.8% | 0.443 | 9.1% | **96.4%** | MIT |
| bert-mini | 4L / 256H BERT | `google/bert_uncased_L-4_H-256_A-4@387825ce42dbb39b87911cdf8e383ee3b25184f8` | 85.7% | 0.753 | 5.5% | **96.4%** | Apache-2.0 |

**Selection rationale:** the baseline is selected from validation-only evidence. It has the best
label accuracy and macro F1 and the lowest gameplay BLOCK false-positive rate. Both encoders
improve real-world-threat recall by about 3.6 percentage points, but at materially higher
gameplay false-positive cost. No frozen test, frozen-adversarial, or owner-golden result was
used to choose the final candidate.

## W11 split consumption

- train: 3,269 — fitting only;
- validation: 385 — candidate selection, calibration measurement, and artifact parity/quantization evidence;
- test: 410 — frozen held-out, opened once;
- frozen_adversarial: 436 — frozen held-out, opened once;
- owner_golden: 52 fixtures, 21 fully labeled for classifier metrics — acceptance only.

The mandatory second encoder comparison was completed after the held-outs had already been
observed. The selected candidate, preprocessing, argmax/0.5 behavior, and model parameters
did **not** change after that observation. Final selection was made from train/validation
evidence only. The already-observed held-outs must not be used for later tuning; a changed
candidate, preprocessing, threshold, or model configuration requires a new/versioned unseen
acceptance set.

## Selected baseline validation results

Validation n=385:

- Label accuracy: 91.9%
- Label macro F1: 0.844
- Label weighted F1: 0.921
- Runtime BLOCK precision: 94.3%
- Runtime BLOCK recall: 92.7%
- Calibration: ECE 0.168, Brier 0.078
- Threshold behavior: unchanged argmax / source-action mapping; no post-held-out retuning

### Critical validation slices

| Slice | n | BLOCK FP rate | BLOCK recall |
|---|---:|---:|---:|
| Minecraft gameplay | 55 | **1.8%** | — |
| Real-world threat | 55 | — | **92.7%** |
| `kys` / self-harm instruction | 20 | — | **95.0%** |
| Self-harm disclosure | 20 | 0.0% | — |
| Slur/hate slice | 25 | — | 92.0% |
| Sexual/minor slice | 27 | — | **100%** |

BERT Mini's validation comparison is intentionally recorded because it is the mandatory
second encoder: 85.7% label accuracy, 0.753 macro F1, 92.7% BLOCK precision/recall,
5.45% gameplay BLOCK FP, 96.36% real-world-threat BLOCK recall, ECE 0.035, Brier 0.047.

## Frozen held-out evidence

These are the original one-time results for the unchanged selected baseline.

### Test (n=410)

- Label macro F1: 0.828
- BLOCK recall: 90.0%
- Minecraft gameplay BLOCK FP: 0.0%

### Frozen adversarial (n=436)

- Label macro F1: 0.790
- BLOCK recall: 93.5%
- Minecraft gameplay BLOCK FP: 9.5%

### Owner golden (21 fully labeled fixtures)

- Label accuracy: 76.2%
- Label macro F1: 0.271
- BLOCK recall: 75.0%
- BLACKMAIL remains unsupported because the training set contains zero BLACKMAIL examples.

The held-out/golden results are not a license to tune this version.

## Selected runtime artifact

The production adapter uses a safe JSON representation of the frozen TF-IDF transform plus
six standard-op ONNX LogisticRegression heads. It does **not** load pickle in production,
does not need a Hugging Face tokenizer, and performs no network download at startup.

Final evidence workflow: `w12-evidence`, run `37157150269`, head
`b2df8afab52699a43c27192dc61cf44adb2287a9`.

- Metadata SHA-256: `f3489e5fffb54303f34ee4f9bef672b211556ee6a6a0d2f2994d3e1c6e7dd1df`
- TF-IDF vectorizer: 7,157 features, 219,161 bytes,
  SHA-256 `1afabd1ac09b70826c1c322f8bbe36c279eff1212ea3e5cd73c6272fd9ed1db1`
- Six ONNX heads + vectorizer total: 1,022,836 bytes
- sklearn ↔ selected FP32 ONNX parity on all 385 validation examples:
  **0 prediction mismatches**; maximum absolute probability delta
  `1.6771714006491578e-7` at tolerance `1e-4`
- Runtime health loaded all six heads and the exact vectorizer checksum successfully.

### CPU benchmark

GitHub-hosted Ubuntu x86-64, Python 3.12, ONNX Runtime 1.30.0:

| Metric | Selected FP32 | Dynamic QInt8 |
|---|---:|---:|
| Artifact bytes | 1,022,836 | 425,780 |
| Cold load | 8.15 ms | 7.99 ms |
| Attributable RSS | 0.469 MB | 0.379 MB |
| p50 | 0.230 ms | 0.188 ms |
| p95 | 0.248 ms | 0.204 ms |
| p99 | 0.271 ms | 0.226 ms |
| Batch-1 throughput | 4,342 req/s | 5,340 req/s |

### Quantization decision

Dynamic QInt8 is technically supported for the standard-op export and materially reduces
artifact size and latency. It is **not selected** for this model version because validation
parity changed: 4 head-level prediction outcomes changed across the 385 validation examples,
with a maximum absolute probability delta of 0.0279124. The selected FP32 artifact retains
exact predicted classes and near-numerical parity with the frozen sklearn model.

This is a representation decision only. No model was retrained and no threshold was changed.

## Artifact storage

Review artifacts are stored in GitHub Actions for 30 days:

- selected baseline/ONNX evidence artifact ID `11286343154`,
  ZIP SHA-256 `2f72512864b52ccb531b17248017489e6354de138c332e2c8718f1028ae305dc`;
- BERT Mini validation artifact ID `11286348459`,
  ZIP SHA-256 `5560f47553758314f2debf68a22709ea70a10b22a995d8ff3d6d1104f93bb78e`.

No approved durable production model-binary destination has been designated. The repository
contains reproducible training/export code plus checksum/evidence summaries; production
rollout must define artifact distribution separately.

## Runtime integration

The service loads the W12 bundle only when both are configured:

- `AI_MOD_ONNX_METADATA_PATH`
- `AI_MOD_ONNX_METADATA_SHA256`

Otherwise it remains in the existing stub/not-ready fail-open mode. Model load/checksum
failure is not-ready; inference timeout/error is caught by the existing moderation runtime
and fails open. Production inference dependencies are pinned separately from the training
stack.

## Known limitations

1. Synthetic training data only; no production chat used.
2. W11 near-duplicate detection was lexical, not embedding-based.
3. **BLACKMAIL has zero training examples** and is not learned by this classifier.
4. DOXXING and GROOMING are underrepresented.
5. Containment duration is sparse; the adapter returns `None` rather than inventing policy.
6. Structured memory is not represented as supervised model input.
7. Baseline calibration is imperfect (ECE 0.168).
8. Frozen adversarial gameplay BLOCK FP is 9.5%.
9. The original held-outs are now permanently off-limits for tuning this model version.
10. Dynamic QInt8 is rejected for this version because it changes four validation predictions.
11. Review artifact retention is temporary; production binary distribution is unresolved.
12. AI does not own bans or final punishment decisions.

## Reproduction

```bash
# Baseline fitting
python -m workers.w12.baseline

# Second encoder training (train only)
python -m workers.w12.train_encoder --candidate bert-mini --seed 42 --epochs 5 --batch-size 16 --lr 3e-5

# Second encoder validation (validation only)
python -m workers.w12.run_validation_candidate --candidate bert-mini --seed 42

# Selected baseline standard-op ONNX export + validation-only parity/benchmark/int8 comparison
python -m workers.w12.run_baseline_onnx_evidence
```

See `workers/w12/reports/evidence-summary.json` for compact machine-readable evidence.
