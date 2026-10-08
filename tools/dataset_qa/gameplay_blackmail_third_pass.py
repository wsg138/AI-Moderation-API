"""Third-pass G10 coordinator queue; source-locked and never auto-admitted.

116 game-only candidates and 83 unscoped cases originate from a preliminary
reading of public-synthetic conversations. These are NOT independently
adjudicated labels, and the source file must remain unchanged.
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
    PINNED_SOURCE_BLOB_SHA1,
    SUGGESTED,
    _blob_sha1,
    _curated_ids,
)
from .gameplay_blackmail_second_pass import _second_pass_groups
from .gameplay_blackmail_triage import scope_bucket
from .owner_blackmail_audit import G10, _load_synthetic_g10, game_only_candidate

THIRD_PASS_GROUPS: dict[str, tuple[int, ...]] = {
    "minecraft_cheating_report_leverage": (
        40, 41, 44, 45, 51, 54, 55, 57, 58, 59, 60, 62, 63,
        64, 65, 69, 71, 72, 73, 74, 77, 80, 84, 85, 86, 87,
        88, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 101,
        103, 106,
    ),
    "minecraft_guild_plot_and_alt_leverage": (
        196, 202, 203, 209, 214, 217, 218, 220, 221, 222, 223,
        224, 225, 229, 232, 240, 241,
    ),
    "minecraft_tnt_build_and_grief_leverage": (
        243, 244, 246, 247, 248, 250, 251, 254, 255, 256,
        258, 260, 261, 262, 263, 264, 265, 266, 267, 268,
    ),
    "minecraft_alt_account_report_leverage": (
        270, 271, 272, 273, 274, 275, 277, 278, 280, 282,
        284, 285, 286, 288, 289, 290, 291, 292, 293,
    ),
    "minecraft_trade_scam_report_leverage": (
        297, 298, 299, 301, 302, 303, 304, 305, 306, 307,
        308, 309, 310, 312, 313, 314, 315, 316, 317,
    ),
    "minecraft_guild_election_leverage": (328,),
}


def _third_pass_ids() -> dict[str, str]:
    ids: dict[str, str] = {}
    for category, values in THIRD_PASS_GROUPS.items():
        for number in values:
            identifier = f"G10-{number:04d}"
            if identifier in ids:
                raise ValueError("duplicate third-pass ID")
            ids[identifier] = category
    if len(ids) != 116:
        raise ValueError("third-pass provisional set must have 116 unique IDs")
    return ids


def _third_pass_record(
    row: dict[str, Any], line: int, source_digest: str,
    groups: dict[str, str],
) -> dict[str, object]:
    projected = serialize_as_of_target(row)
    canonical = json.dumps(projected, sort_keys=True, ensure_ascii=False).encode()
    basis = groups.get(str(row["example_id"]))
    result: dict[str, object] = {
        "example_id": row["example_id"],
        "source_file": G10,
        "source_line": line,
        "source_sha256": source_digest,
        "target_index": row["target_index"],
        "visible_context_sha256": hashlib.sha256(canonical).hexdigest(),
        "preliminary_disposition": (
            "provisional_game_only" if basis else "pending_scope_review"
        ),
        "basis": basis or "insufficient_game_vs_real_world_scope",
        "review_origin": "coordinator_preliminary_screen_only",
        "independent_review": "not_received",
        "adjudicated": False,
        "training_eligible": False,
    }
    if basis:
        result["conditional_proposal"] = dict(SUGGESTED)
    return result


def _collect_weak_scope_cases(
    rows: list[dict[str, Any]], digest: str, proposed: dict[str, str],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for line, row in enumerate(rows, 1):
        if not game_only_candidate(row):
            continue
        if scope_bucket(row) == "insufficient_scope_evidence":
            output.append(_third_pass_record(row, line, digest, proposed))
    return output


def build_third_pass(raw: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Require source bytes and exact original 199-case coverage."""
    if _blob_sha1(raw) != PINNED_SOURCE_BLOB_SHA1:
        raise ValueError("G10 source bytes differ from pinned reviewed version")
    rows = _load_synthetic_g10(raw)
    proposed = _third_pass_ids()
    old = set(_curated_ids()) | set(_second_pass_groups())
    if old.intersection(proposed):
        raise ValueError("third pass overlaps earlier adjudication queues")
    digest = hashlib.sha256(raw).hexdigest()
    output = _collect_weak_scope_cases(rows, digest, proposed)
    if len(output) != 199:
        raise ValueError("third-pass count changed from 199")
    counts = Counter(str(row["preliminary_disposition"]) for row in output)
    if counts != {"provisional_game_only": 116, "pending_scope_review": 83}:
        raise ValueError("third-pass proposed/pending balance changed")
    return output, {
        "source_sha256": digest,
        "third_pass_count": len(output),
        "dispositions": dict(sorted(counts.items())),
        "total_provisional_all_passes": 100 + len(proposed),
        "pending_all_passes": 7 + 35 + counts["pending_scope_review"],
        "independent_approvals": 0,
        "training_admitted": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator-manifest-out", type=Path)
    args = parser.parse_args(argv)
    try:
        records, summary = build_third_pass((ROOT / G10).read_bytes())
        if args.coordinator_manifest_out is not None:
            _write_jsonl(_outside_checkout(args.coordinator_manifest_out), records)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"G10 third-pass verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
