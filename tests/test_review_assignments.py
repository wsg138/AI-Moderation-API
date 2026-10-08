"""Two distinct blind-review assignments, no gold or future data leakage."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tools.dataset_qa.blind_review import make_packet
from tools.dataset_qa.review_assignments import assign_reviewers, packet_digest

KEY = b"test-only-reviewer-assignments-secret"


def _packet(number: int) -> dict[str, object]:
    record: dict[str, Any] = {
        "example_id": f"G10-{number:04d}", "source": "synthetic",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "messages": [
            {"speaker": "A", "offset_ms": 0, "text": f"target {number}"},
            {"speaker": "A", "offset_ms": 1, "text": "future"},
        ],
        "target_index": 0, "label": "SAFE", "action": "ALLOW",
    }
    return make_packet(record, KEY)


def test_two_distinct_assignments_are_balanced() -> None:
    packets = [_packet(i) for i in range(1, 22)]
    assigned, manifest = assign_reviewers(packets, ["r1", "r2", "r3"], KEY)
    assert len(manifest) == len(packets)
    assert all(len(row["assigned_reviewers"]) == 2 for row in manifest)
    assert all(len(set(row["assigned_reviewers"])) == 2 for row in manifest)
    assert max(map(len, assigned.values())) - min(map(len, assigned.values())) <= 1
    assert all("label" not in row and "future" not in str(row) for rows in
               assigned.values() for row in rows)


def test_assignment_is_deterministic_and_order_invariant() -> None:
    packets = [_packet(i) for i in range(1, 10)]
    first = assign_reviewers(packets, ["a1", "b2", "c3"], KEY)
    second = assign_reviewers(list(reversed(packets)), ["c3", "a1", "b2"], KEY)
    assert first == second


def test_packet_digest_changes_when_visible_text_changes() -> None:
    packet = _packet(1)
    changed = deepcopy(packet)
    changed["messages"][0]["text"] = "different text"
    assert packet_digest(packet) != packet_digest(changed)


def test_original_gold_and_later_messages_cannot_be_assigned() -> None:
    packet = _packet(1)
    packet["label"] = "BLOCK"
    with pytest.raises(ValueError, match="fields"):
        assign_reviewers([packet], ["r1", "r2"], KEY)


def test_post_target_messages_are_rejected() -> None:
    packet = _packet(1)
    packet["messages"].append({"speaker": "A", "offset_ms": 10, "text": "future"})
    with pytest.raises(ValueError, match="post-target"):
        assign_reviewers([packet], ["r1", "r2"], KEY)


def test_duplicate_or_single_reviewer_cannot_satisfy_double_review() -> None:
    packets = [_packet(1)]
    with pytest.raises(ValueError, match="duplicate reviewer"):
        assign_reviewers(packets, ["same", "same"], KEY)
    with pytest.raises(ValueError, match="2-20"):
        assign_reviewers(packets, ["one"], KEY)


def test_duplicate_packet_and_short_key_fail_closed() -> None:
    packet = _packet(1)
    with pytest.raises(ValueError, match="duplicate review packet"):
        assign_reviewers([packet, packet], ["r1", "r2"], KEY)
    with pytest.raises(ValueError, match="too short"):
        assign_reviewers([packet], ["r1", "r2"], b"x")


@pytest.mark.parametrize("field,value", [
    ("platform_hint", {"source_label": "BLACKMAIL"}),
    ("channel_profile", ""),
    ("target_index", True),
])
def test_packet_invalid_scope_or_boolean_target_is_rejected(
    field: str, value: object,
) -> None:
    packet = _packet(1)
    packet[field] = value
    with pytest.raises(ValueError, match="scope|target"):
        assign_reviewers([packet], ["r1", "r2"], KEY)


@pytest.mark.parametrize("field,value", [
    ("speaker", {"gold": "BLACKMAIL"}),
    ("text", {"source_label": "BLOCK"}),
    ("offset_ms", True),
    ("offset_ms", 0.1),
])
def test_message_nested_metadata_or_invalid_timestamp_is_rejected(
    field: str, value: object,
) -> None:
    packet = _packet(1)
    packet["messages"][0][field] = value
    with pytest.raises(ValueError, match="timestamp|speaker/text"):
        assign_reviewers([packet], ["r1", "r2"], KEY)


def test_future_dated_earlier_message_is_rejected_even_if_target_is_last() -> None:
    packet = _packet(1)
    packet["messages"].insert(
        0, {"speaker": "B", "offset_ms": 10, "text": "future information"}
    )
    packet["target_index"] = 1
    with pytest.raises(ValueError, match="future"):
        assign_reviewers([packet], ["r1", "r2"], KEY)


def test_empty_assignment_is_not_a_completed_reviewer_batch() -> None:
    with pytest.raises(ValueError, match="at least one packet"):
        assign_reviewers([], ["reviewerA", "reviewerB"], KEY)
