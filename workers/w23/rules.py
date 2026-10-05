"""Predeclared W23 decision-rule candidates."""

from __future__ import annotations

import numpy as np  # pyright: ignore[reportMissingImports]

from workers.w12.dataset import ACTION_TO_ID, CONTAINMENT_TO_ID
from workers.w23.config import BLOCK_THRESHOLDS, SCREENING_THRESHOLDS, STRIKE_THRESHOLDS
from workers.w23.metrics import block_from_bundle, mute_from_bundle, threshold_predictions
from workers.w23.modeling import PredictionBundle


def positive_probability(
    bundle: PredictionBundle,
    head: str,
    positive_id: int,
) -> list[float]:
    return bundle.probabilities[head][:, positive_id].astype(float).tolist()


def screening_probability(bundle: PredictionBundle) -> list[float]:
    allow_id = ACTION_TO_ID["ALLOW"]
    return (1.0 - bundle.probabilities["action"][:, allow_id]).astype(float).tolist()


def block_probability(bundle: PredictionBundle) -> list[float]:
    return positive_probability(bundle, "action", ACTION_TO_ID["BLOCK"])


def strike_probability(bundle: PredictionBundle) -> list[float]:
    return positive_probability(bundle, "strike", 1)


def mute_probability(bundle: PredictionBundle) -> list[float]:
    return positive_probability(bundle, "containment", CONTAINMENT_TO_ID["MUTE"])


def _threshold_rules(
    prefix: str,
    probabilities: list[float],
    thresholds: tuple[float, ...],
) -> dict[str, list[int]]:
    return {
        f"{prefix}@{threshold:.3f}": threshold_predictions(probabilities, threshold)
        for threshold in thresholds
    }


def screening_rules(bundles: dict[str, PredictionBundle]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for name in ("word", "char", "combined", "bert", "meta"):
        probabilities = screening_probability(bundles[name])
        result.update(_threshold_rules(name, probabilities, SCREENING_THRESHOLDS))
    word = np.asarray(screening_probability(bundles["word"]))
    bert = np.asarray(screening_probability(bundles["bert"]))
    combined = np.asarray(screening_probability(bundles["combined"]))
    max_prob = np.maximum.reduce([word, bert, combined]).tolist()
    avg_prob = ((word + bert + combined) / 3.0).tolist()
    result.update(_threshold_rules("union-prob", max_prob, SCREENING_THRESHOLDS))
    result.update(_threshold_rules("average-prob", avg_prob, SCREENING_THRESHOLDS))
    return result


def block_rules(bundles: dict[str, PredictionBundle]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for name in ("word", "char", "combined", "bert", "meta"):
        result[f"{name}-argmax"] = block_from_bundle(bundles[name])
        result.update(_threshold_rules(name, block_probability(bundles[name]), BLOCK_THRESHOLDS))
    _add_paired_block_rules(result, bundles)
    _add_cascade_rules(result, bundles)
    return result


def _add_paired_block_rules(
    result: dict[str, list[int]],
    bundles: dict[str, PredictionBundle],
) -> None:
    pairs = (("word", "bert"), ("combined", "bert"), ("char", "bert"))
    for left_name, right_name in pairs:
        left = block_from_bundle(bundles[left_name])
        right = block_from_bundle(bundles[right_name])
        result[f"{left_name}+{right_name}-intersection"] = [
            int(a and b) for a, b in zip(left, right, strict=True)
        ]
        result[f"{left_name}+{right_name}-union"] = [
            int(a or b) for a, b in zip(left, right, strict=True)
        ]


def _add_cascade_rules(
    result: dict[str, list[int]],
    bundles: dict[str, PredictionBundle],
) -> None:
    combined = block_probability(bundles["combined"])
    bert = block_probability(bundles["bert"])
    char = block_probability(bundles["char"])
    for high in (0.70, 0.80, 0.90):
        for support in (0.60, 0.70, 0.80):
            name = f"cascade-high{high:.2f}-support{support:.2f}"
            result[name] = [
                int(primary >= high or (primary >= 0.45 and semantic >= support and robust >= 0.50))
                for primary, semantic, robust in zip(combined, bert, char, strict=True)
            ]


def strike_rules(
    bundles: dict[str, PredictionBundle],
    selected_block: list[int],
) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for name in ("word", "char", "combined", "bert", "meta"):
        probabilities = strike_probability(bundles[name])
        for threshold in STRIKE_THRESHOLDS:
            strike = threshold_predictions(probabilities, threshold)
            result[f"{name}-strike@{threshold:.3f}+block-gate"] = [
                int(flag and block) for flag, block in zip(strike, selected_block, strict=True)
            ]
    _add_strike_consensus(result, bundles, selected_block)
    return result


def _all_positive(*series: list[int]) -> list[int]:
    return [int(all(value == 1 for value in values)) for values in zip(*series, strict=True)]


def _add_strike_consensus(
    result: dict[str, list[int]],
    bundles: dict[str, PredictionBundle],
    selected_block: list[int],
) -> None:
    word = bundles["word"].predictions["strike"]
    bert = bundles["bert"].predictions["strike"]
    combined = bundles["combined"].predictions["strike"]
    result["word+bert-strike-intersection+block-gate"] = _all_positive(word, bert, selected_block)
    result["combined+bert-strike-intersection+block-gate"] = _all_positive(
        combined, bert, selected_block
    )
    result["word+combined+bert-strike-intersection+block-gate"] = _all_positive(
        word, combined, bert, selected_block
    )


def mute_rules(bundles: dict[str, PredictionBundle]) -> dict[str, list[int]]:
    result = {f"{name}-argmax": mute_from_bundle(bundle) for name, bundle in bundles.items()}
    word = mute_from_bundle(bundles["word"])
    bert = mute_from_bundle(bundles["bert"])
    combined = mute_from_bundle(bundles["combined"])
    result["word+bert-intersection"] = [int(a and b) for a, b in zip(word, bert, strict=True)]
    result["word+bert-union"] = [int(a or b) for a, b in zip(word, bert, strict=True)]
    result["combined+bert-intersection"] = [
        int(a and b) for a, b in zip(combined, bert, strict=True)
    ]
    return result
