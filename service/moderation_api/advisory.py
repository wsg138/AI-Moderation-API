from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from .models import AdvisoryEvidence, AdvisoryStatus
from .storage import ModerationStore

logger = logging.getLogger(__name__)


class AdvisoryClient(Protocol):
    async def evaluate(self, text: str) -> AdvisoryEvidence: ...

    async def close(self) -> None: ...


class DisabledAdvisoryClient:
    async def evaluate(self, text: str) -> AdvisoryEvidence:
        del text
        return AdvisoryEvidence(status=AdvisoryStatus.DISABLED)

    async def close(self) -> None:
        return None


class OpenAIAdvisoryClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_ms: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url="https://api.openai.com",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_ms / 1000,
        )

    async def evaluate(self, text: str) -> AdvisoryEvidence:
        started = time.perf_counter()
        response = await self._client.post(
            "/v1/moderations",
            json={"model": self._model, "input": text},
        )
        response.raise_for_status()
        payload = response.json()
        result = payload["results"][0]
        return AdvisoryEvidence(
            status=AdvisoryStatus.COMPLETE,
            model=str(payload.get("model", self._model)),
            flagged=bool(result["flagged"]),
            scores={key: float(value) for key, value in result.get("category_scores", {}).items()},
            categories={key: bool(value) for key, value in result.get("categories", {}).items()},
            latency_ms=_elapsed_ms(started),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


@dataclass(frozen=True, slots=True)
class AdvisoryJob:
    event_id: str
    text: str


class AdvisoryDispatcher:
    def __init__(
        self,
        store: ModerationStore,
        client: AdvisoryClient,
        enabled: bool,
        queue_size: int,
        workers: int,
        timeout_ms: int,
    ) -> None:
        self._store = store
        self._client = client
        self._enabled = enabled
        self._queue: asyncio.Queue[AdvisoryJob] = asyncio.Queue(maxsize=queue_size)
        self._worker_count = workers
        self._timeout_seconds = timeout_ms / 1000
        self._tasks: list[asyncio.Task[None]] = []
        self._reserved_slots = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def queue_depth(self) -> int:
        return self._reserved_slots

    @property
    def queue_capacity(self) -> int:
        return self._queue.maxsize

    async def start(self) -> None:
        if not self._enabled or self._tasks:
            return
        self._tasks = [asyncio.create_task(self._worker()) for _ in range(self._worker_count)]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        await self._client.close()

    def reserve(self) -> AdvisoryStatus:
        if not self._enabled:
            return AdvisoryStatus.DISABLED
        if self._reserved_slots >= self._queue.maxsize:
            return AdvisoryStatus.QUEUE_SATURATED
        self._reserved_slots += 1
        return AdvisoryStatus.QUEUED

    def commit(self, event_id: str, text: str) -> None:
        self._queue.put_nowait(AdvisoryJob(event_id, text))

    def release(self) -> None:
        if self._reserved_slots > 0:
            self._reserved_slots -= 1

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            self.release()
            try:
                await self._process_job(job)
            except Exception:
                logger.exception("advisory worker job failed", extra={"event_id": job.event_id})
            finally:
                self._queue.task_done()

    async def _process_job(self, job: AdvisoryJob) -> None:
        await self._store.save_advisory(
            job.event_id,
            AdvisoryEvidence(status=AdvisoryStatus.PROCESSING),
        )
        evidence = await self._evaluate(job.text)
        await self._store.save_advisory(job.event_id, evidence)

    async def _evaluate(self, text: str) -> AdvisoryEvidence:
        started = time.perf_counter()
        try:
            return await asyncio.wait_for(self._client.evaluate(text), self._timeout_seconds)
        except TimeoutError:
            return AdvisoryEvidence(
                status=AdvisoryStatus.ERROR,
                error_code="advisory_timeout",
                latency_ms=_elapsed_ms(started),
            )
        except Exception as exc:  # advisory failures are deliberately isolated
            return AdvisoryEvidence(
                status=AdvisoryStatus.ERROR,
                error_code=f"advisory_error:{type(exc).__name__}",
                latency_ms=_elapsed_ms(started),
            )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))
