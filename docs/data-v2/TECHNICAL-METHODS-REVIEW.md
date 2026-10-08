# Data/Model v2 — technical review and recommended experiment contract

**Date:** 2026-10-07. **Status:** methods/design review only; not a human second-annotation pass, not an acceptance certificate, and not permission to train, merge, deploy or punish. Complements issue #53 and draft PR #54. This document was prepared from public-safe schema, policy and aggregate project records only. No private player records were inspected.

## Decision in one paragraph

**Prioritize ground truth, representative SAFE traffic, leakage-resistant evaluation and a versioned deterministic Policy-v1 resolver over more synthetic volume or a larger model.** Use the existing lightweight encoder as the first controlled baseline. Study context-window size and real/synthetic weighting on development data, then add audited hard negatives. Do not pay for domain-adaptive pretraining (DAPT) or a larger GPU unless a matched ablation demonstrates a credible remaining domain-language error. Do not claim 99% because of a high ALLOW prevalence or a small balanced test.

## 1. Data sources, manifests, lineage and permissions

Keep physically/logically distinct immutable collections: (a) eligible real unlabeled chronological streams; (b) independently verified real target windows; (c) independently reviewed synthetic minimal-pair families; (d) weak/model predictions; (e) frozen/acceptance suites. Training must be an explicit manifest-based materialization of **approved** source revisions, not a glob over all JSONL in a folder.

The existing public source-registry.json is a good start. Add **private per-example records** using this public-safe illustrative shape (values are invented placeholders, not player data):

~~~json
{
  "registry_schema": "data-v2/example-manifest/1",
  "example_id": "SYN-FIX-001",
  "source_id": "public-synthetic-fixture",
  "source_revision": "sha256:PLACEHOLDER",
  "source_kind": "synthetic_reviewed",
  "rights_status": "approved_for_specific_training_use",
  "privacy_status": "public_synthetic",
  "policy_version": "v1",
  "record_schema_version": "dataset-v1",
  "parser_revision": "fixture",
  "redactor_revision": "not_applicable",
  "context_builder_revision": "context-v1",
  "source_time_bucket": "synthetic",
  "session_group": "SYN-SESSION-001",
  "family_group": "SYN-FAMILY-001",
  "parent_ids": [],
  "variant_type": "hard_negative_minimal_pair",
  "target_index": 2,
  "label_status": "independently_adjudicated",
  "review_protocol_revision": "rubric-v1",
  "approved_uses": ["train"],
  "split": "train",
  "release_id": "candidate-v2-001",
  "content_digest": "sha256:PLACEHOLDER",
  "admission_status": "eligible"
}
~~~

For real data, store actual source identifiers, dates, rights/permission documentation, keyed link tokens, reviewer identities, review notes and content hashes **privately**; do not publish even pseudonymized linkage keys, file paths, original texts or private sample-level error data. An unkeyed hash of low-entropy names/chat text is not anonymity. Every transform is a new immutable derivative with parent IDs, code/config revision, content digest, manifest digest and a revocation/tombstone rule. A withdrawn/deletion-requested source invalidates all descendant versions; remove them from future training and document model-retraining/remediation decisions. No source is train-eligible solely because it parses.

**Policy precedence:** accepted policy/POLICY-v1.md and owner interview resolution outrank these suggestions; preserve explicit null/unresolved outcomes, never fill them with a nearby default.

## 2. Training order — what should actually happen first

1. Stop admission of G10–G27 until PR #52 final-byte QA is regenerated, its 12/18 mismatched label reports are corrected, code alerts triaged, labels independently reviewed and families checked. Its 9,000 candidate records are not ground truth. Qwen's 10/21 policy check is not acceptable as unattended labeling.
2. Build a **small verified real development subset** from rights-cleared local material, including ordinary randomly selected SAFE messages and deliberately sampled rare/borderline cases. The 2,279 priority windows are selected, not prevalence-representative. Keep the 552 already-scored/sealed windows out of iteration.
3. Freeze session/family splits, policy-aware annotation and a new *prospective* never-scored traffic holdout **before any next model-based mining or experiment**.
4. Establish no-training baselines on the exact same development split: current W12/W25 encoder/router and a cheap TF-IDF model; separate model semantic-label quality from deterministic policy-resolver quality.
5. First paid/heavy experiment, after explicit owner approval: fine-tune **one already available lightweight pretrained encoder** on verified real + re-audited synthetic labels. Use natural context, a frozen recipe, and report error differences relative to baseline.
6. Next ablation: same model/seed/data and schedule but add independently reviewed hard pairs/rare-class sampling. Measure improvements **and** SAFE false-block regressions.
7. Then evaluate the alternative semantic-facts -> deterministic Policy-v1 resolver against direct six-field prediction. Facts require their own adjudicated evidence; this is an engineering ablation, not a free accuracy improvement.
8. DAPT/MLM on train-eligible unlabeled real Minecraft text is **last**, compared at fixed downstream labeled data, seeds and compute. Published research shows domain adaptation can help, but it is not evidence that it will help this task. Only do it if systematic jargon/tokenization/domain errors remain and an approved pilot has a favorable cost-benefit result.
9. Repeat only the best candidates with seeds **42, 138, 2026** and freeze thresholds/calibration on development. Respect PR #48 W25 separation; W27/W20 are not a reusable hyperparameter leaderboard.

