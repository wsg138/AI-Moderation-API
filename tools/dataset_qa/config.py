from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import ExpectedRange


@dataclass(frozen=True, slots=True)
class QaConfig:
    required_fields: tuple[str, ...]
    message_required_fields: tuple[str, ...]
    labels: frozenset[str]
    actions: frozenset[str]
    review_priorities: frozenset[str]
    containments: frozenset[str]
    support_flows: frozenset[str]
    channel_profiles: frozenset[str]
    exempt_channel_profiles: frozenset[str]
    reason_codes: frozenset[str]
    id_ranges: dict[str, ExpectedRange]
    family_id_pattern: str
    near_duplicate_threshold: float
    near_contradiction_threshold: float


def _range_from_value(prefix: str, value: list[int]) -> ExpectedRange:
    if len(value) != 2:
        raise ValueError(f"range for {prefix} must have [start, end]")
    return ExpectedRange(prefix=prefix, start=int(value[0]), end=int(value[1]))


def _build_config(raw: dict[str, Any]) -> QaConfig:
    ranges = {
        prefix: _range_from_value(prefix, value)
        for prefix, value in raw["id_ranges"].items()
    }
    return QaConfig(
        required_fields=tuple(raw["required_fields"]),
        message_required_fields=tuple(raw["message_required_fields"]),
        labels=frozenset(raw["labels"]),
        actions=frozenset(raw["actions"]),
        review_priorities=frozenset(raw["review_priorities"]),
        containments=frozenset(raw["containments"]),
        support_flows=frozenset(raw["support_flows"]),
        channel_profiles=frozenset(raw["channel_profiles"]),
        exempt_channel_profiles=frozenset(raw["exempt_channel_profiles"]),
        reason_codes=frozenset(raw["reason_codes"]),
        id_ranges=ranges,
        family_id_pattern=str(raw["family_id_pattern"]),
        near_duplicate_threshold=float(raw["near_duplicate_threshold"]),
        near_contradiction_threshold=float(raw["near_contradiction_threshold"]),
    )


def load_config(path: Path | None = None) -> QaConfig:
    config_path = path or Path(__file__).with_name("config.json")
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("dataset QA config must contain a JSON object")
    return _build_config(raw)
