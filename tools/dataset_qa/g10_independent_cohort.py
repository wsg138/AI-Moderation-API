"""Prepare all 500 public synthetic G10 cases for *independent* blind review.

Reviewers get an HMAC-shuffled, as-of-target corpus with no source labels,
prior proposal categories or future messages. The coordinator crosswalk
is isolated and nothing here authenticates reviewers or certifies labels.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any

from .blind_review import KEY_ENV, _outside_checkout, _write_review_outputs, make_packet
from .freshness import ROOT
from .gameplay_blackmail_proposals import PINNED_SOURCE_BLOB_SHA1, _blob_sha1
from .owner_blackmail_audit import G10, _load_synthetic_g10


def _order(identifier: str, secret: bytes) -> str:
    return hmac.new(
        secret, f"g10-review-order:{identifier}".encode(), hashlib.sha256
    ).hexdigest()


def _source_rows(raw: bytes) -> list[dict[str, Any]]:
    if _blob_sha1(raw) != PINNED_SOURCE_BLOB_SHA1:
        raise ValueError("G10 source changed since policy review snapshot")
    rows = _load_synthetic_g10(raw)
    identifiers = [row.get("example_id") for row in rows]
    expected = [f"G10-{i:04d}" for i in range(1, 501)]
    if identifiers != expected:
        raise ValueError("G10 source identities/line numbers do not match")
    return rows


def build_cohort(
    raw: bytes, secret: bytes,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """All G10 controls and candidate cases; no reason-based selections."""
    if len(secret) < 16:
        raise ValueError("review packet key requires 16 or more random bytes")
    rows = _source_rows(raw)
    digest = hashlib.sha256(raw).hexdigest()
    combined: list[tuple[dict[str, object], dict[str, object]]] = []
    for line, row in enumerate(rows, 1):
        packet = make_packet(row, secret)
        mapping: dict[str, object] = {
            "packet_id": packet["packet_id"],
            "example_id": row["example_id"],
            "source_file": G10,
            "source_line": line,
            "source_sha256": digest,
        }
        combined.append((packet, mapping))
    combined.sort(key=lambda entry: _order(str(entry[0]["packet_id"]), secret))
    packets = [packet for packet, _ in combined]
    mapping = [crosswalk for _, crosswalk in combined]
    if len({p["packet_id"] for p in packets}) != 500:
        raise ValueError("unexpected G10 packet ID collision")
    return packets, mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-out", type=Path, required=True)
    parser.add_argument("--coordinator-map-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        packet_out = _outside_checkout(args.packet_out)
        map_out = _outside_checkout(args.coordinator_map_out)
        if packet_out == map_out or packet_out.exists() or map_out.exists():
            raise ValueError("output paths must differ and not exist")
        if (packet_out.is_relative_to(map_out.parent)
                or map_out.is_relative_to(packet_out.parent)):
            raise ValueError("keep crosswalk outside reviewer packet directory")
        secret = os.environ.get(KEY_ENV, "").encode("utf-8")
        packets, mapping = build_cohort((ROOT / G10).read_bytes(), secret)
        _write_review_outputs(packet_out, packets, map_out, mapping)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"G10 blind cohort preparation blocked: {exc}", file=sys.stderr)
        return 2
    print(f"Prepared {len(packets)} blinded G10 synthetic packets (not reviewed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
