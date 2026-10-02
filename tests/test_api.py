from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from moderation_api.app import create_app
from moderation_api.models import Action, ClassificationInput, ClassificationResult, Label


class SplitThreatClassifier:
    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        is_real_world_cue = item.current.text.lower() == "irl"
        has_split_threat = any("stab" in prior.text.lower() for prior in item.context)
        if is_real_world_cue and has_split_threat:
            related = tuple(
                prior.external_message_id
                for prior in item.context
                if "stab" in prior.text.lower()
            )
            return ClassificationResult(
                action=Action.BLOCK,
                label=Label.REAL_WORLD_THREAT,
                scores={"REAL_WORLD_THREAT": 0.98},
                rule_hits=(),
                reason_codes=(
                    "split_message_context",
                    "explicit_real_world_cue",
                    "targeted_violence",
                ),
                related_message_ids=related + (item.current.external_message_id,),
                model_version="test-split-v1",
            )
        return ClassificationResult(
            action=Action.ALLOW,
            label=Label.GAMEPLAY_VIOLENCE,
            scores={"GAMEPLAY_VIOLENCE": 0.9},
            rule_hits=(),
            reason_codes=("minecraft_gameplay_explicit",),
            related_message_ids=(),
            model_version="test-split-v1",
        )

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test"}


class BrokenClassifier:
    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        del item
        raise RuntimeError("model unavailable")

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test"}


class UnreadyBlockingClassifier:
    async def classify(self, item: ClassificationInput) -> ClassificationResult:
        del item
        raise AssertionError("unready classifier must not be called")

    def health(self) -> dict[str, object]:
        return {"ready": False, "mode": "loading"}


def payload(message_id: str, text: str, seconds: int = 0) -> dict[str, object]:
    timestamp = datetime(2026, 10, 2, 1, 0, tzinfo=UTC) + timedelta(seconds=seconds)
    return {
        "platform": "minecraft",
        "scope_id": "smp:global",
        "channel_id": "global",
        "external_message_id": message_id,
        "sender_id": "player-a",
        "occurred_at": timestamp.isoformat(),
        "text": text,
    }


def test_split_message_context_can_retroactively_block(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitThreatClassifier())
    with TestClient(app) as client:
        first = client.post(
            "/v1/moderate",
            headers=rose_headers,
            json=payload("m1", "im gonna stab you"),
        )
        second = client.post("/v1/moderate", headers=rose_headers, json=payload("m2", "irl", 2))

    assert first.status_code == 200
    assert first.json()["action"] == "ALLOW"
    assert second.status_code == 200
    assert second.json()["action"] == "BLOCK"
    assert second.json()["related_message_ids"] == ["m1", "m2"]


def test_retry_is_idempotent_and_conflicting_reuse_is_rejected(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitThreatClassifier())
    with TestClient(app) as client:
        first = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("same", "normal message")
        )
        retry = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("same", "normal message")
        )
        conflict = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("same", "different text")
        )

    assert retry.status_code == 200
    assert retry.json()["event_id"] == first.json()["event_id"]
    assert retry.json()["idempotent_replay"] is True
    assert conflict.status_code == 409


def test_classifier_failure_returns_explicit_fail_open_allow(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=BrokenClassifier())
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("broken", "anything")
        )

    body = response.json()
    assert response.status_code == 200
    assert body["action"] == "ALLOW"
    assert body["degraded"] is True
    assert body["fallback_state"] == "classifier_error"


def test_authentication_and_permissions_are_enforced(settings, rose_headers, staff_headers) -> None:
    app = create_app(settings=settings, classifier=SplitThreatClassifier())
    with TestClient(app) as client:
        missing = client.post("/v1/moderate", json=payload("m1", "hello"))
        wrong_scope = client.post(
            "/v1/moderate", headers=staff_headers, json=payload("m2", "hello")
        )
        allowed = client.post("/v1/moderate", headers=rose_headers, json=payload("m3", "hello"))

    assert missing.status_code == 401
    assert wrong_scope.status_code == 403
    assert allowed.status_code == 200


def test_review_write_and_event_read_use_allowlisted_models(
    settings, rose_headers, staff_headers
) -> None:
    app = create_app(settings=settings, classifier=SplitThreatClassifier())
    with TestClient(app) as client:
        moderated = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("review-me", "hello")
        )
        event_id = moderated.json()["event_id"]
        review = client.post(
            "/v1/reviews",
            headers=staff_headers,
            json={
                "event_id": event_id,
                "reviewer_id": "staff-pseudonym",
                "label": "SAFE",
                "action": "ALLOW",
                "reason_codes": ["human_confirmed"],
                "note": "Reviewed in test.",
            },
        )
        event = client.get(f"/v1/events/{event_id}", headers=staff_headers)

    assert review.status_code == 201
    assert event.status_code == 200
    assert event.json()["reviews"][0]["review_id"] == review.json()["review_id"]
    assert "input_fingerprint" not in event.json()
    assert "external_key" not in event.json()


def test_health_is_independent_of_openai_key(settings) -> None:
    configured = replace(settings, openai_advisory_enabled=True, openai_api_key=None)
    app = create_app(settings=configured, classifier=SplitThreatClassifier())
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    assert ready.json()["advisory_enabled"] is False


def test_naive_timestamp_is_rejected(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitThreatClassifier())
    body = payload("naive", "hello")
    body["occurred_at"] = "2026-10-02T01:00:00"
    with TestClient(app) as client:
        response = client.post("/v1/moderate", headers=rose_headers, json=body)

    assert response.status_code == 422


def test_stub_classifier_is_not_reported_production_ready(settings) -> None:
    app = create_app(settings=settings)
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["classifier_ready"] is False


def test_unready_classifier_is_forced_fail_open(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=UnreadyBlockingClassifier())
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("loading", "anything")
        )

    body = response.json()
    assert response.status_code == 200
    assert body["action"] == "ALLOW"
    assert body["fallback_state"] == "classifier_not_ready"


def test_unknown_request_fields_are_rejected(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitThreatClassifier())
    body = payload("unknown-field", "hello")
    body["internal_admin_override"] = True
    with TestClient(app) as client:
        response = client.post("/v1/moderate", headers=rose_headers, json=body)

    assert response.status_code == 422
