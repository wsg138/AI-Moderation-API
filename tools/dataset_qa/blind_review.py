"""Blinded, synthetic-only Policy-v1 review packet preparation.

Packets omit gold labels/outcomes and post-target messages. A separate crosswalk
must be kept away from reviewers until independent decisions are locked.
NEVER use this on private player logs or protected evaluation material.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from .asof_input import serialize_as_of_target
from .freshness import ROOT, batch_files

KEY_ENV = "ENTHUSIA_REVIEW_PACKET_KEY"
EXAMPLE_ID = re.compile(r"G(?:1[0-9]|2[0-7])-[0-9]{4}$")


def opaque_id(example_id: str, secret: bytes) -> str:
    """Hide the revealing Gxx batch prefix without public reversible IDs."""
    digest = hmac.new(secret, example_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"R-{digest[:24]}"


def make_packet(record: dict[str, Any], secret: bytes) -> dict[str, object]:
    """Use the existing fail-closed as-of-target feature projection."""
    identifier = record.get("example_id")
    if record.get("source") != "synthetic" or not isinstance(identifier, str):
        raise ValueError("expected a public synthetic record with an example_id")
    if EXAMPLE_ID.fullmatch(identifier) is None:
        raise ValueError("unexpected synthetic candidate example_id")
    return {"packet_id": opaque_id(identifier, secret), **serialize_as_of_target(record)}


def _extract(
    path: Path, secret: bytes, seen: set[str]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    raw_bytes = path.read_bytes()
    lines = raw_bytes.decode("utf-8").splitlines()
    if len(lines) != 500:
        raise ValueError(f"{path.name}: expected 500 records")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    packets: list[dict[str, object]] = []
    crosswalk: list[dict[str, object]] = []
    for line_number, line in enumerate(lines, start=1):
        record = json.loads(line)
        packet = make_packet(record, secret)
        identifier = record["example_id"]
        if identifier[:3] != path.name[:3] or identifier in seen:
            raise ValueError("mismatched or duplicate synthetic example_id")
        seen.add(identifier)
        packets.append(packet)
        crosswalk.append({
            "packet_id": packet["packet_id"], "example_id": identifier,
            "source_file": path.name, "source_sha256": digest,
            "source_line": line_number,
        })
    return packets, crosswalk


def build_packets(
    directory: Path, secret: bytes
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Require the complete candidate corpus; do not load other source groups."""
    if len(secret) < 16:
        raise ValueError("review key must have at least 16 random bytes")
    packets: list[dict[str, object]] = []
    crosswalk: list[dict[str, object]] = []
    seen: set[str] = set()
    for path in batch_files(directory, require_complete=True):
        batch_packets, batch_map = _extract(path, secret, seen)
        packets.extend(batch_packets)
        crosswalk.extend(batch_map)
    if len(packets) != 9000 or len(seen) != 9000:
        raise ValueError("expected exactly 9,000 distinct candidate records")
    return packets, crosswalk


def _outside_checkout(path: Path) -> Path:
    root = Path(__file__).resolve().parents[2]
    dest = path.resolve()
    if dest.is_relative_to(root):
        raise ValueError("review packets/crosswalk must not be written inside Git checkout")
    return dest


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-out", type=Path, required=True)
    parser.add_argument("--crosswalk-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        packet_out = _outside_checkout(args.packet_out)
        map_out = _outside_checkout(args.crosswalk_out)
        if packet_out == map_out:
            raise ValueError("packet and crosswalk outputs must be separate")
        secret = os.environ.get(KEY_ENV, "").encode("utf-8")
        packets, crosswalk = build_packets(ROOT, secret)
        _write_jsonl(packet_out, packets)
        _write_jsonl(map_out, crosswalk)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Blind packet preparation failed: {exc}", file=sys.stderr)
        return 2
    print(f"Prepared {len(packets)} public synthetic review packets; labels omitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
