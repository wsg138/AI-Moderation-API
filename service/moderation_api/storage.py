from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from .migrations import LATEST_SCHEMA_VERSION, migrate, schema_version
from .models import (
    AdvisoryEvidence,
    AdvisoryStatus,
    ChannelProfile,
    Containment,
    ContextEvidence,
    ContextMessage,
    CorrectionAuthority,
    CorrectionDecision,
    CorrectionRejectRequest,
    CorrectionRequest,
    CorrectionResponse,
    CorrectionStatus,
    CorrectionVote,
    DecisionHistoryFilter,
    DecisionHistoryItem,
    DecisionHistoryPage,
    EventDetails,
    IncidentKind,
    IncidentSignal,
    IncidentSummary,
    IngestionStatus,
    Label,
    MemoryFact,
    MemoryKind,
    MemorySnapshot,
    MessageAction,
    MessageRef,
    ModerationRequest,
    ModerationResponse,
    Platform,
    ReviewItem,
    ReviewPriority,
    SafetyMemoryFact,
    SafetyMemoryKind,
    StrikeRecommendation,
    SupportContextDecision,
    SupportDecisionSource,
    SupportFlow,
)


class EventConflict(RuntimeError):
    pass


class EventInProgress(RuntimeError):
    pass


class EventNotFound(RuntimeError):
    pass


class DecisionConflict(RuntimeError):
    pass


