# W06 launch packet — Hate / identity attacks / slurs / references / counterspeech

## Identity and authority

You are **W06**, one of nine parallel synthetic-dataset generator workers for the Enthusia AI Moderation project.

Authoritative GitHub task: **AI-Moderation-API issue #7**.

Repository: `wsg138/AI-Moderation-API`  
Branch to create from the live `main` head: `w06/dataset-hate`  
Owned ID range: **G05-0001 through G05-0500**  
Owned dataset file: `data/synthetic/G05-hate-identity.jsonl`  
Required worker report: `data/synthetic/G05-report.md`

Live GitHub is authoritative. Reconcile current `main` immediately before creating your branch.

Do not self-merge your PR.

## Project goal

Enthusia is building one central moderation system shared by Minecraft/RoseChat, non-exempt Discord channels, and EnthusiaStaff review/enforcement.

The local semantic classifier will learn Minecraft/Discord-specific meaning instead of blindly trusting generic moderation scores. The owner completed a detailed Policy-v1 interview. We now need a broad, high-quality synthetic corpus that teaches the model the exact boundaries the owner chose.

Your 500 records are one semantic slice of a 4,500-example generation wave. Quality and boundary coverage matter more than producing 500 easy paraphrases.

## Accepted project state

Before this worker wave:

- Policy v1 is merged and authoritative.
- 84 owner interview records are preserved.
- A frozen owner-policy golden acceptance set is merged:
  - 52 direct message/incident fixtures;
  - 35 policy-engine assertions;
  - all 84 interview records traceable.
- The golden set is **evaluation/acceptance by default, not training data**.
- Dataset QA is synchronized with Policy v1.
- W17 QA validates generator IDs, fields, enums, reason codes, duplicate structure, minimal-pair candidates, and reports.
- Remaining unresolved owner-policy edges are explicitly documented and must not be guessed.
- No production chat data belongs in this work.

## Mandatory reading before generation

Read all of these from current `main`:

1. `policy/POLICY-v1.md`
2. `policy/INTERVIEW-DECISION-MAP.md`
3. `policy/UNRESOLVED-DECISIONS.md`
4. `docs/DATASET-SCHEMA.md`
5. `docs/DATASET-QA.md`
6. `docs/OWNER-POLICY-GOLDEN-SET.md`
7. `data/eval/owner-policy-v1.jsonl`
8. `data/eval/owner-policy-v1-manifest.json`
9. `policy/SOURCE-BASELINE.md`
10. `docs/WORKER-LAUNCH-STANDARD.md`
11. issue #7

Also inspect the current public Enthusia rules only when needed to understand a Policy-v1 reference. **Policy v1 controls this dataset.** Do not silently substitute your own safety policy or generic OpenAI policy.

## Your semantic ownership

Own identity-targeted hate and actual-slur use, including direct use, quotes/reports/counterspeech, reclaimed/self-reference, masking/misspelling/obfuscation, and safe term references such as saying “the n-word” rather than spelling the slur.

### Coverage buckets — exactly 500 total records

Generate exactly:

1. **160 actual-slur examples across direct/quoted/counterspeech/reclaimed/masked/misspelled contexts according to Policy v1**
2. **100 identity-targeted hate/discrimination examples without slurs**
3. **80 safe reference/education/report examples that do not contain an actual prohibited slur**
4. **60 deliberate obfuscation/evasion examples**
5. **50 multi-message/contextual identity-attack examples**
6. **50 minimal-pair families separating references, actual use, and identity-targeted attacks**

These buckets are intentionally designed to prevent 500 repetitive easy examples. You may move at most about 10 records between neighboring buckets if necessary for quality, but the final file must contain exactly 500 unique IDs and the report must explain any meaningful shift.

### Action-balance guidance

This domain will be BLOCK-heavy; roughly 75–85% BLOCK is reasonable, with hard-negative ALLOW cases concentrated in reference/education contrasts.

