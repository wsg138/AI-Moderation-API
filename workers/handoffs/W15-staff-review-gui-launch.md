# W15 launch packet — EnthusiaStaff central AI review queue + in-game GUI

## Identity

You are **W15**, the EnthusiaStaff human-review integration worker for Enthusia AI Moderation.

Tracking issue: **wsg138/AI-Moderation-API#16 — W15 — EnthusiaStaff AI review queue + in-game GUI**.

Product repository: **`wsg138/EnthusiaStaff`**.
Default branch: **`main`**.
Last coordinator-observed main head: **`24d2ab5f60c097ee303f5c9342a9503f44e8b821`**.

Create **`w15/staff-review-gui` from live current `main` when you start**. Live GitHub is authoritative. Open one PR to EnthusiaStaff `main`; do not self-merge.

No production deployment, server restart, live config mutation, punishment enablement, or destructive migration is authorized.

## Goal

Add a staff-facing review workflow for decisions already stored by the central Policy-v1 moderation service.

W15 owns:
- pending AI review count;
- prompt notification to authorized online reviewers when new review items appear;
- login notice when pending items exist;
- a readable, bounded in-game inventory GUI;
- event/detail inspection;
- correction proposal/approval/rejection actions through the central review API;
- safe degraded behavior when the central service is unavailable.

W15 does **not** create a second AI decision store, a second correction voting system, or an automatic punishment system.

The central service is authoritative for AI review/correction state. EnthusiaStaff remains authoritative for normal human moderation/cases/punishments.

## Upstream gate

The central runtime/review contract is accepted.

W19:
- AI repo PR #40 final head `2954bd53b04472537ddfef9622832882b2d8c348`;
- merge `917aef4e97c539fea89d558f9e1be9d0d506b4a4`;
- exact-head CI #67 success;
- post-merge main CI #69 success.

Canonical review contract:
- `wsg138/AI-Moderation-API/docs/API-CONTRACT.md`.

Do not infer review semantics from old RoseChat automation behavior.

## Parallel EnthusiaStaff work — mandatory reconciliation

This repository currently has substantial reopening/moderation work in flight.

At the coordinator checkpoint, relevant open PRs included:
- #302 — post-open moderation platform reconciliation;
- #214 — cross-platform moderation integration;
- #280 and related reopening recovery/validation branches;
- multiple validation-only Staff Mode / Discord replacement PRs.

Before editing:
1. re-read live `main`;
2. inspect current open PRs touching moderation, Paper runtime wiring, Discord/platform identity, GUI/controller infrastructure, and integration contracts;
3. specifically reconcile #302 and #214 if they are still open;
4. do not copy stale architecture from an old branch;
5. do not absorb unrelated reopening work into W15;
6. if an overlapping PR lands, rebase/reconcile and rerun tests.

W15 must fit the accepted Staff architecture rather than becoming a parallel moderation subsystem.

## Existing Staff patterns to reuse

Read live versions of at least:

### RoseChat/staff integration
- `paper/src/main/java/net/enthusia/staff/paper/integration/RoseChatIntegration.java`;
- `RoseChatAutomatedModerationProvider.java`;
- integration contracts under `integration-contracts/.../rosechat/api/staff/`.

### Report GUI workflow
- `domain/.../report/ReportQueue.java`;
- `paper/.../report/ReportGuiState.java`;
- `ReportGuiController.java`;
- `ReportGuiRenderer.java`;
- `ActiveDutyReportStore.java`;
- `persistence/.../JdbcReportStore.java`;
- `JdbcReportQueryStore.java`;
- `paper/src/main/resources/gui/reports.yml`;
- `docs/wiki/pages/Reports-and-Evidence.md`.

### Punishment GUI/workflow
Read the current `paper/.../punishment/` GUI/controller code for interaction/authority patterns, but do not turn an AI correction into a punishment.

