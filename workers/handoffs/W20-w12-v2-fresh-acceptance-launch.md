# W20 — Fresh unseen W12-v2 acceptance set

Repository: `wsg138/AI-Moderation-API`

Issue: #43 — Fresh unseen W12 v2 acceptance set

Use the EXISTING branch only:

- Branch: `w20/fresh-acceptance-set`
- Branch was created from live `main` at coordinator launch.
- Do not create a replacement branch.
- Do not modify or merge PR #42.
- Do not train or tune a model.
- Do not deploy anything.

Live GitHub is authoritative. Re-read issue #43 and current repository state before the first product commit.

## Purpose

Build the independent, versioned, unseen acceptance corpus required for W12 v2.

W12 PR #42 corrected a material preprocessing defect after the original W11 test, frozen-adversarial, and owner-golden results had already been observed. Those old held-out results are now development/superseded evidence for the old preprocessing contract and cannot be used to accept the corrected v2 model.

The current observed W12 head when this packet was prepared is:

`3aac90ca8d0d57ca2174a852f961c6b753e7205d`

That head is intentionally NOT your working branch. Your job is acceptance data only.

## Independence / anti-contamination rules

You MUST NOT inspect:

- `workers/w12/reports/heldout-*.json`;
- any per-example W12 prediction/error output;
- individual W12 model failures in PR #42 comments/reviews;
- model logits/probabilities/predictions when designing examples;
- old held-out examples for inspiration beyond automated leakage comparison.

You MAY use:

- `policy/POLICY-v1.md`;
- `policy/INTERVIEW-DECISION-MAP.md`;
- `policy/KNOWN-DECISIONS.md`;
- `policy/UNRESOLVED-DECISIONS.md`;
- `docs/DATASET-SCHEMA.md`;
- `docs/DATASET-QA.md`;
- W11 manifests/audit only for IDs/family/leakage mechanics, not for copying example wording;
- aggregate project requirements from issue #43 and coordinator state.

Do not tailor the corpus to known model weaknesses. Build it from Policy-v1 coverage requirements.

## Pre-registered scoring gates

Before generating examples, read live `main:docs/W12-V2-ACCEPTANCE-GATES.md` at or after commit
`928c4a28fef7d4ae2b02204fe271167de17699d9`.

That document was frozen before W20 results exist. Its slice coverage minima are part of
your corpus requirements. Do **not** alter the thresholds, optimize examples to a known
model output, or inspect W12 predictions. Your job remains independent corpus construction
and leakage validation; W12 will perform scoring only after W20 is reviewed/frozen.

## Required acceptance corpus

Create a new acceptance-only dataset under `data/eval/` with a clearly versioned name such as:

`w12-v2-acceptance-2026-10-05.jsonl`

and a companion manifest/report.

Target **at least 300 examples** unless a stronger coverage argument justifies a different count.

Use family IDs so minimal pairs/context variants stay grouped.

The corpus must include meaningful coverage of:

1. benign Minecraft/PvP violence;
2. real-world threats and stalking;
3. doxxing/location/privacy threats where Policy v1 is settled;
4. low-level banter vs severe harassment;
5. self-harm instruction/encouragement vs self-disclosure/support;
6. hate/slur actual use vs quotation/counterspeech/reference/reclaimed contexts;
7. sexual/minor policy and benign age-only contrasts;
8. dangerous real-world instructions vs Minecraft/fictional/game instructions;
9. ordinary benign/hard-negative chat;
10. obfuscation/evasion;
11. split-message composition;
12. context reversals where a prior phrase changes interpretation;
13. public vs private channel profiles where policy differs;
14. Discord-general/gaming vs Minecraft contexts;
15. temporal/context-linkage boundaries where Policy v1 is settled;
16. related-message/mirror semantics only where representable without inventing runtime policy.

Include:
- natural player language;
- typos and casual grammar;
- short messages;
- multi-message sequences;
- minimal contrasting pairs;
- adversarial false-positive traps;
- adversarial false-negative traps.

