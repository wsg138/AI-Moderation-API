# Owner Policy v1 Golden Acceptance Set

## Purpose

`data/eval/owner-policy-v1.jsonl` is a frozen acceptance/evaluation corpus derived from the owner's W00 interview. It contains **52 direct message/incident fixtures** using only interview wording, plus **35 policy-engine assertions** in the manifest for owner-resolved system behavior that does not naturally belong in a classifier example.

This set is deliberately separate from generated training data. Training on these exact owner fixtures and then evaluating on them would leak the answers and make the acceptance signal meaningless.

## Authority and source hierarchy

1. Latest direct owner answer in interview JSONL.
2. Policy v1 when it faithfully consolidates that answer.
3. `policy/INTERVIEW-DECISION-MAP.md` as a compact cross-check.

Every direct fixture carries `source_interview_ids`, `primary_source_interview_id`, and `policy_sections`. Focused tests verify the speaker/text sequence exactly matches the primary interview record, so no synthetic wording is introduced.

When raw interview messages omit timing, missing `offset_ms` is normalized to `0` and the record carries `timing_known=false`. Array order is authoritative; zero does not claim measured simultaneity.

## Outcome dimensions

Semantic label, message action, review priority, strike, containment, containment duration, support flow, and staff alert remain separate. A field is `null` where the owner did not resolve that dimension. Do not fill nulls from neighboring examples.

Exempt-channel fixtures may intentionally use `label=null` because exempt content is not sent to semantic classification.

## Training leakage

W11/W12 should keep this corpus in evaluation/acceptance by default:

- do not merge it into ordinary training;
- keep synthetic near-variants grouped away from the golden evaluation side of a split;
- check phrase-level and semantic near-duplicates against this corpus before final splits;
- if a golden fixture is intentionally promoted to training, version the golden set and preserve an unseen equivalent family.

The manifest marks the direct set with `training_default: "excluded"`.

## Policy-engine assertions and provenance gaps

System-policy decisions that are not natural classifier examples are stored separately in `owner-policy-v1-manifest.json`. Three merged Policy-v1 assertions have no matching interview JSONL record and are explicitly marked `evidence_tier="policy_only"` / `provenance_gap=true`:

- mirrors count once;
- fail-open and do-not-invent-missing-memory behavior;
- the recent confirmed-threat target-safety-check rule, including Policy v1's working ~24-hour recency.

They remain visible for acceptance coverage without being mislabeled as interview-derived golden truth.

## Later clarification applied

W00-043 established that a quoted/condemning actual slur is blocked but left its strike dimension unresolved at that point in the interview. W00-076 is a later owner answer covering actual slur use in counterspeech/reclaimed contexts and explicitly resolves it as **BLOCK + strike**.

The source hierarchy says the latest direct owner answer controls, so OPV1-0045 now uses `strike=true` and cites both W00-043 and W00-076. This is recorded as a clarification rather than a remaining Policy-v1/raw conflict.

## Clarified earlier answers

- W00-013 contains an `im 16` line, but W00-057/W00-058 later establish that self-report alone is only a clue. Its minor-specific containment fixture therefore requires reliable minor status in context.
- W00-035 is supplemented by W00-069, which explicitly adds strike + urgent staff ping for apparent doxxing and no automatic mute solely from detector output.

## Unresolved edges

The manifest preserves all nine unresolved edges without deciding them: Discord bot DMs; graphic self-harm disclosure; consensual explicit adult PM content; uncertain-age grooming; broader dangerous-instruction domains; fake-doxxing strike cleanup; full threat containment matrix; blackmail containment duration; and accidental lexical slur matching.

## Validation

Run:

```bash
pytest tests/test_owner_policy_golden.py
```

The focused tests cover JSONL parsing, unique IDs, traceability, exact source wording, source existence, unresolved-source rejection, family syntax, complete 84-record coverage, and policy-only provenance-gap marking.

Issue #25 / PR #27 is now merged. The shared QA tool remains intentionally generator-oriented for G01–G09 ID/range/required-field enforcement, so those generator-only checks are not applied to OPV1 evaluation IDs. The golden-set test suite instead cross-checks every non-null golden semantic/policy enum and reason code against the same merged centralized Policy-v1 QA vocabulary while retaining golden-specific nullability and provenance rules.

## Future owner corrections

For a later correction, retain the new authoritative interview record, update affected fixtures/assertions with the new source ID, record the prior answer under superseded/clarified history, version the golden set when expected truth changes materially, and rerun leakage checks before training/export consumes the new version.
