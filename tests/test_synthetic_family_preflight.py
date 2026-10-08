"""Candidate-only grouped split checks; never admit unreviewed source labels."""
from __future__ import annotations

from typing import Any

import pytest

from tools.data_v2.synthetic_family_audit import SOURCE_COMMIT, Group
from tools.data_v2.synthetic_family_preflight import (
    check,
    conflict_summary,
    validate_proposal,
)


def _proposal(mapping: dict[str, str]) -> dict[str, object]:
    return {
        "status": "candidate", "source_commit": SOURCE_COMMIT,
        "assignments": mapping,
    }


def _row(identifier: str) -> dict[str, Any]:
    return {
        "example_id": identifier, "source": "synthetic", "family_id": "g10.a.001",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "target_index": 0, "messages": [
            {"speaker": "A", "offset_ms": 0, "text": "Please protect my base coordinates tonight"}
        ],
    }


def test_exact_and_family_links_block_candidate_partition() -> None:
    rows = [_row("G10-0001"), _row("G25-0001")]
    result = check(rows, _proposal({
        "G10-0001": "candidate_a", "G25-0001": "candidate_b",
    }))
    assert result["status"] == "blocked"
    assert result["training_eligible"] is False
    assert result["cross_partition_evidence_groups"]["asof_exact"] == 1
    assert result["cross_partition_evidence_groups"]["target_exact"] == 1
    assert result["cross_partition_evidence_groups"]["family_id"] == 1


def test_family_stem_and_near_links_warn_before_split() -> None:
    groups = [
        Group("family_stem_candidate", ("G10-0001", "G10-0002")),
        Group("near_target_candidate", ("G10-0001", "G10-0002")),
    ]
    counts = conflict_summary(groups, {
        "G10-0001": "candidate_a", "G10-0002": "candidate_b",
    })
    assert counts["family_stem_candidate"] == 1
    assert counts["near_target_candidate"] == 1


@pytest.mark.parametrize("mutation", [
    {"status": "approved_training"},
    {"source_commit": "different"},
    {"assignments": {"G10-0001": "train", "G10-0002": "test"}},
    {"assignments": {"G10-0001": "candidate_a"}},
    {"assignments": {"G10-0001": "candidate_a", "G10-0002": "candidate_a"}},
    {"extra": "unsafe"},
])
def test_invalid_proposals_fail_closed(mutation: dict[str, object]) -> None:
    manifest = _proposal({
        "G10-0001": "candidate_a", "G10-0002": "candidate_b",
    })
    manifest.update(mutation)
    with pytest.raises(ValueError):
        validate_proposal(manifest, {"G10-0001", "G10-0002"})


def test_duplicate_source_ids_fail_closed() -> None:
    row = _row("G10-0001")
    with pytest.raises(ValueError, match="duplicate"):
        check([row, row], _proposal({"G10-0001": "candidate_a"}))


def test_no_detected_overlap_never_means_training_ready() -> None:
    first, second = _row("G10-0001"), _row("G25-0001")
    second["family_id"] = "g25.other.001"
    second["messages"][0]["text"] = "Entirely different benign conversation"
    result = check([first, second], _proposal({
        "G10-0001": "candidate_a", "G25-0001": "candidate_b",
    }))
    assert result["status"] == "candidate_only_no_detected_overlap"
    assert result["training_eligible"] is False
