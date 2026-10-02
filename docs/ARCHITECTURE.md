# Architecture

## Core boundary

`AI-Moderation-API` is a central, private moderation service. RoseChat, Discord, and EnthusiaStaff are clients/consumers; none should embed independent copies of the semantic policy.

```text
RoseChat ─────────────┐
                     │ private authenticated API
Discord Ticket Bot ──┼────────► AI Moderation API
                     │              │
EnthusiaStaff ───────┘              ├─ rolling context store
                                    ├─ deterministic safety rules
                                    ├─ local semantic classifier
                                    ├─ OpenAI advisory moderation
                                    ├─ durable event/review store
                                    └─ structured decision evidence
```

## Hosting

Production target: a separate `ai-moderation/` process inside the existing Discord Ticket Bot Pterodactyl server.

The Ticket Bot currently has enough memory headroom for a small quantized text classifier. The AI service must remain independently restartable and non-critical to the Ticket Bot process.

If resource pressure later becomes a problem, the same service can move to another Pterodactyl container without changing the API contract.

## Live decision path

1. Client submits the new message plus source metadata.
2. Service stores the event and updates rolling context.
3. Deterministic normalization/rules run.
4. Local semantic classifier evaluates the current message plus relevant prior messages.
5. Policy engine returns `ALLOW`, `REVIEW`, or `BLOCK` with structured reason codes.
6. Client applies only the message-level action it is authorized to apply.
7. OpenAI Moderation runs asynchronously/advisory and is stored for comparison/training.
8. Human review can later correct the label/action.

OpenAI must not be on the latency-critical path.

## Context ownership

The central service owns semantic context so Minecraft and Discord use the same rules.

Each event includes:
- platform;
- server/guild and channel/scope;
- stable external message ID;
- sender pseudonymous ID;
- timestamp;
- text;
- reply/reference metadata where available.

Context should favor:
- the same sender's recent 3–5 messages;
- recent messages in the same channel/scope;
- tight time windows (initial target roughly 30–45 seconds);
- explicit reply/reply-to relationships.

A later message can change the interpretation of prior messages. The response may therefore contain `related_message_ids` so the client can remove earlier messages when a split-message threat becomes clear.

Example:

```text
A: im gonna stab you
A: irl
```

The second event may produce `BLOCK` plus both message IDs.

## Fail-open contract

AI is an add-on.

For RoseChat/Discord:
- timeout, connection failure, malformed response, queue saturation, service restart, model load failure, or circuit-open state => do not block normal chat;
- clients use a strict deadline and bounded async queue;
- no AI network work on Paper's main thread;
- repeated failures open a circuit breaker;
- health recovery closes it automatically.

For EnthusiaStaff:
- normal moderation/cases/staff tools never depend on AI availability;
- AI can submit evidence/review items, but it never directly owns bans/mutes.

## Decision evidence

Store structured evidence, not hidden chain-of-thought:
- action;
- semantic label;
- per-class probabilities;
- rule hits;
- reason-code list;
- relevant context message IDs;
- local model version;
- policy version;
- OpenAI moderation model/scores;
- local/OpenAI disagreement marker;
- latency;
- fallback/health state;
- human review outcome.

## Privacy / repository boundary

The GitHub repository is currently public. Synthetic phrases, interview records, policy definitions, schemas, tests, and deliberately curated/redacted examples belong in GitHub.

Raw production chat events and identifiers stay in the service's private runtime datastore. They are not auto-pushed to GitHub. Reviewed/redacted examples may be promoted into the curated dataset.
