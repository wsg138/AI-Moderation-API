from __future__ import annotations

import json
from pathlib import Path

from tools.dataset_qa import analyze_records, build_report, load_and_validate, load_config
from tools.dataset_qa.model import ExpectedRange
from tools.dataset_qa.validate import _missing_id_diagnostics


def _record(
    example_id: str,
    *,
    text: str = "ordinary example text",
    label: str = "SAFE",
    action: str = "ALLOW",
    messages: list[dict[str, object]] | None = None,
    target_index: int = 0,
    family_id: str | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "example_id": example_id,
        "policy_version": "draft",
        "source": "synthetic",
        "domain": "test_domain",
        "difficulty": "hard",
        "platform_hint": "minecraft",
        "messages": messages or [{"speaker": "A", "offset_ms": 0, "text": text}],
        "target_index": target_index,
        "label": label,
        "action": action,
        "reason_codes": ["insufficient_context"],
        "notes": "Synthetic QA fixture; not policy-authoritative.",
    }
    if family_id is not None:
        value["family_id"] = family_id
    return value


def _write(path: Path, *records: object) -> None:
    lines = [item if isinstance(item, str) else json.dumps(item) for item in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run(path: Path, range_spec: str = "none"):
    config = load_config(Path(__file__).parents[1] / "tools/dataset_qa/config.json")
    return analyze_records(load_and_validate(path, config, range_spec), config)


def _codes(result) -> set[str]:
    return {item.code for item in result.diagnostics}


def test_malformed_json_reports_file_and_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    _write(path, '{"example_id":')
    result = _run(path)
    assert "invalid_json" in _codes(result)
    assert result.diagnostics[0].line == 1


def test_invalid_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "schema.jsonl"
    value = _record("G01-0001")
    del value["messages"]
    _write(path, value)
    result = _run(path)
    assert "missing_field" in _codes(result)


def test_duplicate_and_missing_ids_are_detected(tmp_path: Path) -> None:
    path = tmp_path / "G01-fixture.jsonl"
    _write(path, _record("G01-0001", text="one"), _record("G01-0001", text="two"))
    result = _run(path, "G01:1-3")
    assert "duplicate_id" in _codes(result)
    assert "missing_ids" in _codes(result)


def test_missing_id_helper_uses_four_digit_format(tmp_path: Path) -> None:
    path = tmp_path / "fixture.jsonl"
    _write(path, _record("G01-0001"))
    config = load_config(Path(__file__).parents[1] / "tools/dataset_qa/config.json")
    raw = load_and_validate(path, config, "none")
    diagnostics = _missing_id_diagnostics(raw.records, ExpectedRange("G01", 1, 2))
    assert "G01-0002" in diagnostics[0].message


def test_exact_duplicate_sequence_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "duplicates.jsonl"
    _write(path, _record("G01-0001"), _record("G01-0002"))
    result = _run(path)
    assert result.exact_duplicate_groups == [["G01-0001", "G01-0002"]]
    assert "exact_duplicate" in _codes(result)


def test_valid_minimal_pair_is_candidate_not_exact_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "minimal.jsonl"
    _write(
        path,
        _record("G01-0001", text="meet me at gate number one", label="SAFE", action="ALLOW"),
        _record(
            "G01-0002",
            text="meet me at gate number two",
            label="AMBIGUOUS_REVIEW",
            action="REVIEW",
        ),
    )
    result = _run(path)
    assert result.exact_duplicate_groups == []
    assert result.near_duplicate_candidates[0]["kind"] == "minimal_pair_candidate"
    assert "exact_contradiction" not in _codes(result)


def test_exact_contradictory_label_and_action_are_flagged(tmp_path: Path) -> None:
    path = tmp_path / "contradiction.jsonl"
    _write(
        path,
        _record("G01-0001", label="SAFE", action="ALLOW"),
        _record("G01-0002", label="AMBIGUOUS_REVIEW", action="REVIEW"),
    )
    result = _run(path)
    assert "exact_contradiction" in _codes(result)


def test_multi_message_normalization_handles_case_and_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "multi.jsonl"
    left = [
        {"speaker": "A", "offset_ms": -1000, "text": "Hello   There"},
        {"speaker": "A", "offset_ms": 0, "text": "GENERAL KENOBI"},
    ]
    right = [
        {"speaker": "a", "offset_ms": -1000, "text": " hello there "},
        {"speaker": "a", "offset_ms": 0, "text": "general kenobi"},
    ]
    _write(
        path,
        _record("G01-0001", messages=left, target_index=1),
        _record("G01-0002", messages=right, target_index=1),
    )
    result = _run(path)
    assert result.exact_duplicate_groups == [["G01-0001", "G01-0002"]]


def test_different_speakers_and_message_boundaries_remain_distinct(tmp_path: Path) -> None:
    path = tmp_path / "structure.jsonl"
    one = [{"speaker": "A", "offset_ms": 0, "text": "alpha beta"}]
    two = [{"speaker": "B", "offset_ms": 0, "text": "alpha beta"}]
    split = [
        {"speaker": "A", "offset_ms": -1, "text": "alpha"},
        {"speaker": "A", "offset_ms": 0, "text": "beta"},
    ]
    _write(
        path,
        _record("G01-0001", messages=one),
        _record("G01-0002", messages=two),
        _record("G01-0003", messages=split, target_index=1),
    )
    result = _run(path)
    assert result.exact_duplicate_groups == []
    assert result.near_duplicate_candidates == []


def test_obfuscated_spacing_remains_distinct(tmp_path: Path) -> None:
    path = tmp_path / "obfuscated.jsonl"
    _write(path, _record("G01-0001", text="kys"), _record("G01-0002", text="k y s"))
    result = _run(path)
    assert result.exact_duplicate_groups == []


def test_invalid_family_id_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "family.jsonl"
    _write(path, _record("G01-0001", family_id="bad family id"))
    result = _run(path)
    assert "invalid_family_id" in _codes(result)


def test_report_output_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "report.jsonl"
    _write(
        path,
        _record("G01-0001", text="one"),
        _record("G01-0002", text="two", family_id="pair.alpha"),
    )
    first = json.dumps(build_report(_run(path)), sort_keys=True)
    second = json.dumps(build_report(_run(path)), sort_keys=True)
    assert first == second


def test_wrong_prefix_out_of_range_and_zero_padding_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "id-errors.jsonl"
    _write(
        path,
        _record("G02-0001", text="wrong prefix"),
        _record("G01-0501", text="out of range"),
        _record("G01-01", text="bad padding"),
    )
    result = _run(path, "G01:1-500")
    assert "wrong_id_prefix" in _codes(result)
    assert "id_out_of_range" in _codes(result)
    assert "malformed_example_id" in _codes(result)


def test_very_close_reason_code_conflict_is_flagged(tmp_path: Path) -> None:
    path = tmp_path / "near-reason.jsonl"
    left = _record("G01-0001", text="a" * 120 + "1")
    right = _record("G01-0002", text="a" * 120 + "2")
    right["reason_codes"] = ["low_severity_insult"]
    _write(path, left, right)
    result = _run(path)
    assert "near_reason_code_conflict" in _codes(result)


def test_markdown_report_lists_review_candidates(tmp_path: Path) -> None:
    from tools.dataset_qa import render_markdown_report

    path = tmp_path / "markdown.jsonl"
    _write(
        path,
        _record("G01-0001", text="meet me at gate number one"),
        _record("G01-0002", text="meet me at gate number two"),
    )
    markdown = render_markdown_report(build_report(_run(path)))
    assert "Near/minimal-pair candidates" in markdown
    assert "G01-0001" in markdown
    assert "G01-0002" in markdown


def test_unicode_line_separator_inside_json_string_is_not_split(tmp_path: Path) -> None:
    path = tmp_path / "unicode-separator.jsonl"
    value = _record("G01-0001", text="alpha\u2028beta")
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
    result = _run(path)
    assert "invalid_json" not in _codes(result)
    messages = result.records[0].data["messages"]
    assert messages[0]["text"] == "alpha\u2028beta"
