# W18 launch packet — Owner-policy golden acceptance set

## Identity

You are **W18**, the owner-policy golden acceptance-set worker for the Enthusia AI Moderation project.

Authoritative task: **AI-Moderation-API issue #26**.

Create branch `w18/owner-policy-golden-set` from current live `main`.

Live GitHub is authoritative. Reconcile current state before changing anything.

## Why this exists

The owner has completed W00. Policy v1 is merged.

Before nine synthetic-data workers generate 4,500 new examples, we want a compact, machine-readable corpus made only from **actual owner decisions already given during the interview**.

This serves several purposes:

- protects the owner's real decisions from being diluted by later synthetic generation;
- gives W11/W12 a frozen high-value evaluation set;
- gives runtime/policy-engine workers concrete acceptance scenarios;
- catches places where Policy-v1 prose accidentally drifts from raw interview evidence;
- gives us traceability from a test failure back to the exact interview item that defined the behavior.

You are **not** being asked to create new policy or new phrases.

## Current project state

Merged:

- W00 Policy v1 via PR #24;
- W01 central runtime foundation;
- W16 deployment/supervisor preparation;
- W17 initial dataset-QA tooling.

In parallel:

- issue #19 reconciles runtime/API/storage/context with Policy v1;
- issue #25 reconciles dataset-QA vocabulary/fields with Policy v1.

W02–W10 synthetic generation remains blocked until the Policy-v1 QA contract is stable.

## Mandatory reading

Read in full:

- `README.md`
- `COORDINATOR-STATE.md`
- `policy/POLICY-v1.md`
- `policy/INTERVIEW-DECISION-MAP.md`
- `policy/UNRESOLVED-DECISIONS.md`
- `policy/interviews/2026-10-01-owner-interview.jsonl`
- `policy/interviews/2026-10-02-owner-interview-continuation.jsonl`
- `docs/DATASET-SCHEMA.md`
- `docs/DATASET-QA.md`
- `docs/WORKER-SYSTEM.md`
- `docs/WORKER-LAUNCH-STANDARD.md`
- issue #26

Also inspect issue #25 so you understand that dataset-QA validation is being updated in parallel. Do not duplicate that worker.

## Source hierarchy

Use this hierarchy when converting interview material:

1. Latest direct owner answer in interview JSONL.
2. Policy v1 if it faithfully consolidates that answer.
3. Decision map as a compact reference.

If Policy-v1 text and a raw owner record materially disagree:
- do not silently pick one;
- record the conflict in the traceability report;
- preserve the raw owner answer as the authoritative interview evidence unless a later owner answer clearly superseded it.

## What counts as a golden fixture

A golden fixture should represent an owner-resolved scenario that can be meaningfully tested.

Good candidates include:

- single-message semantic decisions;
- multi-message/split-message decisions;
- platform/channel contrasts;
- PM/public context;
- strike/no-strike distinctions;
- review-priority distinctions;
- containment anchors with owner-specified durations;
- self-harm support-flow distinctions;
- doxxing/blackmail/grooming decisions;
- harassment/dogpiling incidents;
- exempt-channel behavior;
- mirror/cross-platform context rules where owner-resolved.

Pure policy notes that have no concrete message scenario may instead become:
- policy-engine acceptance cases;
- structured manifest assertions;
- coverage entries.

Do not force every policy note into a fake classifier example.

## Required traceability

Every fixture must include explicit provenance, such as:

```json
{
  "source_interview_ids": ["W00-003"],
  "policy_sections": ["6"],
  ...
}
```

If one fixture depends on multiple interview items, list all of them.

Do not create an example without traceability.

## Required outputs

Preferred layout:

```text
data/eval/
  owner-policy-v1.jsonl
  owner-policy-v1-manifest.json

docs/
  OWNER-POLICY-GOLDEN-SET.md
```

You may add a small supporting script/test if needed, but keep the work narrow.

### owner-policy-v1.jsonl

Include only concrete owner-resolved examples that are suitable as message/incident evaluation cases.

Preserve:

- exact or normalized interview message sequence;
- channel/platform context when material;
- target index where meaningful;
- semantic label only where supported;
- message action;
- review priority where supported;
- strike where supported;
- containment/duration only where explicitly supported;
- support flow where supported;
- reason codes only when directly supportable from Policy v1;
- family/minimal-pair grouping;
- source interview IDs;
- concise source notes.

