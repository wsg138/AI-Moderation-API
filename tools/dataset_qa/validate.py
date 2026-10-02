from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .config import QaConfig
from .model import DatasetResult, Diagnostic, ExpectedRange, RecordRef

ID_PATTERN = re.compile(r"^(G\d{2})-(\d{4})$")
STRING_FIELDS = (
    "example_id",
    "policy_version",
    "source",
    "domain",
    "difficulty",
    "platform_hint",
    "notes",
)


def _diagnostic(
    path: Path,
    line: int | None,
    severity: str,
    code: str,
    message: str,
) -> Diagnostic:
    level = "error" if severity == "error" else "warning"
    return Diagnostic(str(path), line, level, code, message)


def _require_fields(record: RecordRef, config: QaConfig) -> list[Diagnostic]:
    missing = [field for field in config.required_fields if field not in record.data]
    return [
        _diagnostic(
            record.path,
            record.line,
            "error",
            "missing_field",
            f"missing required field '{field}'",
        )
        for field in missing
    ]


def _validate_string(record: RecordRef, field: str) -> list[Diagnostic]:
    value = record.data.get(field)
    if isinstance(value, str) and value.strip():
        return []
    message = f"'{field}' must be a non-empty string"
    return [_diagnostic(record.path, record.line, "error", "invalid_type", message)]


def _validate_enum(
    record: RecordRef,
    field: str,
    allowed: frozenset[str],
) -> list[Diagnostic]:
    value = record.data.get(field)
    if not isinstance(value, str):
        message = f"'{field}' must be a string"
        return [_diagnostic(record.path, record.line, "error", "invalid_type", message)]
    if value in allowed:
        return []
    message = f"unknown {field} value '{value}'"
    return [_diagnostic(record.path, record.line, "error", "unknown_value", message)]


def _invalid_string_field(
    record: RecordRef,
    index: int,
    value: dict[str, Any],
    field: str,
    code: str,
) -> list[Diagnostic]:
    item = value.get(field)
    if field not in value:
        return []
    if isinstance(item, str) and item.strip():
        return []
    message = f"messages[{index}].{field} must be a non-empty string"
    return [_diagnostic(record.path, record.line, "error", code, message)]


def _invalid_offset_field(
    record: RecordRef,
    index: int,
    value: dict[str, Any],
) -> list[Diagnostic]:
    offset = value.get("offset_ms")
    if "offset_ms" not in value:
        return []
    if isinstance(offset, int) and not isinstance(offset, bool):
        return []
    message = f"messages[{index}].offset_ms must be an integer"
    return [
        _diagnostic(
            record.path,
            record.line,
            "error",
            "invalid_message_offset",
            message,
        )
    ]


def _message_field_diagnostics(
    record: RecordRef,
    index: int,
    value: dict[str, Any],
) -> list[Diagnostic]:
    diagnostics = _invalid_string_field(
        record,
        index,
        value,
        "speaker",
        "invalid_message_speaker",
    )
    diagnostics.extend(_invalid_offset_field(record, index, value))
    diagnostics.extend(
        _invalid_string_field(record, index, value, "text", "invalid_message_text")
    )
    return diagnostics


def _validate_message(
    record: RecordRef,
    index: int,
    value: object,
    config: QaConfig,
) -> list[Diagnostic]:
    if not isinstance(value, dict):
        message = f"messages[{index}] must be an object"
        return [
            _diagnostic(record.path, record.line, "error", "invalid_message", message)
        ]
    diagnostics: list[Diagnostic] = []
    for field in config.message_required_fields:
        if field not in value:
            message = f"messages[{index}] missing '{field}'"
            diagnostics.append(
                _diagnostic(
                    record.path,
                    record.line,
                    "error",
                    "missing_message_field",
                    message,
                )
            )
    diagnostics.extend(_message_field_diagnostics(record, index, value))
    return diagnostics


def _target_index_diagnostics(
    record: RecordRef,
    message_count: int,
) -> list[Diagnostic]:
    target_index = record.data.get("target_index")
    if not isinstance(target_index, int) or isinstance(target_index, bool):
        message = "'target_index' must be an integer"
        return [
            _diagnostic(
                record.path,
                record.line,
                "error",
                "invalid_target_index",
                message,
            )
        ]
    if 0 <= target_index < message_count:
        return []
    message = "'target_index' is outside the messages array"
    return [
        _diagnostic(
            record.path,
            record.line,
            "error",
            "invalid_target_index",
            message,
        )
    ]