The existing report GUI already demonstrates important patterns:
- asynchronous bounded reads;
- viewer-bound state;
- permission rechecks on interaction/presentation;
- stale-state fencing so older loads cannot replace newer screens;
- pagination/refresh;
- confirmation before state-changing operations;
- separation of ordinary triage from sensitive evidence;
- bounded presentation rather than dumping raw JSON.

Reuse those engineering patterns.

## Legacy automated RoseChat moderation warning

Current Staff main contains `RoseChatAutomatedModerationProvider`, which supports the older RoseChat rolling-strike -> automatic public-mute path.

That is **not** the W15 review architecture.

Do not:
- route central `strike_recommendation` into that provider;
- automatically create a punishment because an AI review item exists;
- use the old 2-strike/30-day contract as the meaning of central Policy-v1 corrections;
- silently revive disabled AI punishment automation.

W13 is responsible for removing/bypassing the old local RoseChat semantic/strike authority when central mode is active. W15 should remain compatible with the legacy code while keeping central review actions separate.

## Central review API

Authentication uses:
- `X-Client-Id`;
- `Authorization: Bearer <secret>`.

Relevant permissions:
- `review:read`;
- `review:write`;
- optionally `review:admin` only if immediate admin override is deliberately supported.

Endpoints:
- `GET /v1/review-items`;
- `GET /v1/events/{event_id}`;
- `POST /v1/review-corrections`;
- `POST /v1/review-corrections/{proposal_id}/reject`.

### Review queue

`GET /v1/review-items` returns bounded pending NORMAL/URGENT items containing:
- event ID;
- timestamp;
- platform/profile;
- semantic label;
- message action;
- review priority;
- reason codes;
- optional incident ID.

Do not persist a duplicate authoritative queue in EnthusiaStaff merely to make the GUI work.

A small bounded cache for presentation/notifications is fine, but central state wins after refresh/restart.

### Event details

`GET /v1/events/{event_id}` returns an allowlisted event model:
- original message/event metadata;
- original AI decision;
- OpenAI advisory evidence when present;
- correction history;
- accepted correction;
- only context events recorded as material decision evidence.

Do not query or display arbitrary neighboring chat just because Staff has access to other logs.

Do not expose hidden chain-of-thought; the service does not provide it.

### Corrections

A correction contains the full separated Policy-v1 decision:
- semantic label;
- message action;
- review priority;
- strike recommendation;
- containment;
- optional containment duration;
- support flow;
- bounded reason codes.

Normal staff corrections are proposals. The central service requires **two distinct staff approvals** before acceptance.

Normal staff rejection also requires two distinct staff rejection votes.

Admin-authority requests may immediately accept/reject only when the authenticated central client has `review:admin`.

Original AI outcomes remain immutable. Accepted corrected outcomes are stored separately.

W15 must not build a conflicting local quorum/vote database.

## Reviewer identity and authority

Use a stable authoritative staff identity for `reviewer_id`.

Do not use display names as the durable identity when a UUID/stable staff ID is available.

Map local rank/permissions to central `authority` conservatively:
- ordinary reviewer -> `STAFF`;
- `ADMIN` only after a local authority check at both UI and service/application boundary.

If the central client credential has `review:admin`, local code must prevent a regular staff player from causing an ADMIN-authority request by manipulating inventory state/commands.

Add explicit tests for this.

If least-privilege deployment chooses a read/write-only client initially, the GUI must work without admin override.

## Networking / optional-service behavior

The AI service is optional.

EnthusiaStaff must not depend on it for:
- normal reports;
- punishments;
- freezes;
- staff mode;
- vanish;
- inventories;
- evidence;
- login;
- plugin readiness.

All HTTP must run off the owning Paper/server thread.

Use:
- bounded executor/queue;
- strict connect/request timeout;
- bounded response size;
- circuit/backoff behavior;
- cancellation/generation fencing on reload/disable;
- clean shutdown.

If AI is unavailable:
- normal Staff remains operational;
- AI review command/GUI shows a clear unavailable/degraded state;
- login does not block;
- no busy-loop/retry storm;
- no stale cached correction is presented as authoritative.

