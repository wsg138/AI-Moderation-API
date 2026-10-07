from __future__ import annotations

import sqlite3
from dataclasses import replace

from fastapi.testclient import TestClient
from moderation_api.app import create_app
from moderation_api.models import (
    ClassificationInput,
    IncidentKind,
    IncidentSignal,
    Label,
    MessageAction,
    ReviewPriority,
    StrikeRecommendation,
)

from .helpers import payload, result


class SplitClassifier:
    def __init__(self) -> None:
        self.calls = 0

    async def classify(self, item: ClassificationInput):
        self.calls += 1
        if item.current.text == "irl" and item.context:
            prior = item.context[-1]
            return result(
                action=MessageAction.BLOCK,
                label=Label.REAL_WORLD_THREAT,
                review=ReviewPriority.URGENT,
                strike=StrikeRecommendation.STRIKE,
                related=(prior.external_message_id, item.current.external_message_id),
                evidence=(prior.event_id,),
                reasons=("split_message_context", "explicit_real_world_cue"),
            )
        return result(label=Label.GAMEPLAY_VIOLENCE)

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "test-v1"}


class BrokenClassifier:
    async def classify(self, item: ClassificationInput):
        del item
        raise RuntimeError("broken")

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "broken-v1"}


class IncidentClassifier:
    async def classify(self, item: ClassificationInput):
        base = result(label=Label.SEVERE_HARASSMENT, review=ReviewPriority.NORMAL)
        return replace(
            base,
            incident=IncidentSignal(
                incident_key="dogpile:target-b:1",
                kind=IncidentKind.DOGPILE,
                severity=72,
                participant_ids=(item.current.sender_id,),
                target_ids=("target-b",),
                coordinated=False,
            ),
        )

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "incident-v1"}


class SupportContextClassifier:
    async def classify(self, item: ClassificationInput):
        if item.current.text.startswith("bad-context"):
            return result(
                action=MessageAction.BLOCK,
                label=Label.SEVERE_HARASSMENT,
                review=ReviewPriority.NORMAL,
                strike=StrikeRecommendation.STRIKE,
                reasons=("support_history_test",),
            )
        return result()

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "support-context-v1"}


def test_separated_decision_dimensions_and_retroactive_ids(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitClassifier())
    with TestClient(app) as client:
        first = client.post("/v1/moderate", headers=rose_headers, json=payload("m1", "stab"))
        second = client.post("/v1/moderate", headers=rose_headers, json=payload("m2", "irl", 2))

    body = second.json()
    assert first.status_code == 200
    assert body["message_action"] == "BLOCK"
    assert body["semantic_label"] == "REAL_WORLD_THREAT"
    assert body["review_priority"] == "URGENT"
    assert body["strike_recommendation"] == "STRIKE"
    assert body["containment"] == "NONE"
    assert body["support_flow"] == "NONE"
    assert body["related_message_ids"] == ["m1", "m2"]


def test_exempt_scope_never_classifies_or_persists(settings, rose_headers) -> None:
    classifier = SplitClassifier()
    app = create_app(settings=settings, classifier=classifier)
    body = payload(
        "ticket-1",
        "private evidence",
        platform="discord",
        channel_profile="discord_ticket_exempt",
        scope_id="guild",
        channel_id="ticket-7",
    )
    with TestClient(app) as client:
        response = client.post("/v1/moderate", headers=rose_headers, json=body)

    assert response.json()["ingestion_status"] == "SKIPPED_EXEMPT"
    assert response.json()["event_id"] is None
    assert classifier.calls == 0
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM moderation_events").fetchone()[0] == 0


def test_platform_profile_mismatch_is_rejected(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitClassifier())
    body = payload("bad", "hello", channel_profile="discord_ticket_exempt")
    with TestClient(app) as client:
        response = client.post("/v1/moderate", headers=rose_headers, json=body)
    assert response.status_code == 422


def test_idempotent_retry_and_conflicting_reuse(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitClassifier())
    with TestClient(app) as client:
        first = client.post("/v1/moderate", headers=rose_headers, json=payload("same", "hello"))
        retry = client.post("/v1/moderate", headers=rose_headers, json=payload("same", "hello"))
        conflict = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("same", "changed")
        )
    assert retry.json()["event_id"] == first.json()["event_id"]
    assert retry.json()["idempotent_replay"] is True
    assert conflict.status_code == 409


def test_mirror_dedup_links_platform_message_ids(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=SplitClassifier())
    first_body = payload("mc-1", "hello", canonical_message_id="mirror-42")
    mirror_body = payload(
        "discord-1",
        "hello",
        platform="discord",
        channel_profile="discord_general",
        scope_id="guild",
        channel_id="general",
        canonical_message_id="mirror-42",
    )
    with TestClient(app) as client:
        first = client.post("/v1/moderate", headers=rose_headers, json=first_body)
        mirror = client.post("/v1/moderate", headers=rose_headers, json=mirror_body)

    assert mirror.json()["event_id"] == first.json()["event_id"]
    assert mirror.json()["idempotent_replay"] is True
    refs = {item["external_message_id"] for item in mirror.json()["related_messages"]}
    assert refs == {"mc-1", "discord-1"}
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM moderation_events").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM message_aliases").fetchone()[0] == 2


