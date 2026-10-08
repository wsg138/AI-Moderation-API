"""Validate independent blind decisions without certifying any training labels."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

LABELS = {
    "SAFE", "GAMEPLAY_VIOLENCE", "LOW_LEVEL_HARASSMENT",
    "SEVERE_HARASSMENT", "STAFF_TARGETED_ABUSE", "REAL_WORLD_THREAT",
    "SELF_HARM_INSTRUCTION", "SELF_HARM_INTENT",
    "THIRD_PARTY_SELF_HARM_CONCERN", "HATE", "SLUR_USE",
    "SEXUAL_CONTENT", "SEXUAL_MINOR", "DOXXING", "BLACKMAIL",
    "GROOMING", "DANGEROUS_REAL_WORLD_INSTRUCTIONS", "AMBIGUOUS_REVIEW",
}
OUTCOMES = {
    "action": {"ALLOW", "BLOCK", "REVIEW"},
    "review_priority": {"NONE", "NORMAL", "URGENT"},
    "containment": {"NONE", "MUTE"},
    "support_flow": {"NONE", "SELF_HARM_CHECK", "TARGET_SAFETY_CHECK"},
}
REQUIRED = {
    "packet_id", "reviewer_id", "policy_version", "semantic_facts",
    "semantic_label", "action", "review_priority", "strike",
    "containment", "containment_duration_seconds", "support_flow",
    "uncertainty", "evidence_message_indices",
}
UNCERTAINTY = {"CLEAR", "EVIDENCE_INSUFFICIENT", "POLICY_UNRESOLVED"}
DECISION_FIELDS = (
    "semantic_label", "action", "review_priority", "strike", "containment",
    "containment_duration_seconds", "support_flow", "uncertainty",
)


def _validate_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value


def _validate_duration(row: dict[str, Any]) -> None:
    duration = row["containment_duration_seconds"]
    if row["containment"] == "NONE" and duration is not None:
        raise ValueError("NONE containment requires null duration")
    if duration is not None and (type(duration) is not int or duration <= 0):
        raise ValueError("mute duration must be a positive integer or null")


def _validate_outcomes(row: dict[str, Any]) -> None:
    if row["semantic_label"] not in LABELS:
        raise ValueError("unknown semantic label")
    for field, allowed in OUTCOMES.items():
        if row[field] not in allowed:
            raise ValueError(f"invalid {field}")
    if type(row["strike"]) is not bool:
        raise ValueError("strike must be a boolean")
    if row["uncertainty"] not in UNCERTAINTY:
        raise ValueError("unknown uncertainty value")
    _validate_duration(row)


def _validate_facts(facts: object) -> None:
    if not isinstance(facts, list):
        raise ValueError("semantic facts must be bounded text entries")
    if not 1 <= len(facts) <= 32:
        raise ValueError("semantic facts require 1-32 evidence-backed entries")
    if not all(isinstance(f, str) and f.strip() and len(f) <= 200 for f in facts):
        raise ValueError("semantic facts must be bounded nonblank text entries")


def _validate_evidence(indices: object, messages: object) -> None:
    if not isinstance(messages, list) or not isinstance(indices, list):
        raise ValueError("invalid packet context or evidence indices")
    if not indices:
        raise ValueError("review evidence must cite at least one visible message")
    if not all(type(i) is int and 0 <= i < len(messages) for i in indices):
        raise ValueError("evidence index outside as-of-target context")
    if len(indices) != len(set(indices)):
        raise ValueError("duplicate evidence message index")


def validate_decision(
    row: dict[str, Any], packet: dict[str, object],
) -> None:
    """Enforce blinded decision structure; never accept admission/gold fields."""
    if set(row) != REQUIRED:
        raise ValueError("review decision has missing or prohibited fields")
    if row["packet_id"] != packet.get("packet_id"):
        raise ValueError("decision references a different packet")
    _validate_text(row["reviewer_id"], "reviewer_id")
    if row["policy_version"] != "v1":
        raise ValueError("unsupported policy version")
    _validate_outcomes(row)
    _validate_facts(row["semantic_facts"])
    _validate_evidence(row["evidence_message_indices"], packet.get("messages"))


def _decision_fingerprint(row: dict[str, Any]) -> tuple[object, ...]:
    return tuple(row[field] for field in DECISION_FIELDS)


def review_summary(
    packets: list[dict[str, object]], decisions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    """Produce coordinator-only statuses; NEVER mark any case training-ready."""
    packet_by_id = {packet["packet_id"]: packet for packet in packets}
    if len(packet_by_id) != len(packets):
        raise ValueError("duplicate review packet IDs")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for decision in decisions:
        identifier = decision.get("packet_id")
        if identifier not in packet_by_id:
            raise ValueError("decision references unknown packet")
        validate_decision(decision, packet_by_id[identifier])
        if any(d["reviewer_id"] == decision["reviewer_id"] for d in grouped[identifier]):
            raise ValueError("repeat decision from same reviewer")
        grouped[identifier].append(decision)
    return [_status(packet["packet_id"], grouped[packet["packet_id"]]) for packet in packets]


def _status(identifier: str, decisions: list[dict[str, Any]]) -> dict[str, object]:
    status = "awaiting_first_review"
    if len(decisions) == 1:
        status = "awaiting_second_review"
    if len(decisions) >= 2:
        fingerprints = {_decision_fingerprint(row) for row in decisions}
        status = "independent_agreement" if len(fingerprints) == 1 else "adjudication"
    if any(d["uncertainty"] == "POLICY_UNRESOLVED" for d in decisions):
        status = "owner_policy_question"
    return {
        "packet_id": identifier, "status": status,
        "reviewer_count": len(decisions),
        "training_eligible": False,
    }
