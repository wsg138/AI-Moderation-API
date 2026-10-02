from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .models import (
    Action,
    AdvisoryEvidence,
    AdvisoryStatus,
    EventDetails,
    Label,
    ModerationRequest,
    ModerationResponse,
    ReviewRequest,
    ReviewResponse,
)


class EventConflict(RuntimeError):
    pass


class EventInProgress(RuntimeError):
    pass


class EventNotFound(RuntimeError):
    pass


class DecisionConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Reservation:
    event_id: str
    replay: bool


_SCHEMA = """
CREATE TABLE IF NOT EXISTS moderation_events (
  event_id TEXT PRIMARY KEY,
  external_key TEXT NOT NULL UNIQUE,
  input_fingerprint TEXT NOT NULL,
  client_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  channel_id TEXT,
  external_message_id TEXT NOT NULL,
  sender_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  text TEXT NOT NULL,
  reply_to_message_id TEXT,
  status TEXT NOT NULL CHECK(status IN ('PENDING', 'FINAL')),
  action TEXT,
  label TEXT,
  degraded INTEGER NOT NULL DEFAULT 0,
  fallback_state TEXT,
  created_at TEXT NOT NULL,
  finalized_at TEXT
);
CREATE TABLE IF NOT EXISTS decision_evidence (
  event_id TEXT PRIMARY KEY REFERENCES moderation_events(event_id) ON DELETE CASCADE,
  scores_json TEXT NOT NULL,
  rule_hits_json TEXT NOT NULL,
  reason_codes_json TEXT NOT NULL,
  related_message_ids_json TEXT NOT NULL,
  local_model_version TEXT NOT NULL CHECK(length(local_model_version) > 0),
  policy_version TEXT NOT NULL CHECK(length(policy_version) > 0),
  latency_ms INTEGER NOT NULL CHECK(latency_ms >= 0),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS advisory_results (
  event_id TEXT PRIMARY KEY REFERENCES moderation_events(event_id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  model TEXT,
  flagged INTEGER,
  scores_json TEXT NOT NULL DEFAULT '{}',
  categories_json TEXT NOT NULL DEFAULT '{}',
  error_code TEXT,
  latency_ms INTEGER,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
  review_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES moderation_events(event_id) ON DELETE CASCADE,
  reviewer_id TEXT NOT NULL,
  label TEXT NOT NULL,
  action TEXT NOT NULL,
  reason_codes_json TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_scope_time
  ON moderation_events(platform, scope_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_reviews_event_time
  ON reviews(event_id, created_at);
"""


class ModerationStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    async def health_check(self) -> bool:
        return await asyncio.to_thread(self._health_check_sync)

    async def reserve_event(
        self,
        request: ModerationRequest,
        client_id: str,
        fingerprint: str,
        advisory_status: AdvisoryStatus,
    ) -> Reservation:
        return await asyncio.to_thread(
            self._reserve_event_sync,
            request,
            client_id,
            fingerprint,
            advisory_status,
        )

    async def finalize_event(self, response: ModerationResponse) -> None:
        await asyncio.to_thread(self._finalize_event_sync, response)

    async def load_decision(self, event_id: str) -> ModerationResponse:
        return await asyncio.to_thread(self._load_decision_sync, event_id)

    async def create_review(self, request: ReviewRequest) -> ReviewResponse:
        return await asyncio.to_thread(self._create_review_sync, request)

    async def get_event(self, event_id: str) -> EventDetails:
        return await asyncio.to_thread(self._get_event_sync, event_id)

    async def save_advisory(self, event_id: str, evidence: AdvisoryEvidence) -> None:
        await asyncio.to_thread(self._save_advisory_sync, event_id, evidence)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=2.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(_SCHEMA)

    def _health_check_sync(self) -> bool:
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT 1").fetchone()
            return row is not None and row[0] == 1
        except sqlite3.Error:
            return False

    def _reserve_event_sync(
        self,
        request: ModerationRequest,
        client_id: str,
        fingerprint: str,
        advisory_status: AdvisoryStatus,
    ) -> Reservation:
        external_key = _external_key(request)
        event_id = str(uuid4())
        now = _utc_now()
        try:
            with self._connect() as connection:
                self._insert_event(
                    connection,
                    event_id,
                    external_key,
                    fingerprint,
                    client_id,
                    request,
                    now,
                )
                self._insert_advisory(connection, event_id, advisory_status, now)
            return Reservation(event_id, replay=False)
        except sqlite3.IntegrityError:
            return self._resolve_existing(external_key, fingerprint)

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        event_id: str,
        external_key: str,
        fingerprint: str,
        client_id: str,
        request: ModerationRequest,
        now: str,
    ) -> None:
        connection.execute(
            """INSERT INTO moderation_events (
              event_id, external_key, input_fingerprint, client_id, platform, scope_id,
              channel_id, external_message_id, sender_id, occurred_at, text,
              reply_to_message_id, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)""",
            (
                event_id,
                external_key,
                fingerprint,
                client_id,
                request.platform,
                request.scope_id,
                request.channel_id,
                request.external_message_id,
                request.sender_id,
                request.occurred_at.isoformat(),
                request.text,
                request.reply_to_message_id,
                now,
            ),
        )

    def _insert_advisory(
        self,
        connection: sqlite3.Connection,
        event_id: str,
        status: AdvisoryStatus,
        now: str,
    ) -> None:
        connection.execute(
            "INSERT INTO advisory_results(event_id, status, updated_at) VALUES (?, ?, ?)",
            (event_id, status.value, now),
        )

    def _resolve_existing(self, external_key: str, fingerprint: str) -> Reservation:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT event_id, input_fingerprint, status
                   FROM moderation_events WHERE external_key = ?""",
                (external_key,),
            ).fetchone()
        if row is None or row["input_fingerprint"] != fingerprint:
            raise EventConflict("external message id was already used with different content")
        if row["status"] != "FINAL":
            raise EventInProgress("matching event is still being processed")
        return Reservation(str(row["event_id"]), replay=True)

    def _finalize_event_sync(self, response: ModerationResponse) -> None:
        if response.event_id is None:
            raise DecisionConflict("cannot finalize a response without an event id")
        now = _utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE moderation_events
                   SET status='FINAL', action=?, label=?, degraded=?,
                       fallback_state=?, finalized_at=?
                   WHERE event_id=? AND status='PENDING'""",
                (
                    response.action.value,
                    response.label.value,
                    int(response.degraded),
                    response.fallback_state,
                    now,
                    response.event_id,
                ),
            )
            if cursor.rowcount != 1:
                raise DecisionConflict("event is missing or already finalized")
            self._insert_evidence(connection, response, now)
            self._update_advisory_status(connection, response, now)

    def _update_advisory_status(
        self,
        connection: sqlite3.Connection,
        response: ModerationResponse,
        now: str,
    ) -> None:
        error_code = (
            "advisory_queue_saturated"
            if response.advisory_status is AdvisoryStatus.QUEUE_SATURATED
            else None
        )
        connection.execute(
            """UPDATE advisory_results
               SET status=?, error_code=?, updated_at=? WHERE event_id=?""",
            (response.advisory_status.value, error_code, now, response.event_id),
        )

    def _insert_evidence(
        self,
        connection: sqlite3.Connection,
        response: ModerationResponse,
        now: str,
    ) -> None:
        connection.execute(
            """INSERT INTO decision_evidence (
              event_id, scores_json, rule_hits_json, reason_codes_json,
              related_message_ids_json, local_model_version, policy_version,
              latency_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                response.event_id,
                _json(response.scores),
                _json(response.rule_hits),
                _json(response.reason_codes),
                _json(response.related_message_ids),
                response.local_model_version,
                response.policy_version,
                response.latency_ms,
                now,
            ),
        )

    def _load_decision_sync(self, event_id: str) -> ModerationResponse:
        with self._connect() as connection:
            row = connection.execute(_DECISION_SELECT, (event_id,)).fetchone()
        if row is None or row["status"] != "FINAL":
            raise EventNotFound(event_id)
        return _decision_from_row(row)

    def _create_review_sync(self, request: ReviewRequest) -> ReviewResponse:
        review_id = str(uuid4())
        created_at = datetime.now(UTC)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM moderation_events WHERE event_id=?",
                (request.event_id,),
            ).fetchone()
            if row is None or row["status"] != "FINAL":
                raise EventNotFound(request.event_id)
            connection.execute(
                """INSERT INTO reviews (
                  review_id, event_id, reviewer_id, label, action, reason_codes_json,
                  note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    review_id,
                    request.event_id,
                    request.reviewer_id,
                    request.label.value,
                    request.action.value,
                    _json(request.reason_codes),
                    request.note,
                    created_at.isoformat(),
                ),
            )
        return ReviewResponse(
            review_id=review_id,
            event_id=request.event_id,
            reviewer_id=request.reviewer_id,
            label=request.label,
            action=request.action,
            reason_codes=request.reason_codes,
            note=request.note,
            created_at=created_at,
        )

    def _get_event_sync(self, event_id: str) -> EventDetails:
        with self._connect() as connection:
            row = connection.execute(_EVENT_SELECT, (event_id,)).fetchone()
            if row is None or row["status"] != "FINAL":
                raise EventNotFound(event_id)
            reviews = connection.execute(
                "SELECT * FROM reviews WHERE event_id=? ORDER BY created_at ASC",
                (event_id,),
            ).fetchall()
        return _event_details_from_rows(row, reviews)

    def _save_advisory_sync(self, event_id: str, evidence: AdvisoryEvidence) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE advisory_results SET
                  status=?, model=?, flagged=?, scores_json=?, categories_json=?,
                  error_code=?, latency_ms=?, updated_at=? WHERE event_id=?""",
                (
                    evidence.status.value,
                    evidence.model,
                    None if evidence.flagged is None else int(evidence.flagged),
                    _json(evidence.scores),
                    _json(evidence.categories),
                    evidence.error_code,
                    evidence.latency_ms,
                    _utc_now(),
                    event_id,
                ),
            )
            if cursor.rowcount != 1:
                raise EventNotFound(event_id)


_DECISION_SELECT = """
SELECT e.*, d.*, a.status AS advisory_status
FROM moderation_events e
JOIN decision_evidence d ON d.event_id = e.event_id
LEFT JOIN advisory_results a ON a.event_id = e.event_id
WHERE e.event_id = ?
"""

_EVENT_SELECT = """
SELECT e.*, d.*, a.status AS advisory_status, a.model AS advisory_model,
       a.flagged AS advisory_flagged, a.scores_json AS advisory_scores_json,
       a.categories_json AS advisory_categories_json, a.error_code AS advisory_error_code,
       a.latency_ms AS advisory_latency_ms
