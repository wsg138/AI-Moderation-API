from __future__ import annotations

import sqlite3

LATEST_SCHEMA_VERSION = 3


class MigrationError(RuntimeError):
    pass


_BASE_TABLES = (
    """CREATE TABLE IF NOT EXISTS moderation_events (
      event_id TEXT PRIMARY KEY, external_key TEXT NOT NULL UNIQUE,
      input_fingerprint TEXT NOT NULL, client_id TEXT NOT NULL,
      platform TEXT NOT NULL, scope_id TEXT NOT NULL, channel_id TEXT,
      external_message_id TEXT NOT NULL, sender_id TEXT NOT NULL,
      occurred_at TEXT NOT NULL, text TEXT NOT NULL, reply_to_message_id TEXT,
      status TEXT NOT NULL CHECK(status IN ('PENDING', 'FINAL')),
      action TEXT, label TEXT, degraded INTEGER NOT NULL DEFAULT 0,
      fallback_state TEXT, created_at TEXT NOT NULL, finalized_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS decision_evidence (
      event_id TEXT PRIMARY KEY REFERENCES moderation_events(event_id) ON DELETE CASCADE,
      scores_json TEXT NOT NULL, rule_hits_json TEXT NOT NULL,
      reason_codes_json TEXT NOT NULL, related_message_ids_json TEXT NOT NULL,
      local_model_version TEXT NOT NULL CHECK(length(local_model_version) > 0),
      policy_version TEXT NOT NULL CHECK(length(policy_version) > 0),
      latency_ms INTEGER NOT NULL CHECK(latency_ms >= 0), created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS advisory_results (
      event_id TEXT PRIMARY KEY REFERENCES moderation_events(event_id) ON DELETE CASCADE,
      status TEXT NOT NULL, model TEXT, flagged INTEGER,
      scores_json TEXT NOT NULL DEFAULT '{}', categories_json TEXT NOT NULL DEFAULT '{}',
      error_code TEXT, latency_ms INTEGER, disagrees_with_local INTEGER,
      updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS reviews (
      review_id TEXT PRIMARY KEY,
      event_id TEXT NOT NULL REFERENCES moderation_events(event_id) ON DELETE CASCADE,
      reviewer_id TEXT NOT NULL, label TEXT NOT NULL, action TEXT NOT NULL,
      reason_codes_json TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL
    )""",
)

_BASE_COLUMNS = {
    "moderation_events": {
        "event_id", "external_key", "input_fingerprint", "client_id", "platform",
        "scope_id", "external_message_id", "sender_id", "occurred_at", "text",
        "status", "created_at",
    },
    "decision_evidence": {
        "event_id", "scores_json", "rule_hits_json", "reason_codes_json",
        "related_message_ids_json", "local_model_version", "policy_version",
        "latency_ms", "created_at",
    },
}

