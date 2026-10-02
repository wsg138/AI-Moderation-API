from __future__ import annotations

from typing import Protocol

from .models import Action, ClassificationInput, ClassificationResult, Label


class LocalClassifier(Protocol):
    async def classify(self, item: ClassificationInput) -> ClassificationResult: ...

    def health(self) -> dict[str, object]: ...


class StubClassifier:
    """Fail-open placeholder until the separately trained local classifier is integrated."""

    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        del item
        return ClassificationResult(
            action=Action.ALLOW,
            label=Label.AMBIGUOUS_REVIEW,
            scores={},
            rule_hits=(),
            reason_codes=("classifier_stub_fail_open",),
            related_message_ids=(),
            model_version="stub-v1",
        )

    def health(self) -> dict[str, object]:
        return {"ready": False, "mode": "stub", "model_version": "stub-v1"}
