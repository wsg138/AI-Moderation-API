# DATA-V2-16 — 9,000 synthetic cases: verification Stage 1

**Status: automated inspection, not semantic verification, not training approval.**
Inputs are exclusively the existing SHA-256 pinned, public, synthetic batches
G10–G27 (18 × 500 = 9,000). No private player chat, moderation decisions,
hidden prompt records, actual account links, owner review crosswalks, or
evaluation holdouts are imported or published.

## Why Stage 1 exists

The existing dataset quality checks, duplicate/family audit and triage queue
already detect a variety of issues, but **passing schema QA and having two
AI reviewers agree are not human adjudication**. To begin the actual
verification campaign, this stage composes the existing audits and adds
a missing high-risk signal: two examples with the *same exact target-time
visible input* but different **any outcome field** are sent for review.
Those differences may be legitimate source metadata/policy contexts that
aren't captured in visible input; they are **review hypotheses**, not
automatically corrected labels.

Checked dimensions: semantic label, message action, review priority,
strike, containment, mute duration, support flow and reason codes.
No flag overwrites any original source annotation.

## Run the full automated first pass

```sh
python -m tools.data_v2.corpus_verification_stage1
```

The command checks all 18 per-batch dataset QA reports, final-byte SHA-256
source pins, all 9,000 IDs and line order, known exact/near
overlap groups, and existing priority/flag rules. Output is **aggregate
JSON only**: scanned records, source batches, duplicate/overlap group
counts, conflicting exact-input proposed outcomes, priority counts and
size/composition of the first review wave. It always says:

```json
{"independent_reviews_completed":0,"semantically_verified_records":0,"training_eligible":false}
```

Actual values for conflict and priority counts must come from the code
executing against the 9,000 sources; do not invent estimates.

## First blinded independent review wave

Select exactly **180 cases**, **10 from each of 18 source batches**:
- Aim for 4 existing policy/structural-conflict candidates per batch,
  3 high-impact/safety candidates, and 3 routine/negative controls.
  If a batch lacks one tier, fill with other unselected candidates.
- Deterministic SHA-256 candidate ranking makes replay repeatable without
  relying on random seeds or modifying the original data.
- The sampler prefers distinct **declared family IDs** and distinct
  normalized target texts, globally, to avoid review repetition. This is
  a convenience for diverse blind review, *not* proof that cross-batch
  family/semantic leakage has been fully resolved.
- Reviewers receive **only target-as-of-visible messages**, platform
  and channel profile, and an opaque HMAC packet ID. They do not see the
  candidate's batch name, original semantic label, action, strike,
  reasons, post-target chat or the coordinator crosswalk.
- **First wave is now frozen:** the 180-case selection was distributed to
  private reviewers and received owner action-only judgments. The exact ordered
  selection SHA-256 is
  `bec3d820706c4b8e42c9e17ce1e8455bb38811d30c25d293c27e12a4f1350407`
  (hash of comma-joined case IDs), with 34 policy-risk, 72 high-impact and
  74 routine cases. Changing these IDs would invalidate existing private
  packets, crosswalks and reviews. Any improved selector must create an
  explicitly **versioned new wave**, never silently regenerate wave 1.
- **Tier quotas are targets, not guaranteed composition.** Some source batches
  lack entire tiers; in G11, the six policy-risk records represent only two
  distinct declared families, so a four-case strict unique-family policy
  quota is impossible there. G23 also has a shortfall despite seven raw
  policy candidates; constrained tier allocation remains a known future-wave
  improvement. No quota shortfall converts a candidate into gold.
- Owner and independent reviewers may not train or test the AI with
  unadjudicated cases. An independent answer must include all needed
  Policy-v1 dimensions and evidence provenance before any future
  promotion decision. Existing 86 owner action-only reviews are not
  automatically upgraded to full semantic verification.

## Prepare private files (only in approved local environment)

```sh
export ENTHUSIA_REVIEW_PACKET_KEY="<unique high-entropy secret kept outside Git>"
python -m tools.data_v2.corpus_verification_stage1 \
  --packet-out /private/reviewer/round1-blind.jsonl \
  --crosswalk-out /private/coordinator/round1-crosswalk.jsonl
```

Do not paste a review key into logs or upload the private map to GitHub.
Use appropriate secure secret entry for your OS; the `export` line is
schematic, not the preferred way to handle secret storage.
Both paths **must be outside** Git checkout and must be in separated
reviewer/coordinator directories; existing output files cannot be
overwritten. The source map is private. Reviewer files contain synthetic
chat text, not private server chat; keep them out of public Git anyway
to avoid answer contamination during independent review.

## Required next stages

1. Execute Stage 1 and record its true aggregate findings. Triage each
   outcome conflict and high-impact candidate, rather than silently
   auto-correcting original labels.
2. Run two **independent, blinded** review passes on the first 180
   (separate prompts/providers if available, or separately assigned
   trained human reviewers). The candidate answer and prior reviewer
   answer must not be revealed during independent judgment.
3. Validate reviewer outputs, flag disagreements, and obtain human
   adjudication where policy meaning or serious safety is disputed.
   Both reviewers agreeing does **not** automatically promote a case to
   human-approved gold or a production moderation rule.
4. Inspect **false blocks** among benign and Minecraft-specific chat;
   audit action **and** semantic, strike, mute, support and timing
   fields. Estimate remaining errors with an unbiased separate
   stratified sample, not only suspicious items.
5. Keep all candidates in the training quarantine until approved
   human adjudication, source provenance, family-safe train/test
   partitioning, and the existing formal training admission gate
   are demonstrably satisfied. The 180-case set is a review wave,
   **not** a test holdout or an approved training set.

There is no live service hook, model training, merge, auto-punishment or
production rollout in this stage.
