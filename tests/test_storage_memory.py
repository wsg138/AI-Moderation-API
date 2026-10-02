from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from moderation_api.models import (
    ChannelProfile,
    ContextMessage,
    MemoryFact,
    MemoryKind,
    Platform,
    SafetyMemoryFact,
    SafetyMemoryKind,
)
from moderation_api.storage import ModerationStore

NOW = datetime.now(UTC).replace(microsecond=0)


def current(platform: Platform = Platform.MINECRAFT) -> ContextMessage:
    profile = (
        ChannelProfile.MINECRAFT_PUBLIC
        if platform is Platform.MINECRAFT
        else ChannelProfile.DISCORD_GENERAL
    )
    return ContextMessage(
        event_id="current", platform=platform, channel_profile=profile,
        scope_id="smp" if platform is Platform.MINECRAFT else "guild",
        channel_id="global", conversation_id=None, external_message_id="current-message",
        canonical_message_id=None, sender_id="player-a", sender_identity_id="person-a",
        recipient_ids=("target-b",), recipient_identity_ids=("person-b",),
        target_ids=("target-b",), target_identity_ids=("person-b",),
        occurred_at=NOW, text="hello", reply_to_message_id=None,
    )


def memory(
    memory_id: str,
    kind: MemoryKind,
    *,
    target: str | None = None,
    platform: Platform = Platform.MINECRAFT,
    expires: datetime | None = None,
) -> MemoryFact:
    return MemoryFact(
        memory_id, kind, "person-a", target, platform, {"severity": 20},
        1.0, "staff", True, NOW, expires,
    )


@pytest.mark.asyncio
async def test_memory_is_platform_target_decayed_and_safety_isolated(tmp_path: Path) -> None:
    store = ModerationStore(tmp_path / "memory.sqlite3")
    await store.initialize()
    active = NOW + timedelta(days=7)
    facts = (
        memory("mc-global", MemoryKind.INCIDENT, expires=active),
        memory("mc-target", MemoryKind.TARGET_HARASSMENT, target="person-b", expires=active),
        memory("other-target", MemoryKind.TARGET_HARASSMENT, target="person-z", expires=active),
        memory(
            "discord-only", MemoryKind.STRIKE_EVIDENCE, platform=Platform.DISCORD, expires=active
        ),
        memory("expired", MemoryKind.INCIDENT, expires=NOW - timedelta(seconds=1)),
    )
    for fact in facts:
        await store.save_memory_fact(fact)
    await store.save_safety_memory_fact(
        SafetyMemoryFact(
            "safety", SafetyMemoryKind.SAFETY_CHECK, "person-a", {"completed": True},
            1.0, "support-flow", NOW, active,
        )
    )

    snapshot = await store.load_memory_snapshot(current(), 20)
    punishment_ids = {fact.memory_id for fact in snapshot.punishment}
    assert punishment_ids == {"mc-global", "mc-target"}
    assert [fact.memory_id for fact in snapshot.safety] == ["safety"]


@pytest.mark.asyncio
async def test_recent_context_rehydration_defensively_filters_exempt_rows(tmp_path: Path) -> None:
    path = tmp_path / "rehydrate.sqlite3"
    store = ModerationStore(path)
    await store.initialize()
    with sqlite3.connect(path) as connection:
        now = NOW.isoformat()
        connection.execute(
            """INSERT INTO moderation_events(
              event_id,external_key,input_fingerprint,client_id,platform,channel_profile,
              scope_id,external_message_id,sender_id,occurred_at,text,status,action,label,
              created_at,finalized_at
            ) VALUES('e','k','f','client','discord','discord_ticket_exempt','guild','m','p',
                     ?,'secret','FINAL','ALLOW','SAFE',?,?)""",
            (now, now, now),
        )
    assert await store.load_recent_context(45, 100) == ()
