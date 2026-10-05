"""Generate validation-safe ONNX evidence for the selected W12 TF-IDF baseline.

This script intentionally reads only W11 train + validation. It never opens test,
frozen_adversarial, or owner_golden.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import platform
import statistics
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
import psutil
import skl2onnx
import sklearn
from moderation_api.models import (
    ChannelProfile,
    ClassificationInput,
    ContextMessage,
    MemorySnapshot,
    Platform,
)
from moderation_api.onnx_classifier import OnnxClassifier, OnnxClassifierConfig
from moderation_api.tfidf_runtime import TfidfRuntimeVectorizer
from onnxruntime.quantization import QuantType, quantize_dynamic

from .baseline import train_baseline
from .dataset import load_partition
from .evaluate import REPORTS_DIR, evaluate_predictions
from .export_baseline_onnx import EXPORT_DIR, export_baseline_onnx, sha256_of


def _selected_metrics(report: dict[str, Any]) -> dict[str, float | None]:
    return {
        "label_accuracy": report["semantic_label"]["accuracy"],
        "label_macro_f1": report["semantic_label"]["macro_f1"],
        "block_precision": report["runtime_visibility_binary"]["block_precision"],
        "block_recall": report["runtime_visibility_binary"]["block_recall"],
        "gameplay_fp": report["critical_slices"]["minecraft_gameplay"].get(
            "block_false_positive_rate"
        ),
        "threat_recall": report["critical_slices"]["real_world_threat"].get("block_recall"),
    }


def _validation_reproduction() -> tuple[Any, list[Any], dict[str, Any]]:
    """Retrain from W11 train and emit fresh validation-only reproducibility evidence."""
    train = load_partition("train")
    validation = load_partition("validation")
    model = train_baseline(train, seed=42)
    texts = [example.serialized for example in validation]
    predictions = model.predict_all(texts)
    probabilities = model.predict_proba_all(texts)
    report = evaluate_predictions(
        validation,
        predictions["label"],
        predictions["action"],
        predictions["review_priority"],
        predictions["strike"],
        predictions["containment"],
        predictions["support_flow"],
        [row[1] for row in probabilities["action"]],
    )
    report["candidate"] = "baseline-tfidf"
    report["seed"] = 42
    report_path = REPORTS_DIR / "val-baseline-tfidf.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return model, validation, {
        "source": "fresh train+validation-only reproduction in this workflow run",
        "report_path": str(report_path),
        "report_sha256": sha256_of(report_path),
        "metrics": _selected_metrics(report),
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("ONNX metadata must be an object")
    return parsed


def _session_probabilities(
    metadata: dict[str, Any],
    root: Path,
    texts: list[str],
) -> dict[str, np.ndarray]:
    vectorizer_meta = metadata["vectorizer"]
    vectorizer = TfidfRuntimeVectorizer.from_file(root / vectorizer_meta["path"])
    tensor = np.vstack([vectorizer.transform(text, np) for text in texts])
    output: dict[str, np.ndarray] = {}
    for head_name, head in metadata["heads"].items():
        session = ort.InferenceSession(
            str(root / head["path"]),
            providers=["CPUExecutionProvider"],
        )
        probability = session.run(
            [head["probabilities_output"]],
            {head["input_name"]: tensor},
        )[0]
        output[head_name] = np.asarray(probability, dtype=float)
    return output


def _parity_report(
    model: Any,
    validation: list[Any],
    metadata_path: Path,
    *,
    require_exact_predictions: bool = True,
) -> dict[str, Any]:
    metadata = _load_manifest(metadata_path)
    texts = [example.serialized for example in validation]
    sklearn_probabilities = model.predict_proba_all(texts)
    onnx_probabilities = _session_probabilities(metadata, metadata_path.parent, texts)
    heads: dict[str, Any] = {}
    for head_name in metadata["heads"]:
        expected = np.asarray(sklearn_probabilities[head_name], dtype=float)
        actual = onnx_probabilities[head_name]
        if expected.shape != actual.shape:
            raise RuntimeError(
                f"{head_name} parity shape mismatch: sklearn={expected.shape} onnx={actual.shape}"
            )
        differences = np.abs(expected - actual)
        mismatch = int(np.count_nonzero(np.argmax(expected, axis=1) != np.argmax(actual, axis=1)))
        heads[head_name] = {
            "max_abs_probability_delta": float(differences.max(initial=0.0)),
            "mean_abs_probability_delta": float(differences.mean()),
            "prediction_mismatches": mismatch,
            "n": len(validation),
        }
    max_delta = max(item["max_abs_probability_delta"] for item in heads.values())
    total_mismatches = sum(item["prediction_mismatches"] for item in heads.values())
    passed = total_mismatches == 0 and max_delta <= 1e-4
    if require_exact_predictions and not passed:
        raise RuntimeError(
            f"sklearn/ONNX parity failed: mismatches={total_mismatches} max_delta={max_delta}"
        )
    return {
        "passed": passed,
        "tolerance": 1e-4,
        "heads": heads,
        "max_abs_probability_delta": max_delta,
        "total_prediction_mismatches": total_mismatches,
    }


def _quantize_bundle(metadata_path: Path) -> tuple[Path | None, dict[str, Any]]:
    metadata = _load_manifest(metadata_path)
    quantized = copy.deepcopy(metadata)
    result: dict[str, Any] = {"supported": True, "heads": {}}
    try:
        for head_name, head in quantized["heads"].items():
            source = metadata_path.parent / head["path"]
            target = source.with_name(source.stem + "-int8.onnx")
            quantize_dynamic(str(source), str(target), weight_type=QuantType.QInt8)
            head["path"] = target.name
            head["sha256"] = sha256_of(target)
            head["bytes"] = target.stat().st_size
            result["heads"][head_name] = {
                "source_bytes": source.stat().st_size,
                "quantized_bytes": target.stat().st_size,
                "sha256": head["sha256"],
            }
    except Exception as exc:  # noqa: BLE001 - record backend support limitation
        result["supported"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        return None, result

    quantized["model_version"] = str(metadata["model_version"]) + "-int8"
    quantized["quantization"] = "onnxruntime-dynamic-qint8"
    output_path = metadata_path.parent / "baseline-tfidf-int8-metadata.json"
    output_path.write_text(json.dumps(quantized, indent=2) + "\n", encoding="utf-8")
    result["metadata_sha256"] = sha256_of(output_path)
    result["metadata_path"] = output_path.name
    return output_path, result


def _message(
    *,
    event_id: str,
    sender: str,
    offset_ms: int,
    text: str,
    start: datetime,
) -> ContextMessage:
    return ContextMessage(
        event_id=event_id,
        platform=Platform.MINECRAFT,
        channel_profile=ChannelProfile.MINECRAFT_PUBLIC,
        scope_id="w12-benchmark",
        channel_id=None,
        conversation_id=None,
        external_message_id=event_id,
        canonical_message_id=None,
        sender_id=sender,
        sender_identity_id=None,
        recipient_ids=(),
        recipient_identity_ids=(),
        target_ids=(),
        target_identity_ids=(),
        occurred_at=start + timedelta(milliseconds=offset_ms),
        text=text,
        reply_to_message_id=None,
    )


def _single_message_input() -> ClassificationInput:
    start = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    current = _message(
        event_id="bench-single",
        sender="player-a",
        offset_ms=0,
        text="irl at your school tomorrow",
        start=start,
    )
    return ClassificationInput(current=current, context=(), memory=MemorySnapshot())


def _representative_input() -> ClassificationInput:
    start = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    prior = (
        _message(
            event_id="bench-1",
            sender="player-a",
            offset_ms=0,
            text="im gonna get you",
            start=start,
        ),
        _message(
            event_id="bench-2",
            sender="player-b",
            offset_ms=450,
            text="in minecraft?",
            start=start,
        ),
    )
    current = _message(
        event_id="bench-3",
        sender="player-a",
        offset_ms=800,
        text="irl at your school tomorrow",
        start=start,
    )
    return ClassificationInput(current=current, context=prior, memory=MemorySnapshot())


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


async def _benchmark_item(
    classifier: OnnxClassifier,
    item: ClassificationInput,
) -> dict[str, Any]:
    for _ in range(20):
        await classifier.classify(item)
    timings: list[float] = []
    for _ in range(240):
        started = time.perf_counter()
        await classifier.classify(item)
        timings.append((time.perf_counter() - started) * 1000)
    throughput_started = time.perf_counter()
    for _ in range(120):
        await classifier.classify(item)
    throughput_elapsed = time.perf_counter() - throughput_started
    return {
        "latency_ms": {
            "p50": _percentile(timings, 0.50),
            "p95": _percentile(timings, 0.95),
            "p99": _percentile(timings, 0.99),
            "mean": statistics.fmean(timings),
            "n": len(timings),
        },
        "throughput_batch1_per_sec": 120 / throughput_elapsed,
    }


async def _benchmark_async(classifier: OnnxClassifier) -> dict[str, Any]:
    return {
        "single_message": await _benchmark_item(classifier, _single_message_input()),
        "representative_multi_message": await _benchmark_item(
            classifier,
            _representative_input(),
        ),
    }


def _benchmark_bundle(metadata_path: Path) -> dict[str, Any]:
    process = psutil.Process()
    before = process.memory_info().rss / (1024 * 1024)
    started = time.perf_counter()
    classifier = OnnxClassifier(
        OnnxClassifierConfig(
            metadata_path=metadata_path,
            expected_metadata_sha256=sha256_of(metadata_path),
            timeout_ms=1000,
        )
    )
    cold_load = time.perf_counter() - started
    health = classifier.health()
    if health.get("ready") is not True:
        raise RuntimeError(f"selected runtime adapter failed to load artifact: {health}")
    after_load = process.memory_info().rss / (1024 * 1024)
    runtime = asyncio.run(_benchmark_async(classifier))
    steady = process.memory_info().rss / (1024 * 1024)
    metadata = _load_manifest(metadata_path)
    artifact_bytes = int(metadata["vectorizer"]["bytes"]) + sum(
        int(head["bytes"]) for head in metadata["heads"].values()
    )
    return {
        "health": health,
        "cold_load_seconds": cold_load,
        "rss_before_mb": before,
        "rss_after_load_mb": after_load,
        "rss_steady_mb": steady,
        "rss_attributable_mb": max(after_load, steady) - before,
        "artifact_bytes": artifact_bytes,
        "cpu_count": os.cpu_count(),
        "cpu": platform.processor() or "unknown",
        **runtime,
    }


def _copy_manifest_to_reports(metadata_path: Path, report_name: str) -> dict[str, Any]:
    content = metadata_path.read_text(encoding="utf-8")
    target = REPORTS_DIR / report_name
    target.write_text(content, encoding="utf-8")
    return {
        "report_path": str(target),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    model, validation, reproduction = _validation_reproduction()
    metadata = export_baseline_onnx(model)
    metadata_path = EXPORT_DIR / "baseline-tfidf-metadata.json"
    original_manifest = _copy_manifest_to_reports(
        metadata_path,
        "baseline-tfidf-onnx-metadata.json",
    )
    parity = _parity_report(model, validation, metadata_path)
    original_benchmark = _benchmark_bundle(metadata_path)

    quantized_path, quantization = _quantize_bundle(metadata_path)
    quantized_parity: dict[str, Any] | None = None
    quantized_benchmark: dict[str, Any] | None = None
    quantized_manifest: dict[str, Any] | None = None
    if quantized_path is not None:
        # Compare quantized ONNX predictions against the same frozen sklearn baseline.
        quantized_parity = _parity_report(
            model,
            validation,
            quantized_path,
            require_exact_predictions=False,
        )
        quantization["selected"] = bool(quantized_parity["passed"])
        quantization["selection_reason"] = (
            "quantized bundle preserves exact validation predictions within parity tolerance"
            if quantized_parity["passed"]
            else "quantized bundle changes validation predictions; retain selected FP32 bundle"
        )
        quantized_benchmark = _benchmark_bundle(quantized_path)
        quantized_manifest = _copy_manifest_to_reports(
            quantized_path,
            "baseline-tfidf-int8-onnx-metadata.json",
        )

    evidence = {
        "scope": "train+validation only; no held-out partitions opened",
        "github_sha": os.environ.get("GITHUB_SHA"),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "skl2onnx": skl2onnx.__version__,
            "onnxruntime": ort.__version__,
            "psutil": psutil.__version__,
        },
        "validation_reproduction": reproduction,
        "original": {
            "metadata": metadata,
            "manifest_copy": original_manifest,
            "parity": parity,
            "benchmark": original_benchmark,
        },
        "quantization": quantization,
        "quantized": (
            None
            if quantized_path is None
            else {
                "manifest_copy": quantized_manifest,
                "parity": quantized_parity,
                "benchmark": quantized_benchmark,
            }
        ),
    }
    path = REPORTS_DIR / "onnx-baseline-evidence.json"
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == "__main__":
    main()
