"""Check the *bytes* of the public W21 W25 admission source, never its content.

Diagnostic only: does not modify files, manifests or validation policy.
"""
from __future__ import annotations

import hashlib
import json
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


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
