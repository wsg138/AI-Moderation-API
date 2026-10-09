"""Validate action-only Round 4 private judgments against pinned source bytes.

This supports a *reconstructed* mapping: it does not claim an HMAC-authenticated
packet crosswalk or complete semantic/severity reviewer gold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from tools.dataset_qa.asof_input import serialize_as_of_target
from tools.dataset_qa.blind_review import _outside_checkout, _write_jsonl

from .private_owner_actions import (
    ACTIONS,
    REPO,
    ROUND3_COMMIT,
    _require,
    _source_index,
    read_private_ledger,
    validate_ledger,
)

ROUND4_FIELDS = {
    "schema_version", "privacy", "source_commit",
    "original_crosswalk_file_available_at_reconciliation",
    "mapping_reconstruction", "review_round", "reviewer",
    "case_count", "training_eligible_cases", "records",
}
ROW_FIELDS = {
    "question", "opaque_id", "source", "owner_review",
    "source_candidate", "review_packet", "field_status",
    "training_eligible", "triage_flags",
}
SOURCE_FIELDS = {"repository", "commit", "path", "blob_sha", "example_id", "jsonl_line"}
OWNER_FIELDS = {"reviewer", "review_round", "scope", "action", "optional_explanation"}
CANDIDATE_FIELDS = {
    "action_for_comparison_only", "semantic_label_for_comparison_only", "agrees_on_action",
}
PACKET_FIELDS = {"channel", "visible_messages", "target_text_sha256"}
STATUS_FIELDS = {
    "message_action", "semantic_label", "priority", "strike", "mute",
    "support_flow", "containment",
}
OPAQUE = re.compile(r"R-[0-9a-f]{24}$")


def _header(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    _require(set(ledger) == ROUND4_FIELDS, "unexpected Round 4 ledger schema")
    _require(ledger["schema_version"] == "enthusia_round4_owner_action_v1", "wrong schema")
    _require(ledger["privacy"] == "private_coordinator_only", "not a private ledger")
    _require(ledger["source_commit"] == ROUND3_COMMIT, "changed source commit")
    _require(ledger["original_crosswalk_file_available_at_reconciliation"] is False,
             "unexpected crosswalk reconstruction assertion")
    _require(isinstance(ledger["mapping_reconstruction"], str),
             "missing reconstruction provenance")
    _require(type(ledger["case_count"]) is int, "invalid case count")
    _require(ledger["case_count"] == 36, "Round 4 must have 36 cases")
    _require(type(ledger["review_round"]) is int, "invalid review round")
    _require(ledger["review_round"] == 4, "unexpected round")
    _require(ledger["training_eligible_cases"] == 0, "unapproved training admission")
    _require(isinstance(ledger["reviewer"], str) and bool(ledger["reviewer"]),
             "invalid reviewer alias")
    rows = ledger["records"]
    _require(isinstance(rows, list) and len(rows) == 36, "incomplete Round 4")
    return rows


def _row_structure(row: dict[str, Any], ledger: dict[str, Any], index: int) -> None:
    _require(isinstance(row, dict) and set(row) == ROW_FIELDS, "invalid Round 4 row")
    _require(row["question"] == f"Q{index:02d}", "review question order changed")
    _require(isinstance(row["opaque_id"], str), "malformed opaque packet ID")
    _require(bool(OPAQUE.fullmatch(row["opaque_id"])), "malformed opaque packet ID")
    _require(set(row["source"]) == SOURCE_FIELDS, "invalid source field scope")
    _require(set(row["owner_review"]) == OWNER_FIELDS, "invalid owner action scope")
    _require(set(row["source_candidate"]) == CANDIDATE_FIELDS, "invalid candidate scope")
    _require(set(row["review_packet"]) == PACKET_FIELDS, "invalid packet scope")
    _require(set(row["field_status"]) == STATUS_FIELDS, "invalid field-status scope")
    _require(row["training_eligible"] is False, "unapproved training admission")
    _require(isinstance(row["triage_flags"], list), "invalid coordinator flags")
    _require(all(isinstance(flag, str) for flag in row["triage_flags"]),
             "invalid coordinator flags")
    for field in STATUS_FIELDS - {"message_action"}:
        _require(row["field_status"][field] == "unreviewed", "invented policy annotation")
    _require(row["field_status"]["message_action"] == "owner_reviewed",
             "unreviewed message action")


def _owner_action(row: dict[str, Any], ledger: dict[str, Any]) -> None:
    owner = row["owner_review"]
    _require(owner["action"] in ACTIONS, "invalid owner action")
    _require(owner["scope"] == "action_only", "full-schema gold not authorized")
    _require(owner["reviewer"] == ledger["reviewer"], "reviewer mismatch")
    _require(type(owner["review_round"]) is int, "invalid round")
    _require(owner["review_round"] == 4, "invalid owner round")
    _require(
        owner["optional_explanation"] is None
        or isinstance(owner["optional_explanation"], str),
        "invalid optional owner explanation",
    )


def _source(
    row: dict[str, Any], rows: dict[str, dict[str, Any]],
    files: dict[str, tuple[str, str]],
) -> None:
    source = row["source"]
    identifier = source["example_id"]
    _require(isinstance(identifier, str) and identifier in rows, "unknown source ID")
    path, blob = files[identifier[:3]]
    _require(source["repository"] == REPO, "source repository mismatch")
    _require(source["commit"] == ROUND3_COMMIT, "source commit mismatch")
    _require(source["path"] == path, "source path mismatch")
    _require(source["blob_sha"] == blob, "source Git blob mismatch")
    _require(type(source["jsonl_line"]) is int, "invalid source line")
    _require(source["jsonl_line"] == int(identifier[4:]), "source line mismatch")


def _candidate_and_packet(row: dict[str, Any], candidate: dict[str, Any]) -> None:
    comparison = row["source_candidate"]
    action = row["owner_review"]["action"]
    _require(comparison["action_for_comparison_only"] == candidate["action"],
             "source candidate action mismatch")
    _require(comparison["semantic_label_for_comparison_only"] == candidate["label"],
             "source candidate semantic mismatch")
    _require(type(comparison["agrees_on_action"]) is bool, "invalid agreement flag")
    _require(comparison["agrees_on_action"] == (action == candidate["action"]),
             "candidate agreement mismatch")
    visible = serialize_as_of_target(candidate)
    messages = visible["messages"]
    packet = row["review_packet"]
    _require(type(packet["visible_messages"]) is int, "invalid packet size")
    _require(packet["visible_messages"] == len(messages), "packet context mismatch")
    _require(isinstance(packet["channel"], str), "invalid packet channel")
    target = messages[visible["target_index"]]["text"]
    _require(
        packet["target_text_sha256"] == hashlib.sha256(target.encode()).hexdigest(),
        "packet target text differs from frozen public source",
    )


def validate_round4(
    ledger: dict[str, Any], source_rows: dict[str, dict[str, Any]],
    source_files: dict[str, tuple[str, str]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Accept only action-only owner records with exact source provenance."""
    output: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    opaque_ids: set[str] = set()
    for number, row in enumerate(_header(ledger), 1):
        _row_structure(row, ledger, number)
        _owner_action(row, ledger)
        _source(row, source_rows, source_files)
        identifier = row["source"]["example_id"]
        _require(identifier not in seen_ids, "duplicate source ID")
        _require(row["opaque_id"] not in opaque_ids, "duplicate opaque ID")
        _candidate_and_packet(row, source_rows[identifier])
        seen_ids.add(identifier)
        opaque_ids.add(row["opaque_id"])
        output.append(_private_action(row))
    output.sort(key=lambda item: str(item["example_id"]))
    return output, _summary(output)


