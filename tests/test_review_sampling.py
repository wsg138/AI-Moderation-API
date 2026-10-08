"""Tests for blinded, deterministic, candidate-only review cohort sampling."""
from __future__ import annotations

import json
from typing import Any

import pytest

from tools.dataset_qa.freshness import ROOT, batch_files
from tools.dataset_qa.review_sampling import build_sample, sample_review

KEY = b"test-sample-key-only-for-fixtures"


def _example(
    identifier: str, label: str = "SAFE", reason: str = "",
    text: str = "Ordinary chat message",
) -> dict[str, Any]:
    return {
        "example_id": identifier, "source": "synthetic",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "messages": [{"speaker": "A", "offset_ms": 0, "text": text}],
        "target_index": 0, "label": label, "action": "ALLOW",
        "review_priority": "NONE", "strike": False,
        "containment": "NONE", "support_flow": "NONE",
        "reason_codes": [reason] if reason else [],
        "notes": "hidden gold explanation",
    }


def test_review_selection_is_repeatable_and_order_independent() -> None:
    rows = [_example(f"G10-{i:04d}", "SAFE" if i % 2 else "DOXXING")
            for i in range(1, 31)]
    first = sample_review(rows, KEY, label_quota=3, channel_quota=2)
    second = sample_review(list(reversed(rows)), KEY, 3, 2)
    assert first == second
    assert len(first) >= 6
    assert all(reasons for reasons in first.values())


def test_high_risk_safe_flags_are_selected_for_review() -> None:
    rows = [_example(f"G10-{i:04d}") for i in range(1, 30)]
    rows[0]["messages"][0]["text"] = "kys"
    rows[1]["reason_codes"] = ["apparent_doxxing"]
    rows[2]["reason_codes"] = ["staff_targeted_abuse"]
    selected = sample_review(rows, KEY, 1, 1)
    assert "priority:safe_with_self_harm_directive" in selected["G10-0001"]
    assert "priority:safe_with_severe_reason_code" in selected["G10-0002"]
    assert "priority:staff_targeted_reason_label_disagreement" in selected["G10-0003"]


def test_cross_batch_duplicate_targets_stay_together() -> None:
    left = _example("G18-0001", text="identical and sufficiently long text")
    right = _example("G23-0001", text="identical and sufficiently long text")
    selected = sample_review([left, right], KEY, 1, 1)
    assert "cross_batch_family" in selected["G18-0001"]
    assert "cross_batch_family" in selected["G23-0001"]


def test_duplicate_source_ids_fail_closed() -> None:
    row = _example("G10-0001")
    with pytest.raises(ValueError, match="duplicate"):
        sample_review([row, row], KEY)


def test_short_sampling_key_and_invalid_quota_fail_closed() -> None:
    rows = [_example("G10-0001")]
    with pytest.raises(ValueError, match="invalid"):
        sample_review(rows, b"short")
    with pytest.raises(ValueError, match="invalid"):
        sample_review(rows, KEY, label_quota=0)


def _assert_reviewer_separation(packets: list[dict[str, object]]) -> None:
    assert all("example_id" not in packet for packet in packets)
    assert all("label" not in packet and "reason_codes" not in packet
               for packet in packets)
    assert all("selection_reasons" not in json.dumps(packet)
               for packet in packets)


def _assert_mapping_integrity(
    packets: list[dict[str, object]], mapping: list[dict[str, object]]
) -> None:
    assert all("source_sha256" in entry for entry in mapping)
    assert all("selection_reasons" in entry for entry in mapping)
    assert set(packet["packet_id"] for packet in packets) == {
        entry["packet_id"] for entry in mapping
    }


def test_all_available_synthetic_sources_are_sampled_blindly() -> None:
    if not batch_files(ROOT):
        pytest.skip("no G10-G27 candidate batches on main")
    packets, mapping = build_sample(ROOT, KEY)
    assert len(packets) == len(mapping)
    assert len(packets) >= 100
    assert len({packet["packet_id"] for packet in packets}) == len(packets)
    _assert_reviewer_separation(packets)
    _assert_mapping_integrity(packets, mapping)
