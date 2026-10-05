from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.dataset_qa import analyze_records, load_and_validate, load_config
from tools.w21_candidate_audit import audit
from tools.w21_generate_candidates import OUTPUT_PATH, build_records, render_jsonl

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "tools/dataset_qa/config.json"


def _is_repeated_evasion(record: dict[str, Any]) -> bool:
    return (
        record["action"] == "BLOCK"
        and len(record["messages"]) >= 2
        and "obfuscated_evasion" in record["reason_codes"]
    )


def _is_allowed_obfuscated(record: dict[str, Any]) -> bool:
    return record["action"] == "ALLOW" and any(
        "\u200b" in message["text"] or "⚔" in message["text"]
        for message in record["messages"]
    )


def test_w21_candidate_file_is_deterministic() -> None:
    expected = render_jsonl(build_records())
    assert OUTPUT_PATH.read_text(encoding="utf-8") == expected


def test_w21_candidate_schema_and_range_are_clean() -> None:
    config = load_config(CONFIG)
    loaded = load_and_validate(OUTPUT_PATH, config, "G21:1-500")
    result = analyze_records(loaded, config)
    assert result.errors() == []
    assert result.warnings() == []
    assert len(result.records) == 500


def test_w21_families_are_complete_and_candidate_only() -> None:
    records = build_records()
    families: dict[str, int] = {}
    for record in records:
        assert record["source"] == "w21_synthetic_candidate"
        assert "not admitted to frozen training" in record["notes"]
        families[record["family_id"]] = families.get(record["family_id"], 0) + 1
    assert len(families) == 25
    assert set(families.values()) == {20}


def test_w21_repeated_evasion_and_negative_controls_exist() -> None:
    records = build_records()
    assert sum(map(_is_repeated_evasion, records)) >= 20
    assert sum(map(_is_allowed_obfuscated, records)) >= 20


def test_w21_has_no_exact_or_trivial_accepted_leakage() -> None:
    result = audit()
    assert result["exact_collisions"] == []
    assert result["trivial_near_collisions"] == []
