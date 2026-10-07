# Synthetic corpus G10–G27 — moderation classifier training data

18 batches × 500 records = **9,000 synthetic examples** for the Enthusia AI chat-moderation classifier.
Generated 2026-10-07 by parallel Luna workers; every batch validated with
`python3 -m tools.dataset_qa validate --range GXX:1-500` (0 errors required to ship).

## Status: CANDIDATE — not yet approved for training

This data has passed structural QA and one full label-review pass (1,972 records
reviewed, ~350 corrections — see `_changelog-GXX.json` files), plus owner
spot-checks. It has **not** had independent second-model review. Do not train
on it until that gate passes. (G28 swatting batch was blocked by safety filters;
a worker brief for it lives at `data/synthetic/G28-WORKER-BRIEF.md`. G22's brief
is also kept for reference.)

## Batches

| Batch | File | Focus | Top labels |
|---|---|---|---|
| G10 | G10-blackmail-extortion.jsonl | Blackmail/extortion (was 0 examples) | BLACKMAIL 397, SAFE 78, AMBIGUOUS 25 |
| G11 | G11-doxxing.jsonl | Doxxing expansion | DOXXING 400, SAFE 96, AMBIGUOUS 4 |
| G12 | G12-grooming.jsonl | Grooming/predatory patterns | GROOMING 400, SAFE 88, AMBIGUOUS 12 |
| G13 | G13-staff-abuse.jsonl | Staff-targeted abuse | STAFF_TARGETED_ABUSE 375, SAFE 101, AMBIGUOUS 24 |
| G14 | G14-self-harm-third-party.jsonl | Third-party self-harm concern | THIRD_PARTY_SELF_HARM_CONCERN 400, SAFE 84, AMBIGUOUS 16 |
| G15 | G15-evasion-advanced.jsonl | Evasion beyond G08 (non-slur) | SAFE 173, REAL_WORLD_THREAT 99, GAMEPLAY_VIOLENCE 78 |
| G16 | G16-harassment-campaigns.jsonl | Severe harassment: dogpiles, escalation arcs | SEVERE_HARASSMENT 360, SAFE 88, LOW_LEVEL 49 |
| G17 | G17-hate-coded.jsonl | Coded/slur-free identity hate | HATE 347, SAFE 104, LOW_LEVEL 29 |
| G18 | G18-normal-chat.jsonl | Everyday normal chat | SAFE 498, AMBIGUOUS 2 |
| G19 | G19-sexual-content.jsonl | Adult sexual content (no minors) | SEXUAL_CONTENT 389, SAFE 107, AMBIGUOUS 4 |
| G20 | G20-school-threats.jsonl | School & location threats | REAL_WORLD_THREAT 400, SAFE 75, AMBIGUOUS 25 |
| G21 | G21-multilingual.jsonl | Non-English violations (ES/FR/DE/PT) | LOW_LEVEL 224, SEVERE 97, SAFE 75 |
| G22 | G22-dangerous-instructions-2.jsonl | Dangerous-instruction requests, non-explosive | DANGEROUS_INSTRUCTIONS 403, SAFE 89, AMBIGUOUS 8 |
| G23 | G23-low-toxicity.jsonl | Everyday low-level toxicity | LOW_LEVEL 375, SAFE 100, AMBIGUOUS 25 |
| G24 | G24-self-harm-intent.jsonl | First-person self-harm intent | SELF_HARM_INTENT 400, SAFE 75, AMBIGUOUS 25 |
| G25 | G25-boundary.jsonl | Boundary calibration (deliberately borderline) | AMBIGUOUS 239, SAFE 210, violations 51 |
| G26 | G26-safe-community.jsonl | Community-context safe chat | SAFE 499, AMBIGUOUS 1 |
| G27 | G27-private-harassment.jsonl | Private-channel (DM) harassment | SEVERE 240, LOW_LEVEL 160, SAFE 99 |

Each batch has a `GXX-report.md` QA report and a `_changelog-GXX.json` review log.

## Label totals across G10–G27

SAFE 2639 · LOW_LEVEL_HARASSMENT 911 · SEVERE_HARASSMENT 750 ·
REAL_WORLD_THREAT 546 · AMBIGUOUS_REVIEW 496 · DANGEROUS_REAL_WORLD_INSTRUCTIONS 403 ·
DOXXING 402 · SELF_HARM_INTENT 402 · BLACKMAIL 400 · THIRD_PARTY_SELF_HARM_CONCERN 400 ·
GROOMING 400 · HATE 398 · SEXUAL_CONTENT 391 · STAFF_TARGETED_ABUSE 381 ·
GAMEPLAY_VIOLENCE 81

## Owner policy rulings applied (policy/KNOWN-DECISIONS.md)

- Curiosity questions about religious/cultural practice are SAFE, even skeptical
  variants — a single question is never a violation; monitor for escalation.
- "check your dms" and DM-pivot phrases are never violations on their own;
  target_index must point at actual violation content.
- Single innocuous messages are SAFE, not AMBIGUOUS_REVIEW (fail open).

## Also in this change

- `tools/dataset_qa/config.json`: registered ID ranges G10–G28.
- `policy/KNOWN-DECISIONS.md`: the three rulings above.
