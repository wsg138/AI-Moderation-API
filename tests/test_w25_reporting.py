from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from workers.w12.dataset import ModerationExample
from workers.w25.adversarial_benchmark import adversarial_bundle_report
from workers.w25.adversarial_metrics import paired_attack_report
from workers.w25.artifacts import save_bundle
from workers.w25.attacks import ATTACK_FAMILIES
from workers.w25.benchmark import (
    artifact_size_bytes,
    benchmark_callable,
    benchmark_queue_pressure,
)
from workers.w25.comparison import rank_candidates
from workers.w25.contract import HEAD_NAMES, HEAD_VALUES, PredictionBundle
from workers.w25.evaluation import suite_fingerprint
from workers.w25.evidence import aggregate_evidence_manifest
from workers.w25.export_onnx import artifact_metadata, parity_report
from workers.w25.failures import grouped_visibility_failures
from workers.w25.lexical_artifact import export_lexical_artifact
from workers.w25.performance_evidence import benchmark_candidate
from workers.w25.stability import stability_report


def _example(example_id: str, action: str, domain: str = "gameplay") -> ModerationExample:
    return ModerationExample(
        example_id=example_id,
        serialized="[0ms] A: test",
        label="SAFE" if action == "ALLOW" else "LOW_LEVEL_HARASSMENT",
        action=action,
        review_priority="NONE",
        strike=False,
        containment="NONE",
        containment_duration_seconds=None,
        support_flow="NONE",
        channel_profile="minecraft_public",
        platform_hint="minecraft",
        domain=domain,
        difficulty="normal",
        reason_codes=(),
        family_id="family",
    )


def _bundle(action_predictions: list[int]) -> PredictionBundle:
    probabilities = {}
    for head in HEAD_NAMES:
        width = len(HEAD_VALUES[head])
        probabilities[head] = [[1.0] + [0.0] * (width - 1) for _ in action_predictions]
    action_rows = []
    for prediction in action_predictions:
        row = [0.05, 0.05, 0.05]
        row[prediction] = 0.90
        action_rows.append(row)
    probabilities["action"] = action_rows
    predictions = {
        head: [max(range(len(row)), key=row.__getitem__) for row in rows]
        for head, rows in probabilities.items()
    }
    uncertainty = [0.10 for _ in action_predictions]
    return PredictionBundle(predictions, probabilities, uncertainty)


def test_failure_report_groups_ids_without_raw_text_by_default() -> None:
    examples = [_example("A", "ALLOW"), _example("B", "BLOCK", "harassment")]
    bundle = _bundle([1, 0])
    report = grouped_visibility_failures(examples, bundle)
    assert report["total"] == 2
    assert all("serialized" not in item for item in report["examples"])


def test_paired_attack_report_counts_evasion_and_benign_corruption() -> None:
    report = paired_attack_report(
        gold_block=[1, 1, 0, 0],
        clean_block=[1, 1, 0, 0],
        adversarial_block=[0, 1, 1, 0],
    )
    assert report["attack_success_rate"] == pytest.approx(0.5)
    assert report["benign_corruption_false_positive_rate"] == pytest.approx(0.5)


def test_stability_report_exposes_flip_and_metric_ranges() -> None:
    report = stability_report(
        predictions_by_seed={42: [0, 1], 138: [1, 1], 2026: [0, 1]},
        metrics_by_seed={
            42: {"precision": 0.99},
            138: {"precision": 0.98},
            2026: {"precision": 1.0},
        },
        temperatures_by_seed={
            42: {"action": 1.0},
            138: {"action": 1.1},
            2026: {"action": 0.9},
        },
    )
    assert report["prediction_flip_rate"] == pytest.approx(0.5)
    assert report["metrics"]["precision"]["range"] == pytest.approx(0.02)


def test_suite_fingerprint_changes_when_gold_policy_changes() -> None:
    allow = [_example("A", "ALLOW")]
    block = [_example("A", "BLOCK")]
    assert suite_fingerprint(allow) != suite_fingerprint(block)


def test_final_ranking_rejects_mismatched_suite_fingerprints() -> None:
    left = _candidate("left", fingerprint="same")
    right = _candidate("right", fingerprint="different")
    with pytest.raises(ValueError, match="suite mismatch"):
        rank_candidates([left, right])


def test_final_ranking_prioritizes_real_false_positive_behavior() -> None:
    precise = _candidate("precise", fingerprint="same", fpr=0.0001, precision=0.995)
    noisy = _candidate("noisy", fingerprint="same", fpr=0.001, precision=0.999)
    ranked = rank_candidates([noisy, precise])
    assert ranked[0].name == "precise"
    assert ranked[0].readiness == "BLOCK_CONSIDERATION"


