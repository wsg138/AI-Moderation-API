"""Privacy/provenance checks for owner action-only review import (toy fixtures only)."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tools.data_v2.private_owner_actions import (
    ROUND3_COMMIT,
    _git_blob_sha,
    validate_ledger,
)

FILE = "data/synthetic/G10-blackmail-extortion.jsonl"
BLOB = "abc123syntheticblob"


def _row(identifier: str) -> dict[str, Any]:
    return {"example_id": identifier, "label": "SAFE", "action": "ALLOW"}


def _fixture() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, tuple[str, str]]]:
    records: list[dict[str, Any]] = []
    source_rows: dict[str, dict[str, Any]] = {}
    for number in range(1, 51):
        ident = f"G10-{number:04d}"
        source_rows[ident] = _row(ident)
        records.append({
            "question": f"Q{number:02d}",
            "opaque_id": "R-" + f"{number:024x}",
            "source": {
                "repository": "wsg138/AI-Moderation-API",
                "git_commit": ROUND3_COMMIT, "path": FILE,
                "git_blob_sha": BLOB, "record_id": ident,
                "original_jsonl_line_number": number,
            },
            "decision": {
                "reviewer": "toy_owner", "review_round": 3, "policy_version": "v1",
                "authority": "owner_authoritative_action_only",
                "action": "ALLOW", "explanation": None,
            },
            "comparison": {
                "candidate_action": "ALLOW",
                "candidate_semantic_label_for_comparison_only": "SAFE",
                "action_agrees_with_candidate": True,
            },
            "review_flags": [], "training_eligible": False,
            "semantic_label_adjudicated": False,
            "other_policy_fields_adjudicated": False,
        })
    ledger = {
        "schema_version": "action_only_private_coordinator_v1",
        "private_coordinator_artifact": True, "privacy": "toy",
        "review_date": "2026-10-08", "reviewer": "toy_owner",
        "round": 3, "case_count": 50, "source_commit": ROUND3_COMMIT,
        "provenance": "toy", "methodology": "toy", "assessment": {},
        "training_eligible_cases": 0, "records": records,
    }
    return ledger, source_rows, {"G10": (FILE, BLOB)}


def test_all_fifty_toy_actions_import_without_training_admission() -> None:
    ledger, source, files = _fixture()
    corrections, summary = validate_ledger(ledger, source, files)
    assert len(corrections) == 50
    assert summary["imported_owner_action_only"] == 50
    assert summary["semantic_labels_adjudicated"] == 0
    assert summary["training_eligible"] is False
    assert all(row["training_eligible"] is False for row in corrections)
    assert all(row["semantic_and_other_fields"] == "not_adjudicated" for row in corrections)
    assert all("candidate_semantic_label" not in row for row in corrections)


def test_owner_action_can_disagree_with_candidate_without_rewriting_it() -> None:
    ledger, rows, files = _fixture()
    record = ledger["records"][0]
    record["decision"]["action"] = "REVIEW"
    record["comparison"]["action_agrees_with_candidate"] = False
    corrections, summary = validate_ledger(ledger, rows, files)
    assert summary["different_from_synthetic_candidate"] == 1
    assert corrections[0]["owner_action"] == "REVIEW"
    assert corrections[0]["candidate_action_for_comparison"] == "ALLOW"
    assert rows["G10-0001"]["action"] == "ALLOW"


@pytest.mark.parametrize("change", ["source_line", "source_blob", "action", "semantic"])
def test_source_or_comparison_tampering_rejected(change: str) -> None:
    ledger, rows, files = _fixture()
    record = ledger["records"][0]
    if change == "source_line":
        record["source"]["original_jsonl_line_number"] = 2
    elif change == "source_blob":
        record["source"]["git_blob_sha"] = "wrong"
    elif change == "action":
        record["comparison"]["candidate_action"] = "BLOCK"
    else:
        record["comparison"]["candidate_semantic_label_for_comparison_only"] = "BLACKMAIL"
    with pytest.raises(ValueError, match="source provenance|candidate comparison"):
        validate_ledger(ledger, rows, files)


def test_invented_semantic_adjudication_or_training_admission_rejected() -> None:
    ledger, rows, files = _fixture()
    ledger["records"][0]["semantic_label_adjudicated"] = True
    with pytest.raises(ValueError, match="invented annotation"):
        validate_ledger(ledger, rows, files)
    ledger, rows, files = _fixture()
    ledger["records"][0]["training_eligible"] = True
    with pytest.raises(ValueError, match="admission"):
        validate_ledger(ledger, rows, files)


def test_duplicate_source_or_opaque_rejected() -> None:
    ledger, rows, files = _fixture()
    ledger["records"][1]["source"] = deepcopy(ledger["records"][0]["source"])
    with pytest.raises(ValueError, match="duplicate reviewed"):
        validate_ledger(ledger, rows, files)
    ledger, rows, files = _fixture()
    ledger["records"][1]["opaque_id"] = ledger["records"][0]["opaque_id"]
    with pytest.raises(ValueError, match="duplicate reviewed"):
        validate_ledger(ledger, rows, files)


def test_wrong_commit_or_missing_action_rejected() -> None:
    ledger, rows, files = _fixture()
    ledger["source_commit"] = "deadbeef"
    with pytest.raises(ValueError, match="source commit"):
        validate_ledger(ledger, rows, files)
    ledger, rows, files = _fixture()
    ledger["records"][2]["decision"]["action"] = "BAN"
    with pytest.raises(ValueError, match="action scope"):
        validate_ledger(ledger, rows, files)


def test_git_blob_digest_uses_git_prefix() -> None:
    import hashlib

    raw = b"example\n"
    expected = hashlib.sha1(b"blob 8\0" + raw).hexdigest()
    assert _git_blob_sha(raw) == expected
