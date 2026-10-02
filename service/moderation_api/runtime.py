from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from .advisory import AdvisoryDispatcher
from .auth import Principal
from .classifier import LocalClassifier
from .config import Settings
from .context import RollingContextStore
from .models import (
    AdvisoryStatus,
    ClassificationInput,
    ClassificationResult,
    Containment,
    ContextMessage,
    IncidentSignal,
    IncidentSummary,
    IngestionStatus,
    Label,
    MemorySnapshot,
    MessageAction,
    MessageRef,
    ModerationRequest,
    ModerationResponse,
    ReviewPriority,
    StrikeRecommendation,
    SupportFlow,
)
from .storage import EventConflict, EventInProgress, ModerationStore, Reservation


class RequestQueueFull(RuntimeError):
    pass


class ProcessingTimeout(RuntimeError):
    pass


@dataclass(slots=True)
class _RequestJob:
    request: ModerationRequest
    principal: Principal
    future: asyncio.Future[ModerationResponse]


@dataclass(frozen=True, slots=True)
class _PreparedDecision:
    response: ModerationResponse
    evidence_event_ids: tuple[str, ...]
    related_event_ids: tuple[str, ...]
    incident_signal: IncidentSignal | None


class ModerationRuntime:
    def __init__(
        self,
        settings: Settings,
        store: ModerationStore,
        context: RollingContextStore,
        classifier: LocalClassifier,
        advisory: AdvisoryDispatcher,
    ) -> None:
        self._settings = settings
        self._store = store
        self._context = context
        self._classifier = classifier
        self._advisory = advisory
        self._queues = tuple(asyncio.Queue[_RequestJob]() for _ in range(settings.request_workers))
        self._tasks: list[asyncio.Task[None]] = []
        self._rehydrated_context_messages = 0
        self._context_ready = True

    @property
    def queue_depth(self) -> int:
        return sum(queue.qsize() for queue in self._queues)

    @property
    def queue_capacity(self) -> int:
        return self._settings.request_queue_size

    @property
    def worker_count(self) -> int:
        return self._settings.request_workers

    @property
    def advisory_queue_depth(self) -> int:
        return self._advisory.queue_depth

    @property
    def advisory_queue_capacity(self) -> int:
        return self._advisory.queue_capacity

    @property
    def rehydrated_context_messages(self) -> int:
        return self._rehydrated_context_messages

    @property
    def context_ready(self) -> bool:
        return self._context_ready

    def classifier_health(self) -> dict[str, object]:
        try:
            return self._classifier.health()
        except Exception:
            return {"ready": False, "mode": "error", "model_version": None}

    async def start(self) -> None:
        if self._tasks:
            return
        await self._rehydrate_context()
        await self._advisory.start()
        self._tasks = [asyncio.create_task(self._worker(queue)) for queue in self._queues]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        await self._advisory.stop()
        self._reject_pending()

    async def submit(self, request: ModerationRequest, principal: Principal) -> ModerationResponse:
        if request.channel_profile.exempt:
            return self._exempt_response()
        if self.queue_depth >= self.queue_capacity:
            raise RequestQueueFull("moderation queue is saturated")
        future: asyncio.Future[ModerationResponse] = asyncio.get_running_loop().create_future()
        self._queue_for(request).put_nowait(_RequestJob(request, principal, future))
        return await self._wait_for_response(future)

    async def _wait_for_response(
        self,
        future: asyncio.Future[ModerationResponse],
    ) -> ModerationResponse:
        try:
            return await asyncio.wait_for(
                asyncio.shield(future),
                timeout=self._settings.request_timeout_ms / 1000,
            )
        except TimeoutError as exc:
            raise ProcessingTimeout("moderation deadline exceeded") from exc

    async def _rehydrate_context(self) -> None:
        try:
            messages = await self._store.load_recent_context(
                self._settings.context_window_seconds,
                self._settings.context_rehydrate_limit,
            )
            self._rehydrated_context_messages = await self._context.rehydrate(messages)
            self._context_ready = True
        except Exception:
            self._rehydrated_context_messages = 0
            self._context_ready = False

    async def _worker(self, queue: asyncio.Queue[_RequestJob]) -> None:
        while True:
            job = await queue.get()
            try:
                result = await self._process(job.request, job.principal)
                if not job.future.done():
                    job.future.set_result(result)
            except (EventConflict, EventInProgress) as exc:
                if not job.future.done():
                    job.future.set_exception(exc)
            except Exception:
                if not job.future.done():
                    job.future.set_result(
                        self._fail_open(None, time.perf_counter(), "runtime_error")
                    )
            finally:
                queue.task_done()

    def _queue_for(self, request: ModerationRequest) -> asyncio.Queue[_RequestJob]:
        key: tuple[object, ...]
        if request.sender_identity_id:
            key = ("identity", request.sender_identity_id)
        else:
            key = (request.platform.value, request.scope_id, request.sender_id)
        encoded = json.dumps(key, separators=(",", ":")).encode()
        digest = hashlib.blake2s(encoded, digest_size=4).digest()
        return self._queues[int.from_bytes(digest, "big") % len(self._queues)]

    async def _process(
        self,
        request: ModerationRequest,
        principal: Principal,
    ) -> ModerationResponse:
        started = time.perf_counter()
        reservation = await self._reserve_or_fail_open(request, principal, started)
        if isinstance(reservation, ModerationResponse):
            return reservation
        if reservation.replay:
            return await self._replay_or_fail_open(reservation.event_id, started)
        return await self._classify_new(request, reservation.event_id, started)

    async def _reserve_or_fail_open(
        self,
        request: ModerationRequest,
        principal: Principal,
        started: float,
    ) -> Reservation | ModerationResponse:
        try:
            return await self._store.reserve_event(
                request,
                principal.client_id,
                _request_fingerprint(request),
                _canonical_fingerprint(request),
                AdvisoryStatus.DISABLED,
            )
        except (EventConflict, EventInProgress):
            raise
        except Exception:
            return self._fail_open(None, started, "storage_reserve_error")

    async def _classify_new(
        self,
        request: ModerationRequest,
        event_id: str,
        started: float,
    ) -> ModerationResponse:
        current = _context_message(request, event_id)
        prepared = await self._prepare_decision(current, started)
        prepared = await self._record_context_or_fail_open(current, prepared, started)
        return await self._finalize_and_dispatch(request, current, prepared, started)

    async def _prepare_decision(
        self,
        current: ContextMessage,
        started: float,
    ) -> _PreparedDecision:
        if not self._context_ready:
            return _fail_open_prepared(current, started, self._settings, "context_unavailable")
        prior = await self._context_or_fail_open(current, started)
        if isinstance(prior, _PreparedDecision):
            return prior
        memory = await self._memory_or_fail_open(current, started)
        if isinstance(memory, _PreparedDecision):
            return memory
        result = await self._classify_or_fail_open(current, prior, memory)
        return self._prepare_from_classification(current, prior, result, started)

    async def _context_or_fail_open(
        self,
        current: ContextMessage,
        started: float,
    ) -> tuple[ContextMessage, ...] | _PreparedDecision:
        try:
            return await self._context.snapshot_for(current)
        except Exception:
            self._context_ready = False
            return _fail_open_prepared(current, started, self._settings, "context_error")

    async def _memory_or_fail_open(
        self,
        current: ContextMessage,
        started: float,
    ) -> MemorySnapshot | _PreparedDecision:
        try:
            return await self._store.load_memory_snapshot(current, self._settings.memory_fact_limit)
        except Exception:
            return _fail_open_prepared(current, started, self._settings, "memory_error")

    async def _classify_or_fail_open(
        self,
        current: ContextMessage,
        prior: tuple[ContextMessage, ...],
        memory: MemorySnapshot,
    ) -> ClassificationResult:
        if self.classifier_health().get("ready") is not True:
            return _fallback_classification("classifier_not_ready")
        try:
            item = ClassificationInput(current=current, context=prior, memory=memory)
            return await asyncio.wait_for(
                self._classifier.classify(item),
                timeout=self._settings.classifier_timeout_ms / 1000,
            )
        except TimeoutError:
            return _fallback_classification("classifier_timeout")
        except Exception:
            return _fallback_classification("classifier_error")

    def _prepare_from_classification(
        self,
        current: ContextMessage,
        prior: tuple[ContextMessage, ...],
        result: ClassificationResult,
        started: float,
    ) -> _PreparedDecision:
        try:
            return _build_prepared_decision(
                current, prior, result, started, self._settings.policy_version
            )
        except Exception:
            return _fail_open_prepared(
                current, started, self._settings, "classifier_output_error"
            )

    async def _record_context_or_fail_open(
        self,
        current: ContextMessage,
        prepared: _PreparedDecision,
        started: float,
    ) -> _PreparedDecision:
        if not self._context_ready:
            return prepared
        try:
            await self._context.record(current)
            return prepared
        except Exception:
            self._context_ready = False
            return _fail_open_prepared(
                current, started, self._settings, "context_record_error"
            )

    async def _finalize_and_dispatch(
        self,
        request: ModerationRequest,
        current: ContextMessage,
        prepared: _PreparedDecision,
        started: float,
    ) -> ModerationResponse:
        advisory_status = self._advisory.reserve()
        response = prepared.response.model_copy(
            update={"advisory_status": advisory_status, "latency_ms": _elapsed_ms(started)}
        )
        saved = await self._save_decision(response, prepared, advisory_status)
        if not saved:
            await self._remove_context_safely(current.event_id)
            return self._fail_open(None, started, "storage_finalize_error")
        if advisory_status is AdvisoryStatus.QUEUED:
            self._advisory.commit(response.event_id or "", request.text)
        return response

    async def _save_decision(
        self,
        response: ModerationResponse,
        prepared: _PreparedDecision,
        advisory_status: AdvisoryStatus,
    ) -> bool:
        try:
            await self._store.finalize_event(
                response,
                prepared.evidence_event_ids,
                prepared.related_event_ids,
                prepared.incident_signal,
            )
            return True
        except Exception:
            if advisory_status is AdvisoryStatus.QUEUED:
                self._advisory.release()
            return False

    async def _remove_context_safely(self, event_id: str) -> None:
        try:
            await self._context.remove(event_id)
        except Exception:
            self._context_ready = False

    async def _replay_or_fail_open(self, event_id: str, started: float) -> ModerationResponse:
        try:
            response = await self._store.load_decision(event_id)
            return response.model_copy(update={"idempotent_replay": True})
        except Exception:
            return self._fail_open(None, started, "storage_replay_error")

    def _exempt_response(self) -> ModerationResponse:
        return ModerationResponse(
            event_id=None, ingestion_status=IngestionStatus.SKIPPED_EXEMPT,
            message_action=MessageAction.ALLOW, semantic_label=Label.SAFE,
            review_priority=ReviewPriority.NONE, strike_recommendation=StrikeRecommendation.NONE,
            containment=Containment.NONE, containment_duration_seconds=None,
            support_flow=SupportFlow.NONE, scores={}, confidence=None, rule_hits=[],
            reason_codes=["scope_exempt"], related_message_ids=[], related_messages=[],
            local_model_version="not_run", policy_version=self._settings.policy_version,
            advisory_status=AdvisoryStatus.DISABLED, latency_ms=0,
        )

    def _fail_open(
        self,
        event_id: str | None,
        started: float,
        reason: str,
    ) -> ModerationResponse:
        return _fail_open_response(event_id, started, self._settings.policy_version, reason)

    def _reject_pending(self) -> None:
        for queue in self._queues:
            while not queue.empty():
                job = queue.get_nowait()
                if not job.future.done():
                    job.future.set_exception(ProcessingTimeout("runtime stopped"))
                queue.task_done()


