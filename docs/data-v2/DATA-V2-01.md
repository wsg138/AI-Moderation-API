# DATA-V2-01 — public synthetic candidate repair

Issue: #55. Parent: PR #52 / `data/synthetic-g10-g27`.
Source head at dispatch: `53e34e52c6c9a42a8be2ab8f772156e89d31b7e9` (source JSONL; G24 chronology was subsequently corrected).
Run on GitHub Actions, not the owner's PC:

```bash
python -m tools.dataset_qa.freshness --write
python -m tools.dataset_qa.candidate_audit
python -m tools.dataset_qa.freshness
pytest tests/test_dataset_freshness.py
```

The freshness gate runs the **existing** validator, near/exact duplicate analyzer
and Markdown renderer against each final JSONL file, compares the entire report
byte-for-byte, and fails when any result diverges. CI skips G10-G27 on `main`
where they are absent. 18 complete batches are required when any are present.

This is structural QA only. A correct report is **not** independent semantic
acceptance. Candidate labels remain subject to blinded owner-policy adjudication.
Do not train from, merge, or deploy these results without independent approval.

## W11 split isolation

The legacy W11 integration loader now explicitly includes **G01–G09 only**.
New G10–G27 candidate files are not admitted implicitly into the existing
4,500-record W11 audit, partition manifest, or protected evaluation split.
A regression test verifies this source allowlist.

## Chronology repair

19 G24 records had a negative follow-up offset after their offset-zero target.
For these 19 synthetic examples, the follow-up offset was changed from a
negative millisecond value to its positive magnitude; no other field or
message text was changed. Audit SHA-256s reflect the repaired final bytes.

## Validated GitHub Actions checkpoint

Tested source commit: `6afb852c43f53c6a8cc6ddc4e32b857c0355f5b8`.
GitHub-hosted CI (not the owner's PC):
https://github.com/wsg138/AI-Moderation-API/actions/runs/37714450592

- Ruff: passed on DATA-V2-01 code, freshness tests and generator safety test.
- Mypy: passed.
- Complexity CCN <= 8 / functions <= 50 lines: passed.
- G10-G27 report freshness (all 18): passed.
- Pytest: **116 passed in 7.13 s** (including W11 frozen outputs).
- Wheel build: passed.
- Report regeneration/final-byte repeat check:
  https://github.com/wsg138/AI-Moderation-API/actions/runs/37714311210

## Required service CI restored — follow-up branch

The two generator scripts were reformatted to resolve the inherited
Ruff E501/F541/F841 violations without disabling a lint rule. The one
new SIM102 diagnostic was fixed, and new as-of-target validation methods
were separated to satisfy the CCN <= 8 and <= 50-line gates.

Required **service-ci passed** on follow-up commit `30df8731b51a8bff554d6f0fc571afea50111220`:
https://github.com/wsg138/AI-Moderation-API/actions/runs/37716339732 .
Ruff, mypy, complexity, full synthetic dataset QA, report freshness,
W11 reproducibility, tests, and wheel build completed successfully.
Candidate-only checks also passed at the same SHA:
https://github.com/wsg138/AI-Moderation-API/actions/runs/37716334797 .

Subsequent regression updates on the worker branch add all-corpus projection,
runtime-context future-exclusion, exact candidate set, and duplicate-prefix
tests. Verify the latest HEAD run before claiming final acceptance.

## As-of-target input boundary

`tools/dataset_qa/asof_input.py` defines a strict **model-feature projection**
for synthetic candidate records: only allowlisted static `platform_hint` and
`channel_profile`, and `messages[:target_index+1]` with per-message allowlisted
`speaker`, `offset_ms`, and `text` are visible. An earlier message with an
offset later than the target fails closed. Post-target messages are excluded;
retrospective `notes`, labels, action, reason codes, family metadata and any
extra message fields are *not* model input. Regression tests inject future-only
exonerating and contradictory messages/metadata and prove feature invariance.

`tests/test_context.py` independently asserts the live rolling context store
does not include a future-dated event or its linked identity metadata in a
historical snapshot. This is an input-boundary regression, **not** a claim that
a trained model or training collator is already integrated: the current service
classifier is a stub. Any future trainer must explicitly use this projection
(or an equivalent independently tested boundary), with a pre-training
integration gate. Nonterminal targets may remain valid retrospective
fixtures, but never justify reading later text during a real-time prediction.

## Candidate-only missing-corpus guard

The `main`-compatible freshness mode still permits zero G10–G27 batches,
but candidate-only CI now uses `python -m tools.dataset_qa.freshness
--require-complete`, failing if any of the 18 is absent or if batch prefixes
are duplicated. Each submitted batch is independently required to contain
500 valid examples and to match its final-byte report. Tests explicitly
exercise all-missing, incomplete and duplicate scenarios.

PR #52's 53 and PR #56's separate 58 reported findings still require **individual issue-level evidence**
and justified dispositions, especially the one critical and 40 high alerts.
See CODACY-PR52-TRIAGE.md. The dashboard's aggregated comment cannot
establish the validity or false-positive status of each issue.

The audit queues **1,584 nonterminal target indices** (not necessarily
wrong), **354 grooming examples without literal minor-age cues**,
**26 SAFE examples carrying a severe reason code** (often quoted reports),
**10 staff-targeted abuse reason-code/SAFE examples**, and **109 single-speaker
multi-message contexts** for independent adjudication. It found **one
cross-batch exact context group** (G18-0327 / G23-0451, both SAFE) and
**five shared-target-text groups**. The 19 G24 chronological offset
anomalies have been corrected, without relabeling.

**Decision: NOT TRAINING-READY / review-only PR.** Do not merge, train,
deploy or claim verified semantic correctness from structural QA.
