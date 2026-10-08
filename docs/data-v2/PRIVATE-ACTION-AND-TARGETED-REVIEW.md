# DATA-V2-04 — Private owner action intake + targeted blind selection (draft)

**Not a model evaluation, new training set, independent human semantic review,
or permission to change enforcement.** Tracks #53, #57. Stacked on draft #67.

The already collected owner Round 3 action-only ledger is a PRIVATE coordinator
artifact, not a JSONL training source. It was produced from 50 blinded public
synthetic cases. Its opaque packet IDs are **not independently HMAC-reproducible
without the original packet secret**; metadata checks cannot establish human
authentication or tamper-proof provenance alone. A separate owner action is
authoritative for that case's **ALLOW/BLOCK/REVIEW action only**; severity and
semantic fields remain unadjudicated. Do not commit the ledger, explanations,
per-case actions, or opaque-ID crosswalk to public GitHub.

## What was added

- `tools/data_v2/private_owner_actions.py` parses the known Round 3 private
  ledger schema, enforces 50 unique source IDs + opaque IDs, owner action-only
  scope, Policy v1, frozen original source commit `21cc2cfa`, source filename,
  JSONL line, Git blob hash derived from pinned public source bytes, and
  original candidate action/label comparison. Only **message actions** and
  optional owner explanations are written to a separate permission-restricted,
  coordinator-only output. Every row retains `training_eligible=false`.
  No trust is placed in candidate semantic labels; they are comparison-only.
- `tools/data_v2/targeted_blind_review.py` reuses the **source-pinned
  9,000-case** triage queue from #67. It takes a separate new secret, excludes
  the 50 already-reviewed owner case IDs when given the validated private ledger,
  and proposes up to **three policy-conflict candidates, two high-impact
  candidates, one lower-impact random-control candidate per G10–G27 batch**.
  This is a priority/stratified **selection** procedure, not representative
  production sampling or gold-data construction.
- Within each batch/priority stratum, the keyed ordering prefers distinct
  declared family IDs before filling the quota. Family IDs are unverified;
  neither the ranking nor a family group propagates any outcome.
- The reviewer-facing packet includes ONLY opaque packet ID, scope, and target
  plus earlier chronological messages. It is structurally validated by the
  existing review assignment packet checker. The **separate private coordinator
  crosswalk** holds synthetic source ID, source file/digest/line, and triage tier.
  No candidate/gold answers, selection tier, reviewer answers or later messages
  appear in reviewer packets.
- Existing two-human assignment tools can consume the blinded packets if
  full-schema independent reviews are later authorized. The owner quick-action
  form is a **separate** action-only process; never fabricate other required
  fields or independent reviewers.

## Example — offline, private coordinator environment only

The previous owner JSON file should be kept outside this repository, as should
all outputs. Paths below are illustrative (not owner hardware commands that
have been executed in this PR).

```sh
python -m tools.data_v2.private_owner_actions \
  --ledger-input /private/round3-owner-ledger.json \
  --private-corrections-out /private/owner-action-only.jsonl

export ENTHUSIA_REVIEW_PACKET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m tools.data_v2.targeted_blind_review \
  --private-owner-ledger /private/round3-owner-ledger.json \
  --packet-out /private/reviewer/new-priority-packets.jsonl \
  --coordinator-map-out /private/coordinator/new-selection-map.jsonl
```

Use a fresh, separate HMAC key for the next batch, and protect it. Output files
must not exist already and must be outside the source checkout. Keep coordinator
map outside the reviewer-packet directory; do not share it. There is no GPU,
model inference, network API, private Minecraft/Discord log access or payment
required by either offline command.

## Review safety and admission boundary

- All **9,000 synthetic cases remain candidate-only**; the 50 reviewed actions
  do not certify semantic labels, strike, mute, support flow or punishment.
- Sampling skips those 50 source records but may select other members of their
  broad family; their decisions are NOT auto-applied to those members.
- Review queues have **selection bias** and cannot estimate real-chat accuracy,
  false-block rates or the validity of the existing 9,000 labels.
- Self-disclosed personal information, unknown language scope, dangerous
  requests, threats, known-minor interactions and Minecraft-only stakes have
  policy edges requiring versioned reconciliation. Quarantine disputed safety
  annotations and never silently override an owner action or settled safety rule.
- Source privacy/rights, source-family split, protected W20/W27 and real heldout
  isolation, parent PR security/Codacy findings, owner acceptance, and explicit
  training/deployment authorization remain mandatory.

## Limitations / next steps

This PR implements **one** known owner-ledger schema (Round 3), not a general
ledger-merging framework for all past reviews. It does not contain or publish
Round 2's private owner text. The sampler still requires an authorized, private
coordinator run to produce actual review files and a separate reviewer UI/form
for convenient next owner decisions. Never tell the owner that the review is
ready to click simply because offline packet generation code passed CI.

The subsequent coordinator task is to run the tools on authorized local
synthetic/owner files, inspect and privately preserve aggregate diagnostics,
and prepare a self-contained blind quick-review page without exposing its
crosswalk or original labels. Do not require another round until that targeted
review has a clear reason and bounded workload.