class ProposalNotFound(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Reservation:
    event_id: str
    replay: bool
    lease_token: str | None = None
    pending: bool = False
    recovery_request: ModerationRequest | None = None


class ModerationStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    async def initialize(self) -> None:
        await asyncio.to_thread(_initialize, self._path)

    async def health_check(self) -> bool:
        return await asyncio.to_thread(_health_check, self._path)

    async def schema_version(self) -> int | None:
        return await asyncio.to_thread(_read_schema_version, self._path)

    async def reserve_event(
        self,
        request: ModerationRequest,
        client_id: str,
        request_fingerprint: str,
        canonical_fingerprint: str,
        advisory_status: AdvisoryStatus,
        pending_stale_after_ms: int = 30_000,
    ) -> Reservation:
        return await asyncio.to_thread(
            _reserve_event,
            self._path,
            request,
            client_id,
            request_fingerprint,
            canonical_fingerprint,
            advisory_status,
            pending_stale_after_ms,
        )

    async def finalize_event(
        self,
        response: ModerationResponse,
        evidence_event_ids: tuple[str, ...],
        related_event_ids: tuple[str, ...],
        incident_signal: IncidentSignal | None,
        lease_token: str,
    ) -> None:
        await asyncio.to_thread(
            _finalize_event,
            self._path,
            response,
            evidence_event_ids,
            related_event_ids,
            incident_signal,
            lease_token,
        )

    async def load_decision(self, event_id: str) -> ModerationResponse:
        return await asyncio.to_thread(_load_decision, self._path, event_id)

    async def get_event(self, event_id: str) -> EventDetails:
        return await asyncio.to_thread(_get_event, self._path, event_id)

    async def list_review_items(self, limit: int) -> list[ReviewItem]:
        return await asyncio.to_thread(_list_review_items, self._path, limit)

    async def list_decisions(
        self, limit: int, cursor: str | None = None,
        filter: DecisionHistoryFilter = DecisionHistoryFilter.ALL,
    ) -> DecisionHistoryPage:
        return await asyncio.to_thread(_list_decisions, self._path, limit, cursor, filter)

    async def list_support_context(
        self,
        subject_id: str,
        limit: int,
    ) -> list[SupportContextDecision]:
        return await asyncio.to_thread(
            _list_support_context,
            self._path,
            subject_id,
            limit,
        )

    async def create_correction(
        self,
        request: CorrectionRequest,
        admin_override: bool,
    ) -> CorrectionResponse:
        return await asyncio.to_thread(_create_correction, self._path, request, admin_override)

    async def reject_correction(
        self,
        proposal_id: str,
        request: CorrectionRejectRequest,
        admin_override: bool,
    ) -> CorrectionResponse:
        return await asyncio.to_thread(
            _reject_correction,
            self._path,
            proposal_id,
            request,
            admin_override,
        )

    async def save_advisory(self, event_id: str, evidence: AdvisoryEvidence) -> None:
        await asyncio.to_thread(_save_advisory, self._path, event_id, evidence)

    async def load_recent_context(
        self,
        window_seconds: int,
        limit: int,
    ) -> tuple[ContextMessage, ...]:
        return await asyncio.to_thread(_load_recent_context, self._path, window_seconds, limit)

    async def load_memory_snapshot(
        self,
        current: ContextMessage,
        limit: int,
    ) -> MemorySnapshot:
        return await asyncio.to_thread(_load_memory_snapshot, self._path, current, limit)

    async def save_memory_fact(self, fact: MemoryFact) -> None:
        await asyncio.to_thread(_save_memory_fact, self._path, fact)

    async def save_safety_memory_fact(self, fact: SafetyMemoryFact) -> None:
        await asyncio.to_thread(_save_safety_memory_fact, self._path, fact)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=2.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        migrate(connection)


def _health_check(path: Path) -> bool:
    try:
        with _connect(path) as connection:
            row = connection.execute("SELECT 1").fetchone()
            version = schema_version(connection)
        return bool(row and row[0] == 1 and version == LATEST_SCHEMA_VERSION)
    except Exception:
        return False


def _read_schema_version(path: Path) -> int | None:
    try:
        with _connect(path) as connection:
            return schema_version(connection)
    except Exception:
        return None


def _reserve_event(
    path: Path,
    request: ModerationRequest,
    client_id: str,
    request_fingerprint: str,
    canonical_fingerprint: str,
    advisory_status: AdvisoryStatus,
    pending_stale_after_ms: int,
) -> Reservation:
    now = datetime.now(UTC)
    now_text = now.isoformat()
    with _connect(path) as connection:
        # Serialize the short reservation transaction so two first-arrival mirrors
        # cannot both observe an empty canonical key before either insert commits.
        connection.execute("BEGIN IMMEDIATE")
        existing = _find_existing(connection, request)
        if existing is not None:
            return _resolve_existing(
                connection,
                existing,
                request,
                request_fingerprint,
                now,
                pending_stale_after_ms,
            )
        mirror = _find_canonical(connection, request.canonical_message_id)
        if mirror is not None:
            return _resolve_mirror(
                connection,
                mirror,
                request,
                request_fingerprint,
                canonical_fingerprint,
                now,
                pending_stale_after_ms,
            )
        return _insert_new_event(
            connection,
            request,
            client_id,
            request_fingerprint,
            canonical_fingerprint,
            advisory_status,
            now_text,
        )


def _find_existing(
    connection: sqlite3.Connection,
    request: ModerationRequest,
) -> sqlite3.Row | None:
    alias = cast(
        sqlite3.Row | None,
        connection.execute(
            """SELECT a.event_id, a.request_fingerprint, e.status, e.created_at,
                      e.reservation_token, e.reservation_updated_at, 'alias' AS source
               FROM message_aliases a JOIN moderation_events e ON e.event_id=a.event_id
               WHERE a.alias_key=?""",
            (_external_key(request),),
        ).fetchone(),
    )
    if alias is not None:
        return alias
    return cast(
        sqlite3.Row | None,
        connection.execute(
            """SELECT event_id, input_fingerprint AS request_fingerprint, status, created_at,
                      reservation_token, reservation_updated_at, 'legacy' AS source
               FROM moderation_events WHERE external_key=?""",
            (_external_key(request),),
        ).fetchone(),
    )


def _resolve_existing(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    request: ModerationRequest,
    fingerprint: str,
    now: datetime,
    pending_stale_after_ms: int,
) -> Reservation:
    if row["request_fingerprint"] != fingerprint:
        raise EventConflict("external message id was already used with different input")
    if row["source"] == "legacy":
        _insert_alias(connection, str(row["event_id"]), request, fingerprint, now.isoformat())
    return _reservation_from_existing(connection, row, now, pending_stale_after_ms)


def _find_canonical(
    connection: sqlite3.Connection,
    canonical_message_id: str | None,
) -> sqlite3.Row | None:
    if canonical_message_id is None:
        return None
    return cast(
        sqlite3.Row | None,
        connection.execute(
            """SELECT event_id, status, canonical_fingerprint, created_at,
                      reservation_token, reservation_updated_at
               FROM moderation_events WHERE canonical_message_id=?""",
            (canonical_message_id,),
        ).fetchone(),
    )


def _resolve_mirror(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    request: ModerationRequest,
    request_fingerprint: str,
    canonical_fingerprint: str,
    now: datetime,
    pending_stale_after_ms: int,
) -> Reservation:
    stored = row["canonical_fingerprint"]
    if stored is not None and stored != canonical_fingerprint:
        raise EventConflict("canonical message id was reused for different message content")
    event_id = str(row["event_id"])
    _insert_alias(connection, event_id, request, request_fingerprint, now.isoformat())
    return _reservation_from_existing(connection, row, now, pending_stale_after_ms)


def _insert_new_event(
    connection: sqlite3.Connection,
    request: ModerationRequest,
    client_id: str,
    request_fingerprint: str,
    canonical_fingerprint: str,
    advisory_status: AdvisoryStatus,
    now: str,
) -> Reservation:
    event_id = str(uuid4())
    lease_token = str(uuid4())
    _insert_event(
        connection,
        event_id,
        request,
        client_id,
        request_fingerprint,
        canonical_fingerprint,
        lease_token,
        now,
    )
    _insert_alias(connection, event_id, request, request_fingerprint, now)
    connection.execute(
        "INSERT INTO advisory_results(event_id,status,updated_at) VALUES(?,?,?)",
        (event_id, advisory_status.value, now),
    )
    return Reservation(event_id, replay=False, lease_token=lease_token)


def _insert_event(
    connection: sqlite3.Connection,
    event_id: str,
    request: ModerationRequest,
    client_id: str,
    fingerprint: str,
    canonical_fingerprint: str,
    lease_token: str,
    now: str,
) -> None:
    connection.execute(
        """INSERT INTO moderation_events (
          event_id,external_key,input_fingerprint,client_id,platform,channel_profile,
          scope_id,channel_id,conversation_id,external_message_id,canonical_message_id,
          canonical_fingerprint,sender_id,sender_identity_id,recipient_ids_json,
          recipient_identity_ids_json,target_ids_json,target_identity_ids_json,
          occurred_at,text,reply_to_message_id,status,created_at,reservation_token,
          reservation_updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING',?,?,?)""",
        _event_values(
            event_id,
            request,
            client_id,
            fingerprint,
            canonical_fingerprint,
            lease_token,
            now,
        ),
    )


def _event_values(
    event_id: str,
    request: ModerationRequest,
    client_id: str,
    fingerprint: str,
    canonical_fingerprint: str,
    lease_token: str,
    now: str,
) -> tuple[object, ...]:
    return (
        event_id, _external_key(request), fingerprint, client_id, request.platform.value,
        request.channel_profile.value, request.scope_id, request.channel_id,
        request.conversation_id, request.external_message_id, request.canonical_message_id,
        canonical_fingerprint, request.sender_id, request.sender_identity_id,
        _json(request.recipient_ids), _json(request.recipient_identity_ids),
        _json(request.target_ids), _json(request.target_identity_ids),
        request.occurred_at.isoformat(), request.text, request.reply_to_message_id, now,
        lease_token, now,
    )


def _insert_alias(
    connection: sqlite3.Connection,
    event_id: str,
    request: ModerationRequest,
    fingerprint: str,
    now: str,
) -> None:
    connection.execute(
        """INSERT INTO message_aliases (
          alias_key,event_id,request_fingerprint,platform,scope_id,channel_id,
          external_message_id,created_at
        ) VALUES(?,?,?,?,?,?,?,?)""",
        (
            _external_key(request), event_id, fingerprint, request.platform.value,
            request.scope_id, request.channel_id, request.external_message_id, now,
        ),
    )


def _reservation_from_existing(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    now: datetime,
    pending_stale_after_ms: int,
) -> Reservation:
    event_id = str(row["event_id"])
    if row["status"] == "FINAL":
        return Reservation(event_id, replay=True)
    if not _pending_is_stale(row, now, pending_stale_after_ms):
        return Reservation(event_id, replay=False, pending=True)
    return _claim_stale_pending(connection, row, now)


def _pending_is_stale(
    row: sqlite3.Row,
    now: datetime,
    pending_stale_after_ms: int,
) -> bool:
    raw = row["reservation_updated_at"] or row["created_at"]
    updated_at = datetime.fromisoformat(str(raw))
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    age = now - updated_at.astimezone(UTC)
    return age >= timedelta(milliseconds=pending_stale_after_ms)


def _claim_stale_pending(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    now: datetime,
) -> Reservation:
    event_id = str(row["event_id"])
    previous_token = row["reservation_token"]
    previous_updated_at = row["reservation_updated_at"]
    lease_token = str(uuid4())
    now_text = now.isoformat()
    cursor = connection.execute(
        """UPDATE moderation_events
           SET reservation_token=?,reservation_updated_at=?
           WHERE event_id=? AND status='PENDING'
             AND COALESCE(reservation_token,'')=COALESCE(?, '')
             AND COALESCE(reservation_updated_at,'')=COALESCE(?, '')""",
        (lease_token, now_text, event_id, previous_token, previous_updated_at),
    )
    if cursor.rowcount != 1:
        return Reservation(event_id, replay=False, pending=True)
    return Reservation(
        event_id,
        replay=False,
        lease_token=lease_token,
        recovery_request=_load_pending_request(connection, event_id),
    )


def _load_pending_request(
    connection: sqlite3.Connection,
    event_id: str,
) -> ModerationRequest:
    row = connection.execute(
        "SELECT * FROM moderation_events WHERE event_id=? AND status='PENDING'",
        (event_id,),
    ).fetchone()
    if row is None:
        raise EventNotFound(event_id)
    return ModerationRequest(
        platform=Platform(row["platform"]),
        channel_profile=_profile_from_row(row),
        scope_id=str(row["scope_id"]),
        channel_id=row["channel_id"],
        conversation_id=row["conversation_id"],
        external_message_id=str(row["external_message_id"]),
        canonical_message_id=row["canonical_message_id"],
        sender_id=str(row["sender_id"]),
        sender_identity_id=row["sender_identity_id"],
        recipient_ids=json.loads(row["recipient_ids_json"] or "[]"),
        recipient_identity_ids=json.loads(row["recipient_identity_ids_json"] or "[]"),
        target_ids=json.loads(row["target_ids_json"] or "[]"),
        target_identity_ids=json.loads(row["target_identity_ids_json"] or "[]"),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        text=str(row["text"]),
        reply_to_message_id=row["reply_to_message_id"],
    )


def _finalize_event(
    path: Path,
    response: ModerationResponse,
    evidence_event_ids: tuple[str, ...],
    related_event_ids: tuple[str, ...],
    incident_signal: IncidentSignal | None,
    lease_token: str,
) -> None:
    if response.event_id is None:
        raise DecisionConflict("cannot finalize response without event id")
    now = _utc_now()
    with _connect(path) as connection:
        _finalize_event_row(connection, response, lease_token, now)
        _insert_decision_evidence(connection, response, evidence_event_ids, related_event_ids, now)
        if incident_signal is not None and response.incident is not None:
            _upsert_incident(connection, response.event_id, response.incident, incident_signal, now)
        _update_advisory_status(connection, response, now)


def _finalize_event_row(
    connection: sqlite3.Connection,
    response: ModerationResponse,
    lease_token: str,
    now: str,
) -> None:
    cursor = connection.execute(
        """UPDATE moderation_events SET status='FINAL',action=?,label=?,degraded=?,
           fallback_state=?,finalized_at=?,reservation_token=NULL,reservation_updated_at=?
           WHERE event_id=? AND status='PENDING' AND reservation_token=?""",
        (
            response.message_action.value,
            response.semantic_label.value,
            int(response.degraded),
            response.fallback_state,
            now,
            now,
            response.event_id,
            lease_token,
        ),
    )
    if cursor.rowcount != 1:
        raise DecisionConflict("event is missing, finalized, or reservation ownership changed")


def _insert_decision_evidence(
    connection: sqlite3.Connection,
    response: ModerationResponse,
    evidence_event_ids: tuple[str, ...],
    related_event_ids: tuple[str, ...],
    now: str,
) -> None:
    connection.execute(
        """INSERT INTO decision_evidence (
          event_id,scores_json,rule_hits_json,reason_codes_json,related_message_ids_json,
          local_model_version,policy_version,latency_ms,created_at,ingestion_status,
          message_action,semantic_label,review_priority,strike_recommendation,containment,
          containment_duration_seconds,support_flow,confidence,evidence_event_ids_json,
          related_event_ids_json,incident_id
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        _evidence_values(response, evidence_event_ids, related_event_ids, now),
    )


def _evidence_values(
    response: ModerationResponse,
    evidence_event_ids: tuple[str, ...],
    related_event_ids: tuple[str, ...],
    now: str,
) -> tuple[object, ...]:
    return (
        response.event_id, _json(response.scores), _json(response.rule_hits),
        _json(response.reason_codes), _json(response.related_message_ids),
        response.local_model_version, response.policy_version, response.latency_ms, now,
        response.ingestion_status.value, response.message_action.value,
        response.semantic_label.value, response.review_priority.value,
        response.strike_recommendation.value, response.containment.value,
        response.containment_duration_seconds, response.support_flow.value,
        response.confidence, _json(evidence_event_ids), _json(related_event_ids),
        response.incident.incident_id if response.incident else None,
    )


def _upsert_incident(
    connection: sqlite3.Connection,
    event_id: str,
    summary: IncidentSummary,
    signal: IncidentSignal,
    now: str,
) -> None:
    connection.execute(
        """INSERT INTO incidents(
             incident_id,incident_key,kind,severity,coordinated,created_at,updated_at
           ) VALUES(?,?,?,?,?,?,?) ON CONFLICT(incident_key) DO UPDATE SET
           severity=MAX(incidents.severity,excluded.severity),
           coordinated=MAX(incidents.coordinated,excluded.coordinated),
           updated_at=excluded.updated_at""",
        (
            summary.incident_id, signal.incident_key, summary.kind.value, summary.severity,
            int(summary.coordinated), now, now,
        ),
    )
    connection.execute(
        """INSERT OR IGNORE INTO incident_events(
             incident_id,event_id,sender_id,target_ids_json,created_at
           ) SELECT ?,event_id,sender_id,target_ids_json,?
             FROM moderation_events WHERE event_id=?""",
        (summary.incident_id, now, event_id),
    )


def _update_advisory_status(
    connection: sqlite3.Connection,
    response: ModerationResponse,
    now: str,
) -> None:
    error = (
        "advisory_queue_saturated"
        if response.advisory_status is AdvisoryStatus.QUEUE_SATURATED
        else None
    )
    connection.execute(
        "UPDATE advisory_results SET status=?,error_code=?,updated_at=? WHERE event_id=?",
        (response.advisory_status.value, error, now, response.event_id),
    )


_DECISION_SELECT = """
SELECT e.*,d.*,a.status AS advisory_status FROM moderation_events e
JOIN decision_evidence d ON d.event_id=e.event_id
LEFT JOIN advisory_results a ON a.event_id=e.event_id WHERE e.event_id=?
"""

_EVENT_SELECT = """
SELECT e.*,d.*,a.status AS advisory_status,a.model AS advisory_model,
       a.flagged AS advisory_flagged,a.scores_json AS advisory_scores_json,
       a.categories_json AS advisory_categories_json,a.error_code AS advisory_error_code,
       a.latency_ms AS advisory_latency_ms,
       a.disagrees_with_local AS advisory_disagrees_with_local
FROM moderation_events e JOIN decision_evidence d ON d.event_id=e.event_id
LEFT JOIN advisory_results a ON a.event_id=e.event_id WHERE e.event_id=?
"""


def _load_decision(path: Path, event_id: str) -> ModerationResponse:
    with _connect(path) as connection:
        row = connection.execute(_DECISION_SELECT, (event_id,)).fetchone()
        if row is None or row["status"] != "FINAL":
            raise EventNotFound(event_id)
        return _decision_from_row(connection, row)


def _decision_from_row(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
) -> ModerationResponse:
    related_event_ids = tuple(json.loads(row["related_event_ids_json"] or "[]"))
    related_refs = _message_refs(connection, related_event_ids)
    return ModerationResponse(
        event_id=str(row["event_id"]),
        ingestion_status=IngestionStatus(row["ingestion_status"] or "INGESTED"),
        message_action=MessageAction(row["message_action"] or _legacy_action(row["action"])),
        semantic_label=Label(row["semantic_label"] or row["label"]),
        review_priority=ReviewPriority(row["review_priority"]),
        strike_recommendation=StrikeRecommendation(row["strike_recommendation"]),
        containment=Containment(row["containment"]),
        containment_duration_seconds=row["containment_duration_seconds"],
        support_flow=SupportFlow(row["support_flow"]),
        scores=json.loads(row["scores_json"]), confidence=row["confidence"],
        rule_hits=json.loads(row["rule_hits_json"]),
        reason_codes=json.loads(row["reason_codes_json"]),
        related_message_ids=json.loads(row["related_message_ids_json"]),
        related_messages=related_refs,
        incident=_incident_summary(connection, row["incident_id"]),
        local_model_version=str(row["local_model_version"]),
        policy_version=str(row["policy_version"]),
        advisory_status=AdvisoryStatus(row["advisory_status"] or "DISABLED"),
        latency_ms=int(row["latency_ms"]), degraded=bool(row["degraded"]),
        fallback_state=row["fallback_state"],
    )


def _message_refs(
    connection: sqlite3.Connection,
    event_ids: tuple[str, ...],
) -> list[MessageRef]:
    refs: list[MessageRef] = []
    for event_id in event_ids:
        rows = connection.execute(
            """SELECT platform,scope_id,channel_id,external_message_id FROM message_aliases
               WHERE event_id=? ORDER BY created_at ASC""",
            (event_id,),
        ).fetchall()
        if not rows:
            rows = connection.execute(
                """SELECT platform,scope_id,channel_id,external_message_id FROM moderation_events
                   WHERE event_id=?""",
                (event_id,),
            ).fetchall()
        refs.extend(_message_ref(row) for row in rows)
    return refs


def _incident_summary(
    connection: sqlite3.Connection,
    incident_id: str | None,
) -> IncidentSummary | None:
    if incident_id is None:
        return None
    incident = connection.execute(
        "SELECT * FROM incidents WHERE incident_id=?", (incident_id,)
    ).fetchone()
    if incident is None:
        return None
    events = connection.execute(
        "SELECT sender_id,target_ids_json FROM incident_events WHERE incident_id=?",
        (incident_id,),
    ).fetchall()
    participants = sorted({str(row["sender_id"]) for row in events})
    targets = sorted({target for row in events for target in json.loads(row["target_ids_json"])})
    return IncidentSummary(
        incident_id=incident_id, kind=IncidentKind(incident["kind"]),
        severity=int(incident["severity"]), coordinated=bool(incident["coordinated"]),
        participant_ids=participants, target_ids=targets,
    )


def _get_event(path: Path, event_id: str) -> EventDetails:
    with _connect(path) as connection:
        row = connection.execute(_EVENT_SELECT, (event_id,)).fetchone()
        if row is None or row["status"] != "FINAL":
            raise EventNotFound(event_id)
        decision = _decision_from_row(connection, row)
        corrections = _corrections_for_event(connection, event_id)
        accepted = _accepted_correction(connection, event_id)
        context = _context_evidence_rows(connection, row)
        return _event_details(row, decision, corrections, accepted, context)


def _context_evidence_rows(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
) -> list[ContextEvidence]:
    event_ids = tuple(json.loads(row["evidence_event_ids_json"] or "[]"))
    evidence: list[ContextEvidence] = []
    for event_id in event_ids:
        item = connection.execute(
            """SELECT event_id,platform,scope_id,channel_id,external_message_id,
                      sender_id,occurred_at,text FROM moderation_events
               WHERE event_id=? AND status='FINAL'""",
            (event_id,),
        ).fetchone()
        if item is not None:
            evidence.append(_context_evidence(item))
    return evidence


def _event_details(
    row: sqlite3.Row,
    decision: ModerationResponse,
    corrections: list[CorrectionResponse],
    accepted: CorrectionResponse | None,
    context: list[ContextEvidence],
) -> EventDetails:
    return EventDetails(
        event_id=str(row["event_id"]), client_id=str(row["client_id"]),
        platform=Platform(row["platform"]), channel_profile=_profile_from_row(row),
        scope_id=str(row["scope_id"]), channel_id=row["channel_id"],
        conversation_id=row["conversation_id"], external_message_id=str(row["external_message_id"]),
        canonical_message_id=row["canonical_message_id"], sender_id=str(row["sender_id"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]), text=str(row["text"]),
        reply_to_message_id=row["reply_to_message_id"], decision=decision,
        advisory=_advisory_from_row(row), corrections=corrections,
        accepted_correction=accepted, context_evidence=context,
    )


def _advisory_from_row(row: sqlite3.Row) -> AdvisoryEvidence:
    disagreement = row["advisory_disagrees_with_local"]
    return AdvisoryEvidence(
        status=AdvisoryStatus(row["advisory_status"] or "DISABLED"),
        model=row["advisory_model"],
        flagged=None if row["advisory_flagged"] is None else bool(row["advisory_flagged"]),
        scores=json.loads(row["advisory_scores_json"] or "{}"),
        categories=json.loads(row["advisory_categories_json"] or "{}"),
        error_code=row["advisory_error_code"], latency_ms=row["advisory_latency_ms"],
        disagrees_with_local=None if disagreement is None else bool(disagreement),
    )


def _list_review_items(path: Path, limit: int) -> list[ReviewItem]:
    with _connect(path) as connection:
        rows = connection.execute(
            """SELECT e.event_id,e.occurred_at,e.platform,e.channel_profile,
                      d.semantic_label,d.message_action,d.review_priority,d.reason_codes_json,
                      d.incident_id FROM moderation_events e
               JOIN decision_evidence d ON d.event_id=e.event_id
               LEFT JOIN accepted_corrections a ON a.event_id=e.event_id
               WHERE e.status='FINAL' AND d.review_priority!='NONE' AND a.event_id IS NULL
               ORDER BY CASE d.review_priority WHEN 'URGENT' THEN 0 ELSE 1 END,e.occurred_at ASC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [_review_item(row) for row in rows]



def _history_filter_params(history_filter: DecisionHistoryFilter) -> tuple[str, ...]:
    # Bound scalar values; never interpolate caller-derived SQL identifiers.
    return (history_filter.value,) * 6


def _history_anchor(
    connection: sqlite3.Connection, cursor: str, history_filter: DecisionHistoryFilter,
) -> sqlite3.Row:
    row = connection.execute(
        """SELECT e.finalized_at,e.event_id,d.message_action,
                  d.review_priority,d.ingestion_status,
                  (a.event_id IS NOT NULL) AS corrected
           FROM moderation_events e
           JOIN decision_evidence d ON d.event_id=e.event_id
           LEFT JOIN accepted_corrections a ON a.event_id=e.event_id
           WHERE e.event_id=? AND e.status='FINAL'""",
        (cursor,),
    ).fetchone()
    if row is None or not _history_filter_matches(row, history_filter):
        raise EventNotFound(cursor)
    return cast(sqlite3.Row, row)


def _history_filter_matches(
    row: sqlite3.Row, history_filter: DecisionHistoryFilter,
) -> bool:
    match history_filter:
        case DecisionHistoryFilter.ALL:
            return True
        case DecisionHistoryFilter.ALLOWED:
            return str(row["message_action"]) == "ALLOW" and str(row["ingestion_status"]) == "INGESTED"
        case DecisionHistoryFilter.BLOCKED:
            return str(row["message_action"]) == "BLOCK"
        case DecisionHistoryFilter.REVIEW:
            return str(row["review_priority"]) != "NONE"
        case DecisionHistoryFilter.FAIL_OPEN:
            return str(row["ingestion_status"]) == "FAIL_OPEN"
        case DecisionHistoryFilter.CORRECTED:
            return bool(row["corrected"])
    return False


def _history_rows(
    connection: sqlite3.Connection, limit: int,
    history_filter: DecisionHistoryFilter, anchor: sqlite3.Row | None,
) -> list[sqlite3.Row]:
    cutoff = anchor["finalized_at"] if anchor is not None else None
    after_id = anchor["event_id"] if anchor is not None else None
    return connection.execute(
        """SELECT e.event_id,e.occurred_at,e.finalized_at,
                  e.platform,e.channel_profile,e.degraded,
                  d.ingestion_status,d.message_action,d.semantic_label,
                  d.review_priority,d.reason_codes_json,
                  d.local_model_version,d.policy_version,
                  (a.event_id IS NOT NULL) AS corrected
           FROM moderation_events e
           JOIN decision_evidence d ON d.event_id=e.event_id
           LEFT JOIN accepted_corrections a ON a.event_id=e.event_id
           WHERE e.status='FINAL'
             AND (
               ?='all'
               OR (?='allowed' AND d.message_action='ALLOW' AND d.ingestion_status='INGESTED')
               OR (?='blocked' AND d.message_action='BLOCK')
               OR (?='review' AND d.review_priority!='NONE')
               OR (?='fail_open' AND d.ingestion_status='FAIL_OPEN')
               OR (?='corrected' AND a.event_id IS NOT NULL)
             )
             AND (? IS NULL OR (e.finalized_at,e.event_id) < (?,?))
           ORDER BY e.finalized_at DESC,e.event_id DESC
           LIMIT ?""",
        (*_history_filter_params(history_filter), cutoff, cutoff, after_id, limit + 1),
    ).fetchall()


def _list_decisions(
    path: Path, limit: int, cursor: str | None, history_filter: DecisionHistoryFilter,
) -> DecisionHistoryPage:
    """Paginate durable decisions; filter values stay bound in fixed SQL."""
    if not 1 <= limit <= 250:
        raise ValueError("invalid page size")
    with _connect(path) as connection:
        anchor = _history_anchor(connection, cursor, history_filter) if cursor else None
        rows = _history_rows(connection, limit, history_filter, anchor)
    records = rows[:limit]
    return DecisionHistoryPage(
        items=[_decision_history_item(row) for row in records],
        next_cursor=str(records[-1]["event_id"]) if len(rows) > limit else None,
    )


def _decision_history_item(row: sqlite3.Row) -> DecisionHistoryItem:
    return DecisionHistoryItem(
        event_id=str(row["event_id"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        finalized_at=datetime.fromisoformat(row["finalized_at"]),
        platform=Platform(row["platform"]),
        channel_profile=_profile_from_row(row),
        ingestion_status=IngestionStatus(row["ingestion_status"]),
        message_action=MessageAction(row["message_action"]),
        semantic_label=Label(row["semantic_label"]),
        review_priority=ReviewPriority(row["review_priority"]),
        reason_codes=json.loads(row["reason_codes_json"]),
        local_model_version=str(row["local_model_version"]),
        policy_version=str(row["policy_version"]),
        degraded=bool(row["degraded"]),
        corrected=bool(row["corrected"]),
    )


def _create_correction(
    path: Path,
    request: CorrectionRequest,
    admin_override: bool,
) -> CorrectionResponse:
    corrected_json = _json(request.corrected.model_dump(mode="json"))
    correction_hash = hashlib.sha256(corrected_json.encode()).hexdigest()
    now = _utc_now()
    with _connect(path) as connection:
        _require_final_event(connection, request.event_id)
        _guard_existing_correction(connection, request.event_id, correction_hash, admin_override)
        proposal = _find_or_create_proposal(
            connection, request, correction_hash, corrected_json, now
        )
        _guard_rejected_proposal(proposal, admin_override)
        _record_vote(
            connection,
            str(proposal["proposal_id"]),
            request.reviewer_id,
            request.authority,
            CorrectionVote.APPROVE,
            now,
        )
        _accept_if_ready(
            connection, str(proposal["proposal_id"]), request.event_id, admin_override, now
        )
        refreshed = _proposal_row(connection, str(proposal["proposal_id"]))
        assert refreshed is not None
        return _correction_response(connection, refreshed)


def _reject_correction(
    path: Path,
    proposal_id: str,
    request: CorrectionRejectRequest,
    admin_override: bool,
) -> CorrectionResponse:
    now = _utc_now()
    with _connect(path) as connection:
        proposal = _proposal_row(connection, proposal_id)
        if proposal is None:
            raise ProposalNotFound(proposal_id)
        if proposal["status"] == CorrectionStatus.ACCEPTED.value and not admin_override:
            raise DecisionConflict("accepted correction requires Admin+ to reverse")
        _record_vote(
            connection,
            proposal_id,
            request.reviewer_id,
            request.authority,
            CorrectionVote.REJECT,
            now,
        )
        _reject_if_ready(connection, proposal_id, admin_override, now)
        refreshed = _proposal_row(connection, proposal_id)
        assert refreshed is not None
        return _correction_response(connection, refreshed)


def _guard_existing_correction(
    connection: sqlite3.Connection,
    event_id: str,
    correction_hash: str,
    admin_override: bool,
) -> None:
    accepted = connection.execute(
        """SELECT p.correction_hash FROM accepted_corrections a
           JOIN correction_proposals p ON p.proposal_id=a.proposal_id WHERE a.event_id=?""",
        (event_id,),
    ).fetchone()
    if (
        accepted is not None
        and accepted["correction_hash"] != correction_hash
        and not admin_override
    ):
        raise DecisionConflict("event already has a different accepted correction")


def _guard_rejected_proposal(row: sqlite3.Row, admin_override: bool) -> None:
    if row["status"] == CorrectionStatus.REJECTED.value and not admin_override:
        raise DecisionConflict("matching correction proposal was rejected")


def _find_or_create_proposal(
    connection: sqlite3.Connection,
    request: CorrectionRequest,
    correction_hash: str,
    corrected_json: str,
    now: str,
) -> sqlite3.Row:
    row = cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM correction_proposals WHERE event_id=? AND correction_hash=?",
            (request.event_id, correction_hash),
        ).fetchone(),
    )
    if row is not None:
        return row
    proposal_id = str(uuid4())
    connection.execute(
        """INSERT INTO correction_proposals(
          proposal_id,event_id,correction_hash,corrected_json,note,status,created_at
        ) VALUES(?,?,?,?,?,?,?)""",
        (
            proposal_id, request.event_id, correction_hash, corrected_json, request.note,
            CorrectionStatus.PENDING_CONFIRMATION.value, now,
        ),
    )
    created = _proposal_row(connection, proposal_id)
    assert created is not None
    return created


def _record_vote(
    connection: sqlite3.Connection,
    proposal_id: str,
    reviewer_id: str,
    authority: CorrectionAuthority,
    vote: CorrectionVote,
    now: str,
) -> None:
    existing = connection.execute(
        "SELECT vote FROM correction_votes WHERE proposal_id=? AND reviewer_id=?",
        (proposal_id, reviewer_id),
    ).fetchone()
    if existing is not None:
        if existing["vote"] != vote.value:
            raise DecisionConflict("reviewer already cast the opposite vote")
        return
    connection.execute(
        """INSERT INTO correction_votes(proposal_id,reviewer_id,authority,vote,created_at)
           VALUES(?,?,?,?,?)""",
        (proposal_id, reviewer_id, authority.value, vote.value, now),
    )


def _accept_if_ready(
    connection: sqlite3.Connection,
    proposal_id: str,
    event_id: str,
    admin_override: bool,
    now: str,
) -> None:
    approvals, _ = _vote_counts(connection, proposal_id)
    if not admin_override and approvals < 2:
        return
    connection.execute(
        "UPDATE correction_proposals SET status=?,resolved_at=? WHERE proposal_id=?",
        (CorrectionStatus.ACCEPTED.value, now, proposal_id),
    )
    connection.execute(
        """INSERT INTO accepted_corrections(event_id,proposal_id,accepted_at) VALUES(?,?,?)
           ON CONFLICT(event_id) DO UPDATE SET proposal_id=excluded.proposal_id,
           accepted_at=excluded.accepted_at""",
        (event_id, proposal_id, now),
    )


def _reject_if_ready(
    connection: sqlite3.Connection,
    proposal_id: str,
    admin_override: bool,
    now: str,
) -> None:
    _, rejections = _vote_counts(connection, proposal_id)
    if not admin_override and rejections < 2:
        return
    connection.execute(
        "UPDATE correction_proposals SET status=?,resolved_at=? WHERE proposal_id=?",
        (CorrectionStatus.REJECTED.value, now, proposal_id),
    )
    connection.execute("DELETE FROM accepted_corrections WHERE proposal_id=?", (proposal_id,))


def _proposal_row(connection: sqlite3.Connection, proposal_id: str) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM correction_proposals WHERE proposal_id=?",
            (proposal_id,),
        ).fetchone(),
    )


