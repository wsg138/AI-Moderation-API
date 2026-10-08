# Data/Model v2 — training readiness program

**Status:** planning / dataset-acceptance work; **not authorized to train, deploy, merge model code, or enable punishments**.
**Scope:** Enthusia AI moderation across Minecraft and Discord.
**Public repository rule:** this document contains counts and process only. No raw/player chat, usernames, private annotations, secrets, or model-visible examples from private sources belong in this repository.

This program is the follow-up to W25 Phase-A screening; do not replace the pinned W25 experiment or treat its development-set near-pass as production accuracy. The main source of truth for Policy v1 remains the accepted policy and `docs/DATASET-SCHEMA.md`; these documents organize work rather than silently revise policy.

## Why this is changing

- W25's best official DeBERTa-v3-xsmall seed-138 model achieved about **93.7% ALLOW/REVIEW/BLOCK action accuracy** and **77.0% six-field exact-decision accuracy** on its 991-record development slice, not the owner's ~99% goal.
- A local, development-fitted ExtraTrees action-router prototype did narrowly pass W25's precision/recall gates for a particular seed, but was close to the thresholds and was not a multi-seed or independent acceptance result.
- A local Minecraft-log inventory found approximately 1.52M probable chat/log lines. Its v4 parser produced **587,610 player-message candidates** across 336 sessions spanning late 2024 to October 2026. **These are not 587,610 verified clean labels.**
- An initial active-learning pass scored **33,714** deduplicated real context targets and prioritized **2,831** windows for review. Of these, 2,279 are in train/development and 552 are **now excluded from further development** as a real-log holdout candidate. **Caveat:** the split was made *after* the mining/scoring pass; these 552 are not a pristine never-inspected independent benchmark. They must not be used to substantiate a 99% acceptance claim.
- A local Qwen3 8B fact annotator was unreliable on owner-policy examples (10/21 semantic-label matches in a *prompt-contaminated consistency check*). Its hypotheses were **not admitted as training truth**.
- PR #52 contributes **9,000 additional synthetic candidate records** (G10–G27). Its independent semantic review is missing; stale per-batch QA reports and Codacy findings require resolution first. **PR #52 is not training-eligible yet.**

See [source registry](source-registry.json) and [training order / gates](TRAINING-ORDER.md). For outside dataset-review input, see [collaboration questions](COLLABORATOR-REVIEW.md).

## Nonnegotiable principles

1. **Real chronology instead of toxicity stacks.** Keep everyday SAFE chat, PvP, advertisements, ordinary conversations, and occasional harmful-looking lines in their actual observed order. Do not assemble sequences of unrelated slurs/threats back-to-back. Every supervised example has a single marked target; context consists of earlier available messages and relevant metadata, *never future chat*. Use meaningful inactivity/session boundaries rather than connecting unrelated periods. Record the extraction parameters and version.
2. **Separate use cases.** Unlabeled real chat can support domain-language research and candidate discovery. Supervised learning requires independently verified labels. Synthetic data fills specific rare gaps, but is not proof of real-world reliability. Model-generated pseudo-labels remain hypotheses until adjudicated.
3. **Preserve provenance.** Track source, consent/license, parser version, policy version, privacy status, date/session or family group, human-review history, augmentation lineage, intended use, and split assignment. Keep any sensitive manifest values (raw paths, identities, private hashes, original chat) exclusively in private storage.
4. **Anonymization is not a pass/fail adjective.** Replacing usernames in the speaker column is not enough; in-text username mentions, coordinates/IPs, emails, private location, accidental PII, and metadata remain risks. A previous aggressive anonymizer corrupted Minecraft vocabulary, so improved redaction requires both leak tests **and** utility tests. The current real-chat v4 data is **local-only; not cleared for external/cloud labeling**.
5. **Train, select, and evaluate separately.** Split real chat by leakage-resistant date/session/server clusters; group synthetic paraphrases/minimal contrast pairs by family. Detect exact *and semantic/near* overlaps across sources. Never fit thresholds, select models, create prompts, adversarially augment, or train on W27 or W20. The new real-log holdout is also sealed against development iteration.
   **Independent-test caveat:** the new real-log holdout was assigned after model-based mining. Keep it sealed going forward, but obtain a genuinely prospectively frozen, independently labeled, never-mined evaluation cohort for external-validity claims; do not substitute W20/W27 or reuse their data for iteration.
6. **Uncertainty and safety.** The classifier should learn semantic/context facts; a deterministic, versioned policy resolver produces enforcement recommendations. Uncertain/contradictory critical cases route to human review. This does not authorize automatic mutes, bans, message deletion, or any production change. The existing fail-open chat-availability contract remains.
7. **Truthful accuracy reporting.** Track three-class action accuracy, category accuracy, whole-decision exact-match, BLOCK precision/recall, severe-class recall, false-positive rate per 1,000 benign messages, review/abstain rate, latency, and calibration. Report performance on all held-out examples *and* unseen-text / unseen-session subsets. Do not promise 99% or report AI-generated labels as accuracy.

## Source classes

| Data class | Typical contents | Eligible now? | Intended use |
|---|---|---|---|
| Accepted W11-era synthetic G01–G09 | 4,500 labeled synthetic examples, accepted in previous program | **Re-audit for v2** | Controlled supervised baseline, once split/policy consistency checked |
| PR #52 G10–G27 | 9,000 newly generated synthetic records across 18 domains | **No** | Candidate supervised augmentation after final-byte QA + independent policy review + family/leakage audit |
| Real Minecraft client chat v4 | 587,610 parsed local messages with chronological history | **No, local/private only** | Domain study, realistic SAFE distribution, candidate selection; verified subsets later for training |
| Real review queue | 2,279 train/dev priority windows; 552 sealed holdout windows | **No verified labels yet** | Carefully adjudicated development labels, with sealed holdout excluded |
| W25 model predictions / Qwen pseudo-labels | Encoder/router scores and local annotator facts | **No** | Candidate ranking and disagreement discovery; never automatic gold labels |
| Frozen W27 / W20 | Protected acceptance data | **Never for development** | One-time predefined acceptance use after design freeze; W20 last |

## Coordination rules

- GitHub is the source for **code, policy, schemas, sanitized status, approval checklist, and reproducible recipes**.
- Private storage is the source for **real chat, consent records, identity redaction keys, private per-record annotations, training artifacts, and sensitive manifests**. Do not include actual paths containing usernames or private sample text in public PRs.
- PR #48 remains W25 evidence and should not be silently repurposed. PR #52 remains a separate candidate corpus.
- **No expensive machine work without asking the owner first:** before sustained GPU training/inference, mass scans, large downloads/model loads, domain-adaptive pretraining, cloud rental, or other materially heavy operations, propose the command, expected resources, rough duration/cost, stopping rule, and output. Lightweight GitHub documentation and narrow metadata checks are permitted.
- Do not ask the owner to dispatch dozens of worker chats. One coordinator should maintain a manifest/queue with resumption, single-writer leases, checkpointing, automatic QA, and clear owner approval boundaries.
- External collaborators may help with taxonomy, data splitting, audit checklists, and reviewed *synthetic* examples. Do not give them private player logs or a third-party model access to them without explicit source permissions and privacy review.

## Immediate readiness decision

**NOT READY FOR GPU TRAINING.** Resolve PR #52 final-data QA and code alerts; implement a privacy-safe and independently labeled training subset from real chat; perform cross-source and split contamination checks; document the model's semantic facts and deterministic policy outputs; freeze a measurable development recipe and evaluation plan. Only then ask for a bounded, owner-approved training experiment.
