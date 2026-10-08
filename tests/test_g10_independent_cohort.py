"""Full G10 reviewer cohort keeps controls, future messages and labels hidden."""
from __future__ import annotations

import json

import pytest

from tools.dataset_qa.freshness import ROOT
from tools.dataset_qa.g10_independent_cohort import build_cohort
from tools.dataset_qa.owner_blackmail_audit import G10
from tools.dataset_qa.review_assignments import _check_packet, assign_reviewers

KEY = b"synthetic-review-test-key-not-for-reuse"


def _source() -> bytes:
    path = ROOT / G10
    if not path.is_file():
        pytest.skip("G10 synthetic source not available in this checkout")
    return path.read_bytes()


def test_full_500_blind_packet_cohort_includes_both_controls_and_candidates() -> None:
    raw = _source()
    packets, mapping = build_cohort(raw, KEY)
    assert len(packets) == len(mapping) == 500
    assert len({p["packet_id"] for p in packets}) == 500
    assert [p["packet_id"] for p in packets] == [
        row["packet_id"] for row in mapping
    ]
    assert {int(str(m["example_id"])[4:]) for m in mapping} == set(range(1, 501))
    assert all(_check_packet(p) == p["packet_id"] for p in packets)


def test_packet_excludes_source_answer_proposal_category_and_future_content() -> None:
    raw = _source()
    packets, _ = build_cohort(raw, KEY)
    allowed = {"packet_id", "platform_hint", "channel_profile",
               "messages", "target_index"}
    assert all(set(packet) == allowed for packet in packets)
    source = {row["example_id"]: row for row in map(
        json.loads, raw.decode("utf-8").splitlines()
    )}
    _, mapping = build_cohort(raw, KEY)
    for packet, entry in zip(packets, mapping):
        original = source[entry["example_id"]]
        assert packet["target_index"] == len(packet["messages"]) - 1
        assert len(packet["messages"]) == original["target_index"] + 1
        assert all(set(m) == {"speaker", "offset_ms", "text"}
                   for m in packet["messages"])
        assert "example_id" not in packet
        assert "label" not in packet
        assert "reason_codes" not in packet
        assert "preliminary_disposition" not in packet
        assert "training_eligible" not in packet


def test_same_key_yields_reproducible_blind_order_and_different_key_changes_ids() -> None:
    raw = _source()
    first, mapping = build_cohort(raw, KEY)
    duplicate, duplicate_map = build_cohort(raw, KEY)
    other, _ = build_cohort(raw, b"different-reviewer-secret-key")
    assert first == duplicate
    assert mapping == duplicate_map
    assert {p["packet_id"] for p in first} != {
        p["packet_id"] for p in other
    }


def test_frozen_source_lineage_and_no_source_modification() -> None:
    raw = _source()
    _, mapping = build_cohort(raw, KEY)
    assert all(entry["source_line"] == int(str(entry["example_id"])[4:])
               for entry in mapping)
    assert len({entry["source_sha256"] for entry in mapping}) == 1
    assert (ROOT / G10).read_bytes() == raw


def test_short_key_and_source_changes_are_rejected() -> None:
    raw = _source()
    with pytest.raises(ValueError, match="16 or more"):
        build_cohort(raw, b"short")
    changed = raw.replace(b"give me 64 diamonds", b"give me 63 diamonds", 1)
    assert changed != raw
    with pytest.raises(ValueError, match="source changed"):
        build_cohort(changed, KEY)


def test_existing_two_reviewer_assignment_can_consume_cohort() -> None:
    packets, _ = build_cohort(_source(), KEY)
    distributed, manifest = assign_reviewers(
        packets, ["reviewer_one", "reviewer_two", "reviewer_three"], KEY
    )
    assert len(manifest) == 500
    assert all(len(set(item["assigned_reviewers"])) == 2
               for item in manifest)
    assert sum(len(group) for group in distributed.values()) == 1000
    assert all("example_id" not in json.dumps(group)
               for group in distributed.values())
