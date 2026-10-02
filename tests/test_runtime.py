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
from moderation_api.models import (
    Action,
    ClassificationInput,
    ClassificationResult,
    Label,
    ModerationRequest,
)
from moderation_api.runtime import ModerationRuntime, ProcessingTimeout, RequestQueueFull
from moderation_api.storage import ModerationStore


class BlockingClassifier(LocalClassifier):
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        del item
        self.entered.set()
        await self.release.wait()
        return _allow_result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "blocking-v1"}


class SequencingClassifier(LocalClassifier):
    def __init__(self) -> None:
        self.first_entered = asyncio.Event()
        self.second_entered = asyncio.Event()
        self.release_first = asyncio.Event()
        self.second_context: tuple[str, ...] = ()

    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        if item.current.external_message_id == "one":
            self.first_entered.set()
            await self.release_first.wait()
        else:
            self.second_context = tuple(msg.external_message_id for msg in item.context)
            self.second_entered.set()
        return _allow_result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "sequence-v1"}


class SlowClassifier(LocalClassifier):
    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        del item
        await asyncio.sleep(0.08)
        return _allow_result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "slow-v1"}


def _allow_result() -> ClassificationResult:
    return ClassificationResult(
        action=Action.ALLOW,
        label=Label.SAFE,
        scores={"SAFE": 1.0},
        rule_hits=(),
        reason_codes=("test_allow",),
        related_message_ids=(),
        model_version="test-v1",
    )


def _request(message_id: str) -> ModerationRequest:
    return ModerationRequest(
        platform="minecraft",
        scope_id="smp:global",
        external_message_id=message_id,
        sender_id="player",
        occurred_at=datetime.now(UTC),
        text="hello",
    )


def _runtime(settings: Settings, classifier: LocalClassifier) -> ModerationRuntime:
    store = ModerationStore(settings.database_path)
    context = RollingContextStore(45, 10, 10, 5, 8)
    advisory = AdvisoryDispatcher(store, DisabledAdvisoryClient(), False, 1, 1, 100)
    return ModerationRuntime(settings, store, context, classifier, advisory)


@pytest.mark.asyncio
async def test_request_queue_is_bounded(settings) -> None:
    configured = replace(settings, request_queue_size=1, request_workers=1, request_timeout_ms=1000)
    classifier = BlockingClassifier()
    runtime = _runtime(configured, classifier)
    await runtime._store.initialize()
    await runtime.start()
    principal = Principal("rosechat", frozenset({"moderate"}))
    try:
        first = asyncio.create_task(runtime.submit(_request("one"), principal))
        await classifier.entered.wait()
        second = asyncio.create_task(runtime.submit(_request("two"), principal))
        await asyncio.sleep(0)
        with pytest.raises(RequestQueueFull):
            await runtime.submit(_request("three"), principal)
        classifier.release.set()
        await asyncio.gather(first, second)
    finally:
        classifier.release.set()
        await runtime.stop()


@pytest.mark.asyncio
async def test_request_deadline_is_bounded_and_worker_can_finish(settings) -> None:
    configured = replace(settings, request_timeout_ms=10, classifier_timeout_ms=200)
    runtime = _runtime(configured, SlowClassifier())
    await runtime._store.initialize()
    await runtime.start()
    principal = Principal("rosechat", frozenset({"moderate"}))
    try:
        with pytest.raises(ProcessingTimeout):
            await runtime.submit(_request("slow"), principal)
        await asyncio.sleep(0.12)
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_same_scope_requests_preserve_context_order(settings) -> None:
    configured = replace(
        settings, request_workers=2, request_timeout_ms=1000, classifier_timeout_ms=800
    )
    classifier = SequencingClassifier()
    runtime = _runtime(configured, classifier)
    await runtime._store.initialize()
    await runtime.start()
    principal = Principal("rosechat", frozenset({"moderate"}))
    try:
        first = asyncio.create_task(runtime.submit(_request("one"), principal))
        await classifier.first_entered.wait()
        second = asyncio.create_task(runtime.submit(_request("two"), principal))
        await asyncio.sleep(0.02)
        assert not classifier.second_entered.is_set()
        classifier.release_first.set()
        await asyncio.gather(first, second)
        assert classifier.second_context == ("one",)
    finally:
        classifier.release_first.set()
        await runtime.stop()
