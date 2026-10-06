from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from .privacy import redact_text, stable_hash
from .store import MiningStore

_REQUIRED_ADJUDICATION = (
    "policy_version",
    "domain",
    "difficulty",
    "label",
    "action",
    "review_priority",
    "strike",
    "containment",
    "containment_duration_seconds",
    "support_flow",
    "reason_codes",
    "notes",
)
_SPEAKER_RE = re.compile(r"^user_[0-9a-f]{12}$")


def _model_scores(store: MiningStore, message_id: str) -> list[dict[str, object]]:
    return [
        {
            "model": str(row["model"]),
            "action": str(row["action"]),
            "block_confidence": float(row["block_confidence"]),
        }
        for row in store.scores(message_id)
    ]


def _context(
    store: MiningStore,
    row: sqlite3.Row,
    limit: int,
    window_ms: int,
) -> list[dict[str, object]]:
    target_ms = int(row["relative_ms"])
    context = store.context_rows(str(row["channel"]), target_ms, limit, window_ms)
    return [
        {
            "message_id": str(item["message_id"]),
            "speaker": str(item["sender_id"]),
            "offset_ms": int(item["relative_ms"]) - target_ms,
            "text": str(item["text"]),
        }
        for item in context
    ]


def _split_group_id(store: MiningStore, row: sqlite3.Row) -> str:
    node = "s:" + str(row["session_id"])
    seen: set[str] = set()
    parent: sqlite3.Row | None = None
    while node not in seen:
        seen.add(node)
        parent = store.connection.execute(
            "SELECT parent FROM dsu WHERE node=?",
            (node,),
        ).fetchone()
        if parent is None or str(parent["parent"]) == node:
            break
        node = str(parent["parent"])
    if len(seen) == 1 and parent is None:
        node = str(row["session_id"]) + "\x1f" + str(row["family_key"])
    return "group_" + stable_hash(node)[:20]


def _candidate_groups(store: MiningStore) -> Iterator[tuple[sqlite3.Row, list[str], float]]:
    query = """
    SELECT m.*, MAX(c.priority) AS priority, GROUP_CONCAT(c.bucket) AS buckets
    FROM candidates c JOIN messages m ON m.message_id=c.message_id
    GROUP BY m.message_id ORDER BY priority DESC,m.relative_ms,m.message_id
    """
    for row in store.connection.execute(query):
        buckets = sorted(set(str(row["buckets"]).split(",")))
        yield row, buckets, float(row["priority"])


def write_review_queue(
    store: MiningStore,
    path: Path,
    context_limit: int = 5,
    context_window_ms: int = 120_000,
) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row, buckets, priority in _candidate_groups(store):
            payload = {
                "review_id": "review_" + str(row["message_id"]),
                "message_id": str(row["message_id"]),
                "partition": str(row["partition_name"]),
                "group_id": _split_group_id(store, row),
                "relative_ms": int(row["relative_ms"]),
                "chronology_bucket": f"day_{int(row['relative_ms']) // 86_400_000:+07d}",
                "buckets": buckets,
                "priority": priority,
                "platform_hint": str(row["platform"]),
                "channel_profile": str(row["channel_profile"]),
                "messages": _context(store, row, context_limit, context_window_ms),
                "target_message_id": str(row["message_id"]),
                "model_decisions": _model_scores(store, str(row["message_id"])),
                "adjudication": {field: None for field in _REQUIRED_ADJUDICATION},
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            count += 1
    return count


def _schema_vocabulary() -> dict[str, set[str]]:
    config_path = Path(__file__).parents[1] / "dataset_qa" / "config.json"
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "labels": set(raw["labels"]),
        "actions": set(raw["actions"]),
        "review_priorities": set(raw["review_priorities"]),
        "containments": set(raw["containments"]),
        "support_flows": set(raw["support_flows"]),
        "channel_profiles": set(raw["channel_profiles"]),
        "reason_codes": set(raw["reason_codes"]),
    }


def _validate_enum(
    adjudication: dict[str, object],
    field: str,
    allowed: set[str],
    line_no: int,
) -> None:
    value = adjudication[field]
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"line {line_no}: invalid {field}")


def _validate_adjudication(value: dict[str, object], line_no: int) -> dict[str, object]:
    adjudication = value.get("adjudication")
    if not isinstance(adjudication, dict):
        raise ValueError(f"line {line_no}: adjudication must be an object")
    missing = [field for field in _REQUIRED_ADJUDICATION if field not in adjudication]
    if missing:
        raise ValueError(f"line {line_no}: adjudication missing {', '.join(missing)}")
    nullable = {"containment_duration_seconds"}
    incomplete = any(
        adjudication[field] is None
        for field in _REQUIRED_ADJUDICATION
        if field not in nullable
    )
    if incomplete:
        raise ValueError(f"line {line_no}: adjudication is incomplete")
    _validate_adjudication_values(adjudication, line_no)
    return adjudication


def _validate_adjudication_values(adjudication: dict[str, object], line_no: int) -> None:
    for field in ("policy_version", "domain", "difficulty", "notes"):
        value = adjudication[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"line {line_no}: {field} must be a non-empty string")
    if adjudication["policy_version"] != "v1":
        raise ValueError(f"line {line_no}: unsupported policy_version")
    vocabulary = _schema_vocabulary()
    fields = {
        "label": "labels",
        "action": "actions",
        "review_priority": "review_priorities",
        "containment": "containments",
        "support_flow": "support_flows",
    }
    for field, vocabulary_key in fields.items():
        _validate_enum(adjudication, field, vocabulary[vocabulary_key], line_no)
    if not isinstance(adjudication["strike"], bool):
        raise ValueError(f"line {line_no}: strike must be boolean")
    _validate_duration(adjudication, line_no)
    _validate_reason_codes(adjudication, vocabulary["reason_codes"], line_no)


