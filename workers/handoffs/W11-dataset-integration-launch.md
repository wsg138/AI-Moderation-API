# W11 launch packet — Dataset integration, deduplication, leakage audit, and frozen splits

## Identity

You are **W11**, the dataset-integration worker for Enthusia AI Moderation.

Authoritative issue: **#12 — W11 — Dataset integration, deduplication, and leakage audit**.

Repository: `wsg138/AI-Moderation-API`.

Create branch **`w11/dataset-integration` from the current live `main` when you start**. Live GitHub is authoritative; do not use a stale SHA if main has moved. Open one PR to `main` and do not self-merge.

This packet is self-contained. Read the repository sources listed below before changing anything.

## Project goal

Enthusia is building one central modular moderation service used by Minecraft/RoseChat and Discord, with EnthusiaStaff remaining the review/sanction authority.

The moderation service must understand Minecraft/Discord semantics rather than treating generic Internet-safety scores as policy. Examples:

- Minecraft `im gonna kill you` can be ordinary gameplay and Policy v1 allows it under the Minecraft gameplay prior.
- Discord general does not automatically inherit that gameplay prior.
- explicit real-world continuations such as school/house/in-person threats must not be lost across split messages;
- `kys` is BLOCK + strike;
- ordinary low-level toxicity such as `you suck` must not be overblocked merely because a generic model dislikes it;
- Minecraft TNT requests are benign; real-world explosive-construction requests are blocked.

W11 exists to turn the nine independently generated synthetic corpora into a leakage-safe, contradiction-audited training/evaluation foundation for W12. **W11 does not train the model.**

## Current accepted corpus state

All nine generator PRs have now been coordinator-reviewed, accepted, merged, and verified on `main`.

The accepted synthetic corpus is exactly **4,500 records**:

- G01: `data/synthetic/G01-gameplay.jsonl`
- G02: `data/synthetic/G02-real-world-threats.jsonl`
- G03: `data/synthetic/G03-harassment.jsonl`
- G04: `data/synthetic/G04-self-harm.jsonl`
- G05: `data/synthetic/G05-hate-identity.jsonl`
- G06: `data/synthetic/G06-sexual-minor.jsonl`
- G07: `data/synthetic/G07-dangerous-instructions.jsonl`
- G08: `data/synthetic/G08-evasion-context.jsonl`
- G09: `data/synthetic/G09-benign-hard-negatives.jsonl`

Relevant accepted merge commits:

- G01 / PR #34: `8d4df80...`
- G02 / PR #31: `5592c5c...`
- G04 / PR #36: `ccba2f3...`
- G05 / PR #30: `2334167...`
- G06 / PR #38: `f7b3e49...`
- G07 / PR #33: `f021fe2...`
- G09 / PR #35: `38e4919...`
- G03 / PR #32: merge `07cb2af21459983be036134a17a14b590fe8c56b`
- G08 / PR #37: merge `49dc7fb0e443351f346fb846c55fcaf6aea5c947`

The exact main SHA immediately after the final G08 merge was `49dc7fb0e443351f346fb846c55fcaf6aea5c947`, and post-merge `service-ci` run #62 succeeded. If main has moved since then, re-read it and reconcile before starting.

### Important G03/G08 cleanup already completed

Do not redo these fixes unless live evidence contradicts them.

G03 final accepted cleanup:
- 53 redundant same-profile/same-outcome exact-sequence copies were materially rewritten;
- remaining exact normalized message-sequence groups: **39 / 82 records**;
- all 39 are intentional contrasts and each exact-wording group shares one family;
- zero exact cross-worker collisions against accepted G01/G02/G04/G05/G06/G07/G09 at review time;
- zero exact normalized golden collisions;
- canonical QA: 500 records, 0 errors, 0 warnings, 0 exact duplicate groups, 7 near candidates.

G08 final accepted cleanup:
- 5 redundant same-profile/same-outcome exact-sequence groups were rewritten;
- the previously identified G01 collisions at G08-0441 and G08-0459 were rewritten;
- remaining exact normalized message-sequence groups: **23 / 53 records**;
- all 23 are intentional profile/context contrasts and each exact-wording group shares one family;
- zero exact cross-worker collisions at review time;
- zero exact normalized golden collisions;
- canonical QA: 500 records, 0 errors, 0 warnings, 0 exact duplicate groups, 103 near candidates.

These within-worker family repairs do **not** replace W11's cross-corpus audit.

## Mandatory sources

Before editing, read at minimum:

