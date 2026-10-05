from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from enum import StrEnum
from uuid import NAMESPACE_URL, uuid5

from .models import (
    ChannelProfile,
    Label,
    MessageAction,
    Platform,
    ReviewPriority,
    StrikeRecommendation,
    SupportFlow,
)


class HumanReviewState(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    OVERTURNED = "OVERTURNED"


@dataclass(frozen=True, slots=True)
class EvasionLinkPolicy:
    max_gap_seconds: int = 90
    high_confidence: float = 0.90
    character_similarity: float = 0.84
    token_similarity: float = 0.65
    semantic_similarity: float = 0.82
    containment_ratio: float = 0.60


@dataclass(frozen=True, slots=True)
class RelationContext:
    mirrored_copy: bool = False
    quote_or_report: bool = False
    apology_or_correction: bool = False
    appeal_or_review_discussion: bool = False


@dataclass(frozen=True, slots=True)
class ModerationSnapshot:
    event_id: str
    platform: Platform
    channel_profile: ChannelProfile
    scope_id: str
    sender_id: str
    sender_identity_id: str | None
    canonical_message_id: str | None
    occurred_at: datetime
    text: str
    semantic_label: Label
    message_action: MessageAction
    confidence: float | None
    review_priority: ReviewPriority
    strike_recommendation: StrikeRecommendation
    support_flow: SupportFlow
    human_review_state: HumanReviewState = HumanReviewState.UNREVIEWED
    chain_root_event_id: str | None = None
    evasion_depth: int = 0


@dataclass(frozen=True, slots=True)
class EvasionFeatures:
    gap_seconds: float
    same_actor: bool
    same_semantic_label: bool
    character_similarity: float
    token_similarity: float
    semantic_similarity: float | None
    containment_match: bool


@dataclass(frozen=True, slots=True)
class EnthusiaStaffStrikeEvidence:
    evidence_type: str
    chain_id: str
    root_event_id: str
    prior_event_id: str
    current_event_id: str
    attempt_index: int
    relation_score: float
    reason_codes: tuple[str, ...]
    current_strike_recommendation: StrikeRecommendation
    automatic_punishment_allowed: bool = False


@dataclass(frozen=True, slots=True)
class EvasionLinkDecision:
    linked: bool
    relation_score: float
    reason_codes: tuple[str, ...]
    blocker_codes: tuple[str, ...]
    features: EvasionFeatures
    chain_id: str | None = None
    root_event_id: str | None = None
    attempt_index: int = 0

    def staff_evidence(
        self,
        prior: ModerationSnapshot,
        current: ModerationSnapshot,
    ) -> EnthusiaStaffStrikeEvidence | None:
        if not self.linked or self.chain_id is None or self.root_event_id is None:
            return None
        return EnthusiaStaffStrikeEvidence(
            evidence_type="EVASION_CHAIN",
            chain_id=self.chain_id,
            root_event_id=self.root_event_id,
            prior_event_id=prior.event_id,
            current_event_id=current.event_id,
            attempt_index=self.attempt_index,
            relation_score=self.relation_score,
            reason_codes=self.reason_codes,
            current_strike_recommendation=current.strike_recommendation,
        )


_LEET_TRANSLATION = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)
_WORD_RE = re.compile(r"[a-z0-9]+")
_SAFETY_LABELS = frozenset({Label.SELF_HARM_INTENT, Label.THIRD_PARTY_SELF_HARM_CONCERN})


def link_evasion_attempt(
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    *,
    relation: RelationContext | None = None,
    semantic_similarity: float | None = None,
    policy: EvasionLinkPolicy | None = None,
) -> EvasionLinkDecision:
    relation = relation or RelationContext()
    policy = policy or EvasionLinkPolicy()
    features = _features(prior, current, semantic_similarity)
    blockers = _blockers(prior, current, relation, features, policy)
    if blockers:
        return EvasionLinkDecision(False, 0.0, (), blockers, features)
    score, reasons = _relationship_score(prior, current, features, policy)
    if not reasons:
        return EvasionLinkDecision(False, score, (), ("insufficient_similarity",), features)
    root = prior.chain_root_event_id or prior.event_id
    attempt_index = prior.evasion_depth + 1
    chain_id = str(uuid5(NAMESPACE_URL, f"enthusia-evasion:{_actor_key(prior)}:{root}"))
    return EvasionLinkDecision(
        True,
        score,
        tuple(reasons),
        (),
        features,
        chain_id=chain_id,
        root_event_id=root,
        attempt_index=attempt_index,
    )


def _features(
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    semantic_similarity: float | None,
) -> EvasionFeatures:
    prior_tokens, prior_compact = _normalize(prior.text)
    current_tokens, current_compact = _normalize(current.text)
    return EvasionFeatures(
        gap_seconds=max(0.0, (current.occurred_at - prior.occurred_at).total_seconds()),
        same_actor=_same_actor(prior, current),
        same_semantic_label=prior.semantic_label is current.semantic_label,
        character_similarity=_character_similarity(prior_compact, current_compact),
        token_similarity=_token_similarity(prior_tokens, current_tokens),
        semantic_similarity=_bounded_similarity(semantic_similarity),
        containment_match=_containment_match(prior_compact, current_compact),
    )


