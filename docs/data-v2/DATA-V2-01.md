# DATA-V2-01 — public synthetic candidate repair

Issue: #55. Parent: PR #52 / `data/synthetic-g10-g27`.
Source head at dispatch: `53e34e52c6c9a42a8be2ab8f772156e89d31b7e9` (unmodified JSONL expected).
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
