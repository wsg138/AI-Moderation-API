"""Production-safe ONNX export and prediction-parity checks for W25."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np  # pyright: ignore[reportMissingImports]

from workers.w12.dataset import ModerationExample
from workers.w25.contract import HEAD_NAMES, PredictionBundle
from workers.w25.data import serialize_variant


def export_encoder_onnx(
    model,
    tokenizer,
    *,
    output_path: Path,
    sample_text: str,
    max_length: int,
    opset: int = 18,
) -> None:
    import torch  # pyright: ignore[reportMissingImports]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = tokenizer(
        sample_text,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors="pt",
    )
    wrapper = _onnx_wrapper(model).eval()
    dynamic_axes = {
        "input_ids": {0: "batch"},
        "attention_mask": {0: "batch"},
        **{name: {0: "batch"} for name in HEAD_NAMES},
    }
    torch.onnx.export(
        wrapper,
        (encoded["input_ids"], encoded["attention_mask"]),
        output_path,
        input_names=["input_ids", "attention_mask"],
        output_names=list(HEAD_NAMES),
        dynamic_axes=dynamic_axes,
        opset_version=opset,
        do_constant_folding=True,
    )
    _validate_onnx(output_path)


def artifact_metadata(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _validate_onnx(path: Path) -> None:
    import onnx  # pyright: ignore[reportMissingImports]

    model = onnx.load(path)
    onnx.checker.check_model(model)


def _onnx_wrapper(model):
    import torch.nn as nn  # pyright: ignore[reportMissingImports]

    class OnnxHeadWrapper(nn.Module):
        def __init__(self, wrapped) -> None:
            super().__init__()
            self.wrapped = wrapped

        def forward(self, input_ids, attention_mask):
            logits, _pooled = self.wrapped(input_ids, attention_mask)
            return tuple(logits[name] for name in HEAD_NAMES)

    return OnnxHeadWrapper(model)


def load_onnx_session(model_path: Path):
    import onnxruntime as ort  # pyright: ignore[reportMissingImports]

    return ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )


def predict_onnx(
    model_path: Path,
    tokenizer,
    examples: list[ModerationExample],
    *,
    serialization_variant: str,
    max_length: int,
) -> PredictionBundle:
    session = load_onnx_session(model_path)
    return predict_onnx_session(
        session,
        tokenizer,
        examples,
        serialization_variant=serialization_variant,
        max_length=max_length,
    )


def predict_onnx_session(
    session,
    tokenizer,
    examples: list[ModerationExample],
    *,
    serialization_variant: str,
    max_length: int,
) -> PredictionBundle:
    texts = [serialize_variant(item.serialized, serialization_variant) for item in examples]
    encoded = tokenizer(
        texts,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors="np",
    )
    outputs = session.run(
        list(HEAD_NAMES),
        {
            "input_ids": np.asarray(encoded["input_ids"], dtype=np.int64),
            "attention_mask": np.asarray(encoded["attention_mask"], dtype=np.int64),
        },
    )
    probabilities = {
        head: _softmax(np.asarray(matrix, dtype=np.float64)).tolist()
        for head, matrix in zip(HEAD_NAMES, outputs, strict=True)
    }
    predictions = {
        head: np.asarray(rows).argmax(axis=1).astype(int).tolist()
        for head, rows in probabilities.items()
    }
    bundle = PredictionBundle(
        predictions,
        probabilities,
        [1.0 - max(row) for row in probabilities["action"]],
    )
    bundle.validate()
    return bundle


def parity_report(
    reference: PredictionBundle,
    optimized: PredictionBundle,
) -> dict[str, object]:
    reference.validate()
    optimized.validate()
    if len(reference.uncertainty) != len(optimized.uncertainty):
        raise ValueError("parity bundles have different lengths")
    mismatches = {
        head: sum(
            left != right
            for left, right in zip(
                reference.predictions[head],
                optimized.predictions[head],
                strict=True,
            )
        )
        for head in HEAD_NAMES
    }
    deltas = [
        abs(left - right)
        for head in HEAD_NAMES
        for left_row, right_row in zip(
            reference.probabilities[head],
            optimized.probabilities[head],
            strict=True,
        )
        for left, right in zip(left_row, right_row, strict=True)
    ]
    return {
        "examples": len(reference.uncertainty),
        "prediction_mismatches": mismatches,
        "total_prediction_mismatches": sum(mismatches.values()),
        "max_probability_delta": max(deltas, default=0.0),
        "prediction_parity": not any(mismatches.values()),
    }


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / exponentials.sum(axis=1, keepdims=True)
