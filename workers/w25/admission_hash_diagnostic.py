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
    raw = SOURCE.read_bytes()
    normalize = raw.replace(b"\r\n", b"\n")
    raw_sha = hashlib.sha256(raw).hexdigest()
    normalized_sha = hashlib.sha256(normalize).hexdigest()
    expected = record["sha256"]
    return {
        "source": record["path"],
        "manifest_matches_raw": raw_sha == expected,
        "manifest_matches_crlf_normalized": normalized_sha == expected,
        "contains_crlf": b"\r\n" in raw,
        "sha256_expected": expected,
        "sha256_raw": raw_sha,
        "sha256_crlf_normalized": normalized_sha,
        "line_count": raw.count(b"\n"),
        "modifies_files": False,
        "raw_content_exposed": False,
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
