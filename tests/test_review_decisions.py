"""Blind reviewers cannot silently turn opinions into training truth."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tools.dataset_qa.blind_review import make_packet
from tools.dataset_qa.review_decisions import review_summary, validate_decision

KEY = b"a-fixture-only-key-for-blind-review"


def _packet() -> dict[str, object]:
    return make_packet({
        "example_id": "G10-0001", "source": "synthetic",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "messages": [
            {"speaker": "A", "offset_ms": -1000, "text": "before target"},
            {"speaker": "B", "offset_ms": 0, "text": "target statement"},
            {"speaker": "A", "offset_ms": 100, "text": "future clarification"},
        ],
        "target_index": 1, "label": "HATE", "action": "BLOCK",
    }, KEY)


def _decision(packet: dict[str, object], reviewer: str) -> dict[str, Any]:
    return {
        "packet_id": packet["packet_id"], "reviewer_id": reviewer,
        "policy_version": "v1", "semantic_facts": ["text is benign"],
        "semantic_label": "SAFE", "action": "ALLOW",
        "review_priority": "NONE", "strike": False, "containment": "NONE",
        "containment_duration_seconds": None, "support_flow": "NONE",
        "uncertainty": "CLEAR", "evidence_message_indices": [1],
    }


def test_one_or_zero_reviews_cannot_admit_labels() -> None:
    packet = _packet()
    before = review_summary([packet], [])
    first = review_summary([packet], [_decision(packet, "r1")])
    assert before[0]["status"] == "awaiting_first_review"
    assert first[0]["status"] == "awaiting_second_review"
    assert not before[0]["training_eligible"]
    assert not first[0]["training_eligible"]


def test_two_agreeing_reviews_still_do_not_admit_labels() -> None:
    packet = _packet()
    summary = review_summary([packet], [
        _decision(packet, "r1"), _decision(packet, "r2"),
    ])
    assert summary[0]["status"] == "independent_agreement"
    assert summary[0]["reviewer_count"] == 2
    assert summary[0]["training_eligible"] is False


def test_disagreement_requires_adjudication() -> None:
    packet = _packet()
    changed = _decision(packet, "r2")
    changed["action"] = "BLOCK"
    result = review_summary([packet], [_decision(packet, "r1"), changed])
    assert result[0]["status"] == "adjudication"
    assert result[0]["training_eligible"] is False


def test_unresolved_policy_question_is_not_mistaken_for_agreement() -> None:
    packet = _packet()
    first = _decision(packet, "r1")
    second = _decision(packet, "r2")
    first["uncertainty"] = "POLICY_UNRESOLVED"
    second["uncertainty"] = "POLICY_UNRESOLVED"
    summary = review_summary([packet], [first, second])
    assert summary[0]["status"] == "owner_policy_question"


@pytest.mark.parametrize("forbidden", ["gold_label", "training_eligible", "notes"])
def test_secret_source_or_admission_fields_are_rejected(forbidden: str) -> None:
    packet = _packet()
    row = _decision(packet, "r1")
    row[forbidden] = "hidden"
    with pytest.raises(ValueError, match="prohibited"):
        validate_decision(row, packet)


def test_future_evidence_reference_is_rejected() -> None:
    packet = _packet()
    row = _decision(packet, "r1")
    row["evidence_message_indices"] = [2]
    with pytest.raises(ValueError, match="outside"):
        validate_decision(row, packet)


def test_same_reviewer_cannot_submit_twice() -> None:
    packet = _packet()
    row = _decision(packet, "r1")
    with pytest.raises(ValueError, match="repeat"):
        review_summary([packet], [row, deepcopy(row)])


def test_invalid_policy_and_non_boolean_strike_are_rejected() -> None:
    packet = _packet()
    row = _decision(packet, "r1")
    row["strike"] = 1
    with pytest.raises(ValueError, match="boolean"):
        validate_decision(row, packet)
    row["strike"] = False
    row["policy_version"] = "v2"
    with pytest.raises(ValueError, match="policy version"):
        validate_decision(row, packet)


@pytest.mark.parametrize("facts", [[], [" "], ["x"] * 33, ["x" * 201]])
def test_empty_or_unbounded_semantic_facts_fail_closed(facts: list[str]) -> None:
    packet = _packet()
    row = _decision(packet, "r1")
    row["semantic_facts"] = facts
    with pytest.raises(ValueError, match="semantic facts"):
        validate_decision(row, packet)


@pytest.mark.parametrize("evidence", [[], [1, 1]])
def test_missing_or_duplicated_visible_evidence_fails_closed(
    evidence: list[int],
) -> None:
    packet = _packet()
    row = _decision(packet, "r1")
    row["evidence_message_indices"] = evidence
    with pytest.raises(ValueError, match="evidence"):
        validate_decision(row, packet)


def test_zero_evidence_can_never_create_a_false_independent_agreement() -> None:
    packet = _packet()
    first = _decision(packet, "r1")
    second = _decision(packet, "r2")
    first["evidence_message_indices"] = []
    second["evidence_message_indices"] = []
    with pytest.raises(ValueError, match="at least one"):
        review_summary([packet], [first, second])


@pytest.mark.parametrize("uncertainties", [
    ("EVIDENCE_INSUFFICIENT", "EVIDENCE_INSUFFICIENT"),
    ("CLEAR", "EVIDENCE_INSUFFICIENT"),
    ("EVIDENCE_INSUFFICIENT", "CLEAR"),
])
def test_insufficient_evidence_does_not_become_independent_agreement(
    uncertainties: tuple[str, str],
) -> None:
    packet = _packet()
    first = _decision(packet, "r1")
    second = _decision(packet, "r2")
    first["uncertainty"], second["uncertainty"] = uncertainties
    statuses = review_summary([packet], [first, second])
    assert statuses[0]["status"] == "evidence_insufficient"
    assert statuses[0]["training_eligible"] is False


def test_evidence_insufficient_one_review_still_awaits_second() -> None:
    packet = _packet()
    first = _decision(packet, "r1")
    first["uncertainty"] = "EVIDENCE_INSUFFICIENT"
    result = review_summary([packet], [first])
    assert result[0]["status"] == "awaiting_second_review"


def test_unresolved_policy_has_precedence_over_insufficient_evidence() -> None:
    packet = _packet()
    first = _decision(packet, "r1")
    second = _decision(packet, "r2")
    first["uncertainty"] = "POLICY_UNRESOLVED"
    second["uncertainty"] = "EVIDENCE_INSUFFICIENT"
    result = review_summary([packet], [first, second])
    assert result[0]["status"] == "owner_policy_question"
    assert result[0]["training_eligible"] is False
