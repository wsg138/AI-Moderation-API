"""Toy-only regressions for policy reconciliation without label admission."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.policy_conflict_quarantine import (
    make_reconciliation,
    policy_tracks,
)
from tools.data_v2.synthetic_family_audit import find_groups, load_candidates
from tools.data_v2.triage_queue import build_queue, validate_source_order
from tools.dataset_qa.freshness import ROOT, batch_files


def _candidate(
    identifier: str, label: str = "SAFE", action: str = "ALLOW",
    target: str = "general chat message",
) -> dict[str, Any]:
    return {
        "example_id": identifier, "source": "synthetic",
        "label": label, "action": action, "family_id": "toy.one.001",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "target_index": 0,
        "messages": [{"speaker": "A", "offset_ms": 0, "text": target}],
    }


def _triage(row: dict[str, Any]) -> dict[str, object]:
    return {
        "example_id": row["example_id"],
        "source_file": "data/synthetic/G10-toy.jsonl",
        "source_sha256": "toy_source_digest",
        "source_line": int(row["example_id"][4:]),
        "source_commit": "toy_commit",
    }


def _owner(identifier: str, action: str) -> dict[str, object]:
    return {
        "example_id": identifier,
        "owner_action": action,
        "owner_authority": "message_action_only",
        "semantic_and_other_fields": "not_adjudicated",
        "training_eligible": False,
    }


def test_safety_conflict_prioritized_without_approving_gold() -> None:
    sample = _candidate("G10-0001", "DOXXING", "BLOCK", "find their contact info")
    queue, summary = make_reconciliation([sample], [_triage(sample)], [
        _owner("G10-0001", "ALLOW"),
    ])
    assert queue[0]["priority"] == "01_safety_policy_conflict_review"
    assert queue[0]["owner_action_if_reviewed"] == "ALLOW"
    assert queue[0]["full_outcome_status"] == "quarantined_unverified"
    assert queue[0]["training_eligible"] is False
    assert summary["owner_candidate_disagreements"] == 1
    assert summary["semantic_fields_adjudicated"] == 0
    assert sample["action"] == "BLOCK"


def test_owner_disagreement_is_not_automatic_corrected_training_label() -> None:
    sample = _candidate("G10-0001", "SAFE", "ALLOW")
    queue, summary = make_reconciliation([sample], [_triage(sample)], [
        _owner("G10-0001", "BLOCK"),
    ])
    assert queue[0]["priority"] == "02_owner_vs_candidate_action_review"
    assert summary["training_eligible"] is False
    assert queue[0]["candidate_action_for_comparison_only"] == "ALLOW"


def test_language_bucket_is_source_heuristic_not_language_classifier() -> None:
    english = _candidate("G21-0001", target="Hi, how is your day?")
    spanish = _candidate("G15-0001", target="hola que tal")
    assert "language_enforcement" in policy_tracks(english)
    assert "language_enforcement" not in policy_tracks(spanish)
    assert "language_enforcement" in policy_tracks(
        _candidate("G21-0002", target="bonjour")
    )


def test_english_policy_scope_recorded_without_automatic_classification() -> None:
    """A G21 source hint cannot establish a language violation or gold label."""
    sample = _candidate("G21-0001", "SAFE", "ALLOW", "Hi, how is your day?")
    queue, summary = make_reconciliation([sample], [_triage(sample)], [])
    assert queue[0]["policy_track_state"]["language_enforcement"] == (
        "owner_rule_recorded_detector_not_validated"
    )
    assert queue[0]["priority"] == "04_contextual_policy_application_review"
    assert queue[0]["training_eligible"] is False
    assert queue[0]["full_outcome_status"] == "quarantined_unverified"
    assert summary["semantic_fields_adjudicated"] == 0


def test_versioned_english_rule_preserves_exceptions_and_no_sanction_grant() -> None:
    rule_file = Path("policy/english-primary-message-action-v1.json")
    rule = json.loads(rule_file.read_text(encoding="utf-8"))
    assert rule["rule_id"] == "english_primary_2026_10_08"
    assert rule["runtime_enabled"] is False
    assert rule["gold_training_eligible"] is False
    choices = rule["message_action_by_verified_assessment"]
    assert choices["primarily_non_english"] == "BLOCK"
    assert choices["primarily_english"] == "ALLOW"
    assert choices["occasional_foreign_words_or_short_greetings"] == "ALLOW"
    assert choices["player_names_and_recognized_game_terms"] == "ALLOW"
    assert choices["unreliably_assessed_or_ambiguous"] == "UNDECIDED"
    consequences = rule["language_only_consequences"]
    assert consequences["message_action"] == "BLOCK"
    assert consequences["strike"] == "NONE"
    assert consequences["mute"] == "NONE"
    assert consequences["staff_escalation"] == "NONE"
    assert consequences["repeat_violation_escalation"] == "NONE"
    assert consequences["other_punishment"] == "NONE"
    assert rule["unapproved_fields"] == {"semantic_harm_category": "do_not_infer"}
    coverage = rule["applicable_channel_config"]
    assert coverage["status"] == "owner_approved"
    assert coverage["rule_application"] == "all_moderated_surfaces_including_private_messages"
    assert set(coverage["includes"]) == {
        "minecraft_public", "minecraft_private",
        "minecraft_other_configured_rosechat_channels",
        "discord_general", "discord_gaming",
    }
    assert set(coverage["excludes_existing_policy_exemptions"]) == {
        "discord_ticket", "discord_staff_only",
        "discord_other_explicitly_exempt",
    }
    assert "discord_bot_direct_messages" in coverage["undefined_not_authorized"]
    assert not set(coverage["includes"]) & set(coverage["excludes_existing_policy_exemptions"])
    assert coverage["mirror_handling"] == "one_canonical_event_do_not_double_count"
    for example in rule["illustrative_exemplars_not_training_gold"]:
        assert choices[example["assessment"]] == example["action"]


def test_self_disclosure_scope_is_not_equated_to_doxxing() -> None:
    row = _candidate("G10-0001", target="my phone number is a made-up example")
    assert "self_published_contact" in policy_tracks(row)
    queue, _ = make_reconciliation([row], [_triage(row)], [])
    assert queue[0]["priority"] == "03_unresolved_policy_boundary"
    assert queue[0]["candidate_semantic_for_routing_only"] == "SAFE"


def test_first_person_support_is_separate_from_enforcement() -> None:
    row = _candidate("G24-0001", "SELF_HARM_INTENT", "ALLOW", "I feel hopeless")
    queue, _ = make_reconciliation([row], [_triage(row)], [
        _owner("G24-0001", "ALLOW"),
    ])
    assert "self_harm_safety_flow" in queue[0]["policy_review_tracks"]
    assert queue[0]["priority"] == "04_contextual_policy_application_review"
    assert queue[0]["training_eligible"] is False


def test_post_target_messages_do_not_trigger_contact_policy_flag() -> None:
    row = _candidate("G10-0001")
    row["messages"].append({
        "speaker": "B", "offset_ms": 10, "text": "my phone number is 555"
    })
    assert policy_tracks(row) == []


def test_unrecognized_or_duplicate_owner_decision_rejected() -> None:
    row = _candidate("G10-0001")
    with pytest.raises(ValueError, match="unknown owner case"):
        make_reconciliation([row], [_triage(row)], [_owner("G11-0002", "BLOCK")])
    with pytest.raises(ValueError, match="duplicate owner action"):
        make_reconciliation([row], [_triage(row)], [
            _owner("G10-0001", "ALLOW"), _owner("G10-0001", "BLOCK"),
        ])


def test_mutated_training_or_semantic_authority_fails_closed() -> None:
    row = _candidate("G10-0001")
    correction = _owner("G10-0001", "ALLOW")
    correction["training_eligible"] = True
    with pytest.raises(ValueError, match="training admission"):
        make_reconciliation([row], [_triage(row)], [correction])
    correction = _owner("G10-0001", "ALLOW")
    correction["semantic_and_other_fields"] = "approved_gold"
    with pytest.raises(ValueError, match="semantic"):
        make_reconciliation([row], [_triage(row)], [correction])


def test_bad_triage_frame_rejected() -> None:
    row = _candidate("G10-0001")
    with pytest.raises(ValueError, match="duplicate synthetic"):
        make_reconciliation([row, deepcopy(row)], [_triage(row)], [])
    with pytest.raises(ValueError, match="triage source IDs"):
        make_reconciliation([row], [_triage(_candidate("G10-0002"))], [])


def test_all_9000_sources_quarantined_not_training_ready() -> None:
    if not batch_files(ROOT):
        pytest.skip("G10–G27 public candidate sources not present on main")
    rows = load_candidates()
    validate_source_order(rows)
    files = {p.name[:3]: str(p) for p in batch_files(ROOT, require_complete=True)}
    queue, _ = build_queue(rows, find_groups(rows), files)
    output, summary = make_reconciliation(rows, queue, [])
    assert len(output) == 9000
    assert summary["records"] == 9000
    assert summary["owner_action_only_cases"] == 0
    assert sum(summary["priority_counts"].values()) == 9000
    assert all(row["training_eligible"] is False for row in output)


def test_policy_quarantine_complexity_limits() -> None:
    assert analyze(Path("tools/data_v2/policy_conflict_quarantine.py")) == []