The central service currently lives with the Ticket Bot. Staff may run elsewhere. Base URI must be configurable and must not assume `localhost`. W15 does not authorize exposing the API publicly or modifying firewall/bind settings.

## Credentials/config

Never commit a real token.

Add config for:
- feature enable flag;
- base URL;
- client ID;
- bearer token source/reference;
- request/connect timeout;
- poll interval;
- queue/in-flight limits;
- notification permission/rank;
- optional admin override enablement;
- GUI presentation bounds.

Prefer environment/runtime secret injection or the repository's established secret mechanism.

Do not print tokens, Authorization headers, or full client JSON.

Invalid AI-review configuration disables/degrades only the AI review adapter. It must not push Staff into a general failure mode.

## Queue polling and notifications

The central API currently provides pull endpoints, not a push webhook.

Implement bounded polling rather than pretending there is an event subscription.

Requirements:
- poll asynchronously at a documented/configurable interval;
- fetch only a bounded review page;
- maintain a bounded set/cache of already-notified event IDs;
- notify authorized online reviewers when a new NORMAL/URGENT item first appears;
- distinguish URGENT visually/audibly without spamming every poll;
- on login, show current pending count from a recent cache or schedule an async refresh;
- if the cache is stale/unavailable, say so rather than blocking login;
- notification state may reset after restart if necessary, but do not create an unbounded durable mirror DB solely for notifications.

No notification may expose private message content to staff who lack the relevant AI review permission.

## Permissions

Define explicit W15 permissions consistent with Staff's rank tree.

At minimum separate:
- open/list AI review queue;
- view AI review detail;
- propose/approve/reject corrections;
- admin override if supported.

Recheck permission/rank:
- when command is invoked;
- when GUI opens;
- on every inventory action;
- immediately before any central write.

Do not trust a previously opened inventory after permission/rank changes.

## GUI requirements

Create a polished but bounded inventory workflow following existing Staff GUI conventions.

### Queue view

Show useful summary without raw-message dumping:
- priority;
- platform/profile;
- label/action;
- age/timestamp;
- short bounded reason summary;
- incident marker if present;
- pagination/refresh.

Prioritize URGENT items clearly.

### Detail view

Issue #16 requires message/context, source, action, label, scores, advisory, reason codes, timestamps, model/policy versions.

Show:
- original message, safely bounded/wrapped;
- only central `context_evidence`;
- source platform/profile/channel metadata;
- original message action;
- semantic label;
- review priority;
- strike/containment/support dimensions;
- local model scores/confidence;
- OpenAI advisory categories/scores if present;
- structured reason/rule codes;
- event/incident IDs in a bounded form;
- occurred time;
- local model version;
- Policy version;
- correction history/approval count;
- accepted correction if one exists.

Do not place arbitrary sensitive evidence in item lore. If text exceeds safe lore bounds, use paginated/detail surfaces consistent with Staff's existing evidence/privacy patterns.

Do not display raw JSON blobs.

### Actions

Provide clear actions such as:
- Correct decision;
- Should Allow;
- Should Block;
- Needs Review;
- category/semantic correction;
- approve an existing proposal;
- reject a proposal;
- refresh/back.

A convenience action must still construct a complete valid `CorrectionDecision`. Do not accidentally zero unrelated dimensions.

For example, “Should Allow” must not silently erase an urgent support flow unless the reviewer explicitly confirms the full corrected state.

Use review/confirmation UI before write operations.

After any write:
- display central response status;
- refresh authoritative event/queue state;
- do not optimistically remove an item if the central API says the proposal is still pending confirmation.

## Notes / text input

Correction notes may be up to the central API's bounded limit.

Use an established Staff private command/input path similar to report action notes if free text is needed. Do not capture notes through public chat.

Sanitize and bound note display.

## Concurrency / stale GUI safety

Central review state can change while a GUI is open.

Every action must:
- re-fetch or validate the current event/proposal state before write when needed;
- handle already-resolved proposals idempotently;
- handle conflict responses by refreshing;
- never overwrite a newer accepted correction from a stale inventory.

