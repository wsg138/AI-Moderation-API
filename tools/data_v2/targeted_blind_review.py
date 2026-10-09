"""Priority-aware blinded synthetic sample for the next targeted human review.

Coordinator selection reasons and reviewed-owner IDs are never exposed to a
reviewer. Quotas are per batch and candidate triage tier, NOT true prevalence.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tools.dataset_qa.blind_review import (
    KEY_ENV,
    _outside_checkout,
    _write_review_outputs,
    make_packet,
)
from tools.dataset_qa.freshness import ROOT, batch_files
from tools.dataset_qa.review_assignments import _check_packet

from .owner_action_registry import merge_action_only, validate_round4
from .private_owner_actions import (
    _require,
    _source_index,
    read_private_ledger,
    validate_ledger,
)
from .synthetic_family_audit import find_groups, load_candidates
from .triage_queue import build_queue, validate_source_order

QUOTAS = {
    "01_policy_conflict_candidate": 3,
    "02_high_impact_candidate": 2,
    "03_stratified_audit_candidate": 1,
}


def _rank(secret: bytes, identifier: str, purpose: str) -> str:
    return hmac.new(
        secret, f"{purpose}\0{identifier}".encode(), hashlib.sha256
    ).hexdigest()


def _diverse_selection(
    bucket: list[str], by_id: dict[str, dict[str, Any]], secret: bytes,
    purpose: str, count: int,
) -> list[str]:
    """Pick distinct declared families first, then fill quotas if necessary."""
    ordered = sorted(bucket, key=lambda ident: _rank(secret, ident, purpose))
    chosen: list[str] = []
    families: set[str] = set()
    for identifier in ordered:
        family = str(by_id[identifier].get("family_id") or identifier)
        if family not in families:
            chosen.append(identifier)
            families.add(family)
        if len(chosen) == count:
            return chosen
    for identifier in ordered:
        if identifier not in chosen:
            chosen.append(identifier)
        if len(chosen) == count:
            break
    return chosen


def _validate_frame(
    queue: list[dict[str, object]], by_id: dict[str, dict[str, Any]],
) -> None:
    _require(
        len({row["example_id"] for row in queue}) == len(queue),
        "triage queue duplicate",
    )
    _require(len(queue) == len(by_id), "triage queue incomplete")
    for row in queue:
        _require(str(row["example_id"]) in by_id, "unknown candidate ID")
        _require(str(row["triage_priority"]) in QUOTAS, "unknown candidate triage tier")


def _candidate_buckets(
    queue: list[dict[str, object]], reviewed: set[str],
) -> dict[tuple[str, str], list[str]]:
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in queue:
        identifier = str(row["example_id"])
        if identifier not in reviewed:
            buckets[(identifier[:3], str(row["triage_priority"]))].append(identifier)
    return buckets


def select_review_ids(
    queue: list[dict[str, object]], by_id: dict[str, dict[str, Any]],
    reviewed: set[str], secret: bytes,
) -> tuple[list[str], dict[str, object]]:
    """Keyed sample across source batches and priority tiers; no label reuse."""
    _require(len(secret) >= 16, "invalid review secret")
    _require(set(by_id).issuperset(reviewed), "invalid review secret or owner reviewed IDs")
    _validate_frame(queue, by_id)
    selected: list[str] = []
    tiers: Counter[str] = Counter()
    for (batch, tier), identifiers in sorted(_candidate_buckets(queue, reviewed).items()):
        chosen = _diverse_selection(
            identifiers, by_id, secret, f"{batch}:{tier}", QUOTAS[tier]
        )
        selected.extend(chosen)
        tiers[tier] += len(chosen)
    _require(len(selected) == len(set(selected)), "duplicate selected cohort")
    _require(bool(selected), "invalid or empty selected cohort")
    ordered = sorted(selected, key=lambda ident: _rank(secret, ident, "review-order"))
    summary: dict[str, object] = {
        "source_scope": "pinned_public_synthetic_G10_G27",
        "selected": len(ordered),
        "previously_owner_action_reviewed_excluded": len(reviewed),
        "selected_by_priority": dict(sorted(tiers.items())),
        "sampling": "keyed_batch_by_candidate_tier_with_family_diversity",
        "candidate_only": True,
        "training_eligible": False,
    }
    return ordered, summary


def build_blind_sample(
    rows: list[dict[str, Any]], queue: list[dict[str, object]],
    reviewed: set[str], secret: bytes,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    by_id = {str(row["example_id"]): row for row in rows}
    selected, summary = select_review_ids(queue, by_id, reviewed, secret)
    coordinator = {str(row["example_id"]): row for row in queue}
    packets: list[dict[str, object]] = []
    crosswalk: list[dict[str, object]] = []
    for identifier in selected:
        packet = make_packet(by_id[identifier], secret)
        _check_packet(packet)
        item = coordinator[identifier]
        crosswalk.append({
            "packet_id": packet["packet_id"], "example_id": identifier,
            "source_file": item["source_file"],
            "source_sha256": item["source_sha256"],
            "source_line": item["source_line"],
            "selected_priority_tier": item["triage_priority"],
        })
        packets.append(packet)
    return packets, crosswalk, summary


def _owner_reviewed(round3: Path | None, round4: Path | None) -> set[str]:
    if round3 is None and round4 is None:
        return set()
    source_rows, source_files = _source_index()
    prior3: list[dict[str, object]] = []
    prior4: list[dict[str, object]] = []
    if round3 is not None:
        prior3, _ = validate_ledger(
            read_private_ledger(_outside_checkout(round3)), source_rows, source_files
        )
    if round4 is not None:
        prior4, _ = validate_round4(
            read_private_ledger(_outside_checkout(round4)), source_rows, source_files
        )
    combined, _ = merge_action_only(prior3, prior4)
    return {str(item["example_id"]) for item in combined}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-out", type=Path, required=True)
    parser.add_argument("--coordinator-map-out", type=Path, required=True)
    parser.add_argument("--private-owner-ledger", type=Path)
    parser.add_argument("--private-round4-ledger", type=Path)
    args = parser.parse_args(argv)
    try:
        packet_out = _outside_checkout(args.packet_out)
        map_out = _outside_checkout(args.coordinator_map_out)
        if packet_out == map_out or packet_out.exists() or map_out.exists():
            raise ValueError("outputs must be distinct and unused")
        secret = os.environ.get(KEY_ENV, "").encode()
        rows = load_candidates()
        validate_source_order(rows)
        files = {p.name[:3]: str(p) for p in batch_files(ROOT, require_complete=True)}
        queue, _ = build_queue(rows, find_groups(rows), files)
        packets, crosswalk, summary = build_blind_sample(
            rows, queue, _owner_reviewed(
                args.private_owner_ledger, args.private_round4_ledger
            ), secret
        )
        _write_review_outputs(packet_out, packets, map_out, crosswalk)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        print(f"Blind targeted review refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
