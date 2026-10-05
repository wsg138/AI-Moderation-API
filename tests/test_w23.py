"""W23 tests: leakage barriers, deterministic probes, and selection contracts."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest  # pyright: ignore[reportMissingImports]

pytest.importorskip("sklearn")

from workers.w12.dataset import load_partition
from workers.w23.config import IMPORTANT_BENIGN_SLICES
from workers.w23.evasion import TRANSFORMS, build_probe_set, deterministic_probe_sample
from workers.w23.metrics import binary_metrics, decision_rule_report, gold_screening
from workers.w23.modeling import (
    HEAD_CLASS_COUNTS,
    existing_word_baseline_bundle,
    predict_text_model,
    train_text_model,
)
from workers.w23.selection import select_block_rule, select_hypothetical_auto_rule


def _slice_rates(rate: float) -> dict:
    return {
        name: {
            "n": 10,
            "n_gold_allow": 10,
            "false_positives": round(rate * 10),
            "false_positive_rate": rate,
        }
        for name in IMPORTANT_BENIGN_SLICES
    }


def _decision(name: str, precision: float, recall: float, rate: float = 0.0) -> dict:
    return {
        "name": name,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall),
        "false_positive_rate": rate,
        "tp": 90,
        "fp": 5,
        "fn": 10,
        "tn": 95,
        "important_benign_slices": _slice_rates(rate),
    }


def test_word_candidate_matches_existing_w12_baseline() -> None:
    train = load_partition("train")
    validation = load_partition("validation")
    existing = existing_word_baseline_bundle(train, validation)
    w23 = predict_text_model(train_text_model(train, "word"), validation)
    assert w23.predictions == existing.predictions  # nosec B101 - test assertion


def test_existing_word_probabilities_align_to_full_head_vocabularies() -> None:
    train = load_partition("train")
    validation = load_partition("validation")
    existing = existing_word_baseline_bundle(train, validation)
    for name, class_count in HEAD_CLASS_COUNTS.items():
        assert existing.probabilities[name].shape == (len(validation), class_count)  # nosec B101


def test_train_and_validation_membership_are_disjoint() -> None:
    train = {item.example_id for item in load_partition("train")}
    validation = {item.example_id for item in load_partition("validation")}
    assert train.isdisjoint(validation)  # nosec B101 - test assertion


def test_experiment_runner_only_loads_train_and_validation() -> None:
    source = (Path(__file__).parents[1] / "workers/w23/run_experiments.py").read_text()
    assert 'load_partition("train")' in source  # nosec B101 - test assertion
    assert 'load_partition("validation")' in source  # nosec B101 - test assertion
    assert 'load_partition("test")' not in source  # nosec B101 - test assertion
    assert 'load_partition("frozen_adversarial")' not in source  # nosec B101 - test assertion


def test_bert_oof_training_has_no_validation_loader() -> None:
    source = (Path(__file__).parents[1] / "workers/w23/bert_support.py").read_text()
    assert 'load_partition("train")' in source  # nosec B101 - test assertion
    assert 'load_partition("validation")' not in source  # nosec B101 - test assertion


def test_meta_features_do_not_reference_editorial_metadata() -> None:
    import ast

    root = Path(__file__).parents[1] / "workers/w23"
    forbidden = {"reason_codes", "difficulty", "family_id", "example_id"}
    for filename in ("features.py", "meta.py"):
        tree = ast.parse((root / filename).read_text())
        accessed = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert accessed.isdisjoint(forbidden)  # nosec B101 - test assertion


def test_evasion_sample_is_deterministic_and_train_derived() -> None:
    train = load_partition("train")
    first = deterministic_probe_sample(train, size=20)
    second = deterministic_probe_sample(list(reversed(train)), size=20)
    assert [item.example_id for item in first] == [item.example_id for item in second]  # nosec B101


@pytest.mark.parametrize("transform_name", sorted(TRANSFORMS))
def test_evasion_transform_preserves_serializer_markers(transform_name: str) -> None:
    train = load_partition("train")
    original = deterministic_probe_sample(train, size=1)[0]
    probe = build_probe_set(train, transform_name, size=1)[0]
    assert probe.serialized != original.serialized  # nosec B101 - test assertion
    assert probe.serialized.startswith("[PROFILE=")  # nosec B101 - test assertion
    assert "[TARGET]" in probe.serialized  # nosec B101 - test assertion


def test_binary_metrics_use_actual_paired_predictions() -> None:
    metrics = binary_metrics([1, 1, 0, 0], [1, 0, 1, 0])
    assert metrics["precision"] == 0.5  # nosec B101 - test assertion
    assert metrics["recall"] == 0.5  # nosec B101 - test assertion
    assert metrics["tp"] == 1  # nosec B101 - test assertion
    assert metrics["fp"] == 1  # nosec B101 - test assertion


def test_screening_ground_truth_includes_review_and_block() -> None:
    examples = load_partition("validation")
    gold = gold_screening(examples)
    review = next(index for index, item in enumerate(examples) if item.action == "REVIEW")
    block = next(index for index, item in enumerate(examples) if item.action == "BLOCK")
    allow = next(index for index, item in enumerate(examples) if item.action == "ALLOW")
    assert gold[review] == 1  # nosec B101 - test assertion
    assert gold[block] == 1  # nosec B101 - test assertion
    assert gold[allow] == 0  # nosec B101 - test assertion


def test_hypothetical_auto_rule_reports_recall_sacrifice() -> None:
    baseline = {"recall": 0.90}
    candidates = [
        {"name": "precise", "precision": 0.995, "recall": 0.55, "tp": 10},
        {"name": "less-precise", "precision": 0.98, "recall": 0.80, "tp": 20},
    ]
    selected = select_hypothetical_auto_rule(candidates, baseline)
    assert selected["enabled"] is False  # nosec B101 - test assertion
    assert selected["hypothetical_rule"] == "precise"  # nosec B101 - test assertion
    assert selected["recall_sacrifice_vs_baseline"] == pytest.approx(0.35)  # nosec B101


def test_block_selection_prefers_precision_with_recall_and_slice_guard() -> None:
    baseline = _decision("word", 0.94, 0.92, 0.03)
    precise = _decision("consensus", 0.98, 0.90, 0.03)
    risky = _decision("too-risky", 0.99, 0.91, 0.06)
    selected = select_block_rule([baseline, precise, risky], baseline)
    assert selected["rule"] == "consensus"  # nosec B101 - test assertion
    assert selected["slice_guard_applied"] is True  # nosec B101 - test assertion


def test_decision_report_exposes_important_benign_slice_false_positives() -> None:
    examples = load_partition("validation")
    predicted = [0] * len(examples)
    report = decision_rule_report("allow-all", examples, predicted)
    assert set(report["important_benign_slices"]) == set(IMPORTANT_BENIGN_SLICES)  # nosec B101


def test_w23_modules_keep_functions_within_local_complexity_limits() -> None:
    from tools.check_complexity import analyze

    root = Path(__file__).parents[1] / "workers/w23"
    failures = [failure for path in root.glob("*.py") for failure in analyze(path)]
    assert not failures, failures  # nosec B101 - test assertion


def test_no_w23_module_mutates_production_service() -> None:
    root = Path(__file__).parents[1] / "workers/w23"
    modules = "\n".join(path.read_text() for path in root.glob("*.py"))
    assert "moderation_api.storage" not in modules  # nosec B101 - test assertion
    assert "ModerationStore" not in modules  # nosec B101 - test assertion
    assert "punish" not in inspect.getsource(select_block_rule).lower()  # nosec B101
