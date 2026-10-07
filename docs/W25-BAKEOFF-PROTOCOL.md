# W25 five-architecture moderation model bakeoff

W25 is an experiment branch. It does not deploy a model, change production
moderation behavior, enable automatic strikes, or authorize punishments.

## Development isolation

- Branch base: W12 model-training development state.
- W20 fresh acceptance data is forbidden during candidate development,
  threshold selection, calibration, and architecture selection.
- W11 train and validation are the inherited development partitions.
- Any new real-chat or adversarial source must be explicitly reviewed, hash
  pinned in workers/w25/admissions.json, and group-frozen before tuning.
- Generated variants from one base example stay in one partition.
- Final acceptance remains a one-shot action after an architecture is selected
  and frozen.

W21 has now passed an independent W25 admission review. Its exact reviewed
source is hash-pinned and split by family into 220 training, 100 development,
and 180 untouched adversarial-test records. No family crosses partitions. The
W21 slur families use a placeholder token, so they test evasion mechanics rather
than comprehensive real-world slur spelling coverage.

W26 has now produced 3,561 human-adjudicated real-chat examples from the
private Enthusia corpus. The exact private source and partition manifest are
SHA-256 pinned in `workers/w25/admissions.json`; raw production-derived text
remains off GitHub.

W26 freezes 3,098 family groups into 2,489 train / 506 development / 566 test
records. The test partition preserves an ALLOW-heavy real-chat distribution
(557 ALLOW / 9 BLOCK) and is now the W25 real-distribution suite. One unresolved
policy-gap record is quarantined and excluded.

Admitted-development training is therefore ready on an authorized private host
that has `W25_PRIVATE_DATA_ROOT` set to the directory containing the pinned
W26 files. Public GitHub Actions intentionally remains W11-only smoke evidence.

W27 now freezes 3,598 independently adjudicated later-period records after
quarantining two real-animal/pet-harm cases that Policy-v1 does not settle.
Related rows sharing context-message IDs or exact normalized target text remain
in one family. The family-disjoint W25 comparison partitions are:

- context: 600 records (588 ALLOW / 11 BLOCK / 1 REVIEW);
- time-based real chat: 2,998 records (2,989 ALLOW / 9 BLOCK).

The time-based suite also has a separate strict novel-target analysis containing
2,733 targets whose exact normalized target text does not occur in W26
train+development. This secondary analysis does not replace the production-shaped
time-based suite.

Canonical mirror/double-count suppression remains an incident-linker/runtime
responsibility and is separately covered by W24. W25's context suite measures
classifier-visible context, timing, channel/profile, retry/evasion, private-chat,
Discord, and cross-platform duplicate-control behavior.

All five W25 classifier comparison suites are now frozen. W20 remains unseen and
reserved for one-shot final acceptance after architecture selection and freeze.

## Immutable neural backbones

| Key | Model | Revision | License |
| --- | --- | --- | --- |
| modernbert-base | answerdotai/ModernBERT-base | 8949b909ec900327062f0ebf497f51aef5e6f0c8 | Apache-2.0 |
| deberta-v3-xsmall | microsoft/deberta-v3-xsmall | 79c19681226cddc96fe1d9625c8a3ed6dac79624 | MIT |
| deberta-v3-small | microsoft/deberta-v3-small | b25b093541eedd589b3fd60c30142da149189960 | MIT |
| canine-s | google/canine-s | afe7189a311a3ba3601525f03a98bb9e3d8a357e | Apache-2.0 |

Neural candidates use at least three fixed seeds: 42, 138, and 2026.

## Shared outputs

Every candidate must expose semantic label, message action, review priority,
strike recommendation, containment, support flow, calibrated confidence, and
uncertainty. Public experiment records are explicit allowlists; internal model
objects are never returned directly.

Punishment policy remains outside the model. EnthusiaStaff stays authoritative
for actual strikes and punishments.

## Consequence reporting

