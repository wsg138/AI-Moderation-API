from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from moderation_api.advisory import AdvisoryDispatcher, DisabledAdvisoryClient
from moderation_api.auth import Principal
from moderation_api.config import Settings
from moderation_api.context import RollingContextStore
from moderation_api.models import (
    AdvisoryStatus,
    ChannelProfile,
    Containment,
    IngestionStatus,
    Label,
    MessageAction,
    ModerationRequest,
    ModerationResponse,
    Platform,
    ReviewPriority,
    StrikeRecommendation,
    SupportFlow,
)
from moderation_api.runtime import ModerationRuntime
from moderation_api.storage import DecisionConflict, EventConflict, ModerationStore

from .helpers import result


def moderation_request(
    message_id: str,
    *,
    canonical_id: str | None = None,
    platform: Platform = Platform.MINECRAFT,
    profile: ChannelProfile = ChannelProfile.MINECRAFT_PUBLIC,
    scope_id: str = "smp",
    channel_id: str = "global",
    sender_id: str = "player-a",
    text: str = "hello",
) -> ModerationRequest:
    return ModerationRequest(
        platform=platform,
        channel_profile=profile,
        scope_id=scope_id,
        channel_id=channel_id,
        external_message_id=message_id,
        canonical_message_id=canonical_id,
        sender_id=sender_id,
        occurred_at=datetime.now(UTC),
        text=text,
    )


def decision(event_id: str, policy_version: str = "v1") -> ModerationResponse:
    return ModerationResponse(
        event_id=event_id,
        ingestion_status=IngestionStatus.INGESTED,
        message_action=MessageAction.ALLOW,
        semantic_label=Label.SAFE,
        review_priority=ReviewPriority.NONE,
        strike_recommendation=StrikeRecommendation.NONE,
        containment=Containment.NONE,
        containment_duration_seconds=None,
        support_flow=SupportFlow.NONE,
        scores={"SAFE": 1.0},
        confidence=1.0,
        rule_hits=[],
        reason_codes=["test"],
        related_message_ids=[],
        related_messages=[],
        local_model_version="test-v1",
        policy_version=policy_version,
        advisory_status=AdvisoryStatus.DISABLED,
        latency_ms=1,
    )


async def reserve(
    store: ModerationStore,
    request: ModerationRequest,
    request_fingerprint: str,
    canonical_fingerprint: str = "canonical-fingerprint",
    stale_after_ms: int = 30_000,
):
    return await store.reserve_event(
        request,
        "rosechat",
        request_fingerprint,
        canonical_fingerprint,
        AdvisoryStatus.DISABLED,
        stale_after_ms,
    )


def age_pending(path: Path, event_id: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """UPDATE moderation_events
               SET reservation_updated_at='2000-01-01T00:00:00+00:00'
               WHERE event_id=?""",
            (event_id,),
        )


@pytest.mark.asyncio
async def test_active_pending_is_not_stolen_but_stale_retry_takes_ownership(tmp_path: Path) -> None:
    path = tmp_path / "pending.sqlite3"
    store = ModerationStore(path)
    await store.initialize()
    request = moderation_request("same")

    first = await reserve(store, request, "same-fingerprint")
    assert first.lease_token is not None

    active_retry = await reserve(store, request, "same-fingerprint")
    assert active_retry.event_id == first.event_id
    assert active_retry.pending is True
    assert active_retry.lease_token is None

    age_pending(path, first.event_id)
    recovered = await reserve(store, request, "same-fingerprint", stale_after_ms=1)
    assert recovered.event_id == first.event_id
    assert recovered.pending is False
    assert recovered.lease_token not in {None, first.lease_token}
    assert recovered.recovery_request is not None
    assert recovered.recovery_request.external_message_id == "same"

    with pytest.raises(DecisionConflict):
        await store.finalize_event(
            decision(first.event_id),
            (),
            (first.event_id,),
            None,
            first.lease_token,
        )

    assert recovered.lease_token is not None
    await store.finalize_event(
        decision(first.event_id),
        (),
        (first.event_id,),
        None,
        recovered.lease_token,
    )
    replay = await reserve(store, request, "same-fingerprint")
    assert replay.replay is True
    assert replay.event_id == first.event_id


