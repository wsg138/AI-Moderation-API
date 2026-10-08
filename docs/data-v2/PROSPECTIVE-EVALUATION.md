# DATA-V2 — prospective, never-mined evaluation freeze protocol

**Status:** proposed protocol, not consent to collect logs or an approval to access server/private chat, run models, or deploy moderation. Owner sign-off and data-source authorization are required before execution. Tracks readiness issue #53.

The current 552-record real-review holdout is **not** a pristine untouched benchmark: model-based candidate mining happened before its date-grouped split. W20 and W27 remain protected separately. This document defines a *new* future evaluation cohort that is frozen **before any candidate selection, model scoring, labeling-assisted tuning, or synthetic prompt design**.

## 0. Preconditions (no collection until all are met)

- Owner approves the exact source(s): server-owned Minecraft public logs, authorized Discord channels, or explicitly opted-in client logs. Review server notices, user expectations, minors' privacy, and necessary consent/rights; do **not** assume all third-party messages are licensed for cloud labeling, public upload, or training.
- Designate a privacy operator and an independent evaluation custodian. Review where encrypted raw data can be stored, access controls, retention/deletion and opt-out processing. **Keep raw texts, player names, linkage keys, source paths, per-record labels, signatures, and private hashes off public GitHub.**
- Fix the canonical Policy-v1 revision and evaluator rubric. Unresolved policy fields must stay null/unknown, not default to safe or punitive values. Policy amendments after the freeze require an explicit new evaluation version and audit trail.
- Define a prospective cutoff **later than the approval date**. Do not retrospectively pick a flattering time period or mine an already-reviewed log archive and call it independent.
- Commit a public-safe **pre-registration receipt** to GitHub: cutoff rule (not raw private timestamps), eligible channel profiles, selection algorithm/version, sampling fractions, exclusion rules, split/holdout conditions, reason for cluster grouping, validation metrics and confidence-interval method. The private custodian stores exact capture period and any secret random seed.

## 1. Separate two different evaluation products

**A. Natural-traffic cohort** — used for deployment-relevant action accuracy, false BLOCK per 1,000 true ALLOW messages, false strike/mute consequences, REVIEW burden, and prevalence. Sample messages independently of content/model scores: preferably uniform random eligible moderation targets from time-bounded streams with predeclared rate, or full enumerated sessions then a seeded target sample. Include all boring chat. If sampling is stratified by channel/server/time, preserve inclusion probabilities and report correctly weighted totals. Retain denominator counts and missing/excluded reasons privately.

**B. Critical challenge suite** — independently selected/enriched credible threats, self-harm instructions/disclosures, sexual-minor, grooming, doxxing, blackmail, actual-slur use (including Policy-v1 quote/report rules), evasions, staff abuse and gameplay/IRL contrast pairs. Selection may be targeted, but **never mix its enriched prevalence into natural-traffic accuracy**. Do not expose challenge examples during model selection. Rare classes need enough adjudicated items to report an informative per-class interval, not just an ungrounded point estimate.

The two cohorts may share only the protocol, not underlying target/context messages. Overlap is a leakage defect and must be resolved before evaluation.

## 2. The irreversible order of operations

1. **Approve and start fresh capture:** use only authorized prospective sources. No v4 historical corpus, earlier 33,714 scored candidates, W20, W27 or 552 selected real holdout as a substitute.
2. **Ingest once and register:** assign private random IDs and a source/session/incident group; record trust/rights and capture metadata privately. Avoid embedding usernames in public IDs. Preserve speaker consistency in private source mappings.
3. **Select at source level without semantic inspection:** deterministic, precommitted sampling from eligible incoming targets, grouped by session and linked event. Do not filter by apparent toxicity, keyword, previous-model confidence, or desired class.
4. **Create context 'as of' target time:** at most a predeclared number of prior messages and time horizon (initial research proposal: up to eight earlier messages and 120 seconds), target latest; strictly no future text or future-derived metadata. Preserve conversational scope, message order, channel/profile, trust state and private linkage to source.
5. **Apply privacy controls locally:** replace speaker IDs and high-confidence in-text identifiers without corrupting ordinary game words; detect PII leaks and metadata leakage. Record exceptions and rights restrictions. Private source must be withheld from outside reviewers until review-specific transfer is separately authorized.
6. **Seal before scoring:** evaluation custodian writes immutable private record manifest, ordered target IDs, digests of raw/normalized/context windows and grouped split assignment, code SHA, rights/PII review revision, capture rule, and private seed/selection receipt. Sign or otherwise integrity-protect it under the organization's existing trusted process. Only publish aggregate counts and a non-linkable receipt ID in GitHub.
7. **Blindly label:** at least two independent qualified reviews of critical/safety and disputed targets, with owner-policy adjudication. Reviewers do not see model output, generator category, earlier training label, or each other's answer before their first judgment. Track the adjudication version and null outcomes. Normal randomly sampled SAFE and ambiguous messages *must* also be reviewed for honest prevalence.
8. **Freeze gold and prediction contract:** no inference against the cohort until policy, schema, model checkpoint, router thresholds and all evaluation scripts have been locked. Custodian verifies both frozen input manifest and pre-registered output fields.
9. **Evaluate once per authorized candidate:** score each target only with information available at that point in time; publish aggregate metrics, counts, confidence bounds, exclusion decisions and versioned reproducibility receipts. **Do not reveal per-message errors to model developers and then keep calling the same cohort never-seen.** Any subsequent tuning makes it a development set; collect a new future cohort for final acceptance.
10. **Deletion or correction:** honor source removal requests, invalidate derived examples and affected evaluation conclusions, record revocations privately, and rerun only under an explicitly revised evaluation release. A result is not permanently valid after its underlying evidence is withdrawn.

