"""Deterministic two-reviewer assignment for synthetic-only blinded packets.

The coordinator-only manifest must be separate from each reviewer's packet
file. This does not authenticate reviewer identity or certify label truth.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .blind_review import KEY_ENV, _outside_checkout, _write_jsonl

PACKET_FIELDS = {
    "packet_id", "platform_hint", "channel_profile", "messages", "target_index",
}
REVIEWER_ID = re.compile(r"[A-Za-z0-9_-]{2,32}$")


def packet_digest(packet: dict[str, object]) -> str:
    encoded = json.dumps(packet, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _check_packet(packet: dict[str, object]) -> str:
    if set(packet) != PACKET_FIELDS:
        raise ValueError("invalid blind packet fields")
    identifier = packet["packet_id"]
    messages = packet["messages"]
    if not isinstance(identifier, str) or not re.fullmatch(r"R-[a-f0-9]{24}", identifier):
        raise ValueError("invalid opaque packet ID")
    if not isinstance(messages, list) or not messages:
        raise ValueError("review packet has no messages")
    if packet["target_index"] != len(messages) - 1:
        raise ValueError("review packet contains post-target messages")
    if any(not isinstance(m, dict) or set(m) != {"speaker", "offset_ms", "text"}
           for m in messages):
        raise ValueError("review packet contains extra message metadata")
    return identifier


def _validate_roster(reviewers: list[str], secret: bytes) -> list[str]:
    if len(secret) < 16:
        raise ValueError("review assignment key too short")
    if not 2 <= len(reviewers) <= 20:
        raise ValueError("need 2-20 independent reviewer aliases")
    if any(not REVIEWER_ID.fullmatch(name) for name in reviewers):
        raise ValueError("invalid reviewer alias")
    if len(set(reviewers)) != len(reviewers):
        raise ValueError("duplicate reviewer alias")
    return sorted(reviewers)


def _rank(secret: bytes, identifier: str) -> str:
    return hmac.new(secret, f"assign:{identifier}".encode(), hashlib.sha256).hexdigest()


def assign_reviewers(
    packets: list[dict[str, object]], reviewer_ids: list[str], secret: bytes,
) -> tuple[dict[str, list[dict[str, object]]], list[dict[str, object]]]:
    """Each packet goes to two distinct aliases; workloads are balanced."""
    roster = _validate_roster(reviewer_ids, secret)
    seen: set[str] = set()
    for packet in packets:
        identifier = _check_packet(packet)
        if identifier in seen:
            raise ValueError("duplicate review packet")
        seen.add(identifier)
    ordered = sorted(packets, key=lambda p: _rank(secret, str(p["packet_id"])))
    per_reviewer: dict[str, list[dict[str, object]]] = defaultdict(list)
    manifest: list[dict[str, object]] = []
    for position, packet in enumerate(ordered):
        pair = [roster[position % len(roster)], roster[(position + 1) % len(roster)]]
        for alias in pair:
            per_reviewer[alias].append(packet)
        manifest.append({
            "packet_id": packet["packet_id"], "packet_sha256": packet_digest(packet),
            "assigned_reviewers": pair,
        })
    return {alias: per_reviewer[alias] for alias in roster}, manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-input", type=Path, required=True)
    parser.add_argument("--reviewers", required=True, help="comma-separated aliases")
    parser.add_argument("--reviewer-out-dir", type=Path, required=True)
    parser.add_argument("--coordinator-manifest-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        directory = _outside_checkout(args.reviewer_out_dir)
        manifest_path = _outside_checkout(args.coordinator_manifest_out)
        if directory.exists() or manifest_path.exists():
            raise ValueError("review output paths must not already exist")
        if manifest_path.is_relative_to(directory):
            raise ValueError("coordinator manifest must not be visible to reviewers")
        secret = os.environ.get(KEY_ENV, "").encode()
        packets = [
            json.loads(line) for line in args.packet_input.read_text(encoding="utf-8").splitlines()
        ]
        per_reviewer, manifest = assign_reviewers(
            packets, args.reviewers.split(","), secret
        )
        directory.mkdir(mode=0o700, parents=True)
        for alias, selected in per_reviewer.items():
            _write_jsonl(directory / f"{alias}.jsonl", selected)
        _write_jsonl(manifest_path, manifest)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Blind assignment failed: {exc}", file=sys.stderr)
        return 2
    print(f"Assigned {len(manifest)} synthetic packets to two reviewers each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
