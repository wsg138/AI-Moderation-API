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
label accuracy and macro F1 and, critically for normal Minecraft use, the lowest gameplay
BLOCK false-positive rate. Both encoders improve real-world-threat recall by about 3.6
percentage points, but at materially higher gameplay false-positive cost. No frozen test,
frozen-adversarial, or owner-golden result was used to choose the final candidate.

## W11 split consumption

- train: 3,269 — fitting only;
- validation: 385 — candidate selection, calibration measurement, and threshold rationale only;
- test: 410 — frozen held-out, opened once;
- frozen_adversarial: 436 — frozen held-out, opened once;
- owner_golden: 52 fixtures, 21 fully labeled for classifier metrics — acceptance only.

The mandatory second encoder comparison was completed after the held-outs had already been
observed. The selected candidate, preprocessing, argmax/0.5 behavior, and model parameters
did **not** change after that observation. Final selection was made from train/validation
evidence only. The already-observed held-outs must not be used for any later tuning; if the
candidate, preprocessing, thresholds, or model configuration changes, a new/versioned unseen
acceptance set is required.

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

The held-out/golden results are not a license to tune this version. Any semantic model,
preprocessing, or threshold change requires fresh/versioned unseen acceptance evidence.

## Selected runtime artifact

The production adapter uses a safe JSON representation of the frozen TF-IDF transform plus
six numeric-input ONNX LogisticRegression heads. It does **not** load pickle in production,
does not need a Hugging Face tokenizer, and performs no network download at startup.

Evidence workflow: `w12-evidence`, run `37145995076`, head
`546513f8d89de931c92ff1e6f4f195e84c519225`.

- Metadata SHA-256: `b3ac4e9869f0857fbc7cb30e52b5340f40c5ff16f2eb234ca4dbe839ae21d5be`
- TF-IDF vectorizer: 7,157 features, 219,161 bytes,
  SHA-256 `1afabd1ac09b70826c1c322f8bbe36c279eff1212ea3e5cd73c6272fd9ed1db1`
- Six ONNX heads + vectorizer total: 1,295,438 bytes
- sklearn ↔ production ONNX parity on all 385 validation examples:
  0 prediction mismatches; maximum absolute probability delta
  `1.7372870320109257e-7` at tolerance `1e-4`
- Runtime health loaded all six heads and the exact vectorizer checksum successfully.

### CPU benchmark

GitHub hosted Ubuntu 24.04, Python 3.12.14, 4 vCPU x86-64, ONNX Runtime 1.30.0:

| Metric | Result |
|---|---:|
| Cold load | 19.3 ms |
| Attributable RSS | 0.875 MB |
| p50 | 0.512 ms |
| p95 | 0.559 ms |
| p99 | 0.890 ms |
| Mean | 0.521 ms |
| Batch-1 throughput | 1,963 req/s |

This is comfortably within the 2 GB memory and bounded-latency deployment envelope. The
benchmark host has four vCPUs rather than the target host's nominal two; latency therefore
must not be treated as an exact production prediction, but the measured margin is large.

### Quantization

Dynamic QInt8 was attempted with ONNX Runtime 1.30.0. It is not supported for this exported
`ai.onnx.ml` LinearClassifier graph; the quantizer returned
`ValueError: Failed to find proper ai.onnx domain` before producing an int8 artifact.

The launch packet requires dynamic/int8 comparison where supported. W12 therefore retains
the measured FP32 bundle rather than changing the selected graph/model after held-out
observation solely to force an int8 artifact.

## Artifact storage

Review artifacts are stored in GitHub Actions for 30 days:

- baseline ONNX evidence artifact ID `11281729885`,
  ZIP SHA-256 `bc599a3c320e8cb87533066b15d6a06d3ef55a80867a6397f909b1068ba0a448`;
- BERT Mini validation artifact ID `11282161133`,
  ZIP SHA-256 `ca3866600f8d7b95de1b5088dd7eac78cb8b13b322deadf2bf4c79a0289bffba`.

No approved durable production model-binary destination has been designated. The repository
contains reproducible training/export code plus the checksum/evidence summary; production
rollout must define artifact distribution separately.

## Runtime integration

The service loads the W12 bundle only when both of these are configured:

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
10. Dynamic int8 quantization is unsupported by the selected exported graph.
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

# Selected baseline ONNX export + validation-only parity/benchmark evidence
python -m workers.w12.run_baseline_onnx_evidence
```

See `workers/w12/reports/evidence-summary.json` for compact machine-readable evidence.
