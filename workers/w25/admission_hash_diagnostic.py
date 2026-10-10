"""Check the *bytes* of the public W21 W25 admission source, never its content.

Diagnostic only: does not modify files, manifests or validation policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/candidates/W21-adversarial-evasion.jsonl"
MANIFEST = ROOT / "workers/w25/admissions.json"


def report() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    record = next(
        item for item in manifest["sources"]
        if item["path"] == "data/candidates/W21-adversarial-evasion.jsonl"
    )
    return {
        "source": _inspect(SOURCE, record["sha256"]),
        "split": _inspect(
            ROOT / record["partition_manifest"], record["partition_manifest_sha256"]
        ),
        "modifies_files": False,
        "raw_content_exposed": False,
    }


def _inspect(path: Path, expected: str) -> dict[str, object]:
    raw = path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    return {
        "manifest_matches_raw": hashlib.sha256(raw).hexdigest() == expected,
        "manifest_matches_crlf_normalized": (
            hashlib.sha256(normalized).hexdigest() == expected
        ),
        "contains_crlf": b"\r\n" in raw,
        "sha256_expected": expected,
        "sha256_raw": hashlib.sha256(raw).hexdigest(),
        "sha256_crlf_normalized": hashlib.sha256(normalized).hexdigest(),
    }


def _planned_repairs(targets: tuple[tuple[Path, str], ...]) -> list[tuple[Path, bytes]]:
    repairs: list[tuple[Path, bytes]] = []
    for path, expected in targets:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() == expected:
            continue
        normalized = raw.replace(b"\r\n", b"\n")
        if raw == normalized or hashlib.sha256(normalized).hexdigest() != expected:
            raise ValueError("Unknown byte difference; no files changed")
        repairs.append((path, normalized))
    return repairs


def _replace_atomically(path: Path, normalized: bytes) -> None:
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = handle.name
            handle.write(normalized)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def repair_confirmed_crlf() -> list[str]:
    """Only canonicalize files whose LF digest matches the frozen manifest."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    record = next(
        item for item in manifest["sources"]
        if item["path"] == "data/candidates/W21-adversarial-evasion.jsonl"
    )
    targets = (
        (SOURCE, record["sha256"]),
        (ROOT / record["partition_manifest"], record["partition_manifest_sha256"]),
    )
    repairs = _planned_repairs(targets)
    for path, normalized in repairs:
        _replace_atomically(path, normalized)
    return [str(path.relative_to(ROOT)) for path, _ in repairs]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair-confirmed-crlf", action="store_true")
    args = parser.parse_args()
    if args.repair_confirmed_crlf:
        print(json.dumps({"repaired_paths": repair_confirmed_crlf()}))
    print(json.dumps(report(), sort_keys=True, indent=2))
