"""Only invented in-memory-equivalent SQLite fixtures; no owner/private messages."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tools.data_v2.runtime_analytics import report
from tools.data_v2.runtime_dashboard import render, write_dashboard


def _fixture(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE moderation_events(
              event_id TEXT PRIMARY KEY,
              status TEXT, finalized_at TEXT,
              channel_profile TEXT, degraded INTEGER,
              text TEXT, sender_id TEXT
            );
            CREATE TABLE decision_evidence(
              event_id TEXT PRIMARY KEY,
              local_model_version TEXT, policy_version TEXT,
              message_action TEXT, semantic_label TEXT,
              ingestion_status TEXT, review_priority TEXT,
              strike_recommendation TEXT, containment TEXT,
              containment_duration_seconds INTEGER, support_flow TEXT,
              latency_ms INTEGER
            );
            CREATE TABLE accepted_corrections(
              event_id TEXT PRIMARY KEY, proposal_id TEXT
            );
            CREATE TABLE correction_proposals(
              proposal_id TEXT PRIMARY KEY, corrected_json TEXT
            );
            """
        )
    with sqlite3.connect(path) as db:
        _seed_rows(db)


def _seed_rows(db: sqlite3.Connection) -> None:
    with db:
        for index in range(12):
            ident = "PRIVATE-SYNTHETIC-MESSAGE-" + str(index)
            db.execute(
                """INSERT INTO moderation_events
                   VALUES(?, 'FINAL', '2026-10-10T12:00:00',
                          'minecraft_public', ?, 'PRIVATE MESSAGE TEXT', 'SENSITIVE_ID')""",
                (ident, int(index == 11)),
            )
            db.execute(
                """INSERT INTO decision_evidence
                   VALUES(?, 'model-v1', 'policy-v1', ?, 'SAFE', ?, ?, ?, ?,
                          NULL, 'NONE', ?)""",
                (
                    ident,
                    "BLOCK" if index == 0 else "ALLOW",
                    "FAIL_OPEN" if index == 11 else "INGESTED",
                    "NORMAL" if index == 1 else "NONE",
                    "STRIKE" if index == 2 else "NONE",
                    "MUTE" if index == 3 else "NONE",
                    100 + index,
                ),
            )
        _seed_correction(db)
        db.execute(
            """INSERT INTO moderation_events
               VALUES('PENDING-SECRET', 'PENDING', '2026-10-10T12:00:00',
                      'discord_general', 0, 'SECRET', 'SENSITIVE_ID')"""
        )
        db.execute(
            """INSERT INTO moderation_events
               VALUES('OLD-SECRET', 'FINAL', '2026-10-09T12:00:00',
                      'discord_general', 0, 'SECRET', 'SENSITIVE_ID')"""
        )


def _seed_correction(db: sqlite3.Connection) -> None:
    decision = {
        "semantic_label": "SAFE",
        "message_action": "ALLOW",
        "review_priority": "NONE",
        "strike_recommendation": "NONE",
        "containment": "NONE",
        "containment_duration_seconds": None,
        "support_flow": "NONE",
    }
    db.execute("INSERT INTO correction_proposals VALUES(?, ?)",
               ("proposal-1", json.dumps(decision)))
    db.execute("INSERT INTO accepted_corrections VALUES(?, ?)",
               ("PRIVATE-SYNTHETIC-MESSAGE-0", "proposal-1"))


def test_private_read_only_aggregates_preserve_useful_diagnostics(tmp_path) -> None:
    path = tmp_path / "synthetic.sqlite"
    _fixture(path)
    summary = report(path, "2026-10-10", "2026-10-11")
    assert summary["total"]["finalized"] == 12
    assert summary["total"]["blocked"] == 1
    assert summary["total"]["review"] == 1
    assert summary["total"]["degraded"] == 1
    assert summary["total"]["fail_open"] == 1
    assert summary["total"]["accepted_corrections"] == 1
    assert summary["total"]["correction_changed_message_action"] == 1
    assert summary["per_model_policy"]["model-v1/policy-v1"][
        "correction_changed_message_action"
    ] == 1
    assert summary["total"]["strike_proposals"] == 1
    assert summary["total"]["mute_proposals"] == 1
    assert summary["per_model_policy"]["model-v1/policy-v1"]["finalized"] == 12
    assert summary["per_channel"]["minecraft_public"]["finalized"] == 12
    assert summary["latency_ms"]["sample_count"] == 12
    assert summary["client_side_timeouts_and_pre_persistence_losses_not_counted"]


