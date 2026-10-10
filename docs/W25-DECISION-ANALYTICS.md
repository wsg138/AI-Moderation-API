# W25 moderation analytics: every model, every test, traceable decisions

**Implementation stage: offline W25 evaluation, not live chat logging.**
This adds machine-readable per-decision ledgers to the existing saved W25
`PredictionBundle` evaluation artifacts. No models are trained or invoked by
this tool, no acceptance datasets are read by default, and no live moderation
behavior or auto-punishment rules change.

## Why

Aggregate accuracy hides exactly the cases we need to improve. An overall 99%
figure can still represent hundreds of wrongful chat blocks, too many missed
threats, or a model that proposes incorrect strikes. We need a **joinable event
ledger for each candidate, seed, threshold/config revision and evaluation
suite**, with a separate cross-model disagreement report and evidence coverage
audit.

### What is actually captured today

One immutable run JSONL file includes:

| Scope | Recorded evidence |
|---|---|
| Run manifest | Run ID, candidate/model name, seed, suite fingerprint, model artifact and configuration SHA-256, policy version, class/probability ordering, cardinality, known limitations |
| Each case | Stable **HMAC-pseudonymous** case and family key (not player ID), gold label/action/review/strike/containment/support, predicted values for all six W25 heads |
| Scores | **Every class probability** for every head, predicted action confidence, uncertainty, and matching/nonmatching heads |
| Failure categories | Wrongful BLOCK of an ALLOW, missed BLOCK, false strike, false mute recommendation; source channel profile, domain, difficulty and curated reason-code labels for private error slicing |
| Known missing fields | Prediction-time p50/p95 per case, raw logits, deterministic policy/lexical trace, generated explanation, learned mute duration; explicitly `null`, **never invented** |
| Comparison | Per-head disagreement counts, pseudonymous case keys for private drill-down, both-model misses, false-action/sanction counts and channel-level errors for each run |
| Completeness | Expected vs observed run IDs; missing, unexpected or invalid ledger names; no silent success when evidence is absent |

The W25 classifier has **six** learned heads. The accepted gold datasets also
carry mute duration, but W25 does *not* predict that duration as a seventh head.
Therefore the ledger does **not** claim whole seven-field correctness. It
records the gold duration and a null predicted duration. The existing
independently adjudicated Policy-v1 offline evaluator handles full seven-field
comparisons separately.

### Private storage is mandatory

- **NEVER put real chat, private serialized model input, user identifiers,
  tokens, HMAC keys, raw private events, or ledgers in this public GitHub repo.**
- Each captured ledger uses an output directory that must already exist and
  resolve **outside the Git worktree**. Create it on an authorized private
  workstation with user-specific permissions and encrypted volume/storage.
- The per-project `ENTHUSIA_ANALYTICS_HMAC_KEY` needs at least 32 characters,
  must be supplied as a secret in the local process environment, and must
  not be logged or committed. The same key is needed to join the *same* case
  across model runs; rotating it requires a controlled migration plan or
  produces intentionally unlinkable cohorts. HMAC is **pseudonymization, not
  anonymization**.
- New files use exclusive-create semantics and mode `0600` on POSIX; on
  Windows also enforce restrictive ACLs on the containing directory.
- Case names / raw texts do not appear in the ledger. A staff-approved,
  access-controlled private evidence store may separately retain authorized
  original text for a limited operational window, linked with a purpose-bound
  reference; do not copy raw chat to W25 ledgers by default.
- Suggested default: raw diagnostic text **30 days**, curated review labels and
  pseudonymous development ledgers **90 days**, aggregate statistics longer
  with an owner-approved retention schedule. These are **proposals**, not an
  automatic deletion process; privacy and legal requirements may differ.
- Keep private message/reviewer access restricted, audit reading, and support
  deletion/retention reviews. Do not log staff/tickets/exempt scopes. Ordinary
  classifier predictions are **not training gold**.