def test_classifier_failure_is_explicit_fail_open(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=BrokenClassifier())
    with TestClient(app) as client:
        response = client.post("/v1/moderate", headers=rose_headers, json=payload("broken", "x"))
    body = response.json()
    assert body["message_action"] == "ALLOW"
    assert body["ingestion_status"] == "FAIL_OPEN"
    assert body["review_priority"] == "NONE"
    assert body["strike_recommendation"] == "NONE"
    assert body["fallback_state"] == "classifier_error"


def test_authentication_and_permissions(settings, rose_headers, staff_headers) -> None:
    app = create_app(settings=settings, classifier=SplitClassifier())
    with TestClient(app) as client:
        missing = client.post("/v1/moderate", json=payload("missing", "x"))
        forbidden = client.post("/v1/moderate", headers=staff_headers, json=payload("no", "x"))
        allowed = client.post("/v1/moderate", headers=rose_headers, json=payload("yes", "x"))
    assert missing.status_code == 401
    assert forbidden.status_code == 403
    assert allowed.status_code == 200


def _seed_support_context(client: TestClient, rose_headers: dict[str, str]):
    meaningful = client.post(
        "/v1/moderate",
        headers=rose_headers,
        json=payload(
            "support-bad",
            "bad-context raw private phrase",
            sender_id="platform-player-a",
            sender_identity_id="identity-player-a",
        ),
    )
    client.post(
        "/v1/moderate",
        headers=rose_headers,
        json=payload(
            "support-safe",
            "ordinary benign message",
            1,
            sender_id="platform-player-a",
            sender_identity_id="identity-player-a",
        ),
    )
    client.post(
        "/v1/moderate",
        headers=rose_headers,
        json=payload(
            "support-unlinked",
            "bad-context should not match identity lookup",
            2,
            sender_id="identity-player-a",
        ),
    )
    return meaningful


def _assert_support_context_minimized(response, meaningful) -> None:
    assert response.status_code == 200
    body = response.json()
    assert body["subject_id"] == "identity-player-a"
    assert len(body["decisions"]) == 1
    decision = body["decisions"][0]
    assert decision["event_id"] == meaningful.json()["event_id"]
    assert decision["semantic_label"] == "SEVERE_HARASSMENT"
    assert decision["message_action"] == "BLOCK"
    assert decision["decision_source"] == "AI"
    for forbidden in (
        "bad-context raw private phrase",
        "platform-player-a",
        "channel_id",
        "scope_id",
        "sender_id",
    ):
        assert forbidden not in response.text


def test_support_context_requires_dedicated_permission_and_minimizes_data(
    settings,
    rose_headers,
    staff_headers,
    support_headers,
) -> None:
    app = create_app(settings=settings, classifier=SupportContextClassifier())
    with TestClient(app) as client:
        meaningful = _seed_support_context(client, rose_headers)
        missing_auth = client.get("/v1/support-context/identity-player-a")
        wrong_permission = client.get(
            "/v1/support-context/identity-player-a",
            headers=staff_headers,
        )
        response = client.get(
            "/v1/support-context/identity-player-a?limit=10",
            headers=support_headers,
        )

    assert meaningful.status_code == 200
    assert missing_auth.status_code == 401
    assert wrong_permission.status_code == 403
    _assert_support_context_minimized(response, meaningful)


def _accepted_correction_payload(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "reviewer_id": "admin-reviewer",
        "authority": "ADMIN",
        "corrected": {
            "semantic_label": "LOW_LEVEL_HARASSMENT",
            "message_action": "ALLOW",
            "review_priority": "NONE",
            "strike_recommendation": "EVIDENCE",
            "containment": "NONE",
            "containment_duration_seconds": None,
            "support_flow": "NONE",
            "reason_codes": ["staff_corrected"],
        },
        "note": "Owner-reviewed correction for support context.",
    }


def test_support_context_uses_accepted_staff_correction(
    settings,
    rose_headers,
    admin_headers,
    support_headers,
) -> None:
    app = create_app(settings=settings, classifier=SupportContextClassifier())
    with TestClient(app) as client:
        moderated = client.post(
            "/v1/moderate",
            headers=rose_headers,
            json=payload(
                "support-corrected",
                "bad-context corrected later",
                sender_identity_id="identity-corrected",
            ),
        )
        correction = client.post(
            "/v1/review-corrections",
            headers=admin_headers,
            json=_accepted_correction_payload(moderated.json()["event_id"]),
        )
        response = client.get(
            "/v1/support-context/identity-corrected",
            headers=support_headers,
        )

    assert moderated.status_code == 200
    assert correction.status_code == 201
    assert correction.json()["status"] == "ACCEPTED"
    decision = response.json()["decisions"][0]
    assert decision["semantic_label"] == "LOW_LEVEL_HARASSMENT"
    assert decision["message_action"] == "ALLOW"
    assert decision["strike_recommendation"] == "EVIDENCE"
    assert decision["reason_codes"] == ["staff_corrected"]
    assert decision["decision_source"] == "ACCEPTED_CORRECTION"


def test_multi_sender_incident_representation(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=IncidentClassifier())
    with TestClient(app) as client:
        first = client.post(
            "/v1/moderate",
            headers=rose_headers,
            json=payload("a", "leave", sender_id="a", target_ids=["target-b"]),
        )
        second = client.post(
            "/v1/moderate",
            headers=rose_headers,
            json=payload("b", "go", 1, sender_id="c", target_ids=["target-b"]),
        )
    assert first.json()["incident"]["incident_id"] == second.json()["incident"]["incident_id"]
    assert second.json()["incident"]["kind"] == "DOGPILE"
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM incident_events").fetchone()[0] == 2
