"""Block notices and the authenticated ALL-decisions audit, never live enforcement."""
from __future__ import annotations

from fastapi.testclient import TestClient  # pyright: ignore[reportMissingImports]
from moderation_api.app import create_app  # pyright: ignore[reportMissingImports]
from moderation_api.models import (  # pyright: ignore[reportMissingImports]
    ClassificationInput,
    Label,
    MessageAction,
    ReviewPriority,
)

from .helpers import payload, result


class ClassificationForAudit:
    async def classify(self, item: ClassificationInput):
        current = item.current.text
        if current == "broken":
            raise RuntimeError("simulated classification error")
        if current == "harassment":
            return result(
                action=MessageAction.BLOCK,
                label=Label.SEVERE_HARASSMENT,
                reasons=("repeated_targeted_abuse",),
            )
        if current == "quoted":
            return result(
                action=MessageAction.BLOCK,
                label=Label.SLUR_USE,
                reasons=("quoted_prohibited_word",),
            )
        if current == "review":
            return result(
                label=Label.AMBIGUOUS_REVIEW,
                review=ReviewPriority.NORMAL,
                reasons=("needs_staff_review",),
            )
        return result(label=Label.SAFE, reasons=("safe",))

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "fake", "model_version": "fake-audit-1"}


def test_player_notice_is_category_based_and_replay_safe(settings, rose_headers) -> None:
    app = create_app(settings=settings, classifier=ClassificationForAudit())
    with TestClient(app) as client:
        allow = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("allow-1", "ordinary")
        ).json()
        block = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("block-1", "harassment")
        ).json()
        replay = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("block-1", "harassment")
        ).json()
        quote = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("quote-1", "quoted")
        ).json()
        fail = client.post(
            "/v1/moderate", headers=rose_headers, json=payload("fail-1", "broken")
        ).json()

    assert allow["player_notice"] is None  # nosec B101  # nosemgrep
    assert block["player_notice"] is not None  # nosec B101  # nosemgrep
    assert "may contain" in block["player_notice"]  # nosec B101  # nosemgrep
    assert "harassment" in block["player_notice"]  # nosec B101  # nosemgrep
    assert replay["player_notice"] == block["player_notice"]  # nosec B101  # nosemgrep
    assert replay["idempotent_replay"] is True  # nosec B101  # nosemgrep
    assert quote["player_notice"] is not None  # nosec B101  # nosemgrep
    assert "prohibited language" in quote["player_notice"]  # nosec B101  # nosemgrep
    assert "you used" not in quote["player_notice"].lower()  # nosec B101  # nosemgrep
    assert fail["message_action"] == "ALLOW"  # nosec B101  # nosemgrep
    assert fail["player_notice"] is None  # nosec B101  # nosemgrep


def test_all_decisions_are_reviewable_with_cursor(settings, rose_headers, staff_headers) -> None:
    app = create_app(settings=settings, classifier=ClassificationForAudit())
    with TestClient(app) as client:
        for n, word in enumerate(("ordinary", "harassment", "broken", "quoted"), 1):
            response = client.post(
                "/v1/moderate", headers=rose_headers, json=payload(f"audit-{n}", word, n)
            )
            assert response.status_code == 200  # nosec B101  # nosemgrep
        page1 = client.get(
            "/v1/decisions", headers=staff_headers, params={"limit": 2}
        )
        assert page1.status_code == 200  # nosec B101  # nosemgrep
        cursor = page1.json()["next_cursor"]
        assert cursor  # nosec B101  # nosemgrep
        page2 = client.get(
            "/v1/decisions",
            headers=staff_headers,
            params={"limit": 2, "cursor": cursor},
        )
        final = client.get(
            "/v1/decisions",
            headers=staff_headers,
            params={"cursor": page2.json()["items"][-1]["event_id"]},
        )

    first = page1.json()
    second = page2.json()
    assert len(first["items"]) == 2  # nosec B101  # nosemgrep
    assert len(second["items"]) == 2  # nosec B101  # nosemgrep
    assert second["next_cursor"] is None  # nosec B101  # nosemgrep
    assert final.json()["items"] == []  # nosec B101  # nosemgrep
    all_items = first["items"] + second["items"]
    ids = [r["event_id"] for r in all_items]
    assert len(set(ids)) == 4  # nosec B101  # nosemgrep
    assert {r["message_action"] for r in all_items} == {"ALLOW", "BLOCK"}  # nosec B101  # nosemgrep
    assert {r["ingestion_status"] for r in all_items} == {"INGESTED", "FAIL_OPEN"}  # nosec B101  # nosemgrep
    assert all("text" not in r and "sender_id" not in r for r in all_items)  # nosec B101  # nosemgrep
    assert all(r["policy_version"] == "v1" for r in all_items)  # nosec B101  # nosemgrep


