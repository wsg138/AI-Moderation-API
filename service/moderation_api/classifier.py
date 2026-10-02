from __future__ import annotations

from typing import Protocol

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


class LocalClassifier(Protocol):
    async def classify(self, item: ClassificationInput) -> ClassificationResult: ...

    def health(self) -> dict[str, object]: ...


class StubClassifier:
    """Fail-open placeholder until the separately trained local classifier is integrated."""

    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        del item
        return _stub_result()

    def health(self) -> dict[str, object]:
        return {"ready": False, "mode": "stub", "model_version": "stub-v1"}


def _stub_result() -> ClassificationResult:
    return ClassificationResult(
        message_action=MessageAction.ALLOW,
        semantic_label=Label.AMBIGUOUS_REVIEW,
        review_priority=ReviewPriority.NONE,
        strike_recommendation=StrikeRecommendation.NONE,
        containment=Containment.NONE,
        containment_duration_seconds=None,
        support_flow=SupportFlow.NONE,
        scores={},
        confidence=None,
        rule_hits=(),
        reason_codes=("classifier_stub_fail_open",),
        related_message_ids=(),
        evidence_event_ids=(),
        model_version="stub-v1",
    )