def _validate_messages(record: RecordRef, config: QaConfig) -> list[Diagnostic]:
    messages = record.data.get("messages")
    if not isinstance(messages, list) or not messages:
        message = "'messages' must be a non-empty array"
        return [
            _diagnostic(record.path, record.line, "error", "invalid_messages", message)
        ]
    diagnostics: list[Diagnostic] = []
    for index, message in enumerate(messages):
        diagnostics.extend(_validate_message(record, index, message, config))
    diagnostics.extend(_target_index_diagnostics(record, len(messages)))
    return diagnostics


def _validate_reason_codes(record: RecordRef, config: QaConfig) -> list[Diagnostic]:
    values = record.data.get("reason_codes")
    if not isinstance(values, list) or any(
        not isinstance(item, str) for item in values
    ):
        message = "'reason_codes' must be an array of strings"
        return [
            _diagnostic(
                record.path,
                record.line,
                "error",
                "invalid_reason_codes",
                message,
            )
        ]
    diagnostics: list[Diagnostic] = []
    if not values:
        diagnostics.append(
            _diagnostic(
                record.path,
                record.line,
                "warning",
                "empty_reason_codes",
                "reason_codes is empty",
            )
        )
    for value in values:
        if value not in config.reason_codes:
            message = f"unknown reason code '{value}'"
            diagnostics.append(
                _diagnostic(
                    record.path,
                    record.line,
                    "error",
                    "unknown_reason_code",
                    message,
                )
            )
    if len(values) != len(set(values)):
        diagnostics.append(
            _diagnostic(
                record.path,
                record.line,
                "warning",
                "duplicate_reason_code",
                "reason_codes contains duplicates",
            )
        )
    return diagnostics


def _validate_family_id(record: RecordRef, config: QaConfig) -> list[Diagnostic]:
    if "family_id" not in record.data:
        return []
    value = record.data["family_id"]
    if isinstance(value, str) and re.fullmatch(config.family_id_pattern, value):
        return []
    message = "family_id does not match the configured format"
    return [
        _diagnostic(record.path, record.line, "error", "invalid_family_id", message)
    ]


def _validate_schema(record: RecordRef, config: QaConfig) -> list[Diagnostic]:
    diagnostics = _require_fields(record, config)
    for field in STRING_FIELDS:
        if field in record.data:
            diagnostics.extend(_validate_string(record, field))
    if "label" in record.data:
        diagnostics.extend(_validate_enum(record, "label", config.labels))
    if "action" in record.data:
        diagnostics.extend(_validate_enum(record, "action", config.actions))
    if "messages" in record.data or "target_index" in record.data:
        diagnostics.extend(_validate_messages(record, config))
    if "reason_codes" in record.data:
        diagnostics.extend(_validate_reason_codes(record, config))
    diagnostics.extend(_validate_family_id(record, config))
    return diagnostics


def _parse_line(
    path: Path,
    line_number: int,
    text: str,
) -> tuple[RecordRef | None, list[Diagnostic]]:
    if not text.strip():
        message = "blank lines are not valid JSONL records"
        return None, [
            _diagnostic(path, line_number, "error", "blank_line", message)
        ]
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        message = f"invalid JSON: {exc.msg} at column {exc.colno}"
        return None, [
            _diagnostic(path, line_number, "error", "invalid_json", message)
        ]
    if not isinstance(value, dict):
        message = "each JSONL line must contain an object"
        return None, [
            _diagnostic(path, line_number, "error", "invalid_record", message)
        ]
    return RecordRef(path=path, line=line_number, data=value), []


def _explicit_range(range_spec: str) -> ExpectedRange:
    prefix, values = range_spec.split(":", maxsplit=1)
    start_text, end_text = values.split("-", maxsplit=1)
    return ExpectedRange(prefix=prefix, start=int(start_text), end=int(end_text))


def _record_prefixes(records: list[RecordRef]) -> set[str]:
    prefixes: set[str] = set()
    for record in records:
        value = str(record.data.get("example_id", ""))
        match = ID_PATTERN.fullmatch(value)
        if match is not None:
            prefixes.add(match.group(1))
    return prefixes


