"""Data/Model v2 synthetic-only invariant checks.

No private logs are read. Run:
    python tools/data_v2/test_method_invariants.py

This is a small safety fixture, NOT the production session linker,
near-duplicate audit, privacy scanner, or Policy-v1 resolver.
"""

from __future__ import annotations

import unittest


def validate_window(record: dict) -> list[str]:
    """Validate a synthetic as-of-target context window."""
    errors: list[str] = []
    messages = record.get("messages", [])
    target_index = record.get("target_index")

    if not isinstance(messages, list) or not messages:
        return ["missing_messages"]
    if isinstance(target_index, bool) or not isinstance(target_index, int):
        return ["invalid_target_index"]
    if not (0 <= target_index < len(messages)):
        return ["invalid_target_index"]
    if target_index != len(messages) - 1:
        errors.append("target_not_latest")

    offsets: list[int] = []
    scopes: set[str] = set()
    for message in messages:
        if not isinstance(message, dict):
            errors.append("invalid_message")
            continue
        offset = message.get("offset_ms")
        if isinstance(offset, bool) or not isinstance(offset, int):
            errors.append("bad_timestamp")
            continue
        offsets.append(offset)
        scope = message.get("scope_id")
        if not isinstance(scope, str) or not scope:
            errors.append("missing_scope")
        else:
            scopes.add(scope)
        if not isinstance(message.get("speaker"), str) or not message["speaker"]:
            errors.append("missing_speaker")
        if not isinstance(message.get("text"), str):
            errors.append("missing_text")

    if len(scopes) > 1 and not record.get("verified_cross_scope_link"):
        errors.append("unverified_cross_scope")
    if offsets:
        if offsets[-1] != 0:
            errors.append("target_time_not_zero")
        if any(offset > 0 for offset in offsets):
            errors.append("future_message")
        if offsets != sorted(offsets):
            errors.append("nonchronological")
        if not record.get("verified_long_gap_link"):
            if any((right - left) > 120000 for left, right in zip(offsets, offsets[1:])):
                errors.append("unlinked_afk_gap")
    return sorted(set(errors))


def find_split_leaks(records: list[dict]) -> list[str]:
    """Find contradictory group assignments; do NOT consider generic text equal leakage."""
    membership: dict[tuple[str, str], tuple[str, str]] = {}
    leaks: set[str] = set()
    for record in records:
        split = record["split"]
        record_id = record["example_id"]
        if split not in {"train", "dev", "holdout"}:
            raise ValueError("Unrecognized split")
        groups: list[tuple[str, str]] = [("example", record_id)]
        for field in ("session_group", "family_group", "canonical_event_id"):
            value = record.get(field)
            if value:
                groups.append((field, str(value)))
        for message_id in record.get("source_message_ids", []):
            groups.append(("source_message", str(message_id)))
        for parent_id in record.get("parent_ids", []):
            groups.append(("example", str(parent_id)))
        for group in groups:
            previous = membership.get(group)
            if previous and previous[0] != split:
                leaks.add(f"{group[0]}:{group[1]}")
            else:
                membership[group] = (split, record_id)
    return sorted(leaks)


def synthetic_record(
    example_id: str = "FX-001",
    split: str = "train",
    session: str = "SESSION-A",
    family: str = "FAMILY-A",
    source_ids: tuple[str, ...] = ("msg-1", "msg-2"),
) -> dict:
    return {
        "example_id": example_id,
        "split": split,
        "session_group": session,
        "family_group": family,
        "source_message_ids": list(source_ids),
        "parent_ids": [],
        "target_index": 1,
        "messages": [
            {"speaker": "P1", "scope_id": "mc-global", "offset_ms": -1800,
             "text": "queue for duels?"},
            {"speaker": "P2", "scope_id": "mc-global", "offset_ms": 0,
             "text": "sure after this round"},
        ],
    }


class DataV2FixtureTests(unittest.TestCase):
    def test_valid_window(self) -> None:
        self.assertEqual(validate_window(synthetic_record()), [])

    def test_future_context_rejected(self) -> None:
        r = synthetic_record()
        r["messages"][1]["offset_ms"] = 100
        self.assertIn("future_message", validate_window(r))

    def test_target_must_be_current_message(self) -> None:
        r = synthetic_record()
        r["target_index"] = 0
        self.assertIn("target_not_latest", validate_window(r))

    def test_scope_switch_needs_verified_link(self) -> None:
        r = synthetic_record()
        r["messages"][0]["scope_id"] = "discord-general"
        self.assertIn("unverified_cross_scope", validate_window(r))

    def test_afk_gap_not_naively_bridged(self) -> None:
        r = synthetic_record()
        r["messages"][0]["offset_ms"] = -300000
        self.assertIn("unlinked_afk_gap", validate_window(r))

    def test_split_same_family(self) -> None:
        a = synthetic_record()
        b = synthetic_record("FX-002", "holdout", "SESSION-B", "FAMILY-A",
                             ("msg-3", "msg-4"))
        self.assertIn("family_group:FAMILY-A", find_split_leaks([a, b]))

    def test_split_shared_context_message(self) -> None:
        a = synthetic_record()
        b = synthetic_record("FX-002", "dev", "SESSION-B", "FAMILY-B",
                             ("msg-2", "msg-3"))
        self.assertIn("source_message:msg-2", find_split_leaks([a, b]))

    def test_augmentation_parent_stays_together(self) -> None:
        a = synthetic_record()
        b = synthetic_record("FX-002", "dev", "SESSION-B", "FAMILY-B",
                             ("msg-3", "msg-4"))
        b["parent_ids"] = ["FX-001"]
        self.assertIn("example:FX-001", find_split_leaks([a, b]))

    def test_generic_phrase_is_not_alone_leakage(self) -> None:
        a = synthetic_record()
        b = synthetic_record("FX-002", "dev", "SESSION-B", "FAMILY-B",
                             ("msg-3", "msg-4"))
        b["messages"][1]["text"] = a["messages"][1]["text"]
        self.assertEqual(find_split_leaks([a, b]), [])


if __name__ == "__main__":
    unittest.main()