@pytest.mark.asyncio
async def test_finalize_failure_can_be_recovered_after_lease_stales(tmp_path: Path) -> None:
    path = tmp_path / "finalize-failure.sqlite3"
    store = ModerationStore(path)
    await store.initialize()
    request = moderation_request("finalize-failure")
    first = await reserve(store, request, "finalize-fingerprint")
    assert first.lease_token is not None

    with pytest.raises(sqlite3.IntegrityError):
        await store.finalize_event(
            decision(first.event_id, policy_version=""),
            (),
            (first.event_id,),
            None,
            first.lease_token,
        )

    with sqlite3.connect(path) as connection:
        status, token = connection.execute(
            "SELECT status,reservation_token FROM moderation_events WHERE event_id=?",
            (first.event_id,),
        ).fetchone()
    assert status == "PENDING"
    assert token == first.lease_token

    age_pending(path, first.event_id)
    recovered = await reserve(store, request, "finalize-fingerprint", stale_after_ms=1)
    assert recovered.lease_token not in {None, first.lease_token}

    assert recovered.lease_token is not None
    await store.finalize_event(
        decision(first.event_id),
        (),
        (first.event_id,),
        None,
        recovered.lease_token,
    )
    loaded = await store.load_decision(first.event_id)
    assert loaded.message_action is MessageAction.ALLOW


@pytest.mark.asyncio
async def test_stale_pending_survives_restart_and_is_recoverable(tmp_path: Path) -> None:
    path = tmp_path / "restart.sqlite3"
    first_store = ModerationStore(path)
    await first_store.initialize()
    request = moderation_request("restart-pending")
    original = await reserve(first_store, request, "restart-fingerprint")
    assert original.lease_token is not None
    age_pending(path, original.event_id)

    restarted_store = ModerationStore(path)
    await restarted_store.initialize()
    recovered = await reserve(
        restarted_store,
        request,
        "restart-fingerprint",
        stale_after_ms=1,
    )
    assert recovered.event_id == original.event_id
    assert recovered.lease_token not in {None, original.lease_token}
    assert recovered.recovery_request is not None


@pytest.mark.asyncio
async def test_pending_mirror_alias_persists_and_replay_contains_both_refs(tmp_path: Path) -> None:
    path = tmp_path / "mirror.sqlite3"
    store = ModerationStore(path)
    await store.initialize()
    canonical = moderation_request("mc-1", canonical_id="canonical-1")
    mirror = moderation_request(
        "discord-1",
        canonical_id="canonical-1",
        platform=Platform.DISCORD,
        profile=ChannelProfile.DISCORD_GENERAL,
        scope_id="guild",
        channel_id="general",
        sender_id="discord-player",
    )

    owner = await reserve(store, canonical, "mc-fingerprint")
    pending_mirror = await reserve(store, mirror, "discord-fingerprint")
    assert pending_mirror.event_id == owner.event_id
    assert pending_mirror.pending is True

    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM moderation_events").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM message_aliases").fetchone()[0] == 2

    assert owner.lease_token is not None
    await store.finalize_event(
        decision(owner.event_id),
        (),
        (owner.event_id,),
        None,
        owner.lease_token,
    )

    replay = await reserve(store, mirror, "discord-fingerprint")
    assert replay.replay is True
    loaded = await store.load_decision(owner.event_id)
    refs = {item.external_message_id for item in loaded.related_messages}
    assert refs == {"mc-1", "discord-1"}


