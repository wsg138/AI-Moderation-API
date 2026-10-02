# W13 launch packet — RoseChat central moderation client

## Identity

You are **W13**, the RoseChat client-integration worker for Enthusia AI Moderation.

Tracking issue: **wsg138/AI-Moderation-API#14 — W13 — RoseChat client integration**.

Product repository: **`wsg138/Enthusia-RoseChat`**.
Current default branch: **`master`**.
Last coordinator-observed master head: **`0425b7d2c2252f8287af93c12d13e1e4c5e686f4`**.

Create **`w13/rosechat-client` from the live current `master` when you start**. Live GitHub is authoritative. Open one PR to RoseChat `master`; do not self-merge.

No production deployment, plugin restart, live config mutation, or punishment enablement is authorized.

## Goal

Replace RoseChat's local/remote semantic moderation decision path with the central Policy-v1 moderation service while preserving RoseChat's already-proven chat-safety lifecycle:

- short bounded hold;
- asynchronous I/O;
- fail open;
- circuit breaking/backpressure;
- generation fencing across reloads;
- exact-message late deletion;
- staff health/status visibility.

The central service owns semantic policy, bounded context, durable event/review state, OpenAI advisory results, mirror dedupe, and Policy-v1 output dimensions. RoseChat must not continue operating a second independent moderation policy/strike engine beside it.

## Upstream gate

The central runtime/review contract is accepted and stable enough for clients.

W19 runtime recovery:
- AI repo PR #40 final head `2954bd53b04472537ddfef9622832882b2d8c348`;
- merge `917aef4e97c539fea89d558f9e1be9d0d506b4a4`;
- exact-head CI #67 success;
- post-merge main CI #69 success.

Canonical client contract:
- `wsg138/AI-Moderation-API/docs/API-CONTRACT.md`.

Do not copy an older provisional contract from an issue or chat.

## Current RoseChat baseline you must preserve

Read these live files before editing:

- `docs/ai-moderation.md`;
- `src/main/resources/ai-moderation.yml`;
- `src/main/java/dev/rosewood/rosechat/moderation/ai/AiModerationManager.java`;
- `AiModerationConfig.java`;
- `AiModerationContextBuffer.java`;
- `AiModerationPolicy.java`;
- `OpenAiModerationClient.java`;
- `AiModerationMetrics.java`;
- current moderation tests;
- `src/main/java/dev/rosewood/rosechat/api/deletion/MessageDeletionHelper.java`;
- provider-neutral chat bridge code under `api/chatbridge/`;
- `docs/discord-chat-transport-checkpoint.md`;
- relevant `api/staff/` contracts.

The existing manager already has useful safety engineering:
- async moderation;
- bounded local hold (current default 200 ms, config rejects >300 ms);
- late-delete behavior only when the exact published message UUID is resolved;
- a circuit breaker;
- bounded request/in-flight admission;
- a runtime generation fence so stale async completions cannot act after reload;
- staff health/degraded notices;
- metrics;
- a fail-open path.

Preserve those properties unless there is a stronger equivalent with tests.

## Parallel RoseChat work

At the coordinator checkpoint, RoseChat had unrelated open PRs including:
- #17 presence compatibility;
- #8 draft compatibility/staff repairs.

Re-read live open PRs before editing. Do not absorb unrelated work or overwrite overlapping compatibility changes. If an overlapping PR lands while W13 is active, rebase/reconcile and retest.

The Discord chat-transport migration is separate from W13. Do not remove DiscordSRV or redesign the provider-neutral chat bridge as part of this task.

## Central API facts

Authenticated `/v1/*` requests use:
- `X-Client-Id`;
- `Authorization: Bearer <secret>`.

RoseChat needs only the permissions required by its client role, primarily `moderate`. Do not give it review-admin credentials.

`POST /v1/moderate` accepts explicit source metadata and returns separated dimensions:
- `message_action: ALLOW | BLOCK`;
- `semantic_label`;
- `review_priority`;
- `strike_recommendation`;
- `containment` and optional duration;
- `support_flow`;
- bounded scores/confidence;
- reason codes;
- `related_message_ids` / structured `related_messages`;
- policy/model versions;
- degradation/fail-open metadata.

