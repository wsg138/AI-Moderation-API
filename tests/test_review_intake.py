"""Coordinator-only intake refuses forged, stale, or duplicate review records."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tools.dataset_qa.blind_review import make_packet
from tools.dataset_qa.review_assignments import assign_reviewers, packet_digest
from tools.dataset_qa.review_intake import intake

KEY = b"offline-review-intake-test-key"


def _packet() -> dict[str, object]:
    return make_packet({
        "example_id": "G10-0001", "source": "synthetic",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "messages": [{"speaker": "A", "offset_ms": 0, "text": "hi"}],
        "target_index": 0, "label": "SAFE",
    }, KEY)


def _decision(packet: dict[str, object], reviewer: str) -> dict[str, Any]:
    return {
        "packet_id": packet["packet_id"], "reviewer_id": reviewer,
        "policy_version": "v1", "semantic_facts": ["normal greeting"],
        "semantic_label": "SAFE", "action": "ALLOW",
        "review_priority": "NONE", "strike": False, "containment": "NONE",
        "containment_duration_seconds": None, "support_flow": "NONE",
        "uncertainty": "CLEAR", "evidence_message_indices": [0],
    }


def _setup() -> tuple[dict[str, object], list[dict[str, object]]]:
    packet = _packet()
    _, manifest = assign_reviewers([packet], ["reviewerA", "reviewerB"], KEY)
    return packet, manifest


def test_no_decisions_stay_candidate_only() -> None:
    packet, manifest = _setup()
    result = intake([packet], manifest, [])
    assert result[0]["status"] == "awaiting_first_review"
    assert result[0]["training_eligible"] is False


def test_independent_agreement_still_requires_admission_gate() -> None:
    packet, manifest = _setup()
    results = intake([packet], manifest, [
        _decision(packet, "reviewerA"), _decision(packet, "reviewerB"),
    ])
    assert results[0]["status"] == "independent_agreement"
    assert results[0]["training_eligible"] is False


def test_disagreement_goes_to_adjudication() -> None:
    packet, manifest = _setup()
    second = _decision(packet, "reviewerB")
    second["semantic_label"] = "LOW_LEVEL_HARASSMENT"
    results = intake([packet], manifest, [_decision(packet, "reviewerA"), second])
    assert results[0]["status"] == "adjudication"


def test_unassigned_review_cannot_be_counted() -> None:
    packet, manifest = _setup()
    with pytest.raises(ValueError, match="unassigned"):
        intake([packet], manifest, [_decision(packet, "intruder")])


def test_duplicate_review_is_rejected() -> None:
    packet, manifest = _setup()
    first = _decision(packet, "reviewerA")
    with pytest.raises(ValueError, match="duplicate"):
        intake([packet], manifest, [first, deepcopy(first)])


def test_stale_packet_text_fails_hash_check() -> None:
    packet, manifest = _setup()
    changed = deepcopy(packet)
    changed["messages"][0]["text"] = "different"
    with pytest.raises(ValueError, match="frozen"):
        intake([changed], manifest, [])


def test_tampered_assignment_and_unapproved_field_fail_closed() -> None:
    packet, manifest = _setup()
    changed = deepcopy(manifest)
    changed[0]["assigned_reviewers"] = ["reviewerA", "reviewerA"]
    with pytest.raises(ValueError, match="distinct"):
        intake([packet], changed, [])
    decision = _decision(packet, "reviewerA")
    decision["training_eligible"] = True
    with pytest.raises(ValueError, match="prohibited"):
        intake([packet], manifest, [decision])


@pytest.mark.parametrize("field,bad", [
    ("semantic_facts", []),
    ("evidence_message_indices", []),
])
def test_unsubstantiated_reviewer_submission_fails_intake(
    field: str, bad: list[object],
) -> None:
    packet, manifest = _setup()
    row = _decision(packet, "reviewerA")
    row[field] = bad
    with pytest.raises(ValueError, match="semantic facts|at least one"):
        intake([packet], manifest, [row])


def test_two_insufficient_evidence_reviews_are_not_agreement() -> None:
    packet, manifest = _setup()
    first = _decision(packet, "reviewerA")
    second = _decision(packet, "reviewerB")
    first["uncertainty"] = second["uncertainty"] = "EVIDENCE_INSUFFICIENT"
    result = intake([packet], manifest, [first, second])
    assert result[0]["status"] == "evidence_insufficient"
    assert result[0]["reviewer_count"] == 2
    assert result[0]["training_eligible"] is False


def test_rehashed_malformed_packet_cannot_bypass_intake_schema() -> None:
    packet, manifest = _setup()
    changed = deepcopy(packet)
    changed["messages"][0]["text"] = {"secret": "source label"}
    changed_manifest = deepcopy(manifest)
    changed_manifest[0]["packet_sha256"] = packet_digest(changed)
    with pytest.raises(ValueError, match="speaker/text"):
        intake([changed], changed_manifest, [])


def test_review_intake_rejects_empty_batch() -> None:
    with pytest.raises(ValueError, match="at least one packet"):
        intake([], [], [])


@pytest.mark.parametrize("extra_field", [
    ("source_label", "BLACKMAIL"),
    ("training_eligible", True),
])
def test_coordinator_manifest_rejects_hidden_extra_fields(
    extra_field: tuple[str, object],
) -> None:
    packet, manifest = _setup()
    altered = deepcopy(manifest)
    altered[0][extra_field[0]] = extra_field[1]
    with pytest.raises(ValueError, match="prohibited fields"):
        intake([packet], altered, [])


@pytest.mark.parametrize("bad_alias", ["", "reviewer name", "x", "reviewer@outside"])
def test_coordinator_manifest_rejects_invalid_reviewer_alias(
    bad_alias: str,
) -> None:
    packet, manifest = _setup()
    altered = deepcopy(manifest)
    altered[0]["assigned_reviewers"][0] = bad_alias
    with pytest.raises(ValueError, match="invalid reviewer identity"):
        intake([packet], altered, [])
