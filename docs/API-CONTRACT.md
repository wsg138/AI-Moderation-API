# Runtime API contract — Policy v1

This document defines the stable runtime contract that W13 RoseChat, W14 Discord, and W15 EnthusiaStaff may build against. The service is an optional private add-on. Clients must keep their own strict deadline/circuit breaker and must allow normal chat when the service times out, is saturated, is unreachable, or returns a degraded/fail-open result.

OpenAI Moderation remains advisory and asynchronous. It is never on the latency-critical decision path.

## Authentication and permissions

`/v1/*` endpoints require both headers:

- `X-Client-Id: <configured client id>`
- `Authorization: Bearer <runtime secret>`

Credentials and allowlisted permissions come only from `AI_MOD_CLIENTS_JSON`. Supported permissions are:

- `moderate`
- `review:read`
- `review:write`
- `review:admin`

`review:admin` is required when a correction request claims `authority=ADMIN`. Normal staff cannot obtain immediate-override behavior merely by setting the JSON field.

Health endpoints remain unauthenticated for local supervisor checks. No production credential belongs in this repository.

## Source metadata

`POST /v1/moderate` requires an explicit `platform` and `channel_profile`.

Supported profiles are:

- `minecraft_public`
- `minecraft_private`
- `discord_general`
- `discord_gaming`
- `discord_staff_exempt`
- `discord_ticket_exempt`
- `discord_configured_exempt`

Minecraft requests must use a Minecraft profile and Discord requests must use a Discord profile. Production channel IDs are not hard-coded into the service.

The request may additionally carry:

- `conversation_id` for a semantically related private/conversation scope;
- `recipient_ids` and `target_ids` for participant/target linkage;
- `reply_to_message_id` for explicit replies;
- authoritative `*_identity_id` values for cross-platform identity linkage;
- `canonical_message_id` when Minecraft/Discord copies are mirrors of one logical message.

Identity IDs are assertions from authenticated trusted integrations. Clients must populate them only from an authoritative account-linking source; ordinary usernames or inferred matches are not sufficient.

### Exempt profiles

Exempt requests return an `ALLOW` response with `ingestion_status=SKIPPED_EXEMPT` before reservation, classification, advisory dispatch, context insertion, incident creation, or raw-message persistence. Exempt text therefore cannot influence later moderated content.

## `POST /v1/moderate`

Policy v1 separates decision dimensions. There is no overloaded `REVIEW` message action.

The response exposes:

- `semantic_label`: what the message/incident means;
- `message_action`: `ALLOW` or `BLOCK`;
- `review_priority`: `NONE`, `NORMAL`, or `URGENT`;
- `strike_recommendation`: `NONE`, `EVIDENCE`, or `STRIKE`;
- `containment`: `NONE` or `MUTE`;
- `containment_duration_seconds`: nullable and present only when policy/model evidence supplies a duration;
- `support_flow`: `NONE`, `SELF_HARM_CHECK`, or `TARGET_SAFETY_CHECK`;
- `reason_codes`, `rule_hits`, bounded model `scores`, and optional `confidence`;
- `related_message_ids` and structured `related_messages` for retroactive removal;
- optional `incident` summary;
- local model and policy versions;
- advisory/degradation/fallback state.

Semantic labels match the Policy-v1 dataset vocabulary exactly:

`SAFE`, `GAMEPLAY_VIOLENCE`, `LOW_LEVEL_HARASSMENT`, `SEVERE_HARASSMENT`, `STAFF_TARGETED_ABUSE`, `REAL_WORLD_THREAT`, `SELF_HARM_INSTRUCTION`, `SELF_HARM_INTENT`, `THIRD_PARTY_SELF_HARM_CONCERN`, `HATE`, `SLUR_USE`, `SEXUAL_CONTENT`, `SEXUAL_MINOR`, `DOXXING`, `BLACKMAIL`, `GROOMING`, `DANGEROUS_REAL_WORLD_INSTRUCTIONS`, and `AMBIGUOUS_REVIEW`.

### Idempotency and mirrors

A repeated external message key with identical input is an idempotent replay. Reusing that key with different input returns `409 Conflict`.

When two platform messages carry the same non-null `canonical_message_id`, the service stores one canonical moderation event. The second copy becomes a message alias and replays the existing decision. Canonical-ID reuse with different message content returns `409 Conflict`.

If a mirror arrives while the canonical event is still `PENDING`, its alias is persisted immediately before the runtime waits briefly for the canonical decision. If that bounded wait cannot complete inside the moderation deadline, the mirror request fails open without creating a second logical event. A later retry resolves through the durable alias and replays the canonical decision once it is available.

`PENDING` ownership uses a durable reservation token and lease timestamp. A retry does not steal a plausibly active reservation. Once the configured stale threshold has elapsed, one retry may atomically claim the existing event with a new token and resume processing from the original canonical request metadata. Finalization requires the current token, so a superseded worker cannot finalize after another retry has recovered the event.

`related_messages` is resolved through aliases at read/replay time. This lets clients delete all known platform copies of the canonical event without counting a mirror as another incident/strike.

### Retroactive deletion

The classifier may name prior context message IDs as `related_message_ids`. The runtime allowlists them against the actual current/context set; invented deletion targets are discarded. Structured `related_messages` carries platform/scope/channel/external IDs so W13/W14 can later remove prior copies on the correct surface.

The current message is always represented in the internal related-event set even when no prior message is retroactively removed.

## Context contract

The service owns bounded semantic context. Retrieval may cross channel boundaries only through explicit relationships:

- same sender in the same platform/server scope, including Minecraft PM ↔ public continuity;
- participant/target overlap;
- explicit replies;
- shared conversation IDs;
- authoritatively linked identities across Minecraft/Discord.

