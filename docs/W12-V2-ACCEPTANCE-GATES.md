# W12 v2 — pre-registered fresh-acceptance gates

Recorded: 2026-10-05

These gates are fixed **before** the W20 unseen acceptance corpus is revealed to
W12. They are intended to decide whether the frozen `w12-v2` classifier is
acceptable for merge and controlled pre-production/shadow rollout.

They are not permission to enable automatic punishment.

## Why this is pre-registered

The original W11 held-outs became development evidence when preprocessing
changed after their results were observed. W20 exists to restore an unbiased
acceptance check. Defining pass/fail rules only after seeing W20 would undermine
that purpose.

Do not lower these gates in response to W20 results. If a semantic
model/preprocessing/threshold change is made after W20 is opened, W20 is burned
as acceptance evidence and a new unseen set is required.

## Corpus coverage minima

W20 may use overlapping tags/slices; these are minimum scored examples, not
necessarily disjoint quotas.

- Minecraft gameplay/PvP benign or allowed: >= 25
- generic Minecraft violence allowed: >= 20
- benign hard negatives: >= 30
- real-world threats: >= 25
- split-message real-world threats: >= 20
- long-gap/context-non-linkage benign cases: >= 15
- self-harm instruction/encouragement: >= 15
- self-harm disclosure/support (non-block): >= 15
- actual slur use where Policy v1 is settled: >= 15
- quotation/reference/counterspeech/reclaimed or other settled non-use contrasts: >= 15
- sexual-minor/grooming blocking cases: >= 20
- benign age/self-report-only contrasts: >= 20
- dangerous real-world instruction requests: >= 15
- Minecraft/fictional dangerous-instruction contrasts: >= 15
- obfuscation/evasion blocking cases: >= 20
- private/benign flirting contrasts where Policy v1 is settled: >= 20
- Discord-general allowed examples: >= 25
- Minecraft-public allowed examples: >= 25

Unresolved Policy-v1 cases are excluded from scored acceptance.

## Primary runtime-action gates

All must pass:

- runtime BLOCK precision >= **0.90**
- runtime BLOCK recall >= **0.90**
- benign hard-negative BLOCK false-positive rate <= **0.05**
- Minecraft gameplay/PvP BLOCK false-positive rate <= **0.05**
- generic Minecraft violence BLOCK false-positive rate <= **0.05**
- Minecraft-public allowed-example BLOCK false-positive rate <= **0.05**
- Discord-general allowed-example BLOCK false-positive rate <= **0.08**
- private/benign flirting BLOCK false-positive rate <= **0.10**
- benign age/self-report-only BLOCK false-positive rate <= **0.10**
- long-gap/context-non-linkage BLOCK false-positive rate <= **0.05**

## Safety-recall gates

All must pass:

- real-world-threat BLOCK recall >= **0.90**
- split-message-threat BLOCK recall >= **0.90**
- self-harm-instruction BLOCK recall >= **0.90**
- sexual-minor/grooming BLOCK recall >= **0.95**
- dangerous-real-world-instruction BLOCK recall >= **0.95**
- actual-slur-use BLOCK recall >= **0.90**
- obfuscation/evasion BLOCK recall >= **0.85**

## Structured-output gates

- semantic-label macro F1 >= **0.75**
- review-priority macro F1 >= **0.80**
- URGENT review recall >= **0.85**
- no semantic class with >= 10 scored examples may have F1 < **0.50**
- no malformed/unknown runtime enum output is permitted
- exact selected ONNX bundle must complete the full acceptance set without
  inference/runtime errors.

A support-flow or containment dimension with too little W20 support for a
meaningful aggregate score must be reported as underpowered rather than silently
treated as passing.

## Artifact/runtime gates

These are independent of corpus quality and must also pass:

- metadata and every model/vectorizer checksum verify;
- metadata requires `serialization_version=w12-v2`;
- selected FP32 bundle retains zero validation prediction mismatches versus the
  frozen sklearn baseline within the existing parity tolerance;
- production runtime uses JSON + ONNX only, not pickle/joblib;
- W12 service CI is green on the final code head;
- hosted static analysis has no unresolved valid new finding at the final head;
- fail-open tests remain green.

## Interpretation

Passing W20 means the model may be accepted into the moderation service and move
to controlled rollout/shadow verification. It does **not** authorize bans,
mutes, strikes, or other automatic punishments.

Failing any hard gate means:
1. record the failure without changing W20;
2. W20 becomes development evidence if the model is changed;
3. fix the training/model/data problem using train + validation and the observed
   W20 failure only as documented development evidence;
4. create a new versioned unseen acceptance set before claiming final acceptance.

No post-hoc threshold relaxation is allowed merely to make a failed W20 pass.
