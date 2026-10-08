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