def _vote_counts(connection: sqlite3.Connection, proposal_id: str) -> tuple[int, int]:
    rows = connection.execute(
        "SELECT vote,COUNT(*) AS total FROM correction_votes WHERE proposal_id=? GROUP BY vote",
        (proposal_id,),
    ).fetchall()
    counts = {str(row["vote"]): int(row["total"]) for row in rows}
    return counts.get(CorrectionVote.APPROVE.value, 0), counts.get(CorrectionVote.REJECT.value, 0)


def _correction_response(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
) -> CorrectionResponse:
    approvals, rejections = _vote_counts(connection, str(row["proposal_id"]))
    return CorrectionResponse(
        proposal_id=str(row["proposal_id"]), event_id=str(row["event_id"]),
        status=CorrectionStatus(row["status"]),
        corrected=CorrectionDecision.model_validate(json.loads(row["corrected_json"])),
        approvals=approvals, rejections=rejections,
        created_at=datetime.fromisoformat(row["created_at"]),
        resolved_at=(
            None if row["resolved_at"] is None else datetime.fromisoformat(row["resolved_at"])
        ),
    )


def _corrections_for_event(
    connection: sqlite3.Connection,
    event_id: str,
) -> list[CorrectionResponse]:
    rows = connection.execute(
        "SELECT * FROM correction_proposals WHERE event_id=? ORDER BY created_at ASC",
        (event_id,),
    ).fetchall()
    return [_correction_response(connection, row) for row in rows]


