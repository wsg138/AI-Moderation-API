"""Regression coverage for offline review confidentiality and input integrity."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.dataset_qa.blind_review import _write_jsonl, _write_review_outputs
from tools.dataset_qa.review_assignments import _check_packet, _write_assignment_outputs
from tools.dataset_qa.review_intake import _read_jsonl


@pytest.mark.parametrize("coordinator_relative", [
    "crosswalk.jsonl",
    "nested/crosswalk.jsonl",
])
def test_crosswalk_cannot_share_reviewer_tree(
    tmp_path: Path, coordinator_relative: str,
) -> None:
    reviewer = tmp_path / "reviewers" / "packets.jsonl"
    coordinator = reviewer.parent / coordinator_relative
    with pytest.raises(ValueError, match="outside reviewer"):
        _write_review_outputs(reviewer, [], coordinator, [])
    assert not reviewer.exists()
    assert not coordinator.exists()


def test_review_file_cannot_be_nested_under_coordinator_dir(
    tmp_path: Path,
) -> None:
    coordinator = tmp_path / "review" / "map.jsonl"
    reviewer = coordinator.parent / "reviewers" / "packets.jsonl"
    with pytest.raises(ValueError, match="outside reviewer"):
        _write_review_outputs(reviewer, [], coordinator, [])


def test_existing_coordinator_file_rolls_back_new_reviewer_file(
    tmp_path: Path,
) -> None:
    reviewer = tmp_path / "reviewers" / "packets.jsonl"
    coordinator = tmp_path / "private" / "crosswalk.jsonl"
    coordinator.parent.mkdir()
    coordinator.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(FileExistsError):
        _write_review_outputs(reviewer, [{"packet_id": "safe"}], coordinator, [])
    assert not reviewer.exists()
    assert coordinator.read_text(encoding="utf-8") == "do not overwrite"


def test_partial_jsonl_write_is_removed(tmp_path: Path) -> None:
    destination = tmp_path / "partial.jsonl"
    with pytest.raises(TypeError):
        _write_jsonl(destination, [{"a": 1}, {"bad": object()}])
    assert not destination.exists()


@pytest.mark.parametrize("payload", [
    '{"packet_id": "first", "packet_id": "second"}',
    '{"messages": [{"text": "a", "text": "b"}]}',
])
def test_reviewer_jsonl_rejects_ambiguous_duplicate_keys(
    tmp_path: Path, payload: str,
) -> None:
    destination = tmp_path / "packet.jsonl"
    destination.write_text(payload + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        _read_jsonl(destination)


def test_assignment_rejects_out_of_order_pretarget_offsets() -> None:
    packet: dict[str, object] = {
        "packet_id": "R-" + "a" * 24,
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_public",
        "target_index": 2,
        "messages": [
            {"speaker": "a", "offset_ms": 4, "text": "first"},
            {"speaker": "b", "offset_ms": 2, "text": "older"},
            {"speaker": "a", "offset_ms": 5, "text": "target"},
        ],
    }
    with pytest.raises(ValueError, match="chronological"):
        _check_packet(packet)


def test_failed_assignment_manifest_does_not_leave_reviewers_exposed(
    tmp_path: Path,
) -> None:
    reviewer_dir = tmp_path / "new-reviewer-files"
    manifest = tmp_path / "private" / "manifest.jsonl"
    manifest.parent.mkdir()
    manifest.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(FileExistsError):
        _write_assignment_outputs(
            reviewer_dir, manifest,
            {"reviewer01": [{"packet_id": "R-" + "a" * 24}],
             "reviewer02": [{"packet_id": "R-" + "b" * 24}]},
            [{"packet_id": "R-" + "a" * 24}],
        )
    assert not reviewer_dir.exists()
    assert manifest.read_text(encoding="utf-8") == "do not overwrite"
