"""CPU/runtime benchmark harness for W25 candidates."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil  # pyright: ignore[reportMissingImports]


def benchmark_callable(
    operation: Callable[[], object],
    *,
    iterations: int = 100,
    concurrency: int = 1,
    warmup: int = 5,
) -> dict[str, float | int]:
    process = psutil.Process()
    for _ in range(warmup):
        operation()
    rss_before = process.memory_info().rss
    cpu_before = process.cpu_times()
    stop = threading.Event()
    rss_samples = [rss_before]
    sampler = _start_rss_sampler(process, stop, rss_samples)
    started = time.perf_counter()
    latencies = _run_iterations(operation, iterations, concurrency)
    wall_seconds = time.perf_counter() - started
    stop.set()
    sampler.join()
    cpu_after = process.cpu_times()
    rss_after = process.memory_info().rss
    cpu_seconds = _cpu_seconds(cpu_before, cpu_after)
    return _benchmark_record(
        latencies,
        iterations,
        concurrency,
        wall_seconds,
        rss_before,
        rss_after,
        max(rss_samples),
        cpu_seconds,
    )


def benchmark_queue_pressure(
    operation: Callable[[], object],
    *,
    requests: int = 100,
    workers: int = 4,
    timeout_ms: float = 100.0,
) -> dict[str, float | int]:
    _validate_queue_settings(requests, workers, timeout_ms)
    rows = _queue_rows(operation, requests, workers, timeout_ms)
    queue = [row["queue_ms"] for row in rows]
    total = [row["total_ms"] for row in rows]
    timed_out = sum(bool(row["fail_open"]) for row in rows)
    return {
        "requests": requests,
        "workers": workers,
        "timeout_ms": timeout_ms,
        "p50_queue_ms": _percentile(queue, 0.50),
        "p95_queue_ms": _percentile(queue, 0.95),
        "p99_total_ms": _percentile(total, 0.99),
        "fail_open_count": timed_out,
        "fail_open_rate": timed_out / requests,
    }


def _validate_queue_settings(requests: int, workers: int, timeout_ms: float) -> None:
    if requests < 1:
        raise ValueError("queue-pressure requests must be positive")
    if workers < 1:
        raise ValueError("queue-pressure workers must be positive")
    if timeout_ms <= 0:
        raise ValueError("queue-pressure timeout must be positive")


def _queue_rows(
    operation: Callable[[], object],
    requests: int,
    workers: int,
    timeout_ms: float,
) -> list[dict[str, float | bool]]:
    enqueued = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_queued_call, operation, enqueued, timeout_ms)
            for _ in range(requests)
        ]
        return [future.result() for future in futures]


def measure_startup(factory: Callable[[], object], *, iterations: int = 5) -> dict[str, float]:
    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        factory()
        samples.append((time.perf_counter() - started) * 1000.0)
    return {
        "startup_p50_ms": _percentile(samples, 0.50),
        "startup_p95_ms": _percentile(samples, 0.95),
    }


def artifact_size_bytes(paths: list[Path]) -> int:
    return sum(_path_size(path) for path in paths)


def _benchmark_record(
    latencies: list[float],
    iterations: int,
    concurrency: int,
    wall_seconds: float,
    rss_before: int,
    rss_after: int,
    peak_rss: int,
    cpu_seconds: float,
) -> dict[str, float | int]:
    return {
        "iterations": iterations,
        "concurrency": concurrency,
        "p50_ms": _percentile(latencies, 0.50),
        "p95_ms": _percentile(latencies, 0.95),
        "p99_ms": _percentile(latencies, 0.99),
        "throughput_per_second": iterations / max(wall_seconds, 1e-9),
        "wall_seconds": wall_seconds,
        "steady_rss_bytes": rss_after,
        "peak_rss_bytes": peak_rss,
        "rss_delta_bytes": rss_after - rss_before,
        "cpu_seconds": cpu_seconds,
        "cpu_percent_equivalent": 100.0 * cpu_seconds / max(wall_seconds, 1e-9),
    }


def _start_rss_sampler(process, stop: threading.Event, samples: list[int]) -> threading.Thread:
    thread = threading.Thread(
        target=_sample_rss,
        args=(process, stop, samples),
        daemon=True,
    )
    thread.start()
    return thread


def _sample_rss(process, stop: threading.Event, samples: list[int]) -> None:
    while not stop.wait(0.001):
        try:
            samples.append(int(process.memory_info().rss))
        except psutil.Error:
            return


def _run_iterations(
    operation: Callable[[], object],
    iterations: int,
    concurrency: int,
) -> list[float]:
    if concurrency <= 1:
        return [_timed(operation) for _ in range(iterations)]
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_timed, operation) for _ in range(iterations)]
        return [future.result() for future in futures]


def _queued_call(
    operation: Callable[[], object],
    enqueued: float,
    timeout_ms: float,
) -> dict[str, float | bool]:
    started = time.perf_counter()
    operation()
    finished = time.perf_counter()
    queue_ms = (started - enqueued) * 1000.0
    total_ms = (finished - enqueued) * 1000.0
    return {
        "queue_ms": queue_ms,
        "total_ms": total_ms,
        "fail_open": total_ms > timeout_ms,
    }


def _timed(operation: Callable[[], object]) -> float:
    started = time.perf_counter()
    operation()
    return (time.perf_counter() - started) * 1000.0


def _path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())
    raise FileNotFoundError(path)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return float(ordered[index])


def _cpu_seconds(before, after) -> float:
    return float((after.user - before.user) + (after.system - before.system))
