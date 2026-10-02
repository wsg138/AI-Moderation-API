# W12 launch packet — classifier training, evaluation, ONNX export, and runtime model contract

## Identity

You are **W12**, the model-training worker for Enthusia AI Moderation.

Authoritative issue: **#13 — W12 — Classifier training, evaluation, ONNX export**.

Repository: `wsg138/AI-Moderation-API`.

Create branch **`w12/model-training` from the live current `main` when you start**. Live GitHub is authoritative. Open one PR to `main`; do not self-merge.

No production deployment is authorized.

## Why this work matters

The service already has the durable Policy-v1 runtime/API contract, but its local classifier is still a fail-open stub. W12 must build a measured local CPU inference model suitable for the existing Ticket Bot Pterodactyl host without turning generic Internet moderation scores into Enthusia policy.

Enthusia policy deliberately contains platform/context distinctions such as:

- Minecraft generic PvP language may be allowed;
- Discord general does not inherit a Minecraft gameplay prior without actual game context;
- explicit real-world continuations such as `irl`, school, house/address, time, or delivery cues can reverse an otherwise gameplay-like phrase;
- `kys` is BLOCK + strike;
- ordinary low-level toxicity such as `you suck` must not be overblocked;
- Minecraft TNT requests are benign while resolved real-world explosive-construction requests are blocked;
- public vs private sexual/flirting context differs;
- first-person self-harm disclosure is a care/support path, not punishment reputation.

The goal is a reliable local classifier under strict false-positive and fail-open constraints, not the biggest possible model.

## Upstream gates are complete

W11 is accepted and merged.

Accepted W11:
- PR #41;
- accepted head: `3b71c0500c41f883fe6c5d462ce8732dfb185d91`;
- merge commit: `5c337488d3014aefda7ba29fc0883b2beaa5dc0d`;
- exact-head service-ci #83: success;
- post-merge main service-ci #84: success.

Integrated corpus:
- **4,500** synthetic records;
- **1,883** integration families;
- split algorithm: **w11-v2**;
- train: **3,269**;
- validation: **385**;
- test: **410**;
- frozen adversarial: **436**;
- owner golden acceptance set remains separate.

W19 PENDING-event recovery is also accepted and merged:
- PR #40;
- final head `2954bd53b04472537ddfef9622832882b2d8c348`;
- merge commit `917aef4e97c539fea89d558f9e1be9d0d506b4a4`;
- exact-head service-ci #67: success;
- post-merge main service-ci #69: success.

The runtime contract in `docs/API-CONTRACT.md` is now the client-facing Policy-v1 contract.

## Mandatory sources

Before coding/training, read at minimum:

- issue #13;
- `COORDINATOR-STATE.md`;
- `docs/WORKER-SYSTEM.md`;
- `docs/WORKER-LAUNCH-STANDARD.md`;
- `docs/API-CONTRACT.md`;
- `docs/DEPLOYMENT.md`;
- `docs/W11-DATASET-INTEGRATION-REPORT.md`;
- `data/integration/W11-split-manifest.json`;
- `data/integration/W11-adversarial-eval-manifest.json`;
- `data/integration/W11-audit.json`;
- `data/eval/owner-policy-v1.jsonl`;
- `data/eval/owner-policy-v1-manifest.json`;
- `policy/POLICY-v1.md`;
- `policy/UNRESOLVED-DECISIONS.md`;
- `service/moderation_api/classifier.py`;
- `service/moderation_api/models.py`;
- `service/moderation_api/runtime.py`;
- current deployment/runtime dependency files.

Do not use or request raw production chat.

## Hard split / evaluation rules

These rules are non-negotiable.

### Training material

Ordinary training may use only W11's `train` partition.

### Validation

Use only W11's `validation` partition for:
- hyperparameter selection;
- model/candidate selection during development;
- threshold selection;
- calibration fitting;
- early stopping.

### Frozen test

Do not tune on W11's `test` partition. Use it only after the candidate/configuration/thresholds are frozen.

### Frozen adversarial

Do not train or tune on W11's `frozen_adversarial` partition. Use it only as final robustness evaluation.

### Owner golden set

The owner-policy golden set is acceptance evidence, not training data and not ordinary validation data.

Do not:
- train on it;
- copy it into augmentation;
- tune thresholds against it;
- choose a model based on repeated golden-set probing.

Run it only as final acceptance evidence after the candidate is frozen. Report it separately from synthetic test metrics.

If observing the golden result causes a model/config/threshold/preprocessing change, record that the observed golden set has become development evidence. Do not keep iterating on the same golden set and still describe the later result as unbiased final acceptance; a new/versioned unseen acceptance set is required for that claim.

