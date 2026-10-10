"""Development-only threshold tradeoffs for an uncalibrated two-model blend.

Never select or certify a production threshold from these development cases.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from workers.w25.ensemble_development import (
    _blended_action,
    _load_pair,
    _summary,
    _write_once,
)
from workers.w25.metrics import wilson_lower

THRESHOLDS = (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90)


def _average_block_score(
    first: dict[str, Any], second: dict[str, Any], block_index: int,
) -> float:
    return (
        first["probabilities"]["action"][block_index]
        + second["probabilities"]["action"][block_index]
    ) / 2


def _rule_action(
    first: dict[str, Any], second: dict[str, Any],
    names: list[str], block_index: int, threshold: float,
) -> str:
    action = _blended_action(first, second, names)
    if action == "BLOCK" and _average_block_score(first, second, block_index) < threshold:
        return "REVIEW"
    return action


def _block_precision(gold: list[str], predicted: list[str]) -> dict[str, Any]:
    pairs = list(zip(gold, predicted, strict=True))
    tp = sum(g == "BLOCK" and p == "BLOCK" for g, p in pairs)
    fp = sum(g != "BLOCK" and p == "BLOCK" for g, p in pairs)
    denominator = tp + fp
    return {
        "tp": tp, "fp": fp,
        "precision": tp / denominator if denominator else None,
        "lower95": wilson_lower(tp, denominator) if denominator else None,
        "recall": tp / gold.count("BLOCK") if gold.count("BLOCK") else None,
    }


def _threshold_result(
    gold: list[str], predicted: list[str], threshold: float,
) -> dict[str, Any]:
    summary = _summary(gold, predicted)
    return {
        "threshold": threshold,
        "action_correct": summary["action_correct"],
        "wrongful_blocks_on_gold_allow": summary["wrongful_blocks"],
        "missed_blocks": summary["missed_blocks"],
        "sent_to_review": summary["sent_to_review"],
        "block": _block_precision(gold, predicted),
    }


def sweep(first: Path, second: Path) -> dict[str, Any]:
    header, left, right = _load_pair(first, second)
    classes = list(header["probability_head_value_order"]["action"])
    block_index = classes.index("BLOCK")
    gold = [str(value["gold"]["action"]) for value in left.values()]
    results = []
    for threshold in THRESHOLDS:
        predictions = [
            _rule_action(left[key], right[key], classes, block_index, threshold)
            for key in left
        ]
        results.append(_threshold_result(gold, predictions, threshold))
    return {
        "schema_version": "w25-dev-block-threshold-sweep/1",
        "cases": len(gold),
        "model_runs": [header["run_id"], "second_same_dev_input"],
        "thresholds": results,
        "policy_action_only_not_a_complete_moderation_decision": True,
        "selection_on_this_dev_set_would_require_new_unseen_validation": True,
        "not_a_production_approval": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Private development-only BLOCK threshold sweep")
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = sweep(args.first, args.second)
    _write_once(args.output, summary)
    print(json.dumps({
        "report": args.output.name,
        "cases": summary["cases"],
        "thresholds": summary["thresholds"],
        "not_production_approval": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
