from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from moderation_api.evasion import (
    EvasionLinkPolicy,
    HumanReviewState,
    ModerationSnapshot,
    RelationContext,
    link_evasion_attempt,
)
from moderation_api.models import (
    ChannelProfile,
    Label,
    MessageAction,
    Platform,
    ReviewPriority,
    StrikeRecommendation,
    SupportFlow,
)

BASE = datetime(2026, 10, 5, 16, 0, tzinfo=UTC)


def snapshot(
    event_id: str,
    text: str,
    *,
    seconds: int = 0,
    label: Label = Label.SEVERE_HARASSMENT,
    action: MessageAction = MessageAction.BLOCK,
    confidence: float | None = 0.97,
    sender_id: str = "player-a",
    identity_id: str | None = None,
    canonical_id: str | None = None,
    platform: Platform = Platform.MINECRAFT,
    profile: ChannelProfile = ChannelProfile.MINECRAFT_PUBLIC,
    scope_id: str = "smp",
    review_state: HumanReviewState = HumanReviewState.UNREVIEWED,
    review_priority: ReviewPriority = ReviewPriority.NONE,
    strike: StrikeRecommendation = StrikeRecommendation.STRIKE,
    support: SupportFlow = SupportFlow.NONE,
    chain_root: str | None = None,
    evasion_depth: int = 0,
) -> ModerationSnapshot:
    return ModerationSnapshot(
        event_id=event_id,
        platform=platform,
        channel_profile=profile,
        scope_id=scope_id,
        sender_id=sender_id,
        sender_identity_id=identity_id,
        canonical_message_id=canonical_id,
        occurred_at=BASE + timedelta(seconds=seconds),
        text=text,
        semantic_label=label,
        message_action=action,
        confidence=confidence,
        review_priority=review_priority,
        strike_recommendation=strike,
        support_flow=support,
        human_review_state=review_state,
        chain_root_event_id=chain_root,
        evasion_depth=evasion_depth,
    )


def test_character_substitutions_link_as_evasion() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "y0u ar3 a f1lthy 1d10t", seconds=8)

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is True
    assert "character_reformulation" in decision.reason_codes
    assert decision.features.character_similarity > 0.95


def test_spaces_and_punctuation_link_as_evasion() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "y.o.u a.r.e a f.i.l.t.h.y i.d.i.o.t", seconds=4)

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is True
    assert decision.features.character_similarity == 1.0


def test_changed_wording_can_use_approved_local_semantic_similarity() -> None:
    prior = snapshot(
        "p1",
        "I will hurt you at school",
        label=Label.REAL_WORLD_THREAT,
    )
    current = snapshot(
        "p2",
        "when class ends you're getting attacked",
        seconds=12,
        label=Label.REAL_WORLD_THREAT,
    )

    decision = link_evasion_attempt(prior, current, semantic_similarity=0.91)

    assert decision.linked is True
    assert "semantic_reformulation" in decision.reason_codes


def test_changed_wording_does_not_invent_semantic_similarity() -> None:
    prior = snapshot(
        "p1",
        "I will hurt you at school",
        label=Label.REAL_WORLD_THREAT,
    )
    current = snapshot(
        "p2",
        "when class ends you're getting attacked",
        seconds=12,
        label=Label.REAL_WORLD_THREAT,
    )

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert decision.blocker_codes == ("insufficient_similarity",)


def test_quote_or_report_never_links() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "they said you are a filthy idiot", seconds=5)

    decision = link_evasion_attempt(
        prior,
        current,
        relation=RelationContext(quote_or_report=True),
    )

    assert decision.linked is False
    assert "quote_or_report" in decision.blocker_codes


def test_apology_or_correction_never_links() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "sorry I said you are a filthy idiot", seconds=6)

    decision = link_evasion_attempt(
        prior,
        current,
        relation=RelationContext(apology_or_correction=True),
    )

    assert decision.linked is False
    assert "apology_or_correction" in decision.blocker_codes


def test_appeal_or_review_discussion_never_links() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "why was 'you are a filthy idiot' blocked?", seconds=9)

    decision = link_evasion_attempt(
        prior,
        current,
        relation=RelationContext(appeal_or_review_discussion=True),
    )

    assert decision.linked is False
    assert "appeal_or_review_discussion" in decision.blocker_codes


def test_minecraft_benign_retry_cannot_escalate_without_independent_block() -> None:
    prior = snapshot(
        "p1",
        "kill you",
        label=Label.REAL_WORLD_THREAT,
    )
    current = snapshot(
        "p2",
        "kill you next round",
        seconds=7,
        label=Label.GAMEPLAY_VIOLENCE,
        action=MessageAction.ALLOW,
        strike=StrikeRecommendation.NONE,
    )

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "current_not_independently_blocked" in decision.blocker_codes


def test_unrelated_lexical_overlap_does_not_link() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "this build uses an idiotic piston layout", seconds=10)

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert decision.blocker_codes == ("insufficient_similarity",)


def test_mirrored_discord_copy_is_not_an_evasion_attempt() -> None:
    prior = snapshot("p1", "you are a filthy idiot", canonical_id="mirror-7")
    current = snapshot(
        "p2",
        "you are a filthy idiot",
        seconds=1,
        canonical_id="mirror-7",
        platform=Platform.DISCORD,
        profile=ChannelProfile.DISCORD_GAMING,
        scope_id="guild",
        identity_id="identity-a",
    )
    prior = replace(prior, sender_identity_id="identity-a")

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "mirrored_copy" in decision.blocker_codes