def _candidate(
    name: str,
    *,
    fingerprint: str,
    fpr: float = 0.0001,
    precision: float = 0.995,
) -> dict[str, object]:
    suite = _suite(fingerprint, fpr, precision)
    return {
        "candidate": name,
        "suites": {
            "balanced_policy": suite,
            "real_distribution": suite,
            "adversarial_evasion": suite,
            "context": suite,
            "time_based_real_chat": suite,
        },
        "stability": {"prediction_flip_rate": 0.01},
        "performance": {"p95_ms": 10.0, "steady_rss_bytes": 10_000},
        "deployment_complexity": 2,
    }


def _suite(fingerprint: str, fpr: float, precision: float) -> dict[str, object]:
    consequence = {
        "precision": precision,
        "precision_wilson_lower_95": precision,
        "recall": 0.95,
        "false_positive_rate": fpr,
        "false_negative_rate": 0.05,
        "f1": 0.97,
        "fpr_wilson_upper_95": fpr,
        "calibration": {"ece": 0.02, "brier_score": 0.01},
    }
    return {
        "suite": {"fingerprint": fingerprint, "n": 2},
        "semantic_label": {"macro_f1": 0.90},
        "consequences": {
            "review": consequence,
            "block": consequence,
            "strike": {**consequence, "precision": 0.90},
            "containment": {**consequence, "precision": 0.90},
        },
        "critical_slices": {
            "threat": {"n": 10, "n_gold_block": 10, "block_recall": 0.95},
        },
    }


def test_runtime_benchmark_reports_peak_rss_and_cpu() -> None:
    report = benchmark_callable(lambda: sum(range(20)), iterations=3, warmup=1)
    assert report["peak_rss_bytes"] >= report["steady_rss_bytes"] - abs(
        report["rss_delta_bytes"]
    )
    assert report["cpu_percent_equivalent"] >= 0.0


def test_queue_pressure_marks_timeout_as_fail_open() -> None:
    report = benchmark_queue_pressure(
        lambda: time.sleep(0.002),
        requests=4,
        workers=1,
        timeout_ms=1.0,
    )
    assert report["fail_open_count"] == 4
    assert report["fail_open_rate"] == 1.0


def test_artifact_size_counts_files_recursively(tmp_path) -> None:
    first = tmp_path / "a.bin"
    nested = tmp_path / "nested"
    nested.mkdir()
    second = nested / "b.bin"
    first.write_bytes(b"abc")
    second.write_bytes(b"12345")
    assert artifact_size_bytes([tmp_path]) == 8


def test_optimized_export_parity_requires_identical_head_decisions() -> None:
    reference = _bundle([0, 1])
    optimized = _bundle([0, 1])
    report = parity_report(reference, optimized)
    assert report["prediction_parity"] is True
    assert report["total_prediction_mismatches"] == 0

    changed = _bundle([0, 2])
    changed_report = parity_report(reference, changed)
    assert changed_report["prediction_parity"] is False
    assert changed_report["total_prediction_mismatches"] >= 1


def test_candidate_evidence_aggregates_three_seed_flips_and_ranges(tmp_path) -> None:
    seed_entries = [
        _seed_evidence_entry(tmp_path, 42, [0, 1], 10_000),
        _seed_evidence_entry(tmp_path, 138, [1, 1], 12_000),
        _seed_evidence_entry(tmp_path, 2026, [0, 1], 11_000),
    ]
    manifest = tmp_path / "manifest.json"
    _write_json(
        manifest,
        {
            "candidate": "test-candidate",
            "deployment_complexity": 2,
            "seeds": seed_entries,
        },
    )
    evidence = aggregate_evidence_manifest(manifest)
    assert evidence["stability"]["prediction_flip_rate"] == pytest.approx(0.5)
    assert evidence["performance"]["steady_rss_bytes"] == 12_000
    assert evidence["stability"]["thresholds"]["block"]["range"] > 0.0


def _seed_evidence_entry(
    tmp_path,
    seed: int,
    predictions: list[int],
    rss: int,
) -> dict[str, object]:
    seed_dir = tmp_path / str(seed)
    seed_dir.mkdir()
    suites = _write_suite_reports(seed_dir)
    bundle_path = seed_dir / "real-bundle.json"
    save_bundle(bundle_path, _bundle(predictions))
    calibration = seed_dir / "calibration.json"
    thresholds = seed_dir / "thresholds.json"
    performance = seed_dir / "performance.json"
    _write_json(calibration, {"temperatures": {"action": 1.0 + seed / 10000}})
    _write_json(thresholds, {"thresholds": {"block": 0.90 + seed / 100000}})
    _write_json(performance, _performance_fixture(seed, rss))
    return {
        "seed": seed,
        "suites": suites,
        "real_bundle": str(bundle_path),
        "calibration": str(calibration),
        "thresholds": str(thresholds),
        "performance": str(performance),
    }


