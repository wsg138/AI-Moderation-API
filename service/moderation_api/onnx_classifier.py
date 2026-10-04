"""W12 runtime adapter for the selected baseline TF-IDF ONNX bundle.

The selected W12 baseline stores the fitted TF-IDF transform as safe JSON and
exports six numeric-input ONNX logistic-regression heads. This avoids pickle and
backend-specific ONNX string tokenization while preserving the trained model.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model_serialization import ModelMessage, serialize_model_input
from .models import (
    ClassificationInput,
    ClassificationResult,
    Containment,
    Label,
    MessageAction,
    ReviewPriority,
    StrikeRecommendation,
    SupportFlow,
)
from .tfidf_runtime import TfidfRuntimeVectorizer

HEAD_NAMES = ("label", "action", "review_priority", "strike", "containment", "support_flow")
_METADATA_SCHEMA_VERSION = 2


def serialize_input(item: ClassificationInput) -> str:
    """Serialize runtime context with the exact shared W12 training contract."""
    current_time = item.current.occurred_at
    prior = list(item.context)[-20:]
    messages = [
        ModelMessage(
            speaker_key=message.sender_id,
            offset_ms=round((message.occurred_at - current_time).total_seconds() * 1000),
            text=message.text,
        )
        for message in prior
    ]
    messages.append(
        ModelMessage(
            speaker_key=item.current.sender_id,
            offset_ms=0,
            text=item.current.text,
        )
    )
    return serialize_model_input(
        item.current.channel_profile.value,
        messages,
        len(messages) - 1,
    )


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def _verified_file(root: Path, relative_path: str, expected_sha256: str, context: str) -> Path:
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{context} path escapes metadata directory")
    if not path.is_file():
        raise ValueError(f"{context} artifact missing: {path}")
    if _sha256_of(path).lower() != expected_sha256.lower():
        raise ValueError(f"{context} checksum mismatch")
    return path


def _verified_metadata_sha(path: Path, expected_sha256: str) -> str:
    if not path.is_file():
        raise ValueError(f"model metadata missing: {path}")
    actual = _sha256_of(path)
    if actual.lower() != expected_sha256.lower():
        raise ValueError("model metadata checksum mismatch")
    return actual


def _read_metadata(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("model metadata must be an object")
    return parsed


def _required_text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid {key} for {context}")
    return value


def _parse_classes(raw_head: dict[str, Any], head_name: str) -> tuple[str, ...]:
    raw_classes = raw_head.get("classes")
    if not isinstance(raw_classes, list) or not raw_classes:
        raise ValueError(f"missing class metadata for head {head_name}")
    if not all(isinstance(value, str) and value for value in raw_classes):
        raise ValueError(f"invalid class metadata for head {head_name}")
    return tuple(raw_classes)


@dataclass(frozen=True, slots=True)
class OnnxClassifierConfig:
    metadata_path: Path
    expected_metadata_sha256: str
    timeout_ms: int = 500

    @classmethod
    def from_env(cls) -> OnnxClassifierConfig:
        def required(name: str) -> str:
            value = os.environ.get(name)
            if not value:
                raise RuntimeError(f"missing required env var {name}")
            return value

        return cls(
            metadata_path=Path(required("AI_MOD_ONNX_METADATA_PATH")),
            expected_metadata_sha256=required("AI_MOD_ONNX_METADATA_SHA256").lower(),
            timeout_ms=int(os.environ.get("AI_MOD_ONNX_TIMEOUT_MS", "500")),
        )


@dataclass(frozen=True, slots=True)
class _HeadSpec:
    relative_path: str
    expected_sha256: str
    input_name: str
    probabilities_output: str
    classes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _LoadedHead:
    session: Any
    input_name: str
    probabilities_output: str
    classes: tuple[str, ...]


def _parse_manifest(parsed: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    schema_version = parsed.get("schema_version")
    if schema_version != _METADATA_SCHEMA_VERSION:
        raise ValueError(f"unsupported model metadata schema: {schema_version}")
    if parsed.get("candidate") != "baseline-tfidf":
        raise ValueError("model metadata candidate is not baseline-tfidf")
    model_version = _required_text(parsed, "model_version", "model metadata")
    raw_heads = parsed.get("heads")
    raw_vectorizer = parsed.get("vectorizer")
    if not isinstance(raw_heads, dict):
        raise ValueError("model metadata missing heads")
    if not isinstance(raw_vectorizer, dict):
        raise ValueError("model metadata missing vectorizer")
    return model_version, raw_heads, raw_vectorizer


def _head_spec(raw_heads: dict[str, Any], head_name: str) -> _HeadSpec:
    raw_head = raw_heads.get(head_name)
    if not isinstance(raw_head, dict):
        raise ValueError(f"missing metadata for head {head_name}")
    return _HeadSpec(
        relative_path=_required_text(raw_head, "path", f"head {head_name}"),
        expected_sha256=_required_text(raw_head, "sha256", f"head {head_name}"),
        input_name=_required_text(raw_head, "input_name", f"head {head_name}"),
        probabilities_output=_required_text(
            raw_head, "probabilities_output", f"head {head_name}"
        ),
        classes=_parse_classes(raw_head, head_name),
    )


def _load_head(root: Path, head_name: str, raw_heads: dict[str, Any], ort: Any) -> _LoadedHead:
    spec = _head_spec(raw_heads, head_name)
    model_path = _verified_file(
        root, spec.relative_path, spec.expected_sha256, f"head {head_name}"
    )
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    session_inputs = {item.name for item in session.get_inputs()}
    session_outputs = {item.name for item in session.get_outputs()}
    if spec.input_name not in session_inputs:
        raise ValueError(f"input {spec.input_name} absent from {head_name} artifact")
    if spec.probabilities_output not in session_outputs:
        raise ValueError(
            f"output {spec.probabilities_output} absent from {head_name} artifact"
        )
    return _LoadedHead(
        session=session,
        input_name=spec.input_name,
        probabilities_output=spec.probabilities_output,
        classes=spec.classes,
    )


def _load_vectorizer(root: Path, raw: dict[str, Any]) -> TfidfRuntimeVectorizer:
    relative_path = _required_text(raw, "path", "vectorizer")
    expected_sha = _required_text(raw, "sha256", "vectorizer")
    vectorizer_path = _verified_file(root, relative_path, expected_sha, "vectorizer")
    vectorizer = TfidfRuntimeVectorizer.from_file(vectorizer_path)
    expected_features = raw.get("feature_count")
    if not isinstance(expected_features, int) or expected_features != vectorizer.feature_count:
        raise ValueError("vectorizer feature count mismatch")
    return vectorizer


def _import_inference_modules() -> tuple[Any, Any]:
    np: Any = importlib.import_module("numpy")
    ort: Any = importlib.import_module("onnxruntime")
    return np, ort


class OnnxClassifier:
    """Checksum-verified fail-open classifier for the selected baseline bundle."""

    def __init__(self, config: OnnxClassifierConfig) -> None:
        self._config = config
        self._ready = False
        self._error: str | None = None
        self._heads: dict[str, _LoadedHead] = {}
        self._vectorizer: TfidfRuntimeVectorizer | None = None
        self._metadata_sha256: str | None = None
        self._model_version: str | None = None
        self._np: Any = None
        self._load()

    def _load(self) -> None:
        try:
            metadata_path = self._config.metadata_path
            actual_sha = _verified_metadata_sha(
                metadata_path, self._config.expected_metadata_sha256
            )
            model_version, raw_heads, raw_vectorizer = _parse_manifest(
                _read_metadata(metadata_path)
            )
            np, ort = _import_inference_modules()
            root = metadata_path.parent.resolve()
            vectorizer = _load_vectorizer(root, raw_vectorizer)
            loaded = {
                head_name: _load_head(root, head_name, raw_heads, ort)
                for head_name in HEAD_NAMES
            }
        except Exception as exc:  # noqa: BLE001 - invalid model means fail-open not-ready
            self._error = f"model load failed: {exc}"
            self._heads.clear()
            self._vectorizer = None
            return

        self._np = np
        self._heads = loaded
        self._vectorizer = vectorizer
        self._metadata_sha256 = actual_sha
        self._model_version = f"{model_version}+{actual_sha[:12]}"
        self._ready = True

    def health(self) -> dict[str, object]:
        return {
            "ready": self._ready,
            "mode": "onnx-baseline-tfidf",
            "model_version": self._model_version,
            "metadata_sha256": self._metadata_sha256,
            "heads_loaded": len(self._heads),
            "feature_count": (
                self._vectorizer.feature_count if self._vectorizer is not None else 0
            ),
            **({"error": self._error} if self._error else {}),
        }

    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        if (
            not self._ready
            or self._np is None
            or self._model_version is None
            or self._vectorizer is None
        ):
            raise RuntimeError("onnx classifier not ready")
        text = serialize_input(item)
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._infer, text),
                timeout=self._config.timeout_ms / 1000,
            )
        except TimeoutError as exc:
            raise TimeoutError("onnx inference exceeded timeout") from exc

    def _infer_head(
        self,
        head_name: str,
        feature_tensor: Any,
    ) -> tuple[str, float, dict[str, float]]:
        np = self._np
        if np is None:
            raise RuntimeError("onnx classifier not ready")
        loaded = self._heads[head_name]
        outputs = loaded.session.run(
            [loaded.probabilities_output],
            {loaded.input_name: feature_tensor},
        )
        probabilities = np.asarray(outputs[0], dtype=float).reshape(-1)
        if len(probabilities) != len(loaded.classes):
            raise ValueError(
                f"{head_name} probability count {len(probabilities)} "
                f"does not match class count {len(loaded.classes)}"
            )
        best_index = int(np.argmax(probabilities))
        scores = {
            f"{head_name}:{class_name}": _bounded(float(probabilities[index]))
            for index, class_name in enumerate(loaded.classes)
        }
        return (
            loaded.classes[best_index],
            _bounded(float(probabilities[best_index])),
            scores,
        )

    def _infer(self, text: str) -> ClassificationResult:
        np = self._np
        vectorizer = self._vectorizer
        if np is None or vectorizer is None or self._model_version is None:
            raise RuntimeError("onnx classifier not ready")
        feature_tensor = vectorizer.transform(text, np)
        predictions = {
            name: self._infer_head(name, feature_tensor)
            for name in HEAD_NAMES
        }
        scores = {
            key: value
            for _, _, head_scores in predictions.values()
            for key, value in head_scores.items()
        }
        predicted = {name: result[0] for name, result in predictions.items()}
        message_action = (
            MessageAction.BLOCK if predicted["action"] == "BLOCK" else MessageAction.ALLOW
        )
        strike = (
            StrikeRecommendation.STRIKE
            if predicted["strike"].lower() == "true"
            else StrikeRecommendation.NONE
        )
        return ClassificationResult(
            message_action=message_action,
            semantic_label=Label(predicted["label"]),
            review_priority=ReviewPriority(predicted["review_priority"]),
            strike_recommendation=strike,
            containment=Containment(predicted["containment"]),
            containment_duration_seconds=None,
            support_flow=SupportFlow(predicted["support_flow"]),
            scores=scores,
            confidence=predictions["label"][1],
            rule_hits=(),
            reason_codes=("onnx_local_classifier",),
            related_message_ids=(),
            evidence_event_ids=(),
            model_version=self._model_version,
        )
