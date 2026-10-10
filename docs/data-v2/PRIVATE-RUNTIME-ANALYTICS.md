# Runtime moderation analytics — private read-only foundation

This stage produces aggregate evidence from the **existing canonical SQLite
moderation store**, rather than adding a second queue or duplicate event sink.
The source already persists finalized message action, semantic label, model and
policy versions, bounded scores and rule hits, confidence, review priority,
strike/mute recommendations, support flow, latency and accepted staff
corrections. The canonical store is the private, access-controlled drill-down
source. It can contain raw messages; **never upload its database to public
GitHub or attach raw data to a PR**.

## Offline aggregate analyzer

`tools/data_v2/runtime_analytics.py` reads an explicitly supplied local
SQLite database in **read-only URI mode** with `PRAGMA query_only=ON`.
No schema migration, mutation, live hook, or server deployment is involved.

```bash
python -m tools.data_v2.runtime_analytics \
  --database /private/enthusia/moderation.sqlite \
  --from-day 2026-10-01 \
  --until-day 2026-10-11
```

Dates are UTC, start-inclusive and end-exclusive. It emits JSON aggregates
only, grouped by model+policy, channel, UTC day and semantic label. Fields:
canonical finalized count, BLOCK/REVIEW count, degraded and FAIL_OPEN cases,
strike/mute *recommendations*, accepted corrections, and p50/p95/p99
end-to-end recorded latency. For accepted corrections, it also counts **which
structured decision fields changed** (message action, semantic label, review
priority, strike, containment, mute duration, support flow), without exposing
original or corrected message text or reviewer identities. These counts are
staff disagreement categories, not unbiased estimates of error prevalence.
Per-group outputs with fewer than **10 events**
are suppressed. Inputs are capped at 500,000 finalized events per window to
avoid unbounded reports; split larger private time windows.

It does **not** query or emit message text, author identity, case ID, event ID,
reviewer identity, private context, prompt, notes, original evidence, or
individual per-message scores. It uses only source-known aggregate dimensions;
model/category labels that do not match a conservative metadata token format
are replaced with `REDACTED_UNKNOWN`.

**This is not an accuracy metric.** An accepted correction is a selected,
potentially biased staff review outcome, not an independently adjudicated
random sample. An unchanged case has *not* been certified correct. Messages
dropped by upstream clients, disconnected chat bridges, or a client-side
timeout before the API persists an event cannot be guaranteed present.
The counts cover canonical database `FINAL` events only, not every network
attempt or every unobserved chat message.

## What we still need for full observability

1. **W25 per-decision analysis** (separate draft PR #89): one private
   six-head probability ledger per model/run with stable pseudonymous case
   HMACs, per-label errors, cross-model disagreements and capture coverage.
2. **API per-stage trace versioning:** preserve explicit classifier and
   optional advisory model votes, model artifact/checksum, calibration and
   threshold version, uncertainty/abstention, per-stage timing, rule firing,
   context and memory snapshot provenance. Avoid duplicating raw private
   text; bound the trace size, enforce staff-only access and retention.
3. **End-to-end delivery counters:** record client-side mirror/retry/dedupe
   outcomes, API queue timeouts, failed writes, replay collisions and
   estimated event gaps. Some outages can only be measured by client-local
   counters and cannot be reconstructed from the API DB.
4. **Independent correction truth pipeline:** protect original AI outcome,
   attach authorized staff review and correction evidence separately, then
   independently adjudicate sampled cases before claiming precision or
   training eligibility.
5. **Versioned private dashboard:** time series, model/policy comparisons,
   safe benign FPR when independent truth exists, critical recall, channel
   and banter slices, drift, calibration, latency and false sanctions, with
   minimum cell sizes, sampling denominators and confidence intervals.
6. **Prospective two-cohort acceptance** (separate draft PR #88) remains
   mandatory to substantiate near-99% **whole-decision** correctness, not
   just a popular model having many ALLOW predictions.

Read-only aggregate analysis is compatible with shadow-only and preproduction
work. Nothing here enables message blocking, automatic strikes/mutes, bans,
policy v2 or future background collection. Runtime source retention, user
privacy and authorized access must be reviewed before deploying dashboards.
