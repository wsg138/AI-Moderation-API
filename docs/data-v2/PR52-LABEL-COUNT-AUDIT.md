# PR #52 — exact-head label-count audit (public synthetic corpus only)

Audit date: 2026-10-07.
Source pull request: [#52](https://github.com/wsg138/AI-Moderation-API/pull/52).
**Exact inspected head:** `53e34e52c6c9a42a8be2ab8f772156e89d31b7e9`.

Method: fetched each of the 18 submitted `data/synthetic/G10–G27*.jsonl` files and corresponding `GXX-report.md` from the same pinned head. Parsed each of 500 JSONL records and directly compared per-label counts to the report's **`### label`** table. **This is a data/report consistency check, not semantic review, and does not re-run the full dataset QA suite.**

## Result: 12 of 18 reports have label-count mismatches

| Batch | Count table matches final JSONL? | Verified differences (final JSONL vs report) |
|---|---|---|
| G10 | **No** | SAFE 78 vs 77; AMBIGUOUS_REVIEW 25 vs 26 |
| G11 | **No** | SAFE 96 vs 75; AMBIGUOUS_REVIEW 4 vs 25 |
| G12 | **No** | SAFE 88 vs 75; AMBIGUOUS_REVIEW 12 vs 25 |
| G13 | Yes | — |
| G14 | Yes | — |
| G15 | Yes | — |
| G16 | **No** | LOW_LEVEL_HARASSMENT 49 vs 40; SAFE 88 vs 75; AMBIGUOUS_REVIEW 3 vs 25 |
| G17 | **No** | HATE 347 vs 354; LOW_LEVEL_HARASSMENT 29 vs 25; SAFE 104 vs 95; AMBIGUOUS_REVIEW 20 vs 26 |
| G18 | **No** | SAFE 498 vs 450; AMBIGUOUS_REVIEW 2 vs 50 |
| G19 | **No** | SEXUAL_CONTENT 389 vs 400; SAFE 107 vs 75; AMBIGUOUS_REVIEW 4 vs 25 |
| G20 | Yes | — |
| G21 | **No** | SEVERE_HARASSMENT 97 vs 100; LOW_LEVEL_HARASSMENT 224 vs 220; HATE 49 vs 50 |
| G22 | **No** | DANGEROUS_REAL_WORLD_INSTRUCTIONS 403 vs 400; SAFE 89 vs 75; AMBIGUOUS_REVIEW 8 vs 25 |
| G23 | Yes | — |
| G24 | Yes | — |
| G25 | **No** | AMBIGUOUS_REVIEW 239 vs 340; SAFE 210 vs 109 |
| G26 | **No** | SAFE 499 vs 475; AMBIGUOUS_REVIEW 1 vs 25 |
| G27 | **No** | SAFE 99 vs 76; AMBIGUOUS_REVIEW 1 vs 24 |

All 18 submitted files parsed, with 500 records each. Six report label tables matched. These results are **pinned to the head above**; rerun on later revisions.

## Required correction before training

1. **Regenerate all 18 reports from the exact final JSONL bytes.** Label distributions are demonstrably stale; other QA sections could be stale too (action distributions, strike, reason codes, near-duplicate groups, warnings, etc.).
2. Confirm every regenerated report's total record count, label/action distributions, schema errors/warnings, exact/near duplicates, and `target_index` validity against the submitted file after any fixes.
3. Run full dataset QA and regression checks on that same head, not old reports from previous generator states. Publish new results.
4. Independently review label correctness on the final bytes. A structurally valid JSONL file with zero QA errors does **not** establish that a safety class has been labeled correctly.
5. Triage the current Codacy comment (53 findings including one critical and 40 high); distinguish valid tooling defects from harmless flagged synthetic text and document dispositions. Do not blindly suppress all alerts.
6. Audit cross-batch near duplicates/contrastive family overlap, and W11/W25 development overlap only. **Do not inspect W20 or W27 for selection/tuning.**

**Current disposition: candidate-only / not training-ready.** No merge, model retraining, GPU rental, privacy-sensitive artifact upload, or enforcement follows from this audit.