def _resolve_range(
    path: Path,
    records: list[RecordRef],
    config: QaConfig,
    range_spec: str,
) -> ExpectedRange | None:
    if range_spec == "none":
        return None
    if range_spec != "auto":
        return _explicit_range(range_spec)
    filename_match = re.match(r"^(G\d{2})[-_]", path.name)
    if filename_match and filename_match.group(1) in config.id_ranges:
        return config.id_ranges[filename_match.group(1)]
    prefixes = _record_prefixes(records)
    if len(prefixes) == 1:
        return config.id_ranges.get(next(iter(prefixes)))
    return None


def _validate_one_id(
    record: RecordRef,
    value: str,
    expected: ExpectedRange | None,
    config: QaConfig,
) -> list[Diagnostic]:
    match = ID_PATTERN.fullmatch(value)
    if match is None:
        message = f"example_id '{value}' must use GNN-NNNN format"
        return [
            _diagnostic(
                record.path,
                record.line,
                "error",
                "malformed_example_id",
                message,
            )
        ]
    prefix, number_text = match.groups()
    diagnostics: list[Diagnostic] = []
    if prefix not in config.id_ranges:
        message = f"unknown example_id prefix '{prefix}'"
        diagnostics.append(
            _diagnostic(
                record.path,
                record.line,
                "error",
                "unknown_id_prefix",
                message,
            )
        )
    if expected is not None:
        diagnostics.extend(
            _validate_id_against_range(record, prefix, int(number_text), expected)
        )
    return diagnostics


def _validate_ids(
    records: list[RecordRef],
    expected: ExpectedRange | None,
    config: QaConfig,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    values = [record.data.get("example_id") for record in records]
    counts = Counter(value for value in values if isinstance(value, str))
    for record in records:
        value = record.data.get("example_id")
        if not isinstance(value, str):
            continue
        if counts[value] > 1:
            message = f"duplicate example_id '{value}'"
            diagnostics.append(
                _diagnostic(
                    record.path,
                    record.line,
                    "error",
                    "duplicate_id",
                    message,
                )
            )
        diagnostics.extend(_validate_one_id(record, value, expected, config))
    diagnostics.extend(_missing_id_diagnostics(records, expected))
    return diagnostics


def _validate_id_against_range(
    record: RecordRef,
    prefix: str,
    number: int,
    expected: ExpectedRange,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if prefix != expected.prefix:
        message = f"expected prefix {expected.prefix}, found {prefix}"
        diagnostics.append(
            _diagnostic(record.path, record.line, "error", "wrong_id_prefix", message)
        )
    if number < expected.start or number > expected.end:
        message = f"ID number {number} outside {expected.start}-{expected.end}"
        diagnostics.append(
            _diagnostic(record.path, record.line, "error", "id_out_of_range", message)
        )
    return diagnostics


def _missing_id_diagnostics(
    records: list[RecordRef],
    expected: ExpectedRange | None,
) -> list[Diagnostic]:
    if expected is None:
        return []
    present = {str(record.data.get("example_id")) for record in records}
    missing = sorted(expected.expected_ids() - present)
    if not missing:
        return []
    preview = ", ".join(missing[:10])
    suffix = " ..." if len(missing) > 10 else ""
    message = (
        f"missing {len(missing)} IDs from {expected.prefix}:"
        f"{expected.start}-{expected.end}: {preview}{suffix}"
    )
    path = records[0].path if records else Path("<dataset>")
    return [_diagnostic(path, None, "error", "missing_ids", message)]


def load_and_validate(
    path: Path,
    config: QaConfig,
    range_spec: str = "auto",
) -> DatasetResult:
    records: list[RecordRef] = []
    diagnostics: list[Diagnostic] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            text = raw_line.removesuffix("\n")
            record, line_diagnostics = _parse_line(path, line_number, text)
            diagnostics.extend(line_diagnostics)
            if record is not None:
                records.append(record)
                diagnostics.extend(_validate_schema(record, config))
    expected = _resolve_range(path, records, config, range_spec)
    diagnostics.extend(_validate_ids(records, expected, config))
    diagnostics.sort(key=Diagnostic.sort_key)
    return DatasetResult(path=path, records=records, diagnostics=diagnostics)
