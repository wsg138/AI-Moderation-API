"""Focused tests for the pre-registered W12 fresh-acceptance gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workers.w12.run_fresh_acceptance import (
    ALLOW_COVERAGE_MINIMA,
    BLOCK_COVERAGE_MINIMA,
    MAX_SLICE_GATES,
    MIN_SLICE_GATES,
    evaluate_gates,
    load_acceptance,
    sha256_of,
    validate_acceptance_manifest,
)


def _passing_report() -> dict:
    names = set(ALLOW_COVERAGE_MINIMA) | set(BLOCK_COVERAGE_MINIMA)
    slices = {
        name: {
            "n": 100,
            "n_gold_allow": 100,
            "n_gold_block": 100,
            "block_false_positive_rate": 0.0,
            "block_recall": 1.0,
        }
        for name in names
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
    report["critical_slices"]["split_message_threat"]["n_gold_block"] = (
        BLOCK_COVERAGE_MINIMA["split_message_threat"] - 1
    )
    failures = evaluate_gates(report)
    assert any(item["gate"] == "coverage_block:split_message_threat" for item in failures)


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


def test_acceptance_manifest_requires_independence_flags(tmp_path):
    acceptance = tmp_path / "acceptance.jsonl"
    acceptance.write_text(
        json.dumps(
            {
                "example_id": "W20-0001",
                "policy_version": "v1",
                "source": "synthetic",
                "domain": "benign_hard_negative",
                "difficulty": "hard",
                "platform_hint": "minecraft",
                "channel_profile": "minecraft_public",
                "messages": [
                    {"speaker": "A", "offset_ms": 0, "text": "gg that was close"}
                ],
                "target_index": 0,
                "label": "SAFE",
                "action": "ALLOW",
                "review_priority": "NONE",
                "strike": False,
                "containment": "NONE",
                "containment_duration_seconds": None,
                "support_flow": "NONE",
                "reason_codes": ["minecraft_gameplay_explicit"],
                "notes": "fixture",
                "family_id": "w20.fixture.1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    examples = load_acceptance(acceptance)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract": "w12-v2-fresh-acceptance-v1",
                "acceptance_only": True,
                "forbidden_for_training": True,
                "built_without_w12_predictions": False,
                "dataset_sha256": sha256_of(acceptance),
                "record_count": 1,
                "family_count": 1,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="built_without_w12_predictions"):
        validate_acceptance_manifest(manifest, acceptance, examples)
