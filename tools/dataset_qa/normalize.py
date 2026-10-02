from __future__ import annotations

import json
import unicodedata
from typing import Any

from .model import RecordRef


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _normalized_message(value: dict[str, Any]) -> list[object] | None:
    speaker = value.get("speaker")
    offset_ms = value.get("offset_ms")
    text = value.get("text")
    if not isinstance(speaker, str) or not _is_integer(offset_ms) or not isinstance(text, str):
        return None
    return [normalize_text(speaker), offset_ms, normalize_text(text)]


def normalized_context(record: RecordRef) -> dict[str, object] | None:
    platform = record.data.get("platform_hint")
    target_index = record.data.get("target_index")
    messages = record.data.get("messages")
    if (
        not isinstance(platform, str)
        or not _is_integer(target_index)
        or not isinstance(messages, list)
    ):
        return None
    normalized_messages = []
    for message in messages:
        if not isinstance(message, dict):
            return None
        normalized = _normalized_message(message)
        if normalized is None:
            return None
        normalized_messages.append(normalized)
    return {
        "platform_hint": normalize_text(platform),
        "target_index": target_index,
        "messages": normalized_messages,
    }


def exact_fingerprint(record: RecordRef) -> str | None:
    context = normalized_context(record)
    if context is None:
        return None
    return json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def structural_key(record: RecordRef) -> tuple[object, ...] | None:
    context = normalized_context(record)
    if context is None:
        return None
    messages = context["messages"]
    if not isinstance(messages, list):
        return None
    speakers = tuple(message[0] for message in messages)
    offsets = tuple(message[1] for message in messages)
    return (context["platform_hint"], context["target_index"], len(messages), speakers, offsets)


def comparison_text(record: RecordRef) -> str | None:
    context = normalized_context(record)
    if context is None:
        return None
    messages = context["messages"]
    if not isinstance(messages, list):
        return None
    parts = [str(message[2]) for message in messages]
    return " ␞ ".join(parts)