## 3. Leakage / anti-gaming checks before acceptance

- Group by source conversation/session/incident; if a mirrored message appears on Minecraft and Discord, keep the entire connected component together. Any context overlap across train/evaluation is contamination.
- Detect exact normalized target duplicates, overlapping source-message IDs, near-duplicate/paraphrase families and augmentation ancestry. Common low-information text (e.g. 'gg') is not by itself proof of a leak; judge source-event overlap separately.
- Time-boundary embargo prevents a recent training session from bleeding into a newly captured evaluation through overlapping context.
- Do not use **test** model scores to mine hard negatives or generate synthetic close variants; do not tune abstention/BLOCK thresholds on the cohort; do not peek at sealed future labels.
- Show total eligible capture count, missing/deleted count, sampled count and labeled count in aggregate, so selective filtering cannot quietly hide difficult chat.

## 4. Predeclared metric outputs

Report all raw denominators, point estimates and appropriate uncertainty intervals:

1. `action_accuracy` across gold ALLOW / REVIEW / BLOCK, with full confusion matrix.
2. `whole_decision_exact_match` across all **known** policy-resolved dimensions (label, action, review priority, strike, containment, support); report the complete-decision fully-known denominator **separately** from partial-field matches and unresolved null counts.
3. `false_blocks_per_1000_gold_ALLOW`, wrongful-strike rate and false punishments from the **natural-traffic** cohort; also report how many genuine safety cases route to REVIEW.
4. `BLOCK_precision` and `BLOCK_recall` at the observed prevalence, severe-class recall and worst-case critical confusion.
5. `REVIEW_rate`, false review burden per 1,000 benign messages, staff minutes/day, coverage/abstention, p95/p99 inference latency and failure-to-ALLOW service behavior.
6. Slices: channel/platform, unseen sessions/servers, novel-text, PvP context, quoted actual slurs, minors/unknown ages, split threats, repeated harassment.
7. Session/incident-cluster-aware intervals (e.g. clustered bootstrap) and uncertainty from sampling weights when applicable. Do not describe correlated chat messages as independent trials.

**Planning check, not a policy threshold:** With 0 wrongful blocks among *n independent* genuine ALLOW targets, a one-sided 95% error upper bound is approximately `3/n`. To upper-bound wrongful BLOCK at 0.5 per 1,000, about **6,000 independent gold-ALLOW targets** would be needed; correlated sessions and heterogeneous channels generally increase the effective sample requirement. Before scheduling collection, estimate human-review burden and obtain explicit approval. Do not infer 99% across rare categories from a small challenge set.

## 5. Required handoff artifacts / approval gate

Public GitHub holds only:
- The pre-registration design and approved policy/code SHA (no private chats);
- A non-reidentifying evaluation release label and release date;
- Aggregate counts by channel/label, sampling design, exclusion/withdrawal counts and CI method;
- Final signed-off aggregate scorecard, interpretation and any reasons the result is inconclusive.

Private custody holds:
- Source permission and consent/rights evidence, raw and redacted capture records, capture-period boundary, source mappings, incident/session/mirror links, sealed original target IDs and digests, reviewer decision records, consent/deletion records, private seed, and frozen model/policy/threshold hashes.

**Exit decision:** a frozen prospective cohort is available only after all steps are verified by a custodian distinct from day-to-day model tuning. Creating this document, opening a GitHub issue, a passing structural test, or collecting a large pile of unlabeled chats is **not** evidence that the independent benchmark exists or that an AI model is fit to auto-punish players.

## Suggested next owner's decision (not needed yet)

When the source authorization/collection stage becomes the immediate blocker, present the owner a short approval request with proposed server/channel scopes, privacy notices, retention and reviewers, collection start/cutoff, expected number of targets, labeling effort, storage, and **compute/time/money cost**. Wait for explicit authorization before real-data collection or any expensive processing.