def test_explicit_mirror_flag_blocks_even_without_canonical_id() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "you are a filthy idiot", seconds=1)

    decision = link_evasion_attempt(
        prior,
        current,
        relation=RelationContext(mirrored_copy=True),
    )

    assert decision.linked is False
    assert "mirrored_copy" in decision.blocker_codes


def test_same_violation_much_later_is_a_distinct_incident() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "you are a filthy idiot", seconds=600)

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "outside_evasion_window" in decision.blocker_codes


def test_pending_prior_review_cannot_snowball() -> None:
    prior = snapshot(
        "p1",
        "you are a filthy idiot",
        review_state=HumanReviewState.PENDING,
        review_priority=ReviewPriority.NORMAL,
    )
    current = snapshot("p2", "y0u ar3 a f1lthy 1d10t", seconds=8)

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "prior_not_reliable" in decision.blocker_codes


def test_overturned_false_positive_cannot_snowball() -> None:
    prior = snapshot(
        "p1",
        "you are a filthy idiot",
        review_state=HumanReviewState.OVERTURNED,
    )
    current = snapshot("p2", "y0u ar3 a f1lthy 1d10t", seconds=8)

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "prior_not_reliable" in decision.blocker_codes


def test_low_confidence_prior_block_cannot_seed_chain() -> None:
    prior = snapshot("p1", "you are a filthy idiot", confidence=0.72)
    current = snapshot("p2", "y0u ar3 a f1lthy 1d10t", seconds=8)

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "prior_not_high_confidence" in decision.blocker_codes


def test_self_harm_support_event_is_excluded_from_punishment_reputation() -> None:
    prior = snapshot(
        "p1",
        "I want to die",
        label=Label.SELF_HARM_INTENT,
        support=SupportFlow.SELF_HARM_CHECK,
        strike=StrikeRecommendation.NONE,
    )
    current = snapshot(
        "p2",
        "i w4nt t0 d1e",
        seconds=8,
        label=Label.SELF_HARM_INTENT,
        support=SupportFlow.SELF_HARM_CHECK,
        strike=StrikeRecommendation.NONE,
    )

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "safety_event_excluded" in decision.blocker_codes


def test_different_sender_does_not_link() -> None:
    prior = snapshot("p1", "you are a filthy idiot", sender_id="a")
    current = snapshot("p2", "y0u ar3 a f1lthy 1d10t", seconds=8, sender_id="b")

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is False
    assert "different_actor" in decision.blocker_codes


def test_authoritative_identity_allows_cross_platform_linkage() -> None:
    prior = snapshot(
        "p1",
        "you are a filthy idiot",
        identity_id="identity-a",
    )
    current = snapshot(
        "p2",
        "y0u ar3 a f1lthy 1d10t",
        seconds=8,
        identity_id="identity-a",
        platform=Platform.DISCORD,
        profile=ChannelProfile.DISCORD_GAMING,
        scope_id="guild",
    )

    decision = link_evasion_attempt(prior, current)

    assert decision.linked is True
    assert decision.features.same_actor is True


def test_multiple_rapid_evasions_keep_one_chain_root() -> None:
    first = snapshot("p1", "you are a filthy idiot")
    second = snapshot("p2", "y0u ar3 a f1lthy 1d10t", seconds=8)
    second_link = link_evasion_attempt(first, second)
    assert second_link.linked is True

    chained_second = replace(
        second,
        chain_root_event_id=second_link.root_event_id,
        evasion_depth=second_link.attempt_index,
    )
    third = snapshot("p3", "y.o.u are a filthy id10t", seconds=15)
    third_link = link_evasion_attempt(chained_second, third)

    assert third_link.linked is True
    assert third_link.root_event_id == "p1"
    assert third_link.chain_id == second_link.chain_id
    assert third_link.attempt_index == 2


def test_staff_evidence_is_explicit_and_never_authorizes_punishment() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "y0u ar3 a f1lthy 1d10t", seconds=8)

    decision = link_evasion_attempt(prior, current)
    evidence = decision.staff_evidence(prior, current)

    assert evidence is not None
    assert evidence.evidence_type == "EVASION_CHAIN"
    assert evidence.prior_event_id == "p1"
    assert evidence.current_event_id == "p2"
    assert evidence.current_strike_recommendation is StrikeRecommendation.STRIKE
    assert evidence.automatic_punishment_allowed is False


def test_non_linked_decision_has_no_staff_evidence() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot(
        "p2",
        "you are a filthy idiot",
        seconds=8,
        action=MessageAction.ALLOW,
    )

    decision = link_evasion_attempt(prior, current)

    assert decision.staff_evidence(prior, current) is None


def test_custom_window_is_calibration_not_punishment_policy() -> None:
    prior = snapshot("p1", "you are a filthy idiot")
    current = snapshot("p2", "you are a filthy idiot", seconds=45)

    short = link_evasion_attempt(
        prior,
        current,
        policy=EvasionLinkPolicy(max_gap_seconds=30),
    )
    default = link_evasion_attempt(prior, current)

    assert short.linked is False
    assert "outside_evasion_window" in short.blocker_codes
    assert default.linked is True
