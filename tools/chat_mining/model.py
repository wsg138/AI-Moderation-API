from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedMessage:
    platform: str
    channel: str
    sender: str
    text: str
    timestamp_ms: int | None
    recipient: str | None = None
