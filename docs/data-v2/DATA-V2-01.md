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

Existing `service-ci` is still red at Ruff due pre-existing generator
lint debt introduced on PR #52 (162 initially at run 37703372884,
mostly E501). Do not mask the required CI check; resolve separately.

Codacy's 53 reported findings still require **individual issue-level evidence**
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
