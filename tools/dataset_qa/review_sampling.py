"""Reproducible blind-review sampling of public synthetic candidates only.

Priority flags and original source labels are used to SELECT records but are
never included in reviewer-facing packets. This is NOT label adjudication.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .blind_review import (
    KEY_ENV,
    _outside_checkout,
    _write_jsonl,
    build_packets,
)
from .candidate_audit import _add_overlap, _cross_batch, _flags
from .freshness import ROOT, batch_files

PRIORITY_LIMITS = {
    "safe_with_self_harm_directive": None,
    "safe_with_severe_reason_code": None,
    "staff_targeted_reason_label_disagreement": None,
    "grooming_without_explicit_minor_cue": 32,
}


def _rank(identifier: str, secret: bytes, purpose: str) -> str:
    return hmac.new(
        secret, f"{purpose}\0{identifier}".encode(), hashlib.sha256
    ).hexdigest()


def _source_records(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in batch_files(directory, require_complete=True):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("synthetic candidate must be an object")
            rows.append(record)
    return rows


def _buckets(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        identifier = row["example_id"]
        buckets[f"label:{row['label']}"].append(identifier)
        buckets[f"channel:{row['channel_profile']}"].append(identifier)
        for flag in _flags(row):
            if flag in PRIORITY_LIMITS:
                buckets[f"priority:{flag}"].append(identifier)
    return buckets


def _overlap_ids(rows: list[dict[str, Any]]) -> set[str]:
    duplicates: dict[str, list[str]] = defaultdict(list)
    targets: dict[str, list[str]] = defaultdict(list)
    families: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        _add_overlap(row, duplicates, targets, families)
    groups = (
        _cross_batch(duplicates) + _cross_batch(targets) + _cross_batch(families)
    )
    return {identifier for group in groups for identifier in group}


def _selection_reasons(
    rows: list[dict[str, Any]], secret: bytes,
    label_quota: int, channel_quota: int,
) -> dict[str, set[str]]:
    chosen: dict[str, set[str]] = defaultdict(set)
    for bucket, identifiers in sorted(_buckets(rows).items()):
        quota = label_quota if bucket.startswith("label:") else channel_quota
        if bucket.startswith("priority:"):
            flag = bucket.removeprefix("priority:")
            quota = PRIORITY_LIMITS[flag]
        ordered = sorted(identifiers, key=lambda ident: _rank(ident, secret, bucket))
        for identifier in ordered[:quota]:
            chosen[identifier].add(bucket)
    for identifier in _overlap_ids(rows):
        chosen[identifier].add("cross_batch_family")
    return chosen


def sample_review(
    rows: list[dict[str, Any]], secret: bytes,
    label_quota: int = 12, channel_quota: int = 8,
) -> dict[str, set[str]]:
    """Select stratified+priority records; output reasons are coordinator-only."""
    if len(secret) < 16 or label_quota < 1 or channel_quota < 1:
        raise ValueError("invalid sampling key or quotas")
    ids = [row["example_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate synthetic IDs in sampling frame")
    return _selection_reasons(rows, secret, label_quota, channel_quota)


def build_sample(
    directory: Path, secret: bytes,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Return reviewer packets and an isolated coordinator-only selection map."""
    packets, crosswalk = build_packets(directory, secret)
    rows = _source_records(directory)
    reasons = sample_review(rows, secret)
    packet_by_id = {packet["packet_id"]: packet for packet in packets}
    selected_map = [
        {**entry, "selection_reasons": sorted(reasons[entry["example_id"]])}
        for entry in crosswalk if entry["example_id"] in reasons
    ]
    selected_map.sort(key=lambda entry: _rank(entry["example_id"], secret, "order"))
    selected_packets = [packet_by_id[entry["packet_id"]] for entry in selected_map]
    return selected_packets, selected_map


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-out", type=Path, required=True)
    parser.add_argument("--coordinator-map-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        packet_out = _outside_checkout(args.packet_out)
        map_out = _outside_checkout(args.coordinator_map_out)
        if packet_out == map_out or packet_out.exists() or map_out.exists():
            raise ValueError("output paths must be distinct and not already exist")
        secret = os.environ.get(KEY_ENV, "").encode("utf-8")
        packets, selection_map = build_sample(ROOT, secret)
        _write_jsonl(packet_out, packets)
        _write_jsonl(map_out, selection_map)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Review sample preparation failed: {exc}", file=sys.stderr)
        return 2
    print(f"Prepared {len(packets)} blinded synthetic candidates; not reviewed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