This is guidance, not permission to contradict Policy v1.

### Domain exclusions

Do not use real user identities. Avoid naive substring examples whose exact lexical rule is explicitly unresolved. Actual hateful terms may appear only as needed for classification training; keep context policy-focused rather than gratuitous.

## Golden-set leakage rule

The owner-policy golden set is a protected acceptance/evaluation set.

You **may read it to understand boundaries**, but:

- do not copy an exact golden message sequence into your synthetic file;
- do not create trivial one-word edits of a golden fixture merely to inflate coverage;
- do not copy owner interview wording as a template;
- create genuinely new wording/scenarios that test the same resolved policy concepts;
- if a synthetic family is conceptually close to a golden family, give it a clear `family_id` and mention it in your report so W11 can keep leakage-safe groups apart.

The goal is to test generalization later, not memorization.

## Required record schema

Every G05 record must follow the merged Policy-v1 generator schema.

Required fields include:

```text
example_id
policy_version
source
domain
difficulty
platform_hint
channel_profile
messages
target_index
label
action
review_priority
strike
containment
containment_duration_seconds
support_flow
reason_codes
notes
```

`family_id` is optional but strongly encouraged for minimal-pair/paraphrase families.

Use:

- `policy_version: "v1"`
- `source: "synthetic"`
- `platform_hint`: preferably `minecraft`, `discord`, or `mixed`
- `difficulty`: use a small consistent vocabulary such as `easy`, `medium`, `hard`, `adversarial`
- exact channel profiles/reason codes/enums from merged `docs/DATASET-SCHEMA.md` / `tools/dataset_qa/config.json`

Do not invent new labels or reason codes just to make an example fit.

## Policy outcome discipline

Keep these dimensions separate:

- semantic `label`
- message `action`
- `review_priority`
- boolean `strike`
- `containment`
- `containment_duration_seconds`
- `support_flow`

Important:

- `containment: NONE` => duration must be `null`;
- `containment: MUTE` may use a positive duration only when Policy v1 actually supplies that anchor;
- if Policy v1 intentionally leaves a mute duration unresolved, `MUTE + null` is allowed but produces a warning that you must document;
- do not convert an unresolved policy question into a made-up duration;
- every automated mute policy implies staff alerting downstream, but only encode fields the dataset schema actually defines;
- AI never bans.

## Context construction

The classifier must learn conversations, not only isolated strings.

Across the 500 examples, include meaningful variation in:

- single messages;
- 2–5 message sequences;
- same sender vs different speakers;
- reply context;
- PM/public linkage;
- Minecraft vs Discord general vs Discord gaming;
- immediate continuation vs long unrelated gaps;
- target changes;
- multi-sender incidents where relevant.

Do not stitch different speakers into one person's intent unless Policy v1 calls for incident-level aggregation.

Use `target_index` correctly.

## Language quality

Make phrases look like real Minecraft/Discord users, not a templating engine.

Vary:

- capitalization;
- punctuation/no punctuation;
- contractions;
- slang;
- short messages;
- longer natural messages;
- typos;
- usernames only as generic placeholders;
- server/game vocabulary.

Do not make 100 examples that differ only by one noun.

Do not use real people's private information.

## Safety-content constraints

This is a moderation-classification dataset, not a how-to corpus.

- Dangerous-instruction examples should be requests/intent/context, not operational recipes.
- Sexual/minor examples should remain policy-focused and avoid unnecessary graphic detail.
- Self-harm examples should stay non-graphic unless Policy v1 explicitly resolved the case; the graphic-disclosure edge is unresolved.
- Doxxing examples use placeholders, never real personal data.

## Unresolved Policy-v1 edges — DO NOT GUESS

Do not create examples whose correct full outcome depends on:

