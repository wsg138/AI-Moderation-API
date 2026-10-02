from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Action(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class Label(StrEnum):
    SAFE = "SAFE"
    GAMEPLAY_VIOLENCE = "GAMEPLAY_VIOLENCE"
    LOW_LEVEL_HARASSMENT = "LOW_LEVEL_HARASSMENT"
    SEVERE_HARASSMENT = "SEVERE_HARASSMENT"
    REAL_WORLD_THREAT = "REAL_WORLD_THREAT"
    SELF_HARM_INSTRUCTION = "SELF_HARM_INSTRUCTION"
    SELF_HARM_INTENT = "SELF_HARM_INTENT"
    HATE = "HATE"
    SEXUAL_MINOR = "SEXUAL_MINOR"
    DANGEROUS_REAL_WORLD_INSTRUCTIONS = "DANGEROUS_REAL_WORLD_INSTRUCTIONS"
    AMBIGUOUS_REVIEW = "AMBIGUOUS_REVIEW"


class AdvisoryStatus(StrEnum):
    DISABLED = "DISABLED"
    QUEUED = "QUEUED"
    QUEUE_SATURATED = "QUEUE_SATURATED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModerationRequest(ApiModel):
    platform: Annotated[str, Field(min_length=1, max_length=32)]
    scope_id: Annotated[str, Field(min_length=1, max_length=160)]
    channel_id: Annotated[str | None, Field(max_length=160)] = None
    external_message_id: Annotated[str, Field(min_length=1, max_length=200)]
    sender_id: Annotated[str, Field(min_length=1, max_length=200)]
    occurred_at: datetime
    text: Annotated[str, Field(min_length=1, max_length=4096)]
    reply_to_message_id: Annotated[str | None, Field(max_length=200)] = None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value.astimezone(UTC)


class ModerationResponse(ApiModel):
    event_id: str | None
    action: Action
    label: Label
    scores: dict[str, float]
    rule_hits: list[str]
    reason_codes: list[str]
    related_message_ids: list[str]
    local_model_version: str
    policy_version: str
    advisory_status: AdvisoryStatus
    latency_ms: int
    degraded: bool = False
    fallback_state: str | None = None
    idempotent_replay: bool = False


class ReviewRequest(ApiModel):
    event_id: Annotated[str, Field(min_length=1, max_length=64)]
    reviewer_id: Annotated[str, Field(min_length=1, max_length=200)]
    label: Label
    action: Action
    reason_codes: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list,
        max_length=32,
    )
    note: Annotated[str | None, Field(max_length=1200)] = None


class ReviewResponse(ApiModel):
    review_id: str
    event_id: str
    reviewer_id: str
    label: Label
    action: Action
    reason_codes: list[str]
    note: str | None
    created_at: datetime


class AdvisoryEvidence(ApiModel):
    status: AdvisoryStatus
    model: str | None = None
    flagged: bool | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    categories: dict[str, bool] = Field(default_factory=dict)
    error_code: str | None = None
    latency_ms: int | None = None
    disagrees_with_local: bool | None = None


class EventDetails(ApiModel):
    event_id: str
    client_id: str
    platform: str
    scope_id: str
    channel_id: str | None
    external_message_id: str
    sender_id: str
    occurred_at: datetime
    text: str
    reply_to_message_id: str | None
    decision: ModerationResponse
    advisory: AdvisoryEvidence | None = None
    reviews: list[ReviewResponse] = Field(default_factory=list)


class HealthResponse(ApiModel):
    status: str
    ready: bool
    request_queue_depth: int
    request_queue_capacity: int
    request_workers: int
    classifier_ready: bool
    classifier_mode: str
    local_model_version: str | None
    advisory_enabled: bool
    advisory_queue_depth: int
    advisory_queue_capacity: int


@dataclass(frozen=True, slots=True)
class ContextMessage:
    platform: str
    scope_id: str
    channel_id: str | None
    external_message_id: str
    sender_id: str
    occurred_at: datetime
    text: str
    reply_to_message_id: str | None


@dataclass(frozen=True, slots=True)
class ClassificationInput:
    current: ContextMessage
    context: tuple[ContextMessage, ...]


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    action: Action
    label: Label
    scores: dict[str, float]
    rule_hits: tuple[str, ...]
    reason_codes: tuple[str, ...]
    related_message_ids: tuple[str, ...]
    model_version: str
