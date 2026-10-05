"""Focused tests for the pre-registered W12 fresh-acceptance gate."""

from __future__ import annotations

from pathlib import Path

from workers.w12.run_fresh_acceptance import (
    COVERAGE_MINIMA,
    MAX_SLICE_GATES,
    MIN_SLICE_GATES,
    evaluate_gates,
)


def _passing_report() -> dict:
    slices = {
        name: {
            "n": minimum,
            "block_false_positive_rate": 0.0,
            "block_recall": 1.0,
        }
        for name, minimum in COVERAGE_MINIMA.items()
    }
    return {
        "runtime_visibility_binary": {
            "block_precision": 0.95,
            "block_recall": 0.95,
        },
        "semantic_label": {
            "macro_f1": 0.90,
            "per_class": [
                {"label": "SAFE", "support": 100, "f1": 0.90},
                {"label": "REAL_WORLD_THREAT", "support": 25, "f1": 0.90},
            ],
        },
        "review_priority": {
            "macro_f1": 0.90,
            "per_class": [
                {"priority": "NONE", "recall": 0.95},
                {"priority": "NORMAL", "recall": 0.90},
                {"priority": "URGENT", "recall": 0.90},
            ],
        },
        "critical_slices": slices,
    }


def test_fresh_acceptance_gate_accepts_passing_report():
    assert evaluate_gates(_passing_report()) == []


def test_fresh_acceptance_gate_rejects_false_positive_regression():
    report = _passing_report()
    report["critical_slices"]["private_flirting"]["block_false_positive_rate"] = (
        MAX_SLICE_GATES["private_flirting"] + 0.01
    )
    failures = evaluate_gates(report)
    assert any(item["gate"] == "fp:private_flirting" for item in failures)


def test_fresh_acceptance_gate_rejects_critical_recall_regression():
    report = _passing_report()
    report["critical_slices"]["real_world_threat"]["block_recall"] = (
        MIN_SLICE_GATES["real_world_threat"] - 0.01
    )
    failures = evaluate_gates(report)
    assert any(item["gate"] == "recall:real_world_threat" for item in failures)


def test_fresh_acceptance_gate_rejects_underpowered_slice():
    report = _passing_report()
    report["critical_slices"]["split_message_threat"]["n"] = (
        COVERAGE_MINIMA["split_message_threat"] - 1
    )
    failures = evaluate_gates(report)
    assert any(item["gate"] == "coverage:split_message_threat" for item in failures)


def test_fresh_acceptance_runner_cannot_open_legacy_partitions():
    source = (
        Path(__file__).resolve().parents[1] / "workers/w12/run_fresh_acceptance.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "load_partition(",
        "load_adversarial_manifest(",
        "load_owner_golden(",
        "heldout-test",
        "heldout-frozen_adversarial",
        "heldout-owner_golden",
    )
    assert not any(token in source for token in forbidden)