def _write_suite_reports(seed_dir) -> dict[str, str]:
    suites = {}
    for name in (
        "balanced_policy",
        "real_distribution",
        "adversarial_evasion",
        "context",
        "time_based_real_chat",
    ):
        path = seed_dir / f"{name}.json"
        _write_json(path, _suite("same-suite", 0.0001, 0.995))
        suites[name] = str(path)
    return suites


def _performance_fixture(seed: int, rss: int) -> dict[str, float | int]:
    return {
        "p50_ms": 5.0,
        "p95_ms": 10.0 + seed / 1000,
        "p99_ms": 15.0,
        "throughput_per_second": 100.0,
        "steady_rss_bytes": rss,
        "peak_rss_bytes": rss + 500,
        "artifact_size_bytes": 1_000,
    }


def _write_json(path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_adversarial_bundle_report_requires_and_aggregates_all_families(tmp_path) -> None:
    examples = [
        _example("A", "BLOCK"),
        _example("B", "BLOCK"),
        _example("C", "ALLOW"),
        _example("D", "ALLOW"),
    ]
    clean_path = tmp_path / "clean.json"
    attacked_path = tmp_path / "attacked.json"
    save_bundle(clean_path, _bundle([1, 1, 0, 0]))
    save_bundle(attacked_path, _bundle([0, 1, 1, 0]))
    attacked = {family: attacked_path for family in ATTACK_FAMILIES}
    report = adversarial_bundle_report(examples, clean_path, attacked)
    assert report["worst_attack_success_rate"] == pytest.approx(0.5)
    assert report["worst_benign_corruption_false_positive_rate"] == pytest.approx(0.5)


def test_adversarial_bundle_report_rejects_missing_family(tmp_path) -> None:
    examples = [_example("A", "ALLOW")]
    clean_path = tmp_path / "clean.json"
    save_bundle(clean_path, _bundle([0]))
    with pytest.raises(ValueError, match="missing attack families"):
        adversarial_bundle_report(examples, clean_path, {})


def test_final_readiness_requires_drift_precision_too() -> None:
    evidence = _candidate("candidate", fingerprint="same", precision=0.995)
    suites = evidence["suites"]
    assert isinstance(suites, dict)
    drift = suites["time_based_real_chat"]
    assert isinstance(drift, dict)
    consequences = drift["consequences"]
    assert isinstance(consequences, dict)
    block = consequences["block"]
    assert isinstance(block, dict)
    block["precision"] = 0.98
    block["precision_wilson_lower_95"] = 0.98
    ranked = rank_candidates([evidence])
    assert ranked[0].readiness == "SHADOW_ONLY"


def test_composed_performance_report_includes_all_runtime_dimensions(tmp_path) -> None:
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"1234")
    report = benchmark_candidate(
        lambda: sum(range(10)),
        lambda: object(),
        [artifact],
        iterations=3,
        concurrency=2,
        queue_requests=4,
        timeout_ms=1000.0,
    )
    assert set(report) == {
        "concurrency_1",
        "concurrency_realistic",
        "startup",
        "queue_pressure",
        "artifact_size_bytes",
    }
    assert report["artifact_size_bytes"] == 4


def test_export_artifact_metadata_hashes_exact_bytes(tmp_path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"abc")
    metadata = artifact_metadata(artifact)
    assert metadata["size_bytes"] == 3
    assert metadata["sha256"] == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_lexical_artifact_export_is_data_only_and_measured(tmp_path) -> None:
    import numpy as np

    vectorizer = SimpleNamespace(
        get_feature_names_out=lambda: np.asarray(["a", "b"]),
        idf_=np.asarray([1.0, 2.0]),
        analyzer="word",
        ngram_range=(1, 2),
        lowercase=True,
        sublinear_tf=True,
        norm="l2",
        token_pattern=r"(?u)\\b\\w\\w+\\b",
    )
    head = SimpleNamespace(
        coef_=np.asarray([[1.0, -1.0]]),
        intercept_=np.asarray([0.0]),
        classes_=np.asarray([0, 1]),
    )
    model = SimpleNamespace(
        word=vectorizer,
        char=vectorizer,
        heads={"action": head},
        use_embeddings=True,
        serialization_variant="raw",
    )
    metadata = export_lexical_artifact(model, tmp_path)
    measured = sum(path.stat().st_size for path in tmp_path.iterdir())
    assert metadata["total_bytes"] == measured
    assert metadata["production_safe_data_format"] is True
    assert metadata["runtime_adapter_required"] is True