def test_export_contains_no_raw_text_ids_or_reviews(tmp_path) -> None:
    path = tmp_path / "synthetic.sqlite"
    _fixture(path)
    serialized = json.dumps(report(path, "2026-10-10", "2026-10-11"))
    for sensitive in ("PRIVATE MESSAGE", "SENSITIVE_ID", "PRIVATE-SYNTHETIC", "PENDING-SECRET"):
        assert sensitive not in serialized
    assert '"text"' not in serialized
    assert "not_a_model_accuracy_certificate" in serialized


def test_below_threshold_model_channel_and_day_groups_are_suppressed(tmp_path) -> None:
    path = tmp_path / "synthetic.sqlite"
    _fixture(path)
    with sqlite3.connect(path) as db:
        db.execute(
            """UPDATE moderation_events
               SET channel_profile='discord_general'
               WHERE event_id='PRIVATE-SYNTHETIC-MESSAGE-0'"""
        )
        db.execute(
            """UPDATE decision_evidence
               SET local_model_version='experimental'
               WHERE event_id='PRIVATE-SYNTHETIC-MESSAGE-0'"""
        )
    result = report(path, "2026-10-10", "2026-10-11")
    assert "experimental/policy-v1" not in result["per_model_policy"]
    assert "discord_general" not in result["per_channel"]
    assert result["total"]["finalized"] == 12
    assert result["suppressed_small_group_threshold"] == 10


def test_missing_database_and_bad_window_do_not_silently_report_zeros(tmp_path) -> None:
    with pytest.raises(ValueError, match="local private SQLite"):
        report(tmp_path / "absent.sqlite", "2026-10-10", "2026-10-11")
    with pytest.raises(ValueError, match="later"):
        report(tmp_path / "absent.sqlite", "2026-10-11", "2026-10-10")
    with pytest.raises(ValueError):
        report(tmp_path / "absent.sqlite", "not-a-date", "2026-10-11")


def test_raw_records_remain_unmodified_after_aggregate_query(tmp_path) -> None:
    path = tmp_path / "synthetic.sqlite"
    _fixture(path)
    before = path.read_bytes()
    _ = report(path, "2026-10-10", "2026-10-11")
    assert path.read_bytes() == before

def test_offline_dashboard_is_private_aggregate_only(tmp_path) -> None:
    database = tmp_path / "fake.sqlite"
    _fixture(database)
    values = report(database, "2026-10-10", "2026-10-11")
    dashboard = render(values)
    assert "<script" not in dashboard
    assert "Enthusia moderation analytics" in dashboard
    assert "model-v1/policy-v1" in dashboard
    assert "mint" not in dashboard
    assert "PRIVATE MESSAGE TEXT" not in dashboard
    assert "SENSITIVE_ID" not in dashboard
    assert "PRIVATE-SYNTHETIC-MESSAGE" not in dashboard
    assert "not independently adjudicated model accuracy" in dashboard
    output = tmp_path / "dashboard.html"
    write_dashboard(output, values)
    assert output.read_text(encoding="utf-8") == dashboard
    with pytest.raises(ValueError, match="already exists"):
        write_dashboard(output, values)


def test_dashboard_escapes_untrusted_group_titles(tmp_path) -> None:
    database = tmp_path / "fake.sqlite"
    _fixture(database)
    values = report(database, "2026-10-10", "2026-10-11")
    values["per_model_policy"] = {"<img src=x onerror=alert(1)>": {"finalized": 12}}
    dashboard = render(values)
    assert "<img src=x" not in dashboard
    assert "&lt;img src=x onerror=alert(1)&gt;" in dashboard


def test_dashboard_refuses_files_inside_repository(tmp_path) -> None:
    from tools.data_v2.runtime_dashboard import REPO

    with pytest.raises(ValueError, match="outside Git"):
        write_dashboard(REPO / "public-dashboard.html", {
            "schema_version": "private-runtime-aggregates/1"
        })
    with pytest.raises(ValueError, match="Absolute private"):
        write_dashboard(Path("dashboard.html"), {})


