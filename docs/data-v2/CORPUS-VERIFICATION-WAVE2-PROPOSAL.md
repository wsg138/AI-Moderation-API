# DATA-V2-17 — experimental next-wave selection (not issued)

**Status:** candidate-only development. **No reviewer packet has been generated for
this wave**, no human review claimed, no training admission, no model training,
and no production moderation change.

## Do not rewrite the existing 180 reviews

The already-issued Stage-1 wave is frozen on public synthetic G10–G27 sources.
Ordered IDs, joined with commas, have SHA-256:

`bec3d820706c4b8e42c9e17ce1e8455bb38811d30c25d293c27e12a4f1350407`

The owner and local AI pilot reviewed subsets of this **first wave**. The new
selector must refuse any change to that digest. It does not replace, regenerate,
re-key, or amend first-wave packets/crosswalks/answers. Keep the first-wave
private records separate.

## Why a second selector exists

The Stage-1 sampler preferentially fills policy, high-impact, and routine tiers
with nominal per-batch quotas **4 / 3 / 3**; when a tier is absent it must use
other candidates. Some batches have repeated text or few families. Earlier
ordering can consume family/target diversity needed by later tiers. A category
that contains 20 rows does not necessarily contain 20 *different messages*.

This experimental implementation:

1. Loads existing SHA-256-pinned public synthetic sources and reuses Stage-1
   conflict triage.
2. Excludes **all** 180 frozen first-wave record IDs.
3. Prefers targets and declared families not previously selected (within or
   across waves), always prohibiting duplicate normalized target texts.
4. Computes feasible tier allocations using **distinct normalized targets**
   remaining at each batch, rather than raw row counts; redistributes missing
   quota slots proportionally to the other tiers.
5. First attempts the existing diversity-preferring greedy selection. When
   shared target messages make that selection miss a priority quota, a
   deterministic augmenting-path matching step can reassign shared targets
   to preserve a **feasible** tier balance. A focused regression reproduces
   the old 5/2/3 mistake and verifies the corrected 4/3/3 allocation.
   Repeated families are recorded, *not* magically treated as independent
   source scenarios. The pinned proposal's selected IDs are unchanged.
6. Outputs aggregate diagnostics and an ordered-selection checksum **only**.
   It creates no review packets, crosswalk, train/dev/test splits, or labels.

The seed and selection are deterministic; the script does not use any
private owner or reviewer answer to prioritize examples.

## Reproduced, experimental G10–G27 result

Command:

```sh
python -m tools.data_v2.corpus_verification_stage2
```

Result on the pinned 9,000 candidate inputs:

| Item | Proposed result |
| --- | ---: |
| Sources checked | 9,000 |
| Batches represented | 18 |
| New candidate cases | 180 (10 per batch) |
| ID overlap with first wave | 0 |
| Normalized target repetition across both waves | 0 |
| Policy-conflict priority | 32 |
| High-impact priority | 62 |
| Routine/stratified priority | 86 |
| Unmet feasible tier allocations | 0 |
| Repeated declared-family selections within proposed wave | 12 |
| Distinct families in new wave already seen in first wave | 23 |
| Independently verified semantic cases | 0 |
| Training admitted | 0 |

Proposed ordered ID digest:

`bdfcd6392a024db3a525b2abed224447936bd4c2fed6381d82e4fd3e3eacbeb1`

The initial G23 shortfall came from counting repeated candidate messages as
different choices. Using remaining **distinct** normalized target texts yields
no unmet *feasible* category allocations. Some tier types simply do not exist
in certain batches; the resulting 32/62/86 composition is not a random or
statistically representative sample of all server chat.

## Critical interpretation limits

- **Repeated declared families still exist.** The 12 within-wave repeats and
  23 families shared with the first wave are not independent examples for
  leakage-sensitive training/evaluation. Other unrecognized near-duplicates
  and semantically related scenarios may remain.
- The new wave should not automatically become a held-out evaluation sample.
  Risk-enriched, balanced-per-batch sampling is **not** an unbiased estimate
  of false BLOCK rate or general production reliability.
- Model-to-model agreement or agreement with owner *action-only* reviews does
  not validate semantic label, review urgency, strike, mute, support flow,
  or training eligibility.
- Prior owner decisions (2 ALLOW, 3 REVIEW from the recent five-case review)
  remain private and are **not** used to choose second-wave cases.
- No stage may use real chat logs, hidden source mappings, or review packets
  on a public CI runner. Actual future review assignment requires an approved
  private setup and an independent blinded judgment process.

## Before authorizing any second-wave review

Review the category distribution and repeated-family relationships. Establish
whether a narrower targeted review, independent human annotation, or an unbiased
representative held-out sample gives more useful evidence than issuing all
180 proposed new cases. If wave 2 is approved later, use a fresh, distinct,
secret-backed private packet/crosswalk and keep it out of Git.

This draft proposes sampling mechanics only; **do not merge or deploy it
without normal review and explicit owner authorization**.
