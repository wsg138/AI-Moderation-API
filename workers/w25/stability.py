"""Seed-to-seed consistency and calibration stability summaries."""

from __future__ import annotations

import statistics

from workers.w25.metrics import seed_flip_rate


def stability_report(
    predictions_by_seed: dict[int, list[int]],
    metrics_by_seed: dict[int, dict[str, float]],
    temperatures_by_seed: dict[int, dict[str, float]],
) -> dict[str, object]:
    seeds = sorted(predictions_by_seed)
    if set(seeds) != set(metrics_by_seed) or set(seeds) != set(temperatures_by_seed):
        raise ValueError("stability inputs must contain the same seeds")
    return {
        "seeds": seeds,
        "prediction_flip_rate": seed_flip_rate(predictions_by_seed),
        "metrics": aggregate_numeric_values(metrics_by_seed),
        "temperatures": aggregate_numeric_values(temperatures_by_seed),
    }


def aggregate_numeric_values(
    values_by_seed: dict[int, dict[str, float]],
) -> dict[str, dict[str, float]]:
    names = sorted({name for values in values_by_seed.values() for name in values})
    return {
        name: _summary(
            [
                float(values_by_seed[seed][name])
                for seed in sorted(values_by_seed)
                if name in values_by_seed[seed]
            ]
        )
        for name in names
    }


def _summary(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize an empty value list")
    return {
        "mean": statistics.fmean(values),
        "stddev": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
    }