- issue #12 and current PR/branch state if one exists;
- `COORDINATOR-STATE.md`;
- `docs/WORKER-SYSTEM.md`;
- `docs/WORKER-LAUNCH-STANDARD.md`;
- `docs/DATASET-SCHEMA.md`;
- `docs/DATASET-QA.md`;
- `docs/OWNER-POLICY-GOLDEN-SET.md`;
- `policy/POLICY-v1.md`;
- `policy/INTERVIEW-DECISION-MAP.md`;
- `policy/UNRESOLVED-DECISIONS.md`;
- both raw `policy/interviews/*.jsonl` files when a policy contradiction needs source-level interpretation;
- all nine synthetic JSONL files and reports;
- `data/eval/owner-policy-v1.jsonl`;
- `data/eval/owner-policy-v1-manifest.json`;
- the current QA implementation under `tools/dataset_qa` (or its live equivalent).

Policy source hierarchy:
1. latest direct owner answer in raw interview records;
2. Policy v1 when it faithfully consolidates that answer;
3. interview decision map;
4. public rules as broader context.

If two authoritative sources still conflict, **surface the conflict; do not silently choose a label**.

## Frozen owner-golden boundary

The owner-policy acceptance set is evaluation/acceptance by default, not ordinary training data.

Current frozen acceptance material contains:
- **52 direct owner-policy fixtures**;
- **35 policy-engine assertions**;
- traceability coverage for all **84 owner interview records**.

W11 must protect this unseen signal.

Requirements:
- do not put exact golden fixtures into the ordinary training split;
- detect exact and near/trivial synthetic leakage into golden;
- keep related paraphrase/minimal-pair families from crossing train/validation/test boundaries;
- if a synthetic example is too close to a golden fixture, flag it and either keep it out of training or propose a coordinator-reviewed repair;
- do not “fix” leakage by editing the frozen golden set;
- if a golden fixture is ever deliberately promoted to training later, that requires a versioned golden-set decision outside W11.

Three policy-only provenance items are explicitly policy-supported but not raw-interview-attributed:
- mirrored messages count once;
- fail-open / missing-memory-does-not-invent behavior;
- the working ~24h recent-threat target-safety-check rule.

Do not invent interview IDs for them.

## Policy-v1 decision dimensions

Do not collapse these into a single label:

1. semantic meaning;
2. message action;
3. review priority;
4. strike/evidence recommendation;
5. temporary containment recommendation;
6. support/safety flow;
7. human punishment decision.

Runtime message action is `ALLOW` or `BLOCK`. Review is a separate dimension.

Review: `NONE | NORMAL | URGENT`.
Containment: `NONE | MUTE`.
Support: `NONE | SELF_HARM_CHECK | TARGET_SAFETY_CHECK`.

Current Policy-v1 semantic vocabulary:

`SAFE`, `GAMEPLAY_VIOLENCE`, `LOW_LEVEL_HARASSMENT`, `SEVERE_HARASSMENT`,
`STAFF_TARGETED_ABUSE`, `REAL_WORLD_THREAT`, `SELF_HARM_INSTRUCTION`,
`SELF_HARM_INTENT`, `THIRD_PARTY_SELF_HARM_CONCERN`, `HATE`, `SLUR_USE`,
`SEXUAL_CONTENT`, `SEXUAL_MINOR`, `DOXXING`, `BLACKMAIL`, `GROOMING`,
`DANGEROUS_REAL_WORLD_INSTRUCTIONS`, `AMBIGUOUS_REVIEW`.

## Important settled policy anchors

Use these as audit anchors; read Policy v1/raw records for exact details.

- Minecraft generic game-violence language can be ALLOW under the gameplay prior.
- Discord general needs actual game context rather than inheriting Minecraft's prior.
- explicit split real-world threats are BLOCK; distant unrelated messages should not be speculatively stitched together.
- ordinary profanity/low-level game toxicity can be ALLOW.
- repeated same-target harassment, ignored stop requests, and coordinated dogpiles can escalate.
- direct targeted staff abuse is BLOCK + strike; good-faith criticism/appeal stays allowed.
- directed self-harm abuse such as `kys` is BLOCK + strike.
- genuine first-person self-harm disclosure is a safety/support problem, not punishment reputation.
- safety memory must remain conceptually isolated from punishment reputation.
- actual prohibited slur use is BLOCK + strike, including later-owner-settled quoted/counterspeech/reclaimed actual-use cases; reference-only wording such as `the n-word` can be allowed.
- public sexual/NSFW content is blocked; `send nudes` is BLOCK + strike.
- self-reported age alone is a clue, not reliable proof of minor status.
- real doxxing and blackmail are severe; AI still never owns bans.
- dangerous-instruction scope resolved for Policy v1 is specifically real-world explosive-construction requests versus Minecraft/high-level/historical discussion. Do not broaden it into weapons/poisons/malware.