BLOCK, STRIKE, and containment are evaluated independently. Reports include
precision, recall, false-positive rate, false-negative rate, F1, false positives
per 10k/100k/1M benign messages, calibration, Wilson confidence bounds, and
selective risk/coverage. Semantic classification additionally reports macro-F1.

Production precision is also estimated at 0.05%, 0.1%, 0.5%, and 1% prevalence
using the declared base-rate formula. No precision percentage is presented as a
production claim without its evaluation distribution or prevalence.

Experimental target floors are:

- BLOCK: 99% precision.
- STRIKE: 99.5% precision and Policy-v1 eligibility.
- containment: 99.9% precision before consideration.
- disagreement or uncertainty: review/no irreversible punishment.

Readiness labels also require the 95% Wilson lower precision bound to meet the
same floor, so a small sample with zero observed errors cannot by itself qualify
for BLOCK, STRIKE, or containment consideration. These are experiment gates,
not deployment authorization.

## Planned candidate comparison

1. ModernBERT-base multi-task selective classifier, comparing raw input against
   raw plus deterministic normalized text.
2. DeBERTa-v3-xsmall and DeBERTa-v3-small in development; one size is selected
   using development evidence before the final comparison.
3. CANINE-S character-aware multi-task classifier.
4. ModernBERT plus word TF-IDF, character TF-IDF, and compact runtime-realizable
   evasion features; includes a word+character TF-IDF-only ablation.
5. Precision-first cascade with a cheap screen and ModernBERT verifier.
   Different REVIEW/BLOCK/STRIKE/containment operating points are permitted;
   model disagreement never directly authorizes punishment.

All candidates receive the same admitted training data and frozen comparison
suites. Suite reports carry fingerprints, and the final ranking refuses to
compare candidates whose supposedly shared suites do not match.

ModernBERT serialization and DeBERTa size are selected from three-seed
development aggregates before the final candidate comparison. Fusion and cascade
then consume those selected upstream variants rather than handpicked runs.

All trainable W25 candidates use the same deterministic adversarial-training
augmentation by default. Each clean training record is retained and receives at
most one generated target-text corruption, with attack family chosen by a stable
hash across the eight W25 mutation families. Generated variants stay in the
original training family and copy the reviewed Policy-v1 labels; validation and
all frozen comparison suites are never augmented. The `--clean-training-only`
flag exists only for the required pre-adversarial-training development ablation.

## Selection order

Candidate ranking is lexicographic by the project priorities, not a single
score: real-distribution false-positive behavior, block/critical recall,
adversarial robustness, seed/calibration stability, latency/throughput,
memory/artifact size, then deployment simplicity.

A winner may be recommended only for shadow/review use. If punishment-level
precision is not demonstrated, W25 must say so explicitly.

## Current execution gate

The experiment code, baselines, five candidate implementations, calibration,
adversarial harness, grouped failure reporting, seed-stability reporting,
base-rate analysis, ONNX parity checks, and Bloom-oriented latency/RSS/queue
benchmark primitives are implemented.

The public manual bakeoff workflow is W11-only by design. It does not accept
private W26 data. A private-host run must first execute:

`python -m workers.w25.run_bakeoff preflight --require-ready`

which verifies the W21, W26, and W27 admitted sources and their applicable
partition manifests against pinned SHA-256 values before training/evaluation.

All required comparison suites are frozen:

- balanced policy;
- real distribution (W26);
- adversarial/evasion (W11 + W21);
- context (W27);
- time-based real chat (W27).

The remaining blocker is execution of the full private-host multi-seed bakeoff
and evidence aggregation. W20 is not referenced by the development workflow and
remains reserved for the one-shot acceptance process after an architecture is
selected and frozen.

There is intentionally no W25 winner yet. No BLOCK/STRIKE/containment readiness
claim may be made before the full private bakeoff is executed and compared on
fingerprint-identical copies of all five suites.
