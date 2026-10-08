"""Candidate real-time model input: strictly target-as-of-time, no label leakage.

The real-time model trainer is not implemented in this repository. Any future
training/collation path must use this allowlisted boundary (or equivalently
tested, stricter logic) before constructing model features.
"""
from __future__ import annotations

from collections.abc import Mapping


def serialize_as_of_target(record: Mapping[str, object]) -> dict[str, object]:
    """Project only trusted static scope and messages available at target time."""
    raw, index, cutoff = _target_details(record)
    messages: list[dict[str, object]] = []
    for message in raw[: index + 1]:
        messages.append(_as_of_message(message, cutoff))
    return {
        "platform_hint": _static_scope(record, "platform_hint"),
        "channel_profile": _static_scope(record, "channel_profile"),
        "messages": messages,
        "target_index": index,
    }


def _target_details(record: Mapping[str, object]) -> tuple[list[object], int, int]:
    raw = record.get("messages")
    if not isinstance(raw, list):
        raise ValueError("messages must be a list")
    index = _target_index(record.get("target_index"), len(raw))
    target = raw[index]
    if not isinstance(target, dict):
        raise ValueError("target must be a message")
    cutoff = target.get("offset_ms")
    if not isinstance(cutoff, int) or isinstance(cutoff, bool):
        raise ValueError("target message must have integer offset_ms")
    return raw, index, cutoff


def _target_index(value: object, count: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("target_index must be an integer")
    if value < 0 or value >= count:
        raise ValueError("target_index outside message sequence")
    return value


def _static_scope(record: Mapping[str, object], name: str) -> str:
    value = record.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid static scope: {name}")
    return value


def _as_of_message(value: object, cutoff: int) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("message must be an object")
    offset, speaker, content = (
        value.get("offset_ms"), value.get("speaker"), value.get("text")
    )
    if not isinstance(offset, int) or isinstance(offset, bool) or offset > cutoff:
        raise ValueError("pre-target message must not occur after target")
    if not isinstance(speaker, str) or not isinstance(content, str):
        raise ValueError("invalid message text or speaker")
    return {"speaker": speaker, "offset_ms": offset, "text": content}
