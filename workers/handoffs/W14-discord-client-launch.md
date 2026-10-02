# W14 launch packet — Discord moderation bridge in Enthusia Support

## Identity

You are **W14**, the Discord-side central moderation integration worker.

Tracking issue: **wsg138/AI-Moderation-API#15 — W14 — Discord Ticket Bot moderation bridge**.

Product repository: **`wsg138/enthusia-support-bot`**.
Default branch: **`main`**.
Last coordinator-observed main head: **`61e635f9147c11f0262ae157acb8b521582cc2c8`**.

Create **`w14/discord-client` from live current `main` when you start**. Live GitHub is authoritative. Open one PR to the support-bot `main`; do not self-merge.

At the coordinator checkpoint there were no open support-bot PRs, but re-check before editing.

No production deployment, bot restart, Discord permission mutation, live config change, or punishment enablement is authorized.

## Goal

Add the existing Discord bot as a bounded, fail-open client of the central Policy-v1 moderation service for eligible Discord messages.

Do **not** create another Discord bot/client/gateway.

The Ticket Bot already owns the Discord gateway and has several independent `messageCreate` consumers. W14 should add a focused moderation service/listener through the existing `createServices(...)` / `attach(...)` pattern without coupling bot readiness to AI readiness.

The central service owns semantic moderation policy, context, mirror dedupe, review storage, and OpenAI advisory evidence. The Discord bot must not implement a second classifier or local threshold policy.

## Upstream gate

The central runtime/review contract is accepted.

W19 runtime recovery:
- AI repo PR #40 final head `2954bd53b04472537ddfef9622832882b2d8c348`;
- merge `917aef4e97c539fea89d558f9e1be9d0d506b4a4`;
- exact-head CI #67 success;
- post-merge CI #69 success.

Canonical contract:
- `wsg138/AI-Moderation-API/docs/API-CONTRACT.md`.

Do not implement from the old issue summary alone.

## Existing support-bot architecture to inspect

Before coding, read live versions of:

- `enthusiasupport/src/client.ts`;
- `enthusiasupport/src/index.ts`;
- `enthusiasupport/src/services/createServices.ts`;
- `enthusiasupport/src/config/config.ts`;
- `enthusiasupport/src/services/MessageMirrorService.ts`;
- `enthusiasupport/src/services/GuildScopedAiServices.ts`;
- current logging/permission services;
- current ticket/category lookup code;
- `enthusiasupport/package.json`;
- root `start-bots.js`;
- supervisor health code/tests.

Important current facts:
- one existing discord.js `Client` owns the gateway;
- `MessageMirrorService` already listens to message create/update/delete for ticket persistence;
- unrelated Ticket AI / Discord Assistant / Knowledge AI listeners also exist;
- the central AI moderation process is supervised as an **optional** child;
- Ticket Bot startup/readiness must not depend on AI moderation readiness;
- when co-located, the central service normally binds to loopback.

Do not conflate support-agent AI with moderation AI. They solve different problems.

## Central API auth

Moderation requests require:
- `X-Client-Id`;
- `Authorization: Bearer <secret>`.

Create the smallest needed client configuration for W14, normally `moderate` only.

Requirements:
- base URL configurable;
- client ID configurable;
- bearer token configurable;
- no secret values committed;
- no token in logs/errors;
- no `AI_MOD_CLIENTS_JSON` value echoed;
- no hard-coded production URL.

Because the service and Ticket Bot are intended to share the same container, loopback can be a documented safe default only when it matches the supervisor configuration. Do not make Ticket Bot readiness depend on that endpoint existing.

## Eligible vs exempt surfaces

Policy v1 explicitly exempts:
- Discord ticket channels;
- Discord staff-only channels;
- explicitly configured exempt channels.

Supported profiles:
- `discord_general`;
- `discord_gaming`;
- `discord_staff_exempt`;
- `discord_ticket_exempt`;
- `discord_configured_exempt`.

W14 must deterministically classify channel profile before semantic submission.

### Ticket channels

Use authoritative Ticket Bot state/database/category routing to identify ticket channels. Do not moderate ticket contents with the central semantic classifier. Do not send ticket text to the central service merely for logging.

