from __future__ import annotations

import json
from pathlib import Path

from tools.dataset_integration import build_outputs, check_outputs


ROOT = Path(".")
MANIFEST = ROOT / "data/integration/W11-split-manifest.json"
AUDIT = ROOT / "data/integration/W11-audit.json"


def test_w11_generated_outputs_are_reproducible() -> None:
    outputs = build_outputs(ROOT)
    assert check_outputs(ROOT, outputs) == []


def test_w11_split_manifest_preserves_family_and_partition_isolation() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    partitions = manifest["partitions"]
    sets = {name: set(ids) for name, ids in partitions.items()}

    assert manifest["records"] == 4500
    assert sum(len(ids) for ids in sets.values()) == 4500
    assert len(set().union(*sets.values())) == 4500

    for left_name, left_ids in sets.items():
        for right_name, right_ids in sets.items():
            if left_name < right_name:
                assert left_ids.isdisjoint(right_ids)

    partition_by_id = {
        example_id: name for name, ids in sets.items() for example_id in ids
    }
    for group in manifest["groups"]:
        group_partitions = {partition_by_id[item] for item in group["example_ids"]}
        assert group_partitions == {group["partition"]}


def test_w11_audit_has_no_redundant_exact_or_unresolved_cross_worker_conflict() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert audit["records"] == 4500
    assert audit["redundant_exact_groups"] == []
    assert all(
        row["disposition"] == "intentional_policy_contrast"
        for row in audit["cross_source_review"]
    )

    train = set(json.loads(MANIFEST.read_text(encoding="utf-8"))["partitions"]["train"])
    sensitive = {
        row["synthetic_id"]
        for row in audit["golden_leakage_candidates"]
        if row["training_sensitive"]
    }
    assert train.isdisjoint(sensitive)
