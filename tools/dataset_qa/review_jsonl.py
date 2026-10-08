"""Strict JSONL ingestion shared by offline reviewer assignment and intake.

Reject duplicate nested keys so reviewers and coordinators cannot interpret
the same submitted bytes differently. This is an offline tool, not admission.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse JSON objects; reject duplicate keys at every depth."""
    rows = [
        json.loads(line, object_pairs_hook=_unique_object)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("JSONL input must contain objects only")
    return rows
