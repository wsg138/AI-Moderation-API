"""Development-only six-head equal-probability diagnostic, never an enforcement policy."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from workers.w25.ensemble_development import _load_pair, _write_once
from workers.w25.metrics import wilson_lower

CRITICAL = (
    "REAL_WORLD_THREAT", "SELF_HARM_INSTRUCTION", "SLUR_USE",
    "SEXUAL_MINOR", "DOXXING", "GROOMING",
)


def _distribution(values: object, head: str, count: int) -> list[float]:
    if not isinstance(values, list) or len(values) != count:
        raise ValueError("Invalid probability width for " + head)
    if any(not isinstance(v, (int, float)) or not math.isfinite(v)
           or not 0 <= v <= 1 for v in values):
        raise ValueError("Nonfinite model probability in " + head)
    return values


def _mean_choice(
    left: dict[str, Any], right: dict[str, Any],
    head: str, classes: list[str],
) -> object:
    a = _distribution(left["probabilities"][head], head, len(classes))
    b = _distribution(right["probabilities"][head], head, len(classes))
    averages = [(x + y) / 2 for x, y in zip(a, b, strict=True)]
    choice = classes[max(range(len(classes)), key=averages.__getitem__)]
    return choice == "true" if head == "strike" else choice


def _blend(
    left: dict[str, Any], right: dict[str, Any], heads: dict[str, list[str]],
) -> dict[str, object]:
    return {
        head: _mean_choice(left, right, head, classes)
        for head, classes in heads.items()
    }


def _critical(rows: list[dict[str, Any]], decisions: list[dict[str, object]]) -> dict[str, Any]:
    report = {}
    for label in CRITICAL:
        indices = [
            i for i, row in enumerate(rows)
            if row["gold"]["label"] == label and row["gold"]["action"] == "BLOCK"
        ]
        correct = sum(decisions[i]["action"] == "BLOCK" for i in indices)
        report[label] = {
            "gold_block_support": len(indices),
            "correctly_blocked": correct,
            "lower95_recall": wilson_lower(correct, len(indices)) if indices else None,
            "insufficient_support_under_80": len(indices) < 80,
        }
    return report


def _six_head_stats(
    rows: list[dict[str, Any]], decisions: list[dict[str, object]],
) -> dict[str, Any]:
    total = len(rows)
    head_errors: Counter[str] = Counter()
    all_correct = 0
    false_strikes = 0
    false_mutes = 0
    contradictions = 0
    for row, decision in zip(rows, decisions, strict=True):
        wrong = [head for head, value in decision.items() if value != row["gold"][head]]
        head_errors.update(wrong)
        all_correct += int(not wrong)
        false_strikes += int(decision["strike"] is True and row["gold"]["strike"] is False)
        false_mutes += int(
            decision["containment"] == "MUTE" and row["gold"]["containment"] != "MUTE"
        )
        contradictions += int(
            decision["action"] == "ALLOW"
            and (decision["strike"] is True or decision["containment"] == "MUTE")
        )
    return {
        "n": total,
        "six_head_exact": all_correct,
        "six_head_accuracy": round(all_correct / total, 6),
        "six_head_accuracy_lower95": wilson_lower(all_correct, total),
        "head_errors": dict(head_errors),
        "false_strike_recommendations": false_strikes,
        "false_mute_recommendations": false_mutes,
        "allow_with_punitive_head": contradictions,
        "not_seven_field_complete_duration_missing": True,
    }


def _block_rates(
    rows: list[dict[str, Any]], decisions: list[dict[str, object]],
) -> dict[str, Any]:
    gold = [row["gold"]["action"] for row in rows]
    predicted = [out["action"] for out in decisions]
    tp = sum(g == "BLOCK" and p == "BLOCK" for g, p in zip(gold, predicted, strict=True))
    fp = sum(g != "BLOCK" and p == "BLOCK" for g, p in zip(gold, predicted, strict=True))
    targets = gold.count("BLOCK")
    return {
        "block_tp": tp, "block_fp": fp, "block_fn": targets - tp,
        "block_precision": tp / (tp + fp) if tp + fp else None,
        "block_recall": tp / targets if targets else None,
        "block_precision_lower95": wilson_lower(tp, tp + fp) if tp + fp else None,
        "block_recall_lower95": wilson_lower(tp, targets) if targets else None,
    }


def _guard_allow_punitive_heads(decision: dict[str, object]) -> dict[str, object]:
    """A permitted message must not independently propose strike/mute."""
    safe = dict(decision)
    if safe["action"] == "ALLOW":
        safe["strike"] = False
        safe["containment"] = "NONE"
    return safe


def analyze_full(first: Path, second: Path) -> dict[str, Any]:
    header, left, right = _load_pair(first, second)
    order = header["probability_head_value_order"]
    rows = list(left.values())
    mixed = [_blend(left[key], right[key], order) for key in left]
    guarded = [_guard_allow_punitive_heads(item) for item in mixed]
    return {
        "schema_version": "w25-development-full-head-blend/1",
        "n": len(rows),
        "decision_stage": "equal_probabilities_all_six_heads_no_policy_postprocessing",
        "model_runs": [header["run_id"], "second_saved_development_run"],
        "block": _block_rates(rows, mixed),
        "full_heads": _six_head_stats(rows, mixed),
        "guarded_full_heads": _six_head_stats(rows, guarded),
        "critical_action_recall": _critical(rows, mixed),
        "neither_trained_nor_policy_verified": True,
        "not_a_deployment_or_99pct_acceptance_result": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a full six-head development mix")
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    outcome = analyze_full(args.first, args.second)
    _write_once(args.output, outcome)
    print(json.dumps({
        "status": "Private diagnostic, not deployable",
        "cases": outcome["n"],
        "six_head_exact": outcome["full_heads"]["six_head_exact"],
        "block": outcome["block"],
        "false_strikes": outcome["full_heads"]["false_strike_recommendations"],
        "false_mutes": outcome["full_heads"]["false_mute_recommendations"],
        "contradictions": outcome["full_heads"]["allow_with_punitive_head"],
        "guarded_contradictions": outcome["guarded_full_heads"]["allow_with_punitive_head"],
        "guarded_six_head_exact": outcome["guarded_full_heads"]["six_head_exact"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
