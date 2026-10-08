"""Strict JSONL ingestion shared by offline reviewer assignment and intake.

Reject duplicate nested keys so reviewers and coordinators cannot interpret
the same submitted bytes differently. This is an offline tool, not admission.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 64 * 1024
MAX_ROWS = 10_000


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Bound input memory; reject empty, oversized, or ambiguous JSONL."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("review JSONL exceeds input size limit")
    lines = raw.decode("utf-8").splitlines()
    if not 1 <= len(lines) <= MAX_ROWS:
        raise ValueError("review JSONL requires 1-10,000 rows")
    if any(len(line.encode("utf-8")) > MAX_LINE_BYTES for line in lines):
        raise ValueError("review JSONL line exceeds size limit")
    rows = [json.loads(line, object_pairs_hook=_unique_object) for line in lines]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("JSONL input must contain objects only")
    return rows
