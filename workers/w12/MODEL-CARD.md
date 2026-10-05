# W12 Model Card — Enthusia AI Moderation Local Classifier

## Status

- **Selected candidate:** `baseline-tfidf`
- **Model version:** `w12-baseline-tfidf-v2`
- **Serialization:** `w12-v2`
- **Policy version:** v1
- **Model/code freeze used for current evidence:** `3aac90ca8d0d57ca2174a852f961c6b753e7205d`
- **Validation/ONNX evidence workflow:** `w12-evidence` run `37225843627`
- **Production deployment:** not authorized / not performed
- **Final acceptance:** **PENDING** — requires independent fresh W20 acceptance set from issue #43 / PR #44.

This document supersedes the earlier v1 model-card claims. The original W11
test/frozen-adversarial/owner-golden results were observed before a later material
preprocessing correction and therefore cannot accept v2.

## Why v2 was required

Independent audit found two material preprocessing defects after the original held-outs had
already been opened:

1. training and runtime serialized time/speakers differently; and
2. 30 train-only self-harm examples included post-target future messages unavailable at live inference time.

The corrected v2 contract:
- canonicalizes speakers by first appearance;
- makes the target/current message `0 ms`;
- represents prior messages with target-relative negative offsets;
- excludes post-target future messages;
- keeps IDs, domains, reason codes, difficulty, family IDs, and other editorial metadata out of model input;
- version-checks runtime artifacts against `w12-v2`.

Because preprocessing changed after old held-out evidence was seen, those results are
**superseded development evidence**, not v2 acceptance evidence.

## W11 data contract

- train: 3,269 — fitting only
- validation: 385 — candidate selection/calibration/evidence only
- original test: 410 — previously observed, now superseded for v2 acceptance
- original frozen adversarial: 436 — previously observed, now superseded for v2 acceptance
- owner golden: separate — previously observed, now superseded for v2 acceptance

No W11 partition was reshuffled.

## Validation-only candidate comparison

All v2 candidate selection used W11 train + validation only.

| Candidate | Val accuracy | Macro F1 | BLOCK precision | BLOCK recall | Minecraft gameplay BLOCK FP | Real-world-threat BLOCK recall |
|---|---:|---:|---:|---:|---:|---:|
| **baseline-tfidf** | **0.9143** | **0.8281** | **0.9375** | 0.9218 | **0.0357** | 0.9091 |
| bert-mini | 0.8831 | 0.7764 | 0.9194 | **0.9553** | 0.0595 | **0.9636** |
| bert-tiny | 0.6831 | 0.4624 | 0.8093 | 0.8771 | 0.0833 | **0.9636** |

Encoder provenance:
- `bert-mini`: `google/bert_uncased_L-4_H-256_A-4@387825ce42dbb39b87911cdf8e383ee3b25184f8` — Apache-2.0
- `bert-tiny`: `prajjwal1/bert-tiny@6f75de8b60a9f8a2fdf7b69cbd86d9e64bcb3837` — MIT

### Selection rationale

The baseline remains selected under criteria recorded before the final encoder result:
- strongest semantic accuracy/macro-F1;
- lower normal-player false-positive exposure than BERT Mini/Tiny;
- 7/7 split-message threat BLOCK recall;
- 100% sexual/minor BLOCK recall on validation;
- 100% real-world explosive-request BLOCK recall;
- 0% BLOCK false positives on generic Minecraft violence and Minecraft TNT validation slices.

BERT Mini has stronger aggregate BLOCK recall and calibration, but materially worsens several
normal-user slices: gameplay, generic Minecraft violence, Discord general, Minecraft public,
and allowed examples carrying explicit real-world cues. It also misses one of seven
split-message threat cases.

No old held-out result was used to make this v2 selection. No threshold was retuned.

## Selected v2 validation details

Baseline:
- runtime visibility accuracy: 0.9351
- BLOCK precision: 0.9375
- BLOCK recall: 0.9218
- BLOCK F1: 0.9296
- three-way dataset action accuracy: 0.9299
- three-way dataset action macro F1: 0.9171
- review-priority accuracy: 0.9558
- strike accuracy: 0.9740
- containment accuracy: 0.9948
- support-flow accuracy: 1.0000
- calibration ECE: 0.1629
- calibration Brier: 0.0791

Selected critical validation slices:
- Minecraft gameplay: n=87, BLOCK FP 3.57%
- benign hard negatives: n=55, BLOCK FP 3.64%
- generic Minecraft violence: n=48, BLOCK FP 0%
- allowed explicit-real-world-cue examples: BLOCK FP 0%
- real-world threat: n=55, BLOCK recall 90.91%
- split-message threat: n=7, BLOCK recall 100%
- self-harm instruction: n=20, BLOCK recall 95%
- first-person self-harm disclosure: n=5, BLOCK FP 0%
- actual slur: n=21, BLOCK recall 90.48%
- slur reference-only: n=8, BLOCK FP 0%
- sexual/minor: n=7, BLOCK recall 100%
- Minecraft TNT: n=11, BLOCK FP 0%
- real-world explosive request: n=22, BLOCK recall 100%
- obfuscation/evasion: n=7, BLOCK recall 85.71%

