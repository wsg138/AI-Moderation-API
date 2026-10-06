"""Precision-first two-stage cascade decision logic."""

from __future__ import annotations

from dataclasses import dataclass

from workers.w12.dataset import (
    ACTION_TO_ID,
    CONTAINMENT_TO_ID,
    ModerationExample,
)
from workers.w25.contract import HEAD_NAMES, PredictionBundle
from workers.w25.metrics import binary_metrics

SCREEN_GRID = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50)
BLOCK_GRID = (0.80, 0.85, 0.90, 0.95, 0.97, 0.99)
STRIKE_GRID = (0.90, 0.95, 0.97, 0.99, 0.995, 0.999)
CONTAINMENT_GRID = (0.95, 0.97, 0.99, 0.995, 0.999, 0.9995)


@dataclass(frozen=True)
class CascadeThresholds:
    screen_block: float = 0.20
    screen_strike: float = 0.20
    screen_containment: float = 0.10
    uncertainty: float = 0.35
    block: float = 0.90
    strike: float = 0.97
    containment: float = 0.995


def fit_cascade_thresholds(
    examples: list[ModerationExample],
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
) -> CascadeThresholds:
    _require_same_length(stage_a, stage_b)
    if len(examples) != len(stage_a.uncertainty):
        raise ValueError("cascade threshold examples do not align with predictions")
    screen = _fit_screening_thresholds(examples, stage_a)
    block = _fit_consequence_threshold(
        examples,
        stage_a,
        stage_b,
        screen,
        consequence="block",
        grid=BLOCK_GRID,
        target_precision=0.99,
    )
    strike = _fit_consequence_threshold(
        examples,
        stage_a,
        stage_b,
        screen,
        consequence="strike",
        grid=STRIKE_GRID,
        target_precision=0.995,
        block=block,
    )
    containment = _fit_consequence_threshold(
        examples,
        stage_a,
        stage_b,
        screen,
        consequence="containment",
        grid=CONTAINMENT_GRID,
        target_precision=0.999,
        block=block,
        strike=strike,
    )
    return CascadeThresholds(
        screen_block=screen["block"],
        screen_strike=screen["strike"],
        screen_containment=screen["containment"],
        uncertainty=0.35,
        block=block,
        strike=strike,
        containment=containment,
    )


def _fit_screening_thresholds(
    examples: list[ModerationExample],
    stage_a: PredictionBundle,
) -> dict[str, float]:
    block_id = ACTION_TO_ID["BLOCK"]
    mute_id = CONTAINMENT_TO_ID["MUTE"]
    return {
        "block": _high_recall_threshold(
            [1 if item.action == "BLOCK" else 0 for item in examples],
            [row[block_id] for row in stage_a.probabilities["action"]],
        ),
        "strike": _high_recall_threshold(
            [1 if item.strike else 0 for item in examples],
            [row[1] for row in stage_a.probabilities["strike"]],
        ),
        "containment": _high_recall_threshold(
            [1 if item.containment == "MUTE" else 0 for item in examples],
            [row[mute_id] for row in stage_a.probabilities["containment"]],
        ),
    }


def _high_recall_threshold(gold: list[int], probabilities: list[float]) -> float:
    if not any(gold):
        return 1.0
    eligible = []
    for threshold in SCREEN_GRID:
        predicted = [1 if value >= threshold else 0 for value in probabilities]
        report = binary_metrics(gold, predicted)
        if float(report["recall"]) >= 0.995:
            eligible.append(threshold)
    return max(eligible) if eligible else min(SCREEN_GRID)


def _fit_consequence_threshold(
    examples: list[ModerationExample],
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
    screen: dict[str, float],
    *,
    consequence: str,
    grid: tuple[float, ...],
    target_precision: float,
    block: float = 1.0,
    strike: float = 1.0,
) -> float:
    candidates = []
    for threshold in grid:
        thresholds = _candidate_thresholds(
            screen,
            consequence,
            threshold,
            block,
            strike,
        )
        bundle, _ = combine_cascade(stage_a, stage_b, thresholds)
        report = _consequence_report(examples, bundle, consequence)
        candidates.append((threshold, report))
    eligible = [item for item in candidates if float(item[1]["precision"]) >= target_precision]
    if not eligible:
        return 1.0
    best = max(
        eligible,
        key=lambda item: (
            float(item[1]["recall"]),
            -float(item[1]["false_positive_rate"]),
            -item[0],
        ),
    )
    return best[0]


def _candidate_thresholds(
    screen: dict[str, float],
    consequence: str,
    value: float,
    block: float,
    strike: float,
) -> CascadeThresholds:
    return CascadeThresholds(
        screen_block=screen["block"],
        screen_strike=screen["strike"],
        screen_containment=screen["containment"],
        uncertainty=0.35,
        block=value if consequence == "block" else block,
        strike=value if consequence == "strike" else strike,
        containment=value if consequence == "containment" else 1.0,
    )


def _consequence_report(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
    consequence: str,
) -> dict[str, float | int]:
    if consequence == "block":
        gold = [1 if item.action == "BLOCK" else 0 for item in examples]
        predicted = [
            1 if value == ACTION_TO_ID["BLOCK"] else 0
            for value in bundle.predictions["action"]
        ]
    elif consequence == "strike":
        gold = [1 if item.strike else 0 for item in examples]
        predicted = bundle.predictions["strike"]
    else:
        mute_id = CONTAINMENT_TO_ID["MUTE"]
        gold = [1 if item.containment == "MUTE" else 0 for item in examples]
        predicted = [
            1 if value == mute_id else 0
            for value in bundle.predictions["containment"]
        ]
    return binary_metrics(gold, predicted)


