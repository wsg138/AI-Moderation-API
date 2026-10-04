"""Shared W12 model-input serialization.

The classifier can only use information available when the current message
arrives. Training and runtime therefore share this exact serializer:
- speakers are anonymous and assigned A/B/C... by first appearance;
- timing is relative to the current/target message (current = 0 ms);
- messages after the target are excluded as future information.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


SERIALIZATION_VERSION = "w12-v2"


@dataclass(frozen=True, slots=True)
class ModelMessage:
    speaker_key: str
    offset_ms: int
    text: str


def _speaker_marker(index: int) -> str:
    if 0 <= index < 26:
        return chr(ord("A") + index)
    return f"S{index}"


def serialize_model_input(
    channel_profile: str,
    messages: Sequence[ModelMessage],
    target_index: int,
) -> str:
    """Serialize only runtime-realizable context through the target message."""
    if not messages:
        raise ValueError("model input requires at least one message")
    if target_index < 0 or target_index >= len(messages):
        raise ValueError("target_index is outside the message sequence")

    visible = messages[: target_index + 1]
    target_offset = messages[target_index].offset_ms
    aliases: dict[str, str] = {}
    parts = [f"[PROFILE={channel_profile}]"]
    for index, message in enumerate(visible):
        speaker = aliases.setdefault(message.speaker_key, _speaker_marker(len(aliases)))
        offset = message.offset_ms - target_offset
        marker = " [TARGET]" if index == target_index else ""
        parts.append(f"[{speaker}@{offset:+d}ms]{marker} {message.text}")
    return "\n".join(parts)
