"""Offline development-only complementarity analysis of PRIVATE W25 ledgers.

Do not use acceptance/frozen holdouts to discover or select candidates.
An "oracle" is the best-case potential if someone knew gold labels in advance;
it is NOT an implementable selector or evidence of ensemble performance.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from workers.w25.decision_analytics import (
    _read_ledger,
    _validate_compatible_ledgers,
)

REGISTRY = Path(__file__).with_name("candidate_exploration.json")
SLICES = ("channel_profile", "domain", "difficulty")
MIN_SLICE_SUPPORT = 20


def validate_registry(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError("Unknown candidate registry version")
    baseline = set(payload["baseline_families"])
    proposed = payload["experimental_candidates"]
    combos = payload["experimental_combinations"]
    ids = [item["id"] for item in proposed]
    if len(ids) != len(set(ids)) or set(ids) & baseline:
        raise ValueError("Candidate IDs must be unique across all families")
    if any(item["status"] != "proposal" for item in proposed):
        raise ValueError("Exploratory candidates cannot be pre-approved")
    if len({item["id"] for item in combos}) != len(combos):
        raise ValueError("Duplicate experimental combination IDs")
    allowed = baseline | set(ids)
    if any(set(item["members"]) - allowed for item in combos):
        raise ValueError("Combination includes unknown model family")
    if payload["requirements"].get("locked_acceptance_never_used_for_selection") is not True:
        raise ValueError("Acceptance must remain untouched")
    return payload


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    return validate_registry(json.loads(path.read_text(encoding="utf-8")))


def _load_development(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, dict[str, Any]]]]:
    if len(paths) < 2:
        raise ValueError("At least two model-run ledgers are required")
    loaded = [_read_ledger(path) for path in paths]
    headers = [part[0] for part in loaded]
    records = [part[1] for part in loaded]
    _validate_compatible_ledgers(headers, records)
    if any(header.get("suite_name") != "development" for header in headers):
        raise ValueError("Candidate search is restricted to development-only ledgers")
    return headers, records


def _slice(rows: dict[str, dict[str, Any]], field: str, support: int) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows.values():
        buckets.setdefault(str(row[field]), []).append(row)
    return {name: _slice_result(items, support) for name, items in sorted(buckets.items())}


def _slice_result(rows: list[dict[str, Any]], support: int) -> dict[str, Any]:
    if len(rows) < support:
        return {"n": len(rows), "status": "INSUFFICIENT_SUPPORT"}
    errors = Counter(head for row in rows for head in row["head_errors"])
    risk = Counter(tag for row in rows for tag in row["risk_tags"])
    return {
        "n": len(rows),
        "status": "DESCRIPTIVE_ONLY_UNVERIFIED_GOLD",
        "full_six_head_matches": sum(bool(row["all_supervised_heads_correct"]) for row in rows),
        "action_matches": sum(row["gold"]["action"] == row["predicted"]["action"] for row in rows),
        "head_errors": dict(errors),
        "risk_errors": dict(risk),
    }


def _run_report(rows: dict[str, dict[str, Any]], support: int) -> dict[str, Any]:
    values = list(rows.values())
    return {
        "total": _slice_result(values, support),
        "by_slice": {field: _slice(rows, field, support) for field in SLICES},
    }


def _pair_report(
    left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for key in left:
        a, b = left[key], right[key]
        good_a = a["predicted"]["action"] == a["gold"]["action"]
        good_b = b["predicted"]["action"] == b["gold"]["action"]
        counts["left_only_right_action"] += int(good_a and not good_b)
        counts["right_only_right_action"] += int(good_b and not good_a)
        counts["both_wrong_action"] += int(not good_a and not good_b)
        counts["both_right_action"] += int(good_a and good_b)
        counts["action_disagreements"] += int(
            a["predicted"]["action"] != b["predicted"]["action"]
        )
    return dict(counts)


def _pairwise(
    headers: list[dict[str, Any]], records: list[dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    for i, left in enumerate(records):
        for j in range(i + 1, len(records)):
            name = headers[i]["run_id"] + "_vs_" + headers[j]["run_id"]
            pairs[name] = _pair_report(left, records[j])
    return pairs


def _oracle(records: list[dict[str, dict[str, Any]]]) -> dict[str, Any]:
    first = records[0]
    upper_bound = sum(
        any(row[key]["predicted"]["action"] == row[key]["gold"]["action"]
            for row in records)
        for key in first
    )
    return {
        "cases": len(first),
        "hypothetical_oracle_correct_actions": upper_bound,
        "hypothetical_oracle_error_count": len(first) - upper_bound,
        "not_a_real_ensemble": True,
        "requires_unavailable_gold_to_select_per_case": True,
    }


def diagnose(paths: list[Path], *, min_slice_support: int = MIN_SLICE_SUPPORT) -> dict[str, Any]:
    if min_slice_support < MIN_SLICE_SUPPORT:
        raise ValueError("Do not lower the minimum failure-slice support")
    headers, records = _load_development(paths)
    return {
        "schema_version": "w25-candidate-diagnostics/1",
        "suite_name": "development",
        "suite_fingerprint": headers[0]["suite_fingerprint"],
        "input_hmac_fingerprint": headers[0]["input_hmac_fingerprint"],
        "number_of_candidates": len(headers),
        "per_run": {
            head["run_id"]: _run_report(rows, min_slice_support)
            for head, rows in zip(headers, records, strict=True)
        },
        "pairwise_action_complementarity": _pairwise(headers, records),
        "oracle_action_ceiling": _oracle(records),
        "not_an_ensemble_accuracy_claim": True,
        "not_an_acceptance_or_deployment_authorization": True,
        "unreviewed_gold_is_not_independent_truth": True,
        "model_latency_and_cost_require_separate_measured_evidence": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore candidates without fitting any model")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("candidate-registry")
    analysis = sub.add_parser("compare-development")
    analysis.add_argument("private_ledgers", type=Path, nargs="+")
    args = parser.parse_args()
    payload = load_registry() if args.mode == "candidate-registry" else diagnose(
        args.private_ledgers
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
