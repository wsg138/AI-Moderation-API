# W24 — Evasion-chain / strike-linkage prototype

Status: implementation prototype only. It does not enable automatic punishment, mutes, bans, or
authoritative strike mutation.

## Purpose

W24 adds a deterministic evidence layer for the narrow case where one player receives a
high-confidence block and quickly retries substantially the same prohibited meaning with modified
spelling, spacing, punctuation, symbols, or wording.

The evasion signal is additional evidence. It never replaces the moderation decision for the new
message. The current message must still be independently blocked before this prototype can link it
into an evasion chain.

## Architecture boundary

The implementation lives in `moderation_api.evasion` and is intentionally isolated from the live
request/response and SQLite schema for this worker.

That boundary preserves the existing separation:

1. the classifier/policy path decides the current message;
2. the evasion linker compares already-decided evidence;
3. EnthusiaStaff remains authoritative for strikes, mutes, appeals, and punishment state.

The prototype returns an explicit `EnthusiaStaffStrikeEvidence` allowlist. It cannot expose an
internal database row and hard-codes `automatic_punishment_allowed=False`.

## Inputs

`ModerationSnapshot` contains only runtime-available moderation evidence:

- event, sender, platform, scope, channel-profile, and canonical IDs;
- authoritative cross-platform identity ID when supplied by a trusted integration;
- event timestamp and text;
- semantic label, message action, confidence, review priority, strike recommendation, and support
  flow;
- human review state;
- existing evasion-chain root/depth when a caller is continuing a chain.

`RelationContext` supplies explicit relation facts that must prevent mechanical escalation:
mirror, quote/report, apology/correction, and appeal/review discussion.

Optional semantic similarity is accepted only as a numeric value supplied by an approved local
representation. W24 does not call a remote model and does not invent semantic similarity when no
approved representation exists.

## Deterministic eligibility gates

A pair cannot link when any of these conditions applies:

- the prior event was not actually blocked;
- prior confidence is below the prototype high-confidence threshold;
- the prior event is pending human review or has been overturned;
- the current event is not independently blocked;
- either side is a safety/support self-harm event;
- the actors differ and no authoritative shared identity ID exists;
- timestamps are reversed or outside the bounded retry window;
- the messages are canonical mirrors;
- the current message is a quote/report, apology/correction, or appeal/review discussion.

These gates run before textual similarity.

## Similarity features

The linker records auditable feature values rather than hidden reasoning:

- bounded time gap;
- same-actor determination;
- same semantic label;
- Unicode-normalized character similarity;
- token Jaccard overlap;
- compact-text containment;
- optional approved local semantic similarity.

Normalization uses Unicode NFKC, case folding, a small deterministic leetspeak map, word-token
extraction, and a compact alphanumeric form. This makes punctuation/spacing and common character
substitutions comparable without using a naive prohibited-word substring list.

A link is created only when an eligibility gate passes and at least one configured similarity path
is strong enough. Changed wording therefore requires an approved local semantic similarity signal
when lexical evidence is insufficient.

## Prototype calibration values

The default implementation values are relationship-link calibration, not punishment policy:

- retry window: 90 seconds;
- prior high-confidence floor: 0.90;
- character similarity: 0.84;
- token similarity: 0.65;
- optional local semantic similarity: 0.82;
- compact containment length ratio: 0.60.

Policy-v1 explicitly leaves exact classifier confidence thresholds unresolved. These values must be
validated against W21/W22/W23 adversarial and real-chat evaluation work before runtime integration.

No mute duration, strike-count ladder, ban threshold, or other punishment arithmetic is introduced.

## Chain identity and auditability

When linked, the decision exposes:

- deterministic chain ID;
- root event ID;
- immediate prior/current event IDs;
- attempt index;
- relation score;
- exact reason codes showing which similarity paths linked;
- complete feature values;
- current classifier strike recommendation.

Subsequent attempts can carry the same root ID and depth, preserving one chain instead of creating
independent pseudo-incidents for each retry.

## False-link protections covered by tests

Regression coverage includes:

- character substitutions;
- inserted spaces/punctuation;
- changed wording with supplied local semantic similarity;
- refusal to invent semantic similarity;
- quote/report;
- apology/correction;
- appeal/review discussion;
- Minecraft-benign gameplay language;
- unrelated lexical overlap;
- canonical and explicit mirror copies;
- the same violation much later;
- pending prior review;
- a prior false positive later overturned;
- low-confidence prior blocks;
- self-harm safety/support events;
- different senders;
- authoritative cross-platform identity linkage;
- multiple rapid genuine retries retaining one chain root;
- explicit EnthusiaStaff evidence with automatic punishment disabled.

## Proposed EnthusiaStaff authoritative interface

A future API/storage integration can serialize the allowlisted
`EnthusiaStaffStrikeEvidence` fields and submit them as evidence attached to the current
moderation event/case:

```text
evidence_type = EVASION_CHAIN
chain_id
root_event_id
prior_event_id
current_event_id
attempt_index
relation_score
reason_codes[]
current_strike_recommendation
automatic_punishment_allowed = false
```

EnthusiaStaff should own any authoritative strike mutation. It should re-check that both referenced
events still have valid moderation outcomes before applying punishment state. An accepted correction
or overturn should invalidate the evasion evidence's punishment effect while retaining the audit
record and human-confirmed negative example.

## Persistence proposal for a later integration worker

If W24 is promoted from prototype to runtime behavior, use a dedicated append-only evidence table
rather than overloading `incidents` or `moderation_memory`. Recommended columns are:

- link ID and chain ID;
- root/prior/current event IDs with foreign keys;
- attempt index;
- relation score;
- serialized feature values and reason/blocker codes;
- creation timestamp;
- invalidated timestamp/reason;
- correction proposal/event that invalidated the link, when applicable.

The event decisions remain immutable. Correction handling should mark the evasion evidence inactive
for punishment purposes instead of deleting history.

## Policy-v1 decisions still required before punishment automation

W24 intentionally does not decide:

- the production retry window or similarity thresholds;
- whether attempt count changes a strike recommendation and by how much;
- any strike-to-mute arithmetic;
- any automatic mute duration for evasion;
- how confirmed vs merely unreviewed prior events should affect production escalation;
- whether a corrected current event should retroactively split a chain;
- the final semantic representation approved for changed-wording similarity.

Automatic punishment remains disabled until those decisions are frozen and validated.
