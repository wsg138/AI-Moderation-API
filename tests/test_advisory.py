from __future__ import annotations

import httpx
import pytest
from moderation_api.advisory import AdvisoryDispatcher, DisabledAdvisoryClient, OpenAIAdvisoryClient
from moderation_api.models import AdvisoryStatus
from moderation_api.storage import ModerationStore


@pytest.mark.asyncio
async def test_openai_advisory_parses_structured_scores_without_reasoning_text() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/moderations"
        return httpx.Response(
            200,
            json={
                "model": "omni-moderation-latest",
                "results": [
                    {
                        "flagged": True,
                        "categories": {"violence": True},
                        "category_scores": {"violence": 0.91},
                    }
                ],
            },
        )

    http_client = httpx.AsyncClient(
        base_url="https://api.openai.com",
        transport=httpx.MockTransport(handler),
    )
    client = OpenAIAdvisoryClient("secret", "omni-moderation-latest", 500, http_client=http_client)
    evidence = await client.evaluate("example")
    await http_client.aclose()

    assert evidence.flagged is True
    assert evidence.scores == {"violence": 0.91}
    assert evidence.categories == {"violence": True}


def test_advisory_reservations_are_bounded_without_storage_io(tmp_path) -> None:
    store = ModerationStore(tmp_path / "not-initialized.sqlite3")
    dispatcher = AdvisoryDispatcher(
        store, DisabledAdvisoryClient(), enabled=True, queue_size=1, workers=1, timeout_ms=100
    )

    first = dispatcher.reserve()
    second = dispatcher.reserve()
    dispatcher.release()

    assert first is AdvisoryStatus.QUEUED
    assert second is AdvisoryStatus.QUEUE_SATURATED
    assert dispatcher.queue_depth == 0
