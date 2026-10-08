"""Second-pass G10 review of 21 strong-cue and 35 mixed-risk synthetic cases.

No independent labels are fabricated. The 14 additional game-only proposals
remain provisional and the 42 other cases stay pending. No source edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .asof_input import serialize_as_of_target
from .blind_review import _outside_checkout, _write_jsonl
from .freshness import ROOT
from .gameplay_blackmail_proposals import (
    GROUPS,
    PINNED_SOURCE_BLOB_SHA1,
    _blob_sha1,
)
from .gameplay_blackmail_triage import scope_bucket
from .owner_blackmail_audit import G10, _load_synthetic_g10, game_only_candidate

# Exactly seven of the original 21 need more context. No ALLOW suggestion.
UNCLEAR_STRONG = (47, 144, 161, 279, 311, 324, 380)
# Original 35 mixed-risk cases, organized by why a game-only exemption
# cannot safely be concluded from the target-time context.
MIXED_REVIEW: dict[str, tuple[int, ...]] = {
    "personal_voice_chat_exposure": (136, 137, 141, 149, 165),
    "account_purchase_disclosure": (148, 157, 166),
    "possibly_real_money_server_rank_purchase": (
        195, 197, 198, 199, 200, 201, 204, 206,
        207, 208, 210, 211, 212, 213, 215, 216,
    ),
    "unscoped_screenshots_or_voice_disclosure": (
        319, 321, 322, 323, 325, 326, 331, 333, 334, 346, 355,
    ),
}
NEW_GROUPS = (
    "minecraft_cheating_report_leverage",
    "minecraft_account_rule_leverage",
    "minecraft_griefing_or_base_location_leverage",
)


def _id(number: int) -> str:
    return f"G10-{number:04d}"


def _second_pass_groups() -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for name in NEW_GROUPS:
        for start, stop in GROUPS[name]:
            for number in range(start, stop + 1):
                result[_id(number)] = ("provisional_game_only", name)
    for number in UNCLEAR_STRONG:
        result[_id(number)] = ("pending_unclear", "scope_not_proven")
    for name, numbers in MIXED_REVIEW.items():
        for number in numbers:
            result[_id(number)] = ("pending_mixed_or_irl", name)
    if len(result) != 56:
        raise ValueError("second-pass case IDs overlap or are incomplete")
    return result


def _entry(
    row: dict[str, Any], line: int, source_digest: str,
    disposition: str, basis: str,
) -> dict[str, object]:
    if not game_only_candidate(row):
        raise ValueError(f"{row['example_id']}: no longer in source-tagged queue")
    want_bucket = (
        "mixed_or_realworld_risk" if disposition == "pending_mixed_or_irl"
        else "gameplay_scope_confirmation"
    )
    if scope_bucket(row) != want_bucket:
        raise ValueError(f"{row['example_id']}: triage classification changed")
    projected = serialize_as_of_target(row)
    canonical = json.dumps(projected, sort_keys=True, ensure_ascii=False).encode()
    return {
        "example_id": row["example_id"],
        "source_file": G10,
        "source_line": line,
        "source_sha256": source_digest,
        "visible_context_sha256": hashlib.sha256(canonical).hexdigest(),
        "disposition": disposition,
        "reason_for_review": basis,
        "review_origin": "coordinator_preliminary_screen_only",
        "independent_review": "not_received",
        "adjudicated": False,
        "training_eligible": False,
    }


def build_second_pass(raw: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    if _blob_sha1(raw) != PINNED_SOURCE_BLOB_SHA1:
        raise ValueError("source bytes changed from frozen G10 snapshot")
    rows = _load_synthetic_g10(raw)
    group_map = _second_pass_groups()
    digest = hashlib.sha256(raw).hexdigest()
    decisions: list[dict[str, object]] = []
    for line, row in enumerate(rows, start=1):
        reference = group_map.get(str(row.get("example_id")))
        if reference is not None:
            disposition, basis = reference
            decisions.append(_entry(row, line, digest, disposition, basis))
    if len(decisions) != len(group_map):
        raise ValueError("not all 56 G10 second-pass rows were found")
    counts = Counter(str(row["disposition"]) for row in decisions)
    return decisions, {
        "source_file": G10,
        "source_sha256": digest,
        "second_pass_total": len(decisions),
        "disposition_counts": dict(sorted(counts.items())),
        "independently_verified": 0,
        "approved_corrections": 0,
        "training_admitted": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator-second-pass-out", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest, summary = build_second_pass((ROOT / G10).read_bytes())
        if args.coordinator_second_pass_out is not None:
            _write_jsonl(_outside_checkout(args.coordinator_second_pass_out), manifest)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"G10 second-pass review failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
