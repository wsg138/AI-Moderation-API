"""Common W25 multi-head output contract and public allowlisting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from workers.w12.dataset import (
    ACTIONS,
    CONTAINMENTS,
    LABELS,
    REVIEW_PRIORITIES,
    SUPPORT_FLOWS,
)

HEAD_VALUES = {
    "label": tuple(LABELS),
    "action": tuple(ACTIONS),
    "review_priority": tuple(REVIEW_PRIORITIES),
    "strike": ("false", "true"),
    "containment": tuple(CONTAINMENTS),
    "support_flow": tuple(SUPPORT_FLOWS),
}
HEAD_NAMES = tuple(HEAD_VALUES)


@dataclass(frozen=True)
class PredictionBundle:
    predictions: dict[str, list[int]]
    probabilities: dict[str, list[list[float]]]
    uncertainty: list[float]

    def validate(self) -> None:
        _require_exact_heads(self.predictions)
        _require_exact_heads(self.probabilities)
        count = _prediction_count(self.predictions)
        if len(self.uncertainty) != count:
            raise ValueError("uncertainty length does not match predictions")
        for value in self.uncertainty:
            if not 0.0 <= value <= 1.0:
                raise ValueError("uncertainty must be in [0, 1]")
        _validate_heads(self.predictions, self.probabilities, count)


def _require_exact_heads(values: Mapping[str, object]) -> None:
    if set(values) != set(HEAD_NAMES):
        raise ValueError(f"expected exactly heads {HEAD_NAMES}")


def _prediction_count(predictions: dict[str, list[int]]) -> int:
    sizes = {len(values) for values in predictions.values()}
    if len(sizes) != 1:
        raise ValueError("prediction heads have different lengths")
    return sizes.pop() if sizes else 0


def _validate_heads(
    predictions: dict[str, list[int]],
    probabilities: dict[str, list[list[float]]],
    count: int,
) -> None:
    for head in HEAD_NAMES:
        class_count = len(HEAD_VALUES[head])
        if len(probabilities[head]) != count:
            raise ValueError(f"{head} probability length mismatch")
        for predicted, row in zip(predictions[head], probabilities[head], strict=True):
            if not 0 <= predicted < class_count:
                raise ValueError(f"{head} prediction outside class range")
            _validate_probability_row(head, row, class_count)


def _validate_probability_row(head: str, row: list[float], class_count: int) -> None:
    if len(row) != class_count:
        raise ValueError(f"{head} probability width mismatch")
    if any(value < 0.0 or value > 1.0 for value in row):
        raise ValueError(f"{head} probability outside [0, 1]")
    if abs(sum(row) - 1.0) > 1e-4:
        raise ValueError(f"{head} probabilities do not sum to one")


def public_prediction_record(
    *,
    candidate: str,
    seed: int,
    bundle: PredictionBundle,
    index: int,
    abstained: bool,
) -> dict[str, object]:
    """Return only the explicit experiment-facing output allowlist."""
    bundle.validate()
    predictions = bundle.predictions
    confidence = max(bundle.probabilities["action"][index])
    return {
        "candidate": candidate,
        "seed": seed,
        "semantic_label": HEAD_VALUES["label"][predictions["label"][index]],
        "message_action": HEAD_VALUES["action"][predictions["action"][index]],
        "review_priority": HEAD_VALUES["review_priority"][
            predictions["review_priority"][index]
        ],
        "strike_recommendation": bool(predictions["strike"][index]),
        "containment": HEAD_VALUES["containment"][predictions["containment"][index]],
        "support_flow": HEAD_VALUES["support_flow"][predictions["support_flow"][index]],
        "confidence": confidence,
        "uncertainty": bundle.uncertainty[index],
        "abstained": abstained,
    }
