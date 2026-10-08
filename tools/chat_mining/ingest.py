from __future__ import annotations

import json
import secrets
import sqlite3
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from .model import ParsedMessage
from .parsing import parse_line
from .privacy import family_fingerprint, normalized_text, pseudonymize, redact_text, stable_hash
from .store import MiningStore

_DAY_MS = 86_400_000
_SESSION_GAP_MS = 120_000
_SESSION_MAX_MS = 900_000


@dataclass(slots=True)
class IngestStats:
    lines: int = 0
    chat: int = 0
    stored: int = 0
    duplicates: int = 0
    private_skipped: int = 0


class ClockNormalizer:
    def __init__(self, store: MiningStore) -> None:
        self.store = store
        self.base = int(store.meta("clock_base") or 0)
        self.last_absolute = int(store.meta("clock_last") or 0)

    def relative(self, timestamp_ms: int | None) -> int:
        absolute = self._absolute(timestamp_ms)
        if self.base == 0:
            self.base = absolute
            self.store.set_meta("clock_base", str(self.base))
        self.last_absolute = max(self.last_absolute, absolute)
        self.store.set_meta("clock_last", str(self.last_absolute))
        return absolute - self.base

    def _absolute(self, timestamp_ms: int | None) -> int:
        if timestamp_ms is None:
            return self.last_absolute + 1000 if self.last_absolute else 1000
        if timestamp_ms >= _DAY_MS:
            return timestamp_ms
        day = self.last_absolute // _DAY_MS
        candidate = day * _DAY_MS + timestamp_ms
        if self.last_absolute and candidate < self.last_absolute - (_DAY_MS // 2):
            candidate += _DAY_MS
        return candidate


def _run_key(store: MiningStore) -> bytes:
    existing = store.meta("pseudonym_key")
    if existing is not None:
        return bytes.fromhex(existing)
    key = secrets.token_bytes(32)
    store.set_meta("pseudonym_key", key.hex())
    return key


def _load_identity_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("identity map must be a JSON object")
    if not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
        raise ValueError("identity map values must be strings")
    return value


def _duplicate_scope(row: sqlite3.Row, platform: str, channel_id: str) -> bool:
    row_platform = str(row["platform"])
    row_channel = str(row["channel"])
    return row_platform != platform or row_channel == channel_id


def _is_duplicate(
    store: MiningStore,
    sender_id: str,
    text: str,
    relative_ms: int,
    platform: str,
    channel_id: str,
) -> tuple[bool, bool]:
    recent = store.recent_sender(sender_id, relative_ms - 30_000)
    reformulation = False
    for row in recent:
        if not _duplicate_scope(row, platform, channel_id):
            continue
        age = relative_ms - int(row["relative_ms"])
        if row["normalized"] == text and age <= 15_000:
            return True, reformulation
        ratio = SequenceMatcher(None, str(row["normalized"]), text).ratio()
        if ratio >= 0.94 and age <= 5_000:
            return True, reformulation
        reformulation = reformulation or ratio >= 0.80
    return False, reformulation


def _session_id(store: MiningStore, channel: str, relative_ms: int) -> str:
    previous = store.latest_channel(channel)
    if previous is None:
        return "session_" + stable_hash(channel, str(relative_ms))[:20]
    gap_ms = relative_ms - int(previous["relative_ms"])
    session_id = str(previous["session_id"])
    started_ms = store.session_start(session_id)
    span_ms = relative_ms - started_ms if started_ms is not None else _SESSION_MAX_MS + 1
    if 0 <= gap_ms <= _SESSION_GAP_MS and span_ms <= _SESSION_MAX_MS:
        return session_id
    return "session_" + stable_hash(channel, str(relative_ms))[:20]


def _family_key(text: str, session_id: str) -> str:
    compact = "".join(ch for ch in text if ch.isalnum())
    if len(compact) < 8:
        return "short_" + stable_hash(session_id, text)[:20]
    return "family_" + family_fingerprint(text)


def _minecraft_profile(channel: str) -> str:
    if channel == "staff":
        return "minecraft_staff_exempt"
    if channel in {"private", "guild"}:
        return "minecraft_private"
    return "minecraft_public"


def _discord_profile(channel: str) -> str:
    if "ticket" in channel:
        return "discord_ticket_exempt"
    if any(term in channel for term in ("staff", "mod-log", "admin")):
        return "discord_staff_exempt"
    if any(term in channel for term in ("game", "minecraft", "smp")):
        return "discord_gaming"
    return "discord_general"


def _channel_profile(platform: str, channel: str) -> str:
    lowered = channel.casefold()
    if platform == "minecraft":
        return _minecraft_profile(lowered)
    return _discord_profile(lowered)


def _channel_id(
    parsed: ParsedMessage,
    identity_map: dict[str, str],
    run_key: bytes,
    sender_id: str,
) -> str:
    lowered = parsed.channel.casefold()
    if parsed.platform == "minecraft" and lowered == "private":
        if parsed.recipient is None:
            return "dm_" + stable_hash(sender_id, "unknown-recipient")[:20]
        recipient = identity_map.get(parsed.recipient, parsed.recipient)
        recipient_id = pseudonymize(recipient, run_key)
        left, right = sorted((sender_id, recipient_id))
        return "dm_" + stable_hash(left, right)[:20]
    if lowered == "guild":
        # The finalized server export does not contain guild identity. Sender-scoping
        # prevents unrelated guilds from being merged into one false context stream.
        return "guild_" + stable_hash(sender_id)[:20]
    if lowered == "discord_relay":
        # The source export does not identify the originating Discord channel.
        # Sender-scoping is conservative until authoritative channel metadata exists.
        return "discord_relay_" + stable_hash(sender_id)[:20]
    return "channel_" + pseudonymize(parsed.channel, run_key).removeprefix("user_")


def _store_message(
    store: MiningStore,
    source_key: str,
    line_no: int,
    parsed: ParsedMessage,
    identity_map: dict[str, str],
    run_key: bytes,
    clock: ClockNormalizer,
) -> str:
    profile = _channel_profile(parsed.platform, parsed.channel)
    if profile in {"discord_staff_exempt", "discord_ticket_exempt", "minecraft_staff_exempt"}:
        return "private"
    canonical = identity_map.get(parsed.sender, parsed.sender)
    sender_id = pseudonymize(canonical, run_key)
    channel_id = _channel_id(parsed, identity_map, run_key, sender_id)
    text = redact_text(parsed.text)
    normalized = normalized_text(text)
    relative_ms = clock.relative(parsed.timestamp_ms)
    duplicate, reformulation = _is_duplicate(
        store,
        sender_id,
        normalized,
        relative_ms,
        parsed.platform,
        channel_id,
    )
    if duplicate:
        return "duplicate"
    session_id = _session_id(store, channel_id, relative_ms)
    family_key = _family_key(normalized, session_id)
    message_id = "msg_" + stable_hash(source_key, str(line_no), sender_id, normalized)[:24]
    values = (
        message_id,
        parsed.platform,
        channel_id,
        profile,
        sender_id,
        text,
        normalized,
        relative_ms,
        session_id,
        family_key,
        int(reformulation),
        source_key,
        line_no,
    )
    store.insert_message(values)
    return "stored"


def ingest_file(
    store: MiningStore,
    path: Path,
    identity_map: dict[str, str],
    progress_every: int,
) -> IngestStats:
    stats = IngestStats()
    source_key = stable_hash(str(path.resolve()))[:24]
    start_line = store.checkpoint(source_key)
    run_key = _run_key(store)
    clock = ClockNormalizer(store)
    last_line = start_line
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            if line_no <= start_line:
                continue
            last_line = line_no
            stats.lines += 1
            parsed = parse_line(line)
            if parsed is not None:
                stats.chat += 1
                status = _store_message(
                    store, source_key, line_no, parsed, identity_map, run_key, clock
                )
                stats.stored += int(status == "stored")
                stats.duplicates += int(status == "duplicate")
                stats.private_skipped += int(status == "private")
            if line_no % progress_every == 0:
                store.save_checkpoint(source_key, line_no)
                store.commit()
                print(f"{path.name}: line {line_no:,}, stored {stats.stored:,}", file=sys.stderr)
        store.save_checkpoint(source_key, last_line)
        store.commit()
    return stats


def ingest_paths(
    store: MiningStore,
    paths: list[Path],
    identity_map_path: Path | None = None,
    progress_every: int = 50_000,
) -> IngestStats:
    if store.meta("split_seed") is not None:
        raise ValueError(
            "corpus is frozen after split creation; use a fresh database to ingest more"
        )
    identity_map = _load_identity_map(identity_map_path)
    total = IngestStats()
    for path in paths:
        stats = ingest_file(store, path, identity_map, progress_every)
        total.lines += stats.lines
        total.chat += stats.chat
        total.stored += stats.stored
        total.duplicates += stats.duplicates
        total.private_skipped += stats.private_skipped
    return total
