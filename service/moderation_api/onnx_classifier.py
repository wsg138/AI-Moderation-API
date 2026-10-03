"""W12 runtime adapter: ONNX-backed local classifier.

Implements the LocalClassifier protocol using a frozen ONNX export plus its
tokenizer/config artifacts. Fail-open: any load/inference problem reports
not-ready (or raises, letting the runtime fail open) — never a blocking
decision from a broken model.

Configuration (environment):
  AI_MOD_ONNX_MODEL_PATH   path to the .onnx artifact (required)
  AI_MOD_ONNX_TOKENIZER_DIR directory with vocab.txt (required)
  AI_MOD_ONNX_MODEL_SHA256 expected SHA-256 of the artifact (required)
  AI_MOD_ONNX_MODEL_VERSION model version string (required)
  AI_MOD_ONNX_MAX_LEN       max sequence length (default 128)
  AI_MOD_ONNX_TIMEOUT_MS    per-inference timeout guard (default 500)

No network access at startup. No hardcoded developer paths.
"""

from __future__ import annotations

import hashlib
import os
import time
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

LABELS = [label.value for label in Label]
ACTIONS = ["ALLOW", "BLOCK", "REVIEW"]
REVIEW_PRIORITIES = [p.value for p in ReviewPriority]
CONTAINMENTS = [c.value for c in Containment]
SUPPORT_FLOWS = [s.value for s in SupportFlow]
CLASSES = {
    "label": LABELS,
    "action": ACTIONS,
    "review_priority": REVIEW_PRIORITIES,
    "strike": ["false", "true"],
    "containment": CONTAINMENTS,
    "support_flow": SUPPORT_FLOWS,
}


def serialize_input(item: ClassificationInput) -> str:
    """Deterministic preprocessing identical to training serialization."""
    profile = item.current.channel_profile.value
    parts = [f"[PROFILE={profile}]"]
    # Bounded prior context, oldest first, then the current message as target.
    context = list(item.context)[-20:]
    base_ms = context[0].occurred_at.timestamp() * 1000 if context else 0
    for seq, msg in enumerate(context):
        offset = max(0, int(msg.occurred_at.timestamp() * 1000 - base_ms))
        parts.append(f"[CTX{seq}@+{offset}ms] {msg.text}")
    cur_offset = 0
    if context:
        cur_offset = max(0, int(item.current.occurred_at.timestamp() * 1000 - base_ms))
    parts.append(f"[CUR@+{cur_offset}ms] [TARGET] {item.current.text}")
    return "\n".join(parts)


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class OnnxClassifierConfig:
    model_path: Path
    tokenizer_dir: Path
    expected_sha256: str
    model_version: str
    max_len: int = 128
    timeout_ms: int = 500

    @classmethod
    def from_env(cls) -> OnnxClassifierConfig:
        def req(name: str) -> str:
            value = os.environ.get(name)
            if not value:
                raise RuntimeError(f"missing required env var {name}")
            return value

        return cls(
            model_path=Path(req("AI_MOD_ONNX_MODEL_PATH")),
            tokenizer_dir=Path(req("AI_MOD_ONNX_TOKENIZER_DIR")),
            expected_sha256=req("AI_MOD_ONNX_MODEL_SHA256"),
            model_version=req("AI_MOD_ONNX_MODEL_VERSION"),
            max_len=int(os.environ.get("AI_MOD_ONNX_MAX_LEN", "128")),
            timeout_ms=int(os.environ.get("AI_MOD_ONNX_TIMEOUT_MS", "500")),
        )


