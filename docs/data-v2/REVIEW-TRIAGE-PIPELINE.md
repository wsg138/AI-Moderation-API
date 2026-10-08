# DATA-V2-03 — Candidate review triage queue (draft)

**Status: source-pinned candidate triage only. This is NOT verified training data.**
Tracking: [#53](https://github.com/wsg138/AI-Moderation-API/issues/53),
[#57](https://github.com/wsg138/AI-Moderation-API/issues/57).
Stack: draft #66 integration; no production merge.

## Why

Owner Round 2 and Round 3 quick reviews showed a substantial mismatch with some
existing synthetic candidate **actions**. Their action-only decisions are
authoritative **for those records**; they do not establish semantic labels,
strikes, containment, priorities, safety flows, a population error rate, or
a model score. **Keep owner answers, reviewer identities, private opaque-ID
crosswalk and written notes outside the public repository.** None are imported
by this first-pass queue.

A random 50-case quiz is not an efficient way to review 9,000 source records.
Instead we need a complete, source-locked, nonadmitting triage manifest to
prioritize heterogeneous or internally inconsistent candidate families.

## Implemented

`tools/data_v2/triage_queue.py` reuses the existing G10–G27 SHA-256-pinned
candidate loader and deterministic source family audit. It requires **exactly
18 public synthetic batches / 9,000 records** and refuses source-byte drift.
Every case appears once in the coordinator queue with:

- Public synthetic example ID, exact source JSONL path, pinned SHA-256,
  source-line number and source-commit identifier.
- Existing **candidate** action and semantic label, never called gold.
- Deterministic suspicion flags and one of three triage buckets:
  `01_policy_conflict_candidate`, `02_high_impact_candidate`, or
  `03_stratified_audit_candidate`.
- Evidence links to exact as-of-target input, same target wording, declared
  source family, broad stem, or near-wording groups, marked only as
  **overlap evidence**, not semantically equivalent label-sharing groups.
- `label_status=candidate_unverified`, `review_scope=no_owner_action_imported`,
  and hardcoded `training_eligible=false`.

An **identical target-time input with different candidate actions** is explicitly
prioritized for manual investigation. A repeated target with different earlier
context, channel or platform is *not* automatically declared contradictory.
The source fields used as triage hints (label, reason codes, family ID, action)
remain untrusted proposals. All text inspection uses the as-of-target
projection, never post-target replies; post-target presence is recorded only
as a structural flag. The collector performs no model inference, training,
semantic adjudication, owner-answer import, source edits, group-action
propagation, or punishment changes.

Priority buckets are **work queues**, not numerical model risk scores.
The number of findings is not a production accuracy estimate.

## Run (local or GitHub checkout with existing public sources)

To see **aggregate-only** status without writing a queue:

```sh
python -m tools.data_v2.triage_queue
```

To create a **private coordinator-only** manifest for subsequent review
work, specify a *new* path outside the repository:

```sh
python -m tools.data_v2.triage_queue \
  --coordinator-queue-out /tmp/enthusia-coordinator/triage-queue.jsonl
```

The output writer refuses an existing destination and paths inside the
checkout. Protect this file separately from any blind reviewer packets.
The command prints only aggregate counts, no case-level IDs or messages.
The optional file is not a blind reviewer packet; it contains source actions,
labels, and overlap provenance and must **never** go to reviewers.

## Human review workflow (next implementation steps)

1. **Version policy boundaries.** Reconcile owner action decisions separately
   from underlying semantic labels; note conflicts such as apparent threats
   involving real-life proximity, reliably evidenced minors, dangerous
   instruction requests, languages, and self-published contact information.
   Do not silently turn a language preference into a semantic-harm label.
2. **Plan representative review assignments.** Build a new sampled blind
   packet set based on priority queue plus random coverage of the routine
   set. Record seed and inclusion probabilities. Hide the candidate labels,
   category, owner answers, family flags, group rationale and later context.
3. **Only propagate an established versioned rule to an entire cluster if
   equivalence is affirmatively demonstrated**, including platform and
   earlier context. Shared family stem/wording or matching topic alone are
   insufficient; reject a heterogeneous group and inspect outliers.
4. **Audit suggested corrections** within each genuinely homogeneous family
   and explicitly count exceptions/failed samples. Safety/false-punishment
   candidates require individual review where grouping is unsound.
5. **Maintain a separate acceptance gate.** Action-only owner decisions
   cannot fill missing label/strike/mute/support fields. Admit a record only
   with documented scope, verified policy interpretation, source rights,
   privacy clearance and leakage-safe split. Existing formal independent
   reviewer protocol applies to full semantic/severity records unless
   deliberately and explicitly revised.
6. **Freeze unseen prospective evaluation**, assess false BLOCK/strike/mute
   outcomes, severe-harm recall, REVIEW rate and confidence intervals.
   No W20/W27 or protected real holdouts may be examined or used for tuning.

## Non-goals and blockers

This is not a UI form and does not replace the existing blinded reviewer
packet machinery. It does not consume the private Round 2/3 owner ledger or
turn the 216 provisional G10 corrections into verified truth. Broad family
stems may connect unrelated situations. Source rights/privacy, upstream
Codacy per-finding triage and PR-stack gates remain unresolved. No model
downloads, GPU spending, independent-review certification, training,
deployment, or upstream merging are authorized.
