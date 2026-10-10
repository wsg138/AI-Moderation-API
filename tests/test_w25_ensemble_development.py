"""Synthetic-only matched-ensemble tests. Never load sealed or private messages."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from workers.w12.dataset import ModerationExample
from workers.w25.contract import HEAD_VALUES, PredictionBundle
from workers.w25.decision_analytics import capture
from workers.w25.ensemble_development import _write_once, analyze

KEY = b"synthetic-dev-ensemble-test-not-for-production"
SHA_A = "a" * 64
SHA_B = "b" * 64


def _cases() -> list[ModerationExample]:
    return [
        ModerationExample(
            example_id=f"fake-{i}", serialized=f"synthetic {i}",
            label="SAFE", action="BLOCK" if i >= 30 else "ALLOW",
            review_priority="NONE", strike=False, containment="NONE",
            containment_duration_seconds=None, support_flow="NONE",
            channel_profile="minecraft_public", platform_hint="minecraft",
            domain="benign" if i < 30 else "harmful",
            difficulty="hard", reason_codes=(), family_id=f"fake-family-{i}",
        )
        for i in range(40)
    ]


def _bundle(prediction_changes: dict[int, str]) -> PredictionBundle:
    rows = {
        "label": ["SAFE"] * 40,
        "action": ["BLOCK" if i >= 30 else "ALLOW" for i in range(40)],
        "review_priority": ["NONE"] * 40,
        "strike": ["false"] * 40,
        "containment": ["NONE"] * 40,
        "support_flow": ["NONE"] * 40,
    }
    for index, action in prediction_changes.items():
        rows["action"][index] = action
    indices = {
        head: [HEAD_VALUES[head].index(value) for value in values]
        for head, values in rows.items()
    }
    distributions = {
        head: [[float(i == value) for i in range(len(HEAD_VALUES[head]))]
               for value in values]
        for head, values in indices.items()
    }
    return PredictionBundle(indices, distributions, [0.0] * 40)


def _save(tmp_path, name: str, edits: dict[int, str], *, sha: str, suite="development",
          cases=None):
    return capture(
        _cases() if cases is None else cases, _bundle(edits),
        secret=KEY, folder=tmp_path, run_id=name, candidate=name,
        model_sha=sha, config_sha="c" * 64, seed=42,
        policy="v1", suite_name=suite,
    )


def test_ensembles_are_evaluated_as_real_rules_not_perfect_oracle(tmp_path) -> None:
    a = _save(tmp_path, "word", {0: "BLOCK", 30: "ALLOW"}, sha=SHA_A)
    b = _save(tmp_path, "char", {1: "BLOCK", 31: "ALLOW"}, sha=SHA_B)
    report = analyze(a, b)
    results = report["results"]
    assert results["first_model"]["action_correct"] == 38
    assert results["second_model"]["action_correct"] == 38
    assert results["disagreement_to_review"]["action_correct"] == 36
    assert results["disagreement_to_review"]["sent_to_review"] == 4
    assert results["disagreement_to_review"]["wrongful_blocks"] == 0
    assert results["equal_probability_average"]["n"] == 40
    assert report["action_only_not_full_six_head_policy"]
    assert report["not_real_world_accuracy_or_acceptance_evidence"]
    assert "synthetic 0" not in json.dumps(report)


def test_refuses_changed_context_even_when_gold_actions_are_identical(tmp_path) -> None:
    a = _save(tmp_path, "word", {}, sha=SHA_A)
    changed = _cases()
    changed[0] = replace(changed[0], serialized="different synthetic context")
    b = _save(tmp_path, "char", {}, sha=SHA_B, cases=changed)
    with pytest.raises(ValueError, match="input/context changed"):
        analyze(a, b)


def test_refuses_non_development_and_same_model_hash(tmp_path) -> None:
    a = _save(tmp_path, "a", {}, sha=SHA_A)
    frozen = _save(tmp_path, "frozen", {}, sha=SHA_B, suite="time_based_real_chat")
    with pytest.raises(ValueError, match="development-only"):
        analyze(a, frozen)
    dup = _save(tmp_path, "sameweights", {}, sha=SHA_A)
    with pytest.raises(ValueError, match="identical fitted weights"):
        analyze(a, dup)


def test_report_is_private_and_immutable(tmp_path) -> None:
    a = _save(tmp_path, "a", {}, sha=SHA_A)
    b = _save(tmp_path, "b", {}, sha=SHA_B)
    output = tmp_path / "ensemble.json"
    _write_once(output, analyze(a, b))
    assert output.is_file()
    with pytest.raises(ValueError, match="already exists"):
        _write_once(output, analyze(a, b))