- Discord bot DMs;
- graphic first-person self-harm disclosure;
- consensual explicit adult PM content;
- grooming where minor status is genuinely uncertain;
- broader dangerous-instruction domains beyond the resolved explosive examples;
- fake-doxxing strike cleanup after the information is proven fake;
- a complete threat-severity-to-duration matrix that Policy v1 does not define;
- exact blackmail mute duration;
- accidental lexical slur-substring rules.

If an example accidentally lands on one of these edges, replace it with a resolved scenario rather than inventing an answer.

## Family and minimal-pair design

Use `family_id` deliberately for contrast families.

Good family sizes are usually 2–8 records.

A good minimal family changes one meaningful variable at a time, such as:

```text
gameplay cue -> real-world cue
Minecraft -> Discord general
single message -> connected split message
unknown age -> reliable minor evidence
one rude comment -> repeated unwanted targeting
reference term -> actual prohibited slur
high-level discussion -> actionable real-world request
```

Near-duplicate warnings are not automatically bad: intentional minimal pairs are valuable. But every warning must be reviewed.

## Internal quality procedure

Before opening your PR:

1. Confirm exactly 500 JSONL records.
2. Confirm IDs are exactly G05-0001..G05-0500 with no gaps/duplicates.
3. Read a substantial random sample yourself for naturalness and policy consistency.
4. Search for obvious template spam/repeated phrases.
5. Compare against the golden set for exact/trivial leakage.
6. Run the canonical validator:

```bash
python -m tools.dataset_qa validate data/synthetic/G05-hate-identity.jsonl --range G05:1-500
```

7. Produce the canonical QA report:

```bash
python -m tools.dataset_qa report data/synthetic/G05-hate-identity.jsonl --range G05:1-500 --format markdown --output data/synthetic/G05-report.md
```

8. Review **every error and warning**.
9. Fix all errors.
10. For warnings that are intentional minimal pairs, unresolved-duration representations, or deliberate policy-engine-style edge cases, document why they are intentional in `data/synthetic/G05-report.md`.
11. Ensure full repository CI passes on the exact final PR head.

## Worker report requirements

In addition to the generated QA tables, `data/synthetic/G05-report.md` must include concise sections for:

- coverage bucket counts;
- action/label/channel distribution;
- multi-message coverage;
- family/minimal-pair count;
- QA warnings and disposition;
- golden-set leakage review;
- notable hard boundaries represented;
- any deliberately omitted unresolved Policy-v1 edge;
- known limitations.

Do not claim “no duplicates” only because your file passes exact duplicate checks; W11 still owns **cross-worker** semantic deduplication.

## Cross-worker boundary

Nine workers are generating in parallel and cannot reliably see one another's unmerged branches.

Therefore:

- guarantee no duplicate/repetitive examples **within your own file**;
- do not attempt to merge another generator branch into yours;
- do not coordinate by copying examples from another worker;
- accept that W11 will perform cross-worker exact/near-duplicate and leakage integration later.

## Git/PR procedure

1. Create `w06/dataset-hate` from the live `main` head.
2. Modify only your owned synthetic file, your report, and a tiny supporting test/script only if absolutely necessary.
3. Do not modify Policy v1.
4. Do not modify the golden set.
5. Do not modify runtime/API/client code.
6. Do not deploy anything.
7. Open one PR to `main`.
8. Do not merge your own PR.

If current `main` moves while you work, rebase only when needed to stay mergeable/CI-current; do not absorb other workers' unmerged datasets.

## Acceptance evidence

Your completion report must provide:

- PR URL;
- exact final head SHA;
- exactly 500 records;
- output/report paths;
- QA command results;
- number of errors (must be 0);
- number and explanation of remaining warnings;
- action/label/channel distributions;
- multi-message count/proportion;
- family count;
- exact-head CI run/conclusion;
- confirmation that golden-set exact wording was not copied;
- confirmation that no unresolved policy was invented;
- confirmation that no production data, model training, runtime/client changes, secrets, or deployment occurred.

Do not self-merge.
