# Data/Model v2 — training order, acceptance gates, and work queue

This file is an **execution plan**, not approval to run jobs. A gate is complete only when its evidence is saved, reviewed, and referenced by a GitHub issue or PR. Do not run heavy local work or purchase cloud compute without informing/obtaining the owner's approval first.

## Sequencing and ownership

| Stage | Work / goal | Required artifact | Exit gate |
|---|---|---|---|
| **A. Source organization** | Reconcile W11, PR #52, private real logs, licenses/consent, access rights and schema versions | Versioned source registry + private provenance manifest | Every source has known ownership, authorized use, privacy grade, policy/schema versions |
| **B. Real-chat extraction** | Preserve chronological messages, speaker aliases, channel, timestamps/time gaps, target index, parser errors, and original source group | Reproducible parser + PII scrub + utility/leak tests + private manifest | Text is semantically useful and approved for intended local/cloud use; no false 'fully anonymous' claim |
| **C. Split freeze and contamination** | Group real sessions/date/server and synthetic families; audit exact and near-duplicates across sources/splits | Manifest: train/dev/heldout IDs, immutable hashes held privately; public aggregate overlap report | No family/cross-session spillover; W20/W27 unaccessed and untouched; sealed real holdout excluded from iteration |
| **D. Independent labels** | Sample normal chat, hard negatives, severe candidate cases, ambiguous context; double-review critical labels | Annotation rubric, adjudicated labels, disagreement log, label provenance | Labels are independently policy-consistent; model-only labels never auto-promoted |
| **E. Synthetic candidate acceptance** | QA G10–G27 *final JSONL bytes*, audit false labels, near-duplicates, context realism, and Codacy | Fresh 18 QA reports, independent review ledger, fixed/reasoned findings | PR #52 approved explicitly; no test contamination |
| **F. Baseline & policy resolver** | Freeze semantic-fact schema; version deterministic label/action/strike/support routing; compare current DeBERTa and baseline | Tests including gameplay/IRL contrasts, self-harm/support, reported slurs, private-info, staff abuse | All rule/contract tests pass, cost and privacy gate accepted |
| **G. Bounded supervised experiment** | Only after owner approval: fine-tune one candidate using admitted train split; include real/synthetic weighting and controlled rare-class oversampling | Pinned recipe, SHA, seeds, datasets/hashes, checkpoints, reproducible costs, predeclared metrics | Independent development metrics improve meaningfully *without* increased wrongful BLOCKs |
| **H. Optional domain adaptation** | Only if needed and worth compute: compare continued MLM-style Minecraft-domain adaptation against the already-trained encoder / standard fine-tuning | Strictly train-only unlabeled corpus and ablation report | Measured benefit relative to run cost; no heldout text for model selection |
| **I. Multi-seed + evaluation freeze** | Repeat promising candidates across seeds; calibrate on dev; lock architecture/policy/thresholds | Multi-seed table, exact-decision errors, critical-class confusion, false alarms / 1k SAFE, abstention/latency | Pass predefined floors across seeds with acceptable variance |
| **J. Independent acceptance, then shadow** | Use heldout/W27 per their own authorization and preserve W20 for final independent acceptance; shadow-only runtime review first | Versioned acceptance report and separate owner production decision | No merge/deployment/automatic punishments until explicit approval |

**Important real-heldout caveat:** the 552 real-review holdout candidates were assigned to their split *after* the 33,714-example model-based mining/scoring pass. They are excluded from further development, but are not pristine never-mined external acceptance examples. A **new prospective never-scored cohort** is needed before claiming 99% real-world accuracy. W20 and W27 remain reserved as specified by their own frozen protocols.

### What to train, and in what order

1. **No new GPU job yet.** First fix bad or missing labels; 9,000 questionable labels can be worse than 1,000 reliable ones.
2. **Reproduce baseline** on the approved v2 train/dev split. Record the current encoder + router, per-class confusion, and policy-derived exact decisions.
3. **Fine-tune a pretrained language model** on *independently labeled* balanced real + accepted synthetic contexts. Do not train a new encoder from scratch. Use the known lightweight model first (DeBERTa-xsmall), with fixed checkpoints and early stopping.
4. **Contrastive hard-pair curriculum:** similar visible phrases with different contexts; keep natural preceding SAFE/gameplay chat, not artificial streams of harmful lines. Keep entire source session and synthetic family in one split. Train ordinary+hard examples together; optionally increase hard-pair sampling in later epochs, while monitoring false-positive rate.
5. **Facts first, policy second.** Evaluate a fact-based model against directly predicting the six outcome fields. Policy-derived outputs must be consistent, versioned, and covered by golden-policy tests. Model confidence alone does not establish safety.
6. **Domain-adaptive pretraining is an ablation, not a prerequisite.** Try only after a labeled baseline establishes remaining deficits. Massive unlabeled logs alone do not magically create trustworthy supervised labels. Use *train-eligible* unlabeled real chat only and assess if gains justify cost.
7. **Never simultaneously change architecture, data mix, prompt, and threshold.** Change one factor per reproducible experiment and compare against the same untouched development distribution.
8. **Freeze and test** only after robust results across seeds and policy resolution. W27/W20 remain outside routine iteration.

