from __future__ import annotations

from fastapi.testclient import TestClient
from moderation_api.app import create_app
from moderation_api.models import ClassificationInput, Label, ReviewPriority

from .helpers import payload, result


class ReviewClassifier:
    async def classify(self, item: ClassificationInput):
        del item
        return result(label=Label.AMBIGUOUS_REVIEW, review=ReviewPriority.NORMAL)

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "test", "model_version": "review-v1"}


def correction(event_id: str, reviewer: str, authority: str = "STAFF") -> dict[str, object]:
    return {
        "event_id": event_id,
        "reviewer_id": reviewer,
        "authority": authority,
        "corrected": {
            "semantic_label": "SAFE",
            "message_action": "ALLOW",
            "review_priority": "NONE",
            "strike_recommendation": "NONE",
            "containment": "NONE",
            "containment_duration_seconds": None,
            "support_flow": "NONE",
            "reason_codes": ["human_confirmed_safe"],
        },
        "note": "reviewed",
    }


def test_two_staff_confirm_correction_and_preserve_original(
    settings, rose_headers, staff_headers
) -> None:
    app = create_app(settings=settings, classifier=ReviewClassifier())
    with TestClient(app) as client:
        event_id = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("review", "hmm")
        ).json()["event_id"]
        first = client.post(
            "/v1/review-corrections", headers=staff_headers,
            json=correction(event_id, "staff-1"),
        )
        retry = client.post(
            "/v1/review-corrections", headers=staff_headers,
            json=correction(event_id, "staff-1"),
        )
        second = client.post(
            "/v1/review-corrections", headers=staff_headers,
            json=correction(event_id, "staff-2"),
        )
        event = client.get(f"/v1/events/{event_id}", headers=staff_headers)
        queue = client.get("/v1/review-items", headers=staff_headers)
        corrected_history = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "corrected"}
        )

    assert first.json()["status"] == "PENDING_CONFIRMATION"
    assert retry.json()["approvals"] == 1
    assert second.json()["status"] == "ACCEPTED"
    body = event.json()
    assert body["decision"]["semantic_label"] == "AMBIGUOUS_REVIEW"
    assert body["accepted_correction"]["corrected"]["semantic_label"] == "SAFE"
    assert queue.json()["items"] == []
    assert corrected_history.status_code == 200  # nosec B101  # nosemgrep
    assert len(corrected_history.json()["items"]) == 1  # nosec B101  # nosemgrep
    entry = corrected_history.json()["items"][0]
    assert entry["event_id"] == event_id  # nosec B101  # nosemgrep
    assert entry["corrected"] is True  # nosec B101  # nosemgrep
    assert entry["semantic_label"] == "AMBIGUOUS_REVIEW"  # nosec B101  # nosemgrep
    assert "text" not in entry and "sender_id" not in entry  # nosec B101  # nosemgrep
    assert "input_fingerprint" not in body


def test_admin_can_immediately_override_an_accepted_correction(
    settings, rose_headers, staff_headers, admin_headers
) -> None:
    app = create_app(settings=settings, classifier=ReviewClassifier())
    with TestClient(app) as client:
        event_id = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("admin-review", "hmm")
        ).json()["event_id"]
        client.post(
            "/v1/review-corrections", headers=staff_headers,
            json=correction(event_id, "staff-1"),
        )
        client.post(
            "/v1/review-corrections", headers=staff_headers,
            json=correction(event_id, "staff-2"),
        )
        override = correction(event_id, "admin-1", "ADMIN")
        override["corrected"] = {
            **override["corrected"],
            "semantic_label": "LOW_LEVEL_HARASSMENT",
            "review_priority": "NORMAL",
            "reason_codes": ["admin_override"],
        }
        response = client.post(
            "/v1/review-corrections", headers=admin_headers, json=override
        )
        event = client.get(f"/v1/events/{event_id}", headers=admin_headers)

    assert response.json()["status"] == "ACCEPTED"
    assert response.json()["approvals"] == 1
    assert event.json()["accepted_correction"]["corrected"]["semantic_label"] == (
        "LOW_LEVEL_HARASSMENT"
    )
    assert len(event.json()["corrections"]) == 2


def test_staff_cannot_claim_admin_authority(settings, rose_headers, staff_headers) -> None:
    app = create_app(settings=settings, classifier=ReviewClassifier())
    with TestClient(app) as client:
        event_id = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("claim-admin", "hmm")
        ).json()["event_id"]
        response = client.post(
            "/v1/review-corrections", headers=staff_headers,
            json=correction(event_id, "staff-1", "ADMIN"),
        )
    assert response.status_code == 403


def test_two_staff_can_reject_pending_correction(settings, rose_headers, staff_headers) -> None:
    app = create_app(settings=settings, classifier=ReviewClassifier())
    with TestClient(app) as client:
        event_id = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("reject", "hmm")
        ).json()["event_id"]
        proposed = client.post(
            "/v1/review-corrections", headers=staff_headers,
            json=correction(event_id, "staff-1"),
        ).json()
        first = client.post(
            f"/v1/review-corrections/{proposed['proposal_id']}/reject",
            headers=staff_headers,
            json={"reviewer_id": "staff-2", "authority": "STAFF", "note": "no"},
        )
        second = client.post(
            f"/v1/review-corrections/{proposed['proposal_id']}/reject",
            headers=staff_headers,
            json={"reviewer_id": "staff-3", "authority": "STAFF", "note": "no"},
        )
    assert first.json()["status"] == "PENDING_CONFIRMATION"
    assert second.json()["status"] == "REJECTED"
    assert second.json()["rejections"] == 2
