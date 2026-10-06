# W21 adversarial/evasion candidate corpus

Status: **candidate-only; not admitted to W11/W12 training, validation, test, frozen-adversarial, owner-golden, or W20 acceptance data.**

## Scope

W21 adds 500 Policy-v1 development candidates grouped into 25 twenty-example families. The corpus emphasizes attempts to preserve meaning while changing surface form, plus allowed hard negatives that superficially resemble evasion.

Transformations include inserted spaces, punctuation/separators, repeated characters, leetspeak, mixed case with separators, zero-width separators, Unicode confusables, typos/symbol interruptions, split messages, and explicit second-attempt rephrasing.

Policy slices include hate/slur use versus reference-only negatives, real-world threats versus Minecraft violence, directed self-harm abuse versus first/third-person support cases, public/private sexual boundaries and reliable-minor cases, doxxing/privacy threats, dangerous real-world requests versus Minecraft/high-level discussion, harassment/staff abuse, and benign contextual reversals.

## Lexical safety note

The new slur-specific W21 seeds use a policy-safe placeholder token rather than adding a new explicit slur lexicon. This still tests spacing, punctuation, Unicode, split-message, family-linkage, and repeated-attempt mechanics. Existing accepted policy data remains the source of settled slur vocabulary; W21 does not copy those examples into this candidate set.

## Isolation

The generator is designed from Policy-v1 and the dataset schema. It does not inspect W20 examples, W12 per-example failures/predictions, or use owner-golden/W11 held-out messages as generation seeds. Accepted G01-G09 plus owner-golden are used only by the post-generation leakage audit.

No candidate is automatically added to a frozen training manifest. Coordinator review/admission is a separate future step.

## Determinism and QA

- Seed catalog: `data/candidates/W21-seeds.json`
- Generator: `tools/w21_generate_candidates.py`
- Candidate JSONL: `data/candidates/W21-adversarial-evasion.jsonl`
- Manifest: `data/candidates/W21-manifest.json`
- Leakage audit: `tools/w21_candidate_audit.py`
- Focused tests: `tests/test_w21_candidates.py`

Canonical QA runs with `G21:1-500`. The audit compares every candidate against accepted G01-G09 records and owner-golden records, reports >=0.92 lexical near candidates, and fails CI on exact collisions or >=0.985 trivial-near collisions.

## QA and leakage result

Exact-head CI validates 500 records with 0 errors, 0 warnings, and 0 exact duplicate groups. The 922 internal near candidates are expected from deliberately related transformation families and do not cross the QA warning/error thresholds.

The dedicated cross-corpus audit compares W21 against 4,552 accepted G01-G09 and owner-golden records. It reports 0 exact collisions, 0 candidates at or above the 0.92 near threshold, and 0 trivial-near collisions at or above 0.985. W20 acceptance data remains unseen and is not part of the audit.

## Intentionally excluded unresolved policy edges

W21 does not invent outcomes for Discord bot DMs, graphic first-person self-harm disclosure, consensual explicit adult PM boundaries, uncertain-age grooming, broader non-explosive dangerous-instruction domains, fake-doxxing strike cleanup, the complete threat-duration matrix, or blackmail containment duration.

W21 also does not inspect W20 acceptance examples, so no claim is made about overlap with that unseen set.
