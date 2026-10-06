"""Consequence-specific reliability, calibration, and selective-risk metrics."""

from __future__ import annotations

from collections.abc import Iterable


def binary_metrics(gold: list[int], predicted: list[int]) -> dict[str, float | int]:
    if len(gold) != len(predicted):
        raise ValueError("gold/predicted length mismatch")
    tp = sum(g == 1 and p == 1 for g, p in zip(gold, predicted, strict=True))
    fp = sum(g == 0 and p == 1 for g, p in zip(gold, predicted, strict=True))
    fn = sum(g == 1 and p == 0 for g, p in zip(gold, predicted, strict=True))
    tn = len(gold) - tp - fp - fn
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = _ratio(2 * precision * recall, precision + recall)
    fpr = _ratio(fp, fp + tn)
    return {
        "precision": precision,
        "recall": recall,
        "false_positive_rate": fpr,
        "false_negative_rate": 1.0 - recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "false_per_10k_benign": fpr * 10_000,
        "false_per_100k_benign": fpr * 100_000,
        "false_per_1m_benign": fpr * 1_000_000,
        "precision_wilson_lower_95": wilson_lower(tp, tp + fp),
        "fpr_wilson_upper_95": wilson_upper(fp, fp + tn),
    }


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def expected_precision(
    *,
    recall: float,
    false_positive_rate: float,
    prevalence: float,
) -> float:
    if not 0.0 <= prevalence <= 1.0:
        raise ValueError("prevalence must be in [0, 1]")
    true_positive_mass = recall * prevalence
    false_positive_mass = false_positive_rate * (1.0 - prevalence)
    return _ratio(true_positive_mass, true_positive_mass + false_positive_mass)


def base_rate_table(
    *,
    recall: float,
    false_positive_rate: float,
    prevalences: Iterable[float],
) -> list[dict[str, float]]:
    return [
        {
            "prevalence": prevalence,
            "expected_precision": expected_precision(
                recall=recall,
                false_positive_rate=false_positive_rate,
                prevalence=prevalence,
            ),
        }
        for prevalence in prevalences
    ]


def calibration_metrics(
    gold: list[int],
    probabilities: list[float],
    *,
    bins: int = 15,
) -> dict[str, float]:
    if len(gold) != len(probabilities) or not gold:
        raise ValueError("calibration requires equal non-empty arrays")
    if any(not 0.0 <= value <= 1.0 for value in probabilities):
        raise ValueError("probabilities must be in [0, 1]")
    brier = sum((p - y) ** 2 for y, p in zip(gold, probabilities, strict=True)) / len(gold)
    ece = _expected_calibration_error(gold, probabilities, bins)
    return {"ece": ece, "brier_score": brier}


def _expected_calibration_error(
    gold: list[int],
    probabilities: list[float],
    bins: int,
) -> float:
    weighted_error = 0.0
    for bin_id in range(bins):
        indices = _calibration_bin_indices(probabilities, bin_id, bins)
        if not indices:
            continue
        weighted_error += _bin_weighted_error(gold, probabilities, indices)
    return weighted_error


def _calibration_bin_indices(
    probabilities: list[float],
    bin_id: int,
    bins: int,
) -> list[int]:
    lower = bin_id / bins
    upper = (bin_id + 1) / bins
    include_upper = bin_id == bins - 1
    return [
        index
        for index, value in enumerate(probabilities)
        if lower <= value < upper or (include_upper and value == 1.0)
    ]


def _bin_weighted_error(
    gold: list[int],
    probabilities: list[float],
    indices: list[int],
) -> float:
    confidence = sum(probabilities[index] for index in indices) / len(indices)
    accuracy = sum(gold[index] for index in indices) / len(indices)
    return abs(confidence - accuracy) * len(indices) / len(gold)


def risk_coverage_curve(
    correct: list[bool],
    uncertainty: list[float],
) -> list[dict[str, float]]:
    if len(correct) != len(uncertainty) or not correct:
        raise ValueError("risk/coverage requires equal non-empty arrays")
    order = sorted(range(len(correct)), key=lambda i: (uncertainty[i], i))
    mistakes = 0
    points = []
    for rank, index in enumerate(order, start=1):
        mistakes += 0 if correct[index] else 1
        points.append(
            {
                "coverage": rank / len(order),
                "risk": mistakes / rank,
                "uncertainty_threshold": uncertainty[index],
            }
        )
    return points


def seed_flip_rate(predictions_by_seed: dict[int, list[int]]) -> float:
    if not predictions_by_seed:
        raise ValueError("at least one seed is required")
    lengths = {len(values) for values in predictions_by_seed.values()}
    if len(lengths) != 1:
        raise ValueError("seed predictions have different lengths")
    count = lengths.pop()
    flips = sum(
        len({values[index] for values in predictions_by_seed.values()}) > 1
        for index in range(count)
    )
    return _ratio(flips, count)


def wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    center, margin, denominator = _wilson_parts(successes, total, z)
    return max(0.0, (center - margin) / denominator)


def wilson_upper(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 1.0
    center, margin, denominator = _wilson_parts(successes, total, z)
    return min(1.0, (center + margin) / denominator)


def _wilson_parts(successes: int, total: int, z: float) -> tuple[float, float, float]:
    if successes < 0 or successes > total or z <= 0:
        raise ValueError("invalid Wilson interval inputs")
    observed = successes / total
    z2 = z * z
    center = observed + z2 / (2 * total)
    margin = z * (
        (observed * (1 - observed) / total + z2 / (4 * total * total)) ** 0.5
    )
    return center, margin, 1 + z2 / total