Cheap preflight: validate schemas, split/family maps, feature/label correlations, sample loss distribution, and input token lengths **without model download or large local scans**. No costs/runtime are claimed until a device-specific bounded benchmark and owner approval.

## 3. Target-focused chronological context

For a first benchmark, start with **up to 8 preceding messages AND at most 120 seconds**, capped at 512 input tokens, chosen from a **trusted conversational scope**. This is a proposed starting point, **not** a hard Policy-v1 rule: compare target-only vs 2/5/8 earlier messages and 30/120/300 seconds on the development split. Evaluate class-wise changes and added false positives.

Every example has exactly one target index; the target is the **latest available message** at that decision time. Preceding messages are not automatically harmful labels. Preserve original timestamps (relative signed offsets in the training view), within-conversation stable speakers, the target's author, target/recipient IDs as opaque scoped roles, reply links when authoritative, channel profile, server/session and authoritative platform mirror links.

**Never join merely because messages are close in time.** A private conversation must remain participant-pair scoped. Keep staff/ticket/exempt-channel text outside context. Changing server/channel/participant pair resets context unless a verified reply, identity/incident linkage justifies a constrained cross-channel view. A long AFK gap must break naive recency context. Policy v1 also rejects linking split fragments merely because ~20 unrelated messages separate them.

Use an **online/as-of-time build**: prohibit timestamps after target and prohibit learned/future metadata. Retroactive deletion is a *later, separate event-driven policy decision*, not a license to feed future messages into an earlier prediction.

## 4. Leakage audit and split freezing

Assign split at a **connected-component group level**, not row level. Union records that share: source conversation/session; any overlapping source message IDs in target/context windows; canonical mirrored event; incident thread; augmentation parent; exact duplicate; minimal-pair/paraphrase family. Where the same original message appears in multiple windows, its entire component must stay in one split. A single family identifier alone is insufficient when two families have overlapping sources.

Use a forward-time evaluation cohort from **new data captured after a published cutoff**, with a safety embargo around partition boundaries. Also report source-server/channel and novel-session slices; these are not a substitute for the prospective time-based cohort. If shared groups span dates, assign the whole group once or exclude boundary windows. Store the split manifest hash and sampling seed **privately** before scoring.

Run exact normalized text and target+context digests, cross-source character/word n-gram MinHash or SimHash candidate retrieval, and review flagged semantic/embedding neighbors. Test both target-only and target+conversation paraphrase similarity. Normalize spacing/case/Unicode carefully; retain a raw-vs-normalized equivalence map. Do **not** automatically purge all common messages like "gg" because high repetition is part of genuine traffic; distinguish generic reusable tokens from source-derived leakage. Collision/near-overlap acceptance requires documented reviewer dispositions. Audit each data refresh, not just the first split.

**Protected:** W20, W27 and the previously model-mined 552-row subset must not enter model selection, threshold tuning, prompt construction, hard-example targeting, feature design, or iterative failure inspection. An assessment set touched for iteration is no longer independently held out. Claiming unbiased performance requires a new prospectively frozen independent cohort.

## 5. Independent blind label protocol

Blind label packets to model score, seed dataset label, generator goal and other annotator. **Two independent reviewers** for all critical/safety-class records intended for gold, contested policy cases, high-cost false-block examples, and representative samples of non-critical records. A single automated annotator + spot checking is insufficient for critical labels. An owner-policy adjudicator resolves disagreement. If policy itself is unresolved, quarantine; do not vote on a missing rule.

Annotate **observable facts first**: scope, source/target of speech, gameplay cue, real-world cue, quoted-vs-directed nature, age evidence tier (unknown/self-reported/independently reliable), participant continuity, repetition, prior verified stop request, reply linkage, target confidence and absent evidence. Then the semantic label and policy-specific six outcome dimensions, including null when genuinely unresolved. Track disagreements **by category and fact**, reviewer confidence/calibration, and adjudication policy section. Unverifiable age is NOT reliable minor status.

