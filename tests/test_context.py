from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from moderation_api.context import RollingContextStore
from moderation_api.models import ChannelProfile, ContextMessage, Platform

BASE = datetime.now(UTC).replace(microsecond=0)


def message(
    message_id: str,
    *,
    platform: Platform = Platform.MINECRAFT,
    profile: ChannelProfile = ChannelProfile.MINECRAFT_PUBLIC,
    channel: str = "global",
    sender: str = "a",
    seconds: int = 0,
    recipients: tuple[str, ...] = (),
    targets: tuple[str, ...] = (),
    sender_identity: str | None = None,
    recipient_identities: tuple[str, ...] = (),
    target_identities: tuple[str, ...] = (),
) -> ContextMessage:
    return ContextMessage(
        event_id=f"event-{message_id}", platform=platform, channel_profile=profile,
        scope_id="smp" if platform is Platform.MINECRAFT else "guild", channel_id=channel,
        conversation_id=None, external_message_id=message_id, canonical_message_id=None,
        sender_id=sender, sender_identity_id=sender_identity, recipient_ids=recipients,
        recipient_identity_ids=recipient_identities, target_ids=targets,
        target_identity_ids=target_identities, occurred_at=BASE + timedelta(seconds=seconds),
        text=message_id, reply_to_message_id=None,
    )


@pytest.mark.asyncio
async def test_pm_public_same_sender_continuity_crosses_channels() -> None:
    store = RollingContextStore(45, 20, 20, 5, 8)
    private = message(
        "pm", profile=ChannelProfile.MINECRAFT_PRIVATE, channel="pm:a:b", recipients=("b",)
    )
    public = message("public", channel="global", seconds=1, targets=("b",))
    await store.record(private)
    context = await store.snapshot_for(public)
    assert [item.external_message_id for item in context] == ["pm"]


@pytest.mark.asyncio
async def test_unrelated_senders_do_not_bleed_across_channels() -> None:
    store = RollingContextStore(45, 20, 20, 5, 8)
    await store.record(message("other", channel="trade", sender="x", targets=("z",)))
    context = await store.snapshot_for(message("current", channel="global", sender="a"))
    assert context == ()


@pytest.mark.asyncio
async def test_cross_platform_requires_authoritative_link() -> None:
    store = RollingContextStore(45, 20, 20, 5, 8)
    minecraft = message("mc", sender="mc-a", sender_identity="person-a")
    await store.record(minecraft)
    linked = message(
        "dc", platform=Platform.DISCORD, profile=ChannelProfile.DISCORD_GENERAL,
        sender="dc-a", sender_identity="person-a", seconds=1,
    )
    unlinked = message(
        "dc2", platform=Platform.DISCORD, profile=ChannelProfile.DISCORD_GENERAL,
        sender="dc-x", seconds=2,
    )
    assert [item.external_message_id for item in await store.snapshot_for(linked)] == ["mc"]
    assert await store.snapshot_for(unlinked) == ()


@pytest.mark.asyncio
async def test_context_window_and_intervening_limit_are_bounded() -> None:
    store = RollingContextStore(45, 20, 40, 5, 8, intervening_messages=20)
    for index in range(25):
        await store.record(message(f"m{index}", seconds=index, sender="a"))
    context = await store.snapshot_for(message("now", seconds=25, sender="a"))
    ids = {item.external_message_id for item in context}
    assert "m0" not in ids
    assert "m24" in ids


@pytest.mark.asyncio
async def test_remove_prevents_failed_event_from_becoming_context() -> None:
    store = RollingContextStore(45, 20, 20, 5, 8)
    failed = message("failed")
    await store.record(failed)
    await store.remove(failed.event_id)
    context = await store.snapshot_for(message("next", seconds=1))
    assert context == ()