def _blockers(
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    relation: RelationContext,
    features: EvasionFeatures,
    policy: EvasionLinkPolicy,
) -> tuple[str, ...]:
    blockers: list[str] = []
    _append_relation_blockers(blockers, prior, current, relation)
    _append_decision_blockers(blockers, prior, current, policy)
    if not features.same_actor:
        blockers.append("different_actor")
    if current.occurred_at < prior.occurred_at:
        blockers.append("time_order_invalid")
    elif features.gap_seconds > policy.max_gap_seconds:
        blockers.append("outside_evasion_window")
    return tuple(dict.fromkeys(blockers))


def _append_relation_blockers(
    blockers: list[str],
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    relation: RelationContext,
) -> None:
    if relation.mirrored_copy or _same_canonical(prior, current):
        blockers.append("mirrored_copy")
    if relation.quote_or_report:
        blockers.append("quote_or_report")
    if relation.apology_or_correction:
        blockers.append("apology_or_correction")
    if relation.appeal_or_review_discussion:
        blockers.append("appeal_or_review_discussion")


def _append_decision_blockers(
    blockers: list[str],
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    policy: EvasionLinkPolicy,
) -> None:
    _append_prior_decision_blockers(blockers, prior, policy)
    _append_current_decision_blockers(blockers, current)
    if _is_safety_event(prior) or _is_safety_event(current):
        blockers.append("safety_event_excluded")


def _append_prior_decision_blockers(
    blockers: list[str],
    prior: ModerationSnapshot,
    policy: EvasionLinkPolicy,
) -> None:
    if prior.message_action is not MessageAction.BLOCK:
        blockers.append("prior_not_blocked")
    if prior.confidence is None or prior.confidence < policy.high_confidence:
        blockers.append("prior_not_high_confidence")
    if prior.human_review_state in {HumanReviewState.PENDING, HumanReviewState.OVERTURNED}:
        blockers.append("prior_not_reliable")


def _append_current_decision_blockers(
    blockers: list[str],
    current: ModerationSnapshot,
) -> None:
    if current.human_review_state is HumanReviewState.OVERTURNED:
        blockers.append("current_overturned")
    if current.message_action is not MessageAction.BLOCK:
        blockers.append("current_not_independently_blocked")


def _relationship_score(
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    features: EvasionFeatures,
    policy: EvasionLinkPolicy,
) -> tuple[float, list[str]]:
    scores = _similarity_scores(features)
    reasons = _similarity_reasons(prior, current, features, policy)
    if reasons and features.same_semantic_label:
        reasons.append("same_semantic_label")
    return round(max(scores), 6), reasons


def _similarity_scores(features: EvasionFeatures) -> list[float]:
    scores = [features.character_similarity, features.token_similarity]
    if features.semantic_similarity is not None:
        scores.append(features.semantic_similarity)
    return scores


def _similarity_reasons(
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    features: EvasionFeatures,
    policy: EvasionLinkPolicy,
) -> list[str]:
    reasons: list[str] = []
    if features.character_similarity >= policy.character_similarity:
        reasons.append("character_reformulation")
    if features.token_similarity >= policy.token_similarity:
        reasons.append("token_reformulation")
    if _semantic_match(features, policy):
        reasons.append("semantic_reformulation")
    if _containment_similarity(prior, current, features, policy):
        reasons.append("contained_reformulation")
    return reasons


def _containment_similarity(
    prior: ModerationSnapshot,
    current: ModerationSnapshot,
    features: EvasionFeatures,
    policy: EvasionLinkPolicy,
) -> bool:
    return (
        features.containment_match
        and _length_ratio(prior.text, current.text) >= policy.containment_ratio
    )


def _semantic_match(features: EvasionFeatures, policy: EvasionLinkPolicy) -> bool:
    return (
        features.same_semantic_label
        and features.semantic_similarity is not None
        and features.semantic_similarity >= policy.semantic_similarity
    )


def _normalize(text: str) -> tuple[tuple[str, ...], str]:
    normalized = unicodedata.normalize("NFKC", text).casefold().translate(_LEET_TRANSLATION)
    tokens = tuple(_WORD_RE.findall(normalized))
    return tokens, "".join(tokens)


def _same_actor(prior: ModerationSnapshot, current: ModerationSnapshot) -> bool:
    if prior.sender_identity_id and current.sender_identity_id:
        return prior.sender_identity_id == current.sender_identity_id
    return (
        prior.platform is current.platform
        and prior.scope_id == current.scope_id
        and prior.sender_id == current.sender_id
    )


def _same_canonical(prior: ModerationSnapshot, current: ModerationSnapshot) -> bool:
    return bool(
        prior.canonical_message_id
        and current.canonical_message_id
        and prior.canonical_message_id == current.canonical_message_id
    )


def _is_safety_event(item: ModerationSnapshot) -> bool:
    return item.support_flow is not SupportFlow.NONE or item.semantic_label in _SAFETY_LABELS


def _character_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=False).ratio()


def _token_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _containment_match(left: str, right: str) -> bool:
    if min(len(left), len(right)) < 5:
        return False
    return left in right or right in left


def _length_ratio(left: str, right: str) -> float:
    left_len, right_len = len(left.strip()), len(right.strip())
    if not left_len or not right_len:
        return 0.0
    return min(left_len, right_len) / max(left_len, right_len)


def _bounded_similarity(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def _actor_key(item: ModerationSnapshot) -> str:
    if item.sender_identity_id:
        return f"identity:{item.sender_identity_id}"
    return f"{item.platform.value}:{item.scope_id}:{item.sender_id}"
