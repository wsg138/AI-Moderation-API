from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest  # pyright: ignore[reportMissingImports]

from workers.w25.config import MODEL_SPECS, NEURAL_SEEDS
from workers.w25.contract import (
    HEAD_NAMES,
    HEAD_VALUES,
    PredictionBundle,
    public_prediction_record,
)
from workers.w25.data import (
    AdmittedSource,
    assert_group_isolation,
    freeze_group_partitions,
    load_source_partition,
    normalize_text,
    serialize_variant,
    verify_admitted_source,
)
from workers.w25.metrics import (
    base_rate_table,
    binary_metrics,
    calibration_metrics,
    expected_precision,
    risk_coverage_curve,
    seed_flip_rate,
)
from workers.w25.suites import assert_required_suites_ready, load_frozen_suite


def test_model_revisions_are_immutable_sha_pins() -> None:
    assert len(NEURAL_SEEDS) >= 3  # nosec B101
    for spec in MODEL_SPECS.values():
        assert len(spec.revision) == 40  # nosec B101
        assert all(char in "0123456789abcdef" for char in spec.revision)  # nosec B101
        assert spec.license in {"MIT", "Apache-2.0"}  # nosec B101


def test_normalized_serialization_preserves_raw_and_adds_normalized() -> None:
    raw = "A\u200b  Ｂ"
    assert normalize_text(raw) == "A B"  # nosec B101
    serialized = serialize_variant(raw, "raw+normalized")
    assert "RAW:\nA\u200b  Ｂ" in serialized  # nosec B101
    assert "NORMALIZED:\nA B" in serialized  # nosec B101


def test_group_freeze_never_splits_a_family() -> None:
    records = [
        {"example_id": f"E-{family}-{index}", "family_id": family}
        for family in ("A", "B", "C", "D", "E", "F")
        for index in range(3)
    ]
    manifest = freeze_group_partitions(records, group_field="family_id")
    assert_group_isolation(records, manifest, group_field="family_id")
    assert sum(map(len, manifest.values())) == len(records)  # nosec B101


def test_group_freeze_is_reproducible() -> None:
    records = [
        {"example_id": f"E-{index}", "family": f"F-{index // 2}"}
        for index in range(20)
    ]
    left = freeze_group_partitions(records, group_field="family")
    right = freeze_group_partitions(records, group_field="family")
    assert left == right  # nosec B101


def test_admission_rejects_w20_before_file_access() -> None:
    source = AdmittedSource(
        path="data/eval/W20-fresh-acceptance.jsonl",
        sha256="0" * 64,
        role="test",
        reviewed_by="reviewer",
        frozen_group_field="family_id",
    )
    with pytest.raises(ValueError, match="forbidden"):
        verify_admitted_source(source)


def test_binary_metrics_report_scaled_false_positive_rates() -> None:
    report = binary_metrics([0, 0, 0, 1, 1], [0, 1, 0, 1, 0])
    assert report["precision"] == 0.5  # nosec B101
    assert report["recall"] == 0.5  # nosec B101
    assert report["false_positive_rate"] == pytest.approx(1 / 3)  # nosec B101
    assert report["false_per_100k_benign"] == pytest.approx(100_000 / 3)  # nosec B101


def test_base_rate_precision_uses_requested_formula() -> None:
    value = expected_precision(recall=0.97, false_positive_rate=0.001, prevalence=0.001)
    expected = (0.97 * 0.001) / ((0.97 * 0.001) + (0.001 * 0.999))
    assert value == pytest.approx(expected)  # nosec B101
    table = base_rate_table(
        recall=0.97,
        false_positive_rate=0.001,
        prevalences=(0.0005, 0.001, 0.01),
    )
    assert [row["prevalence"] for row in table] == [0.0005, 0.001, 0.01]  # nosec B101


def test_calibration_metrics_include_ece_and_brier() -> None:
    report = calibration_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9], bins=2)
    assert 0.0 <= report["ece"] <= 1.0  # nosec B101
    assert report["brier_score"] == pytest.approx(0.025)  # nosec B101


def test_selective_risk_orders_low_uncertainty_first() -> None:
    curve = risk_coverage_curve([True, False, True], [0.1, 0.9, 0.2])
    assert curve[0]["risk"] == 0.0  # nosec B101
    assert curve[-1]["coverage"] == 1.0  # nosec B101
    assert curve[-1]["risk"] == pytest.approx(1 / 3)  # nosec B101


def test_seed_flip_rate_counts_any_seed_disagreement() -> None:
    rate = seed_flip_rate({42: [0, 1, 1], 138: [0, 0, 1], 2026: [0, 1, 1]})
    assert rate == pytest.approx(1 / 3)  # nosec B101


