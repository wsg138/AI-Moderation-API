from __future__ import annotations

from pathlib import Path

import pytest
from moderation_api.config import ClientCredential, Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "moderation.sqlite3",
        clients=(
            ClientCredential("rosechat", "rose-secret", frozenset({"moderate"})),
            ClientCredential(
                "staff",
                "staff-secret",
                frozenset({"review:read", "review:write"}),
            ),
        ),
        request_queue_size=4,
        request_workers=1,
        request_timeout_ms=500,
        classifier_timeout_ms=200,
        openai_advisory_enabled=False,
    )


@pytest.fixture
def rose_headers() -> dict[str, str]:
    return {"X-Client-Id": "rosechat", "Authorization": "Bearer rose-secret"}


@pytest.fixture
def staff_headers() -> dict[str, str]:
    return {"X-Client-Id": "staff", "Authorization": "Bearer staff-secret"}
