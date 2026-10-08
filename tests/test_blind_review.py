"""Tests for synthetic-only blind review packets and separate join crosswalk."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.dataset_qa.blind_review import (
    _outside_checkout,
    build_packets,
    make_packet,
    opaque_id,
)
from tools.dataset_qa.freshness import ROOT, batch_files

KEY = b"a-test-only-review-key-not-for-production"


def _record() -> dict[str, object]:
    return {
        "example_id": "G10-0001",
        "source": "synthetic",
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_public",
        "messages": [
            {"speaker": "A", "offset_ms": -1000, "text": "ordinary chat"},
            {"speaker": "B", "offset_ms": 0, "text": "this is the target"},
            {"speaker": "A", "offset_ms": 1000, "text": "FUTURE_ONLY_ANSWER"},
        ],
        "target_index": 1,
        "label": "REAL_WORLD_THREAT",
        "action": "BLOCK",
        "review_priority": "URGENT",
        "strike": True,
        "reason_codes": ["FUTURE_ONLY_ANSWER"],
        "notes": "FUTURE_ONLY_ANSWER",
        "family_id": "FUTURE_ONLY_ANSWER",
    }


def test_review_packet_hides_labels_source_id_and_future_context() -> None:
    packet = make_packet(_record(), KEY)
    assert set(packet) == {
        "packet_id", "platform_hint", "channel_profile", "messages", "target_index"
    }
    assert packet["packet_id"].startswith("R-")
    assert len(packet["messages"]) == 2
    assert set(packet["messages"][0]) == {"speaker", "offset_ms", "text"}
    rendered = json.dumps(packet)
    for forbidden in (
        "G10-0001", "REAL_WORLD_THREAT", "BLOCK", "URGENT",
        "FUTURE_ONLY_ANSWER", "reason_codes", "family_id",
    ):
        assert forbidden not in rendered


def test_later_exoneration_and_gold_relabel_do_not_change_packet() -> None:
    changed = deepcopy(_record())
    changed["messages"][2]["text"] = "new future exoneration"
    changed["label"] = "SAFE"
    changed["action"] = "ALLOW"
    changed["notes"] = "gold correction"
    assert make_packet(changed, KEY) == make_packet(_record(), KEY)


def test_review_ids_are_stable_but_not_obvious_batch_ids() -> None:
    first = opaque_id("G10-0001", KEY)
    assert first == opaque_id("G10-0001", KEY)
    assert first != opaque_id("G10-0002", KEY)
    assert first != opaque_id("G10-0001", b"another-test-key-of-sufficient-length")
    assert "G10" not in first


@pytest.mark.parametrize("source", ["real", "model_prediction", None])
def test_non_synthetic_inputs_fail_closed(source: object) -> None:
    record = _record()
    record["source"] = source
    with pytest.raises(ValueError, match="public synthetic"):
        make_packet(record, KEY)


def test_post_target_text_cannot_hide_a_pre_target_future_offset() -> None:
    record = _record()
    record["messages"][0]["offset_ms"] = 9000
    with pytest.raises(ValueError, match="after target"):
        make_packet(record, KEY)


def test_output_in_checkout_is_rejected() -> None:
    with pytest.raises(ValueError, match="outside Git checkout"):
        _outside_checkout(Path("tests/private-crosswalk.jsonl"))


def test_requires_an_unpredictable_secret() -> None:
    with pytest.raises(ValueError, match="16"):
        build_packets(ROOT, b"short")


def _assert_hidden_fields(
    packets: list[dict[str, object]], crosswalk: list[dict[str, object]]
) -> None:
    assert all("label" not in p and "example_id" not in p for p in packets)
    assert all("label" not in row and "action" not in row for row in crosswalk)
    assert {row["example_id"][:3] for row in crosswalk} == {
        f"G{n:02d}" for n in range(10, 28)
    }


def test_all_available_candidate_records_have_blind_packets() -> None:
    if not batch_files(ROOT):
        pytest.skip("main branch has no G10-G27 candidates")
    packets, crosswalk = build_packets(ROOT, KEY)
    assert len(packets) == len(crosswalk) == 9000
    assert len({p["packet_id"] for p in packets}) == 9000
    _assert_hidden_fields(packets, crosswalk)
