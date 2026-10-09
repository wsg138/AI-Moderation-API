"""Private action-only registry toy fixture regression tests."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.owner_action_registry import merge_action_only, validate_round4
from tools.data_v2.private_owner_actions import ROUND3_COMMIT


def fixture() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, tuple[str, str]]]:
    records: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}
    for number in range(1, 37):
        identifier = f"G10-{number:04d}"
        sources[identifier] = {
            "example_id": identifier, "label": "SAFE", "action": "ALLOW",
            "platform_hint": "minecraft", "channel_profile": "minecraft_public",
            "target_index": 0,
            "messages": [{"speaker": "A", "offset_ms": 0, "text": "toy text"}],
        }
        records.append({
            "question": f"Q{number:02d}", "opaque_id": f"R-{number:024x}",
            "source": {
                "repository": "wsg138/AI-Moderation-API", "commit": ROUND3_COMMIT,
                "path": "data/synthetic/G10-toy.jsonl", "blob_sha": "toy",
                "example_id": identifier, "jsonl_line": number,
            },
            "owner_review": {
                "reviewer": "toy", "review_round": 4, "scope": "action_only",
                "action": "ALLOW", "optional_explanation": None,
            },
            "source_candidate": {
                "action_for_comparison_only": "ALLOW",
                "semantic_label_for_comparison_only": "SAFE",
                "agrees_on_action": True,
            },
            "review_packet": {
                "channel": "Minecraft Public", "visible_messages": 1,
                "target_text_sha256": hashlib.sha256(b"toy text").hexdigest(),
            },
            "field_status": {
                "message_action": "owner_reviewed", "semantic_label": "unreviewed",
                "priority": "unreviewed", "strike": "unreviewed", "mute": "unreviewed",
                "support_flow": "unreviewed", "containment": "unreviewed",
            },
            "triage_flags": [], "training_eligible": False,
        })
    ledger = {
        "schema_version": "enthusia_round4_owner_action_v1",
        "privacy": "private_coordinator_only", "source_commit": ROUND3_COMMIT,
        "original_crosswalk_file_available_at_reconciliation": False,
        "mapping_reconstruction": "toy mapping", "review_round": 4,
        "reviewer": "toy", "case_count": 36,
        "training_eligible_cases": 0, "records": records,
    }
    return ledger, sources, {"G10": ("data/synthetic/G10-toy.jsonl", "toy")}


def test_all_36_round4_actions_are_private_and_unadmitted() -> None:
    ledger, rows, files = fixture()
    actions, summary = validate_round4(ledger, rows, files)
    assert len(actions) == 36
    assert summary["training_eligible"] is False
    assert summary["crosswalk_hmac_verified"] is False
    assert all(item["semantic_and_other_fields"] == "not_adjudicated" for item in actions)


def test_action_change_does_not_modify_synthetic_candidate() -> None:
    ledger, rows, files = fixture()
    ledger["records"][0]["owner_review"]["action"] = "BLOCK"
    ledger["records"][0]["source_candidate"]["agrees_on_action"] = False
    actions, summary = validate_round4(ledger, rows, files)
    assert summary["different_from_synthetic_candidate"] == 1
    assert actions[0]["owner_action"] == "BLOCK"
    assert rows["G10-0001"]["action"] == "ALLOW"


@pytest.mark.parametrize("key,value", [
    ("blob_sha", "changed"), ("jsonl_line", 2), ("path", "changed"),
])
def test_source_provenance_drift_fails(key: str, value: object) -> None:
    ledger, rows, files = fixture()
    ledger["records"][0]["source"][key] = value
    with pytest.raises(ValueError):
        validate_round4(ledger, rows, files)


def test_target_text_drift_and_invented_review_fields_fail() -> None:
    ledger, rows, files = fixture()
    ledger["records"][0]["review_packet"]["target_text_sha256"] = "wrong"
    with pytest.raises(ValueError, match="target text"):
        validate_round4(ledger, rows, files)
    ledger, rows, files = fixture()
    ledger["records"][0]["field_status"]["semantic_label"] = "approved"
    with pytest.raises(ValueError, match="invented policy annotation"):
        validate_round4(ledger, rows, files)


def test_duplicate_opaque_or_source_id_fails() -> None:
    ledger, rows, files = fixture()
    ledger["records"][1]["opaque_id"] = ledger["records"][0]["opaque_id"]
    with pytest.raises(ValueError, match="duplicate opaque"):
        validate_round4(ledger, rows, files)
    ledger, rows, files = fixture()
    ledger["records"][1]["source"] = deepcopy(ledger["records"][0]["source"])
    with pytest.raises(ValueError, match="duplicate source"):
        validate_round4(ledger, rows, files)


def test_combined_review_registry_never_invents_gold() -> None:
    ledger, rows, files = fixture()
    round4, _ = validate_round4(ledger, rows, files)
    combined, summary = merge_action_only(
        [{"example_id": "G11-0001", "training_eligible": False}], round4
    )
    assert summary["owner_action_only_records"] == 37
    assert summary["round4_count"] == 36
    assert summary["training_eligible"] is False
    with pytest.raises(ValueError, match="duplicate"):
        merge_action_only([round4[0]], round4)


def test_registry_module_within_complexity_budget() -> None:
    assert analyze(Path("tools/data_v2/owner_action_registry.py")) == []