Avoid turning the set into obvious policy-document prose.

## Unresolved policy

Read `policy/UNRESOLVED-DECISIONS.md`.

If an example would require inventing an answer for an unresolved edge, exclude it or label it as not eligible for scored acceptance according to the existing schema/tooling. Do not silently choose a policy.

## Leakage requirements

Before freezing:

- normalized exact collision vs W11 train = 0;
- normalized exact collision vs W11 validation = 0;
- normalized exact collision vs W11 test = 0;
- normalized exact collision vs W11 frozen adversarial = 0;
- normalized exact collision vs owner golden = 0;
- inspect high-similarity candidates and rewrite/remove trivial paraphrases;
- acceptance families must not reuse W11 family identities;
- document thresholds and all retained near similarities.

Use existing dataset integration/QA normalization where possible rather than inventing incompatible leakage math.

## Schema / quality

The records must validate under current Policy-v1 dataset QA.

Preserve all required outcome dimensions. Do not collapse the problem to a single label if the schema requires action/review/strike/containment/support dimensions.

No raw production chat, private evidence, account identifiers, credentials, staff-only text, or secrets may be committed.

## Acceptance manifest contract

Use these exact top-level fields so the frozen W12 scorer can verify that it is
receiving the independently prepared corpus:

```json
{
  "contract": "w12-v2-fresh-acceptance-v1",
  "acceptance_only": true,
  "forbidden_for_training": true,
  "built_without_w12_predictions": true,
  "dataset_sha256": "<sha256 of exact JSONL bytes>",
  "record_count": 0,
  "family_count": 0
}
```

You may add additional provenance/coverage/leakage fields, but do not rename or
remove these fields.

For the dedicated benign-hard-negative quota, use
`domain: "benign_hard_negative"`.

For the allowed Minecraft/fictional dangerous-instruction contrast quota, use
`domain: "dangerous_instruction_benign_contrast"`.

These domain values are evaluation metadata only and are not part of model input.
Other policy slices should continue using the existing settled reason
codes/channel profiles/labels required by Policy v1 and dataset QA.

## Freeze manifest

Create a machine-readable manifest containing at minimum:

- acceptance set version;
- creation date;
- generator/reviewer description;
- Policy-v1 source commit;
- record count;
- family count;
- per-domain/channel/action/label/outcome distribution;
- SHA-256 of the JSONL;
- leakage audit results;
- explicit statement that no W12 predictions were inspected during construction;
- explicit statement that this set is acceptance-only and must never enter training/validation;
- one-shot evaluation rule.

## Tests/tooling

Add focused deterministic tests/tooling that prove:

- JSONL parses;
- schema validation succeeds;
- IDs/families are unique and valid;
- no exact collision with any W11 partition or owner golden;
- manifest hash/counts match;
- no forbidden partition use;
- generation/check output is deterministic if generation code is included.

Do not weaken existing quality, Ruff, mypy, or complexity gates.

## One-shot evaluation contract

Do NOT evaluate W12 yourself while building the set.

After W20 is independently reviewed/frozen:

1. record the exact W12 candidate/preprocessing/runtime head;
2. expose the frozen set for a single evaluation;
3. report results without changing the model;
4. if any semantic model/preprocessing/threshold change is made afterward, this acceptance set is burned and becomes development evidence;
5. a new unseen acceptance set is then required.

## Deliverables

- `data/eval/<versioned-acceptance>.jsonl`
- `data/eval/<versioned-acceptance>-manifest.json`
- `docs/W20-W12-V2-ACCEPTANCE-SET.md`
- validation/leakage tooling/tests
- issue #43 completion comment with exact head and evidence

## Git / review boundaries

- stay on `w20/fresh-acceptance-set`;
- one PR into `main`;
- do not self-merge;
- do not touch PR #42 model code;
- do not deploy;
- do not enable punishments;
- do not read production data;
- run exact-head CI before declaring READY.

When complete, report the exact head SHA, record/family counts, coverage summary, leakage results, tests/CI, and any unresolved concern.