def test_public_contract_is_exact_allowlist() -> None:
    predictions = {name: [0] for name in HEAD_NAMES}
    probabilities = {
        name: [[1.0] + [0.0] * (len(HEAD_VALUES[name]) - 1)]
        for name in HEAD_NAMES
    }
    bundle = PredictionBundle(predictions, probabilities, [0.1])
    record = public_prediction_record(
        candidate="test",
        seed=42,
        bundle=bundle,
        index=0,
        abstained=False,
    )
    assert set(record) == {  # nosec B101
        "candidate",
        "seed",
        "semantic_label",
        "message_action",
        "review_priority",
        "strike_recommendation",
        "containment",
        "support_flow",
        "confidence",
        "uncertainty",
        "abstained",
    }


def test_admissions_gate_pins_w21_and_private_w26() -> None:
    payload = json.loads(Path("workers/w25/admissions.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ready"  # nosec B101
    assert len(payload["sources"]) == 2  # nosec B101
    sources = {source["role"]: source for source in payload["sources"]}
    adversarial = sources["adversarial_training"]
    assert adversarial["sha256"] == (  # nosec B101
        "4fcffc4cecc87b0d9acaad4e409d2c52cdc09b90811263433c06436d0c8c523c"
    )
    assert adversarial["partition_manifest_sha256"] == (  # nosec B101
        "087588150b349913a76d3d65862bcd418ec6d4ebe7630357f76eda898d8d9d34"
    )
    real_chat = sources["real_chat_training"]
    assert real_chat["storage"] == "private"  # nosec B101
    assert real_chat["sha256"] == (  # nosec B101
        "bc013c6859c7cb835ba92d8dce6c8b97d1d4b0fac7cbdd3dc618fcecc84c9ec3"
    )
    assert real_chat["partition_manifest_sha256"] == (  # nosec B101
        "e096f92f463406f12545f5682abf755aed2de8537484b663b1fc5ac4931017d5"
    )


def test_w21_adversarial_suite_uses_only_frozen_test_families() -> None:
    examples = load_source_partition(
        "data/candidates/W21-adversarial-evasion.jsonl",
        "test",
    )
    assert len(examples) == 180  # nosec B101
    assert len({item.family_id for item in examples}) == 9  # nosec B101
    split = json.loads(
        Path("data/integration/W25-W21-adversarial-split.json").read_text(encoding="utf-8")
    )
    test_ids = {item.example_id for item in examples}
    assert test_ids == set(split["partitions"]["test"])  # nosec B101
    assert test_ids.isdisjoint(split["partitions"]["train"])  # nosec B101
    assert test_ids.isdisjoint(split["partitions"]["development"])  # nosec B101


def test_required_final_suites_remain_blocked_until_real_chat_is_frozen() -> None:
    with pytest.raises(RuntimeError, match="required W25 suites are not ready"):
        assert_required_suites_ready()


def test_balanced_policy_suite_caps_each_w11_test_label_deterministically() -> None:
    examples = load_frozen_suite("balanced_policy")
    counts = Counter(item.label for item in examples)
    assert examples  # nosec B101
    assert max(counts.values()) <= 20  # nosec B101
    assert [item.example_id for item in examples] == sorted(  # nosec B101
        item.example_id for item in examples
    )


def test_adversarial_suite_combines_w11_and_w21_frozen_holdouts() -> None:
    examples = load_frozen_suite("adversarial_evasion")
    assert len(examples) == 616  # nosec B101
    assert len({item.example_id for item in examples}) == 616  # nosec B101


def test_context_suite_waits_for_real_chat_mirror_controls() -> None:
    with pytest.raises(RuntimeError, match="W25 suite is not ready: context"):
        load_frozen_suite("context")


def test_private_admission_is_hash_pinned_under_explicit_root(tmp_path, monkeypatch) -> None:
    data_path = tmp_path / "reviewed.jsonl"
    split_path = tmp_path / "split.json"
    data_path.write_text("{}\n", encoding="utf-8")
    split_path.write_text('{"partitions": {}}\n', encoding="utf-8")
    monkeypatch.setenv("W25_PRIVATE_DATA_ROOT", str(tmp_path))
    source = AdmittedSource(
        path="reviewed.jsonl",
        sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(),
        role="real_chat_training",
        reviewed_by="reviewer",
        frozen_group_field="session_id",
        storage="private",
        partition_manifest="split.json",
        partition_manifest_sha256=hashlib.sha256(split_path.read_bytes()).hexdigest(),
        partition_manifest_storage="private",
    )
    assert verify_admitted_source(source) == data_path  # nosec B101


def test_private_admission_rejects_path_escape(tmp_path, monkeypatch) -> None:
    outside = tmp_path.parent / "outside.jsonl"
    outside.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("W25_PRIVATE_DATA_ROOT", str(tmp_path))
    source = AdmittedSource(
        path="../outside.jsonl",
        sha256=hashlib.sha256(outside.read_bytes()).hexdigest(),
        role="test",
        reviewed_by="reviewer",
        frozen_group_field="session_id",
        storage="private",
    )
    with pytest.raises(ValueError, match="escapes"):
        verify_admitted_source(source)
