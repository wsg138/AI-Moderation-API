"""Deterministic blind-priority review selection without owner-answer leakage."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tools.data_v2.targeted_blind_review import (
    _diverse_selection,
    build_blind_sample,
    select_review_ids,
)

SECRET = b"private-toy-review-key-with-24-bytes"


def _source(identifier: str, family: str, target: str) -> dict[str, Any]:
    return {
        "example_id": identifier, "family_id": family, "source": "synthetic",
        "platform_hint": "minecraft", "channel_profile": "minecraft_private",
        "target_index": 0, "messages": [
            {"speaker": "A", "offset_ms": 0, "text": target},
            {"speaker": "B", "offset_ms": 10, "text": "post-target hidden"},
        ],
        "label": "SAFE", "action": "ALLOW",
    }


def _queue(identifier: str, tier: str) -> dict[str, object]:
    return {
        "example_id": identifier, "triage_priority": tier,
        "source_file": "data/synthetic/" + identifier[:3] + "-fixture.jsonl",
        "source_sha256": "toyhash", "source_line": int(identifier[4:]),
        "candidate_action": "ALLOW", "candidate_semantic_label": "SAFE",
        "triage_flags": ["hidden-label"], "training_eligible": False,
    }


def _fixture() -> tuple[list[dict[str, Any]], list[dict[str, object]]]:
    rows: list[dict[str, Any]] = []
    queue: list[dict[str, object]] = []
    tiers = [
        "01_policy_conflict_candidate",
        "02_high_impact_candidate",
        "03_stratified_audit_candidate",
    ]
    for batch in ("G10", "G11"):
        for position in range(1, 19):
            ident = f"{batch}-{position:04d}"
            rows.append(_source(ident, f"{batch}.family.{position // 3}",
                                f"target {position}"))
            queue.append(_queue(ident, tiers[(position - 1) // 6]))
    return rows, queue


def test_batch_stratification_quotas_and_repeatability() -> None:
    rows, queue = _fixture()
    mapping = {row["example_id"]: row for row in rows}
    first, summary = select_review_ids(queue, mapping, set(), SECRET)
    second, _ = select_review_ids(queue, mapping, set(), SECRET)
    assert first == second
    assert len(first) == 12  # Two batches x (3 + 2 + 1)
    assert summary["selected"] == 12
    assert summary["selected_by_priority"] == {
        "01_policy_conflict_candidate": 6,
        "02_high_impact_candidate": 4,
        "03_stratified_audit_candidate": 2,
    }
    assert summary["training_eligible"] is False


def test_already_reviewed_actions_are_not_resampled() -> None:
    rows, queue = _fixture()
    mapping = {row["example_id"]: row for row in rows}
    excluded = {"G10-0001", "G10-0002", "G11-0001"}
    selected, summary = select_review_ids(queue, mapping, excluded, SECRET)
    assert not excluded.intersection(selected)
    assert summary["previously_owner_action_reviewed_excluded"] == 3


def test_review_packets_hide_source_answer_and_future_messages() -> None:
    rows, queue = _fixture()
    packets, crosswalk, summary = build_blind_sample(rows, queue, set(), SECRET)
    assert len(packets) == len(crosswalk) == summary["selected"]
    assert len({p["packet_id"] for p in packets}) == len(packets)
    for packet in packets:
        assert set(packet) == {
            "packet_id", "platform_hint", "channel_profile",
            "messages", "target_index",
        }
        assert packet["target_index"] == 0
        assert len(packet["messages"]) == 1
        assert "post-target hidden" not in repr(packet)
        assert all(k not in repr(packet) for k in ("candidate_action", "SAFE", "G10-"))
    assert all("selected_priority_tier" in x for x in crosswalk)
    assert all("candidate_action" not in x for x in crosswalk)


def test_distinct_family_first_then_quota_fill() -> None:
    rows, _ = _fixture()
    mapping = {row["example_id"]: row for row in rows}
    ordered = ["G10-0001", "G10-0002", "G10-0003", "G10-0004"]
    result = _diverse_selection(ordered, mapping, SECRET, "test", 3)
    assert len(result) == 3
    assert len(set(result)) == 3
    assert len({mapping[ident]["family_id"] for ident in result}) >= 2


def test_duplicate_or_unknown_candidates_fail_closed() -> None:
    rows, queue = _fixture()
    mapping = {row["example_id"]: row for row in rows}
    with pytest.raises(ValueError, match="duplicate"):
        select_review_ids(queue + [deepcopy(queue[0])], mapping, set(), SECRET)
    queue[0]["triage_priority"] = "approved_gold"
    with pytest.raises(ValueError, match="unknown candidate"):
        select_review_ids(queue, mapping, set(), SECRET)


def test_bad_secret_and_unknown_reviewed_id_rejected() -> None:
    rows, queue = _fixture()
    mapping = {row["example_id"]: row for row in rows}
    with pytest.raises(ValueError, match="invalid review secret"):
        select_review_ids(queue, mapping, set(), b"short")
    with pytest.raises(ValueError, match="invalid review secret"):
        select_review_ids(queue, mapping, {"G27-0999"}, SECRET)