Family/group leakage must remain impossible. Never reconstruct a new random split.

## Current W11 integration facts

W11 found:
- 83 text-only exact groups, all intentional context/policy contrasts;
- 0 redundant same-context/same-outcome exact duplicate groups;
- 2,722 lexical near candidates;
- 27 cross-worker near pairs, all linked into the same integration family before splitting;
- 12 cross-worker differing-decision near pairs reviewed against settled Policy-v1 §6 or §11;
- 0 unresolved cross-worker contradictions;
- 1 synthetic↔golden lexical candidate at similarity 0.760331, below the 0.88 training-sensitive threshold;
- no synthetic golden-sensitive example at the W11 threshold.

Near-duplicate detection is lexical rather than embedding-based. Treat that as a known limitation, not proof that there can be no semantic overlap.

## Runtime interface you must respect

The service calls:

```python
class LocalClassifier(Protocol):
    async def classify(self, item: ClassificationInput) -> ClassificationResult: ...
    def health(self) -> dict[str, object]: ...
```

`ClassificationInput` contains:
- current `ContextMessage`;
- bounded prior `context`;
- structured `MemorySnapshot` with punishment and safety memory separated.

`ClassificationResult` requires:
- `message_action`;
- `semantic_label`;
- `review_priority`;
- `strike_recommendation`;
- `containment`;
- `containment_duration_seconds`;
- `support_flow`;
- bounded scores/confidence;
- auditable reason/rule metadata;
- related/evidence message IDs;
- model version;
- optional incident signal.

Do **not** collapse these into one toxicity score.

AI still does not own a human ban or final punishment decision.

## Modeling strategy

Do not assume one pretrained encoder is best.

Compare at least:
1. a lightweight classical/text baseline useful for sanity checking (for example TF-IDF + linear heads); and
2. at least **two** small pretrained encoder candidates appropriate for CPU inference/ONNX.

For pretrained candidates:
- record exact model identifier and immutable revision/commit;
- record model license and confirm it is compatible with this public repository and intended production use;
- prefer models with well-supported ONNX export and CPU quantization;
- do not select a candidate merely because its aggregate F1 is highest if it materially worsens critical false positives or threat recall.

The final recommendation must be evidence-driven.

## Input serialization

Define and freeze one explicit serialization contract for training and runtime inference.

It must preserve the information Policy v1 depends on:
- platform/channel profile;
- ordered message sequence;
- which message is current/target;
- speaker boundaries;
- relative timing/offset information where present;
- enough context to distinguish split-message continuations.

Do not train on or serialize as model input:
- semantic labels or any other outcome target;
- action / review priority / strike / containment / duration / support-flow values;
- reason codes or rule-hit labels;
- domain;
- difficulty;
- example IDs;
- source file/prefix;
- split name;
- family ID;
- synthetic `notes` or report prose;
- owner interview IDs / policy-section annotations;
- raw runtime UUIDs/player IDs;
- arbitrary absolute timestamps.

These fields are answer/editorial metadata. In particular, `notes`, `reason_codes`, `domain`, and `difficulty` can directly reveal why a synthetic example was labeled. Using them as encoder input would invalidate the evaluation.

Use stable structural markers/tokens rather than accidental source formatting.

If structured memory is not represented in the synthetic corpus well enough for supervised training, do not pretend the model learned it. Keep unsupported runtime-memory logic conservative and explicit.

## Output design

The dataset contains Policy-v1 outcome dimensions separately. Model/evaluate them separately.

### Dataset action vs runtime visibility action

The source dataset intentionally contains a three-value `action` field:
- `ALLOW`;
- `BLOCK`;
- `REVIEW`.

In the dataset schema, `REVIEW` means the message remains visible while review work is created.

The runtime API intentionally does **not** have an overloaded REVIEW message action. Runtime `MessageAction` is only:
- `ALLOW`;
- `BLOCK`;

and `review_priority` is a separate dimension.

Therefore W12 must:
- report the issue-required **three-way ALLOW/BLOCK/REVIEW dataset-action metrics**;
- also report derived **runtime binary visibility metrics**, where source BLOCK is runtime BLOCK and source ALLOW/REVIEW are runtime ALLOW;
- preserve/predict review behavior through the separate `review_priority` target;
- never add REVIEW back into the runtime `MessageAction` enum merely to match the training file.

This is a schema/API compatibility rule. It does not authorize relabeling any W11 example.

### Strike target vs runtime enum

W11 supplies a boolean `strike` target. Runtime exposes `StrikeRecommendation.NONE | EVIDENCE | STRIKE`.

Do not invent a supervised EVIDENCE class that the accepted synthetic labels do not provide. Evaluate the boolean target directly. A runtime adapter may map supervised false/true to NONE/STRIKE; any future EVIDENCE-only behavior needs an explicit policy/data source.

