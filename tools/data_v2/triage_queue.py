"""Source-pinned, read-only triage of G10–G27 synthetic candidate cases.

This queues hypotheses; it NEVER propagates labels or admits training records.
Owner quick-review decisions and their private crosswalk are not read here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tools.dataset_qa.asof_input import serialize_as_of_target
from tools.dataset_qa.blind_review import _outside_checkout, _write_jsonl
from tools.dataset_qa.candidate_audit import _policy_flags, _reason_flags, _text_flags
from tools.dataset_qa.freshness import ROOT, batch_files
from tools.dataset_qa.owner_blackmail_audit import game_only_candidate

from .synthetic_family_audit import (
    SOURCE_COMMIT,
    SOURCE_DIGESTS,
    Group,
    find_groups,
    load_candidates,
)

POLICY_RISK = frozenset({
    "gameplay_blackmail_scope_review",
    "multilingual_policy_boundary",
    "self_disclosed_contact_policy_boundary",
    "asof_exact_candidate_action_conflict",
    "safe_action_disagreement",
    "safe_with_punishment",
    "safe_with_severe_reason_code",
    "ambiguous_action_disagreement",
    "self_harm_disclosure_punished",
    "safe_with_self_harm_directive",
    "actual_slur_reason_label_disagreement",
    "staff_targeted_reason_label_disagreement",
    "real_world_label_with_game_cue",
    "gameplay_label_with_real_cue",
    "dm_pivot_is_target",
})
SAFETY_LABELS = frozenset({
    "REAL_WORLD_THREAT", "SELF_HARM_INSTRUCTION", "SELF_HARM_INTENT",
    "THIRD_PARTY_SELF_HARM_CONCERN", "SEXUAL_MINOR", "DOXXING",
    "BLACKMAIL", "GROOMING", "DANGEROUS_REAL_WORLD_INSTRUCTIONS",
    "HATE", "SLUR_USE", "SEVERE_HARASSMENT", "STAFF_TARGETED_ABUSE",
})
SELF_CONTACT = re.compile(r"\b(?:my (?:phone|address|email)|call me at|my number is)\b", re.I)
GROUP_KINDS = frozenset({
    "asof_exact", "target_exact", "family_id",
    "family_stem_candidate", "near_target_candidate",
})


def _source_ref(identifier: str, source_files: dict[str, str]) -> dict[str, object]:
    batch, number = identifier.split("-")
    line = int(number)
    if batch not in SOURCE_DIGESTS or batch not in source_files or not 1 <= line <= 500:
        raise ValueError("unknown or out-of-range source record")
    return {
        "source_file": source_files[batch],
        "source_sha256": SOURCE_DIGESTS[batch],
        "source_line": line,
    }


def _conflicting_actions(group: Group, by_id: dict[str, dict[str, Any]]) -> bool:
    return len({by_id[identifier].get("action") for identifier in group.example_ids}) > 1


def validate_source_order(rows: list[dict[str, Any]]) -> None:
    """Record suffix must equal its actual JSONL line before citing provenance."""
    for index, row in enumerate(rows):
        expected = f"G{10 + index // 500:02d}-{index % 500 + 1:04d}"
        if row.get("example_id") != expected:
            raise ValueError("source record order differs from example-ID line mapping")


def _group_index(
    groups: list[Group], by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, object]]], set[str]]:
    links: dict[str, list[dict[str, object]]] = defaultdict(list)
    conflicts: set[str] = set()
    for group in groups:
        if group.kind not in GROUP_KINDS or any(i not in by_id for i in group.example_ids):
            raise ValueError("unknown group kind or source ID")
        fingerprint = hashlib.sha256(
            (group.kind + ":" + "|".join(group.example_ids)).encode("utf-8")
        ).hexdigest()[:16]
        signal = {"kind": group.kind, "group_id": fingerprint,
                  "size": len(group.example_ids)}
        for identifier in group.example_ids:
            links[identifier].append(signal)
        if group.kind == "asof_exact" and _conflicting_actions(group, by_id):
            conflicts.update(group.example_ids)
    return links, conflicts


def _source_flags(
    record: dict[str, Any], visible: dict[str, object], conflicting: bool,
) -> set[str]:
    messages = visible["messages"]
    assert isinstance(messages, list)
    target = messages[visible["target_index"]]["text"]
    earlier = " ".join(message["text"] for message in messages)
    label, action = record.get("label"), record.get("action")
    flags = (
        _policy_flags(record, label, action)
        | _text_flags(label, target, earlier)
        | _reason_flags(label, set(record.get("reason_codes", [])))
    )
    if game_only_candidate(record):
        flags.add("gameplay_blackmail_scope_review")
    if str(record["example_id"]).startswith("G21-"):
        flags.add("multilingual_policy_boundary")
    if label == "SAFE" and SELF_CONTACT.search(target):
        flags.add("self_disclosed_contact_policy_boundary")
    if conflicting:
        flags.add("asof_exact_candidate_action_conflict")
    if record["target_index"] < len(record["messages"]) - 1:
        flags.add("post_target_content_excluded")
    return flags


def _priority(flags: set[str], label: str, action: str) -> str:
    if flags & POLICY_RISK:
        return "01_policy_conflict_candidate"
    if label in SAFETY_LABELS or action == "BLOCK":
        return "02_high_impact_candidate"
    return "03_stratified_audit_candidate"


def _case(
    record: dict[str, Any], source_files: dict[str, str],
    links: list[dict[str, object]], conflicting: bool,
) -> dict[str, object]:
    visible = serialize_as_of_target(record)
    flags = _source_flags(record, visible, conflicting)
    identifier = str(record["example_id"])
    return {
        "example_id": identifier,
        **_source_ref(identifier, source_files),
        "source_commit": SOURCE_COMMIT,
        "target_index": visible["target_index"],
        "candidate_semantic_label": record["label"],
        "candidate_action": record["action"],
        "triage_priority": _priority(flags, record["label"], record["action"]),
        "triage_flags": sorted(flags),
        "overlap_evidence": links,
        "label_status": "candidate_unverified",
        "review_scope": "no_owner_action_imported",
        "training_eligible": False,
    }


def _summary(
    queue: list[dict[str, object]], groups: list[Group],
) -> dict[str, object]:
    priority = Counter(str(row["triage_priority"]) for row in queue)
    flags = Counter(str(flag) for row in queue for flag in row["triage_flags"])
    candidate_actions = Counter(str(row["candidate_action"]) for row in queue)
    group_counts = Counter(group.kind for group in groups)
    return {
        "source_commit": SOURCE_COMMIT,
        "source_scope": "public_synthetic_G10_G27_only",
        "records": len(queue),
        "priority_counts": dict(sorted(priority.items())),
        "flag_counts": dict(sorted(flags.items())),
        "candidate_action_counts": dict(sorted(candidate_actions.items())),
        "overlap_group_counts": dict(sorted(group_counts.items())),
        "owner_action_decisions_imported": 0,
        "verified_records": 0,
        "training_eligible": False,
        "note": "Overlaps and flags are unverified hypotheses, not certified corrections",
    }


def build_queue(
    rows: list[dict[str, Any]], groups: list[Group],
    source_files: dict[str, str],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Every input case appears once; every case remains candidate-only."""
    by_id = {str(row["example_id"]): row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate source example IDs")
    links, conflicts = _group_index(groups, by_id)
    queue = [
        _case(row, source_files, links.get(row["example_id"], []),
              row["example_id"] in conflicts)
        for row in rows
    ]
    queue.sort(key=lambda row: (str(row["triage_priority"]), str(row["example_id"])))
    return queue, _summary(queue, groups)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator-queue-out", type=Path)
    args = parser.parse_args(argv)
    try:
        files = {
            path.name[:3]: str(path) for path in batch_files(ROOT, require_complete=True)
        }
        rows = load_candidates()
        validate_source_order(rows)
        queue, summary = build_queue(rows, find_groups(rows), files)
        if args.coordinator_queue_out is not None:
            _write_jsonl(_outside_checkout(args.coordinator_queue_out), queue)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Candidate triage refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
