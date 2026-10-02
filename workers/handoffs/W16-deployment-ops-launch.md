# W16 launch packet — Ticket Bot host deployment/supervisor/operations

## Identity and authority

You are **W16**, the deployment/supervisor/operations worker for the Enthusia AI Moderation project.

Authoritative task: **AI-Moderation-API issue #17**.

Live GitHub is authoritative. Reconcile the current repository state before changing anything.

## Project goal

Enthusia is replacing a narrow OpenAI-only Minecraft filter with a central, modular moderation service shared by:

- RoseChat / Minecraft;
- the Discord Ticket Bot / Discord message moderation;
- EnthusiaStaff for evidence/review/punishment ownership.

The central service is an **optional add-on**. If it crashes, restarts, stalls, becomes unreachable, or fails health checks, normal Minecraft chat, Discord, Ticket Bot operation, and EnthusiaStaff operation must continue.

The local classifier will eventually make the low-latency live semantic decision. OpenAI Moderation remains advisory/asynchronous and must never be on the live latency-critical path.

## Current state you are starting from

Repository:
- `wsg138/AI-Moderation-API`
- current `main` contains merged W01 runtime foundation from PR #18.
- W01 accepted PR head: `6ba61295c41e231f03693cbb22f5cd2739a727a6`
- merge commit: `11f3eaa7b43a830ade0255a375edcce6fc85b13f`
- post-merge CI passed.
- `COORDINATOR-STATE.md` has the current project gate/state.

W01 currently provides:
- FastAPI service;
- private authenticated `POST /v1/moderate`;
- bounded/sharded rolling context;
- SQLite moderation event/evidence/review persistence;
- classifier interface + fail-open stub;
- asynchronous bounded OpenAI advisory path;
- health/readiness endpoints;
- bounded queues/deadlines;
- tests for split-message context and failure isolation.

Important: the current classifier is intentionally a stub and reports not-ready. This project is **not production-ready for live moderation yet**.

W00 is still interviewing the owner. Policy v1 is not frozen. Issue #19 will reconcile the provisional runtime contract after Policy v1. Your work must avoid depending on current provisional label/action details.

## Host and repositories

Target runtime host is the existing **Discord Ticket Bot Pterodactyl server**.

Known host facts from coordinator inspection:
- Pterodactyl allocation: **2 GB RAM**.
- Ticket Bot currently uses roughly **300 MB** in normal operation.
- Target layout:
  ```
  /
  ├── start-bots.js
  ├── enthusiasupport/
  └── ai-moderation/
  ```
- Existing Ticket Bot repository: `wsg138/enthusia-support-bot`.
- `start-bots.js` is tracked at that repository root.
- Ticket Bot application is under `enthusiasupport/`.
- AI runtime source belongs to `wsg138/AI-Moderation-API`.

Credentials/SFTP details exist on the owner’s PC, but **do not commit or copy credentials/tokens/API keys into GitHub**.

The same existing OpenAI API key may be reused by the new AI service through runtime secret/environment injection only. Do not ask the owner to paste it into chat.

## Mandatory reading before work

Read all of:

From `wsg138/AI-Moderation-API`:
- `README.md`
- `COORDINATOR-STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/API-CONTRACT.md`
- `docs/WORKER-SYSTEM.md`
- `docs/WORKER-LAUNCH-STANDARD.md`
- `policy/SOURCE-BASELINE.md`
- issue #17
- issue #19, so you understand which API details are intentionally not frozen

From `wsg138/enthusia-support-bot`:
- current `start-bots.js`
- root package/config files
- `enthusiasupport/package.json`
- current Ticket Bot startup/shutdown behavior
- existing health/restart/backoff behavior
- any current Pterodactyl deployment docs/scripts

Inspect the live Ticket Bot host only **read-only** if needed to verify paths/runtime assumptions. Do not deploy without explicit coordinator authorization.

## Your scope

Prepare the deployment/operations layer so the AI service can later be placed under `/ai-moderation/` and started by the same Pterodactyl container without making it a critical dependency.

You own:

1. **Packaging/runtime command**
   - define how the Python 3.12 service is installed/run;
   - pin/document dependencies;
   - define working directory and database/model paths;
   - do not bundle secrets into artifacts.

