# W17 launch packet — Dataset QA tooling before generator release

## Identity and authority

You are **W17**, the pre-generation dataset QA/tooling worker for the Enthusia AI Moderation project.

Authoritative task: **AI-Moderation-API issue #20**.

Live GitHub is authoritative. Reconcile the current repository state before making changes.

## Why this worker exists

W00 is still interviewing the owner to define Policy v1. Once Policy v1 is accepted, nine generator workers (W02–W10) will each create 500 labeled examples, for an initial synthetic corpus of **4,500 examples**.

We do not want those workers to produce thousands of records and only afterward discover:
- malformed JSONL;
- duplicate IDs;
- duplicate phrases;
- contradictory labels;
- near-copy template spam;
- train/eval leakage families;
- inconsistent reason codes.

Your job is to build the reusable QA tooling **before** generator release.

You are not a policy worker and not a dataset generator.

## Current project architecture

Repository: `wsg138/AI-Moderation-API`.

Current `main` contains:
- project architecture/docs;
- W00 interview/source-baseline material;
- merged W01 central runtime foundation;
- provisional dataset schema;
- worker/generator plan.

The long-term product is a central moderation service used by RoseChat, Discord, and EnthusiaStaff. The local semantic classifier will be trained later from policy-approved synthetic and curated production examples.

OpenAI Moderation remains advisory; the local model/policy will own live semantic behavior.

## Mandatory reading

Before coding, read:

- `README.md`
- `COORDINATOR-STATE.md`
- `docs/DATASET-SCHEMA.md`
- `docs/WORKER-SYSTEM.md`
- `docs/WORKER-LAUNCH-STANDARD.md`
- `policy/KNOWN-DECISIONS.md`
- `policy/SOURCE-BASELINE.md`
- issue #20

Also skim:
- `workers/README.md`
- issues #3–#11 to understand each generator domain and ID range;
- W00 branch/interview only enough to understand that policy is still changing.

Do not treat unfinished W00 answers as frozen policy.

## Dataset design principles you must preserve

The synthetic corpus is split by semantic domain, not alphabetically.

Planned generators:
- G01 Minecraft gameplay/PvP/property/roleplay;
- G02 real-world threats/stalking/doxxing;
- G03 harassment/toxicity;
- G04 self-harm;
- G05 hate/identity;
- G06 sexual/minor;
- G07 dangerous real-world instructions;
- G08 evasion/split-message/adversarial context;
- G09 benign/hard negatives.

Every worker should produce high-value examples, including:
- obvious positives;
- obvious negatives;
- boundary examples;
- minimal contrasting pairs;
- split/multi-message cases;
- false-positive traps;
- false-negative traps;
- evasions/obfuscation;
- quote/report/counterspeech cases;
- cases modeled after known production failures.

The tooling should help detect low-quality generation without pretending it can semantically judge Policy v1.

## Required functionality

Build maintainable tooling under something like `tools/dataset_qa/`.

### 1. JSONL/schema validation

For each line:
- parse JSON;
- enforce required fields from `docs/DATASET-SCHEMA.md`;
- validate field types;
- validate message arrays;
- validate `target_index`;
- validate enum/vocabulary values against a central configurable vocabulary;
- produce clear `file:line` diagnostics.

Do not hard-wire unfinished policy in a way that is difficult to update.

### 2. Example-ID validation

Support declared worker ranges:
- G01-0001..G01-0500;
- ...
- G09-0001..G09-0500.

Detect:
- duplicate IDs;
- missing IDs;
- wrong prefix;
- out-of-range IDs;
- malformed zero-padding.

Make range definitions configurable.

### 3. Exact duplicate detection

Normalize carefully over the **entire multi-message sequence**, not only the target text.

Normalization can reasonably handle:
- Unicode normalization;
- case normalization for duplicate comparison;
- whitespace normalization;
- optionally punctuation normalization.

But do **not** destroy adversarially meaningful differences such as:
- `kys` vs `k y s`;
- `irl` vs no `irl`;
- Minecraft vs real-world cue;
- different speakers;
- different message boundaries/order;
- different platform/channel hints.

Output exact duplicate groups.

### 4. Near-duplicate candidate detection

Provide a deterministic similarity report suitable for human review.

The tool may use character/token similarity or embeddings only if lightweight/reproducible, but it must **not automatically delete** near-duplicates.

Flag likely:
- trivial wording swaps;
- template-spam families;
- examples where only a meaningless adjective/name changed.

Do not flag legitimate minimal pairs as errors merely because they are similar. Ideally distinguish:
- `near_duplicate_candidate`;
- `minimal_pair_candidate` when labels/actions intentionally differ.

### 5. Contradiction detection

For exact normalized sequences and very-close candidates, flag:
- same inputs with different labels;
- same inputs with different actions;
- suspicious reason-code conflicts.

Do not auto-resolve. W11/coordinator/owner decides.

### 6. Family/group support

We need paraphrase/minimal-pair families to stay together when W11 later builds train/validation/evaluation splits.

Provide one of:
- optional `family_id` validation;
- a sidecar manifest;
- deterministic family suggestions.

Do **not** create final splits in W17.

### 7. Statistics/report

Generate deterministic summary data:
- number of records;
- source;
- domain;
- difficulty;
- platform_hint;
- label;
- action;
- number of messages per example;
- proportion of multi-message examples;
- reason-code counts;
- duplicate/near-duplicate counts;
- missing/invalid field counts.

Prefer machine-readable JSON plus human-readable text/Markdown.

### 8. Generator-worker UX

Document one or two commands W02–W10 can run before opening PRs, for example conceptually:

```bash
python -m tools.dataset_qa validate data/synthetic/G01-gameplay.jsonl --range G01:1-500
python -m tools.dataset_qa report data/synthetic/G01-gameplay.jsonl
```

The exact CLI is your design, but make it simple and deterministic.

### 9. Tests and CI

Add unit tests for:
- malformed JSON;
- invalid schema;
- duplicate IDs;
- missing IDs;
- exact duplicate sequence;
- valid minimal pair;
- contradictory label/action;
- multi-message normalization;
- same text with different speaker/message boundaries;
- obfuscated variants that must remain distinct;
- deterministic report output.

Add a CI hook if appropriate. Keep it scoped so docs-only changes do not become brittle.

## Important boundaries

- Policy v1 is unfinished. Do not invent final moderation decisions.
- Do not generate the 500-example datasets.
- Do not create final train/validation/eval splits; W11 owns that.
- Do not train a model; W12 owns that.
- Do not inspect or use raw production chat.
- Do not modify RoseChat, Ticket Bot, EnthusiaStaff, or central runtime behavior.
- Do not silently “fix” a contradictory example; report it.
- Do not make near-duplicate detection so aggressive that intentional minimal pairs become unusable.

## Branch and deliverables

Create `w17/dataset-qa-tooling` from live AI-Moderation-API `main`.

Deliver:
- QA package/tools;
- `docs/DATASET-QA.md`;
- tests;
- CI integration if justified;
- examples/fixtures that are synthetic and clearly non-policy-authoritative;
- PR to `main`.

PR description must include:
- exact head;
- commands to run;
- tests/CI result;
- known limitations;
- explicit statement that no policy labels were invented and no production data was used.

Do not merge your own PR.