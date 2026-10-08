"""Source-anchored G10 gameplay-blackmail review queue, never auto-relabel.

Rules are deliberately conservative lexical SCREENING hints. They do not
decide semantic truth or certify anyone's independent review. Input is the
fixed 500-record public synthetic G10 batch and target-time-visible context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .asof_input import serialize_as_of_target
from .blind_review import _outside_checkout, _write_jsonl
from .freshness import ROOT
from .owner_blackmail_audit import G10, _load_synthetic_g10, game_only_candidate

REAL_WORLD_RISK = re.compile(
    r"\b(?:irl|in real life|real.life|real.world|real money|dollars?|venmo|paypal|"
    r"cashapp|cash app|bank|credit card|street address|home address|phone number|"
    r"personal photos?|nudes?|instagram|snapchat|voice chat|\bvc\b|screenshots?|"
    r"private dms?|bought (?:this|your|the) account|from the store|\bstore\b|"
    r"\bvip\b|\bmvp\b|devotee|enthusiast|gift me|rank[s]? are nice)\b"
    r"|\$\s*\d+",
    re.I,
)
IN_GAME_PAYMENT = re.compile(
    r"\b(?:diamonds?|emeralds?|netherite|debris|elytra|shulker|rockets?|"
    r"pickaxe|chestplate|ingots?|mending book|iron|gold|coins?|tnt|items?)\b",
    re.I,
)
IN_GAME_ASSET = re.compile(
    r"\b(?:minecraft|base|coords|raiders?|nether|portal|vault|spawn|server|"
    r"grief|raid|farm|plot|chest|pvp|bedwars|gear|warp|loot|storage room|"
    r"shulker|world)\b",
    re.I,
)
STATUSES = {
    "gameplay_scope_confirmation": "Needs independent proof both stakes are game-only",
    "mixed_or_realworld_risk": "Possible real money, store purchase or personal disclosure",
    "insufficient_scope_evidence": "No sufficient explicit in-game payment plus asset cues",
}


def _visible_text(row: dict[str, Any]) -> str:
    projected = serialize_as_of_target(row)
    return "\n".join(str(m["text"]) for m in projected["messages"])


def scope_bucket(row: dict[str, Any]) -> str:
    """Priority hints from target-time context, not ground-truth outcomes."""
    visible = _visible_text(row)
    if REAL_WORLD_RISK.search(visible):
        return "mixed_or_realworld_risk"
    if IN_GAME_PAYMENT.search(visible) and IN_GAME_ASSET.search(visible):
        return "gameplay_scope_confirmation"
    return "insufficient_scope_evidence"


def build_queue(raw: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Build coordinator-only, source-locked review manifest for all G10 risks."""
    rows = _load_synthetic_g10(raw)
    digest = hashlib.sha256(raw).hexdigest()
    manifest: list[dict[str, object]] = []
    for line, row in enumerate(rows, 1):
        if not game_only_candidate(row):
            continue
        bucket = scope_bucket(row)
        manifest.append({
            "source_file": G10,
            "source_sha256": digest,
            "source_line": line,
            "example_id": row["example_id"],
            "target_index": row["target_index"],
            "triage_bucket": bucket,
            "status": "pending_semantic_review",
            "suggested_action_if_confirmed_game_only": "SAFE/ALLOW",
            "training_eligible": False,
        })
    breakdown = Counter(str(item["triage_bucket"]) for item in manifest)
    summary: dict[str, object] = {
        "source_file": G10,
        "source_sha256": digest,
        "records": len(rows),
        "original_blackmail_blocks": sum(
            row.get("label") == "BLACKMAIL" and row.get("action") == "BLOCK"
            for row in rows
        ),
        "review_queue_total": len(manifest),
        "priority_bucket_counts": dict(sorted(breakdown.items())),
        "all_pending": True,
        "source_changed": False,
        "training_eligible": False,
    }
    return manifest, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coordinator-manifest-out", type=Path,
        help="Optional JSONL destination outside repository; does not auto-correct labels",
    )
    args = parser.parse_args(argv)
    try:
        path = ROOT / G10
        raw = path.read_bytes()
        manifest, summary = build_queue(raw)
        if args.coordinator_manifest_out is not None:
            dest = _outside_checkout(args.coordinator_manifest_out)
            _write_jsonl(dest, manifest)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"G10 triage failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
