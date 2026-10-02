# W17 follow-up launch packet — Sync dataset QA with Policy v1

## Identity

You are the **W17 follow-up dataset-QA reconciliation worker** for the Enthusia AI Moderation project.

Authoritative task: **AI-Moderation-API issue #25**.

Create branch `w17/policy-v1-dataset-qa` from current live `main`.

Live GitHub is authoritative.

## Why this task exists

W17 previously built policy-independent dataset QA before Policy v1 was frozen.

Policy v1 is now merged via PR #24 and expands the dataset schema substantially.

Before nine generator workers create 4,500 examples, the validator must understand the **actual Policy-v1 schema** or those workers will either fail valid examples or silently omit important dimensions.

This task is deliberately narrow: synchronize validator/config/reporting/tests with the merged schema. Do not generate training data and do not decide unresolved policy.

## Current accepted project state

Merged components include:

- W01 central fail-open runtime foundation;
- W16 deployment/supervisor preparation;
- W17 initial dataset-QA tooling;
- W00 Policy v1.

The generator wave W02–W10 remains blocked until this follow-up is reviewed/merged.

## Mandatory reading

Read all of:

- `README.md`
- `COORDINATOR-STATE.md`
- `policy/POLICY-v1.md`
- `policy/INTERVIEW-DECISION-MAP.md`
- `policy/UNRESOLVED-DECISIONS.md`
- `docs/DATASET-SCHEMA.md`
- `docs/DATASET-QA.md`
- `docs/WORKER-SYSTEM.md`
- `docs/WORKER-LAUNCH-STANDARD.md`
- `tools/dataset_qa/config.json`
- all current dataset-QA source/tests
- issue #25

Also inspect generator issues #3–#11 so validation behavior matches their expected 500-record packages.

## Policy-v1 dataset fields

The merged schema separates semantic truth from policy outcome.

Generator records now need support for fields including:

- `example_id`
- `policy_version`
- `source`
- `domain`
- `difficulty`
- `platform_hint`
- `channel_profile`
- `messages`
- `target_index`
- `label`
- `action`
- `review_priority`
- `strike`
- `containment`
- `containment_duration_seconds`
- `support_flow`
- `reason_codes`
- `notes`
- optional `family_id`

Read the merged schema for exact semantics.

## Required work

### 1. Central vocabulary/config update

Update `tools/dataset_qa/config.json` to match Policy v1.

Semantic labels currently include:

- SAFE
- GAMEPLAY_VIOLENCE
- LOW_LEVEL_HARASSMENT
- SEVERE_HARASSMENT
- STAFF_TARGETED_ABUSE
- REAL_WORLD_THREAT
- SELF_HARM_INSTRUCTION
- SELF_HARM_INTENT
- THIRD_PARTY_SELF_HARM_CONCERN
- HATE
- SLUR_USE
- SEXUAL_CONTENT
- SEXUAL_MINOR
- DOXXING
- BLACKMAIL
- GROOMING
- DANGEROUS_REAL_WORLD_INSTRUCTIONS
- AMBIGUOUS_REVIEW

Actions:
- ALLOW
- REVIEW
- BLOCK

Review priorities:
- NONE
- NORMAL
- URGENT

Containment:
- NONE
- MUTE

Support flows:
- NONE
- SELF_HARM_CHECK
- TARGET_SAFETY_CHECK

Channel profiles:
- minecraft_public
- minecraft_private
- discord_general
- discord_gaming
- discord_staff_exempt
- discord_ticket_exempt
- discord_configured_exempt

Use the merged reason-code vocabulary, not this packet as a replacement.

### 2. Decide required vs optional schema fields from the merged docs

Make the validator and `docs/DATASET-SCHEMA.md` unambiguous about generator records.

Coordinator preference:

- fields that encode Policy-v1 outcome dimensions should be required for W02–W10 generator records;
- `containment_duration_seconds` should be nullable/optional only when no concrete owner duration exists;
- `family_id` remains optional;
- policy unresolved items must not be guessed.

If the docs currently leave requiredness ambiguous, clarify them without changing policy.

### 3. Type and enum validation

Validate:

- `channel_profile` as known string enum;
- `review_priority` as known string enum;
- `strike` as true/false boolean, not integer/string;
- `containment` as known enum;
- `containment_duration_seconds` as null or positive integer according to schema;
- `support_flow` as known enum.

Add cross-field structural validation where it is purely schema-level, for example:

- containment NONE should not carry a mute duration;
- containment MUTE may have null duration only when policy explicitly leaves duration unresolved;
- duration cannot be zero/negative;
- exempt profiles should be flagged/warned if they appear in semantic training data unless the schema says they are deliberate policy-engine fixtures.

Do not encode owner-policy guesses as validator errors.

### 4. Preserve existing QA guarantees

Do not regress:

- JSONL parsing;
- Unicode line-separator fix;
- G01..G09 ID ranges;
- duplicate ID/missing ID checks;
- exact duplicate normalization;
- meaningful message/speaker/boundary distinctions;
- obfuscation preservation;
- near-duplicate advisory reporting;
- minimal-pair candidate handling;
- family IDs;
- contradiction reporting;
- deterministic output.

### 5. Reporting

Extend QA reports with useful Policy-v1 statistics:

- channel profile;
- review priority;
- strike true/false;
- containment;
- support flow;
- containment-duration coverage;
- existing label/action/domain/platform/message/family/reason statistics.

Keep output deterministic.

### 6. Generator UX

Update `docs/DATASET-QA.md` with:

- exact commands W02–W10 should run;
- example of a valid Policy-v1 record;
- explanation of errors vs warnings;
- note that unresolved policy edges must not be invented;
- note that near-duplicate/minimal-pair output needs human review.

### 7. Tests

Add focused tests for:

- valid full Policy-v1 record;
- every new enum rejecting unknown values;
- bool type for strike;
- null/valid/invalid duration;
- containment/duration consistency;
- exempt profile handling;
- new labels/reason codes accepted;
- deterministic report includes new fields;
- old pre-Policy-v1 fixture failure where appropriate;
- all existing W17 tests remain green.

## Unresolved Policy-v1 items

Read `policy/UNRESOLVED-DECISIONS.md`.

Do not invent answers for:

- Discord bot DMs;
- graphic self-harm handling;
- explicit consensual adult PM boundary;
- uncertain-age grooming;
- broader dangerous instructions;
- fake-doxxing strike cleanup;
- full threat duration matrix;
- blackmail duration;
- accidental lexical slur edge cases.

The validator should allow the schema to represent “not concretely specified” where the schema intentionally permits it.

## Non-goals

Do not:

- generate any G01–G09 dataset;
- train a model;
- change runtime/API behavior;
- modify RoseChat/Ticket Bot/EnthusiaStaff;
- use production messages;
- deploy anything;
- add policy decisions.

## Acceptance

Open one PR to `main`; do not self-merge.

Completion report must include:

- PR URL;
- exact head;
- files changed;
- final required-field/vocabulary behavior;
- test count;
- exact-head CI result;
- known limitations;
- confirmation that no policy was invented and no production data/deployment was involved.
