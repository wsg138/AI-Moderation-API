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


def gold_screening(examples: list[ModerationExample]) -> list[int]:
    return [1 if item.action != "ALLOW" else 0 for item in examples]


def gold_block(examples: list[ModerationExample]) -> list[int]:
    return [1 if item.action == "BLOCK" else 0 for item in examples]


def gold_strike(examples: list[ModerationExample]) -> list[int]:
    return [1 if item.strike else 0 for item in examples]


def gold_mute(examples: list[ModerationExample]) -> list[int]:
    return [1 if item.containment == "MUTE" else 0 for item in examples]


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _confusion_counts(gold: list[int], predicted: list[int]) -> tuple[int, int, int, int]:
    pairs = list(zip(gold, predicted, strict=True))
    tp = pairs.count((1, 1))
    fp = pairs.count((0, 1))
    fn = pairs.count((1, 0))
    tn = pairs.count((0, 0))
    return tp, fp, fn, tn


def binary_metrics(gold: list[int], predicted: list[int]) -> dict[str, float | int]:
    tp, fp, fn, tn = _confusion_counts(gold, predicted)
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    return {
        "precision": precision,
        "recall": recall,
        "f1": _safe_ratio(2 * precision * recall, precision + recall),
        "false_positive_rate": _safe_ratio(fp, fp + tn),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def threshold_predictions(probabilities: Iterable[float], threshold: float) -> list[int]:
    return [1 if float(value) >= threshold else 0 for value in probabilities]


def _slice_fp_record(
    examples: list[ModerationExample],
    predicted_block: list[int],
    name: str,
) -> dict[str, float | int | None]:
    indices = [index for index, item in enumerate(examples) if slice_predicate(item, name)]
    allowed = [index for index in indices if examples[index].action != "BLOCK"]
    false_positives = sum(predicted_block[index] == 1 for index in allowed)
    rate = _safe_ratio(false_positives, len(allowed)) if allowed else None
    return {
        "n": len(indices),
        "n_gold_allow": len(allowed),
        "false_positives": false_positives,
        "false_positive_rate": rate,
    }


def important_slice_fprs(
    examples: list[ModerationExample],
    predicted_block: list[int],
) -> dict[str, dict[str, float | int | None]]:
    return {
        name: _slice_fp_record(examples, predicted_block, name) for name in IMPORTANT_BENIGN_SLICES
    }


def screening_rule_report(
    name: str,
    examples: list[ModerationExample],
    predicted: list[int],
    probabilities: list[float] | None = None,
) -> dict:
    gold = gold_screening(examples)
    report = {"name": name, **binary_metrics(gold, predicted)}
    if probabilities is not None:
        report["calibration"] = calibration_report(gold, probabilities)
    return report


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
