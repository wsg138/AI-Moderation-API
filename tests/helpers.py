from __future__ import annotations

from datetime import UTC, datetime, timedelta

from moderation_api.models import (
    ClassificationResult,
    Containment,
    Label,
    MessageAction,
    ReviewPriority,
    StrikeRecommendation,
    SupportFlow,
)

BASE_TIME = datetime.now(UTC).replace(microsecond=0)


def payload(
    message_id: str,
    text: str,
    seconds: int = 0,
    **updates: object,
) -> dict[str, object]:
    body: dict[str, object] = {
        "platform": "minecraft",
        "channel_profile": "minecraft_public",
        "scope_id": "smp",
        "channel_id": "global",
        "external_message_id": message_id,
        "sender_id": "player-a",
        "occurred_at": (BASE_TIME + timedelta(seconds=seconds)).isoformat(),
        "text": text,
    }
    body.update(updates)
    return body


def result(
    *,
    action: MessageAction = MessageAction.ALLOW,
    label: Label = Label.SAFE,
    review: ReviewPriority = ReviewPriority.NONE,
    strike: StrikeRecommendation = StrikeRecommendation.NONE,
    containment: Containment = Containment.NONE,
    duration: int | None = None,
    support: SupportFlow = SupportFlow.NONE,
    related: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    reasons: tuple[str, ...] = ("test",),
) -> ClassificationResult:
    return ClassificationResult(
        message_action=action,
        semantic_label=label,
        review_priority=review,
        strike_recommendation=strike,
        containment=containment,
        containment_duration_seconds=duration,
        support_flow=support,
        scores={label.value: 0.9},
        confidence=0.9,
        rule_hits=(),
        reason_codes=reasons,
        related_message_ids=related,
        evidence_event_ids=evidence,
        model_version="test-v1",
    )
