from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Platform(StrEnum):
    MINECRAFT = "minecraft"
    DISCORD = "discord"


class ChannelProfile(StrEnum):
    MINECRAFT_PUBLIC = "minecraft_public"
    MINECRAFT_PRIVATE = "minecraft_private"
    DISCORD_GENERAL = "discord_general"
    DISCORD_GAMING = "discord_gaming"
    DISCORD_STAFF_EXEMPT = "discord_staff_exempt"
    DISCORD_TICKET_EXEMPT = "discord_ticket_exempt"
    DISCORD_CONFIGURED_EXEMPT = "discord_configured_exempt"

    @property
    def exempt(self) -> bool:
        return self in {
            self.DISCORD_STAFF_EXEMPT,
            self.DISCORD_TICKET_EXEMPT,
            self.DISCORD_CONFIGURED_EXEMPT,
        }


class MessageAction(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class ReviewPriority(StrEnum):
    NONE = "NONE"
    NORMAL = "NORMAL"
    URGENT = "URGENT"


class StrikeRecommendation(StrEnum):
    NONE = "NONE"
    EVIDENCE = "EVIDENCE"
    STRIKE = "STRIKE"


class Containment(StrEnum):
    NONE = "NONE"
    MUTE = "MUTE"


class SupportFlow(StrEnum):
    NONE = "NONE"
    SELF_HARM_CHECK = "SELF_HARM_CHECK"
    TARGET_SAFETY_CHECK = "TARGET_SAFETY_CHECK"


class IngestionStatus(StrEnum):
    INGESTED = "INGESTED"
    SKIPPED_EXEMPT = "SKIPPED_EXEMPT"
    FAIL_OPEN = "FAIL_OPEN"


class Label(StrEnum):
    SAFE = "SAFE"
    GAMEPLAY_VIOLENCE = "GAMEPLAY_VIOLENCE"
    LOW_LEVEL_HARASSMENT = "LOW_LEVEL_HARASSMENT"
    SEVERE_HARASSMENT = "SEVERE_HARASSMENT"
    STAFF_TARGETED_ABUSE = "STAFF_TARGETED_ABUSE"
    REAL_WORLD_THREAT = "REAL_WORLD_THREAT"
    SELF_HARM_INSTRUCTION = "SELF_HARM_INSTRUCTION"
    SELF_HARM_INTENT = "SELF_HARM_INTENT"
    THIRD_PARTY_SELF_HARM_CONCERN = "THIRD_PARTY_SELF_HARM_CONCERN"
    HATE = "HATE"
    SLUR_USE = "SLUR_USE"
    SEXUAL_CONTENT = "SEXUAL_CONTENT"
    SEXUAL_MINOR = "SEXUAL_MINOR"
    DOXXING = "DOXXING"
    BLACKMAIL = "BLACKMAIL"
    GROOMING = "GROOMING"
    DANGEROUS_REAL_WORLD_INSTRUCTIONS = "DANGEROUS_REAL_WORLD_INSTRUCTIONS"
    AMBIGUOUS_REVIEW = "AMBIGUOUS_REVIEW"


class AdvisoryStatus(StrEnum):
    DISABLED = "DISABLED"
    QUEUED = "QUEUED"
    QUEUE_SATURATED = "QUEUE_SATURATED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class IncidentKind(StrEnum):
    HARASSMENT = "HARASSMENT"
    DOGPILE = "DOGPILE"
    THREAT = "THREAT"
    DOXXING = "DOXXING"
    BLACKMAIL = "BLACKMAIL"
    GROOMING = "GROOMING"
    SAFETY = "SAFETY"
    OTHER = "OTHER"


class CorrectionAuthority(StrEnum):
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class CorrectionStatus(StrEnum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class CorrectionVote(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class MemoryKind(StrEnum):
    INCIDENT = "INCIDENT"
    STRIKE_EVIDENCE = "STRIKE_EVIDENCE"
    TARGET_HARASSMENT = "TARGET_HARASSMENT"
    UNWANTED_CONTACT = "UNWANTED_CONTACT"
    MUTUAL_BANTER = "MUTUAL_BANTER"
    TARGET_STRICT_FILTER = "TARGET_STRICT_FILTER"
    STAFF_OUTCOME = "STAFF_OUTCOME"
    AGE_CLUE = "AGE_CLUE"


class SafetyMemoryKind(StrEnum):
    SAFETY_CHECK = "SAFETY_CHECK"
    SAFETY_CONCERN = "SAFETY_CONCERN"


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ShortId = Annotated[str, Field(min_length=1, max_length=200)]
ReasonCode = Annotated[str, Field(min_length=1, max_length=80)]


class MessageRef(ApiModel):
    platform: Platform
    scope_id: str
    channel_id: str | None = None
    external_message_id: str


class ModerationRequest(ApiModel):
    platform: Platform
    channel_profile: ChannelProfile
    scope_id: Annotated[str, Field(min_length=1, max_length=160)]
    channel_id: Annotated[str | None, Field(max_length=160)] = None
    conversation_id: Annotated[str | None, Field(max_length=200)] = None
    external_message_id: ShortId
    canonical_message_id: Annotated[str | None, Field(max_length=200)] = None
    sender_id: ShortId
    sender_identity_id: Annotated[str | None, Field(max_length=200)] = None
    recipient_ids: list[ShortId] = Field(default_factory=list, max_length=16)
    recipient_identity_ids: list[ShortId] = Field(default_factory=list, max_length=16)
    target_ids: list[ShortId] = Field(default_factory=list, max_length=16)
    target_identity_ids: list[ShortId] = Field(default_factory=list, max_length=16)
    occurred_at: datetime
    text: Annotated[str, Field(min_length=1, max_length=4096)]
    reply_to_message_id: Annotated[str | None, Field(max_length=200)] = None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_matching_profile(self) -> ModerationRequest:
        minecraft = {
            ChannelProfile.MINECRAFT_PUBLIC,
            ChannelProfile.MINECRAFT_PRIVATE,
        }
        if self.platform is Platform.MINECRAFT and self.channel_profile not in minecraft:
            raise ValueError("Minecraft requests require a Minecraft channel profile")
        if self.platform is Platform.DISCORD and self.channel_profile in minecraft:
            raise ValueError("Discord requests require a Discord channel profile")
        return self


class IncidentSummary(ApiModel):
    incident_id: str
    kind: IncidentKind
    severity: Annotated[int, Field(ge=0, le=100)]
    coordinated: bool = False
    participant_ids: list[str] = Field(default_factory=list)
    target_ids: list[str] = Field(default_factory=list)


class ModerationResponse(ApiModel):
    event_id: str | None
    ingestion_status: IngestionStatus
    message_action: MessageAction
    semantic_label: Label
    review_priority: ReviewPriority
    strike_recommendation: StrikeRecommendation
    containment: Containment
    containment_duration_seconds: int | None = Field(default=None, ge=1)
    support_flow: SupportFlow
    scores: dict[str, float]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    rule_hits: list[str]
    reason_codes: list[str]
    related_message_ids: list[str]
    related_messages: list[MessageRef]
    incident: IncidentSummary | None = None
    local_model_version: str
    policy_version: str
    advisory_status: AdvisoryStatus
    latency_ms: int
    degraded: bool = False
    fallback_state: str | None = None
    idempotent_replay: bool = False


class CorrectionDecision(ApiModel):
    semantic_label: Label
    message_action: MessageAction
    review_priority: ReviewPriority
    strike_recommendation: StrikeRecommendation
    containment: Containment
    containment_duration_seconds: int | None = Field(default=None, ge=1)
    support_flow: SupportFlow
    reason_codes: list[ReasonCode] = Field(default_factory=list, max_length=32)


class CorrectionRequest(ApiModel):
    event_id: Annotated[str, Field(min_length=1, max_length=64)]
    reviewer_id: ShortId
    authority: CorrectionAuthority
    corrected: CorrectionDecision
    note: Annotated[str | None, Field(max_length=1200)] = None


class CorrectionRejectRequest(ApiModel):
    reviewer_id: ShortId
    authority: CorrectionAuthority
    note: Annotated[str | None, Field(max_length=1200)] = None


class CorrectionResponse(ApiModel):
    proposal_id: str
    event_id: str
    status: CorrectionStatus
    corrected: CorrectionDecision
    approvals: int
    rejections: int
    created_at: datetime
    resolved_at: datetime | None = None


class AdvisoryEvidence(ApiModel):
    status: AdvisoryStatus
    model: str | None = None
    flagged: bool | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    categories: dict[str, bool] = Field(default_factory=dict)
    error_code: str | None = None
    latency_ms: int | None = None
    disagrees_with_local: bool | None = None


class ContextEvidence(ApiModel):
    event_id: str
    message: MessageRef
    sender_id: str
    occurred_at: datetime
    text: str


class EventDetails(ApiModel):
    event_id: str
    client_id: str
    platform: Platform
    channel_profile: ChannelProfile
    scope_id: str
    channel_id: str | None
    conversation_id: str | None
    external_message_id: str
    canonical_message_id: str | None
    sender_id: str
    occurred_at: datetime
    text: str
    reply_to_message_id: str | None
    decision: ModerationResponse
    advisory: AdvisoryEvidence | None = None
    corrections: list[CorrectionResponse] = Field(default_factory=list)
    accepted_correction: CorrectionResponse | None = None
    context_evidence: list[ContextEvidence] = Field(default_factory=list)


class ReviewItem(ApiModel):
    event_id: str
    occurred_at: datetime
    platform: Platform
    channel_profile: ChannelProfile
    semantic_label: Label
    message_action: MessageAction
    review_priority: ReviewPriority
    reason_codes: list[str]
    incident_id: str | None = None


class ReviewQueueResponse(ApiModel):
    items: list[ReviewItem]


class HealthResponse(ApiModel):
    status: str
    ready: bool
    schema_version: int | None
    request_queue_depth: int
    request_queue_capacity: int
    request_workers: int
    classifier_ready: bool
    classifier_mode: str
    local_model_version: str | None
    advisory_enabled: bool
    advisory_queue_depth: int
    advisory_queue_capacity: int
    rehydrated_context_messages: int
    context_ready: bool


@dataclass(frozen=True, slots=True)
class ContextMessage:
    event_id: str
    platform: Platform
    channel_profile: ChannelProfile
    scope_id: str
    channel_id: str | None
    conversation_id: str | None
    external_message_id: str
    canonical_message_id: str | None
    sender_id: str
    sender_identity_id: str | None
    recipient_ids: tuple[str, ...]
    recipient_identity_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    target_identity_ids: tuple[str, ...]
    occurred_at: datetime
    text: str
    reply_to_message_id: str | None


@dataclass(frozen=True, slots=True)
class MemoryFact:
    memory_id: str
    kind: MemoryKind
    subject_id: str
    target_id: str | None
    platform: Platform
    payload: dict[str, Any]
    confidence: float
    source: str
    confirmed: bool
    created_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class SafetyMemoryFact:
    memory_id: str
    kind: SafetyMemoryKind
    subject_id: str
    payload: dict[str, Any]
    confidence: float
    source: str
    created_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    punishment: tuple[MemoryFact, ...] = ()
    safety: tuple[SafetyMemoryFact, ...] = ()


@dataclass(frozen=True, slots=True)
class ClassificationInput:
    current: ContextMessage
    context: tuple[ContextMessage, ...]
    memory: MemorySnapshot


@dataclass(frozen=True, slots=True)
class IncidentSignal:
    incident_key: str
    kind: IncidentKind
    severity: int
    participant_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    coordinated: bool = False


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    message_action: MessageAction
    semantic_label: Label
    review_priority: ReviewPriority
    strike_recommendation: StrikeRecommendation
    containment: Containment
    containment_duration_seconds: int | None
    support_flow: SupportFlow
    scores: dict[str, float]
    confidence: float | None
    rule_hits: tuple[str, ...]
    reason_codes: tuple[str, ...]
    related_message_ids: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    model_version: str
    incident: IncidentSignal | None = None