def _build_prepared_decision(
    current: ContextMessage,
    prior: tuple[ContextMessage, ...],
    result: ClassificationResult,
    started: float,
    policy_version: str,
) -> _PreparedDecision:
    available = {item.external_message_id: item for item in (*prior, current)}
    related = _related_context(result.related_message_ids, available)
    evidence = _evidence_context(result.evidence_event_ids, prior)
    _validate_containment(result)
    degraded = _classification_degraded(result)
    response = _classification_response(
        current, related, result, started, policy_version, degraded
    )
    related_events = tuple(dict.fromkeys((current.event_id, *(item.event_id for item in related))))
    return _PreparedDecision(
        response=response,
        evidence_event_ids=tuple(item.event_id for item in evidence),
        related_event_ids=related_events,
        incident_signal=result.incident,
    )


def _classification_response(
    current: ContextMessage,
    related: tuple[ContextMessage, ...],
    result: ClassificationResult,
    started: float,
    policy_version: str,
    degraded: bool,
) -> ModerationResponse:
    return ModerationResponse(
        event_id=current.event_id,
        ingestion_status=IngestionStatus.FAIL_OPEN if degraded else IngestionStatus.INGESTED,
        message_action=result.message_action, semantic_label=result.semantic_label,
        review_priority=result.review_priority, strike_recommendation=result.strike_recommendation,
        containment=result.containment,
        containment_duration_seconds=result.containment_duration_seconds,
        support_flow=result.support_flow, scores=_safe_scores(result.scores),
        confidence=_safe_confidence(result.confidence), rule_hits=list(result.rule_hits[:32]),
        reason_codes=list(result.reason_codes[:32]),
        related_message_ids=[item.external_message_id for item in related][:32],
        related_messages=[_message_ref(item) for item in (current, *related)][:32],
        incident=_incident_summary(result.incident), local_model_version=result.model_version,
        policy_version=policy_version, advisory_status=AdvisoryStatus.DISABLED,
        latency_ms=_elapsed_ms(started), degraded=degraded,
        fallback_state=result.reason_codes[0] if degraded and result.reason_codes else None,
    )