### Class balance and natural context

- Keep a naturally sampled real-chat slice for honest SAFE prevalence and false-positive measurement.
- Oversample rare critical classes in **training only**, with deduplication and diverse hard negatives; do not make the test set artificially balanced and call its accuracy production accuracy.
- Inspect hard categories separately: grooming, doxxing, blackmail, sexual-minor, threats, directed self-harm instruction, first-person self-harm support, slur use versus quoting/reporting, and confusing Minecraft terms.
- Label a **target message** with context available **before** that target. Preserve other normal users' messages. Speaker aliases may be per-window; preserve whether consecutive messages came from the same participant.
- Ensure chronological sessions are real: no stacking independent synthetic offense prompts as if adjacent real chat. Synthetic minimal pairs should each be complete plausible scenes, not hundreds of isolated violence sentences.
- Do not infer an abuse label from source search terms or from a previous model's score.

### Evidence needed to claim ~99% accuracy

The objective is not merely 99% precision on the messages the model chose to block. Report:

- `action_accuracy`: exact correct ALLOW / REVIEW / BLOCK, denominator all adjudicated test targets.
- `semantic_accuracy` and per-category confusion.
- `whole_decision_exact_match`: policy-derived action, label, review, strike, containment and support all correct together.
- `block_precision`, `block_recall`; critical class/slice recall and catastrophic routing errors.
- `false_blocks_per_1000_benign` and percentage referred to human REVIEW; report end-to-end latency.
- Prevalence-weighted traffic results, unseen-text and unseen-session subsets, and confidence intervals/sample counts. Seven correct rare-class items cannot establish 99% class-level reliability.
- A traceable error log including staff overrides, context boundaries, and policy ambiguities. Human review adjudicates contested labels.

## Work queue — ready for lightweight parallel review, NOT dozens of manually launched chats

| ID | Owner/workstream | Next deliverable | Blocker |
|---|---|---|---|
| DATA-V2-01 | Dataset QA / PR #52 owner | Regenerate all 18 final-byte reports, reconcile G18/G25/G27 counts, investigate 53 Codacy findings | PR #52 |
| DATA-V2-02 | Independent policy reviewer | Second-pass label audit of G10–G27; prioritize safety classes and SAFE false positives | DATA-V2-01 final contents |
| DATA-V2-03 | Privacy/parser reviewer | Local-only PII leak and vocabulary-preservation tests for v4 real chat; permission review before any external access | Source authorization |
| DATA-V2-04 | Split/contamination reviewer | Frozen grouped split, real/synthetic near-duplicate audit, heldout exclusions | No W27/W20 access |
| DATA-V2-05 | Label/adjudication coordinator | Ground-truth real-chat review rubric and 2-reviewer protocol; no unverified Qwen admission | DATA-V2-03 |
| DATA-V2-06 | Modeling coordinator | Semantic facts/policy resolver ablation and benchmark definitions, no training yet | Consistent policy decisions |
| DATA-V2-07 | Experiment operator | Bounded costed training proposal: device, RAM/VRAM, runtime estimate, resource cap, rollback, reproducibility | Explicit owner go-ahead after earlier gates |

### Resource approval contract

Before starting a substantial local CPU/GPU workload, model download, large corpus re-parse, or paid GPU run, send the owner: **what will run, estimated duration, expected CPU/GPU/VRAM/RAM/disk, anticipated money cost, output location, and exact stop/cancel condition**. Wait for permission. Documentation, small source/metadata reads, and lightweight static inspection require no dedicated heavy compute.

## GitHub PR readiness

- Keep W25 PR #48 pinned, experimental, unmerged.
- PR #52 currently **not approved for training**; its overview matches some final data, but individual QA reports became stale after corrections (G18, G25, G27 verified). The automated QA tool's '0 errors' is structural, not independently adjudicated label truth.
- Track acceptance steps as issues/PR comments; do not silently merge candidate data or copy private raw chat into the public repo.
- Source registry and this plan are proposed organizational metadata. A green documentation PR is not a green training gate.
