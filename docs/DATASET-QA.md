# Dataset QA tooling

`tools/dataset_qa/` validates generator JSONL before a dataset PR is opened. It is intentionally policy-independent: it checks structure, declared vocabulary, IDs, duplicate families, and deterministic statistics, but it does not decide what a moderation label should be.

## Generator commands

Run validation first:

```bash
python -m tools.dataset_qa validate data/synthetic/G01-gameplay.jsonl --range G01:1-500
```

Then produce a review report:

```bash
python -m tools.dataset_qa report data/synthetic/G01-gameplay.jsonl --range G01:1-500 --format markdown --output G01-qa.md
```

`--range auto` is the default. It recognizes `G01` through `G09` from the filename or a single valid ID prefix and checks the configured `1..500` range. Use `--range none` only for partial fixtures or non-generator data.

Validation exits non-zero when errors exist. Warnings do not fail the command. Diagnostics use deterministic `file:line` output. `validate --format json` and `report --format json` are available for machine-readable consumers.

## What is checked

The validator checks:

- one JSON object per JSONL line;
- required record/message fields and field types;
- `target_index` bounds;
- current label/action/reason-code vocabulary;
- optional `family_id` syntax;
- `GNN-NNNN` ID formatting, duplicate IDs, prefix/range errors, and missing IDs;
- exact duplicate normalized multi-message inputs;
- exact label/action contradictions and suspicious reason-code conflicts;
- deterministic near-duplicate/minimal-pair candidates;
- summary counts for source, domain, difficulty, platform, label, action, message count, multi-message proportion, reason codes, and family IDs.

The current vocabulary and generator ranges live in `tools/dataset_qa/config.json`. Policy v1 is unfinished, so later policy/schema changes should update that file rather than scattering constants through the implementation.

## Normalization and duplicate safety

Exact duplicate normalization applies Unicode NFKC, case folding, and whitespace collapsing to text. It preserves the full sequence structure: platform hint, target index, speaker, message offsets, message boundaries, and order all remain part of the fingerprint. Punctuation and internal token spacing are not removed, so adversarial distinctions such as `kys` versus `k y s` remain distinct.

Near-duplicate matching only compares examples with the same structural context. It reports candidates for human review and never deletes or rewrites data. Similar examples with different labels/actions are reported as `minimal_pair_candidate`; extremely close differing decisions also receive a warning so W11/coordinators can determine whether the pair is intentional or contradictory.

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

The tooling uses the provisional vocabulary in `config.json`; it does not infer new Policy v1 labels, actions, or reason codes. No production chat data is required or consumed.