FROM moderation_events e
JOIN decision_evidence d ON d.event_id = e.event_id
LEFT JOIN advisory_results a ON a.event_id = e.event_id
WHERE e.event_id = ?
"""


def _decision_from_row(row: sqlite3.Row) -> ModerationResponse:
    return ModerationResponse(
        event_id=row["event_id"],
        action=Action(row["action"]),
        label=Label(row["label"]),
        scores=json.loads(row["scores_json"]),
        rule_hits=json.loads(row["rule_hits_json"]),
        reason_codes=json.loads(row["reason_codes_json"]),
        related_message_ids=json.loads(row["related_message_ids_json"]),
        local_model_version=row["local_model_version"],
        policy_version=row["policy_version"],
        advisory_status=AdvisoryStatus(row["advisory_status"] or "DISABLED"),
        latency_ms=int(row["latency_ms"]),
        degraded=bool(row["degraded"]),
        fallback_state=row["fallback_state"],
    )


def _event_details_from_rows(row: sqlite3.Row, reviews: list[sqlite3.Row]) -> EventDetails:
    advisory = AdvisoryEvidence(
        status=AdvisoryStatus(row["advisory_status"] or "DISABLED"),
        model=row["advisory_model"],
        flagged=None if row["advisory_flagged"] is None else bool(row["advisory_flagged"]),
        scores=json.loads(row["advisory_scores_json"] or "{}"),
        categories=json.loads(row["advisory_categories_json"] or "{}"),
        error_code=row["advisory_error_code"],
        latency_ms=row["advisory_latency_ms"],
    )
    return EventDetails(
        event_id=row["event_id"],
        client_id=row["client_id"],
        platform=row["platform"],
        scope_id=row["scope_id"],
        channel_id=row["channel_id"],
        external_message_id=row["external_message_id"],
        sender_id=row["sender_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        text=row["text"],
        reply_to_message_id=row["reply_to_message_id"],
        decision=_decision_from_row(row),
        advisory=advisory,
        reviews=[_review_from_row(item) for item in reviews],
    )


def _review_from_row(row: sqlite3.Row) -> ReviewResponse:
    return ReviewResponse(
        review_id=row["review_id"],
        event_id=row["event_id"],
        reviewer_id=row["reviewer_id"],
        label=Label(row["label"]),
        action=Action(row["action"]),
        reason_codes=json.loads(row["reason_codes_json"]),
        note=row["note"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _external_key(request: ModerationRequest) -> str:
    return _json((request.platform, request.scope_id, request.external_message_id))


def _json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