### Staff-only channels

Use authoritative configured role/channel/category semantics. Do not infer “staff channel” from channel names.

### Configured exemptions

Add an explicit configuration surface for additional exempt channel/category IDs if needed. It must be bounded, validated, and documented.

### Gaming vs general

Define a configuration-driven mapping for Discord gaming surfaces. Do not infer gaming context from message text alone merely to choose a profile.

### DMs

Discord bot DM policy remains an unresolved Policy-v1 edge. Do **not** invent a moderation rule for DMs in W14. Skip semantic moderation for DMs unless Policy v1 is explicitly updated later.

## Event metadata

For eligible guild messages send:
- `platform=discord`;
- correct `channel_profile`;
- stable `scope_id` (guild/server scope);
- authoritative `channel_id`;
- `external_message_id = Discord message.id`;
- `sender_id = Discord user id`;
- `occurred_at = Discord message creation time`;
- message text;
- `reply_to_message_id` when the Discord message reference is authoritative;
- target/recipient IDs only when derived from real structured mentions/reply participants as defined by the client contract.

Do not infer cross-platform identity from display names/usernames.

If an authoritative account-link source is available through the existing platform architecture, use it only according to that source's contract. Otherwise omit `*_identity_id` rather than guessing.

## Mirror/canonical ID contract

Minecraft↔Discord mirrors must be counted as one logical moderation event.

When a Discord message is a transported copy of a Minecraft RoseChat event:
- pass the exact same `canonical_message_id` used by W13/RoseChat;
- do not classify a copied message as a fresh unrelated Discord author event;
- preserve the Discord `external_message_id` as its real Discord snowflake;
- later central replays must include all known structured aliases in `related_messages`.

Do not detect mirrors by comparing message text.

Use authoritative transport metadata/event IDs from the provider-neutral chat transport. If that metadata is not yet wired into this bot, create a narrow typed seam/resolver and tests, and surface the transport dependency. Do not redesign or duplicate the entire DiscordSRV replacement project in W14.

## Message lifecycle and enforcement

Discord cannot block a message before Discord itself publishes it, so W14 is naturally post-send enforcement.

For an eligible message:
1. dispatch central moderation asynchronously;
2. ordinary bot processing continues;
3. if central returns ALLOW, do nothing;
4. if central returns BLOCK, delete the current Discord message if it is still the exact target and permissions allow;
5. process `related_messages` for prior Discord copies only when their platform/guild/channel/message IDs are explicit and authorized;
6. never delete a Minecraft message from W14; that belongs to W13/RoseChat.

Deletion must be idempotent and bounded.

If a message no longer exists, treat that as already removed rather than an unbounded retry condition.

If Discord permission/API deletion fails:
- log a bounded non-secret diagnostic;
- optionally notify the appropriate staff surface if one already exists;
- do not crash/restart the bot;
- do not retry forever;
- do not reinterpret the failure as permission to punish the author.

## Fail-open / backpressure

AI failure must not affect the Ticket Bot's normal behavior.

Handle:
- central process absent/unready;
- connection refusal;
- timeout;
- 503 queue/deadline;
- malformed response;
- authentication/config error;
- 409 event conflict;
- local queue saturation;
- circuit breaker open state.

All fail open for message availability.

Use bounded concurrency and bounded pending work. Do not accumulate one promise/task per Discord message without a hard limit.

Do not make Discord `ClientReady`, Pterodactyl ready marker, ticket creation, ticket logging, or support-agent AI depend on moderation service health.

## 409 behavior

A 409 means integration/idempotency metadata disagreed with an existing event.

For normal chat:
- fail open;
- record a bounded diagnostic;
- do not retry using a newly invented external/canonical ID;
- surface repeated conflicts to staff/operations.

## Review/strike/containment outputs

W14 enforces only `message_action=BLOCK` by deleting the Discord message when possible.

Do not automatically:
- mute;
- ban;
- timeout;
- add roles;
- create a Discord punishment;
- apply `strike_recommendation` as a sanction.

Review/strike/containment/support dimensions are central evidence for W15/human staff workflows.

