from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "eval" / "owner-policy-v1.jsonl"
MANIFEST = ROOT / "data" / "eval" / "owner-policy-v1-manifest.json"
INTERVIEWS = (
    ROOT / "policy" / "interviews" / "2026-10-01-owner-interview.jsonl",
    ROOT / "policy" / "interviews" / "2026-10-02-owner-interview-continuation.jsonl",
)
FIXTURE_ID = re.compile(r"^OPV1-\d{4}$")
FAMILY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _interviews() -> dict[str, dict[str, Any]]:
    records = [record for path in INTERVIEWS for record in _jsonl(path)]
    return {record["interview_item_id"]: record for record in records}


def test_golden_jsonl_has_unique_traceable_fixtures() -> None:
    fixtures = _jsonl(GOLDEN)
    source = _interviews()
    ids = [fixture["example_id"] for fixture in fixtures]
    assert len(ids) == len(set(ids))
    assert all(FIXTURE_ID.fullmatch(item) for item in ids)
    for fixture in fixtures:
        assert fixture["source"] == "owner_interview"
        assert fixture["source_interview_ids"]
        assert fixture["policy_sections"]
        assert fixture["primary_source_interview_id"] in fixture["source_interview_ids"]
        assert all(item in source for item in fixture["source_interview_ids"])
        assert all(
            source[item]["status"] != "unresolved"
            for item in fixture["source_interview_ids"]
        )
        assert 0 <= fixture["target_index"] < len(fixture["messages"])


def test_golden_preserves_primary_interview_wording() -> None:
    source = _interviews()
    for fixture in _jsonl(GOLDEN):
        original = source[fixture["primary_source_interview_id"]]["messages"]
        expected = [(item["speaker"], item["text"]) for item in original]
        actual = [(item["speaker"], item["text"]) for item in fixture["messages"]]
        assert actual == expected


def test_family_ids_and_timing_normalization_are_explicit() -> None:
    for fixture in _jsonl(GOLDEN):
        family = fixture.get("family_id")
        assert family is None or FAMILY_ID.fullmatch(family)
        assert isinstance(fixture["timing_known"], bool)
        assert all(isinstance(item["offset_ms"], int) for item in fixture["messages"])


def test_manifest_covers_every_interview_record_once() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = _interviews()
    coverage = manifest["source_coverage"]["records"]
    ids = [item["interview_item_id"] for item in coverage]
    assert manifest["source_coverage"]["total_interview_records"] == len(source) == 84
    assert len(ids) == len(set(ids))
    assert set(ids) == set(source)


def test_manifest_fixture_count_and_ids_match_jsonl() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fixtures = _jsonl(GOLDEN)
    assert manifest["direct_golden_fixtures"]["count"] == len(fixtures)
    covered = {
        fixture_id
        for record in manifest["source_coverage"]["records"]
        for fixture_id in record["fixture_ids"]
    }
    assert covered == {fixture["example_id"] for fixture in fixtures}


def test_policy_only_assertions_are_marked_as_provenance_gaps() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for assertion in manifest["policy_engine_assertions"]:
        if assertion["evidence_tier"] == "policy_only":
            assert assertion["provenance_gap"] is True
            assert assertion["source_interview_ids"] == []
        else:
            assert assertion["provenance_gap"] is False
            assert assertion["source_interview_ids"]


def test_unresolved_interview_record_is_not_a_fixture_source() -> None:
    source = _interviews()
    unresolved = {item_id for item_id, item in source.items() if item["status"] == "unresolved"}
    used = {item for fixture in _jsonl(GOLDEN) for item in fixture["source_interview_ids"]}
    assert unresolved == {"W00-064"}
    assert unresolved.isdisjoint(used)


def test_quoted_condemning_slur_uses_later_owner_strike_clarification() -> None:
    fixtures = {item["example_id"]: item for item in _jsonl(GOLDEN)}
    fixture = fixtures["OPV1-0045"]
    assert fixture["strike"] is True
    assert fixture["source_interview_ids"] == ["W00-043", "W00-076"]


def _assert_optional_enum(
    fixture: dict[str, Any],
    field: str,
    allowed: frozenset[str],
) -> None:
    value = fixture.get(field)
    if value is not None:
        assert value in allowed, (fixture["example_id"], field, value)


def _assert_policy_qa_compatibility(fixture: dict[str, Any], config: Any) -> None:
    enum_fields = {
        "label": config.labels,
        "action": config.actions,
        "channel_profile": config.channel_profiles,
        "review_priority": config.review_priorities,
        "containment": config.containments,
        "support_flow": config.support_flows,
    }
    for field, allowed in enum_fields.items():
        _assert_optional_enum(fixture, field, allowed)

    strike = fixture.get("strike")
    assert strike is None or isinstance(strike, bool)

    duration = fixture.get("containment_duration_seconds")
    valid_duration = (
        duration is None
        or isinstance(duration, int)
        and not isinstance(duration, bool)
        and duration > 0
    )
    assert valid_duration

    unknown_reason_codes = set(fixture.get("reason_codes", [])) - config.reason_codes
    assert not unknown_reason_codes, (fixture["example_id"], unknown_reason_codes)


def test_golden_non_null_vocabulary_matches_merged_policy_qa_config() -> None:
    from tools.dataset_qa import load_config

    config = load_config(ROOT / "tools" / "dataset_qa" / "config.json")
    for fixture in _jsonl(GOLDEN):
        _assert_policy_qa_compatibility(fixture, config)
