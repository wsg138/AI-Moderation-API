from __future__ import annotations

from collections import Counter

from .model import DatasetResult, RecordRef

COUNT_FIELDS = (
    "source",
    "domain",
    "difficulty",
    "platform_hint",
    "channel_profile",
    "label",
    "action",
    "review_priority",
    "containment",
    "support_flow",
)


def _sorted_counts(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _field_counts(records: list[RecordRef], field: str) -> dict[str, int]:
    values = [
        value
        for record in records
        if isinstance((value := record.data.get(field)), str)
    ]
    return _sorted_counts(values)


def _bool_counts(records: list[RecordRef], field: str) -> dict[str, int]:
    values = [
        str(value).lower()
        for record in records
        if isinstance((value := record.data.get(field)), bool)
    ]
    return _sorted_counts(values)


def _message_counts(records: list[RecordRef]) -> tuple[dict[str, int], int]:
    counts: list[str] = []
    multi_message = 0
    for record in records:
        messages = record.data.get("messages")
        if not isinstance(messages, list):
            continue
        counts.append(str(len(messages)))
        if len(messages) > 1:
            multi_message += 1
    return _sorted_counts(counts), multi_message


def _reason_counts(records: list[RecordRef]) -> dict[str, int]:
    values: list[str] = []
    for record in records:
        reason_codes = record.data.get("reason_codes")
        if isinstance(reason_codes, list):
            values.extend(item for item in reason_codes if isinstance(item, str))
    return _sorted_counts(values)


def _family_counts(records: list[RecordRef]) -> dict[str, int]:
    values = [
        value
        for record in records
        if isinstance((value := record.data.get("family_id")), str)
    ]
    return _sorted_counts(values)


def _duration_bucket(record: RecordRef) -> tuple[str, str | None]:
    if "containment_duration_seconds" not in record.data:
        return "missing", None
    duration = record.data.get("containment_duration_seconds")
    containment = record.data.get("containment")
    if duration is None:
        mute_bucket = "mute_without_duration" if containment == "MUTE" else None
        return "null", mute_bucket
    if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0:
        mute_bucket = "mute_with_duration" if containment == "MUTE" else None
        return "concrete", mute_bucket
    return "invalid", None


def _duration_coverage(records: list[RecordRef]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        primary, mute_bucket = _duration_bucket(record)
        counts[primary] += 1
        if mute_bucket is not None:
            counts[mute_bucket] += 1
    return dict(sorted(counts.items()))


def _diagnostic_counts(result: DatasetResult) -> dict[str, object]:
    by_code = Counter(item.code for item in result.diagnostics)
    return {
        "errors": len(result.errors()),
        "warnings": len(result.warnings()),
        "by_code": dict(sorted(by_code.items())),
    }


def _duplicate_counts(result: DatasetResult) -> dict[str, int]:
    exact_records = sum(len(group) for group in result.exact_duplicate_groups)
    minimal_pairs = sum(
        item.get("kind") == "minimal_pair_candidate"
        for item in result.near_duplicate_candidates
    )
    return {
        "exact_group_count": len(result.exact_duplicate_groups),
        "exact_record_count": exact_records,
        "near_candidate_count": len(result.near_duplicate_candidates),
        "minimal_pair_candidate_count": minimal_pairs,
    }


def build_report(result: DatasetResult) -> dict[str, object]:
    message_distribution, multi_message = _message_counts(result.records)
    denominator = len(result.records)
    fields = {field: _field_counts(result.records, field) for field in COUNT_FIELDS}
    return {
        "path": str(result.path),
        "records": denominator,
        "fields": fields,
        "strike": _bool_counts(result.records, "strike"),
        "containment_duration": _duration_coverage(result.records),
        "messages": {
            "count_distribution": message_distribution,
            "multi_message_records": multi_message,
            "multi_message_proportion": (
                round(multi_message / denominator, 6) if denominator else 0.0
            ),
        },
        "reason_codes": _reason_counts(result.records),
        "family_ids": _family_counts(result.records),
        "diagnostics": _diagnostic_counts(result),
        "duplicates": _duplicate_counts(result),
        "exact_duplicate_groups": result.exact_duplicate_groups,
        "near_duplicate_candidates": result.near_duplicate_candidates,
        "family_suggestions": result.family_suggestions,
    }


def _table(title: str, values: dict[str, int]) -> list[str]:
    lines = [f"### {title}", "", "| Value | Count |", "|---|---:|"]
    if not values:
        return lines + ["| _(none)_ | 0 |", ""]
    lines.extend(f"| `{key}` | {value} |" for key, value in values.items())
    lines.append("")
    return lines


def _exact_group_lines(report: dict[str, object]) -> list[str]:
    lines = ["### Exact duplicate groups", ""]
    groups = report["exact_duplicate_groups"]
    if not groups:
        return lines + ["_(none)_", ""]
    lines.extend(f"- {', '.join(f'`{item}`' for item in group)}" for group in groups)
    lines.append("")
    return lines


def _near_candidate_lines(report: dict[str, object]) -> list[str]:
    lines = [
        "### Near/minimal-pair candidates",
        "",
        "| Left | Right | Similarity | Kind |",
        "|---|---|---:|---|",
    ]
    candidates = report["near_duplicate_candidates"]
    if not candidates:
        return lines + ["| _(none)_ |  |  |  |", ""]
    for item in candidates:
        lines.append(
            f"| `{item['left']}` | `{item['right']}` | {item['similarity']:.6f} | "
            f"`{item['kind']}` |"
        )
    lines.append("")
    return lines


def _family_suggestion_lines(report: dict[str, object]) -> list[str]:
    lines = ["### Family suggestions", ""]
    suggestions = report["family_suggestions"]
    if not suggestions:
        return lines + ["_(none)_", ""]
    for item in suggestions:
        ids = ", ".join(f"`{value}`" for value in item["example_ids"])
        lines.append(f"- `{item['suggested_family_id']}`: {ids}")
    lines.append("")
    return lines


def render_markdown_report(report: dict[str, object]) -> str:
    diagnostics = report["diagnostics"]
    messages = report["messages"]
    duplicates = report["duplicates"]
    lines = [
        "# Dataset QA report",
        "",
        f"- File: `{report['path']}`",
        f"- Records: **{report['records']}**",
        f"- Errors: **{diagnostics['errors']}**",
        f"- Warnings: **{diagnostics['warnings']}**",
        f"- Exact duplicate groups: **{duplicates['exact_group_count']}**",
        f"- Near candidates: **{duplicates['near_candidate_count']}**",
        f"- Minimal-pair candidates: **{duplicates['minimal_pair_candidate_count']}**",
        f"- Multi-message proportion: **{messages['multi_message_proportion']:.6f}**",
        "",
    ]
    for field, values in report["fields"].items():
        lines.extend(_table(field, values))
    lines.extend(_table("Strike", report["strike"]))
    lines.extend(_table("Containment duration coverage", report["containment_duration"]))
    lines.extend(_table("Reason codes", report["reason_codes"]))
    lines.extend(_table("Message count", messages["count_distribution"]))
    lines.extend(_table("Diagnostic codes", diagnostics["by_code"]))
    lines.extend(_exact_group_lines(report))
    lines.extend(_near_candidate_lines(report))
    lines.extend(_family_suggestion_lines(report))
    return "\n".join(lines).rstrip() + "\n"
