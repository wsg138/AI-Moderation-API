"""Public-metadata source admission preflight for Data/Model v2.

Never reads real/private datasets and never authorizes training by itself.
Actual source rights, independent labels, privacy, and lineage require
separately verified private manifests and explicit owner approval.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REGISTRY = Path(__file__).resolve().parents[2] / "docs" / "data-v2" / "source-registry.json"
EXPECTED_SCHEMA = "data-v2-source-registry/1"
FORBIDDEN_KINDS = {"frozen_validation", "fresh_unseen_acceptance"}
FORBIDDEN_IDS = {"w20-acceptance", "w27-frozen", "real-review-heldout-v1"}


def source_blockers(source: dict[str, Any]) -> list[str]:
    """Conservatively identify metadata blockers. No blocker ≠ data approval."""
    blockers: list[str] = []
    sid = str(source.get("id", ""))
    kind = source.get("kind")

    if sid in FORBIDDEN_IDS or kind in FORBIDDEN_KINDS:
        blockers.append("protected_evaluation")
    if source.get("status") != "approved_training":
        blockers.append("not_training_approved")
    uses = source.get("use")
    if not isinstance(uses, list) or "train" not in uses:
        blockers.append("training_use_not_approved")
    exclusions = source.get("exclusions")
    if isinstance(exclusions, list) and "training" in exclusions:
        blockers.append("explicit_training_exclusion")
    privacy = source.get("privacy")
    if privacy not in {"public_synthetic", "reviewed_local_private"}:
        blockers.append("privacy_not_training_cleared")

    # Metadata evidence references are necessary but not sufficient:
    # reviewers must check signed/private authorization records separately.
    for key in ("rights_approval_ref", "privacy_approval_ref", "label_approval_ref"):
        value = source.get(key)
        if not isinstance(value, str) or not value.strip():
            blockers.append(f"missing_{key}")
    return sorted(set(blockers))


def audit_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if registry.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError("unsupported source registry schema")
    sources = registry.get("sources")
    if not isinstance(sources, list):
        raise ValueError("registry sources must be a list")

    known = registry.get("eligibility_values")
    if not isinstance(known, list):
        raise ValueError("registry must declare eligibility_values")

    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("source entries must be objects")
        sid = item.get("id")
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError("source IDs must be non-empty strings")
        if sid in seen:
            raise ValueError(f"duplicate source ID: {sid}")
        seen.add(sid)
        if item.get("status") not in known:
            raise ValueError(f"unknown eligibility status for {sid}")
        blockers = source_blockers(item)
        results.append({
            "id": sid,
            "status": item["status"],
            "metadata_preflight_pass": not blockers,
            "blockers": blockers,
        })
    return {
        "schema": EXPECTED_SCHEMA,
        "public_metadata_only": True,
        "not_an_authorization": True,
        "results": results,
        "metadata_preflight_pass_count": sum(
            bool(r["metadata_preflight_pass"]) for r in results
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--source-id", help="Print/check one named source")
    args = parser.parse_args()

    payload = json.loads(args.registry.read_text(encoding="utf-8"))
    result = audit_registry(payload)
    if args.source_id:
        matches = [r for r in result["results"] if r["id"] == args.source_id]
        if not matches:
            raise SystemExit(f"Unknown source ID: {args.source_id}")
        result["results"] = matches

    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Intentionally never returns a training/go-ahead signal. This is a
    # read-only informational structural gate, not an authorization system.


if __name__ == "__main__":
    main()
