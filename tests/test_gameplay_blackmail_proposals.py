"""Source-locked provisional correction requests are never certified labels."""
from __future__ import annotations

import json

import pytest

from tools.dataset_qa.freshness import ROOT
from tools.dataset_qa.gameplay_blackmail_proposals import (
    PINNED_SOURCE_BLOB_SHA1,
    SUGGESTED,
    _curated_ids,
    build_proposals,
)
from tools.dataset_qa.owner_blackmail_audit import G10


def _source() -> bytes:
    path = ROOT / G10
    if not path.exists():
        pytest.skip("G10 synthetic candidate batch unavailable")
    return path.read_bytes()


def test_100_curated_cases_have_independent_review_gate() -> None:
    raw = _source()
    proposals, summary = build_proposals(raw)
    assert summary["provisional_game_only_proposals"] == 100
    assert len(proposals) == len(_curated_ids()) == 100
    assert len({r["example_id"] for r in proposals}) == 86
    assert all(r["status"] == "requires_independent_policy_adjudication"
               for r in proposals)
    assert all(r["training_eligible"] is False for r in proposals)
    assert summary["finalized"] == summary["training_admitted"] == 0


def test_proposals_anchor_every_case_to_same_source_and_visible_context() -> None:
    proposals, summary = build_proposals(_source())
    assert all(row["source_sha256"] == summary["source_sha256"]
               for row in proposals)
    assert all(len(str(row["visible_context_sha256"])) == 64
               for row in proposals)
    assert all(row["source_line"] == int(str(row["example_id"])[4:])
               for row in proposals)
    assert all(row["proposal"] == SUGGESTED for row in proposals)
    assert all("messages" not in row and "source_gold" not in row
               for row in proposals)
    assert summary["pinned_source_blob_sha1"] == PINNED_SOURCE_BLOB_SHA1


def test_declines_source_drift_even_when_rows_are_still_valid_json() -> None:
    raw = _source()
    changed = raw.replace(b"give me 64 diamonds", b"give me 63 diamonds", 1)
    assert changed != raw
    with pytest.raises(ValueError, match="source bytes changed"):
        build_proposals(changed)


def test_does_not_change_candidate_dataset_bytes() -> None:
    raw = _source()
    build_proposals(raw)
    assert (ROOT / G10).read_bytes() == raw


def test_distinct_game_only_proposals_keep_gameplay_and_irl_risks_separate() -> None:
    proposed, _ = build_proposals(_source())
    ids = {str(row["example_id"]) for row in proposed}
    assert {"G10-0008", "G10-0031", "G10-0219", "G10-0245"} <= ids
    assert {"G10-0043", "G10-0050", "G10-0079", "G10-0104",
            "G10-0138", "G10-0163", "G10-0281", "G10-0381"} <= ids
    assert {"G10-0047", "G10-0144", "G10-0161", "G10-0279",
            "G10-0311", "G10-0324", "G10-0380"} & ids == set()
    assert {"G10-0148", "G10-0195", "G10-0207", "G10-0321"} & ids == set()


def test_no_proposal_is_marked_approved_by_a_gold_label() -> None:
    proposals, _ = build_proposals(_source())
    assert all(row["review_origin"] == "coordinator_provisional_screen_only"
               for row in proposals)
    assert all(json.dumps(row).count("admitted") == 0 for row in proposals)


def test_explicit_irl_exposure_source_rows_cannot_get_gameplay_proposal() -> None:
    source_rows = [
        json.loads(line) for line in _source().decode("utf-8").splitlines()
    ]
    known_irl = {"G10-0107", "G10-0108", "G10-0110", "G10-0124"}
    assert known_irl <= {row["example_id"] for row in source_rows}
    assert all(
        "explicit_real_world_cue" in row["reason_codes"]
        for row in source_rows if row["example_id"] in known_irl
    )
    proposals, _ = build_proposals(_source())
    assert not ({row["example_id"] for row in proposals} & known_irl)


def test_14_new_game_only_leverage_cases_remain_provisional() -> None:
    proposals, summary = build_proposals(_source())
    assert summary["provisional_game_only_proposals"] == 100
    groups = summary["groups"]
    assert groups["minecraft_cheating_report_leverage"] == 9
    assert groups["minecraft_account_rule_leverage"] == 3
    assert groups["minecraft_griefing_or_base_location_leverage"] == 2
    assert all(item["status"] == "requires_independent_policy_adjudication"
               for item in proposals)
    assert summary["training_admitted"] == 0
