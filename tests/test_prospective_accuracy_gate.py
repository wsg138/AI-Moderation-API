"""Invented aggregate demonstrations only; no real data or accuracy claims."""
from __future__ import annotations

from dataclasses import replace

from tools.data_v2.policy_eval_metrics import Decision, Example, evaluate
from tools.data_v2.prospective_accuracy_gate import (
    REQUIRED_ASSERTIONS,
    SCHEMA,
    assess,
)

SAFE = Decision("SAFE", "ALLOW", "NONE", False, "NONE", None, "NONE")
LABELS = (
    "REAL_WORLD_THREAT", "SELF_HARM_INSTRUCTION", "SLUR_USE",
    "SEXUAL_MINOR", "DOXXING", "GROOMING",
)


def _attack(label: str) -> Decision:
    return Decision(label, "BLOCK", "URGENT", False, "NONE", None, "NONE")


def _natural() -> list[Example]:
    items = [Example(f"n{i}", "traffic", SAFE, SAFE) for i in range(4000)]
    items += [
        Example(f"nb{i}", "traffic", _attack("REAL_WORLD_THREAT"),
                _attack("REAL_WORLD_THREAT"))
        for i in range(100)
    ]
    return items


def _challenge() -> list[Example]:
    return [
        Example(f"c{label}_{i}", "rare_safety", _attack(label), _attack(label))
        for label in LABELS for i in range(100)
    ]


def _metadata(natural_n: int = 4100, challenge_n: int = 600) -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema_version": SCHEMA,
        "model_sha256": "a" * 64,
        "natural_cohort_sha256": "b" * 64,
        "challenge_cohort_sha256": "c" * 64,
        "natural_cases": natural_n,
        "challenge_cases": challenge_n,
        "independent_audit_reference": "PRIVATE-audit-record-placeholder",
    }
    manifest.update({key: True for key in REQUIRED_ASSERTIONS})
    return manifest


def test_perfect_two_cohort_toy_metrics_do_not_authorize_deployment() -> None:
    result = assess(evaluate(_natural()), evaluate(_challenge()), _metadata())
    assert result["result"] == "PROVISIONAL_EVIDENCE_THRESHOLDS_MET"
    assert result["blockers"] == []
    assert result["not_a_deployment_authorization"] is True
    assert result["never_authorizes_automatic_punishments"] is True
    assert result["attestation_is_self_declared_and_requires_independent_verification"]


def test_natural_all_allow_baseline_cannot_pass_on_traffic_prevalence() -> None:
    rows = [
        replace(item, predicted=SAFE)
        for item in _natural()
    ]
    result = assess(evaluate(rows), evaluate(_challenge()), _metadata())
    assert result["result"] == "NOT_ESTABLISHED"
    assert "full_decision_exact_match_lower95_below_99pct" in result["blockers"]


def test_perfect_small_samples_still_fail_confidence_and_benign_support() -> None:
    result = assess(
        evaluate(_natural()[:350]), evaluate(_challenge()[:60]),
        _metadata(natural_n=350, challenge_n=60),
    )
    assert "benign_support_under_3500" in result["blockers"]
    assert "block_precision_support_under_100" in result["blockers"]
    assert "critical_GROOMING_support_under_80" in result["blockers"]


def test_challenge_missed_threats_rejects_recall_and_rare_class() -> None:
    rows = [
        replace(item, predicted=SAFE) if item.truth.semantic_label == "GROOMING"
        else item for item in _challenge()
    ]
    result = assess(evaluate(_natural()), evaluate(rows), _metadata())
    assert "critical_GROOMING_block_recall_lower95_below_95pct" in result["blockers"]
    assert "block_recall_lower95_below_95pct" in result["blockers"]


def test_false_strike_blocks_even_when_message_action_is_correct() -> None:
    rows = _natural()
    rows[0] = replace(rows[0], predicted=replace(SAFE, strike=True))
    result = assess(evaluate(rows), evaluate(_challenge()), _metadata())
    assert "natural_false_strikes" in result["blockers"]


def test_self_reported_metadata_is_required_but_never_sufficient() -> None:
    metadata = _metadata()
    metadata["independently_double_adjudicated"] = "true"
    metadata["model_sha256"] = "model_latest"
    metadata["challenge_cases"] = 123
    metadata["challenge_cohort_sha256"] = "b" * 64
    result = assess(evaluate(_natural()), evaluate(_challenge()), metadata)
    assert result["result"] == "NOT_ESTABLISHED"
    assert "unverified_independently_double_adjudicated" in result["blockers"]
    assert "invalid_digest_model_sha256" in result["blockers"]
    assert "challenge_cohort_size_mismatch" in result["blockers"]
    assert "cohort_digests_not_distinct" in result["blockers"]


def test_rare_safety_corpus_is_not_substituted_for_natural_traffic() -> None:
    result = assess(
        evaluate(_challenge()), evaluate(_challenge()),
        _metadata(natural_n=600, challenge_n=600),
    )
    assert result["result"] == "NOT_ESTABLISHED"
    assert "benign_support_under_3500" in result["blockers"]
    assert "false_blocks_upper95_over_one_per_1000_benign" in result["blockers"]
