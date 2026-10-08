# DATA-V2-01 — PR #52 Codacy triage checkpoint

Source: PR #52 Codacy comment 6049061884 at exact head 53e34e5.
Codacy dashboard: https://app.codacy.com/gh/wsg138/AI-Moderation-API/pull-requests/52/issues

The GitHub-visible comment exposes aggregate categories but **not** 53 per-alert
rule IDs, file paths, line positions, or evidence. PR inline review threads
contain no detail. Do not pretend those individual findings were inspected or
mark the critical/high issues resolved without an authenticated export.

| Source category | Reported | Evidence/disposition |
|---|---:|---|
| UnusedCode, medium | 1 | Found unused import sys in gen_g14.py by Ruff; removed. Confirm Codacy ID on export. |
| ErrorProne, high | 16 | Generator gen_g15.py had absolute /home/hatch/... output and unguarded main() write on import; fixed. Other 14+ specific alerts require rule/path evidence. |
| Security, high | 24 | **Untriaged individually.** Candidate synthetic text false positives are possible, but not substantiated from summary alone. Need line-level review, especially critical. |
| Security, critical | 1 | **Blocking: evidence unavailable.** No blanket suppression; request issue-level inspection before acceptance. |
| Security, medium | 3 | Untriaged individually pending export. |
| Complexity, medium | 8 | Potentially generator-wide complexity; no blanket exemption. Require paths and per-method review. |

Separate GitHub Actions baseline finding: PR #52 run 37703372884 failed
Ruff with **162 findings** across tools/gen_g14.py and tools/gen_g15.py,
mostly E501 long lines, plus F401 and F541. The service CI was red before
this worker branch; Ruff stopped mypy, pytest, dataset QA and wheel steps.
Fixed the reproducibility/import defects and unused import; formatting
debt remains **unresolved**, not dismissed as false positive.

Next mandatory Codacy review: export each of the 53 finding IDs with its
severity, rule, path, line, source snippet and applicability. Map each to:
valid tooling defect (fix+test), style/complexity (refactor), or demonstrably
synthetic-text misclassification (individual reason and evidence). Do not
disable checks, batch-ignore files, or merge candidate data until the
valid critical/high findings and CI have an accountable resolution.

## Follow-up: PR #56 Codacy analysis and evidence limitation

The PR #56 check on worker head `458df211908cfac779238a1ba5075659266836a5`
is check-run `113108114745`. Its GitHub-visible output is **58 new HIGH**
findings: **18 ErrorProne, 40 Security**, with two classified as solved.
The check output also says `annotations_count: 50` but does not list
rule/path/line/snippet. The GitHub connector can read the check-run summary
via the commit check-runs collection, but its approved fetch interface rejects
`/check-runs/113108114745/annotations`; the same limitation applies to the
PR #52 check-run `113072489541` (also `annotations_count: 50`).
Those counts are not evidence for specific findings and are not the same
as the complete per-finding details (53 / 58).

The GitHub PR discussion and inline review threads similarly contain no
individual Codacy rule IDs, paths, line numbers or snippets. **No individual
critical/high alert is being declared false-positive or fixed on that basis.**
The automated generator Ruff repair resolves GitHub-confirmed style defects,
but it is not proof of resolving any specific Codacy issue.

**Evidence request / blocking follow-up:** obtain authenticated per-finding
Codacy exports (PR #52 and current PR #56), with stable finding IDs, severity,
tool/rule, path, start/end lines, redacted finding evidence, and live status.
Verify every valid tooling/security finding, fix and test it; document each
synthetic-text false positive separately with a concrete rule/path rationale.
Reconcile changes in counts between commits rather than combining rollups
as if they were a single deduplicated list. No global exclusions, severity
downgrades, acceptance, merge or model training on aggregate-only reports.
