"""All G10 review passes must form exactly one complete source-locked queue."""
from __future__ import annotations

import json
import pytest

from tools.dataset_qa.freshness import ROOT
from tools.dataset_qa.gameplay_blackmail_proposals import build_proposals
from tools.dataset_qa.gameplay_blackmail_second_pass import build_second_pass
from tools.dataset_qa.gameplay_blackmail_third_pass import build_third_pass
from tools.dataset_qa.owner_blackmail_audit import G10, game_only_candidate


def _source() -> bytes:
    path = ROOT / G10
    if not path.is_file():
        pytest.skip("G10 public synthetic source unavailable")
    return path.read_bytes()


def _source_candidates(raw: bytes) -> set[str]:
    return {
        row["example_id"] for row in map(
            json.loads, raw.decode("utf-8").splitlines()
        ) if game_only_candidate(row)
    }


def _matching_ids(
    rows: list[dict[str, object]], field: str, expected: str,
) -> set[str]:
    return {str(row["example_id"]) for row in rows if row[field] == expected}


def _unadmitted(*groups: list[dict[str, object]]) -> bool:
    return all(row["training_eligible"] is False for group in groups
               for row in group)


def test_all_passes_exactly_partition_341_source_flagged_cases() -> None:
    raw = _source()
    first, _ = build_proposals(raw)
    second, _ = build_second_pass(raw)
    third, _ = build_third_pass(raw)
    first_ids = {str(row["example_id"]) for row in first}
    second_proposed = _matching_ids(
        second, "disposition", "provisional_game_only"
    )
    second_pending = {str(row["example_id"]) for row in second} - second_proposed
    third_ids = {str(row["example_id"]) for row in third}
    assert len(first_ids) == 100
    assert len(second_proposed) == 14
    assert second_proposed <= first_ids
    assert len(second_pending) == 42
    assert len(third_ids) == 199
    assert not (first_ids & second_pending)
    assert not (first_ids & third_ids)
    assert not (second_pending & third_ids)
    source_ids = _source_candidates(raw)
    assert source_ids == first_ids | second_pending | third_ids
    assert len(source_ids) == 341


def test_total_proposals_and_pending_remain_disjoint_and_unadmitted() -> None:
    raw = _source()
    first, _ = build_proposals(raw)
    second, _ = build_second_pass(raw)
    third, _ = build_third_pass(raw)
    proposed = ({str(row["example_id"]) for row in first}
                | _matching_ids(
                    third, "preliminary_disposition", "provisional_game_only"
                ))
    pending = (_matching_ids(second, "disposition", "pending_unclear")
               | _matching_ids(second, "disposition", "pending_mixed_or_irl")
               | _matching_ids(
                    third, "preliminary_disposition", "pending_scope_review"
                ))
    assert len(proposed) == 216
    assert len(pending) == 125
    assert not proposed & pending
    assert _unadmitted(first, second, third)
    assert (ROOT / G10).read_bytes() == raw