def _accepted_correction(
    connection: sqlite3.Connection,
    event_id: str,
) -> CorrectionResponse | None:
    row = connection.execute(
        """SELECT p.* FROM accepted_corrections a
           JOIN correction_proposals p ON p.proposal_id=a.proposal_id WHERE a.event_id=?""",
        (event_id,),
    ).fetchone()
    return None if row is None else _correction_response(connection, row)


def _require_final_event(connection: sqlite3.Connection, event_id: str) -> None:
    row = connection.execute(
        "SELECT status FROM moderation_events WHERE event_id=?", (event_id,)
    ).fetchone()
    if row is None or row["status"] != "FINAL":
        raise EventNotFound(event_id)


def _save_advisory(path: Path, event_id: str, evidence: AdvisoryEvidence) -> None:
    with _connect(path) as connection:
        disagreement = _advisory_disagreement(connection, event_id, evidence)
        cursor = connection.execute(
            """UPDATE advisory_results SET status=?,model=?,flagged=?,scores_json=?,
               categories_json=?,error_code=?,latency_ms=?,disagrees_with_local=?,updated_at=?
               WHERE event_id=?""",
            (
                evidence.status.value, evidence.model,
                None if evidence.flagged is None else int(evidence.flagged),
                _json(evidence.scores), _json(evidence.categories), evidence.error_code,
                evidence.latency_ms, disagreement, _utc_now(), event_id,
            ),
        )
        if cursor.rowcount != 1:
            raise EventNotFound(event_id)


