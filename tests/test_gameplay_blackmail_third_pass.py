"""The G10 third pass preserves owner-rule and training-admission gates."""
from __future__ import annotations

import json

import pytest

from tools.dataset_qa.freshness import ROOT
from tools.dataset_qa.gameplay_blackmail_third_pass import (
    THIRD_PASS_GROUPS,
    _third_pass_ids,
    build_third_pass,
)
from tools.dataset_qa.owner_blackmail_audit import G10


def _source() -> bytes:
    path = ROOT / G10
    if not path.is_file():
        pytest.skip("G10 public-synthetic source is unavailable")
    return path.read_bytes()


def test_199_case_coverage_and_disjoint_116_83_split() -> None:
    records, summary = build_third_pass(_source())
    assert summary["third_pass_count"] == len(records) == 199
    assert summary["dispositions"] == {
        "pending_scope_review": 83,
        "provisional_game_only": 116,
    }
    assert summary["total_provisional_all_passes"] == 216
    assert summary["pending_all_passes"] == 125
    assert len({record["example_id"] for record in records}) == 199


def test_group_accounting_and_known_case_dispositions() -> None:
    records, _ = build_third_pass(_source())
    assert {key: len(values) for key, values in THIRD_PASS_GROUPS.items()} == {
        "minecraft_cheating_report_leverage": 40,
        "minecraft_guild_plot_and_alt_leverage": 17,
        "minecraft_tnt_build_and_grief_leverage": 20,
        "minecraft_alt_account_report_leverage": 19,
        "minecraft_trade_scam_report_leverage": 19,
        "minecraft_guild_election_leverage": 1,
    }
    proposals = {row["example_id"] for row in records
                 if row["preliminary_disposition"] == "provisional_game_only"}
    assert proposals == set(_third_pass_ids())
    assert {"G10-0040", "G10-0254", "G10-0297", "G10-0328"} <= proposals
    assert not {"G10-0039", "G10-0151", "G10-0276", "G10-0360"} & proposals


def test_no_prior_stage_or_real_world_source_ids_are_reincluded() -> None:
    records, _ = build_third_pass(_source())
    ids = {row["example_id"] for row in records}
    assert {"G10-0008", "G10-0043", "G10-0219", "G10-0381"} & ids == set()
    assert {"G10-0107", "G10-0195", "G10-0321"} & ids == set()


def test_all_records_keep_human_review_and_training_guards() -> None:
    records, summary = build_third_pass(_source())
    assert summary["training_admitted"] == summary["independent_approvals"] == 0
    assert all(row["independent_review"] == "not_received" for row in records)
    assert all(row["adjudicated"] is False for row in records)
    assert all(row["training_eligible"] is False for row in records)
    assert all(row["review_origin"] == "coordinator_preliminary_screen_only"
               for row in records)
    assert all("messages" not in row and "gold_label" not in row
               for row in records)


def test_source_line_visible_context_hash_and_optional_proposal() -> None:
    records, summary = build_third_pass(_source())
    assert all(row["source_sha256"] == summary["source_sha256"]
               for row in records)
    assert all(row["source_line"] == int(str(row["example_id"])[4:])
               for row in records)
    assert all(len(str(row["visible_context_sha256"])) == 64
               for row in records)
    assert all(
        ("conditional_proposal" in row)
        == (row["preliminary_disposition"] == "provisional_game_only")
        for row in records
    )
    assert all(row["conditional_proposal"]["action"] == "ALLOW"
               for row in records if "conditional_proposal" in row)


def test_byte_drift_fails_closed_and_never_mutates_original() -> None:
    raw = _source()
    build_third_pass(raw)
    assert _source() == raw
    modified = raw.replace(b"give me 64 diamonds", b"give me 63 diamonds", 1)
    assert modified != raw
    with pytest.raises(ValueError, match="source bytes differ"):
        build_third_pass(modified)


def test_metadata_cannot_override_bounded_source_inspection() -> None:
    records, _ = build_third_pass(_source())
    data = "\n".join(json.dumps(row) for row in records)
    assert '"training_eligible": true' not in data
    assert '"adjudicated": true' not in data
    assert '"source_gold"' not in data
