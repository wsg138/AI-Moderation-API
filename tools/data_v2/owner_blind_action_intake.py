"""Verify owner action-only answers against locked private first-wave packets.

This is offline coordinator tooling for source-pinned synthetic data only.
No model agreement, owner action, or REVIEW status is training gold.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from tools.dataset_qa.asof_input import serialize_as_of_target
from tools.dataset_qa.blind_review import _outside_checkout, _write_jsonl
from tools.dataset_qa.freshness import ROOT, batch_files
from tools.dataset_qa.review_jsonl import read_jsonl

from .corpus_verification_stage1 import stage1
from .private_owner_actions import read_private_ledger
from .synthetic_family_audit import SOURCE_COMMIT, find_groups, load_candidates

OPAQUE = re.compile(r"R-[0-9a-f]{24}\Z")
ACTIONS = frozenset({"ALLOW", "REVIEW", "BLOCK"})
MAP_FIELDS = frozenset({
    "packet_id", "example_id", "source_commit", "source_sha256",
    "source_line", "candidate_label_for_comparison_only",
    "candidate_action_for_comparison_only", "training_eligible",
})
OWNER_FIELDS = frozenset({"type", "training_eligible", "decisions"})
DECISION_FIELDS = frozenset({"packet_id", "owner_action", "owner_reason"})


def _require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def _index(
    packets: list[dict[str, Any]], maps: list[dict[str, Any]],
    selected: list[str], source: dict[str, dict[str, Any]],
    queue: dict[str, dict[str, object]],
) -> dict[str, tuple[str, dict[str, Any]]]:
    """Check every sealed packet against the source-pinned as-of projection."""
    _require(len(packets) == len(maps) == len(selected) == 180,
             "expected exactly the frozen 180-case first wave")
    indexed: dict[str, tuple[str, dict[str, Any]]] = {}
    seen_sources: set[str] = set()
    for packet, entry, identifier in zip(packets, maps, selected, strict=True):
        _require(set(entry) == MAP_FIELDS, "invalid crosswalk fields")
        _require(entry["example_id"] == identifier and identifier in source,
                 "crosswalk is not the frozen ordered first wave")
        pid = entry["packet_id"]
        _require(isinstance(pid, str) and bool(OPAQUE.fullmatch(pid)),
                 "invalid blinded packet identifier")
        _require(pid not in indexed and identifier not in seen_sources,
                 "duplicate source or packet")
        _require(entry["source_commit"] == SOURCE_COMMIT,
                 "source commit mismatch")
        _require(entry["source_sha256"] == queue[identifier]["source_sha256"],
                 "source digest mismatch")
        _require(entry["source_line"] == queue[identifier]["source_line"],
                 "source line mismatch")
        _require(entry["candidate_label_for_comparison_only"] == source[identifier]["label"],
                 "candidate label mismatch")
        _require(entry["candidate_action_for_comparison_only"] == source[identifier]["action"],
                 "candidate action mismatch")
        _require(entry["training_eligible"] is False,
                 "crosswalk attempted training admission")
        expected = {"packet_id": pid, **serialize_as_of_target(source[identifier])}
        _require(packet == expected, "private packet differs from pinned target context")
        indexed[pid] = identifier, entry
        seen_sources.add(identifier)
    return indexed


def _owner_rows(submission: dict[str, Any]) -> list[dict[str, Any]]:
    _require(set(submission) == OWNER_FIELDS
             and submission["type"] == "blinded_owner_action_review"
             and submission["training_eligible"] is False,
             "invalid action-only owner submission")
    rows = submission["decisions"]
    _require(isinstance(rows, list) and 1 <= len(rows) <= 180,
             "owner review must contain 1-180 decisions")
    for row in rows:
        _require(isinstance(row, dict) and set(row) == DECISION_FIELDS,
                 "invalid owner decision fields")
        _require(row["owner_action"] in ACTIONS, "unknown owner action")
        _require(isinstance(row["owner_reason"], str)
                 and len(row["owner_reason"]) <= 2000, "invalid owner reason")
    return rows


def reconcile(
    packets: list[dict[str, Any]], mapping: list[dict[str, Any]],
    submission: dict[str, Any], selected: list[str],
    source: dict[str, dict[str, Any]], queue: dict[str, dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Owner decisions are action-only, never semantic or enforcement approval."""
    lookup = _index(packets, mapping, selected, source, queue)
    seen: set[str] = set()
    records: list[dict[str, object]] = []
    for decision in _owner_rows(submission):
        pid = decision["packet_id"]
        _require(isinstance(pid, str) and pid in lookup and pid not in seen,
                 "unknown or duplicate owner packet")
        seen.add(pid)
        identifier, meta = lookup[pid]
        action = decision["owner_action"]
        records.append({
            "packet_id": pid,
            "example_id": identifier,
            "source_commit": SOURCE_COMMIT,
            "source_sha256": meta["source_sha256"],
            "source_line": meta["source_line"],
            "owner_action": action,
            "owner_reason": decision["owner_reason"],
            "candidate_action_for_comparison_only": source[identifier]["action"],
            "owner_matches_candidate": action == source[identifier]["action"],
            "owner_authority": "action_only",
            "semantic_label_verified": False,
            "punishment_fields_verified": False,
            "independent_semantic_review_completed": False,
            "training_eligible": False,
        })
    records.sort(key=lambda row: str(row["example_id"]))
    actions = Counter(str(row["owner_action"]) for row in records)
    return records, {
        "owner_action_only_records": len(records),
        "actions": dict(sorted(actions.items())),
        "disagrees_with_candidate_action": sum(
            not row["owner_matches_candidate"] for row in records
        ),
        "owner_review_unresolved": actions["REVIEW"],
        "semantic_labels_verified": 0,
        "training_eligible": False,
        "opaque_crosswalk_key_authenticated": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-input", type=Path, required=True)
    parser.add_argument("--crosswalk-input", type=Path, required=True)
    parser.add_argument("--owner-input", type=Path, required=True)
    parser.add_argument("--private-registry-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        sources = [args.packet_input, args.crosswalk_input, args.owner_input]
        source_paths = [_outside_checkout(path) for path in sources]
        output = _outside_checkout(args.private_registry_out)
        _require(output not in source_paths and not output.exists(),
                 "registry destination exists or matches input")
        files = batch_files(ROOT, require_complete=True)
        rows = load_candidates()
        selected, queue, _ = stage1(rows, find_groups(rows), {
            file.name[:3]: str(file) for file in files
        })
        records, result = reconcile(
            read_jsonl(source_paths[0]), read_jsonl(source_paths[1]),
            read_private_ledger(source_paths[2]), selected,
            {str(row["example_id"]): row for row in rows}, queue,
        )
        _write_jsonl(output, records)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print(f"Private owner intake refused: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