When a policy outcome dimension was never actually answered:
- leave it null/unspecified if the schema permits;
- do not infer it from neighboring examples.

### manifest

Create a machine-readable manifest that separates:

- direct message/incident fixtures;
- policy-engine assertions;
- non-fixture policy notes;
- unresolved owner-policy edges;
- known superseded answers;
- source coverage.

### documentation

`docs/OWNER-POLICY-GOLDEN-SET.md` should explain:

- what the golden set is;
- why it must remain separate from generated training data;
- source hierarchy;
- how to run validation;
- how W11/W12 should use it;
- why it should normally remain in evaluation/acceptance rather than training;
- how future owner corrections should version/update it.

## Important dataset-safety rule

The owner-policy golden set should **not be casually included in training**.

Reason: if the exact 84 interview-derived decisions are trained on and then also used for evaluation, we create leakage and lose the ability to tell whether the model generalized.

Coordinator preference:

- keep direct owner interview fixtures as a frozen acceptance/evaluation set;
- synthetic workers may create related paraphrase families, but W11 must keep near variants grouped and prevent leakage into the golden evaluation;
- if a specific owner fixture is ever intentionally promoted to training, version the golden set and preserve an unseen equivalent test family.

Document this.

## Minimal pairs

Preserve important contrast families, for example:

- Minecraft generic kill threat vs Discord generic threat vs Discord gaming;
- PvP violence vs IRL continuation;
- Minecraft base/bomb language vs real-world bomb request;
- PM/public cross-context;
- ordinary toxicity vs repeated harassment;
- KYS vs self-harm disclosure vs gameplay death language;
- quoted actual slur vs “n-word” reference;
- public flirting vs private flirting;
- age clue vs reliably known minor;
- apparent vs confirmed doxxing;
- exempt ticket/staff channel vs moderated channel.

Do not invent new wording just to make a pair. Use actual owner-resolved records when available.

## Policy-note acceptance assertions

Some owner decisions are system-policy assertions rather than message examples.

Examples:

- AI never bans;
- every automated mute alerts staff;
- tickets exempt;
- staff-only Discord channels exempt;
- self-harm history does not affect punishment reputation;
- linked cross-platform punishment histories remain separate;
- accepted human corrections remove punishment effect but preserve training evidence;
- normal staff corrections require two-person agreement, Admin+ can override;
- fail open when AI/memory unavailable;
- mirrors count once.

Represent these separately from classifier-message fixtures.

## Unresolved items

Read `policy/UNRESOLVED-DECISIONS.md`.

Do not resolve:

- Discord bot DMs;
- graphic self-harm handling;
- consensual explicit adult PM boundary;
- uncertain-age grooming;
- broader dangerous instructions;
- fake-doxxing strike cleanup;
- full threat containment matrix;
- blackmail duration;
- accidental lexical slur matching.

The golden-set docs should explicitly list these as excluded/unresolved where relevant.

## QA interaction

Issue #25 is updating the validator in parallel.

Do not rewrite dataset-QA tooling.

If #25 merges before you finish:
- rebase/update and validate the golden set against the new schema.

If #25 is still open:
- structure output to match merged `docs/DATASET-SCHEMA.md`;
- clearly document any fields that current QA cannot yet validate;
- do not block your entire analysis on #25.

## Tests / validation

At minimum:

- JSONL parses;
- source interview IDs exist;
- no duplicate golden fixture IDs;
- every fixture has traceability;
- unresolved interview items are not presented as settled fixtures;
- superseded/updated answers are not accidentally duplicated as conflicting truth;
- family IDs are valid where used;
- final dataset-QA passes once #25 is available.

Add a small traceability checker if needed.

## Non-goals

Do not:

- generate 500-example synthetic datasets;
- paraphrase or expand owner examples;
- invent policy;
- train a model;
- modify runtime/API/client code;
- use production chat;
- deploy anything;
- merge your own PR.

## Acceptance report

Open one PR to `main`.

Completion report must include:

- PR URL;
- exact head;
- count of direct golden fixtures;
- count of policy-engine assertions;
- count/list of interview items excluded and why;
- any Policy-v1/raw-interview conflicts discovered;
- validation/test results;
- exact-head CI;
- confirmation that no new policy, production data, model training, or deployment occurred.