Fence overlapping async GUI loads so a slower old response cannot replace a newer page, matching the existing reports GUI pattern.

## Privacy

Raw production messages belong to the central private runtime DB, not this public repo.

Do not:
- commit runtime event samples;
- snapshot private review items into tests;
- write central message contents into public debug logs;
- copy private context into Discord/public chat;
- expose arbitrary neighboring chat.

Tests must use synthetic fixtures.

The GUI is a privileged staff surface, but still apply least exposure:
- show only central allowlisted event details;
- require permissions;
- avoid retaining content longer than necessary in process caches.

## Corrected-training eligibility

Accepted corrections may later become candidates for curated/redacted training export.

W15 should preserve enough central identifiers/status to support that future workflow, but it must **not**:
- automatically export raw events to GitHub;
- create training JSONL from production chat;
- send review content to a public repository.

Curated export is a separate reviewed/redacted task.

## Required tests

At minimum:

1. AI review disabled/unconfigured -> Staff normal startup unaffected.
2. central unavailable/timeout -> normal Staff unaffected; review GUI shows unavailable.
3. bounded polling discovers new items.
4. same item is not repeatedly spam-notified.
5. URGENT vs NORMAL presentation.
6. login notice uses bounded async/cache path and never blocks login.
7. unauthorized player cannot open queue.
8. permission removed after open -> clicks rejected.
9. queue pagination/refresh stale-load fencing.
10. event detail renders only allowlisted central fields.
11. bounded message/context/scores/reason presentation.
12. no hidden/raw JSON presentation.
13. normal STAFF correction creates proposal, not immediate acceptance.
14. two distinct STAFF approvals reflected correctly.
15. duplicate same-reviewer approval is idempotent/does not fake quorum.
16. STAFF cannot request ADMIN authority.
17. authorized ADMIN path works only when configured and locally authorized.
18. rejection path honors central two-staff/admin semantics.
19. resolved/stale proposal refreshes rather than overwrites.
20. convenience actions preserve/confirm all Policy-v1 dimensions.
21. AI correction never automatically creates a Staff punishment.
22. central outage does not affect reports/punishments/staff mode/vanish.
23. credentials/redaction tests.
24. executor/queue bounds and clean shutdown.
25. Bedrock/text fallback where existing Staff GUI standards require it.

Use a deterministic fake HTTP server/client. Do not call a live moderation service in repository tests.

## Existing Staff report architecture

Do not store AI review items as ordinary player reports merely because the report GUI already exists. Their semantics differ.

Reuse:
- controller/state/fencing patterns;
- rendering conventions;
- permission checks;
- private text-note patterns;
- pagination;
- async scheduling.

Keep AI review state in a dedicated adapter/model whose source of truth is the central API.

## Repository validation

Run the repository's canonical Gradle checks and focused module tests appropriate to the touched modules.

At minimum ensure:
- affected `domain` / `paper` / integration-contract tests pass;
- architecture/security checks remain green;
- GUI tests remain deterministic;
- no live Paper server is required for unit acceptance unless repository policy explicitly marks a behavior as staging-only.

If live staging evidence is later needed, that is a separate authorized validation step. Do not deploy from W15.

## Non-goals

Do not:
- deploy/restart Staff;
- mutate production DBs;
- change Policy v1;
- train a model;
- reimplement central correction voting;
- enable automatic AI punishment;
- merge AI items into ordinary report authority;
- expose review data through Discord/public chat;
- edit W13/W14 clients;
- redesign the broad Discord moderation platform;
- absorb unrelated reopening/Staff Mode PR work.

## PR completion comment

Include:
- exact head/base SHA;
- current overlapping PRs reconciled;
- config names (no secret values);
- permissions/rank mapping;
- poll interval/queue bounds;
- GUI screenshots or deterministic rendered evidence if repository practice supports it;
- fake-server API tests;
- normal staff/admin correction semantics;
- outage/fail-open evidence;
- repository Gradle/check results;
- confirmation that no automatic punishment/deployment/live mutation occurred.