Crucial policy-specific examples: generic "I will kill you" in Minecraft can be ALLOW, whereas Discord general differs. Under **current Policy v1 actual quoted slurs are still BLOCK**, even if quote/report context mitigates intent; do not use a generic external platform's "quoted slur = always SAFE" rubric. First-person self-harm disclosure routes to support rather than a strike. Plain server-IP discussion is not doxxing. Grooming must have strong minor/pattern evidence, not a mere age guess. Some Policy-v1 penalties are unresolved; do not train false concrete durations.

Gold promotions require rights/privacy clearance, both independent decisions where required, resolution of contradictions, source lineage, split assignment and signature/record of adjudicator. Create versioned corrective delta rows; do not silently edit already-frozen examples.

## 6. Traffic-representative SAFE and challenge suites

Maintain two separate evaluation views:
- **Traffic view:** probability or time/session-based sampling from actual future moderated traffic, with its naturally occurring SAFE prevalence, channel/time stratification and unbiased random denominators. This is the source for real-world false-BLOCK and workload estimates. Label even seemingly boring chat. Use target-level action metrics and session-cluster uncertainty.
- **Challenge view:** independently authored/test-only and actual rare-class examples (credible threats, slur quotation, self-harm, sexual-minor, grooming, doxxing, blackmail, evasions, gameplay hard negatives), deliberately enriched to measure per-class recall and exact policy behavior. Never call its raw aggregate accuracy "deployment accuracy."

A mostly SAFE stream can give an "always ALLOW" classifier high accuracy. Conversely, 99% BLOCK precision from a balanced test can collapse under real violation prevalence. Report class prevalence and prevalence-adjusted expected precision with scenario assumptions, not only macro percentages. Keep false-BLOCK denominators specifically benign/gold-ALLOW traffic; report wrongful STRIKE/MUTE separately.

## 7. Synthetic data: realism and contradiction gates

Generate a *scene*, not a succession of category exemplars. Each scene should contain a normal conversational objective (mining, queueing, gear, builds, event planning), ordinary interleaved speech with appropriate delays, then **at most one or a causally connected small number of safety targets**. A scene may also be entirely SAFE. Keep banter, jokes and corrections common without creating chains of unrelated severe offenses.

Construct paired scenes by changing **one verified interpretation variable** (same-sender vs different sender; Minecraft vs Discord general; IRL cue vs game cue; known minor vs unsupported self-report; actual slur vs reference; existing targeted threat vs general game taunt; one continuous incident vs 15-minute gap). Each branch receives its own annotation, but shares a family group for leakage. Never force a desired offense label when the actual context contradicts it.

Score sampled candidate scenes before admission on: chronological validity; unique target; metadata/speaker consistency; channel/participant realism; baseline SAFE density; coherent topic/time gaps; valid policy label; expert semantic disagreement; within- and cross-family redundancy; parser/redaction artifacts. Compare vocabulary, message-length, turn-count and per-scene unsafe-density distributions to **approved aggregate** real traffic, not private copied text. Quarantine unnatural "offense stacks", future clues, fake age authority, corrupted game vocabulary, and identical text paired with contradictory metadata/labels. Synthetic volume is a tool for coverage, not an accuracy metric.

## 8. Evaluation gate: define the consequence, then the threshold

Report three distinct questions: (1) semantic class correctness; (2) action (ALLOW/REVIEW/BLOCK) correctness and consequence-specific harm; (3) **full decision exact match** across action, review priority, strike, containment, duration when policy-resolved, and support flow. For historically tracked six fields, give a six-field score on *fully specified gold decisions*, plus a separate partial-field/known-mask score and unresolved count; never silently convert policy nulls to "NONE" or treat them as successes.

**Proposed acceptance targets for discussion, not approved Policy-v1 cutoffs:**
- Overall full-decision exact match at least 99% with an explicit one-sided 95% lower confidence bound target, on a genuinely independent data cohort; give action accuracy separately.
- **Wrongful BLOCK**: aim for a one-sided 95% upper confidence bound **no greater than 0.5 per 1,000** genuine ALLOW messages in traffic view. This is a deliberately strict proposal; final tolerances require staff/owner risk and observed-volume budgeting.
- Critical-class recall and no severe cross-category support/punishment regressions; require an independently agreed per-category lower-confidence-bound floor, not a microaverage hiding a rare safety failure. For comparison, observing 300/300 successes only supports about 99% as a one-sided 95% lower bound *under independent sampling*.
- Record REVIEW/abstention fraction, false-review per 1,000 SAFE, fraction of critical cases safely captured by review, staff minutes/day, escalation delay, and p95/p99 latency during concurrent chat.

