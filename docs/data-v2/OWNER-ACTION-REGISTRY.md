# DATA-V2-06 — Owner action-only registry (Rounds 3 and 4)

**Draft status. No source relabeling, semantic-gold admission, training or deployment.**
This is a private coordinator protocol, stacked on draft PR #69.

The owner completed another targeted, blinded sample: 36 valid Round 4
action-only decisions. Original candidate-action agreement was **20/36**;
the owner selected 30 ALLOW, 1 REVIEW and 5 BLOCK. The cohort was enriched
and cannot estimate corpus-wide error, let alone a model's performance.
Aggregate public tracking only: issue #53. All per-case source mappings,
opaque IDs, actions, and notes stay off public GitHub.

## Implemented

- `tools/data_v2/owner_action_registry.py` validates a *private* Round 4
  ledger with a source-anchored reconstructed Q-to-source mapping. Requires 36
  ordered, unique, valid opaque IDs, source row IDs and original JSONL lines,
  pinned Git commit and source Git blob SHAs from the SHA-256-pinned public
  source loader, original candidate action/semantic label **for comparison**,
  target-time visible message count and target-text SHA-256.
- Maintains all seven semantic/punishment/support review fields at
  `unreviewed`; imported records are **owner message-action only** and
  `training_eligible=false`. It rejects claims of extra annotations,
  wrong source content, swapped cases, duplicate owner-reviewed source IDs,
  unsanctioned owner actions, invalid review rounds and source drift.
- Can privately merge the existing 50 Round 3 and 36 Round 4 action
  judgments into 86 distinct coordinator records, while rejecting overlap.
  Creates only a **new, private, coordinator-only registry** and prints
  aggregate validation counts.
- `tools/data_v2/targeted_blind_review.py` now supports optional
  `--private-round4-ledger` alongside the existing Round 3 owner ledger,
  excluding both cohorts when sampling new blinded public synthetic cases.
  This avoids a new questionnaire reusing already answered prompts. The
  reviewer-facing packet still cannot see action answers, original labels
  or source IDs.

## Private coordinator commands (no files on GitHub)

```sh
python -m tools.data_v2.owner_action_registry \
  --round3-ledger /private/Round3-Ledger.json \
  --round4-ledger /private/Round4-Ledger.json \
  --private-registry-out /private/owner-actions-3-and-4.jsonl
```

For subsequent blinded review selection, provide BOTH existing private
ledgers in addition to the previous packet/crosswalk destinations:

```sh
python -m tools.data_v2.targeted_blind_review \
  --private-owner-ledger /private/Round3-Ledger.json \
  --private-round4-ledger /private/Round4-Ledger.json \
  --packet-out /private/reviewer/new-packets.jsonl \
  --coordinator-map-out /private/coordinator/new-crosswalk.jsonl
```

Both commands require source files present, source digests matching the
pinned records, and exclusive outputs outside Git checkout. The sampler
requires a separately generated secret in the existing
`ENTHUSIA_REVIEW_PACKET_KEY` environment variable. These examples are not
a claim that the owner device is connected.

## Important provenance limitation

The original separate Round 4 coordinator crosswalk file was **not
accessible** in the reconciling environment. The private Round 4 ledger
therefore reconstructs source mapping from the previous Round 4 selection
trace, matches Q numbers to opaque packet IDs in the retained offline HTML,
and independently checks target text and public source IDs/blob hashes.
The original secret is unavailable: **opaque packet ID HMAC derivation is
not cryptographically verified**. This tool explicitly returns
`crosswalk_hmac_verified=false`. It validates consistency/provenance
of the reconstructed ledger, **not** ownership/authenticity beyond those
observations. Keep this caveat with all private output.

The independently verified earlier Round 3 owner action-ledger schema is
unchanged, and no Round 2 source mapping is invented here. Semantic labels,
strike/mute/support/containment, rights/privacy gates, dangerous-content and
known-minor rule reconciliation, independent full-schema review, and
leakage-safe evaluation remain incomplete. Do not train on these action-only
decisions as if they were complete labeled policy outcomes.