def _advisory_disagreement(
    connection: sqlite3.Connection,
    event_id: str,
    evidence: AdvisoryEvidence,
) -> int | None:
    if evidence.flagged is None:
        return None
    row = connection.execute(
        """SELECT COALESCE(d.message_action,e.action) AS message_action FROM moderation_events e
           LEFT JOIN decision_evidence d ON d.event_id=e.event_id WHERE e.event_id=?""",
        (event_id,),
    ).fetchone()
    if row is None or row["message_action"] is None:
        return None
    local_flagged = _legacy_action(str(row["message_action"])) == MessageAction.BLOCK.value
    return int(bool(evidence.flagged) != local_flagged)


def _load_recent_context(
    path: Path,
    window_seconds: int,
    limit: int,
) -> tuple[ContextMessage, ...]:
    cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)
    with _connect(path) as connection:
        rows = connection.execute(
            """SELECT * FROM moderation_events WHERE status='FINAL' AND channel_profile IS NOT NULL
               AND occurred_at>=? ORDER BY occurred_at DESC LIMIT ?""",
            (cutoff.isoformat(), limit),
        ).fetchall()
    messages = [_context_message_from_row(row) for row in reversed(rows)]
    return tuple(item for item in messages if not item.channel_profile.exempt)


def _load_memory_snapshot(
    path: Path,
    current: ContextMessage,
    limit: int,
) -> MemorySnapshot:
    subject_ids = [current.sender_id]
    if current.sender_identity_id:
        subject_ids.append(current.sender_identity_id)
    targets = _memory_targets(current)
    now = _utc_now()
    with _connect(path) as connection:
        punishment = _load_punishment_memory(
            connection, subject_ids, current.platform, targets, now, limit
        )
        safety = _load_safety_memory(connection, subject_ids, now, limit)
    return MemorySnapshot(tuple(punishment), tuple(safety))