With **zero** wrongful blocks in n independent SAFE trials, the one-sided 95% upper error bound is approximately 3/n: around **6,000 independently representative SAFE targets** are needed even to upper-bound the false-BLOCK rate around 0.5/1,000. Correlated sessions reduce effective evidence; add cluster-bootstrap/session-level intervals and independent capture periods. These are planning estimates, not a ready-to-ship result.

Keep calibrated risk thresholds separate for ALLOW, REVIEW and BLOCK. Optimize thresholds against *cost of false punishment and missed severe harm* on development only. A model-reported confidence is not a safety guarantee. REVIEW is the safety valve for genuine uncertainty **when service is available**; fail-open on service outages remains Policy v1, and automated punishments stay disabled unless separately authorized. A detected incident may need human staff handling even when no immediate auto-BLOCK is justified.

## 9. Controlled experiment matrix and GPU gate

Pre-register all candidates against **one versioned source/split manifest**:

| ID | Model inputs/output | Variable changed | Decision |
|---|---|---|---|
| B0 | Existing TF-IDF and current W25/W12 baseline | None; inference only | Establish true start |
| E1 | Existing lightweight encoder, target-only direct policy output | Admitted independently labeled real+audited synthetic | Tests value of better labels |
| E2 | E1 with short chronological context | Context only | Keep if false-block and full-decision improve |
| E3 | E2 with controlled hard-negative/minimal-pair sampling | Curriculum/weights only | Keep if no SAFE regression |
| E4 | E2 or E3 with fact heads + deterministic resolver | Decision architecture only | Keep only if gold fact/decision errors improve |
| E5 | Winner + train-only domain adaptive pretraining | Domain adaptation only | Run last, if earlier evidence justifies cost |

E1/E2 comparison must use **matched data/seed/budget**; a target-only baseline trained on old data is a separate historical reference, not a causal ablation. Keep minority-class evaluation independent of resampling. Use 42/138/2026 for finalists; record tokenizer/checkpoint hash, code SHA, loader seed, trainable parameters, epoch/batch/accumulation, maximum tokens, LR/scheduler, precision, optimizer, train sample weighting, privacy authorization, checkpoint sizes and run logs.

Use development-only early stopping with a predeclared composite metric favoring **full-decision exact match subject to false-block and severe-recall constraints**. No single averaged F1 should choose the winner. Limit each exploratory run to a fixed budget/step count and abort on out-of-memory, invalid checkpoint hash, training-data leak, unstable loss, or clearly worse harmful-error rate. Profile on the real target host with a **small bounded synthetic batch only**, without loading private corpora, before estimating VRAM, RAM, disk, time and rental cost. Send the exact estimate and stopping rule to the owner and **wait for authorization**. No large runs, model downloads or paid GPU orders are approved by this document.

## 10. Acceptance checklist for the coordinator

- [ ] Source use rights, redaction-vocabulary preservation, deletion propagation and per-source approval confirmed.
- [ ] PR #52 final-byte QA and independent semantic corrections complete; no candidate data auto-promoted.
- [ ] Split connected components cross sessions/mirrors/families; near-duplicate queue adjudicated.
- [ ] Prospective never-scored real-traffic test captured and sealed **before** modeling.
- [ ] Annotator independence, critical double-review and owner-policy null treatment verified.
- [ ] Natural conversation context validated with no future text and no cross-scope leakage.
- [ ] B0–E3 and optional E4/E5 recipe, thresholds, stop rules and costs precommitted.
- [ ] Session-cluster uncertainty, critical slice lower bounds, SAFE false blocks and staff REVIEW workload reported.
- [ ] W25 pinned results preserved; W20/W27 never used for iterative selection.
- [ ] Owner separately approves compute, acceptance and deployment; no automatic punishments.

## References

- Existing project: policy/POLICY-v1.md, docs/DATASET-SCHEMA.md, docs/data-v2/README.md, docs/data-v2/ANNOTATION-RUBRIC.md, docs/data-v2/TRAINING-ORDER.md, PRs #48/#52/#54, issue #53.
- scikit-learn grouped cross-validation: https://scikit-learn.org/stable/modules/cross_validation.html
- Gururangan et al., *Don't Stop Pretraining*, ACL 2020: https://aclanthology.org/2020.acl-main.740/
- Warner et al., *ModernBERT*, ACL 2025: https://aclanthology.org/2025.acl-long.127/
- NIST AI Risk Management Framework resource center: https://airc.nist.gov/

**Review limitation:** This is an independent methodological assessment, **not** an independent adjudicated second-pass label audit; that requirement remains open. Proposed numbers and context caps are experiment starting points, not new owner moderation policy.
