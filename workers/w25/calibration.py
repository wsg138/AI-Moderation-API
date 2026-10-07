"""Leakage-safe scalar temperature calibration for W25 heads."""

from __future__ import annotations

import math

from workers.w12.dataset import (
    ACTION_TO_ID,
    CONTAINMENT_TO_ID,
    LABEL_TO_ID,
    REVIEW_TO_ID,
    SUPPORT_TO_ID,
    ModerationExample,
)
from workers.w25.contract import HEAD_NAMES, PredictionBundle


def fit_temperature(
    logits: list[list[float]],
    gold: list[int],
    *,
    minimum: float = 0.5,
    maximum: float = 3.0,
    step: float = 0.05,
) -> float:
    if len(logits) != len(gold) or not logits:
        raise ValueError("temperature fitting requires equal non-empty arrays")
    candidates = _temperature_grid(minimum, maximum, step)
    return min(candidates, key=lambda value: _nll(logits, gold, value))


def apply_temperature(logits: list[list[float]], temperature: float) -> list[list[float]]:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    return [_softmax([value / temperature for value in row]) for row in logits]


def calibrate_bundle(
    bundle: PredictionBundle,
    examples: list[ModerationExample],
) -> tuple[PredictionBundle, dict[str, float]]:
    bundle.validate()
    if len(bundle.uncertainty) != len(examples):
        raise ValueError("calibration examples do not align with predictions")
    gold = _gold_by_head(examples)
    temperatures = {}
    calibrated = {}
    for head in HEAD_NAMES:
        logits = [
            [math.log(max(value, 1e-12)) for value in row]
            for row in bundle.probabilities[head]
        ]
        temperature = fit_temperature(logits, gold[head])
        temperatures[head] = temperature
        calibrated[head] = apply_temperature(logits, temperature)
    return _bundle_from_probabilities(calibrated), temperatures


def apply_bundle_temperatures(
    bundle: PredictionBundle,
    temperatures: dict[str, float],
) -> PredictionBundle:
    bundle.validate()
    if set(temperatures) != set(HEAD_NAMES):
        raise ValueError("frozen temperatures must cover every W25 head")
    calibrated = {}
    for head in HEAD_NAMES:
        logits = [
            [math.log(max(value, 1e-12)) for value in row]
            for row in bundle.probabilities[head]
        ]
        calibrated[head] = apply_temperature(logits, temperatures[head])
    return _bundle_from_probabilities(calibrated)


def _bundle_from_probabilities(
    probabilities: dict[str, list[list[float]]],
) -> PredictionBundle:
    predictions = {
        head: [max(range(len(row)), key=row.__getitem__) for row in rows]
        for head, rows in probabilities.items()
    }
    uncertainty = [1.0 - max(row) for row in probabilities["action"]]
    result = PredictionBundle(predictions, probabilities, uncertainty)
    result.validate()
    return result


def _gold_by_head(examples: list[ModerationExample]) -> dict[str, list[int]]:
    return {
        "label": [LABEL_TO_ID[item.label] for item in examples],
        "action": [ACTION_TO_ID[item.action] for item in examples],
        "review_priority": [REVIEW_TO_ID[item.review_priority] for item in examples],
        "strike": [1 if item.strike else 0 for item in examples],
        "containment": [CONTAINMENT_TO_ID[item.containment] for item in examples],
        "support_flow": [SUPPORT_TO_ID[item.support_flow] for item in examples],
    }


def _temperature_grid(minimum: float, maximum: float, step: float) -> list[float]:
    if minimum <= 0 or maximum < minimum or step <= 0:
        raise ValueError("invalid temperature grid")
    count = int(round((maximum - minimum) / step))
    return [minimum + index * step for index in range(count + 1)]


def _nll(logits: list[list[float]], gold: list[int], temperature: float) -> float:
    losses = []
    for row, expected in zip(logits, gold, strict=True):
        probabilities = _softmax([value / temperature for value in row])
        if not 0 <= expected < len(probabilities):
            raise ValueError("gold class outside logits range")
        losses.append(-math.log(max(probabilities[expected], 1e-12)))
    return sum(losses) / len(losses)


def _softmax(values: list[float]) -> list[float]:
    maximum = max(values)
    exponentials = [math.exp(value - maximum) for value in values]
    denominator = sum(exponentials)
    return [value / denominator for value in exponentials]
