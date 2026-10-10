"""Synthetic-only checks of six-head blend diagnostics and policy conflicts."""
from __future__ import annotations

from pathlib import Path

import pytest

from workers.w25.contract import HEAD_VALUES
from workers.w25.full_head_blend import (
    _block_rates,
    _critical,
    _guard_allow_punitive_heads,
    _mean_choice,
    _six_head_stats,
    analyze_full,
)


def _row(label: str = "SAFE", action: str = "ALLOW"):
    gold = {
        "label": label, "action": action, "review_priority": "NONE",
        "strike": False, "containment": "NONE", "support_flow": "NONE",
    }
    classes = {
        head: list(values) for head, values in HEAD_VALUES.items()
    }
    return {
        "gold": gold, "predicted": gold,
        "probabilities": {
            head: [float(value == ("false" if head == "strike" else gold[head]))
                   for value in values]
            for head, values in classes.items()
        },
    }


def test_synthetic_full_heads_agree_and_critical_recall_is_label_scoped() -> None:
    rows = [_row()] * 21 + [_row("REAL_WORLD_THREAT", "BLOCK")] * 5
    decisions = [item["gold"] for item in rows]
    full = _six_head_stats(rows, decisions)
    assert full["six_head_exact"] == 26
    assert full["false_strike_recommendations"] == 0
    assert _block_rates(rows, decisions)["block_precision"] == 1.0
    critical = _critical(rows, decisions)["REAL_WORLD_THREAT"]
    assert critical["gold_block_support"] == 5
    assert critical["insufficient_support_under_80"]


def test_allow_and_strike_or_mute_contradiction_is_reported() -> None:
    row = _row()
    decision = dict(row["gold"], strike=True, containment="MUTE")
    result = _six_head_stats([row], [decision])
    assert result["false_strike_recommendations"] == 1
    assert result["false_mute_recommendations"] == 1
    assert result["allow_with_punitive_head"] == 1
    assert result["six_head_exact"] == 0


def test_allow_guard_clears_only_current_message_punitive_heads() -> None:
    row = _row()
    raw = dict(row["gold"], strike=True, containment="MUTE")
    guarded = _guard_allow_punitive_heads(raw)
    assert guarded["strike"] is False
    assert guarded["containment"] == "NONE"
    assert guarded["action"] == "ALLOW"
    assert raw["strike"] is True
    assert _six_head_stats([row], [guarded])["allow_with_punitive_head"] == 0


def test_probability_average_validates_finite_scores_and_head_type() -> None:
    left = _row()
    right = _row()
    assert _mean_choice(left, right, "strike", list(HEAD_VALUES["strike"])) is False
    left["probabilities"]["action"][0] = float("nan")
    with pytest.raises(ValueError, match="Nonfinite"):
        _mean_choice(left, right, "action", list(HEAD_VALUES["action"]))


def test_full_report_does_not_infer_rare_class_accuracy(monkeypatch) -> None:
    rows = {"a": _row()}
    header = {"run_id": "a", "probability_head_value_order": {
        head: list(classes) for head, classes in HEAD_VALUES.items()
    }}
    monkeypatch.setattr(
        "workers.w25.full_head_blend._load_pair",
        lambda a, b: (header, rows, rows),
    )
    result = analyze_full(Path("not-read-a"), Path("not-read-b"))
    assert result["full_heads"]["six_head_exact"] == 1
    assert result["critical_action_recall"]["GROOMING"]["lower95_recall"] is None
    assert result["not_a_deployment_or_99pct_acceptance_result"]
