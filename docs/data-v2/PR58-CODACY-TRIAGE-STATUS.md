# Codacy and review-intake security checkpoint — PR #58

**Scope:** public-synthetic reviewer tooling in draft stacked [PR #58](https://github.com/wsg138/AI-Moderation-API/pull/58), not accepted training data or production services. Source labels remain frozen and non-admitted.

## Exact findings available

At prior PR #58 head `00da5cef367dfc93319c5d80bc1accde970e28df`, the completed GitHub Codacy check `113169047139` reported **507 newly added issues**, with **zero permitted** by its quality threshold. Its accessible check summary lists complexity increases across 25 touched tools/test files and six added clone groups, but does **not** expose individual issue ID, scanner rule, line, evidence, severity, or false-positive classification. This number is check-specific and fluctuated across earlier heads; it is **not 507 established bugs**.

An older PR #58 Codacy bot conversation summary (not the current SHA) displayed the *first 100* findings as 80 high Security, 17 high ErrorProne, and 3 medium BestPractice. **Do not extrapolate these proportions to 507 current reports.** The top-level Codacy PR report and PR comment do not establish full rule-by-rule signoff.

At parent PR #56 head `cec977a69de0c891a1041d7af529cb0721eeb5bd`, a separate check reported **112 newly added issues**; at PR #52 head `53e34e52c6c9a42a8be2ab8f772156e89d31b7e9`, **53**. These are distinct branch comparisons, not deduplicated totals and not inherently attributable to PR #58's added code.

**Access limitation:** the available GitHub check response exposes aggregate summaries only. Its per-line check-run annotations endpoint is not accessible through the current GitHub connector, and Codacy's issue-details page cannot be fetched through the available browser. No findings were globally suppressed, dismissed, or marked resolved without evidence.

## One confirmed independent code defect and its patch

Source examination identified an **actual validation gap in `tools/dataset_qa/review_decisions.py`**: `_validate_facts` and `_validate_evidence` formerly checked element constraints with `all(...)` but did **not** reject an empty list. Two assigned aliases could therefore submit empty factual/evidence lists, allowing `review_summary` to report `independent_agreement` **without any cited context**. Even then, the status correctly remained `training_eligible=false` — this did **not** permit training or cause a production punishment.

The draft patch now requires:
- **1–32 nonblank observed facts** of at most 200 characters each;
- **at least one valid, target-time-visible evidence index** and no duplicate evidence indices;
- matching limits in the existing offline HTML reviewer form;
- regression tests at direct validator, review-summary, offline-form and assigned-intake boundaries.

These are evidence-quality controls only, not source-policy or model-label changes. A passing unit test is not independent reviewer identity authentication.

## Remaining audit steps before closing Codacy

1. Obtain the actual **latest-SHA Codacy issue list** with issue ID, analyzer/rule, severity, file, line and message. The user or an authorized reviewer can inspect [PR #58 issues](https://app.codacy.com/gh/wsg138/AI-Moderation-API/pull-requests/58/issues), and similarly [PR #56](https://app.codacy.com/gh/wsg138/AI-Moderation-API/pull-requests/56/issues) and [PR #52](https://app.codacy.com/gh/wsg138/AI-Moderation-API/pull-requests/52/issues). Do not submit keys or access tokens to ChatGPT.
2. Classify findings *per rule and affected source location*: security exploit or information leakage, correctness defect, nonbreaking maintainability issue, test fixture/string classifier false positive, confirmed duplicate or inherited unchanged issue. Record specific evidence, and address valid high/critical defects first.
3. For tool-pattern or synthetic-text false positives, justify the exact rule and scope; do **not** globally disable security scans, suppress all failures or treat the fluctuating zero-issues heads as permanent clearance.
4. Re-run both required CI and fresh exact-head Codacy, and document remaining findings plus explicit signoff separately on parent PRs.

**Release blocks unchanged:** no PR merge, no G10 label rewrite, no independent certification without real reviewers, no admission for training, no private Minecraft data, no W20/W27, no model training or production actions.

## Verified follow-up — 2026-10-08 exact head

At **`12bcf8dfe6f4c856d9e3dc720a4b59c0a28b34a3`**, the [required GitHub workflow](https://github.com/wsg138/AI-Moderation-API/actions/runs/37734489967) completed successfully with **235 passed tests**. The same SHA-specific Codacy check remains `action_required` with **516 newly reported findings, 0 allowed**. This replaces the older 507-head count for current status, **not** a deduplicated catalog of defects. The actual rule/path/line-level issue list is still unavailable through permitted current connector access.

The added evidence-required validation is verified by CI. No blanket scanner suppression, gold-label acceptance, source edit, merge, training, or deployment has occurred.
