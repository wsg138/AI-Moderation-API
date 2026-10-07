# Architecture

## Core boundary

`AI-Moderation-API` is the central private moderation service. RoseChat, the Discord Ticket Bot, and EnthusiaStaff are clients/consumers; they do not embed separate semantic-policy implementations.

```text
RoseChat ─────────────┐
                     │ authenticated private API
Discord Ticket Bot ──┼──────► AI Moderation API
                     │           │
EnthusiaStaff ───────┘           ├─ scope gate / canonical dedup
                                 ├─ bounded relationship context
                                 ├─ structured durable memory
                                 ├─ local semantic classifier
                                 ├─ policy decision dimensions
                                 ├─ incident aggregation
                                 ├─ SQLite event/review store
                                 └─ async OpenAI advisory
```

The AI service is optional. Chat and normal EnthusiaStaff functionality must remain usable if it is stopped, unhealthy, saturated, or restarting.

## Live path

1. Authenticate the caller and validate platform/channel profile metadata.
2. Return immediately for exempt profiles without ingesting the text.
3. Reserve an idempotent canonical event or resolve a mirror/retry.
4. Retrieve bounded relevant short-term context and structured memory.
5. Run the local classifier under a strict timeout.
6. Convert classifier output into separate semantic/action/review/strike/containment/support dimensions.
7. Atomically finalize decision evidence and optional incident linkage.
8. Return the local decision to the client.
9. Enqueue OpenAI Moderation asynchronously for advisory evidence only.
10. Allow later human correction without mutating the original AI decision.

OpenAI is never on the latency-critical path.

## Scope and privacy gate

Channel profiles are explicit runtime metadata rather than literal production channel IDs. Discord ticket, staff-only, and configured exempt profiles exit before event reservation. Their text is not stored, classified, added to context, or used by incidents/memory.

## Context ownership

The central service owns semantic context so Minecraft and Discord use the same linkage rules. Context is relationship-bounded rather than global.

Useful links include same-sender continuity, PM/public participant relationships, targets, explicit replies, conversation IDs, and authoritative cross-platform identity IDs. Candidate scope count, message count, time window, and intervening-message count are bounded.

The request dispatcher hashes a canonical identity when available, otherwise the platform/server/sender tuple, so related messages from one sender stay FIFO even when they cross public/private channels.

## Canonical events and mirrors

A logical message may have multiple platform message IDs. `canonical_message_id` identifies that logical message; `message_aliases` maps each platform copy to one moderation event. This prevents mirrors from double-counting incidents, strikes, or context while still preserving all deletion targets.

## Incident aggregation

A message remains a message. Multi-message behavior is represented separately as an incident with event links, sender IDs, target IDs, severity, kind, and coordination state. The design supports repeated harassment, unwanted contact, dogpiling, threats, doxxing, blackmail, grooming, and safety incidents without concatenating different speakers into one authored statement.

## Durable memory

Policy-relevant memory is structured data rather than model weights.

Punishment-oriented `moderation_memory` is platform-separated and supports target-specific facts, confidence/provenance, confirmation state, and expiry. `safety_memory` is stored/retrieved separately so self-harm/safety history cannot become punishment reputation. `identity_links` reserves the durable authoritative account-link model.

Memory absence or read failure is neutral/fail-open; it never fabricates history.

## Restart recovery

Recent finalized moderated events are rehydrated from SQLite into bounded in-memory context at startup. Exempt rows are defensively ignored and canonical IDs deduplicate mirror copies.

A rehydration failure keeps readiness false and forces moderation into fail-open operation until a clean restart. This avoids making blocking decisions from a partially recovered context state.

## Persistence and migrations

SQLite stores raw private runtime events, structured decision evidence, OpenAI advisory results, incidents, durable memories, identity links, and correction workflow state.

Schema changes are versioned with transactional `PRAGMA user_version` migrations. Migration failure rolls back instead of deleting/recreating the database. A newer unsupported schema is rejected. Schema v3 adds only the partial authoritative-identity/time index used by the bounded support-context read; it does not rewrite moderation decisions.

## Support enrichment boundary

Support may optionally request privacy-minimized historical decision metadata through the dedicated `support:context` permission. The lookup key is an authoritative `sender_identity_id`; there is no username or raw-sender fallback. Raw message text, neighboring context, channel/scope IDs, and platform sender IDs remain inside the moderation service. Accepted staff corrections are treated as the effective decision for this read.

Support availability never participates in live moderation decisions, and moderation unavailability must degrade support enrichment to no context rather than block support.

## Review/corrections

Review reads use explicit public response models. Only context event IDs recorded as material evidence are exposed with an event.

Corrections use proposals/votes. Two distinct normal staff approvals finalize; Admin+ may finalize immediately. Rejections follow the same two-person/Admin+ authority model. The original AI decision remains immutable beside the accepted correction for audit and later curated training export.

## Fail-open boundary

Classifier, memory, context, storage, restart-rehydration, migration/readiness, queue, timeout, and OpenAI failures must not create a harmful block by default. If durable finalization of a classifier decision fails, the caller receives an unpersisted fail-open allow rather than the original block.

Automatic punishments remain disabled during calibration/acceptance. The central service returns containment/strike recommendations; EnthusiaStaff owns authoritative punishment state and staff own bans.

## Repository/data boundary

The GitHub repository is public. Policy, schemas, synthetic examples, tests, and deliberately redacted/curated data may live here. Raw production messages, account identifiers, secrets, and private moderation evidence remain in private runtime storage.