def _related_context(
    message_ids: tuple[str, ...],
    available: dict[str, ContextMessage],
) -> tuple[ContextMessage, ...]:
    selected = [available[item] for item in message_ids if item in available]
    unique = {item.event_id: item for item in selected}
    return tuple(unique.values())


def _evidence_context(
    event_ids: tuple[str, ...],
    prior: tuple[ContextMessage, ...],
) -> tuple[ContextMessage, ...]:
    available = {item.event_id: item for item in prior}
    return tuple(available[item] for item in event_ids if item in available)


def _incident_summary(signal: IncidentSignal | None) -> IncidentSummary | None:
    if signal is None:
        return None
    key = signal.incident_key.strip()
    if not key:
        raise ValueError("incident key must not be empty")
    return IncidentSummary(
        incident_id=str(uuid5(NAMESPACE_URL, f"enthusia-moderation:{key}")),
        kind=signal.kind, severity=max(0, min(100, signal.severity)),
        coordinated=signal.coordinated,
        participant_ids=list(dict.fromkeys(signal.participant_ids))[:64],
        target_ids=list(dict.fromkeys(signal.target_ids))[:64],
    )


def _validate_containment(result: ClassificationResult) -> None:
    duration = result.containment_duration_seconds
    if result.containment is Containment.NONE and duration is not None:
        raise ValueError("containment duration requires containment")
    if duration is not None and duration <= 0:
        raise ValueError("containment duration must be positive")


