from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from moderation_api.advisory import AdvisoryDispatcher, DisabledAdvisoryClient
from moderation_api.auth import Principal
from moderation_api.classifier import LocalClassifier
from moderation_api.config import Settings
from moderation_api.context import RollingContextStore
from moderation_api.models import ChannelProfile, ModerationRequest
from moderation_api.runtime import ModerationRuntime, ProcessingTimeout, RequestQueueFull
from moderation_api.storage import ModerationStore

from .helpers import result


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
        return {"ready": True, "mode": "test", "model_version": "blocking-v1"}


class SequencingClassifier:
    def __init__(self) -> None:
        self.first_entered = asyncio.Event()
        self.release_first = asyncio.Event()
        self.second_context: tuple[str, ...] = ()

    async def classify(self, item):
        if item.current.external_message_id == "one":
            self.first_entered.set()
            await self.release_first.wait()
        else:
            self.second_context = tuple(msg.external_message_id for msg in item.context)
        return result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "sequence-v1"}


class SlowClassifier:
    async def classify(self, item):
        del item
        await asyncio.sleep(0.08)
        return result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "slow-v1"}


def request(message_id: str) -> ModerationRequest:
    return ModerationRequest(
        platform="minecraft", channel_profile="minecraft_public", scope_id="smp",
        external_message_id=message_id, sender_id="player", occurred_at=datetime.now(UTC),
        text="hello",
    )


def runtime(settings: Settings, classifier: LocalClassifier) -> ModerationRuntime:
    store = ModerationStore(settings.database_path)
    context = RollingContextStore(45, 10, 10, 5, 8)
    advisory = AdvisoryDispatcher(store, DisabledAdvisoryClient(), False, 1, 1, 100)
    return ModerationRuntime(settings, store, context, classifier, advisory)


@pytest.mark.asyncio
async def test_request_queue_is_bounded(settings) -> None:
    configured = replace(settings, request_queue_size=1, request_workers=1, request_timeout_ms=1000)
    classifier = BlockingClassifier()
    service = runtime(configured, classifier)
    await service._store.initialize()
    await service.start()
    principal = Principal("rosechat", frozenset({"moderate"}))
    try:
        first = asyncio.create_task(service.submit(request("one"), principal))
        await classifier.entered.wait()
        second = asyncio.create_task(service.submit(request("two"), principal))
        await asyncio.sleep(0)
        with pytest.raises(RequestQueueFull):
            await service.submit(request("three"), principal)
        classifier.release.set()
        await asyncio.gather(first, second)
    finally:
        classifier.release.set()
        await service.stop()


@pytest.mark.asyncio
async def test_request_deadline_is_bounded_and_worker_can_finish(settings) -> None:
    configured = replace(settings, request_timeout_ms=10, classifier_timeout_ms=200)
    service = runtime(configured, SlowClassifier())
    await service._store.initialize()
    await service.start()
    principal = Principal("rosechat", frozenset({"moderate"}))
    try:
        with pytest.raises(ProcessingTimeout):
            await service.submit(request("slow"), principal)
        await asyncio.sleep(0.12)
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_same_sender_requests_preserve_cross_scope_context_order(settings) -> None:
    configured = replace(
        settings, request_workers=2, request_timeout_ms=1000, classifier_timeout_ms=800
    )
    classifier = SequencingClassifier()
    service = runtime(configured, classifier)
    await service._store.initialize()
    await service.start()
    principal = Principal("rosechat", frozenset({"moderate"}))
    try:
        first = asyncio.create_task(service.submit(request("one"), principal))
        await classifier.first_entered.wait()
        second_request = request("two").model_copy(
            update={
                "channel_profile": ChannelProfile.MINECRAFT_PRIVATE,
                "channel_id": "pm:player:b",
            }
        )
        second = asyncio.create_task(service.submit(second_request, principal))
        await asyncio.sleep(0.02)
        assert classifier.second_context == ()
        classifier.release_first.set()
        await asyncio.gather(first, second)
        assert classifier.second_context == ("one",)
    finally:
        classifier.release_first.set()
        await service.stop()
