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


def test_all_passes_exactly_partition_341_source_flagged_cases() -> None:
    raw = _source()
    first, _ = build_proposals(raw)
    second, _ = build_second_pass(raw)
    third, _ = build_third_pass(raw)
    first_ids = {row["example_id"] for row in first}
    second_proposed = {row["example_id"] for row in second
                       if row["disposition"] == "provisional_game_only"}
    second_pending = {row["example_id"] for row in second
                      if row["disposition"] != "provisional_game_only"}
    third_ids = {row["example_id"] for row in third}
    assert len(first_ids) == 100
    assert len(second_proposed) == 14
    assert second_proposed <= first_ids
    assert len(second_pending) == 42
    assert len(third_ids) == 199
    assert not (first_ids & second_pending)
    assert not (first_ids & third_ids)
    assert not (second_pending & third_ids)
    source_candidates = {
        row["example_id"] for row in map(
            json.loads, raw.decode("utf-8").splitlines()
        ) if game_only_candidate(row)
    }
    assert source_candidates == first_ids | second_pending | third_ids
    assert len(source_candidates) == 341


def test_total_proposals_and_pending_remain_disjoint_and_unadmitted() -> None:
    raw = _source()
    first, _ = build_proposals(raw)
    second, _ = build_second_pass(raw)
    third, _ = build_third_pass(raw)
    proposed = ({row["example_id"] for row in first}
                | {row["example_id"] for row in third
                   if row["preliminary_disposition"] == "provisional_game_only"})
    pending = ({row["example_id"] for row in second
                if row["disposition"] != "provisional_game_only"}
               | {row["example_id"] for row in third
                  if row["preliminary_disposition"] == "pending_scope_review"})
    assert len(proposed) == 216
    assert len(pending) == 125
    assert not proposed & pending
    assert all(row["training_eligible"] is False for row in first)
    assert all(row["training_eligible"] is False for row in second)
    assert all(row["training_eligible"] is False for row in third)
    assert (ROOT / G10).read_bytes() == raw
