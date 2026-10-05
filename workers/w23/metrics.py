"""Metrics for W23 base models, decision rules, and paired error overlap."""

from __future__ import annotations

from collections.abc import Iterable

from workers.w12.dataset import (
    ACTION_TO_ID,
    CONTAINMENT_TO_ID,
    ModerationExample,
)
from workers.w12.evaluate import calibration_report, evaluate_predictions, slice_predicate
from workers.w23.config import IMPORTANT_BENIGN_SLICES
from workers.w23.modeling import PredictionBundle


def gold_block(examples: list[ModerationExample]) -> list[int]:
    return [1 if item.action == "BLOCK" else 0 for item in examples]


def gold_strike(examples: list[ModerationExample]) -> list[int]:
    return [1 if item.strike else 0 for item in examples]


def gold_mute(examples: list[ModerationExample]) -> list[int]:
    return [1 if item.containment == "MUTE" else 0 for item in examples]


def binary_metrics(gold: list[int], predicted: list[int]) -> dict[str, float | int]:
    tp = sum(
        expected == 1 and actual == 1 for expected, actual in zip(gold, predicted, strict=True)
    )
    fp = sum(
        expected == 0 and actual == 1 for expected, actual in zip(gold, predicted, strict=True)
    )
    fn = sum(
        expected == 1 and actual == 0 for expected, actual in zip(gold, predicted, strict=True)
    )
    tn = len(gold) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def threshold_predictions(probabilities: Iterable[float], threshold: float) -> list[int]:
    return [1 if float(value) >= threshold else 0 for value in probabilities]


def important_slice_fprs(
    examples: list[ModerationExample],
    predicted_block: list[int],
) -> dict[str, dict[str, float | int | None]]:
    result = {}
    for name in IMPORTANT_BENIGN_SLICES:
        indices = [index for index, item in enumerate(examples) if slice_predicate(item, name)]
        allowed = [index for index in indices if examples[index].action != "BLOCK"]
        false_positives = [index for index in allowed if predicted_block[index] == 1]
        result[name] = {
            "n": len(indices),
            "n_gold_allow": len(allowed),
            "false_positives": len(false_positives),
            "false_positive_rate": len(false_positives) / len(allowed) if allowed else None,
        }
    return result


def decision_rule_report(
    name: str,
    examples: list[ModerationExample],
    predicted: list[int],
    probabilities: list[float] | None = None,
) -> dict:
    report = {
        "name": name,
        **binary_metrics(gold_block(examples), predicted),
        "important_benign_slices": important_slice_fprs(examples, predicted),
    }
    if probabilities is not None:
        report["calibration"] = calibration_report(gold_block(examples), probabilities)
    return report


def strike_rule_report(
    name: str,
    examples: list[ModerationExample],
    predicted: list[int],
) -> dict:
    return {"name": name, **binary_metrics(gold_strike(examples), predicted)}


def mute_rule_report(
    name: str,
    examples: list[ModerationExample],
    predicted: list[int],
) -> dict:
    return {"name": name, **binary_metrics(gold_mute(examples), predicted)}


def full_bundle_report(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict:
    block_probability = bundle.probabilities["action"][:, ACTION_TO_ID["BLOCK"]].tolist()
    return evaluate_predictions(
        examples,
        bundle.predictions["label"],
        bundle.predictions["action"],
        bundle.predictions["review_priority"],
        bundle.predictions["strike"],
        bundle.predictions["containment"],
        bundle.predictions["support_flow"],
        block_probability,
    )


def binary_from_bundle(bundle: PredictionBundle, head: str, positive_id: int) -> list[int]:
    return [1 if value == positive_id else 0 for value in bundle.predictions[head]]


def block_from_bundle(bundle: PredictionBundle) -> list[int]:
    return binary_from_bundle(bundle, "action", ACTION_TO_ID["BLOCK"])


def mute_from_bundle(bundle: PredictionBundle) -> list[int]:
    return binary_from_bundle(bundle, "containment", CONTAINMENT_TO_ID["MUTE"])


def _error_indices(
    gold: list[int],
    predicted: list[int],
    expected_gold: int,
    expected_prediction: int,
) -> set[int]:
    return {
        index
        for index, (actual_gold, actual_prediction) in enumerate(zip(gold, predicted, strict=True))
        if actual_gold == expected_gold and actual_prediction == expected_prediction
    }


def paired_error_overlap(
    examples: list[ModerationExample],
    left: list[int],
    right: list[int],
) -> dict:
    gold = gold_block(examples)
    left_fp = _error_indices(gold, left, 0, 1)
    right_fp = _error_indices(gold, right, 0, 1)
    left_fn = _error_indices(gold, left, 1, 0)
    right_fn = _error_indices(gold, right, 1, 0)
    return {
        "false_positives": _overlap_record(examples, left_fp, right_fp),
        "false_negatives": _overlap_record(examples, left_fn, right_fn),
    }


def _overlap_record(
    examples: list[ModerationExample],
    left: set[int],
    right: set[int],
) -> dict:
    shared = left & right
    return {
        "left": len(left),
        "right": len(right),
        "intersection": len(shared),
        "union": len(left | right),
        "left_only": len(left - right),
        "right_only": len(right - left),
        "intersection_example_ids": [examples[index].example_id for index in sorted(shared)[:20]],
    }