_V1_COLUMNS = {
    "moderation_events": (
        ("channel_profile", "TEXT"),
        ("conversation_id", "TEXT"),
        ("canonical_message_id", "TEXT"),
        ("canonical_fingerprint", "TEXT"),
        ("sender_identity_id", "TEXT"),
        ("recipient_ids_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("recipient_identity_ids_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("target_ids_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("target_identity_ids_json", "TEXT NOT NULL DEFAULT '[]'"),
    ),
    "decision_evidence": (
        ("ingestion_status", "TEXT NOT NULL DEFAULT 'INGESTED'"),
        ("message_action", "TEXT"),
        ("semantic_label", "TEXT"),
        ("review_priority", "TEXT NOT NULL DEFAULT 'NONE'"),
        ("strike_recommendation", "TEXT NOT NULL DEFAULT 'NONE'"),
        ("containment", "TEXT NOT NULL DEFAULT 'NONE'"),
        ("containment_duration_seconds", "INTEGER"),
        ("support_flow", "TEXT NOT NULL DEFAULT 'NONE'"),
        ("confidence", "REAL"),
        ("evidence_event_ids_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("related_event_ids_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("incident_id", "TEXT"),
    ),
}

_V2_COLUMNS = {
    "moderation_events": (
        ("reservation_token", "TEXT"),
        ("reservation_updated_at", "TEXT"),
    ),
}


_V1_TABLES = (
    """CREATE TABLE message_aliases (
      alias_key TEXT PRIMARY KEY,
      event_id TEXT NOT NULL REFERENCES moderation_events(event_id) ON DELETE CASCADE,
      request_fingerprint TEXT NOT NULL, platform TEXT NOT NULL, scope_id TEXT NOT NULL,
      channel_id TEXT, external_message_id TEXT NOT NULL, created_at TEXT NOT NULL
    )""",
    """CREATE TABLE incidents (
      incident_id TEXT PRIMARY KEY, incident_key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
      severity INTEGER NOT NULL CHECK(severity BETWEEN 0 AND 100),
      coordinated INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE incident_events (
      incident_id TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
      event_id TEXT NOT NULL REFERENCES moderation_events(event_id) ON DELETE CASCADE,
      sender_id TEXT NOT NULL, target_ids_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY (incident_id, event_id)
    )""",
    """CREATE TABLE moderation_memory (
      memory_id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject_id TEXT NOT NULL,
      target_id TEXT, platform TEXT NOT NULL, payload_json TEXT NOT NULL,
      confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1), source TEXT NOT NULL,
      confirmed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL, expires_at TEXT
    )""",
    """CREATE TABLE safety_memory (
      memory_id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject_id TEXT NOT NULL,
      payload_json TEXT NOT NULL, confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
      source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, expires_at TEXT
    )""",
    """CREATE TABLE identity_links (
      platform TEXT NOT NULL, platform_user_id TEXT NOT NULL,
      canonical_identity_id TEXT NOT NULL, source TEXT NOT NULL,
      confirmed_at TEXT NOT NULL, revoked_at TEXT,
      PRIMARY KEY (platform, platform_user_id)
    )""",
    """CREATE TABLE correction_proposals (
      proposal_id TEXT PRIMARY KEY,
      event_id TEXT NOT NULL REFERENCES moderation_events(event_id) ON DELETE CASCADE,
      correction_hash TEXT NOT NULL, corrected_json TEXT NOT NULL, note TEXT,
      status TEXT NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT,
      UNIQUE(event_id, correction_hash)
    )""",
    """CREATE TABLE correction_votes (
      proposal_id TEXT NOT NULL REFERENCES correction_proposals(proposal_id) ON DELETE CASCADE,
      reviewer_id TEXT NOT NULL, authority TEXT NOT NULL, vote TEXT NOT NULL,
      created_at TEXT NOT NULL, PRIMARY KEY (proposal_id, reviewer_id)
    )""",
    """CREATE TABLE accepted_corrections (
      event_id TEXT PRIMARY KEY REFERENCES moderation_events(event_id) ON DELETE CASCADE,
      proposal_id TEXT NOT NULL UNIQUE
        REFERENCES correction_proposals(proposal_id) ON DELETE CASCADE,
      accepted_at TEXT NOT NULL
    )""",
)

_INDEXES = (
    """CREATE INDEX IF NOT EXISTS idx_events_scope_time
       ON moderation_events(platform, scope_id, occurred_at)""",
    "CREATE INDEX IF NOT EXISTS idx_aliases_event ON message_aliases(event_id)",
    "CREATE INDEX IF NOT EXISTS idx_incident_events_event ON incident_events(event_id)",
    """CREATE INDEX IF NOT EXISTS idx_memory_subject
       ON moderation_memory(platform, subject_id, expires_at)""",
    """CREATE INDEX IF NOT EXISTS idx_memory_target
       ON moderation_memory(platform, subject_id, target_id, expires_at)""",
    """CREATE INDEX IF NOT EXISTS idx_safety_memory_subject
       ON safety_memory(subject_id, expires_at)""",
    """CREATE INDEX IF NOT EXISTS idx_corrections_event_status
       ON correction_proposals(event_id, status)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_events_canonical_message
       ON moderation_events(canonical_message_id)
       WHERE canonical_message_id IS NOT NULL""",
)


def migrate(connection: sqlite3.Connection) -> int:
    current = schema_version(connection)
    if current > LATEST_SCHEMA_VERSION:
        raise MigrationError(
            f"database schema version {current} is newer than supported {LATEST_SCHEMA_VERSION}"
        )
    if current == LATEST_SCHEMA_VERSION:
        return current
    try:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_base_schema(connection)
        _validate_base_schema(connection)
        if current < 1:
            _apply_v1(connection)
        if current < 2:
            _apply_v2(connection)
        if current < 3:
            _apply_v3(connection)
        connection.execute(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION}")
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise MigrationError("schema migration failed; transaction rolled back") from exc
    return LATEST_SCHEMA_VERSION


def schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row is not None else 0


def _ensure_base_schema(connection: sqlite3.Connection) -> None:
    for statement in _BASE_TABLES:
        connection.execute(statement)


def _validate_base_schema(connection: sqlite3.Connection) -> None:
    for table, required in _BASE_COLUMNS.items():
        missing = required - _columns(connection, table)
        if missing:
            raise MigrationError(f"legacy table {table} is missing columns: {sorted(missing)}")


def _apply_v1(connection: sqlite3.Connection) -> None:
    for table, columns in _V1_COLUMNS.items():
        for column, definition in columns:
            _add_column_if_missing(connection, table, column, definition)
    for statement in _V1_TABLES:
        _create_table_if_missing(connection, statement)
    for statement in _INDEXES:
        connection.execute(statement)
    _backfill_v1_decisions(connection)


def _apply_v2(connection: sqlite3.Connection) -> None:
    for table, columns in _V2_COLUMNS.items():
        for column, definition in columns:
            _add_column_if_missing(connection, table, column, definition)
    connection.execute(
        """UPDATE moderation_events
           SET reservation_token=COALESCE(reservation_token,event_id),
               reservation_updated_at=COALESCE(reservation_updated_at,created_at)
           WHERE status='PENDING'"""
    )


def _apply_v3(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE INDEX IF NOT EXISTS idx_events_sender_identity_time
           ON moderation_events(sender_identity_id, occurred_at DESC)
           WHERE sender_identity_id IS NOT NULL"""
    )


def _create_table_if_missing(connection: sqlite3.Connection, statement: str) -> None:
    connection.execute(statement.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1))


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    if column not in _columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


def _backfill_v1_decisions(connection: sqlite3.Connection) -> None:
    connection.execute(
        """UPDATE decision_evidence SET message_action = (
             SELECT CASE WHEN e.action='BLOCK' THEN 'BLOCK' ELSE 'ALLOW' END
             FROM moderation_events e WHERE e.event_id=decision_evidence.event_id
           ) WHERE message_action IS NULL"""
    )
    connection.execute(
        """UPDATE decision_evidence SET semantic_label = (
             SELECT e.label FROM moderation_events e
             WHERE e.event_id=decision_evidence.event_id
           ) WHERE semantic_label IS NULL"""
    )
    connection.execute(
        """UPDATE decision_evidence SET review_priority='NORMAL'
           WHERE event_id IN (SELECT event_id FROM moderation_events WHERE action='REVIEW')"""
    )
