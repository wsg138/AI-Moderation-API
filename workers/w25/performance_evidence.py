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