RoseChat enforces the **message action** only. It must not convert review/strike/containment recommendations into an automatic punishment engine.

## Channel/profile mapping

Minecraft requests must use:
- `minecraft_public`, or
- `minecraft_private`.

Do not infer a Discord profile or cross-platform identity from names.

If Staff/RoseChat policy says a surface is exempt, bypass semantic moderation locally where that is already authoritative. Do not send staff-only/configured-exempt text merely for logging.

The service itself guarantees that explicit exempt profiles are not persisted or inserted into context, but RoseChat should avoid unnecessary requests when it already knows a surface is outside semantic moderation.

Document the exact mapping from RoseChat channel/private-message surfaces to central profiles.

## Request identity and mirror contract

Every submitted logical message must have a stable external ID suitable for exact replay/deletion.

Requirements:
- `external_message_id` must remain stable across a retry of the same RoseChat message;
- never generate a new idempotency ID merely because an HTTP call retries;
- changed content with the same external key is a conflict, not a new event;
- map reply metadata only when authoritative;
- target/recipient identity fields must come from real application state, not text inference.

For Minecraft↔Discord mirrors, use one stable `canonical_message_id` for the same logical message.

Coordinate with the provider-neutral outbound chat event ID and W14 so:
- the Minecraft original and Discord mirror use the same canonical ID;
- the service stores one moderation event;
- `related_messages` can identify every known platform copy;
- mirrored copies do not create duplicate incidents/strikes.

If current transport wiring cannot yet carry the canonical ID end-to-end, define the provider-neutral contract/change needed and test it, but do not build a second Discord transport or remove the existing one in W13.

## Timing and fail-open requirements

Minecraft chat availability is the priority.

Preserve a strict local hold budget no greater than the current safety envelope. A slow/unreachable AI service must not stall the main server thread.

Handle at least:
- connect failure;
- request timeout;
- central HTTP 503 queue/deadline failure;
- malformed response;
- authentication/config failure;
- circuit-open state;
- local queue/backpressure;
- reload while requests are in flight.

These all fail open for ordinary chat.

A central `409 Conflict` is not a reason to block chat. Treat it as an idempotency/integration defect:
- fail open;
- record bounded diagnostic state;
- alert authorized staff/health diagnostics;
- do not retry forever with mutated IDs.

If the service returns `ingestion_status=FAIL_OPEN`, `degraded=true`, or an equivalent fail-open state, RoseChat must allow the message.

## Current-message and late-deletion lifecycle

Preserve RoseChat's atomic one-message lifecycle.

If `BLOCK` arrives before publication:
- do not publish the current message;
- provide an appropriate player-facing message;
- do not locally punish the sender.

If `BLOCK` arrives after fail-open publication but within a supported late-result path:
- delete only the exact RoseChat message UUID that corresponds to the central event;
- never guess a nearby message;
- if exact deletion cannot be proven, keep chat safe and alert staff instead.

For `related_messages`:
- act only on structured entries whose platform/scope/channel belong to this RoseChat/Minecraft surface;
- delete only exact resolvable message IDs;
- ignore foreign-platform entries for local deletion;
- bound work and make repeated responses idempotent.

The current event and retroactive related events must never be deleted twice because of a race between timeout/publication and async completion.

## Context ownership

The central service now owns bounded semantic context, restart continuity, mirror aliases, and explicit relationship linkage.

Do not send a local prose transcript as if it were the authoritative classifier input.

RoseChat should send the current structured message plus authoritative metadata. Legacy `AiModerationContextBuffer` may remain temporarily only where required for old diagnostic/shadow tooling during migration, but it must not become a competing production context/policy engine after central integration.

If legacy OpenAI diagnostic commands are kept, label them clearly as diagnostics and ensure they cannot produce production enforcement alongside the central service.

## Remove duplicate policy authority

The existing local OpenAI threshold policy and rolling strike/mute path predate the central architecture.

W13 must not leave these as a second active production decision authority:
- `AiModerationPolicy` must not independently decide production ALLOW/DELETE when the central service is enabled;
- direct RoseChat OpenAI moderation must not be the production semantic decision path;
- the local strike ledger must not create AI punishment escalation;
- `punishments.enabled` must not silently continue a second punishment system;
- RoseChat must not turn central `strike_recommendation` or `containment` into a mute/ban on its own.

