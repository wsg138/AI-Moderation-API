# Runtime API contract

This document defines the W01 service-foundation contract. The service is a private, optional add-on. Clients must keep their own strict deadline/circuit breaker and must allow the original Minecraft or Discord message when this service times out, rejects a malformed response, is saturated, or is unreachable.

## Authentication

`/v1/*` endpoints require both headers:

- `X-Client-Id: <configured client id>`
- `Authorization: Bearer <runtime secret>`

Clients and permission allowlists are supplied only through `AI_MOD_CLIENTS_JSON`. Supported permissions are `moderate`, `review:read`, and `review:write`. Health endpoints are intentionally unauthenticated for local supervisor checks. No real credential belongs in GitHub.

## `POST /v1/moderate`

The request contains the platform/scope, stable external message id, pseudonymous sender id, timezone-aware timestamp, text, and optional channel/reply ids. Unknown request fields are rejected.

The response exposes only the public decision contract: `event_id`, `action`, semantic `label`, bounded class `scores`, deterministic `rule_hits`, normalized `reason_codes`, `related_message_ids`, local model/policy versions, advisory status, latency, degradation/fallback state, and whether the response is an idempotent replay.

A repeated `(platform, scope_id, external_message_id)` with an identical request is an idempotent retry and returns the original event/decision. Reusing that key with different input is `409 Conflict`. Queue saturation or the caller-visible processing deadline returns `503`; clients must fail open.

The runtime itself also converts classifier/context/storage-reservation failures into an explicit degraded `ALLOW` decision. A classifier decision is never returned as `BLOCK` when the decision cannot be durably finalized.

## Context

The context store is in-memory and bounded by all of the following. Request workers are sharded by platform/scope/channel so messages sharing a context partition remain FIFO while independent partitions can still run concurrently:

- time window (default 45 seconds);
- maximum retained scopes;
- maximum retained messages per scope;
- same-sender context count (default 5);
- same-channel/scope context count (default 8).

Explicit replies are favored when present. The classifier receives the current message separately from prior context. `related_message_ids` are filtered against IDs actually present in the current/context set so a classifier cannot invent client deletion targets.

## Durable private data

SQLite stores raw moderation events, structured decision evidence, OpenAI advisory results, and human reviews. The default database path is under `runtime-data/`, which is gitignored. Nothing automatically exports production records to GitHub.

Decision evidence stores action/label, scores, rule hits, reason codes, related IDs, model/policy versions, latency, and degradation state. Advisory evidence stores the OpenAI model/scores plus a coarse disagreement marker comparing OpenAI `flagged` with the local message action. It does not store hidden chain-of-thought.

`GET /v1/events/{event_id}` requires `review:read`. `POST /v1/reviews` requires `review:write`. Both return explicit public response models rather than raw database rows.

## OpenAI advisory path

OpenAI moderation is disabled by default. When enabled, `OPENAI_API_KEY` is read only from the runtime environment and is never persisted by this service. Advisory work uses a separate bounded queue and worker pool, and the live moderation response does not wait for the OpenAI request.

Missing OpenAI credentials disable only the advisory path. Advisory timeout, API error, queue saturation, or advisory persistence failure cannot change or delay the local decision path beyond the bounded enqueue bookkeeping.

## Health

- `GET /health/live`: process liveness only.
- `GET /health/ready`: durable store + local-classifier readiness and bounded queue telemetry.

OpenAI advisory availability does not control readiness because it is explicitly secondary. The built-in stub classifier reports `classifier_ready=false`; this prevents the foundation package from presenting itself as production-ready before W12 supplies an accepted local classifier.
