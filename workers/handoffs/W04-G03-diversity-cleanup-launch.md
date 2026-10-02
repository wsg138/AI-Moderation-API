# G03 cleanup launch packet — Harassment corpus diversity/family repair

## Identity

You are a **fresh cleanup worker** for W04 / G03.

Existing issue: **#5**.
Existing PR: **#32 — Add G03 harassment/toxicity synthetic dataset**.
Existing branch: `w04/dataset-harassment`.
Current reviewed head before your changes: `d2ba67f7e40e046700c6fbcbe7a174aac1623150`.

Continue the existing branch/PR; do **not** open a second G03 PR.

## Why revision is required

The dataset is structurally valid and policy coverage is useful, but coordinator text-sequence auditing found too much repeated/template content.

Coordinator findings on the reviewed head:

- 74 identical normalized **message-text sequence** groups;
- 170 / 500 records participate in those groups;
- all 74 groups are split across different `family_id` values;
- 35 groups repeat identical text with the same channel profile and same label/action, adding no useful contrast.

Example already documented in PR #32: records such as G03-0101 and G03-0131 reuse the same full message-text sequence and same policy outcome under unrelated family IDs.

The merged W17 duplicate fingerprint intentionally preserves more metadata, so passing the canonical exact-duplicate check is not enough here. This cleanup is about training diversity and leakage-safe family structure.

## Mandatory reading

Read:

- PR #32 conversation, especially coordinator revision comment;
- issue #5;
- current `data/synthetic/G03-harassment.jsonl` on the PR branch;
- `data/synthetic/G03-report.md`;
- `policy/POLICY-v1.md`;
- `docs/DATASET-SCHEMA.md`;
- `docs/DATASET-QA.md`;
- `docs/OWNER-POLICY-GOLDEN-SET.md`;
- current golden fixtures;
- current main `COORDINATOR-STATE.md`.

## Preserve exactly

Keep:

- exactly 500 IDs: `G03-0001..G03-0500`;
- original seven coverage buckets: 100 / 100 / 80 / 70 / 70 / 50 / 30;
- Policy-v1 decisions;
- no unresolved-policy invention;
- no production data;
- no golden-set edits;
- no runtime/client changes.

The prior action distribution does not need to remain mathematically identical, but do not materially distort the intended corpus balance merely to fix wording.

## Required cleanup

### 1. Rewrite redundant same-profile/same-outcome duplicates

For every identical normalized message-text sequence that repeats with the same effective policy meaning and no useful contextual/profile contrast, rewrite the redundant copies into genuinely different natural scenarios.

Do not make cosmetic edits such as changing one adjective/name.

Vary:

- message structure;
- number/order of turns;
- slang;
- game/server context;
- target reaction;
- stop-request wording;
- duration/repetition cues;
- staff interaction wording;
- dogpile participation;
- mutual-banter evidence.

### 2. Re-family intentional identical wording

If identical wording is intentionally reused because profile, speaker relationship, context, or policy outcome meaningfully differs, all such variants must share one `family_id`.

W11 must never be able to split exact-wording contrast variants across train/eval.

### 3. Reduce template pools

The original dogpile/consent sections reuse small phrase pools heavily. Expand them.

Avoid repeated target phrases such as the same “lol fair…” / “run it back” / “nobody wants…” sequence across many families unless that exact reuse is itself the intended minimal pair.

### 4. Preserve hard boundaries

Keep strong coverage for:

- tolerated low-level toxicity/profanity;
- repetition crossing into harassment;
- explicit stop requests;
- mutual banter vs unwanted contact;
- targeted staff abuse vs good-faith criticism;
- multi-sender dogpiling;
- /ignore and stricter-target-filter context;
- review vs block distinctions.

## Required independent audit

In addition to canonical QA, run a **message-text-only sequence duplicate audit** that ignores offsets/notes/family/profile.

Normalization at minimum:

- Unicode normalize;
- lowercase;
- collapse whitespace;
- preserve message order and speaker.

Final target:

- no redundant same-profile/same-outcome identical text-sequence groups;
- every intentionally identical contrast group has one shared family ID;
- substantially fewer repeated identical sequences overall.

Document final counts in the report.

## Golden leakage

Re-check against the frozen owner golden set.

No exact golden sequence and no trivial rewrite of a golden fixture.

## Final validation

Run canonical:

```bash
python -m tools.dataset_qa validate data/synthetic/G03-harassment.jsonl --range G03:1-500
python -m tools.dataset_qa report data/synthetic/G03-harassment.jsonl --range G03:1-500 --format markdown --output data/synthetic/G03-report.md
```

Then rerun the full repository CI.

Update PR #32 body/comment with:

- new exact head;
- exactly 500 records;
- canonical QA result;
- message-text-only duplicate group count;
- count of intentional identical-wording contrast groups;
- confirmation those groups share family IDs;
- action/label/channel distribution;
- multi-message count;
- exact-head CI.

Do not self-merge.