def _memory_targets(current: ContextMessage) -> set[str]:
    return {
        *current.recipient_ids, *current.target_ids,
        *current.recipient_identity_ids, *current.target_identity_ids,
    }


def _load_punishment_memory(
    connection: sqlite3.Connection,
    subject_ids: list[str],
    platform: Platform,
    targets: set[str],
    now: str,
    limit: int,
) -> list[MemoryFact]:
    placeholders = ",".join("?" for _ in subject_ids)
    rows = connection.execute(
        f"""SELECT * FROM moderation_memory WHERE platform=? AND subject_id IN ({placeholders})
            AND (expires_at IS NULL OR expires_at>?) ORDER BY created_at DESC LIMIT ?""",
        (platform.value, *subject_ids, now, limit),
    ).fetchall()
    return [
        _memory_fact(row) for row in rows
        if row["target_id"] is None or str(row["target_id"]) in targets
    ]


def _load_safety_memory(
    connection: sqlite3.Connection,
    subject_ids: list[str],
    now: str,
    limit: int,
) -> list[SafetyMemoryFact]:
    placeholders = ",".join("?" for _ in subject_ids)
    rows = connection.execute(
        f"""SELECT * FROM safety_memory WHERE subject_id IN ({placeholders})
            AND (expires_at IS NULL OR expires_at>?) ORDER BY created_at DESC LIMIT ?""",
        (*subject_ids, now, limit),
    ).fetchall()
    return [_safety_memory_fact(row) for row in rows]