def test_staff_filters_and_rejects_cursors_not_in_selected_filter(
    settings, rose_headers, staff_headers,
) -> None:
    app = create_app(settings=settings, classifier=ClassificationForAudit())
    with TestClient(app) as client:
        for n, word in enumerate(("ordinary", "harassment", "broken", "quoted", "ordinary"), 1):
            response = client.post(
                "/v1/moderate", headers=rose_headers, json=payload(f"filter-{n}", word, n)
            )
            assert response.status_code == 200  # nosec B101  # nosemgrep

        allowed = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "allowed"}
        )
        blocked = client.get(
            "/v1/decisions", headers=staff_headers,
            params={"filter": "blocked", "limit": 1}
        )
        fail_open = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "fail_open"}
        )
        invalid = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "unknown"}
        )
        correction = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "corrected"}
        )

        wrong_cursor = client.get(
            "/v1/decisions", headers=staff_headers,
            params={"filter": "allowed", "cursor": blocked.json()["items"][0]["event_id"]}
        )
        next_blocked = client.get(
            "/v1/decisions", headers=staff_headers,
            params={"filter": "blocked", "limit": 1, "cursor": blocked.json()["next_cursor"]}
        )

    assert allowed.status_code == 200  # nosec B101  # nosemgrep
    assert len(allowed.json()["items"]) == 2  # nosec B101  # nosemgrep
    assert all(r["message_action"] == "ALLOW" for r in allowed.json()["items"])  # nosec B101  # nosemgrep
    assert blocked.status_code == 200  # nosec B101  # nosemgrep
    assert blocked.json()["next_cursor"] is not None  # nosec B101  # nosemgrep
    assert fail_open.status_code == 200  # nosec B101  # nosemgrep
    assert len(fail_open.json()["items"]) == 1  # nosec B101  # nosemgrep
    assert fail_open.json()["items"][0]["degraded"] is True  # nosec B101  # nosemgrep
    assert correction.json()["items"] == []  # nosec B101  # nosemgrep
    assert invalid.status_code == 422  # nosec B101  # nosemgrep
    assert wrong_cursor.status_code == 404  # nosec B101  # nosemgrep
    assert next_blocked.status_code == 200  # nosec B101  # nosemgrep
    assert len(next_blocked.json()["items"]) == 1  # nosec B101  # nosemgrep


def test_matching_event_cursor_can_be_shared_by_overlapping_filters(
    settings, rose_headers, staff_headers,
) -> None:
    app = create_app(settings=settings, classifier=ClassificationForAudit())
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate", headers=rose_headers,
            json=payload("cursor-overlap-1", "harassment"),
        )
        assert response.status_code == 200  # nosec B101  # nosemgrep
        blocked = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "blocked"}
        )
        assert blocked.status_code == 200  # nosec B101  # nosemgrep
        cursor = blocked.json()["items"][0]["event_id"]
        overlapping = client.get(
            "/v1/decisions", headers=staff_headers,
            params={"filter": "all", "cursor": cursor},
        )

    # Cursors are event IDs; membership is checked, not the originating filter.
    assert overlapping.status_code == 200  # nosec B101  # nosemgrep


def test_exempt_no_ingestion_or_notice(settings, rose_headers, staff_headers) -> None:
    app = create_app(settings=settings, classifier=ClassificationForAudit())
    body = payload(
        "exempt-1", "quoted", platform="discord",
        channel_profile="discord_ticket_exempt", scope_id="tickets",
    )
    with TestClient(app) as client:
        skipped = client.post("/v1/moderate", headers=rose_headers, json=body)
        listing = client.get("/v1/decisions", headers=staff_headers)
    assert skipped.status_code == 200  # nosec B101  # nosemgrep
    assert skipped.json()["ingestion_status"] == "SKIPPED_EXEMPT"  # nosec B101  # nosemgrep
    assert skipped.json()["player_notice"] is None  # nosec B101  # nosemgrep
    assert listing.json() == {"items": [], "next_cursor": None}  # nosec B101  # nosemgrep


def test_decision_list_access_and_invalid_cursor(
    settings, rose_headers, staff_headers,
) -> None:
    app = create_app(settings=settings, classifier=ClassificationForAudit())
    with TestClient(app) as client:
        missing_auth = client.get("/v1/decisions")
        non_staff = client.get("/v1/decisions", headers=rose_headers)
        missing_cursor = client.get(
            "/v1/decisions", headers=staff_headers, params={"cursor": "missing"}
        )
        invalid_limit = client.get(
            "/v1/decisions", headers=staff_headers, params={"limit": 300}
        )
    assert missing_auth.status_code == 401  # nosec B101  # nosemgrep
    assert non_staff.status_code == 403  # nosec B101  # nosemgrep
    assert missing_cursor.status_code == 404  # nosec B101  # nosemgrep
    assert invalid_limit.status_code == 422  # nosec B101  # nosemgrep



def test_review_priority_filter_includes_allowed_review_not_ordinary_allow(
    settings, rose_headers, staff_headers,
) -> None:
    app = create_app(settings=settings, classifier=ClassificationForAudit())
    with TestClient(app) as client:
        for message_id, word in (("review-filter-1", "ordinary"), ("review-filter-2", "review")):
            response = client.post(
                "/v1/moderate", headers=rose_headers, json=payload(message_id, word)
            )
            assert response.status_code == 200  # nosec B101  # nosemgrep

        review_page = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "review"}
        )
        allowed_page = client.get(
            "/v1/decisions", headers=staff_headers, params={"filter": "allowed"}
        )

    assert review_page.status_code == 200  # nosec B101  # nosemgrep
    assert len(review_page.json()["items"]) == 1  # nosec B101  # nosemgrep
    reviewed = review_page.json()["items"][0]
    assert reviewed["message_action"] == "ALLOW"  # nosec B101  # nosemgrep
    assert reviewed["review_priority"] == "NORMAL"  # nosec B101  # nosemgrep
    assert len(allowed_page.json()["items"]) == 2  # nosec B101  # nosemgrep
