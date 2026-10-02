from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from .advisory import (
    AdvisoryClient,
    AdvisoryDispatcher,
    DisabledAdvisoryClient,
    OpenAIAdvisoryClient,
)
from .auth import Authenticator, Principal, permission_dependency
from .classifier import LocalClassifier, StubClassifier
from .config import Settings
from .context import RollingContextStore
from .models import (
    EventDetails,
    HealthResponse,
    ModerationRequest,
    ModerationResponse,
    ReviewRequest,
    ReviewResponse,
)
from .runtime import ModerationRuntime, ProcessingTimeout, RequestQueueFull
from .storage import EventConflict, EventInProgress, EventNotFound, ModerationStore


def create_app(
    settings: Settings | None = None,
    classifier: LocalClassifier | None = None,
    advisory_client: AdvisoryClient | None = None,
) -> FastAPI:
    config = settings or Settings.from_env()
    store = ModerationStore(config.database_path)
    context = _build_context(config)
    local_classifier = classifier or StubClassifier()
    advisory, advisory_enabled = _build_advisory(config, store, advisory_client)
    runtime = ModerationRuntime(config, store, context, local_classifier, advisory)
    authenticator = Authenticator(config.clients)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await store.initialize()
        await runtime.start()
        app.state.runtime = runtime
        app.state.store = store
        yield
        await runtime.stop()

    app = FastAPI(title="Enthusia AI Moderation API", version="0.1.0", lifespan=lifespan)
    moderate_auth = permission_dependency(authenticator, "moderate")
    review_read_auth = permission_dependency(authenticator, "review:read")
    review_write_auth = permission_dependency(authenticator, "review:write")
    _register_health(app, store, runtime, advisory_enabled)
    _register_moderation(app, runtime, moderate_auth)
    _register_reviews(app, store, review_read_auth, review_write_auth)
    return app


def _build_context(settings: Settings) -> RollingContextStore:
    return RollingContextStore(
        window_seconds=settings.context_window_seconds,
        max_scopes=settings.context_max_scopes,
        messages_per_scope=settings.context_messages_per_scope,
        sender_messages=settings.context_sender_messages,
        channel_messages=settings.context_channel_messages,
    )


def _build_advisory(
    settings: Settings,
    store: ModerationStore,
    override: AdvisoryClient | None,
) -> tuple[AdvisoryDispatcher, bool]:
    enabled = settings.openai_advisory_enabled and (
        override is not None or settings.openai_api_key is not None
    )
    client = override or _default_advisory_client(settings, enabled)
    dispatcher = AdvisoryDispatcher(
        store=store,
        client=client,
        enabled=enabled,
        queue_size=settings.openai_queue_size,
        workers=settings.openai_workers,
        timeout_ms=settings.openai_timeout_ms,
    )
    return dispatcher, enabled


def _default_advisory_client(settings: Settings, enabled: bool) -> AdvisoryClient:
    if not enabled or settings.openai_api_key is None:
        return DisabledAdvisoryClient()
    return OpenAIAdvisoryClient(
        settings.openai_api_key,
        settings.openai_model,
        settings.openai_timeout_ms,
    )


def _register_health(
    app: FastAPI,
    store: ModerationStore,
    runtime: ModerationRuntime,
    advisory_enabled: bool,
) -> None:
    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", response_model=HealthResponse)
    async def ready() -> HealthResponse | JSONResponse:
        database_ready = await store.health_check()
        classifier = runtime.classifier_health()
        classifier_ready = classifier.get("ready") is True
        is_ready = database_ready and classifier_ready
        payload = HealthResponse(
            status="ready" if is_ready else "not_ready",
            ready=is_ready,
            request_queue_depth=runtime.queue_depth,
            request_queue_capacity=runtime.queue_capacity,
            request_workers=runtime.worker_count,
            classifier_ready=classifier_ready,
            classifier_mode=str(classifier.get("mode", "unknown")),
            local_model_version=(
                str(classifier["model_version"]) if classifier.get("model_version") else None
            ),
            advisory_enabled=advisory_enabled,
            advisory_queue_depth=runtime.advisory_queue_depth,
            advisory_queue_capacity=runtime.advisory_queue_capacity,
        )
        if is_ready:
            return payload
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )


def _register_moderation(
    app: FastAPI,
    runtime: ModerationRuntime,
    auth_dependency: Callable[..., Awaitable[Principal]],
) -> None:
    @app.post("/v1/moderate", response_model=ModerationResponse)
    async def moderate(
        request: ModerationRequest,
        principal: Annotated[Principal, Depends(auth_dependency)],
    ) -> ModerationResponse:
        try:
            return await runtime.submit(request, principal)
        except RequestQueueFull as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="moderation queue saturated",
            ) from exc
        except ProcessingTimeout as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="moderation deadline exceeded",
            ) from exc
        except EventInProgress as exc:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="event is still processing",
            ) from exc
        except EventConflict as exc:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="external message id conflict",
            ) from exc


def _register_reviews(
    app: FastAPI,
    store: ModerationStore,
    read_dependency: Callable[..., Awaitable[Principal]],
    write_dependency: Callable[..., Awaitable[Principal]],
) -> None:
    @app.get("/v1/events/{event_id}", response_model=EventDetails)
    async def get_event(
        event_id: str,
        _: Annotated[Principal, Depends(read_dependency)],
    ) -> EventDetails:
        try:
            return await store.get_event(event_id)
        except EventNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="event not found") from exc

    @app.post("/v1/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
    async def create_review(
        request: ReviewRequest,
        _: Annotated[Principal, Depends(write_dependency)],
    ) -> ReviewResponse:
        try:
            return await store.create_review(request)
        except EventNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="event not found") from exc


app = create_app()