Known validation concerns that final W20 acceptance must probe independently:
- private-flirting BLOCK FP: 18.18% (n=11)
- age-self-report-only BLOCK FP: 25% (n=4)
- Discord-general BLOCK FP: 9.52% on allowed examples in that slice
- calibration is materially worse than BERT Mini

These are validation observations only; do not design W20 from individual W12 failures.

## Runtime artifact

Production runtime uses a safe JSON TF-IDF vectorizer plus six standard-op ONNX logistic heads.
It does not load pickle in production and performs no network download at startup.

Current v2 selected FP32 bundle:
- metadata SHA-256: `aca804fd0bdedd7414be7dbeaecb777c68e2ebfdf299660a6920fce240e111c2`
- vectorizer: 7,073 features, 216,544 bytes
- total runtime artifact bytes: 1,010,811
- validation parity: 0 predicted-class mismatches across all six heads / 385 examples
- maximum absolute probability delta: `1.8235273024913567e-7`
- serialization version enforced as `w12-v2`

Artifact review ZIP:
- Actions artifact ID: `11311807878`
- ZIP SHA-256: `0fc9e21da1486d496800fd11b6c084b5d449e269204de56be0cac29535a4d87e`
- expires: 2026-11-03

## CPU benchmark

GitHub-hosted Ubuntu x86-64, Python 3.12, ONNX Runtime, 4 reported CPUs.

Selected FP32:
- cold load: 13.85 ms
- attributable RSS: 1.04 MB
- single message p50/p95/p99: 0.553 / 0.647 / 1.006 ms
- representative multi-message p50/p95/p99: 0.582 / 0.796 / 2.563 ms
- multi-message batch-1 throughput: ~1,798 req/s

Dynamic QInt8:
- artifact bytes: 420,811
- metadata SHA-256: `09e1e9c1886a85d88261c38113fc3c4785bafc09bedcedc04507973abda87e81`
- 3 head-level validation prediction mismatches
- maximum probability delta: 0.02605
- multi-message p50/p95/p99: 0.564 / 0.617 / 0.668 ms

QInt8 remains **rejected** for v2 because it changes validation predictions. FP32 is selected.

## Evidence artifacts

Current-head W12 evidence run `37225843627`:
- baseline validation artifact `11311728142` — ZIP SHA-256 `23386236e43f6c3e3b0ff1e034782ed7516502b3de703faae0775e940cc3d797`
- baseline ONNX artifact `11311807878` — ZIP SHA-256 `0fc9e21da1486d496800fd11b6c084b5d449e269204de56be0cac29535a4d87e`
- BERT Tiny artifact `11311629011` — ZIP SHA-256 `b99e1ef2aaefa3864f98acda12d55a8554beac01564d8325a5c9feecdd0adb69`
- BERT Mini artifact `11312028066` — ZIP SHA-256 `41eb6d4123b17e789bb1802e97138b8b55bca3829cefe4847ba1d6d9eb61e1e3`

All currently expire 2026-11-03. A durable production artifact destination is still unresolved.

## Acceptance contract

W12 v2 is frozen for final acceptance at model/code head
`3aac90ca8d0d57ca2174a852f961c6b753e7205d`, subject only to non-semantic
documentation/static-analysis cleanup that is demonstrated not to change model/runtime outputs.

Issue #43 / PR #44 owns a new independent unseen W20 acceptance set. W12 must not inspect that
set while it is being built.

After W20 is reviewed/frozen:
1. record the exact candidate/runtime artifact hashes;
2. evaluate v2 once;
3. report the result without tuning;
4. if any semantic model/preprocessing/threshold change follows, W20 becomes development evidence and a new unseen set is required.

## Known limitations

1. Training is synthetic-only; no production chat was used.
2. W11 near-duplicate detection was lexical rather than embedding-based.
3. BLACKMAIL has zero W11 training examples and is not a learned v2 class.
4. DOXXING/GROOMING support is sparse.
5. Containment duration remains sparse and partly policy-defined.
6. Structured durable memory is not supervised model input.
7. Baseline calibration is imperfect.
8. Some normal-user validation slices remain small and show non-zero false positives.
9. Old W11 held-out/golden results are permanently off-limits as v2 acceptance evidence.
10. QInt8 is rejected because it changes predictions.
11. Review artifacts are temporary; durable production model storage is unresolved.
12. AI does not own bans or final punishment decisions.

## Reproduction

```bash
python -m workers.w12.run_validation_baseline
python -m workers.w12.train_encoder --candidate bert-tiny --seed 42 --epochs 5 --batch-size 16 --lr 3e-5
python -m workers.w12.run_validation_candidate --candidate bert-tiny --seed 42
python -m workers.w12.train_encoder --candidate bert-mini --seed 42 --epochs 5 --batch-size 16 --lr 3e-5
python -m workers.w12.run_validation_candidate --candidate bert-mini --seed 42
python -m workers.w12.run_baseline_onnx_evidence
```
