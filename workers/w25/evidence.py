"""Aggregate three-seed W25 evidence without hiding per-seed instability."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from workers.w25.artifacts import load_bundle
from workers.w25.stability import aggregate_numeric_values, stability_report

RANKING_SUITES = (
    "balanced_policy",
    "real_distribution",
    "adversarial_evasion",
    "context",
    "time_based_real_chat",
)


def aggregate_evidence_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_json(path)
    seeds = _load_manifest_seeds(manifest)
    stability = _aggregate_stability(seeds)
    return {
        "candidate": str(manifest["candidate"]),
        "suites": _aggregate_suites(seeds),
        "stability": stability,
        "performance": _aggregate_performance(seeds),
        "deployment_complexity": int(manifest.get("deployment_complexity", 99)),
        "seed_details": [_seed_detail(seed) for seed in seeds],
    }


def _load_manifest_seeds(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    seed_entries = manifest.get("seeds")
    if not isinstance(seed_entries, list) or len(seed_entries) < 3:
        raise ValueError("candidate evidence requires at least three seed entries")
    return [_load_seed_entry(entry) for entry in seed_entries]


def _aggregate_suites(seeds: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        name: _aggregate_suite([_seed_suite(seed, name) for seed in seeds])
        for name in RANKING_SUITES
    }


def _aggregate_stability(seeds: list[dict[str, Any]]) -> dict[str, Any]:
    predictions = _action_predictions(seeds)
    metrics = _seed_metrics(seeds)
    temperatures = _seed_numeric_payloads(seeds, "calibration", "temperatures")
    thresholds = _seed_numeric_payloads(seeds, "thresholds", "thresholds")
    result = stability_report(predictions, metrics, temperatures)
    result["thresholds"] = aggregate_numeric_values(thresholds)
    return result


def _action_predictions(seeds: list[dict[str, Any]]) -> dict[int, list[int]]:
    return {
        int(seed["seed"]): load_bundle(Path(seed["real_bundle"])).predictions["action"]
        for seed in seeds
    }


def _seed_metrics(seeds: list[dict[str, Any]]) -> dict[int, dict[str, float]]:
    return {
        int(seed["seed"]): _stability_metrics(_seed_suites(seed))
        for seed in seeds
    }


def _seed_numeric_payloads(
    seeds: list[dict[str, Any]],
    path_key: str,
    payload_key: str,
) -> dict[int, dict[str, float]]:
    return {
        int(seed["seed"]): _numeric_payload(Path(seed[path_key]), payload_key)
        for seed in seeds
    }


def _seed_suites(seed: dict[str, Any]) -> dict[str, Any]:
    return _mapping(seed, "suites")


def _seed_suite(seed: dict[str, Any], name: str) -> dict[str, Any]:
    return _mapping(_seed_suites(seed), name)


def _load_seed_entry(entry: object) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("seed evidence entry must be an object")
    suites = entry.get("suites")
    if not isinstance(suites, dict):
        raise ValueError("seed evidence requires suites object")
    loaded_suites = {}
    for name in RANKING_SUITES:
        value = suites.get(name)
        if not isinstance(value, str):
            raise ValueError(f"seed evidence missing suite path: {name}")
        loaded_suites[name] = _load_json(Path(value))
    return {
        "seed": int(entry["seed"]),
        "suites": loaded_suites,
        "real_bundle": Path(str(entry["real_bundle"])),
        "calibration": Path(str(entry["calibration"])),
        "thresholds": Path(str(entry["thresholds"])),
        "performance": _load_json(Path(str(entry["performance"]))),
    }


def _aggregate_suite(reports: list[dict[str, Any]]) -> dict[str, Any]:
    fingerprint = _shared_fingerprint(reports)
    return {
        "suite": {
            "fingerprint": fingerprint,
            "n": int(_suite_meta(reports[0])["n"]),
        },
        "semantic_label": {
            "macro_f1": _mean_path(reports, ("semantic_label", "macro_f1")),
        },
        "consequences": {
            name: _aggregate_consequence(reports, name)
            for name in ("review", "block", "strike", "containment")
        },
        "critical_slices": _aggregate_critical_slices(reports),
    }


def _aggregate_consequence(
    reports: list[dict[str, Any]],
    name: str,
) -> dict[str, Any]:
    fields = (
        "precision",
        "recall",
        "false_positive_rate",
        "false_negative_rate",
        "f1",
        "precision_wilson_lower_95",
        "fpr_wilson_upper_95",
    )
    consequence: dict[str, Any] = {
        field: _mean_consequence(reports, name, field) for field in fields
    }
    consequence["calibration"] = {
        key: _mean_calibration(reports, name, key)
        for key in ("ece", "brier_score")
    }
    return consequence


def _aggregate_critical_slices(
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    slices = _mapping(reports[0], "critical_slices")
    aggregated = {}
    for name, first in slices.items():
        if not isinstance(first, dict):
            continue
        rows = [_mapping(_mapping(report, "critical_slices"), name) for report in reports]
        item: dict[str, object] = {"n": int(first.get("n", 0))}
        if "n_gold_block" in first:
            item["n_gold_block"] = int(first["n_gold_block"])
        if first.get("block_recall") is not None:
            item["block_recall"] = statistics.fmean(
                float(row["block_recall"]) for row in rows
            )
        aggregated[name] = item
    return aggregated


def _aggregate_performance(seeds: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [seed["performance"] for seed in seeds]
    numeric = {
        key: [float(row[key]) for row in rows if isinstance(row, dict) and key in row]
        for key in (
            "p50_ms",
            "p95_ms",
            "p99_ms",
            "throughput_per_second",
            "startup_p50_ms",
            "startup_p95_ms",
            "cpu_percent_equivalent",
        )
    }
    result: dict[str, object] = {
        key: statistics.fmean(values)
        for key, values in numeric.items()
        if values
    }
    result["steady_rss_bytes"] = _max_metric(rows, "steady_rss_bytes")
    result["peak_rss_bytes"] = _max_metric(rows, "peak_rss_bytes")
    result["artifact_size_bytes"] = _max_metric(rows, "artifact_size_bytes")
    return result


def _stability_metrics(suites: dict[str, Any]) -> dict[str, float]:
    real = _mapping(suites, "real_distribution")
    adversarial = _mapping(suites, "adversarial_evasion")
    block = _consequence(real, "block")
    return {
        "real_block_precision": float(block["precision"]),
        "real_block_recall": float(block["recall"]),
        "real_block_fpr": float(block["false_positive_rate"]),
        "real_block_ece": float(_mapping(block, "calibration")["ece"]),
        "adversarial_block_recall": float(_consequence(adversarial, "block")["recall"]),
    }


def _seed_detail(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": int(seed["seed"]),
        "metrics": _stability_metrics(seed["suites"]),
        "performance": seed["performance"],
    }


def _shared_fingerprint(reports: list[dict[str, Any]]) -> str:
    values = {str(_suite_meta(report)["fingerprint"]) for report in reports}
    if len(values) != 1:
        raise ValueError("seed suite fingerprints do not match")
    return values.pop()


def _suite_meta(report: dict[str, Any]) -> dict[str, Any]:
    return _mapping(report, "suite")


def _mean_path(
    reports: list[dict[str, Any]],
    path: tuple[str, ...],
) -> float:
    values = []
    for report in reports:
        current: Any = report
        for key in path:
            if not isinstance(current, dict):
                raise ValueError(f"invalid report path: {path}")
            current = current[key]
        values.append(float(current))
    return statistics.fmean(values)


def _mean_consequence(
    reports: list[dict[str, Any]],
    name: str,
    field: str,
) -> float:
    return statistics.fmean(float(_consequence(report, name)[field]) for report in reports)


def _mean_calibration(
    reports: list[dict[str, Any]],
    name: str,
    field: str,
) -> float:
    return statistics.fmean(
        float(_mapping(_consequence(report, name), "calibration")[field])
        for report in reports
    )


def _consequence(report: dict[str, Any], name: str) -> dict[str, Any]:
    return _mapping(_mapping(report, "consequences"), name)


def _numeric_payload(path: Path, key: str) -> dict[str, float]:
    payload = _load_json(path)
    values = payload.get(key)
    if not isinstance(values, dict):
        raise ValueError(f"{path} requires {key} object")
    return {str(name): float(value) for name, value in values.items()}


def _max_metric(rows: list[Any], key: str) -> int:
    values = [
        int(row[key])
        for row in rows
        if isinstance(row, dict) and row.get(key) is not None
    ]
    return max(values) if values else 0


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value
