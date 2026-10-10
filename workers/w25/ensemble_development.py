"""Compare fixed action-only ensemble rules on matched, private DEVELOPMENT ledgers.

This is an inexpensive exploratory analysis, not a learned policy or
production classifier. Never use sealed acceptance suites to choose rules.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any

from workers.w25.decision_analytics import (
    _private_root,
    _read_ledger,
    _validate_compatible_ledgers,
)
from workers.w25.metrics import wilson_lower, wilson_upper

SCHEMA = "w25-development-ensemble-probe/1"


def _load_pair(
    first: Path, second: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    left_header, left = _read_ledger(first)
    right_header, right = _read_ledger(second)
    _validate_compatible_ledgers([left_header, right_header], [left, right])
    if any(
        header.get("suite_name") != "development"
        for header in (left_header, right_header)
    ):
        raise ValueError("Ensemble exploration requires development-only ledgers")
    if left_header["policy_version"] != right_header["policy_version"]:
        raise ValueError("Cannot blend different policy versions")
    if left_header["probability_head_value_order"] != right_header["probability_head_value_order"]:
        raise ValueError("Different output probability class orders")
    if left_header["model_artifact_sha256"] == right_header["model_artifact_sha256"]:
        raise ValueError("Cannot call identical fitted weights an independent ensemble")
    return left_header, left, right


def _probabilities(row: dict[str, Any], size: int) -> list[float]:
    vector = row["probabilities"]["action"]
    if not isinstance(vector, list) or len(vector) != size:
        raise ValueError("Invalid action probability vector width")
    if any(
        not isinstance(value, (int, float)) or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
        for value in vector
    ):
        raise ValueError("Invalid model action probability")
    if abs(sum(vector) - 1.0) > 0.0001:
        raise ValueError("Action probability vector is not normalized")
    return vector


def _blended_action(
    left: dict[str, Any], right: dict[str, Any], classes: list[str],
) -> str:
    a = _probabilities(left, len(classes))
    b = _probabilities(right, len(classes))
    mean = [(x + y) / 2 for x, y in zip(a, b, strict=True)]
    return classes[max(range(len(classes)), key=mean.__getitem__)]


def _review_disagreements(left: dict[str, Any], right: dict[str, Any]) -> str:
    action_a = left["predicted"]["action"]
    action_b = right["predicted"]["action"]
    return str(action_a) if action_a == action_b else "REVIEW"


def _false_block_upper_bound(false_blocks: int, benign_count: int) -> float | None:
    if benign_count < 100:
        return None
    return round(1000 * wilson_upper(false_blocks, benign_count), 3)


def _summary(gold: list[str], predicted: list[str]) -> dict[str, Any]:
    correct = sum(a == b for a, b in zip(gold, predicted, strict=True))
    safe = [b for a, b in zip(gold, predicted, strict=True) if a == "ALLOW"]
    harmful = [b for a, b in zip(gold, predicted, strict=True) if a == "BLOCK"]
    false_blocks = sum(b == "BLOCK" for b in safe)
    misses = sum(b != "BLOCK" for b in harmful)
    return {
        "n": len(gold),
        "action_correct": correct,
        "action_accuracy": round(correct / len(gold), 6),
        "action_accuracy_wilson_lower95": wilson_lower(correct, len(gold)),
        "gold_allow_support": len(safe),
        "gold_block_support": len(harmful),
        "wrongful_blocks": false_blocks,
        "missed_blocks": misses,
        "sent_to_review": predicted.count("REVIEW"),
        "false_block_upper95_per_1000_benign": _false_block_upper_bound(
            false_blocks, len(safe)
        ),
        "confusion": dict(sorted(Counter(
            a + " -> " + b for a, b in zip(gold, predicted, strict=True)
        ).items())),
    }


def analyze(first: Path, second: Path) -> dict[str, Any]:
    header, left, right = _load_pair(first, second)
    names = list(header["probability_head_value_order"]["action"])
    if not {"ALLOW", "BLOCK", "REVIEW"} <= set(names):
        raise ValueError("Unknown three-action policy labels")
    keys = list(left)
    gold = [str(left[key]["gold"]["action"]) for key in keys]
    baseline_a = [str(left[key]["predicted"]["action"]) for key in keys]
    baseline_b = [str(right[key]["predicted"]["action"]) for key in keys]
    blended = [_blended_action(left[key], right[key], names) for key in keys]
    review = [_review_disagreements(left[key], right[key]) for key in keys]
    return {
        "schema_version": SCHEMA,
        "suite_name": "development",
        "n": len(keys),
        "same_input_hmac_verified": True,
        "model_runs": [header["run_id"], _read_ledger(second)[0]["run_id"]],
        "results": {
            "first_model": _summary(gold, baseline_a),
            "second_model": _summary(gold, baseline_b),
            "equal_probability_average": _summary(gold, blended),
            "disagreement_to_review": _summary(gold, review),
        },
        "action_only_not_full_six_head_policy": True,
        "exploratory_not_calibrated_or_trained": True,
        "no_automatic_sanctions_or_deployment": True,
        "not_real_world_accuracy_or_acceptance_evidence": True,
    }


def _write_once(path: Path, data: dict[str, Any]) -> None:
    _private_root(path.parent)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("Ensemble report already exists") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, sort_keys=True, allow_nan=False)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare development-only action combinations")
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.first, args.second)
    _write_once(args.output, result)
    print(json.dumps({
        "saved_report": args.output.name,
        "n": result["n"],
        "results": {
            key: {metric: value for metric, value in row.items()
                  if metric in ("action_correct", "wrongful_blocks", "missed_blocks",
                                "sent_to_review")}
            for key, row in result["results"].items()
        },
        "status": "Development-only, not production accuracy",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
