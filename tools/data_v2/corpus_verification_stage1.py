"""Stage 1 of independent verification: source-locked, non-admitting audit.

Checks all G10-G27 candidates; identifies same-input outcome contradictions;
creates a balanced, family-deduplicated blind review wave. No AI judge or
human verification is implied. Public stdout is aggregate counts only.
"""
from __future__ import annotations

import argparse
import hashlib
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
from tools.dataset_qa.freshness import ROOT, batch_files, report_for
from tools.dataset_qa.normalize import normalize_text

from .synthetic_family_audit import SOURCE_COMMIT, Group, find_groups, load_candidates
from .triage_queue import build_queue, validate_source_order

WAVE_PER_BATCH = 10
TARGET_QUOTA = {
    "01_policy_conflict_candidate": 4,
    "02_high_impact_candidate": 3,
    "03_stratified_audit_candidate": 3,
}
OUTCOME_FIELDS = (
    "label", "action", "review_priority", "strike", "containment",
    "containment_duration_seconds", "support_flow", "reason_codes",
)
SELECTION_SEED = b"enthusia-verification-stage1-v1"


def _require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def _digest_id(identifier: str) -> str:
    return hashlib.sha256(SELECTION_SEED + identifier.encode("ascii")).hexdigest()


def _outcome(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def outcome_conflicts(
    rows: list[dict[str, Any]], groups: list[Group],
) -> dict[str, set[str]]:
    """Same target-visible input with differing proposed outcomes needs review."""
    indexed = {row["example_id"]: row for row in rows}
    flagged: dict[str, set[str]] = defaultdict(set)
    for group in groups:
        if group.kind != "asof_exact":
            continue
        for field in OUTCOME_FIELDS:
            values = {_outcome(indexed[i].get(field)) for i in group.example_ids}
            if len(values) > 1:
                for identifier in group.example_ids:
                    flagged[identifier].add(field)
    return dict(flagged)


def _level(row: dict[str, object], conflicts: dict[str, set[str]]) -> str:
    identifier = str(row["example_id"])
    if identifier in conflicts:
        return "01_policy_conflict_candidate"
    return str(row["triage_priority"])


def _unique_key(row: dict[str, Any]) -> tuple[str, str]:
    target = row["messages"][row["target_index"]]["text"]
    return str(row.get("family_id") or row["example_id"]), normalize_text(target)


def _unseen(row: dict[str, Any], used_families: set[str], used_targets: set[str]) -> bool:
    family, target = _unique_key(row)
    return family not in used_families and target not in used_targets


def _include(row: dict[str, Any], families: set[str], targets: set[str]) -> None:
    family, target = _unique_key(row)
    families.add(family)
    targets.add(target)


def _add_if_new(
    row: dict[str, Any], selected: list[str],
    families: set[str], targets: set[str], mode: str = "both",
) -> bool:
    identifier = str(row["example_id"])
    family, target = _unique_key(row)
    if identifier in selected:
        return False
    if mode == "both" and not _unseen(row, families, targets):
        return False
    if mode == "family" and family in families:
        return False
    selected.append(identifier)
    families.add(family)
    targets.add(target)
    return True


def _fill_batch(
    ordered: list[dict[str, Any]], selected: list[str],
    families: set[str], targets: set[str],
) -> None:
    for mode in ("both", "family", "any"):
        for row in ordered:
            if len(selected) >= WAVE_PER_BATCH:
                return
            _add_if_new(row, selected, families, targets, mode)


def _select_batch(
    rows: list[dict[str, Any]], tiers: dict[str, str],
    families: set[str], targets: set[str],
) -> list[str]:
    """Prefer distinct families/targets, but never leave a batch unrepresented."""
    ordered = sorted(rows, key=lambda row: _digest_id(str(row["example_id"])))
    selected: list[str] = []
    for tier, limit in TARGET_QUOTA.items():
        chosen = 0
        for row in ordered:
            if tiers[str(row["example_id"])] != tier:
                continue
            if _add_if_new(row, selected, families, targets):
                chosen += 1
            if chosen == limit:
                break
    _fill_batch(ordered, selected, families, targets)
    _require(len(selected) == WAVE_PER_BATCH, "not enough source cases for review wave")
    return selected


def sample_wave(
    rows: list[dict[str, Any]], tiers: dict[str, str],
) -> list[str]:
    """Choose 10 per public source batch, deterministically, no shared family/target."""
    by_batch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_batch[str(row["example_id"])[:3]].append(row)
    _require(set(by_batch) == {f"G{i:02d}" for i in range(10, 28)},
             "expected all 18 public source batches")
    families: set[str] = set()
    targets: set[str] = set()
    chosen: list[str] = []
    for batch in sorted(by_batch):
        chosen.extend(_select_batch(by_batch[batch], tiers, families, targets))
    _require(len(chosen) == 180 and len(set(chosen)) == 180,
             "expected 180 unique candidates")
    return chosen


def stage1(
    rows: list[dict[str, Any]], groups: list[Group], files: dict[str, str],
) -> tuple[list[str], dict[str, dict[str, object]], dict[str, object]]:
    """Full-corpus review routing; no verified labels, no training admission."""
    validate_source_order(rows)
    queue, prior_summary = build_queue(rows, groups, files)
    contrasts = outcome_conflicts(rows, groups)
    tiers = {str(row["example_id"]): _level(row, contrasts) for row in queue}
    selected = sample_wave(rows, tiers)
    indexed = {str(row["example_id"]): row for row in queue}
    counters = Counter(tiers.values())
    chosen_counts = Counter(tiers[identifier] for identifier in selected)
    fields = Counter(field for names in contrasts.values() for field in names)
    chosen_keys = [_unique_key(row) for row in rows if row["example_id"] in set(selected)]
    family_counts = Counter(family for family, _ in chosen_keys)
    target_counts = Counter(target for _, target in chosen_keys)
    return selected, indexed, {
        "source_commit": SOURCE_COMMIT,
        "all_source_hashes_verified": True,
        "records_audited": len(rows),
        "source_batches": len(files),
        "duplicate_and_family_audit_groups": len(groups),
        "same_input_outcome_conflict_cases": len(contrasts),
        "same_input_conflicting_fields": dict(sorted(fields.items())),
        "priority_candidates": dict(sorted(counters.items())),
        "first_blind_review_wave": len(selected),
        "selected_priority_counts": dict(sorted(chosen_counts.items())),
        "selected_declared_family_repetitions": sum(n - 1 for n in family_counts.values()),
        "selected_normalized_target_repetitions": sum(n - 1 for n in target_counts.values()),
        "independent_reviews_completed": 0,
        "semantically_verified_records": 0,
        "training_eligible": False,
        "no_candidate_labels_changed": True,
    }


def private_review_outputs(
    selected: list[str], rows: list[dict[str, Any]],
    queue: dict[str, dict[str, object]], packet_path: Path, map_path: Path,
    secret: bytes,
) -> None:
    """Reviewer sees only context; coordinator privately keeps source mapping."""
    _require(len(secret) >= 16, "review key must have at least 16 bytes")
    packets: list[dict[str, object]] = []
    mappings: list[dict[str, object]] = []
    by_id = {str(r["example_id"]): r for r in rows}
    for identifier in selected:
        packet = make_packet(by_id[identifier], secret)
        meta = queue[identifier]
        packets.append(packet)
        mappings.append({
            "packet_id": packet["packet_id"], "example_id": identifier,
            "source_commit": meta["source_commit"],
            "source_sha256": meta["source_sha256"],
            "source_line": meta["source_line"],
            "candidate_label_for_comparison_only": meta["candidate_semantic_label"],
            "candidate_action_for_comparison_only": meta["candidate_action"],
            "training_eligible": False,
        })
    _write_review_outputs(_outside_checkout(packet_path), packets,
                          _outside_checkout(map_path), mappings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-out", type=Path)
    parser.add_argument("--crosswalk-out", type=Path)
    args = parser.parse_args(argv)
    try:
        files = batch_files(ROOT, require_complete=True)
        _require(len(files) == 18, "expected 18 candidate source files")
        for path in files:
            report_for(path)
        rows = load_candidates()
        selected, queue, summary = stage1(
            rows, find_groups(rows), {p.name[:3]: str(p) for p in files},
        )
        _require((args.packet_out is None) == (args.crosswalk_out is None),
                 "review packets and coordinator map must both be requested")
        if args.packet_out is not None and args.crosswalk_out is not None:
            private_review_outputs(
                selected, rows, queue, args.packet_out, args.crosswalk_out,
                os.environ.get(KEY_ENV, "").encode("utf-8"),
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stage-1 candidate audit refused: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
