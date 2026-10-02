# W01 follow-up launch packet — Reconcile runtime contract with Policy v1

## Identity

You are the **W01 follow-up runtime-contract reconciliation worker** for the Enthusia AI Moderation project.

Authoritative task: **AI-Moderation-API issue #19**.

Create branch `w01/policy-v1-runtime-reconciliation` from the current live `main` head when you start.

Live GitHub is authoritative. Reconcile current state before making changes.

## Project goal

Enthusia is building one central, modular moderation service used by:

- RoseChat / Minecraft public chat and private messages;
- the Discord Ticket Bot for non-exempt Discord channels;
- EnthusiaStaff for evidence, review, corrections, strikes, containment, appeals, and punishment state.

The AI service is an optional add-on. Its outage must never break Minecraft chat, Discord chat, the Ticket Bot, or normal EnthusiaStaff functionality.

The intended live semantic path is a small local classifier. OpenAI Moderation is advisory/asynchronous and must never be on the live latency-critical path.

## Current accepted state

### Policy

Policy v1 is now merged into `main` via PR #24.

Coordinator-accepted policy includes:

- semantic meaning, message action, review priority, evidence/strike, temporary containment, support/safety flow, and human punishment are separate dimensions;
- AI never bans; staff own bans/final severe sanctions;
- Minecraft public and PMs are moderated;
- Discord general/gaming are moderated unless exempt;
- Discord ticket channels are completely exempt;
- Discord staff-only channels are completely exempt;
- configured additional exempt Discord channels are completely exempt;
- exempt content is not sent to AI, classified, stored as moderation context, used for AI incidents/strikes, or used to influence later moderated content;
- mirrored Minecraft/Discord copies are one canonical moderation event and must not double-count;
- cross-scope context is allowed only when semantically relevant;
- authoritatively linked Minecraft/Discord identities may provide cross-platform context, while punishment histories remain platform-separated;
- split messages can form one semantic act and later context may retroactively remove prior related messages;
- roughly >20 unrelated intervening messages normally breaks speculative split-message linkage;
- structured player/relationship moderation memory is desired with decay;
- self-harm safety history must be isolated from punishment reputation;
- corrections must be auditable and human-confirmed;
- incident-level harassment/dogpiling and target-specific history matter;
- every automated mute alerts staff and provides an appeal/ticket path;
- automatic punishments remain disabled during calibration/acceptance.

Read the actual policy files. Do not rely only on this summary.

### Runtime foundation

W01 foundation was merged via PR #18.

It currently provides:

- authenticated versioned FastAPI moderation API;
- bounded/sharded short-term context;
- SQLite moderation-event/evidence/review persistence;
- explicit response models;
- idempotency/conflict handling;
- classifier interface + fail-open stub;
- asynchronous bounded OpenAI advisory path;
- disagreement evidence;
- health/readiness;
- queue saturation/deadline behavior;
- failure-isolation tests.

This foundation intentionally predates Policy v1 and is not the frozen final contract.

### Deployment/ops

W16 preparation is merged.

The AI service will later run as an optional/non-critical process beside the Discord Ticket Bot. No production deployment has occurred.

### Dataset QA

W17 tooling is merged. A separate follow-up issue #25 will synchronize dataset QA vocabulary/fields with Policy v1. Do not duplicate #25.

## Mandatory reading

Before coding, read all of:

- `README.md`
- `COORDINATOR-STATE.md`
- `policy/POLICY-v1.md`
- `policy/INTERVIEW-DECISION-MAP.md`
- `policy/UNRESOLVED-DECISIONS.md`
- both `policy/interviews/*.jsonl`
- `policy/SOURCE-BASELINE.md`
- `docs/ARCHITECTURE.md`
- `docs/API-CONTRACT.md`
- `docs/DATASET-SCHEMA.md`
- `docs/WORKER-SYSTEM.md`
- `docs/WORKER-LAUNCH-STANDARD.md`
- issue #19
- merged W01 runtime code/tests

Also inspect current RoseChat/EnthusiaStaff/Ticket Bot contracts only where required to keep API boundaries compatible. Do not modify those repos in this task.

## Your job

Reconcile the central runtime/API/storage/context contract with Policy v1 so W13 RoseChat, W14 Discord, and W15 EnthusiaStaff can build against a stable contract.

This is a **runtime contract task**, not model training and not client integration.

## Required changes

### 1. Separate decision dimensions

Do not overload one action enum with unrelated meaning.

The API/storage model must separately represent at least:

- semantic label;
- message action;
- review priority;
- strike/evidence recommendation;
- containment recommendation;
- containment duration when explicitly known;
- support/safety flow;
- reason codes;
- related message IDs;
- confidence/model evidence;
- policy/model versions.

The exact public schema should be explicit and documented.

Do not invent policy for unresolved cases.

### 2. Final Policy-v1 semantic vocabulary

Reconcile provisional runtime labels with the merged Policy-v1 vocabulary.

At minimum consider labels now present in the dataset schema such as:

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

If runtime naming should differ from dataset naming for good technical reasons, document a stable mapping. Do not silently diverge.

### 3. Channel/scope profile semantics

The API needs explicit source/scope metadata sufficient to distinguish:

- Minecraft public;
- Minecraft private;
- Discord general;
- Discord gaming;
- exempt profiles.

Exempt content should be rejected/skipped before semantic ingestion where practical. The service must not persist or use exempt message text as moderation context.

