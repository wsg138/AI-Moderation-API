# Dataset QA tooling

`tools/dataset_qa/` validates generator JSONL before a dataset PR is opened. It checks structure, the centralized Policy-v1 vocabulary, fixed IDs, duplicate families, and deterministic statistics, but it does not decide what a moderation label or punishment should be.

## Generator commands

W02–W10 should run the command pair for their package before opening a PR:

```bash
python -m tools.dataset_qa validate data/synthetic/G01-gameplay.jsonl --range G01:1-500
python -m tools.dataset_qa report data/synthetic/G01-gameplay.jsonl --range G01:1-500 --format markdown --output G01-qa.md
python -m tools.dataset_qa validate data/synthetic/G02-real-world-threats.jsonl --range G02:1-500
python -m tools.dataset_qa report data/synthetic/G02-real-world-threats.jsonl --range G02:1-500 --format markdown --output G02-qa.md
python -m tools.dataset_qa validate data/synthetic/G03-harassment.jsonl --range G03:1-500
python -m tools.dataset_qa report data/synthetic/G03-harassment.jsonl --range G03:1-500 --format markdown --output G03-qa.md
python -m tools.dataset_qa validate data/synthetic/G04-self-harm.jsonl --range G04:1-500
python -m tools.dataset_qa report data/synthetic/G04-self-harm.jsonl --range G04:1-500 --format markdown --output G04-qa.md
python -m tools.dataset_qa validate data/synthetic/G05-hate-identity.jsonl --range G05:1-500
python -m tools.dataset_qa report data/synthetic/G05-hate-identity.jsonl --range G05:1-500 --format markdown --output G05-qa.md
python -m tools.dataset_qa validate data/synthetic/G06-sexual-minor.jsonl --range G06:1-500
python -m tools.dataset_qa report data/synthetic/G06-sexual-minor.jsonl --range G06:1-500 --format markdown --output G06-qa.md
python -m tools.dataset_qa validate data/synthetic/G07-dangerous-instructions.jsonl --range G07:1-500
python -m tools.dataset_qa report data/synthetic/G07-dangerous-instructions.jsonl --range G07:1-500 --format markdown --output G07-qa.md
python -m tools.dataset_qa validate data/synthetic/G08-evasion-context.jsonl --range G08:1-500
python -m tools.dataset_qa report data/synthetic/G08-evasion-context.jsonl --range G08:1-500 --format markdown --output G08-qa.md
python -m tools.dataset_qa validate data/synthetic/G09-benign-hard-negatives.jsonl --range G09:1-500
python -m tools.dataset_qa report data/synthetic/G09-benign-hard-negatives.jsonl --range G09:1-500 --format markdown --output G09-qa.md
```

`--range auto` remains the default. It recognizes configured ID ranges from the filename or a single valid ID prefix. `G01` through `G09` remain the admitted synthetic-generator ranges; W21 reserves `G21-0001..G21-0500` for candidate-only adversarial/evasion development data under `data/candidates/`. Use `--range none` only for partial fixtures or non-generator data.

Validation exits non-zero when errors exist. Warnings do not fail the command. Diagnostics use deterministic `file:line` output. `validate --format json` and `report --format json` are available for machine-readable consumers.

### Valid Policy-v1 record

Every generator record must include all Policy-v1 outcome fields. `family_id` is optional.

```json
{
  "example_id": "G01-0001",
  "policy_version": "v1",
  "source": "synthetic",
  "domain": "real_world_threat",
  "difficulty": "hard",
  "platform_hint": "minecraft",
  "channel_profile": "minecraft_public",
  "messages": [
    {"speaker": "A", "offset_ms": -1800, "text": "im gonna stab you"},
    {"speaker": "A", "offset_ms": 0, "text": "irl"}
  ],
  "target_index": 1,
  "label": "REAL_WORLD_THREAT",
  "action": "BLOCK",
  "review_priority": "URGENT",
  "strike": true,
  "containment": "MUTE",
  "containment_duration_seconds": 604800,
  "support_flow": "NONE",
  "reason_codes": ["split_message_context", "explicit_real_world_cue", "targeted_violence"],
  "notes": "Synthetic hard pair.",
  "family_id": "threat.real-world-cue.001"
}
```

