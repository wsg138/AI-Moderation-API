from __future__ import annotations

from fastapi.testclient import TestClient
from moderation_api.app import create_app
from moderation_api.models import ClassificationInput
from moderation_api.storage import ModerationStore

from .helpers import payload, result


class CaptureClassifier:
    def __init__(self) -> None:
        self.contexts: list[tuple[str, ...]] = []
        self.calls = 0

    async def classify(self, item: ClassificationInput):
        self.calls += 1
        self.contexts.append(tuple(message.external_message_id for message in item.context))
        return result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "capture-v1"}


def test_restart_rehydrates_bounded_context_without_duplicate_mirror(
    settings, rose_headers
) -> None:
    first_app = create_app(settings=settings, classifier=CaptureClassifier())
    with TestClient(first_app) as client:
        client.post(
            "/v1/moderate", headers=rose_headers,
            json=payload("original", "hello", canonical_message_id="canonical"),
        )
        client.post(
            "/v1/moderate", headers=rose_headers,
            json=payload(
                "mirror", "hello", platform="discord", channel_profile="discord_general",
                scope_id="guild", channel_id="general", canonical_message_id="canonical",
            ),
        )

    second_classifier = CaptureClassifier()
    second_app = create_app(settings=settings, classifier=second_classifier)
    with TestClient(second_app) as client:
        health = client.get("/health/ready")
        client.post(
            "/v1/moderate", headers=rose_headers, json=payload("after-restart", "next", 1)
        )

    assert health.json()["rehydrated_context_messages"] == 1
    assert second_classifier.contexts == [("original",)]


def test_rehydration_failure_forces_sticky_fail_open(settings, rose_headers, monkeypatch) -> None:
    classifier = CaptureClassifier()

    async def fail_rehydrate(self, window_seconds: int, limit: int):
        del self, window_seconds, limit
        raise RuntimeError("disk read failed")

    monkeypatch.setattr(ModerationStore, "load_recent_context", fail_rehydrate)
    app = create_app(settings=settings, classifier=classifier)
    with TestClient(app) as client:
        health = client.get("/health/ready")
        response = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("rehydrate-fail", "x")
        )
    assert health.status_code == 503
    assert health.json()["context_ready"] is False
    assert response.json()["message_action"] == "ALLOW"
    assert response.json()["fallback_state"] == "context_unavailable"
    assert classifier.calls == 0


def test_memory_failure_is_fail_open_not_empty_history(settings, rose_headers, monkeypatch) -> None:
    classifier = CaptureClassifier()

    async def fail_memory(self, current, limit):
        del self, current, limit
        raise RuntimeError("memory unavailable")

    monkeypatch.setattr(ModerationStore, "load_memory_snapshot", fail_memory)
    app = create_app(settings=settings, classifier=classifier)
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("memory-fail", "x")
        )
    assert response.json()["message_action"] == "ALLOW"
    assert response.json()["fallback_state"] == "memory_error"
    assert classifier.calls == 0


def test_storage_reservation_failure_is_unpersisted_fail_open(
    settings, rose_headers, monkeypatch
) -> None:
    async def fail_reserve(self, *args, **kwargs):
        del self, args, kwargs
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(ModerationStore, "reserve_event", fail_reserve)
    app = create_app(settings=settings, classifier=CaptureClassifier())
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("reserve-fail", "x")
        )
    assert response.json()["event_id"] is None
    assert response.json()["fallback_state"] == "storage_reserve_error"
