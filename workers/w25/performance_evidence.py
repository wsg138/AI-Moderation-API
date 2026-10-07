"""Compose reproducible runtime measurements for a loaded W25 candidate."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from workers.w25.benchmark import (
    artifact_size_bytes,
    benchmark_callable,
    benchmark_queue_pressure,
    measure_startup,
)


def benchmark_candidate(
    operation: Callable[[], object],
    startup_factory: Callable[[], object],
    artifact_paths: list[Path],
    *,
    iterations: int = 100,
    concurrency: int = 4,
    queue_requests: int = 100,
    timeout_ms: float = 100.0,
) -> dict[str, object]:
    if concurrency < 1:
        raise ValueError("benchmark concurrency must be positive")
    return {
        "concurrency_1": benchmark_callable(
            operation,
            iterations=iterations,
            concurrency=1,
        ),
        "concurrency_realistic": benchmark_callable(
            operation,
            iterations=iterations,
            concurrency=concurrency,
        ),
        "startup": measure_startup(startup_factory),
        "queue_pressure": benchmark_queue_pressure(
            operation,
            requests=queue_requests,
            workers=concurrency,
            timeout_ms=timeout_ms,
        ),
        "artifact_size_bytes": artifact_size_bytes(artifact_paths),
    }


def ranking_performance_fields(report: dict[str, object]) -> dict[str, float | int]:
    """Flatten the benchmark dimensions consumed by evidence ranking."""
    single = _metric_group(report, "concurrency_1")
    realistic = _metric_group(report, "concurrency_realistic")
    startup = _metric_group(report, "startup")
    return {
        "p50_ms": float(_numeric(single, "p50_ms")),
        "p95_ms": float(_numeric(single, "p95_ms")),
        "p99_ms": float(_numeric(single, "p99_ms")),
        "throughput_per_second": float(
            _numeric(realistic, "throughput_per_second")
        ),
        "startup_p50_ms": float(_numeric(startup, "startup_p50_ms")),
        "startup_p95_ms": float(_numeric(startup, "startup_p95_ms")),
        "cpu_percent_equivalent": float(
            _numeric(realistic, "cpu_percent_equivalent")
        ),
        "steady_rss_bytes": int(_numeric(realistic, "steady_rss_bytes")),
        "peak_rss_bytes": max(
            int(_numeric(single, "peak_rss_bytes")),
            int(_numeric(realistic, "peak_rss_bytes")),
        ),
        "artifact_size_bytes": int(_numeric(report, "artifact_size_bytes")),
    }


def _metric_group(report: dict[str, object], key: str) -> dict[str, object]:
    value = report.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"benchmark report requires {key} object")
    return value


def _numeric(report: dict[str, object], key: str) -> float | int:
    value = report.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"benchmark report requires numeric {key}")
    return value