EnthusiaStaff owns human review and punishment/case authority.

Preserve migration compatibility carefully: do not delete old user config without a deliberate documented upgrade path. Mark legacy fields/deprecations explicitly.

## Health/status/metrics

Adapt RoseChat's AI status surface to the central client.

Useful status should include bounded/non-secret information such as:
- configured/enabled/shadow/enforcement state where still applicable;
- central endpoint availability;
- circuit status;
- queue/in-flight depth;
- request success/failure/timeout/conflict counts;
- p50/p95/p99 client-observed latency;
- ALLOW/BLOCK/degraded counts;
- late deletions;
- last bounded failure category;
- central model/policy version when returned.

Never print bearer tokens or full credential JSON.

A service being unavailable must show degraded health while chat continues.

## Configuration and networking

Do not hard-code `localhost`.

The central service currently lives with the Ticket Bot and defaults to a loopback bind. RoseChat may run on a different server/container. W13 must therefore:
- make base URI configurable;
- make client ID/token configurable through a safe mechanism;
- never commit production secrets;
- never assume the Minecraft server can reach `127.0.0.1` of the Ticket Bot container;
- not change the central service bind/firewall/private routing as part of W13.

If production RoseChat requires an approved private network route that does not yet exist, implement/test the client against a mock/local fixture and surface the networking dependency to the coordinator. Do not expose the moderation API publicly to solve it.

## Threading / Paper safety

No network I/O on the main Paper thread.

Any Bukkit/Paper operation that must run on the server thread—including player notification or message deletion if required by the API—must be handed back through the correct scheduler.

Keep queues/executors bounded and shutdown-safe.

Reload/disable must cancel or fence stale work; no old response may enforce after a newer configuration generation has taken ownership.

## Required tests

Add focused tests for at least:

1. ALLOW before hold deadline.
2. BLOCK before publish.
3. Timeout -> publish/fail open.
4. 503 -> fail open.
5. central degraded/fail-open response -> allow.
6. 409 id conflict -> fail open + diagnostic, no regenerated ID loop.
7. exact late BLOCK deletion.
8. late deletion cannot resolve exact UUID -> no guessed deletion.
9. retroactive `related_messages` deletes only exact Minecraft refs.
10. foreign Discord related refs are ignored by RoseChat deletion.
11. retry preserves external/canonical IDs.
12. mirrored canonical ID is stable and provider-neutral.
13. circuit breaker opens/reprobes without blocking chat.
14. local queue/backpressure fails open.
15. reload/disable generation fence prevents stale enforcement.
16. private/public profile mapping.
17. staff/exempt channel bypass.
18. credentials are never logged.
19. main-thread/network separation.
20. old local threshold/strike path cannot simultaneously enforce when central mode is active.

Use deterministic HTTP fixtures/fakes. Tests must not call a live central service.

## Acceptance criteria

Before requesting review:
- the central API is the single active semantic moderation authority in central mode;
- Minecraft chat remains fail-open and bounded;
- no main-thread HTTP;
- exact current/retroactive deletion is race-safe and idempotent;
- mirror IDs are stable;
- central degraded states never block chat;
- no automatic punishment path is re-enabled;
- legacy config migration is documented;
- build/tests pass;
- any static analysis/check workflows on the repository pass;
- exact PR head and evidence are reported.

## Non-goals

Do not:
- deploy;
- restart Paper/Pterodactyl;
- expose the central API publicly;
- change Policy v1;
- train a model;
- edit the central service runtime;
- implement the W14 Discord listener;
- implement the W15 review GUI;
- remove DiscordSRV/chat transport as part of this task;
- enable automatic punishments.

## PR completion comment

Include:
- exact head SHA;
- base/master SHA used;
- files/legacy paths retired or bypassed;
- config migration behavior;
- HTTP deadline/queue/circuit settings;
- exact profile mapping;
- external/canonical ID strategy;
- current/late/retroactive deletion evidence;
- tests/build workflow results;
- any unresolved private-network dependency;
- confirmation that no deployment/live config/punishment change occurred.
