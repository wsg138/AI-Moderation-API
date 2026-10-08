"""Read-only triage of G10 labels under the owner's gameplay-blackmail rule.

The reason codes are original UNVERIFIED synthetic annotations. Counts are
review queue hints, never adjudication or permission to relabel candidates.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .freshness import ROOT

G10 = "G10-blackmail-extortion.jsonl"


def game_only_candidate(row: dict[str, Any]) -> bool:
    """Find blocked cases tagged game-only by the existing source metadata."""
    reasons = row.get("reason_codes", [])
    return (
        row.get("label") == "BLACKMAIL"
        and row.get("action") == "BLOCK"
        and isinstance(reasons, list)
        and "minecraft_gameplay_explicit" in reasons
        and "explicit_real_world_cue" not in reasons
    )


def _load_synthetic_g10(source: bytes) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in source.decode("utf-8").splitlines()]
    if len(rows) != 500 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("expected complete 500-record G10 synthetic batch")
    if any(row.get("source") != "synthetic" for row in rows):
        raise ValueError("audit scope is public synthetic G10 only")
    return rows


def audit_file(path: Path) -> dict[str, object]:
    """Return aggregate candidate counts, never rewrite source or emit raw chat."""
    source = path.read_bytes()
    rows = _load_synthetic_g10(source)
    blocked = [row for row in rows if row.get("label") == "BLACKMAIL"
               and row.get("action") == "BLOCK"]
    return {
        "source_file": path.name,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "records": len(rows),
        "current_blackmail_block_count": len(blocked),
        "gameplay_tagged_no_irl_cue_review_candidates": sum(
            game_only_candidate(row) for row in blocked
        ),
        "policy": "Owner 2026-10-08: game-only blackmail ALLOW; IRL blackmail BLOCK",
        "action": "review_only_no_auto_relabels",
        "training_eligible": False,
    }


def main() -> None:
    print(json.dumps(audit_file(ROOT / G10), indent=2))


if __name__ == "__main__":
    main()