## Capture without retraining or re-evaluating

When W25 has already generated a prediction bundle and the candidate's model
artifact and config checksums are known, run on the authorized computer:

```bash
python -m workers.w25.decision_analytics capture \
  --suite balanced_policy \
  --bundle /private/w25/w25-modelA-bundle.json \
  --candidate deberta-v3-xsmall --seed 42 \
  --run-id modelA-seed42-balanced-v1 \
  --model-sha256 <64-lowercase-hex> \
  --config-sha256 <64-lowercase-hex> \
  --policy v1 \
  --private-dir /private/enthusia-analytics \
  --secret-env ENTHUSIA_ANALYTICS_HMAC_KEY
```

Set `ENTHUSIA_ANALYTICS_HMAC_KEY` privately in the environment first.
The CLI does not print original text, IDs, the key or model probabilities; it
prints only the new private filename and capture status. It loads one **W25
registry-approved ready suite**; direct W20/W27/owner acceptance access is
intentionally rejected. Case count must match bundle cardinality exactly, no
duplicate IDs allowed. Reusing the run ID does not overwrite a previous ledger.

For comparisons of already saved PRIVATE ledgers:

```bash
python -m workers.w25.decision_analytics compare \
  /private/enthusia-analytics/modelA-seed42-balanced-v1.jsonl \
  /private/enthusia-analytics/modelB-seed42-balanced-v1.jsonl
```

Run completeness check after each batch:

```bash
python -m workers.w25.decision_analytics audit \
  --private-dir /private/enthusia-analytics \
  --expected-run modelA-seed42-balanced-v1 \
  --expected-run modelB-seed42-balanced-v1
```

Comparison **rejects** different suite fingerprints, different case pseudonyms
(e.g., HMAC rotation), changes to gold decisions, duplicate runs, and
incomplete/corrupt files. Reported numbers mean **corpus agreement and
disagreement**, not proven correctness when source labels are unverified.

## Next instrumentation phases

1. **W25 inference adapters**: capture pre-calibration and post-calibration
   distributions, raw logits where actually returned, candidate artifact/config
   hashes, model loads, inference wall-time per target, timeouts, exceptions,
   CPU/RSS and policy resolver rule hits. Version the wire contract and never
   synthesize absent fields. Add a run registry proving each candidate,
   architecture, seed, suite and threshold was captured before any model
   comparison. No model execution or expensive compute without explicit
   authorization.
2. **Central moderation API**: one canonical event ID across retry/mirror
   attempts; capture request context **references**, model/policy versions,
   per-stage times, individual model votes and reason-code evidence, final
   action, fail-open/error code, and staff correction outcome into access-
   controlled durable storage. Delivery-failure local buffering needs
   bounded capacity and an honest loss counter, not an impossible guarantee
   that every attempted message will always be saved.
3. **Analytics dashboard**: prevalence-aware action confusion, per-label and
   per-channel false BLOCKs, threat recall, review volume, model disagreement,
   calibration/drift, high/low confidence mistakes, security/error/latency
   percentiles, false strikes, false mute suggestions, and correction-rate
   over time. Compare the SAME frozen suite and source fingerprint across
   candidates; show sample counts and 95% intervals.
4. **Human-reviewed learning loop**: staff corrections recorded separately,
   independent adjudication, explicit train/dev/eval permissions, immutable
   versions and leakage detection. Do not auto-train on an AI's own outputs
   or quietly consume frozen W20/W27/owner evaluation records.

## Hard limits

This PR does **not** claim real-world +99% accuracy or authorize use of
private sealed suites. Ledger capture is an **explicit offline command**
performed after existing W25 saved runs: it is not yet an automatic hook on
every runtime invocation. The audit can prove completeness only against a
declared expected-run list; a future independent experiment manifest should
define required candidates/suites automatically. Successful CI validates
code behavior on invented data, not training quality, actual production chat
or complete observability.