class OnnxClassifier:
    """Fail-open ONNX local classifier."""

    def __init__(self, config: OnnxClassifierConfig) -> None:
        self._config = config
        self._ready = False
        self._error: str | None = None
        self._session: Any = None
        self._tokenizer: Any = None
        self._load()

    def _load(self) -> None:
        try:
            import numpy as np  # noqa: F401  (used at inference)
            import onnxruntime as ort  # type: ignore[import-untyped]
            from transformers import BertTokenizer
        except ImportError as exc:
            self._error = f"missing inference dependency: {exc}"
            return
        if not self._config.model_path.is_file():
            self._error = f"model artifact missing: {self._config.model_path}"
            return
        if not (self._config.tokenizer_dir / "vocab.txt").is_file():
            self._error = f"tokenizer vocab missing in {self._config.tokenizer_dir}"
            return
        actual = _sha256_of(self._config.model_path)
        if actual != self._config.expected_sha256:
            self._error = "model artifact checksum mismatch"
            return
        try:
            self._session = ort.InferenceSession(
                str(self._config.model_path), providers=["CPUExecutionProvider"]
            )
            self._tokenizer = BertTokenizer(
                str(self._config.tokenizer_dir / "vocab.txt"), do_lower_case=True
            )
        except Exception as exc:  # noqa: BLE001 — fail-open, record and stay not-ready
            self._error = f"model load failed: {exc}"
            return
        self._ready = True

    def health(self) -> dict[str, object]:
        return {
            "ready": self._ready,
            "mode": "onnx",
            "model_version": self._config.model_version,
            **({"error": self._error} if self._error else {}),
        }

    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        if not self._ready or self._session is None or self._tokenizer is None:
            raise RuntimeError("onnx classifier not ready")
        import numpy as np

        text = serialize_input(item)
        enc = self._tokenizer(
            text, max_length=self._config.max_len, truncation=True,
            padding="max_length", return_tensors="np",
        )
        deadline = time.monotonic() + self._config.timeout_ms / 1000
        outputs = self._session.run(
            [f"logits_{name}" for name in HEAD_NAMES],
            {
                "input_ids": enc["input_ids"].astype(np.int64),
                "attention_mask": enc["attention_mask"].astype(np.int64),
            },
        )
        if time.monotonic() > deadline:
            raise TimeoutError("onnx inference exceeded timeout")

        preds: dict[str, int] = {}
        scores: dict[str, float] = {}
        for name, logits in zip(HEAD_NAMES, outputs, strict=True):
            arr = np.asarray(logits)[0]
            # Numerically stable softmax
            shifted = arr - arr.max()
            exp = np.exp(shifted)
            probs = exp / exp.sum()
            best = int(np.argmax(probs))
            preds[name] = best
            scores[f"{name}:{CLASSES[name][best]}"] = round(float(probs[best]), 4)

        # Dataset REVIEW -> runtime ALLOW + review priority (never add REVIEW action)
        action_name = ACTIONS[preds["action"]]
        message_action = MessageAction.BLOCK if action_name == "BLOCK" else MessageAction.ALLOW
        strike_bool = preds["strike"] == 1
        strike_rec = StrikeRecommendation.STRIKE if strike_bool else StrikeRecommendation.NONE

        # Conservative deterministic containment duration: only where the model
        # predicts MUTE do we return a duration, and only the policy-anchored
        # values would be set here — default None preserves review behavior.
        containment = Containment(CLASSES["containment"][preds["containment"]])

        return ClassificationResult(
            message_action=message_action,
            semantic_label=Label(CLASSES["label"][preds["label"]]),
            review_priority=ReviewPriority(CLASSES["review_priority"][preds["review_priority"]]),
            strike_recommendation=strike_rec,
            containment=containment,
            containment_duration_seconds=None,
            support_flow=SupportFlow(CLASSES["support_flow"][preds["support_flow"]]),
            scores={k: max(0.0, min(1.0, v)) for k, v in scores.items()},
            confidence=scores.get(f"label:{CLASSES['label'][preds['label']]}"),
            rule_hits=(),
            reason_codes=("onnx_local_classifier",),
            related_message_ids=(),
            evidence_event_ids=(),
            model_version=self._config.model_version,
        )