def _save_memory_fact(path: Path, fact: MemoryFact) -> None:
    with _connect(path) as connection:
        connection.execute(
            """INSERT INTO moderation_memory(
              memory_id,kind,subject_id,target_id,platform,payload_json,confidence,source,
              confirmed,created_at,updated_at,expires_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_id) DO UPDATE SET
              kind=excluded.kind,target_id=excluded.target_id,payload_json=excluded.payload_json,
              confidence=excluded.confidence,source=excluded.source,confirmed=excluded.confirmed,
              updated_at=excluded.updated_at,expires_at=excluded.expires_at""",
            _memory_values(fact),
        )


def _memory_values(fact: MemoryFact) -> tuple[object, ...]:
    return (
        fact.memory_id, fact.kind.value, fact.subject_id, fact.target_id, fact.platform.value,
        _json(fact.payload), fact.confidence, fact.source, int(fact.confirmed),
        fact.created_at.isoformat(), _utc_now(),
        None if fact.expires_at is None else fact.expires_at.isoformat(),
    )


def _save_safety_memory_fact(path: Path, fact: SafetyMemoryFact) -> None:
    with _connect(path) as connection:
        connection.execute(
            """INSERT INTO safety_memory(
              memory_id,kind,subject_id,payload_json,confidence,source,
              created_at,updated_at,expires_at
            ) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_id) DO UPDATE SET
              kind=excluded.kind,payload_json=excluded.payload_json,confidence=excluded.confidence,
              source=excluded.source,updated_at=excluded.updated_at,
              expires_at=excluded.expires_at""",
            (
                fact.memory_id, fact.kind.value, fact.subject_id, _json(fact.payload),
                fact.confidence, fact.source, fact.created_at.isoformat(), _utc_now(),
                None if fact.expires_at is None else fact.expires_at.isoformat(),
            ),
        )


def _message_ref(row: sqlite3.Row) -> MessageRef:
    return MessageRef(
        platform=Platform(row["platform"]), scope_id=str(row["scope_id"]),
        channel_id=row["channel_id"], external_message_id=str(row["external_message_id"]),
    )


