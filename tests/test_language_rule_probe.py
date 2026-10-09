"""Tests for OFFLINE language rule routing and private detector evaluation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.language_detector_benchmark import evaluate_predictions
from tools.data_v2.language_rule_probe import (
    RULE_PATH,
    evaluate_rule,
    language_only_effects,
    load_rule,
    run_probes,
)


def test_illustrative_rule_probes_do_not_claim_detection_or_gold() -> None:
    outcome = run_probes(
        load_rule(), Path("data/policy-probes/english-primary-v1.jsonl")
    )
    assert outcome["developer_probes_passed"] == 20
    assert outcome["outcomes"] == {
        "ABSTAIN": 4, "ALLOW": 6, "BLOCK": 4,
        "OUT_OF_SCOPE": 2, "SKIP_EXEMPT": 4,
    }
    assert outcome["language_detector_evaluated"] is False
    assert outcome["independent_holdout_evaluated"] is False
    assert outcome["training_eligible"] is False
    assert outcome["runtime_enabled"] is False


@pytest.mark.parametrize("profile", [
    "minecraft_public", "minecraft_private", "discord_general", "discord_gaming",
])
def test_verified_foreign_assessment_maps_to_block_only(profile: str) -> None:
    policy = load_rule()
    assert evaluate_rule(policy, profile, "primarily_non_english") == "BLOCK"
    effects = language_only_effects(policy, "BLOCK")
    assert effects["message_action"] == "BLOCK"
    assert set(effects.values()) == {"BLOCK", "NONE"}


@pytest.mark.parametrize("profile", [
    "discord_staff_exempt", "discord_ticket_exempt", "discord_configured_exempt",
])
def test_exempt_profiles_never_block_language_only(profile: str) -> None:
    policy = load_rule()
    assert evaluate_rule(policy, profile, "primarily_non_english") == "SKIP_EXEMPT"


@pytest.mark.parametrize("profile", [
    "discord_bot_direct_messages", "discord_private", "future_channel", "",
])
def test_unknown_profiles_never_block_language_only(profile: str) -> None:
    assert evaluate_rule(load_rule(), profile, "primarily_non_english") == "OUT_OF_SCOPE"


@pytest.mark.parametrize("assessment", [
    "occasional_foreign_words_or_short_greetings",
    "player_names_and_recognized_game_terms", "primarily_english",
])
def test_allowed_assessments_never_block(assessment: str) -> None:
    assert evaluate_rule(load_rule(), "minecraft_private", assessment) == "ALLOW"


@pytest.mark.parametrize("assessment", [
    "unreliably_assessed_or_ambiguous", None, "", "spanish", "g21_batch",
])
def test_unavailable_or_ambiguous_assessment_abstains(
    assessment: str | None,
) -> None:
    assert evaluate_rule(load_rule(), "discord_general", assessment) == "ABSTAIN"


def _prediction(
    number: int, expected: str = "ALLOW", assessment: str = "primarily_english",
) -> dict[str, Any]:
    return {
        "case_id": f"private-eval-{number:04d}",
        "review_provenance": "independent_human_review",
        "human_reviewed": True, "channel_profile": "minecraft_public",
        "human_expected_action": expected,
        "detector_assessment": assessment,
    }


def _write_private(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    file = tmp_path / "private-synthetic-benchmark.jsonl"
    file.write_text(
        "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8"
    )
    return file


def test_private_evaluation_reports_only_aggregate_error_rates(tmp_path: Path) -> None:
    file = _write_private(tmp_path, [
        _prediction(1), _prediction(2, "ALLOW", "primarily_non_english"),
        _prediction(3, "BLOCK", "primarily_non_english"),
        _prediction(4, "BLOCK", "primarily_english"),
        _prediction(5, "ALLOW", "unavailable"),
    ])
    summary = evaluate_predictions(file, load_rule())
    assert summary["reviewed_private_cases"] == 5
    assert summary["false_blocks"] == 1
    assert summary["false_block_rate_expected_allow"] == 0.333333
    assert summary["false_allows"] == 1
    assert summary["false_allow_rate_expected_block"] == 0.5
    assert summary["abstentions"] == 1
    assert summary["abstention_rate"] == 0.2
    assert summary["runtime_enabled"] is False
    assert summary["automated_release_approval"] is False
    assert "private-eval" not in json.dumps(summary)
    assert "text" not in json.dumps(summary)


@pytest.mark.parametrize("mutator", [
    lambda x: x.update({"human_reviewed": False}),
    lambda x: x.update({"review_provenance": "synthetic_candidate"}),
    lambda x: x.update({"channel_profile": "discord_staff_exempt"}),
    lambda x: x.update({"detector_assessment": "unknown"}),
    lambda x: x.update({"human_expected_action": "REVIEW"}),
    lambda x: x.update({"raw_text": "not allowed"}),
])
def test_private_evaluation_rejects_invalid_rows(
    tmp_path: Path, mutator: Any,
) -> None:
    row = _prediction(1)
    mutator(row)
    with pytest.raises(ValueError):
        evaluate_predictions(_write_private(tmp_path, [row]), load_rule())


def test_private_evaluation_rejects_duplicate_cases(tmp_path: Path) -> None:
    row = _prediction(1)
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_predictions(_write_private(tmp_path, [row, row]), load_rule())


def test_private_evaluation_rejects_checkout_input() -> None:
    with pytest.raises(ValueError):
        evaluate_predictions(RULE_PATH, load_rule())


def test_policy_tamper_to_runtime_or_punishment_rejected(tmp_path: Path) -> None:
    policy = load_rule()
    policy["runtime_enabled"] = True
    bad = tmp_path / "bad-policy.json"
    bad.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(ValueError, match="live runtime"):
        load_rule(bad)
    policy["runtime_enabled"] = False
    policy["language_only_consequences"]["strike"] = "STRIKE"
    bad.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(ValueError, match="penalty"):
        load_rule(bad)


def test_language_gate_modules_respect_complexity_budget() -> None:
    assert analyze(Path("tools/data_v2/language_rule_probe.py")) == []
    assert analyze(Path("tools/data_v2/language_detector_benchmark.py")) == []
