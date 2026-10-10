"""Synthetic-only BLOCK threshold experiments; no sealed acceptance access."""
from __future__ import annotations

from pathlib import Path

import pytest

from workers.w25.contract import HEAD_VALUES
from workers.w25.threshold_sweep import _block_precision, _rule_action, sweep


def _vector(block: float) -> list[float]:
    labels = list(HEAD_VALUES["action"])
    result = {key: 0.0 for key in labels}
    result["BLOCK"] = block
    result["ALLOW"] = 1.0 - block
    return [result[key] for key in labels]


def _row(gold: str, block_probability: float) -> dict:
    return {
        "gold": {"action": gold},
        "probabilities": {"action": _vector(block_probability)},
    }


def test_false_block_precision_counts_review_gold_as_false_positive() -> None:
    report = _block_precision(
        ["BLOCK", "ALLOW", "REVIEW"],
        ["BLOCK", "BLOCK", "ALLOW"],
    )
    assert report["tp"] == 1
    assert report["fp"] == 1
    assert report["precision"] == 0.5


def test_higher_threshold_routes_low_score_blocks_to_review() -> None:
    classes = list(HEAD_VALUES["action"])
    a, b = _row("ALLOW", 0.60), _row("ALLOW", 0.60)
    idx = classes.index("BLOCK")
    assert _rule_action(a, b, classes, idx, 0.50) == "BLOCK"
    assert _rule_action(a, b, classes, idx, 0.65) == "REVIEW"


def test_sweep_reports_tradeoffs_not_authorized_promotion(monkeypatch) -> None:
    rows = {
        "a": _row("BLOCK", 0.90),
        "b": _row("BLOCK", 0.55),
        "c": _row("ALLOW", 0.60),
    }
    right = {
        "a": _row("BLOCK", 0.90),
        "b": _row("BLOCK", 0.55),
        "c": _row("ALLOW", 0.60),
    }
    monkeypatch.setattr(
        "workers.w25.threshold_sweep._load_pair",
        lambda *_: ({"run_id": "devA", "probability_head_value_order": {
            "action": list(HEAD_VALUES["action"]),
        }}, rows, right),
    )
    result = sweep(Path("fakeA"), Path("fakeB"))
    points = result["thresholds"]
    assert len(points) >= 8
    assert points[0]["block"]["fp"] >= points[-1]["block"]["fp"]
    assert points[0]["block"]["tp"] >= points[-1]["block"]["tp"]
    assert result["selection_on_this_dev_set_would_require_new_unseen_validation"]
    assert result["not_a_production_approval"]


def test_no_positive_predictions_yield_unknown_not_perfect_precision() -> None:
    report = _block_precision(["ALLOW", "BLOCK"], ["ALLOW", "REVIEW"])
    assert report["precision"] is None
    assert report["recall"] == 0


def test_invalid_policy_dimensions_do_not_masquerade_as_three_actions() -> None:
    # The actual pair loader already validates the frozen source and class order.
    with pytest.raises(ValueError):
        _rule_action(_row("ALLOW", 0.6), _row("ALLOW", 0.6), ["ALLOW"], 1, 0.5)