Do not hard-code literal production channel IDs into the AI service.

### 4. Cross-scope context

Current W01 short-term context is mostly same-scope/channel.

Policy v1 requires a design that can support:

- PM -> public context between relevant participants;
- public -> PM context;
- related moderated scopes;
- same sender continuity;
- target/recipient relationships;
- explicit replies;
- incident grouping;
- authoritatively linked cross-platform identities;
- multi-sender harassment/dogpiling.

Do not make this unrestricted global history.

Design clear linkage keys/relationships and privacy boundaries.

### 5. Incident-level moderation

Add a stable representation for multi-message/multi-sender incidents without forcing the classifier to pretend every incident is one message.

Needed use cases include:

- repeated harassment;
- repeated unwanted contact;
- coordinated/uncoordinated dogpiling;
- later context changing prior message meaning;
- target-specific stronger filtering;
- recent confirmed threat history causing review sooner.

It is acceptable to separate per-message classification from incident aggregation, but the storage/API contracts must support it.

### 6. Structured durable memory

Policy v1 wants durable structured moderation memory, separate from model weights.

Design storage/contracts for policy-relevant facts such as:

- incidents/category/severity;
- strikes/evidence;
- target-specific history;
- stop/unwanted-contact state;
- mutual-banter/consent state;
- target-specific stricter filtering;
- staff-confirmed / staff-overturned outcomes;
- authoritative account linkage;
- age clues with provenance/confidence;
- safety-check state in a restricted area.

Important boundaries:

- history decays;
- missing memory must fail open/neutral, not invent facts;
- self-harm/safety memory must not influence punishment reputation;
- punishment histories stay platform-separated;
- cross-platform context only uses authoritative linkage.

You do not need to finalize every decay formula. You do need a schema/migration-safe design that can support Policy v1.

### 7. Restart/context continuity

The service must not unnecessarily lose all useful recent moderation context on restart if durable events are available.

Design bounded rehydration/recovery from durable storage while preserving:

- fast startup;
- bounded memory;
- fail-open behavior;
- privacy/exemption rules;
- no duplicate incident counting.

If rehydration is intentionally deferred, document exactly why and what downstream behavior results.

### 8. Schema migrations

The current database foundation must become safely versioned before production.

Implement a migration mechanism suitable for:

- existing dev/runtime SQLite databases;
- additive Policy-v1 fields/tables;
- rollback planning;
- startup failures that do not corrupt data.

Do not solve migration by silently deleting/recreating the DB.

### 9. Retroactive/related-message contract

Finalize a stable contract that lets clients:

- block the current message;
- receive related prior message IDs;
- later remove prior messages when new context changes interpretation;
- avoid double-counting mirrored copies;
- link one canonical moderation event to platform-specific message IDs.

W13/W14 will implement actual deletion later.

### 10. Review/correction contract

W15 needs a stable API/storage contract to:

- list pending review items;
- fetch structured evidence/context;
- submit human corrections;
- track reviewer identity/time;
- support two-person confirmation for normal staff;
- allow Admin+ immediate override;
- preserve the original AI outcome and accepted corrected outcome;
- make corrected samples eligible for later curated training export.

Do not build the GUI here.

### 11. Privacy and data minimization

Raw production messages stay in private runtime storage, not GitHub.

Staff review should expose only the context materially used/relevant to the moderation event.

Exempt content must never leak into context because it should never have been ingested.

### 12. Fail-open behavior

Preserve and expand existing guarantees.

Classifier error, context error, storage error, memory error, queue saturation, timeout, migration-readiness failure, OpenAI failure, or service restart must never cause a harmful content block by default.

The client contract must clearly identify errors so clients can fail open.

OpenAI remains advisory only.

## Unresolved Policy-v1 edges

Read `policy/UNRESOLVED-DECISIONS.md`.

Do not invent answers for:

- Discord bot DMs;
- graphic self-harm disclosure;
- consensual explicit adult PM boundaries;
- grooming with uncertain age;
- broader dangerous-instruction categories;
- fake-doxxing strike cleanup;
- complete threat-containment duration matrix;
- blackmail containment duration;
- lexical slur false-positive details.

Design the runtime so those decisions can be added later without another destructive redesign.

## Tests

Add strong tests for at least:

- separated action/review/strike/containment/support fields;
- exempt scopes not entering context/storage;
- PM/public related-context linkage;
- unrelated scope isolation;
- linked vs unlinked cross-platform identities;
- split-message related IDs;
- mirror deduplication;
- multi-sender incident representation;
- restart rehydration without duplicate counting;
- memory unavailable => neutral/fail-open;
- safety memory isolated from punishment memory;
- migration from current W01 schema;
- review correction workflow state transitions;
- idempotency preserved;
- failure paths preserved.

Keep existing CI gates green: Ruff, strict mypy, complexity, pytest, wheel, and any current dataset/deployment checks.

## Non-goals

Do not:

- train the classifier;
- generate synthetic datasets;
- implement RoseChat client behavior;
- implement Discord client behavior;
- implement EnthusiaStaff GUI;
- deploy or restart production;
- enable automatic punishments;
- add production secrets;
- use raw production chat.

## Acceptance

Open one PR to `main` and do not self-merge.

Completion report must include:

- PR URL;
- exact head SHA;
- schema/API changes;
- migration strategy;
- context/incident/memory design;
- test count and exact-head CI run;
- unresolved items intentionally deferred;
- confirmation that no deployment/secrets/production data were involved.