`containment_duration_seconds` is required but nullable. Use `null` with `containment: NONE`. With `MUTE`, use a positive integer only when owner policy supplies a concrete duration; `null` is permitted for an explicitly unresolved duration and produces a warning for human confirmation.

### Errors vs warnings

Errors make the command fail: missing required fields, unknown enums/reason codes, non-boolean `strike`, invalid/non-positive durations, `NONE` containment with a duration, malformed/missing IDs, exact duplicates, and exact label/action contradictions.

Warnings require human review but do not fail the command. They include unresolved/null `MUTE` duration, exempt channel profiles in semantic data, empty reason-code lists, and very-close possible contradictions.

Do not silence a warning by inventing policy. If a record hits `policy/UNRESOLVED-DECISIONS.md`, preserve the schema-supported uncertainty and call it out in the generator report/PR.

## What is checked

The validator checks:

- one JSON object per JSONL line;
- required record/message fields and field types;
- `target_index` bounds;
- current label/action/channel-profile/review-priority/containment/support-flow enums and full reason-code vocabulary;
- strict boolean `strike` and nullable/positive-integer containment duration consistency;
- exempt-profile and unresolved-mute-duration warnings;
- optional `family_id` syntax;
- `GNN-NNNN` ID formatting, duplicate IDs, prefix/range errors, and missing IDs;
- exact duplicate normalized multi-message inputs;
- exact label/action contradictions and suspicious reason-code conflicts;
- deterministic near-duplicate/minimal-pair candidates;
- summary counts for source, domain, difficulty, platform, channel profile, label, action, review priority, strike, containment, support flow, containment-duration coverage, message count, multi-message proportion, reason codes, and family IDs.

The canonical Policy-v1 vocabulary and generator ranges live in `tools/dataset_qa/config.json`. Later owner-policy vocabulary changes should update that centralized config and focused tests rather than scattering constants through the implementation.

## Normalization and duplicate safety

Exact duplicate normalization applies Unicode NFKC, case folding, and whitespace collapsing to text. It preserves the full sequence structure: platform hint, target index, speaker, message offsets, message boundaries, and order all remain part of the fingerprint. Punctuation and internal token spacing are not removed, so adversarial distinctions such as `kys` versus `k y s` remain distinct.

Near-duplicate matching only compares examples with the same structural context. It reports candidates for human review and never deletes or rewrites data. Similar examples with different labels/actions are reported as `minimal_pair_candidate`; extremely close differing decisions also receive a warning so W11/coordinators can determine whether the pair is intentional or contradictory. Near-duplicate and minimal-pair output is advisory and always requires human review.

## Families

Dataset records may optionally add:

```json
"family_id": "threat.school-context.001"
```

The validator checks only its configured syntax. Reports also emit deterministic family suggestions from exact/near-related examples. W17 does not create train/validation/evaluation splits; W11 remains responsible for keeping accepted families together when splits are built.

## CI

The repository CI already runs Ruff, mypy, the project complexity checker, tests, and a wheel build. The complexity checker includes `tools/dataset_qa/`. CI also validates any `data/synthetic/*.jsonl` file present in a PR using automatic generator-range detection. Docs-only changes outside the existing scoped CI paths do not trigger this workflow.

## Known limitations

Near-duplicate detection uses deterministic `difflib.SequenceMatcher` comparisons within structurally matching groups. This is lightweight and reproducible for 500-record generator files, but it is a candidate finder rather than semantic similarity. It can miss paraphrases with large wording changes and may still flag intentional template families. Human review remains required.

The validator intentionally does not resolve the remaining owner-policy edges: Discord bot DMs, graphic self-harm disclosure, consensual explicit adult PM boundaries, uncertain-age grooming, broader dangerous instructions, fake-doxxing strike cleanup, the full threat-duration matrix, blackmail duration, or accidental lexical slur edges. No production chat data is required or consumed.
