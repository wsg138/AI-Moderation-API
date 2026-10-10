"""Read-only aggregate diagnostics from the canonical private moderation database.

Never returns raw messages, event/player IDs, reviewer IDs, conversation IDs,
incident text, or individual scores. Corrections are biased feedback, NOT gold.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

MAX_EVENTS = 500_000
MIN_GROUP = 10
SAFE_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,100}\Z")


def _day(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def _public_tag(value: object) -> str:
    if isinstance(value, str) and SAFE_TOKEN.fullmatch(value):
        return value
    return "REDACTED_UNKNOWN"


def _quantile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def _row_result(row: sqlite3.Row) -> dict[str, object]:
    return {
        "day": _public_tag(row["day"]),
        "model": _public_tag(row["local_model_version"]),
        "policy": _public_tag(row["policy_version"]),
        "channel": _public_tag(row["channel_profile"]),
        "action": _public_tag(row["message_action"]),
        "label": _public_tag(row["semantic_label"]),
        "ingestion": _public_tag(row["ingestion_status"]),
        "degraded": bool(row["degraded"]),
        "review": row["review_priority"] != "NONE",
        "strike_proposed": row["strike_recommendation"] == "STRIKE",
        "mute_proposed": row["containment"] == "MUTE",
        "corrected": bool(row["corrected"]),
        "latency_ms": row["latency_ms"],
    }


def _update_count(counts: Counter[str], item: dict[str, object]) -> None:
    counts["finalized"] += 1
    for field, trigger in (
        ("blocked", item["action"] == "BLOCK"),
        ("review", item["review"]),
        ("degraded", item["degraded"]),
        ("fail_open", item["ingestion"] == "FAIL_OPEN"),
        ("strike_proposals", item["strike_proposed"]),
        ("mute_proposals", item["mute_proposed"]),
        ("accepted_corrections", item["corrected"]),
    ):
        counts[field] += int(bool(trigger))


def _safe_counts(counts: Counter[str], *, min_group: int) -> dict[str, int] | None:
    return dict(counts) if counts["finalized"] >= min_group else None


def _rollup(
    per_group: dict[tuple[str, ...], Counter[str]], *, minimum: int,
) -> dict[str, dict[str, int]]:
    return {
        "/".join(key): dict(counts)
        for key, counts in sorted(per_group.items())
        if _safe_counts(counts, min_group=minimum) is not None
    }


def _aggregate_rows(rows: Any, *, minimum: int) -> dict[str, object]:
    total: Counter[str] = Counter()
    model: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    channel: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    per_day: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    by_label: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    latencies: list[int] = []
    for index, raw in enumerate(rows):
        if index >= MAX_EVENTS:
            raise ValueError("Event cap exceeded; split the aggregate query by date")
        item = _row_result(raw)
        _update_count(total, item)
        _update_count(model[(str(item["model"]), str(item["policy"]))], item)
        _update_count(channel[(str(item["channel"]),)], item)
        _update_count(per_day[(str(item["day"]),)], item)
        _update_count(by_label[(str(item["label"]),)], item)
        value = item["latency_ms"]
        if type(value) is int and value >= 0:
            latencies.append(value)
    return {
        "total": dict(total),
        "per_model_policy": _rollup(model, minimum=minimum),
        "per_channel": _rollup(channel, minimum=minimum),
        "per_day": _rollup(per_day, minimum=minimum),
        "per_semantic_label": _rollup(by_label, minimum=minimum),
        "latency_ms": {
            "sample_count": len(latencies),
            "p50": _quantile(latencies, 0.50),
            "p95": _quantile(latencies, 0.95),
            "p99": _quantile(latencies, 0.99),
        },
        "suppressed_small_group_threshold": minimum,
    }


def _read_rows(path: Path, start: str, end: str) -> dict[str, object]:
    if not path.is_file():
        raise ValueError("A local private SQLite database file is required")
    # URI read-only mode plus PRAGMA query_only: no migrations, no writes.
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        rows = db.execute(
            """SELECT substr(e.finalized_at, 1, 10) AS day,
                      e.channel_profile, e.degraded,
                      d.local_model_version, d.policy_version,
                      d.message_action, d.semantic_label,
                      d.ingestion_status, d.review_priority,
                      d.strike_recommendation, d.containment,
                      d.latency_ms,
                      (ac.event_id IS NOT NULL) AS corrected
               FROM moderation_events AS e
               JOIN decision_evidence AS d ON e.event_id=d.event_id
               LEFT JOIN accepted_corrections AS ac ON e.event_id=ac.event_id
               WHERE e.status='FINAL'
                 AND e.finalized_at >= ?
                 AND e.finalized_at < ?
               ORDER BY e.finalized_at, e.event_id""",
            (start + "T00:00:00", end + "T00:00:00"),
        )
        return _aggregate_rows(rows, minimum=MIN_GROUP)


def report(path: Path, start: str, end: str) -> dict[str, object]:
    after, before = _day(start), _day(end)
    if after >= before:
        raise ValueError("End date must be later than start date")
    counts = _read_rows(path, after, before)
    return {
        "schema_version": "private-runtime-aggregates/1",
        "date_start_inclusive": after,
        "date_end_exclusive": before,
        "no_raw_messages_or_user_ids": True,
        "source": "canonical_durable_FINAL_events_only",
        "not_a_model_accuracy_certificate": True,
        "accepted_corrections_are_biased_not_independently_adjudicated_truth": True,
        "client_side_timeouts_and_pre_persistence_losses_not_counted": True,
        **counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Private read-only moderation diagnostics")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--from-day", required=True)
    parser.add_argument("--until-day", required=True, help="Exclusive UTC date")
    args = parser.parse_args()
    try:
        result = report(args.database, args.from_day, args.until_day)
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        parser.error("No analytics exported: " + type(exc).__name__)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