## Unresolved policy edges — preserve as unresolved

W11 must not manufacture labels to fill these gaps:

1. Discord bot DMs.
2. Exact boundary for graphic first-person self-harm disclosure.
3. Consensual explicit adult PM content.
4. Grooming where minor status is genuinely uncertain.
5. Broader dangerous-instruction categories beyond resolved explosive examples.
6. What happens to an apparent-doxxing strike if information is later proven fake.
7. Complete threat-severity -> containment-duration matrix.
8. Exact blackmail containment duration.
9. Exact accidental lexical slur/substring false-positive behavior.

If the merged corpus accidentally answers one of these, flag it as a policy contradiction and stop short of silently relabeling it.

## W11 required work

### 1. Whole-corpus validation

Validate all 4,500 records together, not as nine isolated files.

Confirm:
- IDs/ranges/schema;
- enums and required fields;
- reason-code validity;
- channel/profile validity;
- containment/duration consistency;
- support-flow consistency;
- no exempt-channel semantic training records;
- no real personal data or production chat;
- no operational dangerous-instruction recipes.

Use the canonical QA tool, but do not treat “validator green” as sufficient.

### 2. Exact deduplication audit

Build a deterministic cross-corpus exact audit with at least:
- normalized ordered message text;
- ordered speaker identity/role where available;
- channel/profile;
- policy outcomes;
- family IDs.

Distinguish:
- genuinely redundant duplicates;
- intentional identical-wording contrasts;
- mirrored conceptual examples that differ meaningfully.

Do not delete intentional minimal pairs merely to make a duplicate counter zero.

### 3. Near-duplicate / template-reuse audit

Audit across all workers for:
- paraphrase leakage;
- repeated sentence skeletons;
- small noun/name swaps;
- small template pools;
- mechanically repeated context structures;
- examples that are “different” only because timestamps/metadata changed.

Pay particular attention to the large advisory candidate pools from G02 and G08 and to any new cross-worker candidates that only become visible after integration.

Produce machine-readable candidate output plus a human disposition summary.

### 4. Contradiction detection

Find near-identical message/context cases with incompatible:
- semantic label;
- action;
- review priority;
- strike;
- containment/duration;
- support flow.

For each contradiction:
- identify all example IDs;
- state which dimensions differ;
- trace the relevant Policy-v1 / owner source;
- classify as intentional contrast, data bug, or unresolved policy question.

**Never silently relabel a policy disagreement.** Mechanical/data errors may be fixed when the source policy is unambiguous; policy ambiguity must be surfaced to coordinator/owner.

### 5. Family reconciliation

Audit `family_id` across all nine corpora.

Requirements:
- exact-wording contrasts must not be split across different families;
- paraphrases/minimal pairs that test one boundary should stay grouped for leakage-safe splitting;
- unrelated examples must not be grouped merely because they share a broad domain;
- cross-worker families that represent the same contrast should be reconciled or mapped through a deterministic integration-family layer.

Do not destroy original provenance. If you create an integration-level family mapping, preserve source file/example IDs.

### 6. Golden leakage audit

Compare all 4,500 synthetic records against the frozen owner golden set using multiple views:
- exact normalized sequence;
- high text similarity;
- family/template similarity;
- minimal-pair semantic closeness.

Flag exact/trivial leakage aggressively. The point is to preserve genuinely unseen acceptance evidence, not merely to avoid byte-identical text.

### 7. Distribution / coverage audit

Report whole-corpus distributions for:
- domain;
- semantic label;
- action;
- review priority;
- strike;
- containment and duration;
- support flow;
- channel profile/platform;
- single vs multi-message;
- difficulty/adversarial status;
- family sizes.

Also report cross-tabs useful for finding artifacts, such as label x channel and action x domain.

Identify materially underrepresented or suspiciously overrepresented semantic regions. Do not add new policy examples in W11 merely to “balance” counts unless the issue is a mechanical gap and the coordinator explicitly approves it.

### 8. Leakage-safe train/validation/test splits

Create deterministic machine-readable split manifests for W12.

