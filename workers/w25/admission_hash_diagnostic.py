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


def repair_confirmed_crlf() -> list[str]:
    """Repair only known repo files whose LF bytes exactly match the manifest."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    record = next(
        item for item in manifest["sources"]
        if item["path"] == "data/candidates/W21-adversarial-evasion.jsonl"
    )
    targets = (
        (SOURCE, record["sha256"]),
        (ROOT / record["partition_manifest"], record["partition_manifest_sha256"]),
    )
    # Verify *both* before touching either file; never fix unknown content.
    repairs: list[tuple[Path, bytes]] = []
    for path, expected in targets:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() == expected:
            continue
        normalized = raw.replace(b"\r\n", b"\n")
        if raw == normalized or hashlib.sha256(normalized).hexdigest() != expected:
            raise ValueError("Unknown byte difference; no files changed")
        repairs.append((path, normalized))
    changed = []
    for path, normalized in repairs:
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temp_name = handle.name
                handle.write(normalized)
            os.replace(temp_name, path)
            changed.append(str(path.relative_to(ROOT)))
        finally:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair-confirmed-crlf", action="store_true")
    args = parser.parse_args()
    if args.repair_confirmed_crlf:
        print(json.dumps({"repaired_paths": repair_confirmed_crlf()}))
    print(json.dumps(report(), sort_keys=True, indent=2))
