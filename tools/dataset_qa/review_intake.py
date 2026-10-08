"""Fail-closed intake of independently assigned Policy-v1 review decisions.

This is an OFFLINE evidence/status gate. Reviewer IDs are assertions,
not proof of independent human identities. All records remain unadmitted.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .blind_review import _outside_checkout, _write_jsonl
from .review_assignments import _check_packet, packet_digest
from .review_decisions import review_summary, validate_decision


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("JSONL input must contain objects only")
    return rows


def _manifest_index(
    packets: list[dict[str, object]], manifest: list[dict[str, Any]],
) -> dict[str, set[str]]:
    packet_by_id = {str(packet["packet_id"]): packet for packet in packets}
    if len(packet_by_id) != len(packets) or len(manifest) != len(packets):
        raise ValueError("manifest/packet count or identity mismatch")
    assigned: dict[str, set[str]] = {}
    for entry in manifest:
        identifier = entry.get("packet_id")
        if identifier not in packet_by_id or identifier in assigned:
            raise ValueError("unknown or duplicate manifest packet")
        if entry.get("packet_sha256") != packet_digest(packet_by_id[identifier]):
            raise ValueError("packet content differs from frozen assignment")
        reviewers = entry.get("assigned_reviewers")
        if not isinstance(reviewers, list) or len(reviewers) != 2:
            raise ValueError("each packet requires two assigned reviewers")
        if not all(isinstance(alias, str) for alias in reviewers):
            raise ValueError("invalid reviewer identity")
        if len(set(reviewers)) != 2:
            raise ValueError("reviewers must be distinct")
        assigned[identifier] = set(reviewers)
    return assigned


def intake(
    packets: list[dict[str, object]], manifest: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    """Reject unauthorized or copied submissions before status creation."""
    for packet in packets:
        _check_packet(packet)
    assigned = _manifest_index(packets, manifest)
    packet_by_id = {str(packet["packet_id"]): packet for packet in packets}
    submitted: dict[str, set[str]] = defaultdict(set)
    for decision in decisions:
        identifier = decision.get("packet_id")
        alias = decision.get("reviewer_id")
        if identifier not in assigned or alias not in assigned[identifier]:
            raise ValueError("unassigned reviewer submission")
        if alias in submitted[identifier]:
            raise ValueError("duplicate reviewer submission")
        validate_decision(decision, packet_by_id[identifier])
        submitted[identifier].add(alias)
    return review_summary(packets, decisions)


def _status_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row["status"])] += 1
    return dict(sorted(counts.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-input", type=Path, required=True)
    parser.add_argument("--manifest-input", type=Path, required=True)
    parser.add_argument("--decision-input", type=Path, action="append", default=[])
    parser.add_argument("--status-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        destination = _outside_checkout(args.status_out)
        if destination.exists():
            raise ValueError("status file already exists")
        packets = _read_jsonl(args.packet_input)
        manifest = _read_jsonl(args.manifest_input)
        decisions = [
            row for file in args.decision_input for row in _read_jsonl(file)
        ]
        result = intake(packets, manifest, decisions)
        _write_jsonl(destination, result)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Review intake failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"review_statuses": _status_counts(result), "training_eligible": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
