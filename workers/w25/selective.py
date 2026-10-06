"""Development-fitted selective decision policy for W25 candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from workers.w12.dataset import (
    ACTION_TO_ID,
    CONTAINMENT_TO_ID,
    REVIEW_TO_ID,
    ModerationExample,
)
from workers.w25.contract import PredictionBundle
from workers.w25.metrics import binary_metrics

BLOCK_GRID = (0.70, 0.80, 0.85, 0.90, 0.95, 0.97, 0.99)
STRIKE_GRID = (0.90, 0.95, 0.97, 0.99, 0.995, 0.999)
CONTAINMENT_GRID = (0.95, 0.97, 0.99, 0.995, 0.999, 0.9995)
UNCERTAINTY_GRID = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50)


@dataclass(frozen=True)
class SelectiveThresholds:
    block: float
    strike: float
    containment: float
    uncertainty_review: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def fit_selective_thresholds(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> SelectiveThresholds:
    bundle.validate()
    if len(examples) != len(bundle.uncertainty):
        raise ValueError("threshold fitting examples do not align with predictions")
    block, uncertainty = _fit_block_policy(examples, bundle)
    strike = _fit_binary_threshold(
        [1 if example.strike else 0 for example in examples],
        [row[1] for row in bundle.probabilities["strike"]],
        STRIKE_GRID,
        target_precision=0.995,
    )
    mute_id = CONTAINMENT_TO_ID["MUTE"]
    containment = _fit_binary_threshold(
        [1 if example.containment == "MUTE" else 0 for example in examples],
        [row[mute_id] for row in bundle.probabilities["containment"]],
        CONTAINMENT_GRID,
        target_precision=0.999,
    )
    return SelectiveThresholds(block, strike, containment, uncertainty)


def apply_selective_policy(
    bundle: PredictionBundle,
    thresholds: SelectiveThresholds,
) -> tuple[PredictionBundle, list[bool]]:
    bundle.validate()
    predictions = {name: list(values) for name, values in bundle.predictions.items()}
    abstained = _apply_visibility_policy(predictions, bundle, thresholds)
    _apply_irreversible_policy(predictions, bundle, thresholds, abstained)
    result = PredictionBundle(predictions, bundle.probabilities, bundle.uncertainty)
    result.validate()
    return result, abstained


def _fit_block_policy(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> tuple[float, float]:
    gold = [int(example.action == "BLOCK") for example in examples]
    candidates = [
        _block_candidate(bundle, gold, block, uncertainty)
        for block in BLOCK_GRID
        for uncertainty in UNCERTAINTY_GRID
    ]
    return _select_block_candidate(candidates)


def _block_candidate(
    bundle: PredictionBundle,
    gold: list[int],
    block: float,
    uncertainty: float,
) -> tuple[float, float, dict[str, float | int]]:
    thresholds = SelectiveThresholds(block, 1.0, 1.0, uncertainty)
    selective, _ = apply_selective_policy(bundle, thresholds)
    predicted = [
        int(value == ACTION_TO_ID["BLOCK"])
        for value in selective.predictions["action"]
    ]
    return block, uncertainty, binary_metrics(gold, predicted)


def _select_block_candidate(
    candidates: list[tuple[float, float, dict[str, float | int]]],
) -> tuple[float, float]:
    eligible = [item for item in candidates if float(item[2]["precision"]) >= 0.99]
    if not eligible:
        return 1.0, min(UNCERTAINTY_GRID)
    best = max(eligible, key=_block_candidate_rank)
    return best[0], best[1]


def _block_candidate_rank(
    item: tuple[float, float, dict[str, float | int]],
) -> tuple[float, float, float]:
    return (
        float(item[2]["recall"]),
        -float(item[2]["false_positive_rate"]),
        -item[0],
    )


def _fit_binary_threshold(
    gold: list[int],
    probabilities: list[float],
    grid: tuple[float, ...],
    *,
    target_precision: float,
) -> float:
    candidates = []
    for threshold in grid:
        predicted = [1 if value >= threshold else 0 for value in probabilities]
        report = binary_metrics(gold, predicted)
        candidates.append((threshold, report))
    eligible = [item for item in candidates if float(item[1]["precision"]) >= target_precision]
    if not eligible:
        return 1.0
    best = max(eligible, key=_binary_candidate_rank)
    return best[0]


def _binary_candidate_rank(
    item: tuple[float, dict[str, float | int]],
) -> tuple[float, float, float]:
    return (
        float(item[1]["recall"]),
        -float(item[1]["false_positive_rate"]),
        -item[0],
    )


def _apply_visibility_policy(
    predictions: dict[str, list[int]],
    bundle: PredictionBundle,
    thresholds: SelectiveThresholds,
) -> list[bool]:
    block_id = ACTION_TO_ID["BLOCK"]
    review_id = ACTION_TO_ID["REVIEW"]
    normal_review_id = REVIEW_TO_ID["NORMAL"]
    abstained = []
    for index, action in enumerate(predictions["action"]):
        block_probability = bundle.probabilities["action"][index][block_id]
        uncertain = bundle.uncertainty[index] >= thresholds.uncertainty_review
        weak_block = action == block_id and block_probability < thresholds.block
        should_review = uncertain or weak_block
        abstained.append(should_review)
        if should_review:
            predictions["action"][index] = review_id
            predictions["review_priority"][index] = max(
                predictions["review_priority"][index],
                normal_review_id,
            )
    return abstained


def _apply_irreversible_policy(
    predictions: dict[str, list[int]],
    bundle: PredictionBundle,
    thresholds: SelectiveThresholds,
    abstained: list[bool],
) -> None:
    mute_id = CONTAINMENT_TO_ID["MUTE"]
    none_id = CONTAINMENT_TO_ID["NONE"]
    block_id = ACTION_TO_ID["BLOCK"]
    for index, did_abstain in enumerate(abstained):
        block_selected = predictions["action"][index] == block_id
        strike_probability = bundle.probabilities["strike"][index][1]
        mute_probability = bundle.probabilities["containment"][index][mute_id]
        predictions["strike"][index] = int(
            block_selected
            and not did_abstain
            and strike_probability >= thresholds.strike
        )
        predictions["containment"][index] = (
            mute_id
            if block_selected
            and not did_abstain
            and mute_probability >= thresholds.containment
            else none_id
        )