def _classification_degraded(result: ClassificationResult) -> bool:
    return bool(result.reason_codes and result.reason_codes[0].startswith("classifier_"))


def _fallback_classification(reason: str) -> ClassificationResult:
    return ClassificationResult(
        message_action=MessageAction.ALLOW, semantic_label=Label.AMBIGUOUS_REVIEW,
        review_priority=ReviewPriority.NONE, strike_recommendation=StrikeRecommendation.NONE,
        containment=Containment.NONE, containment_duration_seconds=None,
        support_flow=SupportFlow.NONE, scores={}, confidence=None, rule_hits=(),
        reason_codes=(reason,), related_message_ids=(), evidence_event_ids=(),
        model_version="unavailable",
    )


def _fail_open_prepared(
    current: ContextMessage,
    started: float,
    settings: Settings,
    reason: str,
) -> _PreparedDecision:
    return _PreparedDecision(
        response=_fail_open_response(current.event_id, started, settings.policy_version, reason),
        evidence_event_ids=(), related_event_ids=(current.event_id,), incident_signal=None,
    )


def _fail_open_response(
    event_id: str | None,
    started: float,
    policy_version: str,
    reason: str,
) -> ModerationResponse:
    return ModerationResponse(
        event_id=event_id, ingestion_status=IngestionStatus.FAIL_OPEN,
        message_action=MessageAction.ALLOW, semantic_label=Label.AMBIGUOUS_REVIEW,
        review_priority=ReviewPriority.NONE, strike_recommendation=StrikeRecommendation.NONE,
        containment=Containment.NONE, containment_duration_seconds=None,
        support_flow=SupportFlow.NONE, scores={}, confidence=None, rule_hits=[],
        reason_codes=[f"fail_open_{reason}"], related_message_ids=[], related_messages=[],
        local_model_version="unavailable", policy_version=policy_version,
        advisory_status=AdvisoryStatus.DISABLED, latency_ms=_elapsed_ms(started),
        degraded=True, fallback_state=reason,
    )


def _context_message(request: ModerationRequest, event_id: str) -> ContextMessage:
    return ContextMessage(
        event_id=event_id, platform=request.platform, channel_profile=request.channel_profile,
        scope_id=request.scope_id, channel_id=request.channel_id,
        conversation_id=request.conversation_id, external_message_id=request.external_message_id,
        canonical_message_id=request.canonical_message_id, sender_id=request.sender_id,
        sender_identity_id=request.sender_identity_id, recipient_ids=tuple(request.recipient_ids),
        recipient_identity_ids=tuple(request.recipient_identity_ids),
        target_ids=tuple(request.target_ids),
        target_identity_ids=tuple(request.target_identity_ids),
        occurred_at=request.occurred_at, text=request.text,
        reply_to_message_id=request.reply_to_message_id,
    )


def _message_ref(message: ContextMessage) -> MessageRef:
    return MessageRef(
        platform=message.platform, scope_id=message.scope_id, channel_id=message.channel_id,
        external_message_id=message.external_message_id,
    )


def _request_fingerprint(request: ModerationRequest) -> str:
    payload = request.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _canonical_fingerprint(request: ModerationRequest) -> str:
    encoded = json.dumps({"text": request.text}, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _safe_scores(scores: dict[str, float]) -> dict[str, float]:
    safe: dict[str, float] = {}
    for key, value in list(scores.items())[:32]:
        number = float(value)
        if math.isfinite(number):
            safe[str(key)[:80]] = min(1.0, max(0.0, number))
    return safe


def _safe_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return min(1.0, max(0.0, number))


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))
