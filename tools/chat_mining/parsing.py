from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from .model import ParsedMessage

_PAPER_CHAT = re.compile(
    r"^\[(?P<ts>[^]]+)](?: \[[^]]+/INFO])?:?\s*<(?P<sender>[^<>]{1,64})>\s+(?P<text>.+)$"
)
_DISCORDSRV = re.compile(
    r"^\[(?P<ts>[^]]+)](?: \[[^]]+/INFO])?:?\s*(?:\[DiscordSRV])?\s*"
    r"\[Discord(?:\s*\|\s*(?P<channel>[^]]+))?]\s*(?P<sender>[^»:]{1,64})\s*[»:]+\s*(?P<text>.+)$",
    re.IGNORECASE,
)
_SIMPLE_DISCORD = re.compile(
    r"^\[(?P<ts>[^]]+)]\s*\[#(?P<channel>[^]]+)]\s*(?P<sender>[^:]{1,64}):\s*(?P<text>.+)$"
)
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S,%f",
    "%Y-%m-%d %H:%M:%S",
    "%H:%M:%S",
)


def _timestamp_ms(value: object) -> int | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    for fmt in _TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
        if fmt == "%H:%M:%S":
            return (parsed.hour * 3600 + parsed.minute * 60 + parsed.second) * 1000
        return int(parsed.replace(tzinfo=UTC).timestamp() * 1000)
    try:
        return int(datetime.fromisoformat(cleaned.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def _json_sender(value: dict[str, object]) -> str | None:
    sender = value.get("author", value.get("username", value.get("sender", value.get("player"))))
    if isinstance(sender, dict):
        if sender.get("bot") is True:
            return None
        sender = sender.get("username", sender.get("name"))
    return sender.strip() if isinstance(sender, str) else None


def _json_timestamp(value: dict[str, object]) -> object:
    timestamp = value.get("timestamp", value.get("created_at"))
    if timestamp is not None:
        return timestamp
    date = value.get("date")
    time = value.get("time")
    if isinstance(date, str) and isinstance(time, str):
        return f"{date.strip()} {time.strip()}"
    return time


def _json_recipient(value: dict[str, object]) -> str | None:
    recipient = value.get("recipient")
    if not isinstance(recipient, str):
        return None
    cleaned = recipient.strip()
    return cleaned or None


def _json_message(line: str) -> ParsedMessage | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    text = value.get("content", value.get("message", value.get("text")))
    sender = _json_sender(value)
    if not isinstance(text, str) or not text.strip() or sender is None:
        return None
    platform = str(value.get("platform", value.get("source_platform", "discord"))).casefold()
    channel = str(value.get("channel", value.get("channel_name", "unknown")))
    return ParsedMessage(
        platform,
        channel,
        sender,
        text.strip(),
        _timestamp_ms(_json_timestamp(value)),
        _json_recipient(value),
    )


def parse_line(line: str) -> ParsedMessage | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith("{"):
        parsed = _json_message(stripped)
        if parsed is not None:
            return parsed
    patterns = (
        (_DISCORDSRV, "discord"),
        (_SIMPLE_DISCORD, "discord"),
        (_PAPER_CHAT, "minecraft"),
    )
    for pattern, platform in patterns:
        match = pattern.match(stripped)
        if match is None:
            continue
        groups = match.groupdict()
        channel = groups.get("channel") or ("global" if platform == "minecraft" else "unknown")
        return ParsedMessage(
            platform,
            channel.strip(),
            groups["sender"].strip(),
            groups["text"].strip(),
            _timestamp_ms(groups["ts"]),
        )
    return None
