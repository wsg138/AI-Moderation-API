"""Small public-metadata-only tests: no datasets, training, or private files."""

from __future__ import annotations

import copy
import json

import pytest

from tools.data_v2.source_admission_gate import REGISTRY, audit_registry, source_blockers


def fixture_approved() -> dict[str, object]:
    return {
        "id": "fictional-reviewed-synthetic",
        "kind": "synthetic_labeled",
        "status": "approved_training",
        "use": ["train"],
        "exclusions": [],
        "privacy": "public_synthetic",
        "rights_approval_ref": "TEST_ONLY-1",
        "privacy_approval_ref": "TEST_ONLY-2",
        "label_approval_ref": "TEST_ONLY-3",
    }


def test_existing_registry_sources_are_not_training_ready() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    audit = audit_registry(registry)
    assert len(audit["results"]) == 8
    assert audit["metadata_preflight_pass_count"] == 0
    assert audit["not_an_authorization"] is True


def test_pr52_candidate_is_blocked() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    item = next(s for s in registry["sources"] if s["id"] == "pr52-g10-g27")
    blockers = source_blockers(item)
    assert "not_training_approved" in blockers
    assert "explicit_training_exclusion" in blockers


@pytest.mark.parametrize("id", ["w20-acceptance", "w27-frozen", "real-review-heldout-v1"])
def test_protected_evaluation_is_blocked_even_with_forged_approvals(id: str) -> None:
    item = fixture_approved()
    item["id"] = id
    assert "protected_evaluation" in source_blockers(item)


def test_private_candidate_cannot_pass() -> None:
    item = fixture_approved()
    item["privacy"] = "private_local_not_cloud_approved"
    assert "privacy_not_training_cleared" in source_blockers(item)


def test_approval_references_are_required() -> None:
    item = fixture_approved()
    item.pop("label_approval_ref")
    assert "missing_label_approval_ref" in source_blockers(item)


def test_synthetic_fixture_metadata_preflight_is_not_authorization() -> None:
    item = fixture_approved()
    registry = {
        "schema_version": "data-v2-source-registry/1",
        "eligibility_values": ["approved_training"],
        "sources": [item],
    }
    audit = audit_registry(registry)
    assert audit["metadata_preflight_pass_count"] == 1
    assert audit["not_an_authorization"] is True


def test_duplicate_source_id_rejected() -> None:
    item = fixture_approved()
    registry = {
        "schema_version": "data-v2-source-registry/1",
        "eligibility_values": ["approved_training"],
        "sources": [item, copy.deepcopy(item)],
    }
    with pytest.raises(ValueError, match="duplicate source ID"):
        audit_registry(registry)


def test_unknown_eligibility_status_rejected() -> None:
    item = fixture_approved()
    item["status"] = "unreviewed-but-someone-said-yes"
    registry = {
        "schema_version": "data-v2-source-registry/1",
        "eligibility_values": ["approved_training"],
        "sources": [item],
    }
    with pytest.raises(ValueError, match="unknown eligibility status"):
        audit_registry(registry)
