"""Common W25 evaluator for all candidate architectures."""

from __future__ import annotations

import hashlib

from workers.w12.dataset import ACTION_TO_ID, CONTAINMENT_TO_ID, ModerationExample
from workers.w12.evaluate import evaluate_predictions
from workers.w25.config import PREVALENCE_LEVELS
from workers.w25.contract import PredictionBundle
from workers.w25.failures import grouped_visibility_failures
from workers.w25.metrics import (
    base_rate_table,
    binary_metrics,
    calibration_metrics,
    risk_coverage_curve,
)


def evaluate_candidate(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict[str, object]:
    bundle.validate()
    report = _full_multihead_report(examples, bundle)
    consequences = {
        "review": _review_report(examples, bundle),
        "block": _block_report(examples, bundle),
        "strike": _strike_report(examples, bundle),
        "containment": _containment_report(examples, bundle),
    }
    report["suite"] = {
        "n": len(examples),
        "fingerprint": suite_fingerprint(examples),
    }
    report["consequences"] = consequences
    report["visibility_failures"] = grouped_visibility_failures(examples, bundle)
    report["base_rate_block_precision"] = base_rate_table(
        recall=_numeric(consequences["block"], "recall"),
        false_positive_rate=_numeric(consequences["block"], "false_positive_rate"),
        prevalences=PREVALENCE_LEVELS,
    )
    report["risk_coverage"] = _risk_coverage(examples, bundle)
    # A training operator can require a private, immutable per-case ledger for
    # every result produced by this common evaluator. Missing/failed capture
    # must fail the run, never silently emit an unaudited success report.
    from workers.w25.decision_analytics import capture_if_required

    capture_if_required(examples, bundle)
    return report


def suite_fingerprint(examples: list[ModerationExample]) -> str:
    """Hash ordered IDs and gold policy outputs so candidate suites are comparable."""
    digest = hashlib.sha256()
    for item in examples:
        fields = (
            item.example_id,
            item.label,
            item.action,
            item.review_priority,
            "1" if item.strike else "0",
            item.containment,
            item.support_flow,
        )
        digest.update("\x1f".join(fields).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _full_multihead_report(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict[str, object]:
    block_probability = [
        row[ACTION_TO_ID["BLOCK"]] for row in bundle.probabilities["action"]
    ]
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


def _block_report(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict[str, object]:
    gold = [1 if item.action == "BLOCK" else 0 for item in examples]
    predicted = [
        1 if value == ACTION_TO_ID["BLOCK"] else 0
        for value in bundle.predictions["action"]
    ]
    probability = [row[ACTION_TO_ID["BLOCK"]] for row in bundle.probabilities["action"]]
    return _with_calibration(gold, predicted, probability)


def _strike_report(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict[str, object]:
    gold = [1 if item.strike else 0 for item in examples]
    predicted = list(bundle.predictions["strike"])
    probability = [row[1] for row in bundle.probabilities["strike"]]
    return _with_calibration(gold, predicted, probability)


def _containment_report(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict[str, object]:
    mute_id = CONTAINMENT_TO_ID["MUTE"]
    gold = [1 if item.containment == "MUTE" else 0 for item in examples]
    predicted = [
        1 if value == mute_id else 0
        for value in bundle.predictions["containment"]
    ]
    probability = [row[mute_id] for row in bundle.probabilities["containment"]]
    return _with_calibration(gold, predicted, probability)


def _review_report(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict[str, object]:
    review_id = ACTION_TO_ID["REVIEW"]
    gold = [
        1 if item.action == "REVIEW" or item.review_priority != "NONE" else 0
        for item in examples
    ]
    predicted = [
        1 if value == review_id or bundle.predictions["review_priority"][index] != 0 else 0
        for index, value in enumerate(bundle.predictions["action"])
    ]
    probability = [
        max(row[review_id], 1.0 - bundle.probabilities["review_priority"][index][0])
        for index, row in enumerate(bundle.probabilities["action"])
    ]
    return _with_calibration(gold, predicted, probability)


def _with_calibration(
    gold: list[int],
    predicted: list[int],
    probability: list[float],
) -> dict[str, object]:
    report: dict[str, object] = dict(binary_metrics(gold, predicted))
    report["calibration"] = calibration_metrics(gold, probability)
    return report


def _numeric(report: dict[str, object], key: str) -> float:
    value = report.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _risk_coverage(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> list[dict[str, float]]:
    correct = [
        bundle.predictions["action"][index] == ACTION_TO_ID[item.action]
        for index, item in enumerate(examples)
    ]
    return risk_coverage_curve(correct, bundle.uncertainty)
