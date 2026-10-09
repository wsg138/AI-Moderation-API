# Deployment and operations

This document prepares the AI moderation service for the existing Ticket Bot Pterodactyl container. It does **not** authorize deployment. W16 must not install, restart, or modify the live host until the coordinator explicitly authorizes it.

## Target layout

```text
/
├── start-bots.js                  # from wsg138/enthusia-support-bot
├── enthusiasupport/               # existing critical Ticket Bot
└── ai-moderation/                 # checkout/release from this repository
    ├── .venv/
    ├── deployment/
    ├── service/
    └── runtime-data/
        ├── moderation.sqlite3
        └── models/                # reserved for the accepted W12 model artifacts
```

The AI process is optional. Ticket Bot startup, Discord connectivity, and Pterodactyl readiness must never wait for AI readiness.

## Install and runtime command

The target runtime is Python 3.12. From `/ai-moderation`:

```bash
bash deployment/install-runtime.sh
bash deployment/run-service.sh
```

`install-runtime.sh` creates `.venv`, installs the exact runtime/build versions in `deployment/requirements-runtime.lock`, installs this repository with `--no-build-isolation --no-deps`, and creates `runtime-data/`. It does not delete or recreate the moderation database.

The supervisor should start `deployment/run-service.sh`. The wrapper defaults to:

```text
http://127.0.0.1:8787
```

It refuses a non-loopback bind unless `AI_MOD_ALLOW_NONLOCAL_BIND=true` is explicitly set. That override is only for a future approved private-network move; it is not permission to expose the API publicly.

## Health contract

- `GET /health/live` is process liveness.
- `GET /health/ready` is durable-store + classifier/runtime readiness.
- Without an accepted/configured W12 ONNX bundle, the service stays in stub/fail-open mode and `/health/ready` returns HTTP 503. After W12 acceptance, readiness is HTTP 200 only when the configured checksum-verified classifier bundle loads successfully.
- An unready or unavailable AI service must not stop or delay the Ticket Bot.

The Ticket Bot supervisor may restart the AI child after repeated liveness failures. Readiness failure alone is a degraded state and must not restart or stop the Ticket Bot.

## Runtime environment

`.env.example` is a variable-name/reference file only. The Python service and `deployment/run-service.sh` do **not** auto-load a dotenv file. Configure production values through Pterodactyl/runtime environment injection so credentials never need to live in the checked-out source tree or appear on the command line.

## Runtime secrets

Secret names only:

- `OPENAI_API_KEY` — existing OpenAI key, injected through the runtime environment.
- `AI_MOD_CLIENTS_JSON` — client allowlist and bearer credentials.
- one random bearer token each for the RoseChat, Discord, and EnthusiaStaff client identities.

Generate client tokens on the deployment host or another trusted secret-management surface, for example:

```bash
python3.12 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Do not paste generated values into GitHub, PR comments, startup commands, or logs. The service reads credentials from the environment and does not persist them.

## Persistent data

The production database path should remain:

```text
/ai-moderation/runtime-data/moderation.sqlite3
```

Keep the entire `/ai-moderation/runtime-data/` directory outside any destructive release cleanup. Accepted model artifacts must live under `runtime-data/models/` (or another explicitly persistent path chosen at deployment) rather than inside a disposable virtual environment. Configure `AI_MOD_ONNX_METADATA_PATH` and `AI_MOD_ONNX_METADATA_SHA256` to the accepted metadata file and its recorded SHA-256; the runtime then verifies the metadata, vectorizer, every ONNX head, schema version, and `w12-v2` serialization contract before reporting classifier readiness.

Rollback rules:

1. stop only the AI child or stop the container gracefully if a full release rollback is required;
2. preserve `runtime-data/` unchanged;
3. restore the previous AI source/release;
4. rebuild only `.venv` if dependency rollback is needed;
5. start the previous AI release;
6. verify the existing database opens and `/health/live` responds.

Never solve a rollback by deleting or replacing `moderation.sqlite3`.

## Resource envelope

**Owner-reported allocation (2026-10-09):** the Ticket Bot Pterodactyl
server now has **3 GB RAM and 800% configured CPU allocation**. The owner
reports that the SMP does not share this allocated Ticket Bot CPU split.
These are owner-provided allocation settings, **not measured AI consumption,
guaranteed CPU pinning or an observed host benchmark**. Ticket Bot reliability
remains the priority. The earlier estimate of roughly 300 MB Ticket Bot RAM
usage was planning context, not a newly measured production value.

W12 v2 currently measures the selected FP32 TF-IDF/ONNX bundle at roughly 1 MB of model/vectorizer artifacts and around 1 MB attributable RSS on GitHub's CPU evidence host. Final W20 unseen acceptance is still required before production use. Use these operating rules:

- no GPU dependency for the currently prepared small ONNX inference candidate;
- start with one AI inference thread/worker and bounded queue; do not
  interpret an 800% Pterodactyl allocation as a reason to launch eight workers;
- if a later DeBERTa-based model is approved, independently benchmark memory,
  95th/99th-percentile classification latency and CPU bursts before selecting
  its allocation. Do not use the lightweight ~1 MB ONNX artifact measurement
  as a DeBERTa RAM forecast;
- keep the AI worker count at the current bounded defaults unless measured load requires a change;
- do not raise queue sizes merely to hide sustained overload;
- keep several hundred MB of free/container headroom for Ticket Bot bursts and Python/model variance;
- do not enable a model whose measured steady-state memory plus Ticket Bot usage leaves the container close to its 3 GB allocation.

Watch the Pterodactyl memory graph, OOM/restart events, AI queue depth from `/health/ready`, and repeated supervisor liveness failures. If pressure appears, disable/revert the AI service before reducing Ticket Bot headroom.

## Deployment-time smoke plan

Run only after explicit deployment authorization.

1. Start the container and confirm the existing Ticket Bot reaches its normal Discord-ready marker.
2. `curl -fsS http://127.0.0.1:8787/health/live` must return `{"status":"ok"}`.
3. Check `/health/ready`. Before a model is configured, HTTP 503/`not_ready` is expected and must not affect the Ticket Bot. With the accepted model configured, require HTTP 200/`ready`, `classifier_mode=onnx-baseline-tfidf`, the expected `local_model_version`, and the expected metadata checksum before enabling any client.
4. Record the SQLite file identity/size, stop only the AI child, and confirm:
   - Ticket Bot remains online;
   - the supervisor logs the AI exit;
   - AI restart attempts use increasing bounded delays;
   - the same SQLite file remains present after restart.
5. Deliberately make the AI runner fail in a controlled staging/smoke window and confirm repeated failures never busy-loop or terminate the Ticket Bot/container.
6. Stop the Pterodactyl server normally and confirm both children receive graceful termination; no AI child remains orphaned.
7. Review startup/supervisor logs and confirm no bearer token, `AI_MOD_CLIENTS_JSON` value, or OpenAI key is printed.

## Rollback trigger

Rollback the AI release (without touching Ticket Bot data or moderation data) if any of these occur:

- Ticket Bot stability changes because of the supervisor change;
- AI restarts become a tight loop;
- AI cannot be terminated cleanly;
- memory pressure threatens the Ticket Bot;
- secrets appear in logs;
- the persistent database cannot be reopened by the previous release.

Because the API contract is independent of the hosting location, the AI service can later move to another private container by changing the client base address and runtime bind/network configuration rather than changing moderation semantics.