At minimum, measure:
- semantic label;
- three-way dataset action;
- derived binary runtime visibility action;
- review priority;
- strike;
- containment;
- support flow.

Containment duration is highly sparse and partly policy-defined/unresolved. Do not invent a fully learned duration policy from 195 MUTE records. Prefer a documented conservative deterministic mapping only where Policy v1/data provide an explicit duration; otherwise return `None` and preserve review behavior.

Reason codes are auditable facts, not free-form chain-of-thought. If you model them, use a bounded multi-label vocabulary and measure them explicitly. Do not generate prose reasoning.

Dynamic `related_message_ids`, evidence IDs, and incident IDs are runtime identifiers, not fixed classes. Do not invent IDs from the model. Any runtime adapter must select only IDs present in the actual `ClassificationInput` and remain within the API contract's allowlisting behavior.

## Critical evaluation

Do not report only accuracy.

Required final evaluation:

### Semantic label
- per-class precision / recall / F1;
- macro F1;
- weighted F1;
- confusion matrix.

### Policy dimensions
Separate metrics for:
- three-way source action: ALLOW / BLOCK / REVIEW;
- derived runtime visibility action: ALLOW / BLOCK;
- review priority;
- strike;
- containment;
- support flow.

For binary/rare heads, include precision, recall, F1, support, and confusion counts.

### Critical policy slices
Report dedicated slices for at least:
- Minecraft gameplay/PvP false positives;
- benign/hard negatives;
- generic Minecraft violence vs explicit real-world cues;
- real-world threat recall;
- split-message threat continuation;
- long-gap/non-linkage false positives;
- `kys` / self-harm instruction;
- first-person self-harm disclosure;
- slur actual-use vs reference-only;
- public vs private flirting/sexual context;
- sexual/minor cases and age-evidence reliability;
- Minecraft TNT vs real-world explosive request;
- obfuscation/evasion;
- frozen adversarial W11 slice.

For the Minecraft gameplay slice, report both:
- BLOCK false-positive rate;
- count/list of the most important false-positive families.

A candidate with a noticeably worse gameplay false-positive rate is not acceptable merely because macro F1 improves.

### Owner golden acceptance
Run the owner golden set only after freezing the final candidate.

Report:
- overall pass count;
- failures by owner fixture ID;
- failure dimensions;
- whether each failure is model semantics, thresholding, or unsupported runtime logic.

Do not alter the golden set to improve results.

## Calibration / thresholds

Use validation only for thresholding/calibration.

Required:
- reliability/calibration analysis;
- expected calibration error or similarly explicit metric;
- Brier score where applicable;
- reliability plot/table;
- chosen thresholds with rationale.

Use asymmetric thresholds when justified by policy risk. For example, BLOCK false positives on normal Minecraft gameplay have a different cost from routing an ambiguous case to review.

Do not tune on test, frozen adversarial, or golden.

## Training methodology

Make training reproducible.

Record:
- Python/library versions;
- model identifier + immutable upstream revision;
- seed(s);
- tokenizer config;
- max sequence length;
- batch size;
- optimizer/scheduler;
- learning rate;
- epochs/early stopping;
- class weighting or sampling;
- multi-task loss weights;
- threshold/calibration procedure;
- hardware used;
- elapsed training time.

Use multiple seeds for the final shortlisted candidate if practical. If compute limits prevent this, say so and quantify the limitation.

## ONNX / CPU artifact requirements

Final export must target CPU inference.

Required:
- ONNX export;
- ONNX model validation;
- dynamic/int8 quantization comparison where supported;
- numerical parity check against the framework model on a representative validation batch;
- artifact SHA-256;
- artifact size;
- exact export command/script;
- model metadata file;
- tokenizer/config artifacts required for deterministic inference.

Do not commit a large model binary directly into Git unless repository policy is explicitly changed.

Preferred storage behavior:
- keep reproducible export/training scripts and metadata in Git;
- if CI/PR artifact storage is available, use it for review evidence;
- otherwise record checksums, sizes, and exact reproduction steps and surface the lack of an approved durable binary store to the coordinator.

Do not invent an artifact upload destination.

Avoid unsafe pickle-only runtime loading. Prefer ONNX plus normal tokenizer/config files and immutable checksums.

## Runtime resource envelope

Target host:
- Python 3.12;
- no GPU dependency;
- 2 GB total container RAM;
- existing Ticket Bot normally uses roughly 300 MB and remains priority.

Benchmark the final ONNX candidate on CPU.