Cross-platform linkage is not inferred from names. Unrelated channels/senders do not become global history. Candidate scopes and returned messages are bounded, and only the most recent configured intervening messages are considered (Policy-v1 default: 20).

Request queue affinity keeps one sender/canonical identity ordered across related scopes so a fast PM→public continuation cannot race ahead of its own context.

## Incidents

Per-message classification and incident aggregation remain separate. A classifier may emit an `IncidentSignal` with a stable incident key, kind, severity, participating senders, targets, and coordination flag. Storage maintains:

- one incident record;
- many incident-event links;
- distinct sender and target information per linked event.

This supports repeated harassment, unwanted contact, dogpiling, threats, later reinterpretation, and target-specific history without pretending multiple senders authored one message.

## Durable structured memory

Durable runtime memory is separate from model weights and from raw short-term context.

`moderation_memory` can store policy facts such as incidents, strike/evidence history, target harassment, unwanted-contact/stop state, mutual-banter state, target-strict-filter state, staff outcomes, and age clues. Facts contain source, confidence, optional target, confirmation state, timestamps, and optional expiry.

Punishment-oriented memory is filtered by platform. Missing/expired facts are neutral; they are never synthesized.

`safety_memory` is a physically separate table/query path for safety checks and self-harm concerns. It is returned separately in `MemorySnapshot` and is never included in punishment-memory queries.

`identity_links` reserves a migration-safe durable representation for authoritative Minecraft/Discord linkage. Runtime cross-platform request metadata must come from authoritative client-side linkage; future sync endpoints can populate this table without redesigning event storage.

Exact decay curves remain a calibration concern. Expiry timestamps support Policy-v1 decay without hard-coding unresolved formulas.

## Restart continuity

At startup, the runtime rehydrates a bounded set of recent `FINAL` moderated events from SQLite into the in-memory context store. Rehydration defensively excludes exempt profiles and deduplicates canonical mirrors.

If rehydration fails, readiness is false and moderation stays in a sticky explicit fail-open state until the process is restarted successfully. It does not resume blocking with a partially trusted context cache.

## Fail-open behavior

The following cannot cause a blocking decision by default:

- classifier unavailable/error/timeout;
- malformed classifier output;
- context read/write/rehydration failure;
- durable memory read failure;
- storage reservation/finalization/replay failure;
- request queue saturation/deadline;
- schema/readiness failure;
- OpenAI advisory failure/saturation/timeout.

Internal failures return `message_action=ALLOW`, `ingestion_status=FAIL_OPEN`, `degraded=true`, and a structured `fallback_state` when a response can safely be produced. Queue/deadline failures return `503` and explicitly require the client to fail open. A decision is never returned as `BLOCK` if its durable finalization fails.

## Review and correction API

### `GET /v1/review-items`

Requires `review:read`. Returns pending `NORMAL`/`URGENT` items without leaking internal database rows. Events with an accepted correction are omitted from the pending queue.

### `GET /v1/events/{event_id}`

Requires `review:read`. Returns an explicit allowlisted model containing the original AI decision, advisory evidence, correction history, accepted correction, and only the context events whose IDs were recorded as material decision evidence.

The service does not expose arbitrary neighboring chat merely because it was present in the rolling buffer.

### `POST /v1/review-corrections`

Requires `review:write`. A normal staff correction is a proposal and requires two distinct staff approvals before becoming accepted. Repeating the same vote is idempotent; attempting the opposite vote creates a conflict.

A caller using `authority=ADMIN` additionally requires `review:admin` and may immediately accept/override a correction.

### `POST /v1/review-corrections/{proposal_id}/reject`

Requires `review:write`. Two normal staff rejection votes reject a pending proposal. Admin+ may reject immediately and may reverse an accepted proposal when explicitly authorized.

Original AI outcomes are immutable. Accepted corrected outcomes are stored separately, remain auditable, and can later be selected for reviewed/redacted training export.

## SQLite schema migrations

SQLite uses `PRAGMA user_version` and transactional versioned migrations. Existing W01 dev/runtime databases are migrated in place; the database is never silently deleted/recreated.

Migration v1:

- preserves W01 event/evidence/advisory/review tables;
- adds Policy-v1 source/decision/context fields;
- adds aliases, incidents, durable memory, safety memory, identity-link, and correction tables;
- maps legacy `action=REVIEW` to `message_action=ALLOW` + `review_priority=NORMAL`;
- maps legacy `BLOCK`/`ALLOW` to the new message-action dimension;
- preserves legacy labels as semantic labels.

Migration v2:

- adds `reservation_token` and `reservation_updated_at` to moderation events;
- backfills existing `PENDING` rows with recoverable ownership state without deleting or duplicating them;
- leaves finalized moderation decisions unchanged.

Migration runs in `BEGIN IMMEDIATE` and commits only after all additions/backfills/indexes succeed. Failure rolls the transaction back and readiness remains false. A database with a schema version newer than the running binary is rejected rather than modified.

Rollback planning is binary-first: stop the new binary and restore a pre-migration database backup if an operator needs to return to the old W01 runtime. The migration is additive, but the old binary is not expected to understand Policy-v1 writes; production deployment remains separately gated.

## Privacy boundary

Raw production messages and identifiers stay in the private runtime database, never this public repository. Exempt content is not ingested. Review reads expose only allowlisted fields and materially used context. Curated training export remains a separate reviewed/redacted process.

## Intentionally unresolved Policy-v1 edges

The runtime is extensible without assigning policy for unresolved cases. It does not invent answers for Discord bot DMs, graphic self-harm disclosure, consensual explicit adult PMs, grooming with uncertain age, broader dangerous-instruction domains, fake-doxxing strike cleanup, a complete threat-containment duration matrix, blackmail duration, or lexical slur false-positive rules.