2. **Supervisor changes**
   - extend `start-bots.js` so it starts the Ticket Bot and AI service as separate child processes;
   - Ticket Bot remains critical according to its existing semantics;
   - AI service is explicitly non-critical;
   - AI child crash must not terminate Ticket Bot or the Pterodactyl container;
   - use bounded restart/backoff to avoid crash loops;
   - graceful SIGTERM/SIGINT shutdown for both;
   - avoid zombie/orphan child processes.

3. **Readiness/liveness**
   - use `/health/live` for process liveness;
   - use `/health/ready` for classifier/runtime readiness;
   - do not make Ticket Bot startup/readiness depend on AI readiness;
   - log AI degraded/unready state clearly.

4. **Networking**
   - bind the moderation API privately/local-only where practical;
   - do not expose it publicly just because FastAPI can listen on 0.0.0.0;
   - document the eventual private address clients should use;
   - preserve the ability to move the AI service to another container later without changing its API.

5. **Secrets**
   - reuse OpenAI via `OPENAI_API_KEY` or equivalent runtime secret;
   - create separate random client bearer tokens for RoseChat/Discord/EnthusiaStaff at deployment time, not in Git;
   - document secret names, not values.

6. **Persistence**
   - identify a persistent path for `runtime-data/moderation.sqlite3`;
   - preserve raw production moderation records across AI restarts;
   - model artifacts/config must persist across restarts;
   - rollback must never silently destroy moderation data.

7. **Resource controls**
   - design around 2 GB total container RAM with Ticket Bot baseline around 300 MB;
   - avoid a production design requiring GPU;
   - reserve enough headroom for Ticket Bot bursts;
   - document memory/CPU expectations and how to detect pressure;
   - do not assume the final ONNX model size until W12.

8. **Rollback/smoke plan**
   - exact reversible steps;
   - verify Ticket Bot stays online if AI is deliberately killed;
   - verify AI restarts with backoff;
   - verify AI unready does not stop Ticket Bot;
   - verify graceful Pterodactyl stop;
   - verify persistent DB survives AI restart;
   - verify no secret appears in logs.

## Critical failure boundary

The following behavior is mandatory:

```text
AI process exits
→ Ticket Bot stays online
→ supervisor logs the AI failure
→ AI retries after bounded backoff
→ normal Discord/Ticket Bot operation continues

AI service returns 503 / is unready
→ Ticket Bot stays online
→ future Discord moderation client must fail open

AI service repeatedly crash-loops
→ supervisor must not busy-loop or take down the container
```

Do not make `start-bots.js` exit simply because the AI child exits.

## What you must NOT do

- Do not deploy to production.
- Do not restart the live Ticket Bot/Pterodactyl server.
- Do not install packages on the live server.
- Do not modify RoseChat.
- Do not modify EnthusiaStaff.
- Do not implement Discord moderation behavior; W14 owns the Discord client.
- Do not train or choose the final semantic model; W12 owns that.
- Do not freeze provisional Policy-v1 API fields; #19 will reconcile them.
- Do not commit raw production chat, DB files, SFTP credentials, bot tokens, API keys, or client bearer secrets.

## Branch / PR expectations

AI repo:
- create `w16/deployment-ops` from live `main` if AI-repo deployment docs/files are needed.

Ticket Bot repo:
- if `start-bots.js` must change, use a dedicated branch such as `ai-moderation/optional-service-supervisor` from live `main`.
- keep changes narrow and reviewable.

If work spans both repositories, open separate PRs and cross-link them. Do not mix unrelated Ticket Bot changes into this work.

## Acceptance evidence

Before declaring complete, provide:

- exact branch/head(s);
- changed-file summary;
- tests for supervisor failure isolation where feasible;
- a local/synthetic smoke demonstration showing AI child failure does not kill Ticket Bot supervisor;
- documented startup command and directory layout;
- documented secret names;
- documented rollback;
- documented resource assumptions;
- confirmation that no deployment occurred;
- CI results for every PR.

Do not merge your own PR unless the coordinator explicitly tells you to.
