"""W12 CPU benchmark: latency percentiles, throughput, and memory for ONNX artifacts.

Measures on CPU only (production target). Must NOT run while heavy training
saturates the machine — run benchmarks on an otherwise idle host.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import psutil
from transformers import BertTokenizer

from workers.w12.train_encoder import CANDIDATES

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
EXPORT_DIR = ARTIFACT_DIR / "onnx"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"

HEAD_NAMES = ["label", "action", "review_priority", "strike", "containment", "support_flow"]


def _rss_mb(proc: psutil.Process) -> float:
    return proc.memory_info().rss / (1024 * 1024)


def benchmark_onnx(candidate: str, seed: int, quantized: bool, max_len: int = 128,
                   n_warmup: int = 20, n_timed: int = 200) -> dict:
    name = f"{candidate}-seed{seed}" + ("-int8" if quantized else "")
    onnx_path = EXPORT_DIR / f"{name}.onnx"
    cfg = CANDIDATES[candidate]
    tokenizer = BertTokenizer(str(cfg["local_dir"] / "vocab.txt"), do_lower_case=True)

    proc = psutil.current_process()
    rss_before = _rss_mb(proc)
    t0 = time.time()
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    load_time = time.time() - t0
    rss_after_load = _rss_mb(proc)

    output_names = [f"logits_{n}" for n in HEAD_NAMES]

    # Representative inputs: short single message and multi-message context
    samples = [
        "[PROFILE=minecraft_public]\n[A@+0ms] [TARGET] im gonna kill you",
        ("[PROFILE=minecraft_public]\n[A@+0ms] im gonna stab you\n"
         "[A@+800ms] [TARGET] irl at your school tomorrow"),
        ("[PROFILE=discord_general]\n[A@+0ms] you are terrible at this game\n"
         "[B@+5000ms] lol cope\n[A@+9000ms] [TARGET] kys"),
    ]
    enc = tokenizer(samples, max_length=max_len, truncation=True, padding=True,
                    return_tensors="np")

    def single(i: int) -> dict:
        return {
            "input_ids": enc["input_ids"][i:i+1].astype(np.int64),
            "attention_mask": enc["attention_mask"][i:i+1].astype(np.int64),
        }

    # Warmup
    for _ in range(n_warmup):
        sess.run(output_names, single(0))

    # Batch-size-1 latency
    lat: list[float] = []
    for _ in range(n_timed):
        for i in range(len(samples)):
            t = time.perf_counter()
            sess.run(output_names, single(i))
            lat.append((time.perf_counter() - t) * 1000)
    lat_sorted = sorted(lat)
    def pct(p: float) -> float:
        return lat_sorted[min(int(p / 100 * len(lat_sorted)), len(lat_sorted) - 1)]

    # Throughput (batch-size-1, steady state)
    t = time.perf_counter()
    n_iter = 100
    for _ in range(n_iter):
        sess.run(output_names, single(1))
    elapsed = time.perf_counter() - t
    throughput = n_iter / elapsed

    rss_steady = _rss_mb(proc)

    result = {
        "candidate": candidate,
        "seed": seed,
        "quantized": quantized,
        "artifact": onnx_path.name,
        "artifact_bytes": onnx_path.stat().st_size,
        "cpu": {
            "count": os.cpu_count(),
            "model": _cpu_model(),
        },
        "cold_load_seconds": round(load_time, 3),
        "rss_before_mb": round(rss_before, 1),
        "rss_after_load_mb": round(rss_after_load, 1),
        "rss_steady_mb": round(rss_steady, 1),
        "rss_attributable_mb": round(rss_steady - rss_before, 1),
        "latency_ms": {
            "p50": round(pct(50), 2),
            "p95": round(pct(95), 2),
            "p99": round(pct(99), 2),
            "n_samples": len(lat),
        },
        "throughput_batch1_per_sec": round(throughput, 1),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / f"benchmark-{name}.json", "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2), flush=True)
    return result


def _cpu_model() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=list(CANDIDATES), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quantized", action="store_true")
    args = parser.parse_args()
    benchmark_onnx(args.candidate, args.seed, args.quantized)


if __name__ == "__main__":
    main()
