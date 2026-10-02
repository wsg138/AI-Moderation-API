from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest
from moderation_api.models import (
    Action,
    AdvisoryStatus,
    Label,
    ModerationRequest,
    ModerationResponse,
)
from moderation_api.storage import ModerationStore


def request() -> ModerationRequest:
    return ModerationRequest(
        platform="minecraft",
        scope_id="smp:global",
        external_message_id="rollback",
        sender_id="player",
        occurred_at=datetime(2026, 10, 2, 1, 0, tzinfo=UTC),
        text="hello",
    )


def response(event_id: str, policy_version: str, action: Action) -> ModerationResponse:
    return ModerationResponse(
        event_id=event_id,
        action=action,
        label=Label.SAFE,
        scores={"SAFE": 1.0},
        rule_hits=[],
        reason_codes=["test"],
        related_message_ids=[],
        local_model_version="test-v1",
        policy_version=policy_version,
        advisory_status=AdvisoryStatus.DISABLED,
        latency_ms=1,
    )


@pytest.mark.asyncio
async def test_failed_finalize_rolls_back_event_state(tmp_path) -> None:
    store = ModerationStore(tmp_path / "store.sqlite3")
    await store.initialize()
    reservation = await store.reserve_event(
        request(),
        "rosechat",
        "fingerprint",
        AdvisoryStatus.DISABLED,
    )

    with pytest.raises(sqlite3.IntegrityError):
        await store.finalize_event(response(reservation.event_id, "", Action.BLOCK))

    await store.finalize_event(response(reservation.event_id, "draft", Action.ALLOW))
    loaded = await store.load_decision(reservation.event_id)
    assert loaded.action is Action.ALLOW


@pytest.mark.asyncio
async def test_finalize_persists_advisory_queue_saturation(tmp_path) -> None:
    store = ModerationStore(tmp_path / "advisory.sqlite3")
    await store.initialize()
    reservation = await store.reserve_event(
        request(), "rosechat", "advisory-fingerprint", AdvisoryStatus.DISABLED
    )
    saturated = response(reservation.event_id, "draft", Action.ALLOW).model_copy(
        update={"advisory_status": AdvisoryStatus.QUEUE_SATURATED}
    )

    await store.finalize_event(saturated)
    event = await store.get_event(reservation.event_id)

    assert event.advisory is not None
    assert event.advisory.status is AdvisoryStatus.QUEUE_SATURATED
    assert event.advisory.error_code == "advisory_queue_saturated"


@pytest.mark.asyncio
async def test_advisory_disagreement_is_persisted(tmp_path) -> None:
    store = ModerationStore(tmp_path / "disagreement.sqlite3")
    await store.initialize()
    reservation = await store.reserve_event(
        request(), "rosechat", "disagreement-fingerprint", AdvisoryStatus.DISABLED
    )
    await store.finalize_event(response(reservation.event_id, "draft", Action.ALLOW))
    from moderation_api.models import AdvisoryEvidence

    await store.save_advisory(
        reservation.event_id,
        AdvisoryEvidence(
            status=AdvisoryStatus.COMPLETE,
            model="omni-moderation-latest",
            flagged=True,
            scores={"violence": 0.9},
            categories={"violence": True},
        ),
    )

    event = await store.get_event(reservation.event_id)
    assert event.advisory is not None
    assert event.advisory.disagrees_with_local is True