If a severe/urgent result needs staff visibility, use the established logging/alert mechanism without making the alert itself a punishment.

## Edits and deletions

Define behavior explicitly.

### Message edits

A materially edited eligible Discord message should be treated as changed content.

Because reusing the same external key with changed content correctly conflicts, do not silently submit mutated content under the original event ID as if unchanged.

Choose and document a safe integration strategy consistent with the central contract—for example a distinct versioned external moderation key derived from authoritative Discord message ID + edit version/timestamp while preserving original Discord message identity in client metadata where supported. If the current API cannot represent this safely without contract changes, surface it instead of inventing behavior.

Do not weaken central idempotency to accommodate edits.

### User/bot deletes

No moderation retry is needed after a message is already deleted. Existing `MessageMirrorService` logging must continue to work.

## Bots/webhooks/system content

Do not automatically moderate the bot's own messages, central transport copies, or arbitrary webhooks as if they were player speech.

Define a narrow eligibility policy and tests:
- ignore this bot;
- avoid loops from RoseChat transport;
- handle other bots/webhooks conservatively;
- do not treat bot-generated support content as player evidence.

## Configuration

Extend the existing Zod env schema rather than reading ad hoc environment variables throughout the code.

Suggested configuration dimensions:
- enable flag;
- base URL;
- client ID;
- bearer token;
- timeout;
- max in-flight/queue;
- circuit-breaker thresholds;
- general/gaming channel/category IDs;
- additional exempt IDs;
- staff alert destination if needed.

Do not log secret config.

Invalid moderation config should disable/degrade only moderation, not prevent the Ticket Bot from starting. This is important: current global `config.ts` fails startup for invalid mandatory bot config, so moderation-only optional values should be parsed in a way that cannot turn an optional AI feature into a critical bot startup dependency.

## Required tests

At minimum cover:

1. eligible general message -> central request.
2. gaming mapping -> `discord_gaming`.
3. ticket channel -> no semantic request.
4. staff channel -> no semantic request.
5. configured exempt -> no semantic request.
6. DM -> skipped while policy unresolved.
7. bot/self/transport-loop message -> skipped.
8. ALLOW -> no deletion.
9. BLOCK -> exact current Discord message deletion.
10. related Discord messages -> bounded exact deletion.
11. related Minecraft refs -> ignored locally.
12. timeout/refusal/503 -> fail open.
13. malformed/degraded central result -> fail open.
14. 409 -> fail open with bounded diagnostic and stable IDs.
15. bounded concurrency/backpressure.
16. circuit breaker recovery.
17. bot readiness independent from central AI health.
18. bearer/token redaction.
19. reply metadata mapping.
20. mirror canonical ID propagation from authoritative transport metadata.
21. no duplicate processing of a mirrored Minecraft message.
22. no automatic punishments from review/strike/containment fields.
23. message edit behavior is explicit and idempotency-safe.
24. shutdown removes/settles moderation work without hanging bot exit.

Use deterministic mock HTTP and discord.js fixtures. No live Discord/server calls in CI.

## Repository checks

Run the repository's canonical checks, including from `enthusiasupport/`:
- `npm run check`;
- build/type checks;
- focused new moderation tests.

Do not weaken existing tests.

## Non-goals

Do not:
- create a second Discord gateway/client;
- modify central Policy v1;
- embed a second classifier;
- merge moderation with support-agent/Ticket AI policy;
- moderate exempt ticket/staff text;
- implement W13's Minecraft deletion path;
- implement W15's review GUI;
- redesign all Discord chat transport;
- deploy/restart the Ticket Bot;
- change live Discord roles/permissions;
- enable automatic punishments.

## PR completion comment

Include:
- exact head/base SHA;
- exact eligibility/profile mapping;
- config variables added (names only, no secret values);
- queue/timeout/circuit settings;
- mirror canonical-ID source/seam;
- current/related deletion evidence;
- fail-open tests;
- exemption/privacy tests;
- `npm run check` result;
- any transport dependency still unresolved;
- confirmation that Ticket Bot startup/readiness remains independent;
- confirmation no deployment/live config/punishment changes occurred.
