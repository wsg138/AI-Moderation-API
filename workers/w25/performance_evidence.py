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
    single = benchmark_callable(operation, iterations=iterations, concurrency=1)
    realistic = benchmark_callable(
        operation,
        iterations=iterations,
        concurrency=concurrency,
    )
    startup = measure_startup(startup_factory)
    queue = benchmark_queue_pressure(
        operation,
        requests=queue_requests,
        workers=concurrency,
        timeout_ms=timeout_ms,
    )
    return {
        "p50_ms": realistic["p50_ms"],
        "p95_ms": realistic["p95_ms"],
        "p99_ms": realistic["p99_ms"],
        "throughput_per_second": realistic["throughput_per_second"],
        "steady_rss_bytes": realistic["steady_rss_bytes"],
        "peak_rss_bytes": realistic["peak_rss_bytes"],
        "cpu_percent_equivalent": realistic["cpu_percent_equivalent"],
        "startup_p50_ms": startup["startup_p50_ms"],
        "startup_p95_ms": startup["startup_p95_ms"],
        "concurrency_1": single,
        "concurrency_realistic": realistic,
        "startup": startup,
        "queue_pressure": queue,
        "artifact_size_bytes": artifact_size_bytes(artifact_paths),
    }
