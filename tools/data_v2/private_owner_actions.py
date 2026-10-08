"""Offline owner action-only intake; private ledger is NEVER committed.

Only source-anchored action judgments are imported. No semantic/punishment gold.
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

from tools.dataset_qa.blind_review import _outside_checkout, _write_jsonl
from tools.dataset_qa.freshness import ROOT, batch_files

from .synthetic_family_audit import load_candidates
from .triage_queue import validate_source_order

ROUND3_COMMIT = "21cc2cfa734c9b16801ee90ad03fbd93c1d73f56"
REPO = "wsg138/AI-Moderation-API"
ACTIONS = frozenset({"ALLOW", "REVIEW", "BLOCK"})
OPAQUE = re.compile(r"R-[0-9a-f]{24}$")
RECORD_FIELDS = {
    "question", "opaque_id", "source", "decision", "comparison",
    "review_flags", "training_eligible", "semantic_label_adjudicated",
    "other_policy_fields_adjudicated",
}
SOURCE_FIELDS = {
    "repository", "git_commit", "path", "git_blob_sha",
    "record_id", "original_jsonl_line_number",
}
DECISION_FIELDS = {
    "reviewer", "review_round", "policy_version",
    "authority", "action", "explanation",
}
COMPARISON_FIELDS = {
    "candidate_action", "candidate_semantic_label_for_comparison_only",
    "action_agrees_with_candidate",
}


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate private-ledger JSON key")
        result[key] = value
    return result


def read_private_ledger(path: Path) -> dict[str, Any]:
    """Enforce tight size and JSON bounds without printing any contents."""
    raw = path.read_bytes()
    if len(raw) > 4 * 1024 * 1024 or not raw:
        raise ValueError("private ledger empty or oversized")
    result = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    if not isinstance(result, dict):
        raise ValueError("private ledger must be a JSON object")
    return result


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324 - Git SHA-1 lineage only


def _source_index() -> tuple[dict[str, dict[str, Any]], dict[str, tuple[str, str]]]:
    rows = load_candidates()
    validate_source_order(rows)
    files: dict[str, tuple[str, str]] = {}
    for path in batch_files(ROOT, require_complete=True):
        files[path.name[:3]] = (str(path), _git_blob_sha(path.read_bytes()))
    return {str(row["example_id"]): row for row in rows}, files


def _header(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    required = {
        "schema_version", "private_coordinator_artifact", "privacy", "review_date",
        "reviewer", "round", "case_count", "source_commit", "provenance",
        "methodology", "assessment", "training_eligible_cases", "records",
    }
    if set(ledger) != required or ledger["source_commit"] != ROUND3_COMMIT:
        raise ValueError("unexpected private ledger schema or source commit")
    records = ledger["records"]
    if (ledger["private_coordinator_artifact"] is not True
            or ledger["training_eligible_cases"] != 0
            or type(ledger["round"]) is not int or ledger["round"] != 3
            or not isinstance(records, list) or len(records) != 50
            or type(ledger["case_count"]) is not int or ledger["case_count"] != 50):
        raise ValueError("invalid owner review header or count")
    return records


def _check_structure(entry: dict[str, Any], ledger: dict[str, Any]) -> None:
    if set(entry) != RECORD_FIELDS or set(entry["source"]) != SOURCE_FIELDS:
        raise ValueError("missing or unexpected owner/source fields")
    if set(entry["decision"]) != DECISION_FIELDS or set(entry["comparison"]) != COMPARISON_FIELDS:
        raise ValueError("missing or unexpected action/comparison fields")
    decision = entry["decision"]
    if (decision["action"] not in ACTIONS or decision["authority"] !=
            "owner_authoritative_action_only" or decision["policy_version"] != "v1"):
        raise ValueError("invalid owner action scope")
    if (decision["reviewer"] != ledger["reviewer"] or
            decision["review_round"] != ledger["round"]):
        raise ValueError("reviewer or review round mismatch")
    if decision["explanation"] is not None and not isinstance(decision["explanation"], str):
        raise ValueError("invalid optional explanation")
    if (entry["training_eligible"] is not False or
            entry["semantic_label_adjudicated"] is not False or
            entry["other_policy_fields_adjudicated"] is not False):
        raise ValueError("unapproved label admission or invented annotation")
    if not isinstance(entry["opaque_id"], str) or not OPAQUE.fullmatch(entry["opaque_id"]):
        raise ValueError("malformed opaque review ID")


def _check_source(
    entry: dict[str, Any], rows: dict[str, dict[str, Any]],
    files: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    source = entry["source"]
    identifier = source["record_id"]
    if not isinstance(identifier, str) or identifier not in rows:
        raise ValueError("review references unknown source case")
    path, blob = files[identifier[:3]]
    if (source["repository"] != REPO or source["git_commit"] != ROUND3_COMMIT
            or source["path"] != path or source["git_blob_sha"] != blob
            or type(source["original_jsonl_line_number"]) is not int
            or source["original_jsonl_line_number"] != int(identifier[4:])):
        raise ValueError("source provenance does not match frozen bytes")
    comparison = entry["comparison"]
    candidate = rows[identifier]
    if (comparison["candidate_action"] != candidate["action"]
            or comparison["candidate_semantic_label_for_comparison_only"] != candidate["label"]
            or type(comparison["action_agrees_with_candidate"]) is not bool
            or comparison["action_agrees_with_candidate"] != (
                entry["decision"]["action"] == candidate["action"]
            )):
        raise ValueError("private review candidate comparison mismatch")
    return candidate


def validate_ledger(
    ledger: dict[str, Any], rows: dict[str, dict[str, Any]],
    files: dict[str, tuple[str, str]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """No context, label or punishment field is imported as owner ground truth."""
    seen_ids: set[str] = set()
    seen_opaque: set[str] = set()
    corrections: list[dict[str, object]] = []
    for entry in _header(ledger):
        _check_structure(entry, ledger)
        identifier = entry["source"]["record_id"]
        if identifier in seen_ids or entry["opaque_id"] in seen_opaque:
            raise ValueError("duplicate reviewed source or opaque ID")
        _check_source(entry, rows, files)
        seen_ids.add(identifier)
        seen_opaque.add(entry["opaque_id"])
        corrections.append(_owner_action_row(entry))
    corrections.sort(key=lambda item: str(item["example_id"]))
    return corrections, _aggregate(corrections)


def _owner_action_row(entry: dict[str, Any]) -> dict[str, object]:
    decision = entry["decision"]
    source = entry["source"]
    comparison = entry["comparison"]
    return {
        "example_id": source["record_id"],
        "source_path": source["path"],
        "source_git_blob_sha": source["git_blob_sha"],
        "source_line": source["original_jsonl_line_number"],
        "owner_action": decision["action"],
        "owner_explanation": decision["explanation"],
        "candidate_action_for_comparison": comparison["candidate_action"],
        "action_differs": not comparison["action_agrees_with_candidate"],
        "owner_review_round": decision["review_round"],
        "owner_authority": "message_action_only",
        "semantic_and_other_fields": "not_adjudicated",
        "training_eligible": False,
    }


def _aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "source_commit": ROUND3_COMMIT,
        "imported_owner_action_only": len(rows),
        "actions": dict(sorted(Counter(str(r["owner_action"]) for r in rows).items())),
        "different_from_synthetic_candidate": sum(bool(r["action_differs"]) for r in rows),
        "semantic_labels_adjudicated": 0,
        "training_eligible": False,
        "provenance": "source_bytes_verified; opaque_id_not_cryptographically_rederived",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger-input", type=Path, required=True)
    parser.add_argument("--private-corrections-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        destination = _outside_checkout(args.private_corrections_out)
        if destination == args.ledger_input.resolve() or destination.exists():
            raise ValueError("private destination exists or aliases input")
        corrections, summary = validate_ledger(
            read_private_ledger(args.ledger_input), *_source_index()
        )
        _write_jsonl(destination, corrections)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        print(f"Private action intake refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
