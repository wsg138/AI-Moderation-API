"""Candidate-only triage regressions: no truth promotion or future leakage."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.synthetic_family_audit import Group, find_groups, load_candidates
from tools.data_v2.triage_queue import build_queue, validate_source_order
from tools.dataset_qa.blind_review import _outside_checkout
from tools.dataset_qa.freshness import ROOT, batch_files

SOURCES = {
    "G10": "data/synthetic/G10-blackmail-extortion.jsonl",
    "G11": "data/synthetic/G11-doxxing.jsonl",
    "G20": "data/synthetic/G20-school-threats.jsonl",
    "G21": "data/synthetic/G21-multilingual.jsonl",
}


def _record(
    identifier: str, text: str = "please trade me diamonds",
    label: str = "SAFE", action: str = "ALLOW",
) -> dict[str, Any]:
    return {
        "example_id": identifier, "source": "synthetic", "family_id": "g10.test.001",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "target_index": 0, "messages": [
            {"speaker": "A", "offset_ms": 0, "text": text}
        ], "label": label, "action": action, "reason_codes": [],
        "strike": False, "containment": "NONE",
    }


def test_queue_preserves_actions_without_admitting_labels() -> None:
    rows = [
        _record("G10-0001"),
        _record("G10-0002", label="BLACKMAIL", action="BLOCK"),
    ]
    queue, summary = build_queue(rows, find_groups(rows), SOURCES)
    assert len(queue) == 2
    assert summary["verified_records"] == 0
    assert summary["owner_action_decisions_imported"] == 0
    assert summary["training_eligible"] is False
    assert {r["candidate_action"] for r in queue} == {"ALLOW", "BLOCK"}
    assert all(r["training_eligible"] is False for r in queue)
    assert all(r["label_status"] == "candidate_unverified" for r in queue)
    assert all(r["review_scope"] == "no_owner_action_imported" for r in queue)


def test_same_visible_input_conflicting_actions_are_priority_hypothesis() -> None:
    left = _record("G10-0001", "same message")
    right = deepcopy(left)
    right["example_id"] = "G11-0001"
    right["action"] = "BLOCK"
    right["label"] = "DOXXING"
    queue, summary = build_queue([left, right], find_groups([left, right]), SOURCES)
    assert summary["flag_counts"]["asof_exact_candidate_action_conflict"] == 2
    assert all(r["triage_priority"] == "01_policy_conflict_candidate" for r in queue)
    assert all(any(g["kind"] == "asof_exact" for g in r["overlap_evidence"]) for r in queue)


def test_same_target_in_different_context_does_not_imply_action_conflict() -> None:
    left = _record("G10-0001", "same target message for testing")
    right = _record("G11-0001", "same target message for testing", label="DOXXING", action="BLOCK")
    right["messages"].insert(0, {"speaker": "B", "offset_ms": -10, "text": "context"})
    right["target_index"] = 1
    queue, summary = build_queue([left, right], find_groups([left, right]), SOURCES)
    assert "asof_exact_candidate_action_conflict" not in summary["flag_counts"]
    assert all(any(g["kind"] == "target_exact" for g in r["overlap_evidence"]) for r in queue)


def test_future_irl_cue_is_never_a_feature() -> None:
    row = _record("G20-0001", "I will blow you up in pvp",
                  label="REAL_WORLD_THREAT", action="BLOCK")
    row["messages"].append({
        "speaker": "B", "offset_ms": 100, "text": "your address is real-world"
    })
    queue, _ = build_queue([row], [], SOURCES)
    assert "real_world_label_with_game_cue" in queue[0]["triage_flags"]
    assert "post_target_content_excluded" in queue[0]["triage_flags"]
    assert "your address" not in repr(queue[0])


def test_game_only_source_metadata_is_hypothesis_not_corrected_action() -> None:
    row = _record("G10-0001", "pay diamonds or base coords go public",
                  label="BLACKMAIL", action="BLOCK")
    row["reason_codes"] = ["minecraft_gameplay_explicit", "blackmail"]
    queue, summary = build_queue([row], [], SOURCES)
    assert summary["priority_counts"]["01_policy_conflict_candidate"] == 1
    assert "gameplay_blackmail_scope_review" in queue[0]["triage_flags"]
    assert queue[0]["candidate_action"] == "BLOCK"
    assert queue[0]["training_eligible"] is False


def test_unknown_group_and_duplicate_ids_fail_closed() -> None:
    row = _record("G10-0001")
    with pytest.raises(ValueError, match="duplicate"):
        build_queue([row, deepcopy(row)], [], SOURCES)
    with pytest.raises(ValueError, match="unknown group"):
        build_queue([row], [Group("asof_exact", ("G10-0001", "G11-9999"))], SOURCES)


def test_unexpected_source_or_line_rejected() -> None:
    with pytest.raises(ValueError, match="unknown or out-of-range"):
        build_queue([_record("G11-0501")], [], SOURCES)
    with pytest.raises(ValueError, match="unknown or out-of-range"):
        build_queue([_record("G15-0001")], [], SOURCES)


def test_source_lineage_check_detects_reordered_rows() -> None:
    rows = [_record("G10-0001"), _record("G10-0002")]
    validate_source_order(rows)
    with pytest.raises(ValueError, match="source record order"):
        validate_source_order(list(reversed(rows)))


def test_multilingual_and_self_disclosure_are_only_review_hypotheses() -> None:
    rows = [
        _record("G21-0001", "salut"),
        _record("G11-0001", "my phone number is 555-555-5555"),
    ]
    queue, summary = build_queue(rows, [], SOURCES)
    assert summary["priority_counts"]["01_policy_conflict_candidate"] == 2
    assert any("multilingual_policy_boundary" in r["triage_flags"] for r in queue)
    assert any("self_disclosed_contact_policy_boundary" in r["triage_flags"] for r in queue)
    assert all(r["training_eligible"] is False for r in queue)


def test_coordinator_queue_must_not_be_saved_in_checkout() -> None:
    with pytest.raises(ValueError, match="inside Git checkout"):
        _outside_checkout(Path("docs/data-v2/private-results.jsonl").absolute())


def test_full_9000_records_stay_unverified() -> None:
    if not batch_files(ROOT):
        pytest.skip("candidate sources not present on main")
    rows = load_candidates()
    validate_source_order(rows)
    files = {path.name[:3]: str(path) for path in batch_files(ROOT, require_complete=True)}
    queue, summary = build_queue(rows, find_groups(rows), files)
    assert len(queue) == 9000
    assert len({item["example_id"] for item in queue}) == 9000
    assert summary["records"] == 9000
    assert sum(summary["priority_counts"].values()) == 9000
    assert summary["training_eligible"] is False
    assert all(item["training_eligible"] is False for item in queue)


def test_triage_module_follows_complexity_limits() -> None:
    assert analyze(Path("tools/data_v2/triage_queue.py")) == []
