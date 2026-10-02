from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_ALLOWED_PERMISSIONS = frozenset({"moderate", "review:read", "review:write"})


@dataclass(frozen=True, slots=True)
class ClientCredential:
    client_id: str
    token: str
    permissions: frozenset[str]


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path = Path("runtime-data/moderation.sqlite3")
    policy_version: str = "draft"
    clients: tuple[ClientCredential, ...] = ()
    request_queue_size: int = 256
    request_workers: int = 4
    request_timeout_ms: int = 250
    classifier_timeout_ms: int = 150
    context_window_seconds: int = 45
    context_max_scopes: int = 512
    context_messages_per_scope: int = 100
    context_sender_messages: int = 5
    context_channel_messages: int = 8
    openai_advisory_enabled: bool = False
    openai_api_key: str | None = None
    openai_model: str = "omni-moderation-latest"
    openai_timeout_ms: int = 1500
    openai_queue_size: int = 256
    openai_workers: int = 2

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_path=Path(_env("AI_MOD_DATABASE_PATH", "runtime-data/moderation.sqlite3")),
            policy_version=_env("AI_MOD_POLICY_VERSION", "draft"),
            clients=_parse_clients(os.getenv("AI_MOD_CLIENTS_JSON", "[]")),
            request_queue_size=_positive_int("AI_MOD_REQUEST_QUEUE_SIZE", 256),
            request_workers=_positive_int("AI_MOD_REQUEST_WORKERS", 4),
            request_timeout_ms=_positive_int("AI_MOD_REQUEST_TIMEOUT_MS", 250),
            classifier_timeout_ms=_positive_int("AI_MOD_CLASSIFIER_TIMEOUT_MS", 150),
            context_window_seconds=_positive_int("AI_MOD_CONTEXT_WINDOW_SECONDS", 45),
            context_max_scopes=_positive_int("AI_MOD_CONTEXT_MAX_SCOPES", 512),
            context_messages_per_scope=_positive_int("AI_MOD_CONTEXT_MESSAGES_PER_SCOPE", 100),
            context_sender_messages=_positive_int("AI_MOD_CONTEXT_SENDER_MESSAGES", 5),
            context_channel_messages=_positive_int("AI_MOD_CONTEXT_CHANNEL_MESSAGES", 8),
            openai_advisory_enabled=_bool_env("AI_MOD_OPENAI_ADVISORY_ENABLED", False),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=_env("AI_MOD_OPENAI_MODEL", "omni-moderation-latest"),
            openai_timeout_ms=_positive_int("AI_MOD_OPENAI_TIMEOUT_MS", 1500),
            openai_queue_size=_positive_int("AI_MOD_OPENAI_QUEUE_SIZE", 256),
            openai_workers=_positive_int("AI_MOD_OPENAI_WORKERS", 2),
        )


def _env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    value = default if raw is None else int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return normalized == "true"


def _parse_clients(raw: str) -> tuple[ClientCredential, ...]:
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("AI_MOD_CLIENTS_JSON must be a JSON array")
    clients = tuple(_parse_client(item) for item in parsed)
    ids = [client.client_id for client in clients]
    if len(ids) != len(set(ids)):
        raise ValueError("AI_MOD_CLIENTS_JSON contains duplicate client ids")
    return clients


def _parse_client(item: object) -> ClientCredential:
    if not isinstance(item, dict):
        raise ValueError("each client credential must be a JSON object")
    client_id = str(item.get("id", "")).strip()
    token = str(item.get("token", "")).strip()
    permissions_raw = item.get("permissions", [])
    if not client_id or not token or not isinstance(permissions_raw, list):
        raise ValueError("client id, token, and permissions are required")
    permissions = frozenset(str(value) for value in permissions_raw)
    unknown = permissions - _ALLOWED_PERMISSIONS
    if unknown:
        raise ValueError(f"unknown client permissions: {sorted(unknown)}")
    return ClientCredential(client_id, token, permissions)
