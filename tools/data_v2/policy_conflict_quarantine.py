"""Source-locked, non-admitting policy reconciliation queue for synthetic moderation.

Flags are case-review hypotheses, not policy decisions or ground-truth labels.
Optional validated owner actions are private inputs, never published to stdout.
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

from .owner_action_registry import merge_action_only, validate_round4
from .private_owner_actions import _require, _source_index, read_private_ledger, validate_ledger
from .synthetic_family_audit import find_groups, load_candidates
from .triage_queue import build_queue, validate_source_order

CONTACT = re.compile(
    r"\b(?:my (?:phone|address|email)|call me at|my number is)\b", re.I
)
POTENTIAL_SAFETY = frozenset({
    "GROOMING", "DOXXING", "REAL_WORLD_THREAT", "HATE", "SLUR_USE",
    "DANGEROUS_REAL_WORLD_INSTRUCTIONS", "SEXUAL_MINOR",
    "STAFF_TARGETED_ABUSE", "SEVERE_HARASSMENT", "BLACKMAIL",
})
SELF_HARM = frozenset({
    "SELF_HARM_INTENT", "THIRD_PARTY_SELF_HARM_CONCERN", "SELF_HARM_DISCLOSURE",
})
HARASSMENT = frozenset({
    "LOW_LEVEL_HARASSMENT", "SEVERE_HARASSMENT", "HARASSMENT",
})
RECONCILIATION_PATHS = {
    "language_enforcement": "owner_rule_scope_not_versioned",
    "self_published_contact": "owner_rule_scope_not_versioned",
    "uncertain_minor_context": "policy_edge_open",
    "dangerous_domain_scope": "policy_edge_open",
    "private_sexual_boundary": "policy_edge_open",
    "real_world_threat_evidence": "apply_settled_rule_with_context",
    "third_party_private_information": "apply_settled_rule_with_context",
    "gameplay_blackmail_scope": "apply_settled_rule_with_context",
    "self_harm_safety_flow": "apply_settled_rule_with_support_separately",
    "harassment_incident_context": "apply_settled_rule_with_context",
}
REVIEWED_FIELDS = frozenset({
    "example_id", "owner_action", "owner_authority",
    "semantic_and_other_fields", "training_eligible",
})


def _asof_target(row: dict[str, Any]) -> str:
    view = serialize_as_of_target(row)
    return str(view["messages"][view["target_index"]]["text"])


def _open_policy_tracks(row: dict[str, Any], label: str, target: str) -> set[str]:
    tracks: set[str] = set()
    if str(row["example_id"]).startswith("G21-"):
        tracks.add("language_enforcement")
    if CONTACT.search(target):
        tracks.add("self_published_contact")
    if label == "GROOMING":
        tracks.add("uncertain_minor_context")
    if label == "DANGEROUS_REAL_WORLD_INSTRUCTIONS":
        tracks.add("dangerous_domain_scope")
    if label in {"SEXUAL_CONTENT", "SEXUAL_MINOR"} and "private" in row["channel_profile"]:
        tracks.add("private_sexual_boundary")
    return tracks


def _settled_policy_tracks(label: str) -> set[str]:
    tracks: set[str] = set()
    if label == "REAL_WORLD_THREAT":
        tracks.add("real_world_threat_evidence")
    if label == "DOXXING":
        tracks.add("third_party_private_information")
    if label == "BLACKMAIL":
        tracks.add("gameplay_blackmail_scope")
    if label in SELF_HARM:
        tracks.add("self_harm_safety_flow")
    if label in HARASSMENT:
        tracks.add("harassment_incident_context")
    return tracks


def policy_tracks(row: dict[str, Any]) -> list[str]:
    """Candidate-only issue routing; no language, age or intent inference."""
    label = str(row.get("label", ""))
    return sorted(
        _open_policy_tracks(row, label, _asof_target(row)) | _settled_policy_tracks(label)
    )


def _owner_index(
    actions: list[dict[str, object]], ids: set[str],
) -> dict[str, str]:
    owner: dict[str, str] = {}
    for action in actions:
        _require(REVIEWED_FIELDS.issubset(action), "incomplete owner action registry")
        identifier = action["example_id"]
        _require(isinstance(identifier, str) and identifier in ids, "unknown owner case")
        _require(identifier not in owner, "duplicate owner action case")
        _require(action["training_eligible"] is False, "unapproved training admission")
        _require(action["owner_authority"] == "message_action_only", "unverified authority")
        _require(action["semantic_and_other_fields"] == "not_adjudicated",
                 "unapproved semantic-field adjudication")
        _require(action["owner_action"] in {"ALLOW", "REVIEW", "BLOCK"},
                 "invalid owner message action")
        owner[identifier] = str(action["owner_action"])
    return owner


def _tier(owner_action: str | None, candidate: str, label: str, tracks: list[str]) -> str:
    if owner_action == "ALLOW" and candidate == "BLOCK" and label in POTENTIAL_SAFETY:
        return "01_safety_policy_conflict_review"
    if owner_action is not None and owner_action != candidate:
        return "02_owner_vs_candidate_action_review"
    if any(RECONCILIATION_PATHS[t] in {
        "owner_rule_scope_not_versioned", "policy_edge_open"
    } for t in tracks):
        return "03_unresolved_policy_boundary"
    if tracks:
        return "04_contextual_policy_application_review"
    return "05_other_unverified_candidate"


def _row(
    row: dict[str, Any], source: dict[str, object], owner: str | None,
) -> dict[str, object]:
    tracks = policy_tracks(row)
    return {
        "example_id": row["example_id"],
        "source_file": source["source_file"],
        "source_sha256": source["source_sha256"],
        "source_line": source["source_line"],
        "source_commit": source["source_commit"],
        "candidate_action_for_comparison_only": row["action"],
        "candidate_semantic_for_routing_only": row["label"],
        "owner_action_if_reviewed": owner,
        "owner_action_scope": "message_action_only" if owner else "not_reviewed",
        "priority": _tier(owner, row["action"], row["label"], tracks),
        "policy_review_tracks": tracks,
        "policy_track_state": {t: RECONCILIATION_PATHS[t] for t in tracks},
        "full_outcome_status": "quarantined_unverified",
        "training_eligible": False,
    }


def make_reconciliation(
    candidates: list[dict[str, Any]], triage: list[dict[str, object]],
    owner_actions: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Output one source-anchored private row per case, no eligible examples."""
    by_id = {str(r["example_id"]): r for r in candidates}
    source = {str(r["example_id"]): r for r in triage}
    _require(len(by_id) == len(candidates), "duplicate synthetic case IDs")
    _require(len(source) == len(triage) == len(candidates), "incomplete triage frame")
    _require(set(source) == set(by_id), "triage source IDs do not match")
    owner = _owner_index(owner_actions, set(by_id))
    output = [_row(by_id[i], source[i], owner.get(i)) for i in sorted(by_id)]
    priority = Counter(str(r["priority"]) for r in output)
    tracks = Counter(t for r in output for t in r["policy_review_tracks"])
    compared = sum(
        r["owner_action_if_reviewed"] is not None
        and r["owner_action_if_reviewed"] != r["candidate_action_for_comparison_only"]
        for r in output
    )
    return output, {
        "source_scope": "pinned_G10_G27_public_synthetic",
        "records": len(output),
        "owner_action_only_cases": len(owner),
        "owner_candidate_disagreements": compared,
        "priority_counts": dict(sorted(priority.items())),
        "policy_track_counts": dict(sorted(tracks.items())),
        "semantic_fields_adjudicated": 0,
        "training_eligible": False,
        "note": "Counts are candidate routing hypotheses, not verified policy violations",
    }


def _private_actions(round3: Path | None, round4: Path | None) -> list[dict[str, object]]:
    if round3 is None and round4 is None:
        return []
    _require(round3 is not None and round4 is not None,
             "both private reviewed rounds are required for complete accounting")
    original, blobs = _source_index()
    r3, _ = validate_ledger(read_private_ledger(_outside_checkout(round3)),
                            original, blobs)
    r4, _ = validate_round4(read_private_ledger(_outside_checkout(round4)),
                            original, blobs)
    return merge_action_only(r3, r4)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round3-ledger", type=Path)
    parser.add_argument("--round4-ledger", type=Path)
    parser.add_argument("--private-manifest-out", type=Path)
    args = parser.parse_args(argv)
    try:
        files = {p.name[:3]: str(p) for p in batch_files(ROOT, require_complete=True)}
        candidates = load_candidates()
        validate_source_order(candidates)
        triage, _ = build_queue(candidates, find_groups(candidates), files)
        actions = _private_actions(args.round3_ledger, args.round4_ledger)
        queue, summary = make_reconciliation(candidates, triage, actions)
        if args.private_manifest_out is not None:
            _write_jsonl(_outside_checkout(args.private_manifest_out), queue)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print(f"Policy reconciliation quarantine refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
