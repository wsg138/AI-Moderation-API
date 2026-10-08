from __future__ import annotations

import json
from pathlib import Path

from tools import dataset_integration

ROOT = Path(".")
MANIFEST = ROOT / "data/integration/W11-split-manifest.json"
AUDIT = ROOT / "data/integration/W11-audit.json"
ADVERSARIAL = ROOT / "data/integration/W11-adversarial-eval-manifest.json"


def test_w11_generated_outputs_are_reproducible() -> None:
    outputs = dataset_integration.build_outputs(ROOT)
    assert dataset_integration.check_outputs(ROOT, outputs) == []


def _partition_by_id(partitions: dict[str, list[str]]) -> dict[str, str]:
    return {
        example_id: name
        for name, ids in partitions.items()
        for example_id in ids
    }


def _assert_group_isolation(
    groups: list[dict[str, object]],
    partition_by_id: dict[str, str],
) -> None:
    for group in groups:
        ids = group["example_ids"]
        assert isinstance(ids, list)
        group_partitions = {partition_by_id[str(item)] for item in ids}
        assert group_partitions == {group["partition"]}


def _assert_cross_source_isolation(
    partition_by_id: dict[str, str],
    rows: list[dict[str, object]],
) -> None:
    for row in rows:
        assert partition_by_id[str(row["left"])] == partition_by_id[str(row["right"])]


def test_w11_split_manifest_preserves_family_and_partition_isolation() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    partitions = manifest["partitions"]
    all_ids = [example_id for ids in partitions.values() for example_id in ids]

    assert manifest["records"] == 4500
    assert len(all_ids) == 4500
    assert len(set(all_ids)) == 4500

    partition_by_id = _partition_by_id(partitions)
    _assert_group_isolation(manifest["groups"], partition_by_id)

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    _assert_cross_source_isolation(
        partition_by_id,
        audit["cross_source_near_candidates"],
    )


def test_w11_audit_has_no_redundant_exact_or_unresolved_cross_worker_conflict() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert audit["records"] == 4500
    assert audit["redundant_exact_groups"] == []
    assert all(
        row["disposition"] == "intentional_policy_contrast"
        for row in audit["cross_source_review"]
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    train = set(manifest["partitions"]["train"])
    sensitive = {
        row["synthetic_id"]
        for row in audit["golden_leakage_candidates"]
        if row["training_sensitive"]
    }
    assert train.isdisjoint(sensitive)
    assert sensitive <= set(manifest["partitions"]["frozen_adversarial"])

    adversarial = json.loads(ADVERSARIAL.read_text(encoding="utf-8"))
    assert adversarial["algorithm_version"] == manifest["algorithm_version"]
    assert adversarial["example_ids"] == manifest["partitions"]["frozen_adversarial"]


def test_w11_rejects_unadmitted_candidate_batches() -> None:
    examples = dataset_integration.load_synthetic(ROOT)
    assert len(examples) == 4500
    assert {row.source_prefix for row in examples} == {
        f"G{index:02d}" for index in range(1, 10)
    }
