"""Second-pass coordinator screening is complete but never independent truth."""
from __future__ import annotations

import json

import pytest

from tools.dataset_qa.freshness import ROOT
from tools.dataset_qa.gameplay_blackmail_proposals import (
    _curated_ids,
)
from tools.dataset_qa.gameplay_blackmail_second_pass import (
    _second_pass_groups,
    build_second_pass,
)
from tools.dataset_qa.owner_blackmail_audit import G10


def _source() -> bytes:
    path = ROOT / G10
    if not path.is_file():
        pytest.skip("G10 public-synthetic candidate batch is unavailable")
    return path.read_bytes()


def test_all_original_56_second_pass_cases_have_exact_dispositions() -> None:
    records, summary = build_second_pass(_source())
    assert summary["second_pass_total"] == len(records) == 56
    assert summary["disposition_counts"] == {
        "pending_mixed_or_irl": 35,
        "pending_unclear": 7,
        "provisional_game_only": 14,
    }
    assert {row["example_id"] for row in records} == set(_second_pass_groups())


def test_14_newly_proposed_cases_match_full_proposal_set() -> None:
    records, _ = build_second_pass(_source())
    proposed = {row["example_id"] for row in records
                if row["disposition"] == "provisional_game_only"}
    assert len(proposed) == 14
    assert proposed <= set(_curated_ids())
    assert len(_curated_ids()) == 100


def test_original_86_proposals_are_not_duplicate_second_pass_cases() -> None:
    records, _ = build_second_pass(_source())
    original = {
        "G10-0008", "G10-0135", "G10-0219", "G10-0245",
        "G10-0389", "G10-0495",
    }
    assert not ({row["example_id"] for row in records} & original)


def test_realworld_stakes_never_receive_new_game_only_proposals() -> None:
    records, _ = build_second_pass(_source())
    index = {str(row["example_id"]): row for row in records}
    for case in ("G10-0136", "G10-0148", "G10-0195",
                 "G10-0207", "G10-0321", "G10-0355"):
        assert index[case]["disposition"] == "pending_mixed_or_irl"
        assert index[case]["training_eligible"] is False
    for case in ("G10-0047", "G10-0161", "G10-0380"):
        assert index[case]["disposition"] == "pending_unclear"


def test_source_line_context_integrity_and_no_gold_in_manifest() -> None:
    records, summary = build_second_pass(_source())
    assert all(row["source_sha256"] == summary["source_sha256"]
               for row in records)
    assert all(row["source_line"] == int(str(row["example_id"])[4:])
               for row in records)
    assert all(len(str(row["visible_context_sha256"])) == 64
               for row in records)
    assert all("messages" not in row and "source_label" not in row
               for row in records)
    assert all(row["independent_review"] == "not_received"
               for row in records)
    assert all(row["adjudicated"] is False for row in records)
    assert summary["approved_corrections"] == summary["training_admitted"] == 0


def test_source_bytes_are_unchanged_by_second_pass_builder() -> None:
    raw = _source()
    records, _ = build_second_pass(raw)
    assert len(records) == 56
    assert raw == (ROOT / G10).read_bytes()


def test_source_drift_fails_closed_even_with_valid_json() -> None:
    raw = _source()
    changed = raw.replace(b"give me 64 diamonds", b"give me 63 diamonds", 1)
    assert changed != raw
    with pytest.raises(ValueError, match="source bytes changed"):
        build_second_pass(changed)


def test_no_training_eligible_field_can_be_inferred_from_original_gold() -> None:
    records, _ = build_second_pass(_source())
    payload = "\n".join(json.dumps(row) for row in records)
    assert '"training_eligible": true' not in payload
    assert all(row["review_origin"] == "coordinator_preliminary_screen_only"
               for row in records)