@pytest.mark.asyncio
async def test_pending_canonical_conflict_does_not_attach_bad_mirror(tmp_path: Path) -> None:
    path = tmp_path / "mirror-conflict.sqlite3"
    store = ModerationStore(path)
    await store.initialize()
    canonical = moderation_request("mc-1", canonical_id="canonical-1", text="hello")
    owner = await reserve(store, canonical, "mc-fingerprint", "canonical-a")
    assert owner.pending is False

    mirror = moderation_request(
        "discord-1",
        canonical_id="canonical-1",
        platform=Platform.DISCORD,
        profile=ChannelProfile.DISCORD_GENERAL,
        scope_id="guild",
        channel_id="general",
        sender_id="discord-player",
        text="changed",
    )
    with pytest.raises(EventConflict):
        await reserve(store, mirror, "discord-fingerprint", "canonical-b")

    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM moderation_events").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM message_aliases").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_simultaneous_first_arrival_mirrors_create_one_event(tmp_path: Path) -> None:
    path = tmp_path / "first-arrival-race.sqlite3"
    store = ModerationStore(path)
    await store.initialize()
    canonical = moderation_request("mc-race", canonical_id="race-canonical")
    mirror = moderation_request(
        "discord-race",
        canonical_id="race-canonical",
        platform=Platform.DISCORD,
        profile=ChannelProfile.DISCORD_GENERAL,
        scope_id="guild",
        channel_id="general",
        sender_id="discord-player",
    )

    first, second = await asyncio.gather(
        reserve(store, canonical, "mc-race-fingerprint"),
        reserve(store, mirror, "discord-race-fingerprint"),
    )

    assert first.event_id == second.event_id
    assert sum(item.lease_token is not None for item in (first, second)) == 1
    assert sum(item.pending for item in (first, second)) == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM moderation_events").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM message_aliases").fetchone()[0] == 2


class BlockingClassifier:
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def classify(self, item):
        del item
        self.entered.set()
        await self.release.wait()
        return result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "pending-block-v1"}


def build_runtime(settings: Settings, classifier: BlockingClassifier) -> ModerationRuntime:
    store = ModerationStore(settings.database_path)
    context = RollingContextStore(45, 10, 10, 5, 8)
    advisory = AdvisoryDispatcher(store, DisabledAdvisoryClient(), False, 1, 1, 100)
    return ModerationRuntime(settings, store, context, classifier, advisory)


def different_queue_mirror(
    service: ModerationRuntime,
    canonical: ModerationRequest,
) -> ModerationRequest:
    canonical_queue = service._queue_for(canonical)
    for index in range(20):
        candidate = moderation_request(
            "discord-runtime",
            canonical_id="runtime-canonical",
            platform=Platform.DISCORD,
            profile=ChannelProfile.DISCORD_GENERAL,
            scope_id="guild",
            channel_id="general",
            sender_id=f"discord-player-{index}",
        )
        if service._queue_for(candidate) is not canonical_queue:
            return candidate
    raise AssertionError("could not find a different request shard")


@pytest.mark.asyncio
async def test_pending_mirror_fails_open_then_replays_after_canonical_finalizes(settings) -> None:
    configured = replace(
        settings,
        request_workers=4,
        request_timeout_ms=1000,
        classifier_timeout_ms=800,
        pending_stale_after_ms=30_000,
    )
    classifier = BlockingClassifier()
    service = build_runtime(configured, classifier)
    await service._store.initialize()
    await service.start()
    principal = Principal("rosechat", frozenset({"moderate"}))

    canonical = moderation_request(
        "mc-runtime",
        canonical_id="runtime-canonical",
        sender_id="minecraft-player",
    )
    mirror = different_queue_mirror(service, canonical)

    try:
        first_task = asyncio.create_task(service.submit(canonical, principal))
        await classifier.entered.wait()

        pending_response = await service.submit(mirror, principal)
        assert pending_response.message_action is MessageAction.ALLOW
        assert pending_response.ingestion_status is IngestionStatus.FAIL_OPEN
        assert pending_response.fallback_state == "event_in_progress"
        assert pending_response.event_id is None

        with sqlite3.connect(configured.database_path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM moderation_events").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM message_aliases").fetchone()[0] == 2

        classifier.release.set()
        first_response = await first_task
        assert first_response.event_id is not None

        replay = await service.submit(mirror, principal)
        assert replay.idempotent_replay is True
        assert replay.event_id == first_response.event_id
        refs = {item.external_message_id for item in replay.related_messages}
        assert refs == {"mc-runtime", "discord-runtime"}
    finally:
        classifier.release.set()
        await service.stop()
