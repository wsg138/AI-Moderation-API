"""Draft OWNER-ruling correction proposals; source remains frozen, unadmitted.

These 100 synthetic examples were provisionally screened in as-of-target
context for game-only payment and game-only leverage. This is coordinator
screening, NOT independent semantic verification or certified gold truth.
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
from .gameplay_blackmail_triage import scope_bucket
from .owner_blackmail_audit import G10, _load_synthetic_g10, game_only_candidate

PINNED_SOURCE_BLOB_SHA1 = "3604b8e139892595fd280764869dc3ca1786044d"
# Inclusive source-ID intervals, manually screened against visible chat only.
# Exclude ambiguous or unspecified cheating evidence, real/store purchases, personal voice-chat,
# unspecified secrets, and otherwise underspecified mixed-stakes examples.
GROUPS: dict[str, tuple[tuple[int, int], ...]] = {
    "minecraft_base_location_leverage": (
        (1, 38), (135, 135), (338, 341), (343, 343), (348, 348),
        (350, 350), (353, 354), (359, 359), (362, 363), (369, 369),
        (372, 372), (375, 375), (377, 379), (384, 384),
        (387, 387), (389, 392), (495, 495), (500, 500),
    ),
    "minecraft_guild_vault_or_base_location": (
        (219, 219), (226, 228), (230, 231), (233, 239), (242, 242),
    ),
    "minecraft_build_grief_leverage": (
        (245, 245), (252, 253), (257, 257), (259, 259), (269, 269),
    ),
    "minecraft_spawn_grief_record": ((146, 146),),
    "minecraft_cheating_report_leverage": (
        (43, 43), (49, 50), (53, 53), (56, 56),
        (61, 61), (68, 68), (83, 83), (104, 104),
    ),
    "minecraft_account_rule_leverage": (
        (79, 79), (138, 138), (281, 281),
    ),
    "minecraft_griefing_or_base_location_leverage": (
        (163, 163), (381, 381),
    ),
}
SUGGESTED = {
    "semantic_label": "SAFE",
    "action": "ALLOW",
    "review_priority": "NONE",
    "strike": False,
    "containment": "NONE",
    "containment_duration_seconds": None,
    "support_flow": "NONE",
}


def _curated_ids() -> dict[str, str]:
    result: dict[str, str] = {}
    for group, ranges in GROUPS.items():
        for first, last in ranges:
            for number in range(first, last + 1):
                identifier = f"G10-{number:04d}"
                if identifier in result:
                    raise ValueError("overlapping curated examples")
                result[identifier] = group
    return result


def _blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def _case_proposal(
    row: dict[str, Any], line: int, group: str, digest: str,
) -> dict[str, object]:
    if not game_only_candidate(row):
        raise ValueError(f"{row['example_id']}: source label/scope changed")
    if scope_bucket(row) != "gameplay_scope_confirmation":
        raise ValueError(f"{row['example_id']}: source no longer clear gameplay")
    projected = serialize_as_of_target(row)
    canonical = json.dumps(projected, sort_keys=True, ensure_ascii=False).encode()
    return {
        "example_id": row["example_id"],
        "source_file": G10,
        "source_sha256": digest,
        "source_line": line,
        "target_index": row["target_index"],
        "visible_context_sha256": hashlib.sha256(canonical).hexdigest(),
        "observed_gameplay_basis": group,
        "proposal": dict(SUGGESTED),
        "review_origin": "coordinator_provisional_screen_only",
        "status": "requires_independent_policy_adjudication",
        "training_eligible": False,
    }


def build_proposals(raw: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Fail closed on source drift; never touch G10 or source outcome fields."""
    if _blob_sha1(raw) != PINNED_SOURCE_BLOB_SHA1:
        raise ValueError("source bytes changed since pinned G10 review")
    rows = _load_synthetic_g10(raw)
    wanted = _curated_ids()
    digest = hashlib.sha256(raw).hexdigest()
    result: list[dict[str, object]] = []
    for line, row in enumerate(rows, start=1):
        identifier = row.get("example_id")
        if identifier in wanted:
            result.append(_case_proposal(row, line, wanted[identifier], digest))
    if len(result) != len(wanted):
        raise ValueError("missing curated G10 example IDs")
    counts = Counter(str(row["observed_gameplay_basis"]) for row in result)
    return result, {
        "source_sha256": digest,
        "pinned_source_blob_sha1": PINNED_SOURCE_BLOB_SHA1,
        "provisional_game_only_proposals": len(result),
        "groups": dict(sorted(counts.items())),
        "finalized": 0,
        "training_admitted": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator-proposals-out", type=Path)
    args = parser.parse_args(argv)
    try:
        proposals, summary = build_proposals((ROOT / G10).read_bytes())
        if args.coordinator_proposals_out is not None:
            _write_jsonl(_outside_checkout(args.coordinator_proposals_out), proposals)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Provisional G10 proposals failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