def combine_cascade(
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
    thresholds: CascadeThresholds,
) -> tuple[PredictionBundle, list[bool]]:
    stage_a.validate()
    stage_b.validate()
    _require_same_length(stage_a, stage_b)
    routed = route_mask(stage_a, thresholds)
    probabilities = _combine_probabilities(stage_a, stage_b, routed)
    return finalize_cascade(
        probabilities,
        stage_a,
        stage_b,
        routed,
        thresholds,
    ), routed


def finalize_cascade(
    probabilities: dict[str, list[list[float]]],
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
    routed: list[bool],
    thresholds: CascadeThresholds,
) -> PredictionBundle:
    _require_same_length(stage_a, stage_b)
    if len(routed) != len(stage_a.uncertainty):
        raise ValueError("cascade routing mask length mismatch")
    predictions = _default_predictions(probabilities)
    _apply_action_policy(
        predictions,
        probabilities,
        stage_a,
        stage_b,
        routed,
        thresholds,
    )
    uncertainty = [1.0 - max(row) for row in probabilities["action"]]
    result = PredictionBundle(predictions, probabilities, uncertainty)
    result.validate()
    return result


def route_mask(stage_a: PredictionBundle, thresholds: CascadeThresholds) -> list[bool]:
    block_id = ACTION_TO_ID["BLOCK"]
    return [
        stage_a.probabilities["action"][index][block_id] >= thresholds.screen_block
        or stage_a.probabilities["strike"][index][1] >= thresholds.screen_strike
        or stage_a.probabilities["containment"][index][CONTAINMENT_TO_ID["MUTE"]]
        >= thresholds.screen_containment
        or stage_a.uncertainty[index] >= thresholds.uncertainty
        for index in range(len(stage_a.uncertainty))
    ]


def _combine_probabilities(
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
    routed: list[bool],
) -> dict[str, list[list[float]]]:
    combined = {name: [] for name in HEAD_NAMES}
    for index, use_verifier in enumerate(routed):
        for name in HEAD_NAMES:
            left = stage_a.probabilities[name][index]
            right = stage_b.probabilities[name][index]
            row = _blend(left, right, 0.25, 0.75) if use_verifier else list(left)
            combined[name].append(row)
    return combined


def _blend(left: list[float], right: list[float], lw: float, rw: float) -> list[float]:
    return [lw * a + rw * b for a, b in zip(left, right, strict=True)]


def _default_predictions(
    probabilities: dict[str, list[list[float]]],
) -> dict[str, list[int]]:
    return {
        name: [max(range(len(row)), key=row.__getitem__) for row in rows]
        for name, rows in probabilities.items()
    }


def _apply_action_policy(
    predictions: dict[str, list[int]],
    probabilities: dict[str, list[list[float]]],
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
    routed: list[bool],
    thresholds: CascadeThresholds,
) -> None:
    for index, use_verifier in enumerate(routed):
        if not use_verifier:
            continue
        _set_message_action(predictions, probabilities, stage_a, stage_b, index, thresholds)
        _set_irreversible_heads(predictions, stage_a, stage_b, index, thresholds)


def _set_message_action(
    predictions,
    probabilities,
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
    index: int,
    thresholds: CascadeThresholds,
) -> None:
    block_id = ACTION_TO_ID["BLOCK"]
    review_id = ACTION_TO_ID["REVIEW"]
    verifier_block = stage_b.probabilities["action"][index][block_id]
    disagreement = stage_a.predictions["action"][index] != stage_b.predictions["action"][index]
    if verifier_block >= thresholds.block:
        predictions["action"][index] = block_id
    elif disagreement:
        predictions["action"][index] = review_id
        probabilities["action"][index] = _review_distribution(
            probabilities["action"][index], review_id
        )


def _set_irreversible_heads(
    predictions,
    stage_a: PredictionBundle,
    stage_b: PredictionBundle,
    index: int,
    thresholds: CascadeThresholds,
) -> None:
    strike_ok = (
        stage_a.probabilities["strike"][index][1] >= thresholds.strike
        and stage_b.probabilities["strike"][index][1] >= thresholds.strike
    )
    mute_id = CONTAINMENT_TO_ID["MUTE"]
    mute_ok = (
        stage_a.probabilities["containment"][index][mute_id] >= thresholds.containment
        and stage_b.probabilities["containment"][index][mute_id] >= thresholds.containment
    )
    predictions["strike"][index] = 1 if strike_ok else 0
    predictions["containment"][index] = mute_id if mute_ok else CONTAINMENT_TO_ID["NONE"]


def _review_distribution(row: list[float], review_id: int) -> list[float]:
    adjusted = [value * 0.25 for value in row]
    adjusted[review_id] += 0.75
    total = sum(adjusted)
    return [value / total for value in adjusted]


def _require_same_length(left: PredictionBundle, right: PredictionBundle) -> None:
    if len(left.uncertainty) != len(right.uncertainty):
        raise ValueError("cascade stages must predict the same examples")