Required measurements:
- cold load time;
- steady-state RSS attributable to model/runtime;
- single-request latency p50/p95/p99;
- batch-size-1 throughput;
- representative multi-message input latency;
- quantized vs non-quantized latency/size/memory;
- benchmark CPU/platform details.

Use multiple warmup iterations and enough timed iterations to make p95 meaningful.

The model should fit comfortably under the host limit with several hundred MB of safety headroom. Do not consume the whole 2 GB merely because it technically fits.

## Runtime adapter

W12 should provide the code needed for the service to load/use the accepted ONNX classifier **without deploying it**.

Requirements:
- artifact path configurable through environment/config, not hard-coded;
- health reports not-ready if required model/tokenizer artifacts are missing or checksum/version validation fails;
- load failure is fail-open through the existing runtime;
- inference timeout/error is fail-open through the existing runtime;
- bounded score outputs;
- deterministic preprocessing identical to training;
- no network download at service startup;
- no hidden dependency on Hugging Face Internet access in production;
- model version includes a reproducible artifact/config identifier.

If the final binary is intentionally not in Git, tests must use a small fixture/mock export so repository CI remains self-contained.

Do not weaken the existing queue/deadline/fail-open contract.

## Dependency policy

Do not casually add the entire training stack to production runtime requirements.

Separate:
- development/training dependencies;
- export dependencies;
- minimal production ONNX inference/tokenizer dependencies.

Pin production-compatible versions in the appropriate runtime lock only after measuring and justifying them.

## Unresolved Policy-v1 edges

Do not manufacture labels or thresholds for:
1. Discord bot DMs;
2. exact graphic first-person self-harm boundary;
3. consensual explicit adult PM content;
4. grooming with genuinely uncertain minor status;
5. broader dangerous instructions beyond resolved explosive examples;
6. fake-doxxing strike cleanup;
7. complete threat severity→containment-duration matrix;
8. exact blackmail containment duration;
9. accidental lexical slur/substring false positives.

If training data appears to answer one of these, surface it instead of expanding policy.

## Privacy / safety

Repository is public.

Never commit:
- production chat;
- player identifiers;
- runtime moderation DBs;
- credentials/API keys;
- private staff data.

Do not augment dangerous-instruction examples into actionable real-world recipes.

## Deliverables

At minimum:

- reproducible dataset loader using W11 manifests;
- frozen input serialization/tokenization contract;
- baseline training/evaluation code;
- candidate encoder training/evaluation code;
- multi-task output design or a clearly justified alternative;
- validation-only threshold/calibration tooling;
- full final test/adversarial/golden evaluation report;
- confusion matrices/calibration plots or machine-readable data used to make them;
- ONNX export + validation + quantization scripts;
- benchmark script and measured CPU results;
- artifact metadata/checksum manifest;
- production runtime classifier adapter and focused tests;
- dependency separation;
- human-readable W12 model card/report documenting known limitations.

Keep generated metric artifacts reasonably small and text/JSON where possible.

## Acceptance criteria

Before requesting review:

- no family/split leakage;
- training loader consumes only W11 train IDs for training;
- validation is the only tuning partition;
- test/frozen adversarial/golden are excluded from fitting/calibration;
- at least two small encoder candidates plus a simple baseline are compared;
- final candidate choice is justified by critical policy slices, not aggregate F1 alone;
- Minecraft gameplay false positives are explicitly measured;
- real-world threat and split-message recall are explicitly measured;
- per-label and per-policy-dimension metrics are present;
- calibration is measured and thresholds documented;
- ONNX export validates and matches framework outputs within documented tolerance;
- quantized CPU artifact is benchmarked;
- runtime memory/latency evidence fits the deployment envelope;
- runtime adapter remains fail-open and does not download from the Internet at startup;
- all repository tests pass;
- Ruff passes;
- strict mypy passes;
- complexity gate passes;
- dataset QA/W11 reproducibility still pass;
- wheel build passes;
- exact-head GitHub CI is green.

Do not claim a hosted quality check that does not exist.

## Non-goals

Do not:
- change Policy v1;
- change the W11 split to improve metrics;
- edit the owner golden set;
- ingest production chat;
- implement client integrations in RoseChat/Discord/EnthusiaStaff;
- enable automatic punishment;
- deploy/restart the AI service;
- change live Pterodactyl configuration.

## PR completion comment

Include:
- exact head SHA;
- candidate models/revisions/licenses;
- final selected candidate;
- exact W11 split counts actually consumed;
- validation/test/frozen-adversarial/golden results;
- critical slice metrics;
- calibration/threshold summary;
- ONNX/quantized SHA-256 and sizes;
- CPU benchmark environment and p50/p95/p99/RSS;
- artifact publication/storage status;
- tests/CI run;
- known limitations;
- confirmation that no production deployment occurred.
