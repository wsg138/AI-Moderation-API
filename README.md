# Enthusia AI Moderation API

Central, fail-open moderation service for Enthusia Minecraft and Discord.

## Goals

- One shared moderation API for RoseChat, Discord, and EnthusiaStaff.
- Minecraft-aware semantic classification with multi-message context.
- Local classifier is the live decision path; OpenAI Moderation is advisory/secondary.
- Every moderation event is recorded with structured scores, reason codes, model/policy versions, context IDs, and review state.
- Human review feeds a curated training dataset.
- AI outages must never break Minecraft chat, Discord chat, or normal EnthusiaStaff operations.
- Automatic punishments remain a separate EnthusiaStaff policy decision and are disabled until accuracy is proven.

## Planned runtime

The service will run as a separate process in the existing Discord Ticket Bot Pterodactyl server under an `ai-moderation/` folder. The Ticket Bot supervisor may start/restart it, but the AI process is non-critical: if it crashes, the Ticket Bot stays up.

Clients:

- **RoseChat**: private API client, short timeout, circuit breaker, fail-open.
- **Discord Ticket Bot**: sends eligible Discord messages to the same API and applies returned message actions.
- **EnthusiaStaff**: owns review workflow, evidence, strikes, punishments, and the in-game review GUI.

## Repository layout

```text
docs/                    Architecture, API, privacy, worker contracts
policy/                  Human moderation policy and interview records
data/
  synthetic/             Generated/reviewed synthetic training data
  curated/               Human-approved training examples
  eval/                  Frozen evaluation sets
workers/                  Worker handoffs and ownership rules
service/                  AI moderation API runtime
training/                 Training/export/evaluation pipeline
integrations/             Client contracts/examples
```

## Data rule

This repository is currently **public**. Never commit API keys, Discord tokens, SFTP credentials, raw production chat logs, account identifiers, private staff data, or unreviewed production evidence.

Generated phrases, policy-interview answers, synthetic datasets, schemas, evaluation corpora, and deliberately curated/redacted training examples belong here.

Raw production moderation events are stored by the deployed AI service in its private runtime data store. A reviewed/redacted export process may later promote selected examples into `data/curated/`.

## Decision evidence

The system stores structured decision evidence, not hidden chain-of-thought. A decision record should include:

- final action and label;
- class probabilities / model scores;
- deterministic rule hits;
- relevant context message IDs;
- normalized semantic reason codes;
- local model version and policy version;
- OpenAI moderation scores when available;
- latency and failure/fallback state;
- human review/correction if supplied.

## Initial phases

1. Policy interview with the owner.
2. Freeze Policy v1 and dataset schema.
3. Generate balanced synthetic dataset in parallel worker packages.
4. Deduplicate, contradiction-check, and create train/validation/evaluation splits.
5. Fine-tune and export a small classifier to ONNX.
6. Build the central API/context store and advisory OpenAI path.
7. Integrate RoseChat, Discord, and EnthusiaStaff review tooling.
8. Shadow-test, review disagreements, retrain, then cautiously enable message blocking.
9. Keep automatic punishments disabled until separately accepted.
