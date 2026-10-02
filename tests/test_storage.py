from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest
from moderation_api.models import (
    AdvisoryEvidence,
    AdvisoryStatus,
    Containment,
    IngestionStatus,
    Label,
    MessageAction,
    ModerationRequest,
    ModerationResponse,
    ReviewPriority,
    StrikeRecommendation,
    SupportFlow,
)
from moderation_api.storage import ModerationStore


def request() -> ModerationRequest:
    return ModerationRequest(
        platform="minecraft", channel_profile="minecraft_public", scope_id="smp",
        external_message_id="rollback", sender_id="player",
        occurred_at=datetime.now(UTC), text="hello",
    )


def response(event_id: str, policy_version: str) -> ModerationResponse:
    return ModerationResponse(
        event_id=event_id, ingestion_status=IngestionStatus.INGESTED,
        message_action=MessageAction.ALLOW, semantic_label=Label.SAFE,
        review_priority=ReviewPriority.NONE, strike_recommendation=StrikeRecommendation.NONE,
        containment=Containment.NONE, containment_duration_seconds=None,
        support_flow=SupportFlow.NONE, scores={"SAFE": 1.0}, confidence=1.0,
        rule_hits=[], reason_codes=["test"], related_message_ids=[], related_messages=[],
        local_model_version="test-v1", policy_version=policy_version,
        advisory_status=AdvisoryStatus.DISABLED, latency_ms=1,
    )


@pytest.mark.asyncio
async def test_failed_finalize_rolls_back_event_state(tmp_path) -> None:
    store = ModerationStore(tmp_path / "store.sqlite3")
    await store.initialize()
    reservation = await store.reserve_event(
        request(), "rosechat", "fingerprint", "canonical", AdvisoryStatus.DISABLED
    )
    assert reservation.lease_token is not None
    with pytest.raises(sqlite3.IntegrityError):
        await store.finalize_event(
            response(reservation.event_id, ""),
            (),
            (),
            None,
            reservation.lease_token,
        )
    await store.finalize_event(
        response(reservation.event_id, "v1"),
        (),
        (),
        None,
        reservation.lease_token,
    )
    loaded = await store.load_decision(reservation.event_id)
    assert loaded.message_action is MessageAction.ALLOW


@pytest.mark.asyncio
async def test_advisory_disagreement_is_persisted(tmp_path) -> None:
    store = ModerationStore(tmp_path / "advisory.sqlite3")
    await store.initialize()
    reservation = await store.reserve_event(
        request(), "rosechat", "fingerprint", "canonical", AdvisoryStatus.DISABLED
    )
    assert reservation.lease_token is not None
    await store.finalize_event(
        response(reservation.event_id, "v1"),
        (),
        (),
        None,
        reservation.lease_token,
    )
    await store.save_advisory(
        reservation.event_id,
        AdvisoryEvidence(
            status=AdvisoryStatus.COMPLETE, model="omni-moderation-latest",
            flagged=True, scores={"violence": 0.9}, categories={"violence": True},
        ),
    )
    event = await store.get_event(reservation.event_id)
    assert event.advisory is not None
    assert event.advisory.disagrees_with_local is True
