from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
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
from .migrations import LATEST_SCHEMA_VERSION
from .models import (
    CorrectionAuthority,
    CorrectionRejectRequest,
    CorrectionRequest,
    CorrectionResponse,
    DecisionHistoryPage,
    DecisionHistoryFilter,
    EventDetails,
    HealthResponse,
    ModerationRequest,
    ModerationResponse,
    ReviewQueueResponse,
    SupportContextResponse,
)
from .runtime import ModerationRuntime, ProcessingTimeout, RequestQueueFull
from .storage import (
    DecisionConflict,
    EventConflict,
    EventInProgress,
    EventNotFound,
    ModerationStore,
    ProposalNotFound,
)

AuthDependency = Callable[..., Awaitable[Principal]]


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

    app = FastAPI(title="Enthusia AI Moderation API", version="0.2.0", lifespan=lifespan)
    moderate_auth = permission_dependency(authenticator, "moderate")
    review_read_auth = permission_dependency(authenticator, "review:read")
    review_write_auth = permission_dependency(authenticator, "review:write")
    support_context_auth = permission_dependency(authenticator, "support:context")
    _register_health(app, store, runtime, advisory_enabled)
    _register_moderation(app, runtime, moderate_auth)
    _register_reviews(app, store, review_read_auth, review_write_auth)
    _register_support_context(app, store, support_context_auth)
    return app


def _build_context(settings: Settings) -> RollingContextStore:
    return RollingContextStore(
        window_seconds=settings.context_window_seconds,
        max_scopes=settings.context_max_scopes,
        messages_per_scope=settings.context_messages_per_scope,
        sender_messages=settings.context_sender_messages,
        channel_messages=settings.context_channel_messages,
        linked_scopes=settings.context_linked_scopes,
        intervening_messages=settings.context_intervening_messages,
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
        is_ready = database_ready and classifier_ready and runtime.context_ready
        payload = _health_payload(
            runtime,
            classifier,
            classifier_ready,
            advisory_enabled,
            is_ready,
        )
        if is_ready:
            return payload
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )


def _health_payload(
    runtime: ModerationRuntime,
    classifier: dict[str, object],
    classifier_ready: bool,
    advisory_enabled: bool,
    is_ready: bool,
) -> HealthResponse:
    # schema_version is filled by the async route after the DB health check.
    return HealthResponse(
        status="ready" if is_ready else "not_ready",
        ready=is_ready,
        schema_version=LATEST_SCHEMA_VERSION,
        request_queue_depth=runtime.queue_depth,
        request_queue_capacity=runtime.queue_capacity,
        request_workers=runtime.worker_count,
        classifier_ready=classifier_ready,
        classifier_mode=str(classifier.get("mode", "unknown")),
        local_model_version=_optional_string(classifier.get("model_version")),
        advisory_enabled=advisory_enabled,
        advisory_queue_depth=runtime.advisory_queue_depth,
        advisory_queue_capacity=runtime.advisory_queue_capacity,
        rehydrated_context_messages=runtime.rehydrated_context_messages,
        context_ready=runtime.context_ready,
    )


def _register_moderation(
    app: FastAPI,
    runtime: ModerationRuntime,
    auth_dependency: AuthDependency,
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
                detail="moderation queue saturated; client must fail open",
            ) from exc
        except ProcessingTimeout as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="moderation deadline exceeded; client must fail open",
            ) from exc
        except EventInProgress as exc:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="event is still processing"
            ) from exc
        except EventConflict as exc:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="external or canonical message id conflict",
            ) from exc


def _register_reviews(
    app: FastAPI,
    store: ModerationStore,
    read_dependency: AuthDependency,
    write_dependency: AuthDependency,
) -> None:
    _register_event_read(app, store, read_dependency)
    _register_review_queue(app, store, read_dependency)
    _register_decision_history(app, store, read_dependency)
    _register_correction_write(app, store, write_dependency)
    _register_correction_reject(app, store, write_dependency)


def _register_event_read(app: FastAPI, store: ModerationStore, dependency: AuthDependency) -> None:
    @app.get("/v1/events/{event_id}", response_model=EventDetails)
    async def get_event(
        event_id: str,
        _: Annotated[Principal, Depends(dependency)],
    ) -> EventDetails:
        try:
            return await store.get_event(event_id)
        except EventNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="event not found") from exc


def _register_review_queue(
    app: FastAPI,
    store: ModerationStore,
    dependency: AuthDependency,
) -> None:
    @app.get("/v1/review-items", response_model=ReviewQueueResponse)
    async def review_items(
        _: Annotated[Principal, Depends(dependency)],
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
    ) -> ReviewQueueResponse:
        return ReviewQueueResponse(items=await store.list_review_items(limit))



def _register_decision_history(
    app: FastAPI,
    store: ModerationStore,
    dependency: AuthDependency,
) -> None:
    @app.get("/v1/decisions", response_model=DecisionHistoryPage)
    async def decisions(
        _: Annotated[Principal, Depends(dependency)],
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        cursor: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
        filter: DecisionHistoryFilter = DecisionHistoryFilter.ALL,
    ) -> DecisionHistoryPage:
        try:
            return await store.list_decisions(limit, cursor, filter)
        except EventNotFound as exc:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="decision cursor not found"
            ) from exc


def _register_correction_write(
    app: FastAPI,
    store: ModerationStore,
    dependency: AuthDependency,
) -> None:
    @app.post("/v1/review-corrections", response_model=CorrectionResponse, status_code=201)
    async def create_correction(
        request: CorrectionRequest,
        principal: Annotated[Principal, Depends(dependency)],
    ) -> CorrectionResponse:
        admin_override = _authorize_correction_authority(principal, request.authority)
        try:
            return await store.create_correction(request, admin_override)
        except EventNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="event not found") from exc
        except DecisionConflict as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _register_correction_reject(
    app: FastAPI,
    store: ModerationStore,
    dependency: AuthDependency,
) -> None:
    @app.post("/v1/review-corrections/{proposal_id}/reject", response_model=CorrectionResponse)
    async def reject_correction(
        proposal_id: str,
        request: CorrectionRejectRequest,
        principal: Annotated[Principal, Depends(dependency)],
    ) -> CorrectionResponse:
        admin_override = _authorize_correction_authority(principal, request.authority)
        try:
            return await store.reject_correction(proposal_id, request, admin_override)
        except ProposalNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="correction not found") from exc
        except DecisionConflict as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _authorize_correction_authority(
    principal: Principal,
    authority: CorrectionAuthority,
) -> bool:
    if authority is not CorrectionAuthority.ADMIN:
        return False
    if "review:admin" not in principal.permissions:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="admin correction permission denied")
    return True


def _optional_string(value: object) -> str | None:
    return str(value) if value else None


def _register_support_context(
    app: FastAPI,
    store: ModerationStore,
    dependency: AuthDependency,
) -> None:
    @app.get(
        "/v1/support-context/{subject_id}",
        response_model=SupportContextResponse,
    )
    async def support_context(
        subject_id: Annotated[str, Path(min_length=1, max_length=200)],
        _: Annotated[Principal, Depends(dependency)],
        limit: Annotated[int, Query(ge=1, le=25)] = 10,
    ) -> SupportContextResponse:
        decisions = await store.list_support_context(subject_id, limit)
        return SupportContextResponse(subject_id=subject_id, decisions=decisions)

app = create_app()
