from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from moderation_api.context import RollingContextStore
from moderation_api.models import ContextMessage


def message(
    scope: str,
    message_id: str,
    sender: str,
    seconds: int,
    channel: str | None = None,
) -> ContextMessage:
    return ContextMessage(
        platform="minecraft",
        scope_id=scope,
        channel_id=channel,
        external_message_id=message_id,
        sender_id=sender,
        occurred_at=datetime(2026, 10, 1, 20, 0, tzinfo=UTC) + timedelta(seconds=seconds),
        text=message_id,
        reply_to_message_id=None,
    )


@pytest.mark.asyncio
async def test_context_is_bounded_by_scope_and_time() -> None:
    store = RollingContextStore(
        45,
        max_scopes=2,
        messages_per_scope=3,
        sender_messages=2,
        channel_messages=2,
    )
    await store.record(message("one", "old", "a", 0))
    await store.record(message("one", "recent", "a", 50))
    await store.record(message("two", "two", "b", 50))
    await store.record(message("three", "three", "c", 50))

    evicted = await store.snapshot_for(message("one", "target", "a", 60))
    current = await store.snapshot_for(message("three", "target", "c", 60))

    assert evicted == ()
    assert [item.external_message_id for item in current] == ["three"]


@pytest.mark.asyncio
async def test_context_does_not_bleed_between_channels() -> None:
    store = RollingContextStore(45, 10, 10, 5, 8)
    await store.record(message("guild", "one", "a", 0, channel="one"))
    await store.record(message("guild", "two", "a", 1, channel="two"))

    context = await store.snapshot_for(message("guild", "target", "a", 2, channel="two"))

    assert [item.external_message_id for item in context] == ["two"]
