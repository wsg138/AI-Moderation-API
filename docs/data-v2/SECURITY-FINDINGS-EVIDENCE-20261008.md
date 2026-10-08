# DATA-V2-W2 security evidence — 2026-10-08

Scope: issue [#61](https://github.com/wsg138/AI-Moderation-API/issues/61), public-synthetic **offline** reviewer tooling. Source labels are untouched, and reviewer results remain **candidate-only** (`training_eligible=false`). These findings are from independent code inspection; they **cannot be mapped to specific Codacy IDs** without the scanner's issue-level evidence.

## Exact upstream checks (distinct comparisons)

| PR / exact head | GitHub required CI | Codacy check and latest accessible evidence |
| --- | --- | --- |
| [#52](https://github.com/wsg138/AI-Moderation-API/pull/52) / `53e34e52c6c9a42a8be2ab8f772156e89d31b7e9` | `verify` failed, [run 37703372884](https://github.com/wsg138/AI-Moderation-API/actions/runs/37703372884) | check `113072489541` = `action_required`, **53 added** (1 critical/40 high/12 medium in GitHub bot comment) |
| [#56](https://github.com/wsg138/AI-Moderation-API/pull/56) / `cec977a69de0c891a1041d7af529cb0721eeb5bd` | `verify` succeeded, [run 37716704283](https://github.com/wsg138/AI-Moderation-API/actions/runs/37716704283); candidate QA succeeded, [run 37716699432](https://github.com/wsg138/AI-Moderation-API/actions/runs/37716699432) | check `113114816945` = `action_required`, **112 added, 6 solved** |
| [#58](https://github.com/wsg138/AI-Moderation-API/pull/58) / `a77fdaf15a90123225311ebc4c8823191655bc69` | `verify` succeeded, [run 37791338234](https://github.com/wsg138/AI-Moderation-API/actions/runs/37791338234), **250 tests** per issue #53 | check `113359776906` = `action_required`, **534 added** |

Counts are **not a deduplicated list** and cannot be added to estimate a total number of genuine defects. The GitHub check summaries give per-file complexity increments, aggregate issue counts and 50 annotation counts, **not** finding identifiers, rules, severity, file lines, or evidence. Direct GitHub check-annotation requests were rejected by the available connector (HTTP 400 endpoint not allowed), and the Codacy issue page did not expose its content through the accessible browser. No suppression, false-positive dismissal or exact Codacy issue disposition is claimed.

## Confirmed independent defects and fixes

These are source-based findings with reproducible negative tests on the W2 branch, **not** claimed mappings to the 53/112/534 scanner alerts.

| Local ID / source | Evidence and impact | Fix and regression |
| --- | --- | --- |
| W2-SEC-01 / `tools/dataset_qa/blind_review.py` former `main()` lines 108–115; `review_sampling.py` former `main()` lines 130–137 | Packet file and coordinator crosswalk could be written in the **same directory**, or crosswalk nested below the reviewer directory. Passing such a directory to reviewers could expose original source IDs/file hashes and break blinding. Previously only exact-path equality was blocked. | Shared `_write_review_outputs` rejects ancestor/equal reviewer/coordinator directory overlap before creating any output; used by both CLIs. `tests/test_review_security_boundaries.py` covers same-directory and nested paths. |
| W2-INT-02 / `tools/dataset_qa/review_intake.py` former `_read_jsonl()` lines 20–24 | `json.loads` silently resolves duplicate object keys by keeping the last key. Contradictory packet/decision/manifest JSON could therefore be interpreted differently by other reviewers or implementations. | Object-pairs hook rejects duplicate keys including nested objects, regression covers both. |
| W2-INT-03 / `tools/dataset_qa/review_assignments.py` former `_check_messages()` lines 31–42 | Timestamp validation only bounded context by target time; preceding messages with offsets such as `4,2,5` were accepted despite nonchronological ordering. This undermines the intended chronological evidence presentation. | Reject decreasing offsets; regression verifies rejection of otherwise valid-looking packet. |
| W2-FS-04 / `tools/dataset_qa/blind_review.py` former `_write_jsonl()` lines 94–99; `main()` lines 114–115 | A serialization/disk-write failure could leave a truncated output file; a second-file failure could leave a reviewer packet artifact without its crosswalk. | Remove a newly created partial file on failure; paired helper removes the newly created reviewer file if the coordinator output fails. Regression covers partial serialization and non-overwrite/rollback with an existing coordinator path. |

## Remaining risks, classification and gates

- **Codacy details: needs evidence.** Inspect latest-SHA findings via the authorized [#52](https://app.codacy.com/gh/wsg138/AI-Moderation-API/pull-requests/52/issues), [#56](https://app.codacy.com/gh/wsg138/AI-Moderation-API/pull-requests/56/issues), and [#58](https://app.codacy.com/gh/wsg138/AI-Moderation-API/pull-requests/58/issues) dashboards, recording per item: issue ID, analyzer/rule, severity, path/line/snippet, inherited/new status, fix/individual false-positive evidence. **The PR #52 critical scanner alert remains blocked and not declared false positive.** Do not infer individual scanner outcomes from W2 fixes.
- **OS path races: needs hardening or acceptable-trust determination.** `_outside_checkout` canonicalizes paths and exclusive-open blocks existing final names, but an untrusted local actor with write access to ancestor directories could race changes to symlinks between validation and creation. These offline tools should run with trusted private output parents until descriptor-relative directory traversal is added/tested. W2's directory separation is a static placement check, not an atomic filesystem sandbox.
- **Manifest tampering: not cryptographically authenticated.** A SHA-256 of serialized packet data detects accidental drift against a trusted manifest, but an attacker controlling **both** packet and manifest can recalculate it. No claim of verified reviewer identity: aliases are assertions. Store manifests/crosswalks in owner-controlled locations and verify independent humans outside the tool. Separate keyed signatures/manifest provenance are future work.
- **Other multi-file producers:** G10 cohort and reviewer assignment CLIs retain a possible partial *multi-file* artifact set on a later output failure. Common `_write_jsonl` now cleans its own partial file but not earlier successful artifacts in those callers. Keep incomplete runs quarantined; add transactional rollback in a separately scoped change.
- **Review semantics:** `EVIDENCE_INSUFFICIENT`, owner-policy questions, and reviewer disagreement remain pending. The code does not establish independent human review, policy truth, split isolation, or admission. No private player data, W20/W27, training, paid inference, merges or production modifications were used.

## Validation

W2 source changes: `6ed2bea688bf25584262fca3f285a0c9091e347f`, with a follow-up complexity refactor at `a525cb7407019ad7b3a6e5e1f7458e272c3fff89`. Six new regression test functions cover eight parameterized negative cases in `tests/test_review_security_boundaries.py`.

- **Initial CI failed** at `028a9ddef2cf33055d4bfcf3b37fa360428e4545` ([run 37800388912](https://github.com/wsg138/AI-Moderation-API/actions/runs/37800388912)) on `_check_messages` **CCN 10 > 8**, after Ruff/mypy success. Refactored chronology validation into a separate helper, without weakening rejection.
- **Corrected code head passed** GitHub-hosted `service-ci` at `a525cb7407019ad7b3a6e5e1f7458e272c3fff89` ([run 37800592856](https://github.com/wsg138/AI-Moderation-API/actions/runs/37800592856)): Ruff, mypy, CCN, candidate dataset QA, 18 report freshness checks, W11 integration reproducibility, **258 tests passed**, and wheel build.
- No passing local build claim: the isolated tool container cannot clone GitHub due to network/DNS restrictions. These are GitHub-hosted results. Recheck the final documentation-only PR head and Codacy independently; a successful required workflow does **not** establish security scanner clearance.