Hard rules:
- owner golden set stays separate;
- no family/minimal-pair group may cross train/validation/test;
- exact/near-duplicate groups must remain together;
- preserve useful label/channel/domain coverage in validation and test;
- avoid optimizing the split by peeking at future model performance;
- record the seed/algorithm/version so split generation is reproducible.

Prefer manifests that reference source example IDs rather than copying full records unnecessarily.

### 9. Frozen adversarial/split-message evaluation slice

Create a dedicated frozen evaluation slice emphasizing:
- split-message threat reversal;
- long-gap non-linkage;
- obfuscation/evasion;
- Minecraft vs Discord-general vs Discord-gaming flips;
- self-harm instruction vs game/death language;
- slur actual-use vs reference-only;
- harassment stop/consent/dogpile contrasts;
- sexual/minor reliability-of-age evidence;
- real explosive request vs Minecraft/history;
- quote/report/reply-vs-endorsement.

Keep families intact and keep this slice out of ordinary training.

### 10. Integration report

Produce a detailed report that includes:
- exact corpus counts;
- QA results;
- exact/near duplicate findings and dispositions;
- contradictions and source traceability;
- family reconciliation;
- golden leakage findings;
- distributions/cross-tabs;
- split sizes and family integrity checks;
- frozen adversarial slice makeup;
- known limitations;
- any owner/coordinator decisions still required.

## Expected deliverables

At minimum:
- deterministic integration/audit tooling in an appropriate `tools/` location;
- machine-readable train/validation/test manifests;
- machine-readable frozen adversarial/split-message evaluation manifest;
- machine-readable duplicate/leakage/contradiction audit output where useful;
- a human-readable W11 integration report under `docs/` or `data/` consistent with current repository organization;
- tests for deterministic splitting, family isolation, golden isolation, and key audit invariants.

Do not rewrite all nine source JSONL files simply to produce a split. Preserve provenance and keep source changes localized to verified data defects.

## Acceptance evidence

Before requesting review:

- canonical Dataset QA passes for all source corpora;
- W11 integration audit completes deterministically;
- total synthetic source count is still **4,500**, unless a documented coordinator-approved defect repair intentionally changes it;
- no exact/trivial golden fixture is present in the ordinary training split;
- family/minimal-pair groups do not cross split boundaries;
- frozen adversarial slice does not leak into ordinary training;
- all tests pass;
- Ruff passes;
- strict mypy passes;
- complexity gate passes;
- wheel build passes;
- exact-head GitHub CI is green.

Report exact counts and exact head SHA. Do not claim hosted Codacy clearance unless a real Codacy status/check exists on that exact head.

## Architecture / runtime boundaries

This worker is **data/integration only**.

Do not:
- train or export the classifier (W12 owns that);
- change runtime Policy-v1 API behavior;
- change RoseChat, Ticket Bot, or EnthusiaStaff;
- alter exemptions, auth, incident storage, memory, or failure behavior;
- deploy/restart production;
- enable punishments;
- use or commit raw production chat;
- add secrets;
- change the frozen owner golden set to make audit results look cleaner.

The central moderation runtime is fail-open and optional. W11 must not create any dependency that could make chat availability depend on dataset tooling.

## Upstream/downstream dependencies

Upstream complete:
- Policy v1;
- owner interview corpus;
- frozen owner golden acceptance set;
- dataset QA;
- all G01–G09 accepted synthetic corpora.

Parallel work:
- W19 / issue #39 is repairing runtime PENDING-event recovery. It does not block W11.

Downstream:
- **W12 / issue #13** may start only after W11's integrated, leakage-safe split artifacts are reviewed/accepted.
- W13/W14/W15 client integrations are separately blocked on W19 runtime recovery, not on W11.

## Privacy / safety

Repository is public.

Never commit:
- production chat;
- private player identifiers;
- runtime moderation databases;
- tokens/keys/credentials;
- operational explosive-construction recipes.

Synthetic examples may describe dangerous requests for classification purposes, but must not become instructional recipes with quantities/components/steps.

## PR behavior

Use one branch: `w11/dataset-integration`.
Open one PR to `main`.
Keep commits scoped and reviewable.
Do not merge your own PR.
Do not deploy anything.

In the PR completion comment include:
- exact head SHA;
- exact 4,500-record validation result;
- duplicate/near-duplicate/contradiction counts;
- golden leakage result;
- split sizes and family-isolation proof;
- adversarial-slice size;
- tests/CI run;
- any unresolved policy questions that require owner/coordinator action.
