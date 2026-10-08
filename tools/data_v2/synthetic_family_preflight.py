"""Fail-closed candidate-only split proposal checker (never creates splits)."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .synthetic_family_audit import (
    EVIDENCE_KINDS,
    SOURCE_COMMIT,
    Group,
    find_groups,
    load_candidates,
)

PARTITIONS = frozenset({"candidate_a", "candidate_b"})


def _header(payload: object) -> object:
    if not isinstance(payload, dict) or set(payload) != {
        "status", "source_commit", "assignments",
    }:
        raise ValueError("proposal must contain only status, source_commit, assignments")
    if payload["status"] != "candidate" or payload["source_commit"] != SOURCE_COMMIT:
        raise ValueError("unapproved status or unpinned source commit")
    return payload["assignments"]


def _assignments(value: object, source_ids: set[str]) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != source_ids:
        raise ValueError("proposal must assign exactly every pinned synthetic case")
    if any(not isinstance(item, str) or item not in PARTITIONS for item in value.values()):
        raise ValueError("only candidate_a and candidate_b are permitted")
    if set(value.values()) != PARTITIONS:
        raise ValueError("both candidate partitions must be present")
    return value


def validate_proposal(payload: object, source_ids: set[str]) -> dict[str, str]:
    """Require complete coverage and pinned public candidate status."""
    return _assignments(_header(payload), source_ids)


def conflict_summary(
    groups: list[Group], assignments: dict[str, str],
) -> dict[str, int]:
    """Count evidence groups spanning both candidate partitions."""
    counts: Counter[str] = Counter()
    for group in groups:
        if len({assignments[identifier] for identifier in group.example_ids}) > 1:
            counts[group.kind] += 1
    return {kind: counts[kind] for kind in EVIDENCE_KINDS}


def check(rows: list[dict[str, Any]], payload: object) -> dict[str, object]:
    ids = [row["example_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate IDs")
    assignments = validate_proposal(payload, set(ids))
    conflict_counts = conflict_summary(find_groups(rows), assignments)
    blocked = any(conflict_counts.values())
    return {
        "source_commit": SOURCE_COMMIT,
        "status": "blocked" if blocked else "candidate_only_no_detected_overlap",
        "training_eligible": False,
        "candidate_cases": len(rows),
        "cross_partition_evidence_groups": conflict_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = load_candidates()
        payload = json.loads(args.proposal.read_text(encoding="utf-8"))
        result = check(rows, payload)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Candidate split preflight rejected: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
