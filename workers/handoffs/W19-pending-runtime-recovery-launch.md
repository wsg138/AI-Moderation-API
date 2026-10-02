# W19 launch packet — Repair PENDING-event and pending-mirror recovery

## Identity

You are **W19**, the runtime-recovery repair worker for Enthusia AI Moderation.

Authoritative issue: **#39 — Repair PENDING-event and pending-mirror recovery**.

Create branch `w19/pending-recovery` from the current live `main` when you start.

Do not deploy. Do not modify RoseChat, Ticket Bot, or EnthusiaStaff. Open one PR to `main` and do not self-merge.

## Why this exists

Policy-v1 runtime reconciliation PR #29 was merged into `main`, but coordinator review had already identified two recovery defects in the PENDING-event path. They are not policy problems; they are correctness/idempotency problems.

No production deployment has occurred, so the correct action is to fix forward before W13/W14/W15 build against the runtime as frozen.

## Mandatory reading

Read:

- issue #39;
- PR #29 conversation/comments, especially the coordinator blocker comment;
- `service/moderation_api/storage.py`;
- `service/moderation_api/runtime.py`;
- `service/moderation_api/models.py`;
- `service/moderation_api/migrations.py`;
- `tests/test_api.py`;
- `tests/test_storage.py`;
- `tests/test_restart_failopen.py`;
- `docs/API-CONTRACT.md`;
- `policy/POLICY-v1.md`;
- `COORDINATOR-STATE.md`.

Run the full current suite before changing code so you know the baseline.

## Blocker A — stranded PENDING reservation

Current flow can be:

1. `reserve_event()` inserts a PENDING moderation event and external-message alias;
2. classification succeeds;
3. `finalize_event()` fails, or the process dies before finalization;
4. runtime fails open;
5. database row remains PENDING;
6. later retry of the same message raises `EventInProgress` indefinitely.

That permanently poisons the idempotency/canonical key and violates the intended fail-open recovery boundary.

### Required behavior

Implement **bounded stale-PENDING recovery**.

Requirements:

- an event that is still plausibly being processed must not be stolen/deleted;
- stale detection must be based on durable timestamps/lease state, not an unbounded wait;
- stale recovery must preserve one-event semantics;
- external-message retry after stale recovery must be able to classify/finalize normally;
- canonical mirror retry must resolve to the same logical event;
- a stale recovery path must not silently lose already-recorded mirror aliases;
- concurrent active requests must not both become owners;
- crash/finalize-failure recovery must be deterministic and testable.

A lease/attempt marker, compare-and-swap update, or equivalent SQLite-safe mechanism is acceptable. Do not solve this by blindly deleting all PENDING rows.

## Blocker B — mirror arrives while canonical is PENDING

Current mirror path checks the canonical event and may raise `EventInProgress` before recording the mirror alias.

That means a Discord/Minecraft mirror can become visible, fail open, and never be durably linked to the canonical event. If the canonical result later BLOCKs, the service may not know the mirrored platform message ID to delete.

### Required behavior

When a mirror arrives while canonical processing is active:

- persist/link the alias safely to the canonical event without creating another moderation event;
- preserve request/canonical fingerprint conflict checking;
- do not count the mirror as another incident/strike/context event;
- use bounded wait/replay or another deadline-compatible mechanism;
- if the caller ultimately times out/fails open, a later retry must cleanly replay the canonical decision;
- after finalization, `related_messages` must contain both canonical and mirror refs;
- no active canonical worker may be disrupted by stale-cleanup logic.

## Deadline / fail-open interaction

The public client contract remains fail-open.

If bounded waiting exceeds the request deadline, the client may receive the existing 503/fail-open-required behavior. That is acceptable **only if** durable alias/idempotency state remains recoverable and a later retry can replay correctly.

Do not extend the live moderation hold just to hide the race.

## Tests required

Add focused regression/concurrency tests for at least:

1. finalize failure leaves a recoverable PENDING event;
2. retry before stale threshold does not steal an active event;
3. retry after stale threshold safely recovers and finalizes;
4. crash-like pre-seeded stale PENDING row recovers;
5. mirror arrives before canonical finalizes;
6. only one moderation event exists after concurrent canonical + mirror;
7. mirror alias persists even when mirror caller times out/fails open;
8. later mirror retry replays the final canonical decision;
9. related refs contain both platform copies after finalization;
10. conflicting mirror content/canonical fingerprint still returns conflict;
11. existing idempotency, fail-open, restart, migration, exempt-scope, incident, and review tests remain green.

Avoid flaky wall-clock sleeps where possible; inject/configure time or use deterministic timestamps.

## Configuration

If a stale-PENDING lease threshold needs configuration:

- add a clearly named bounded setting;
- choose a conservative default above normal moderation processing time;
- document it in `.env.example` and `docs/API-CONTRACT.md`;
- validate it as positive;
- do not make the request deadline depend on this threshold.

## Migration safety

If schema changes are needed:

- add a new schema version rather than rewriting v1 assumptions;
- migrate transactionally;
- preserve existing v1 dev/runtime DBs;
- add migration tests;
- never delete/recreate the database.

## Acceptance

Before opening the PR:

- Ruff green;
- strict mypy green;
- complexity gate green;
- full pytest green;
- dataset QA step green;
- wheel build green;
- exact-head CI green.

Completion report must include:

- PR URL;
- exact head SHA;
- chosen stale-recovery mechanism;
- mirror-pending behavior;
- schema/config changes if any;
- exact regression tests added;
- test count;
- exact-head CI run;
- confirmation that no production deployment, secrets, or production data were touched.