def _validate_duration(adjudication: dict[str, object], line_no: int) -> None:
    duration = adjudication["containment_duration_seconds"]
    containment = adjudication["containment"]
    valid_int = isinstance(duration, int) and not isinstance(duration, bool) and duration > 0
    if duration is not None and not valid_int:
        raise ValueError(f"line {line_no}: invalid containment duration")
    if containment == "NONE" and duration is not None:
        raise ValueError(f"line {line_no}: NONE containment requires null duration")


def _validate_reason_codes(
    adjudication: dict[str, object],
    allowed: set[str],
    line_no: int,
) -> None:
    reason_codes = adjudication["reason_codes"]
    if not isinstance(reason_codes, list):
        raise ValueError(f"line {line_no}: reason_codes must be a string list")
    for item in reason_codes:
        if not isinstance(item, str):
            raise ValueError(f"line {line_no}: reason_codes must be a string list")
        if item not in allowed:
            raise ValueError(f"line {line_no}: unknown reason code")


def _messages_for_export(
    value: dict[str, object], line_no: int
) -> tuple[list[dict[str, object]], int]:
    raw_messages = value.get("messages")
    target_id = value.get("target_message_id")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError(f"line {line_no}: messages must be a non-empty list")
    messages: list[dict[str, object]] = []
    target_index = -1
    for index, item in enumerate(raw_messages):
        message, is_target = _export_message(item, target_id, line_no)
        messages.append(message)
        if is_target:
            target_index = index
    if target_index < 0:
        raise ValueError(f"line {line_no}: target message not present in context")
    return messages, target_index


def _export_message(
    item: object,
    target_id: object,
    line_no: int,
) -> tuple[dict[str, object], bool]:
    if not isinstance(item, dict):
        raise ValueError(f"line {line_no}: invalid context message")
    speaker = item.get("speaker")
    if not isinstance(speaker, str) or not _SPEAKER_RE.fullmatch(speaker):
        raise ValueError(f"line {line_no}: context speaker is not pseudonymized")
    offset = item.get("offset_ms")
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise ValueError(f"line {line_no}: context offset_ms must be an integer")
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"line {line_no}: context text must be non-empty")
    message = {
        "speaker": speaker,
        "offset_ms": offset,
        "text": redact_text(text),
    }
    return message, item.get("message_id") == target_id


def _export_record(value: dict[str, object], line_no: int) -> dict[str, object]:
    adjudication = _validate_adjudication(value, line_no)
    messages, target_index = _messages_for_export(value, line_no)
    vocabulary = _schema_vocabulary()
    channel_profile = value.get("channel_profile")
    if channel_profile not in vocabulary["channel_profiles"]:
        raise ValueError(f"line {line_no}: invalid channel_profile")
    platform_hint = value.get("platform_hint")
    if not isinstance(platform_hint, str) or not platform_hint.strip():
        raise ValueError(f"line {line_no}: invalid platform_hint")
    message_id = str(value.get("message_id", ""))
    group_id = value.get("group_id")
    if not isinstance(group_id, str) or not re.fullmatch(r"group_[0-9a-f]{20}", group_id):
        raise ValueError(f"line {line_no}: missing or invalid split group_id")
    return {
        "example_id": "RCH-" + message_id.removeprefix("msg_"),
        "policy_version": adjudication["policy_version"],
        "source": "production_reviewed_redacted",
        "domain": adjudication["domain"],
        "difficulty": adjudication["difficulty"],
        "platform_hint": platform_hint,
        "channel_profile": channel_profile,
        "messages": messages,
        "target_index": target_index,
        "label": adjudication["label"],
        "action": adjudication["action"],
        "review_priority": adjudication["review_priority"],
        "strike": adjudication["strike"],
        "containment": adjudication["containment"],
        "containment_duration_seconds": adjudication["containment_duration_seconds"],
        "support_flow": adjudication["support_flow"],
        "reason_codes": adjudication["reason_codes"],
        "notes": adjudication["notes"],
        "family_id": "real." + group_id.removeprefix("group_"),
    }


def _write_reviewed(review_path: Path, output_path: Path) -> int:
    count = 0
    seen: set[str] = set()
    with review_path.open("r", encoding="utf-8") as source, output_path.open(
        "w", encoding="utf-8"
    ) as output:
        for line_no, line in enumerate(source, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_no}: review record must be an object")
            record = _export_record(value, line_no)
            example_id = str(record["example_id"])
            if example_id in seen:
                continue
            seen.add(example_id)
            output.write(json.dumps(record, sort_keys=True) + "\n")
            count += 1
    return count


def export_reviewed(review_path: Path, output_path: Path) -> int:
    temporary = output_path.with_name(output_path.name + ".tmp")
    try:
        count = _write_reviewed(review_path, temporary)
        temporary.replace(output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return count


def review_bucket_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            for bucket in value.get("buckets", []):
                counts[str(bucket)] += 1
    return dict(sorted(counts.items()))