def _context_evidence(row: sqlite3.Row) -> ContextEvidence:
    return ContextEvidence(
        event_id=str(row["event_id"]), message=_message_ref(row),
        sender_id=str(row["sender_id"]), occurred_at=datetime.fromisoformat(row["occurred_at"]),
        text=str(row["text"]),
    )


def _review_item(row: sqlite3.Row) -> ReviewItem:
    return ReviewItem(
        event_id=str(row["event_id"]), occurred_at=datetime.fromisoformat(row["occurred_at"]),
        platform=Platform(row["platform"]), channel_profile=_profile_from_row(row),
        semantic_label=Label(row["semantic_label"]),
        message_action=MessageAction(row["message_action"]),
        review_priority=ReviewPriority(row["review_priority"]),
        reason_codes=json.loads(row["reason_codes_json"]), incident_id=row["incident_id"],
    )


def _profile_from_row(row: sqlite3.Row) -> ChannelProfile:
    value = row["channel_profile"]
    if value is not None:
        return ChannelProfile(value)
    if row["platform"] == Platform.MINECRAFT.value:
        return ChannelProfile.MINECRAFT_PUBLIC
    return ChannelProfile.DISCORD_GENERAL


def _context_message_from_row(row: sqlite3.Row) -> ContextMessage:
    return ContextMessage(
        event_id=str(row["event_id"]), platform=Platform(row["platform"]),
        channel_profile=_profile_from_row(row), scope_id=str(row["scope_id"]),
        channel_id=row["channel_id"], conversation_id=row["conversation_id"],
        external_message_id=str(row["external_message_id"]),
        canonical_message_id=row["canonical_message_id"],
        sender_id=str(row["sender_id"]), sender_identity_id=row["sender_identity_id"],
        recipient_ids=tuple(json.loads(row["recipient_ids_json"] or "[]")),
        recipient_identity_ids=tuple(json.loads(row["recipient_identity_ids_json"] or "[]")),
        target_ids=tuple(json.loads(row["target_ids_json"] or "[]")),
        target_identity_ids=tuple(json.loads(row["target_identity_ids_json"] or "[]")),
        occurred_at=datetime.fromisoformat(row["occurred_at"]), text=str(row["text"]),
        reply_to_message_id=row["reply_to_message_id"],
    )


def _memory_fact(row: sqlite3.Row) -> MemoryFact:
    return MemoryFact(
        memory_id=str(row["memory_id"]), kind=MemoryKind(row["kind"]),
        subject_id=str(row["subject_id"]), target_id=row["target_id"],
        platform=Platform(row["platform"]), payload=json.loads(row["payload_json"]),
        confidence=float(row["confidence"]), source=str(row["source"]),
        confirmed=bool(row["confirmed"]), created_at=datetime.fromisoformat(row["created_at"]),
        expires_at=None if row["expires_at"] is None else datetime.fromisoformat(row["expires_at"]),
    )


def _safety_memory_fact(row: sqlite3.Row) -> SafetyMemoryFact:
    return SafetyMemoryFact(
        memory_id=str(row["memory_id"]), kind=SafetyMemoryKind(row["kind"]),
        subject_id=str(row["subject_id"]), payload=json.loads(row["payload_json"]),
        confidence=float(row["confidence"]), source=str(row["source"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        expires_at=None if row["expires_at"] is None else datetime.fromisoformat(row["expires_at"]),
    )


def _legacy_action(value: str | None) -> str:
    return MessageAction.BLOCK.value if value == "BLOCK" else MessageAction.ALLOW.value


def _external_key(request: ModerationRequest) -> str:
    return _json((request.platform.value, request.scope_id, request.external_message_id))


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

def _list_support_context(
    path: Path,
    subject_id: str,
    limit: int,
) -> list[SupportContextDecision]:
    candidate_limit = min(250, max(limit, limit * 5))
    with _connect(path) as connection:
        rows = connection.execute(
            """SELECT e.event_id,e.occurred_at,e.platform,e.channel_profile,
                      d.semantic_label,d.message_action,d.review_priority,
                      d.strike_recommendation,d.containment,d.support_flow,
                      d.reason_codes_json
               FROM moderation_events e
               JOIN decision_evidence d ON d.event_id=e.event_id
               WHERE e.status='FINAL'
                 AND e.sender_identity_id=?
                 AND d.ingestion_status='INGESTED'
                 AND (
                   e.channel_profile IS NULL OR
                   e.channel_profile NOT IN (
                     'discord_staff_exempt',
                     'discord_ticket_exempt',
                     'discord_configured_exempt'
                   )
                 )
               ORDER BY e.occurred_at DESC
               LIMIT ?""",
            (subject_id, candidate_limit),
        ).fetchall()

        decisions: list[SupportContextDecision] = []
        for row in rows:
            accepted = _accepted_correction(connection, str(row["event_id"]))
            decision = _support_context_decision(row, accepted)
            if not _meaningful_support_decision(decision):
                continue
            decisions.append(decision)
            if len(decisions) >= limit:
                break
        return decisions


def _support_context_decision(
    row: sqlite3.Row,
    accepted: CorrectionResponse | None,
) -> SupportContextDecision:
    if accepted is not None:
        corrected = accepted.corrected
        return SupportContextDecision(
            event_id=str(row["event_id"]),
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            platform=Platform(row["platform"]),
            semantic_label=corrected.semantic_label,
            message_action=corrected.message_action,
            review_priority=corrected.review_priority,
            strike_recommendation=corrected.strike_recommendation,
            containment=corrected.containment,
            support_flow=corrected.support_flow,
            reason_codes=list(corrected.reason_codes),
            decision_source=SupportDecisionSource.ACCEPTED_CORRECTION,
        )

    return SupportContextDecision(
        event_id=str(row["event_id"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        platform=Platform(row["platform"]),
        semantic_label=Label(row["semantic_label"]),
        message_action=MessageAction(row["message_action"]),
        review_priority=ReviewPriority(row["review_priority"]),
        strike_recommendation=StrikeRecommendation(row["strike_recommendation"]),
        containment=Containment(row["containment"]),
        support_flow=SupportFlow(row["support_flow"]),
        reason_codes=json.loads(row["reason_codes_json"] or "[]"),
        decision_source=SupportDecisionSource.AI,
    )


def _meaningful_support_decision(decision: SupportContextDecision) -> bool:
    return any(
        (
            decision.semantic_label is not Label.SAFE,
            decision.message_action is not MessageAction.ALLOW,
            decision.review_priority is not ReviewPriority.NONE,
            decision.strike_recommendation is not StrikeRecommendation.NONE,
            decision.containment is not Containment.NONE,
            decision.support_flow is not SupportFlow.NONE,
        )
    )

