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
