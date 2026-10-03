"""W12 runtime adapter for the selected baseline TF-IDF ONNX bundle.

The selected W12 baseline exports one string-input ONNX model per policy head.
This adapter loads that exact bundle from a checksum-pinned metadata manifest.
It performs no network access and stays not-ready on any artifact/dependency
problem so the existing moderation runtime can fail open.
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

HEAD_NAMES = ("label", "action", "review_priority", "strike", "containment", "support_flow")
_METADATA_SCHEMA_VERSION = 1


def serialize_input(item: ClassificationInput) -> str:
    """Serialize runtime context with the same structural contract as W12 training.

    Synthetic training examples use abstract speaker markers (A, B, ...), relative
    millisecond offsets, one channel profile marker, and one TARGET marker. Runtime
    identities are therefore mapped to first-seen abstract speaker markers instead
    of leaking player IDs into model input.
    """
    messages = [*list(item.context)[-20:], item.current]
    parts = [f"[PROFILE={item.current.channel_profile.value}]"]
    if not messages:
        return "\n".join(parts)

    base_time = messages[0].occurred_at
    speakers: dict[str, str] = {}
    for message in messages:
        speaker = speakers.get(message.sender_id)
        if speaker is None:
            speaker = _speaker_marker(len(speakers))
            speakers[message.sender_id] = speaker
        offset_ms = max(0, round((message.occurred_at - base_time).total_seconds() * 1000))
        target = " [TARGET]" if message is item.current else ""
        parts.append(f"[{speaker}@+{offset_ms}ms]{target} {message.text}")
    return "\n".join(parts)


def _speaker_marker(index: int) -> str:
    if 0 <= index < 26:
        return chr(ord("A") + index)
    return f"S{index}"


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


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
class _LoadedHead:
    session: Any
    input_name: str
    probabilities_output: str
    classes: tuple[str, ...]


class OnnxClassifier:
    """Checksum-verified fail-open classifier for the selected baseline bundle."""

    def __init__(self, config: OnnxClassifierConfig) -> None:
        self._config = config
        self._ready = False
        self._error: str | None = None
        self._heads: dict[str, _LoadedHead] = {}
        self._metadata_sha256: str | None = None
        self._model_version: str | None = None
        self._np: Any = None
        self._load()

    def _load(self) -> None:
        metadata_path = self._config.metadata_path
        if not metadata_path.is_file():
            self._error = f"model metadata missing: {metadata_path}"
            return

        actual_metadata_sha = _sha256_of(metadata_path)
        if actual_metadata_sha.lower() != self._config.expected_metadata_sha256:
            self._error = "model metadata checksum mismatch"
            return

        try:
            parsed = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._error = f"model metadata invalid: {exc}"
            return
        if not isinstance(parsed, dict):
            self._error = "model metadata must be an object"
            return

        schema_version = parsed.get("schema_version")
        if schema_version != _METADATA_SCHEMA_VERSION:
            self._error = f"unsupported model metadata schema: {schema_version}"
            return
        if parsed.get("candidate") != "baseline-tfidf":
            self._error = "model metadata candidate is not baseline-tfidf"
            return

        model_version = parsed.get("model_version")
        raw_heads = parsed.get("heads")
        if not isinstance(model_version, str) or not model_version:
            self._error = "model metadata missing model_version"
            return
        if not isinstance(raw_heads, dict):
            self._error = "model metadata missing heads"
            return

        try:
            np: Any = importlib.import_module("numpy")
            ort: Any = importlib.import_module("onnxruntime")
        except ImportError as exc:
            self._error = f"missing inference dependency: {exc}"
            return

        root = metadata_path.parent.resolve()
        loaded: dict[str, _LoadedHead] = {}
        try:
            for head_name in HEAD_NAMES:
                raw_head = raw_heads.get(head_name)
                if not isinstance(raw_head, dict):
                    raise ValueError(f"missing metadata for head {head_name}")

                relative_path = raw_head.get("path")
                expected_sha = raw_head.get("sha256")
                input_name = raw_head.get("input_name")
                probabilities_output = raw_head.get("probabilities_output")
                raw_classes = raw_head.get("classes")
                if not isinstance(relative_path, str) or not relative_path:
                    raise ValueError(f"invalid artifact path for head {head_name}")
                if not isinstance(expected_sha, str) or not expected_sha:
                    raise ValueError(f"invalid artifact checksum for head {head_name}")
                if not isinstance(input_name, str) or not input_name:
                    raise ValueError(f"invalid input name for head {head_name}")
                if not isinstance(probabilities_output, str) or not probabilities_output:
                    raise ValueError(f"invalid probability output for head {head_name}")
                if not isinstance(raw_classes, list) or not raw_classes:
                    raise ValueError(f"missing class metadata for head {head_name}")
                if not all(isinstance(value, str) and value for value in raw_classes):
                    raise ValueError(f"invalid class metadata for head {head_name}")

                model_path = (root / relative_path).resolve()
                if not model_path.is_relative_to(root):
                    raise ValueError(f"artifact path escapes metadata directory for {head_name}")
                if not model_path.is_file():
                    raise ValueError(f"model artifact missing for {head_name}: {model_path}")
                if _sha256_of(model_path).lower() != expected_sha.lower():
                    raise ValueError(f"model artifact checksum mismatch for {head_name}")

                session = ort.InferenceSession(
                    str(model_path),
                    providers=["CPUExecutionProvider"],
                )
                session_inputs = {item.name for item in session.get_inputs()}
                session_outputs = {item.name for item in session.get_outputs()}
                if input_name not in session_inputs:
                    raise ValueError(f"input {input_name} absent from {head_name} artifact")
                if probabilities_output not in session_outputs:
                    raise ValueError(
                        f"output {probabilities_output} absent from {head_name} artifact"
                    )
                loaded[head_name] = _LoadedHead(
                    session=session,
                    input_name=input_name,
                    probabilities_output=probabilities_output,
                    classes=tuple(raw_classes),
                )
        except Exception as exc:  # noqa: BLE001 - fail closed at load, runtime then fails open
            self._error = f"model load failed: {exc}"
            self._heads.clear()
            return

        self._np = np
        self._heads = loaded
        self._metadata_sha256 = actual_metadata_sha
        self._model_version = f"{model_version}+{actual_metadata_sha[:12]}"
        self._ready = True

    def health(self) -> dict[str, object]:
        return {
            "ready": self._ready,
            "mode": "onnx-baseline-tfidf",
            "model_version": self._model_version,
            "metadata_sha256": self._metadata_sha256,
            "heads_loaded": len(self._heads),
            **({"error": self._error} if self._error else {}),
        }

    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        if not self._ready or self._np is None or self._model_version is None:
            raise RuntimeError("onnx classifier not ready")
        text = serialize_input(item)
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._infer, text),
                timeout=self._config.timeout_ms / 1000,
            )
        except TimeoutError as exc:
            raise TimeoutError("onnx inference exceeded timeout") from exc

    def _infer(self, text: str) -> ClassificationResult:
        np = self._np
        if np is None or self._model_version is None:
            raise RuntimeError("onnx classifier not ready")

        predicted: dict[str, str] = {}
        scores: dict[str, float] = {}
        selected_scores: dict[str, float] = {}
        input_tensor = np.asarray([[text]], dtype=object)

        for head_name in HEAD_NAMES:
            loaded = self._heads[head_name]
            outputs = loaded.session.run(
                [loaded.probabilities_output],
                {loaded.input_name: input_tensor},
            )
            probabilities = np.asarray(outputs[0], dtype=float).reshape(-1)
            if len(probabilities) != len(loaded.classes):
                raise ValueError(
                    f"{head_name} probability count {len(probabilities)} "
                    f"does not match class count {len(loaded.classes)}"
                )
            best_index = int(np.argmax(probabilities))
            class_name = loaded.classes[best_index]
            predicted[head_name] = class_name
            selected_scores[head_name] = _bounded(float(probabilities[best_index]))
            for class_index, value in enumerate(probabilities):
                scores[f"{head_name}:{loaded.classes[class_index]}"] = _bounded(float(value))

        source_action = predicted["action"]
        message_action = (
            MessageAction.BLOCK if source_action == "BLOCK" else MessageAction.ALLOW
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
            confidence=selected_scores["label"],
            rule_hits=(),
            reason_codes=("onnx_local_classifier",),
            related_message_ids=(),
            evidence_event_ids=(),
            model_version=self._model_version,
        )
