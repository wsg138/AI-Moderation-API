from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from moderation_api.migrations import MigrationError, migrate
from moderation_api.storage import ModerationStore

LEGACY_SCHEMA = """
CREATE TABLE moderation_events (
  event_id TEXT PRIMARY KEY, external_key TEXT NOT NULL UNIQUE,
  input_fingerprint TEXT NOT NULL, client_id TEXT NOT NULL,
  platform TEXT NOT NULL, scope_id TEXT NOT NULL, channel_id TEXT,
  external_message_id TEXT NOT NULL, sender_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL, text TEXT NOT NULL, reply_to_message_id TEXT,
  status TEXT NOT NULL, action TEXT, label TEXT, degraded INTEGER NOT NULL DEFAULT 0,
  fallback_state TEXT, created_at TEXT NOT NULL, finalized_at TEXT
);
CREATE TABLE decision_evidence (
  event_id TEXT PRIMARY KEY REFERENCES moderation_events(event_id), scores_json TEXT NOT NULL,
  rule_hits_json TEXT NOT NULL, reason_codes_json TEXT NOT NULL,
  related_message_ids_json TEXT NOT NULL, local_model_version TEXT NOT NULL,
  policy_version TEXT NOT NULL, latency_ms INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE advisory_results (
  event_id TEXT PRIMARY KEY REFERENCES moderation_events(event_id), status TEXT NOT NULL,
  model TEXT, flagged INTEGER, scores_json TEXT NOT NULL DEFAULT '{}',
  categories_json TEXT NOT NULL DEFAULT '{}', error_code TEXT, latency_ms INTEGER,
  disagrees_with_local INTEGER, updated_at TEXT NOT NULL
);
CREATE TABLE reviews (
  review_id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES moderation_events(event_id),
  reviewer_id TEXT NOT NULL, label TEXT NOT NULL, action TEXT NOT NULL,
  reason_codes_json TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL
);
"""


def seed_legacy(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(LEGACY_SCHEMA)
        connection.execute(
            """INSERT INTO moderation_events(
              event_id,external_key,input_fingerprint,client_id,platform,scope_id,channel_id,
              external_message_id,sender_id,occurred_at,text,status,action,label,
              created_at,finalized_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "legacy", '["minecraft","smp","m1"]', "fingerprint", "rosechat",
                "minecraft", "smp", "global", "m1", "p1", "2026-10-02T04:00:00+00:00",
                "review me", "FINAL", "REVIEW", "AMBIGUOUS_REVIEW",
                "2026-10-02T04:00:00+00:00", "2026-10-02T04:00:00+00:00",
            ),
        )
        connection.execute(
            """INSERT INTO decision_evidence VALUES(
              'legacy','{}','[]','["legacy_reason"]','[]','legacy-model','draft',1,
              '2026-10-02T04:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO advisory_results(event_id,status,updated_at)
               VALUES('legacy','DISABLED','2026-10-02T04:00:00+00:00')"""
        )


@pytest.mark.asyncio
async def test_w01_database_migrates_in_place_and_preserves_legacy_review(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite3"
    seed_legacy(path)
    store = ModerationStore(path)
    await store.initialize()

    decision = await store.load_decision("legacy")
    assert await store.schema_version() == 3  # nosec B101  # nosemgrep
    assert decision.message_action.value == "ALLOW"
    assert decision.review_priority.value == "NORMAL"
    assert decision.semantic_label.value == "AMBIGUOUS_REVIEW"
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT text FROM moderation_events").fetchone()[0] == "review me"
        assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0


def test_pending_row_gets_recoverable_lease_during_migration(tmp_path: Path) -> None:
    path = tmp_path / "pending-legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(LEGACY_SCHEMA)
        connection.execute(
            """INSERT INTO moderation_events(
              event_id,external_key,input_fingerprint,client_id,platform,scope_id,channel_id,
              external_message_id,sender_id,occurred_at,text,status,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "pending-legacy",
                '["minecraft","smp","pending"]',
                "fingerprint",
                "rosechat",
                "minecraft",
                "smp",
                "global",
                "pending",
                "p1",
                "2026-10-02T04:00:00+00:00",
                "hello",
                "PENDING",
                "2026-10-02T04:00:00+00:00",
            ),
        )
        connection.commit()
        migrate(connection)
        row = connection.execute(
            """SELECT reservation_token,reservation_updated_at
               FROM moderation_events WHERE event_id='pending-legacy'"""
        ).fetchone()
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert version == 3  # nosec B101  # nosemgrep
    assert row == ("pending-legacy", "2026-10-02T04:00:00+00:00")


def test_v3_adds_sender_identity_support_context_index(tmp_path: Path) -> None:
    path = tmp_path / "support-index.sqlite3"
    seed_legacy(path)
    with sqlite3.connect(path) as connection:
        migrate(connection)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        index = connection.execute(
            """SELECT sql FROM sqlite_master
               WHERE type='index' AND name='idx_events_sender_identity_time'"""
        ).fetchone()

    assert version == 3  # nosec B101  # nosemgrep
    assert index is not None  # nosec B101  # nosemgrep
    assert "sender_identity_id" in str(index[0])  # nosec B101  # nosemgrep
    assert "occurred_at DESC" in str(index[0])  # nosec B101  # nosemgrep


def test_failed_migration_rolls_back_without_recreating_database(tmp_path: Path) -> None:
    path = tmp_path / "broken.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE moderation_events(event_id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO moderation_events VALUES('sentinel')")
        connection.commit()
        with pytest.raises(MigrationError):
            migrate(connection)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        row = connection.execute("SELECT event_id FROM moderation_events").fetchone()[0]
        columns = {item[1] for item in connection.execute("PRAGMA table_info(moderation_events)")}
    assert version == 0
    assert row == "sentinel"
    assert columns == {"event_id"}


def test_newer_unknown_schema_is_rejected_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sentinel(value TEXT)")
        connection.execute("INSERT INTO sentinel VALUES('keep')")
        connection.execute("PRAGMA user_version=99")
        with pytest.raises(MigrationError):
            migrate(connection)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 99
        assert connection.execute("SELECT value FROM sentinel").fetchone()[0] == "keep"
