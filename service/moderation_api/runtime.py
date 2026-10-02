from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from dataclasses import dataclass

from .advisory import AdvisoryDispatcher
from .auth import Principal
from .classifier import LocalClassifier
from .config import Settings
from .context import RollingContextStore
from .models import (
    Action,
    AdvisoryStatus,
    ClassificationInput,
    ClassificationResult,
    ContextMessage,
    Label,
    ModerationRequest,
    ModerationResponse,
)
from .storage import EventConflict, EventInProgress, ModerationStore


class RequestQueueFull(RuntimeError):
    pass


class ProcessingTimeout(RuntimeError):
    pass


@dataclass(slots=True)
class _RequestJob:
    request: ModerationRequest
    principal: Principal
    future: asyncio.Future[ModerationResponse]


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

    def classifier_health(self) -> dict[str, object]:
        try:
            return self._classifier.health()
        except Exception:
            return {"ready": False, "mode": "error", "model_version": None}

    async def start(self) -> None:
        if self._tasks:
            return
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
        if self.queue_depth >= self.queue_capacity:
            raise RequestQueueFull("moderation queue is saturated")
        future: asyncio.Future[ModerationResponse] = asyncio.get_running_loop().create_future()
        queue = self._queue_for(request)
        queue.put_nowait(_RequestJob(request, principal, future))
        try:
            return await asyncio.wait_for(
                asyncio.shield(future),
                timeout=self._settings.request_timeout_ms / 1000,
            )
        except TimeoutError as exc:
            raise ProcessingTimeout("moderation deadline exceeded") from exc

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
        encoded = json.dumps(_scope_key(request), separators=(",", ":")).encode()
        digest = hashlib.blake2s(encoded, digest_size=4).digest()
        index = int.from_bytes(digest, "big") % len(self._queues)
        return self._queues[index]

    async def _process(
        self,
        request: ModerationRequest,
        principal: Principal,
    ) -> ModerationResponse:
        started = time.perf_counter()
        fingerprint = _fingerprint(request)
        initial_advisory = AdvisoryStatus.DISABLED
        try:
            reservation = await self._store.reserve_event(
                request,
                principal.client_id,
                fingerprint,
                initial_advisory,
            )
        except (EventConflict, EventInProgress):
            raise
        except Exception:
            return self._fail_open(None, started, "storage_reserve_error")
        if reservation.replay:
            return await self._replay_or_fail_open(reservation.event_id, started)
        return await self._classify_new(request, reservation.event_id, started)

    async def _classify_new(
        self,
        request: ModerationRequest,
        event_id: str,
        started: float,
    ) -> ModerationResponse:
        current = _context_message(request)
        try:
            prior = await self._context.snapshot_for(current)
            await self._context.record(current)
        except Exception:
            response = self._fail_open(event_id, started, "context_error")
            return await self._finalize_and_dispatch(request, response, started)
        classification = await self._classify_or_fail_open(current, prior, started)
        try:
            response = self._response_from_classification(
                event_id, classification, prior, current, started
            )
        except Exception:
            response = self._fail_open(event_id, started, "classifier_output_error")
        return await self._finalize_and_dispatch(request, response, started)

    async def _classify_or_fail_open(
        self,
        current: ContextMessage,
        prior: tuple[ContextMessage, ...],
        started: float,
    ) -> ClassificationResult:
        if self.classifier_health().get("ready") is not True:
            return _fallback_classification("classifier_not_ready")
        try:
            return await asyncio.wait_for(
                self._classifier.classify(ClassificationInput(current=current, context=prior)),
                timeout=self._settings.classifier_timeout_ms / 1000,
            )
        except TimeoutError:
            return _fallback_classification("classifier_timeout")
        except Exception:
            return _fallback_classification("classifier_error")

    def _response_from_classification(
        self,
        event_id: str,
        result: ClassificationResult,
        prior: tuple[ContextMessage, ...],
        current: ContextMessage,
        started: float,
    ) -> ModerationResponse:
        allowed_ids = {item.external_message_id for item in prior}
        allowed_ids.add(current.external_message_id)
        related_ids = [item for item in result.related_message_ids if item in allowed_ids]
        degraded = result.reason_codes and result.reason_codes[0].startswith("classifier_")
        return ModerationResponse(
            event_id=event_id,
            action=result.action,
            label=result.label,
            scores=_safe_scores(result.scores),
            rule_hits=list(result.rule_hits[:32]),
            reason_codes=list(result.reason_codes[:32]),
            related_message_ids=related_ids[:16],
            local_model_version=result.model_version,
            policy_version=self._settings.policy_version,
            advisory_status=AdvisoryStatus.DISABLED,
            latency_ms=_elapsed_ms(started),
            degraded=bool(degraded),
            fallback_state=result.reason_codes[0] if degraded else None,
        )

    async def _finalize_and_dispatch(
        self,
        request: ModerationRequest,
        response: ModerationResponse,
        started: float,
    ) -> ModerationResponse:
        advisory_status = self._advisory.reserve()
        final_response = response.model_copy(
            update={"advisory_status": advisory_status, "latency_ms": _elapsed_ms(started)}
        )
        try:
            await self._store.finalize_event(final_response)
        except Exception:
            if advisory_status is AdvisoryStatus.QUEUED:
                self._advisory.release()
            return self._fail_open(None, started, "storage_finalize_error")
        if advisory_status is AdvisoryStatus.QUEUED:
            self._advisory.commit(response.event_id or "", request.text)
        return final_response

    async def _replay_or_fail_open(self, event_id: str, started: float) -> ModerationResponse:
        try:
            response = await self._store.load_decision(event_id)
            return response.model_copy(update={"idempotent_replay": True})
        except Exception:
            return self._fail_open(None, started, "storage_replay_error")

    def _fail_open(
        self,
        event_id: str | None,
        started: float,
        reason: str,
    ) -> ModerationResponse:
        return ModerationResponse(
            event_id=event_id,
            action=Action.ALLOW,
            label=Label.AMBIGUOUS_REVIEW,
            scores={},
            rule_hits=[],
            reason_codes=[f"fail_open_{reason}"],
            related_message_ids=[],
            local_model_version="unavailable",
            policy_version=self._settings.policy_version,
            advisory_status=AdvisoryStatus.DISABLED,
            latency_ms=_elapsed_ms(started),
            degraded=True,
            fallback_state=reason,
        )

    def _reject_pending(self) -> None:
        for queue in self._queues:
            self._reject_queue(queue)

    def _reject_queue(self, queue: asyncio.Queue[_RequestJob]) -> None:
        while not queue.empty():
            job = queue.get_nowait()
            if not job.future.done():
                job.future.set_exception(ProcessingTimeout("runtime stopped"))
            queue.task_done()


def _fallback_classification(reason: str) -> ClassificationResult:
    return ClassificationResult(
        action=Action.ALLOW,
        label=Label.AMBIGUOUS_REVIEW,
        scores={},
        rule_hits=(),
        reason_codes=(f"classifier_{reason.removeprefix('classifier_')}",),
        related_message_ids=(),
        model_version="unavailable",
    )


def _context_message(request: ModerationRequest) -> ContextMessage:
    return ContextMessage(
        platform=request.platform,
        scope_id=request.scope_id,
        channel_id=request.channel_id,
        external_message_id=request.external_message_id,
        sender_id=request.sender_id,
        occurred_at=request.occurred_at,
        text=request.text,
        reply_to_message_id=request.reply_to_message_id,
    )


def _scope_key(request: ModerationRequest) -> tuple[str, str, str | None]:
    return request.platform, request.scope_id, request.channel_id


def _fingerprint(request: ModerationRequest) -> str:
    payload = request.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _safe_scores(scores: dict[str, float]) -> dict[str, float]:
    safe: dict[str, float] = {}
    for key, value in list(scores.items())[:32]:
        number = float(value)
        if math.isfinite(number):
            safe[str(key)[:80]] = min(1.0, max(0.0, number))
    return safe


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))