def _private_action(row: dict[str, Any]) -> dict[str, object]:
    return {
        "example_id": row["source"]["example_id"],
        "source_path": row["source"]["path"],
        "source_git_blob_sha": row["source"]["blob_sha"],
        "source_line": row["source"]["jsonl_line"],
        "owner_action": row["owner_review"]["action"],
        "owner_explanation": row["owner_review"]["optional_explanation"],
        "candidate_action_for_comparison": row["source_candidate"]["action_for_comparison_only"],
        "action_differs": not row["source_candidate"]["agrees_on_action"],
        "owner_review_round": 4,
        "owner_authority": "message_action_only",
        "semantic_and_other_fields": "not_adjudicated",
        "training_eligible": False,
    }


def _summary(output: list[dict[str, object]]) -> dict[str, object]:
    return {
        "round": 4,
        "owner_action_only_count": len(output),
        "actions": dict(sorted(Counter(str(r["owner_action"]) for r in output).items())),
        "different_from_synthetic_candidate": sum(bool(r["action_differs"]) for r in output),
        "training_eligible": False,
        "semantic_labels_adjudicated": 0,
        "crosswalk_hmac_verified": False,
    }


def merge_action_only(
    round3: list[dict[str, object]], round4: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Disallow silently overwriting a previous owner decision for one source."""
    combined = round3 + round4
    ids = [str(row["example_id"]) for row in combined]
    _require(len(ids) == len(set(ids)), "duplicate owner-reviewed case across rounds")
    _require(all(row["training_eligible"] is False for row in combined),
             "unapproved training admission")
    combined.sort(key=lambda row: str(row["example_id"]))
    return combined, {
        "owner_action_only_records": len(combined),
        "round3_count": len(round3), "round4_count": len(round4),
        "training_eligible": False,
        "semantic_labels_adjudicated": 0,
        "crosswalk_hmac_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round3-ledger", type=Path, required=True)
    parser.add_argument("--round4-ledger", type=Path, required=True)
    parser.add_argument("--private-registry-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = _outside_checkout(args.private_registry_out)
        inputs = [_outside_checkout(args.round3_ledger), _outside_checkout(args.round4_ledger)]
        _require(output not in inputs and not output.exists(), "unsafe output destination")
        source_rows, source_files = _source_index()
        r3, _ = validate_ledger(read_private_ledger(inputs[0]), source_rows, source_files)
        r4, _ = validate_round4(read_private_ledger(inputs[1]), source_rows, source_files)
        combined, summary = merge_action_only(r3, r4)
        _write_jsonl(output, combined)
    except (ValueError, OSError, TypeError, KeyError, UnicodeError) as exc:
        print(f"Private action-only registry refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
