# G10 blackmail correction queue — owner game-vs-IRL ruling

**Review-only stage.** Source: `data/synthetic/G10-blackmail-extortion.jsonl` at source snapshot `cc5d928707f20cf24bb7fd561c690ce9fecb572d`. This document is about publicly generated synthetic samples, not private Minecraft player conversations.

## Why not simply change 341 labels?

The existing batch is 500 records, with 397 `BLACKMAIL/BLOCK` records. The earlier metadata-only filter found **341** records both labeled BLOCK and tagged `minecraft_gameplay_explicit`, without the `explicit_real_world_cue` tag. Those tags were authored along with the candidate labels, so they are **not independent proof** of game-only content.

Initial target-time-text audit of that 341-case queue using `tools/dataset_qa/gameplay_blackmail_triage.py` divides the records into *priority buckets*, not certified labels:

| Pending triage bucket | Cases | Next step |
|---|---:|---|
| `gameplay_scope_confirmation` | 107 | Explicit game-payment and game-asset terms, no defined mixed/real-world risk match; **verify both the demand and threat are exclusively gameplay** |
| `mixed_or_realworld_risk` | 35 | Possible purchase of server ranks for actual money, personal/voice-chat disclosure, or other real-world exposure; **do not assume game-only** |
| `insufficient_scope_evidence` | 199 | Not enough explicit game-economy *and* game-asset wording for the conservative screen; **inspect target and preceding messages** |
| **Total pending** | **341** | **0 reviewed/admitted by this script** |

These are rough lexical review-priority groups. In particular, a `minecraft_gameplay_explicit` source tag is not evidence that a requested **store purchase** is merely an in-game item. A video of Minecraft cheating may be purely game-related; a voice-chat embarrassment or private screenshot might involve real people. The script must not infer without additional context.

### Examples of what needs attention

- Demand for diamonds in exchange for withholding **Minecraft base coordinates**: strong game-only candidate, likely to be `SAFE/ALLOW` once reviewed and confirmed under the owner's 2026-10-08 rule.
- Demand to **buy VIP or MVP in a server store**: may require real money; preserve for scope review, regardless of game platform.
- Demand for items in exchange for not sharing **voice-chat disclosures or personal screenshots**: may be mixed-stakes. Need review, not an automatic game allowance.
- Demand for in-game items in exchange for not reporting **Minecraft cheating to server staff**: the conversation could be entirely in-game even without 'base' or 'coords'. It belongs in the remaining scope-review bucket rather than being preemptively marked real-world.
- Real-life home-address, photo exposure, or money demand: remains prohibited under the settled policy regardless of channel.

## Reproducible evidence and per-case queue

From a checkout of the stacked PR #58 branch:

```bash
python -m tools.dataset_qa.gameplay_blackmail_triage

# Optional: privately export all 341 source IDs/line numbers/buckets
python -m tools.dataset_qa.gameplay_blackmail_triage \
  --coordinator-manifest-out /tmp/enthusia-g10-scope-review.jsonl
```

The default prints only source SHA-256, counts and flags. The optional JSONL manifest is **coordinator-only** and cannot be written inside the Git checkout. It lists source byte SHA-256, source line, example ID, target index, review bucket, and **pending** status, **not** original chat text or authenticated reviewer judgments. It pins each case to the precise file bytes for invalidation on future source changes.

`suggested_action_if_confirmed_game_only: "SAFE/ALLOW"` is a **conditional correction proposal**, not an actual adjudication and not an automatic relabel of all rows.

## Accepting corrections safely

1. Prioritize reviewing the 107 stronger gameplay-cue candidates; independently confirm both threatened information and requested payment are strictly gameplay, and preserve a record of the evidence. Reclassify only those verified, not on keyword matches alone.
2. Independently inspect the 35 mixed-risk candidates and 199 underspecified cases. Some belong in game-only ALLOW, some in real-world BLOCK, and some need REVIEW.
3. For confirmed pure gameplay extortion, propose `semantic_label=SAFE`, `action=ALLOW`, `review_priority=NONE`, `strike=false`, `containment=NONE`, duration `null`, and `support_flow=NONE`. Keep real-world blackmail blocked, with appropriate urgent review and containment; preserve uncertainties as unresolved.
4. Do **not** edit G10 or any other dataset JSONL based on this preliminary screen, owner solo pilot, or AI-generated guesses. Obtain separate review/adjudication, source/split checks and release acceptance first.
5. The 9,000 synthetic records remain **candidate-only**. No model training, deployment, private player-data access, W20/W27 use, or automatic punishments are authorized.

Related: [owner rule](./GAMEPLAY-BLACKMAIL-OWNER-RULING.md); [DATA-V2-02 review protocol](./BLIND-REVIEW-PACKET-PROTOCOL.md); GitHub issue #59.

## Coordinator preliminary scope screen (86 proposals; not yet independently adjudicated)

A narrower manual/semantic **coordinator preliminary screen** of as-of-target
synthetic text selected **86 of the 107** stronger-gameplay-cue cases as
provisional correction requests. These cases depict explicit game-item payment
for leverage over Minecraft bases, guild vaults/coordinates, in-game griefing,
or in-game records. The selection excludes underspecified threats, cheating
report leverage, a personal voice-chat disclosure, real-money purchases of
server ranks and all cases containing identified real-world cues. Even though
these 86 were provisionally read in their context, this does **not** constitute
a second independent human review or certify their final labels.

The 341 flagged records are now tracked as:

| State | Count | Admission |
|---|---:|---|
| Provisional game-only corrections prepared | **86** | Zero approved; independent/adjudication gate remains |
| Other stronger-gameplay-cue cases, not yet provisionally proposed | **21** | Pending |
| Mixed/real-world-risk scope | **35** | Pending; no game-only allowance assumed |
| Insufficient game-only scope evidence | **199** | Pending |
| **Total originally flagged** | **341** | **0 admitted** |

Reproduce the proposal set, pinned to the exact original Git blob and target-time
context:

```bash
python -m tools.dataset_qa.gameplay_blackmail_proposals

# Optional coordinator-only output (not inside Git checkout):
python -m tools.dataset_qa.gameplay_blackmail_proposals \
  --coordinator-proposals-out /tmp/enthusia-g10-provisional-corrections.jsonl
```

Each optional proposal JSONL row has the original synthetic ID, precise source
line and source SHA-256, an as-of-target visible-context SHA-256, a short
gameplay scope basis, and a proposed new `SAFE / ALLOW / NONE / no strike / no
mute / support NONE` tuple. Crucially, it always has
`status=requires_independent_policy_adjudication`,
`review_origin=coordinator_provisional_screen_only`, and
`training_eligible=false`. Neither command rewrites the G10 dataset, creates
official review decisions, changes production, or removes the existing
source/split and security blockers.

Remaining per-record verification should inspect the **21** unproposed
strong-cue examples first and explicitly identify any overlooked mixed or
real-world stakes before extending the proposal set; also validate the current
86 proposed cases independently and resolve contradictions. Grouped phrases
or source-provided tags are not enough to certify semantic outcomes.

## Second-pass update (supersedes 86/255 totals above)

The [case-by-case second pass](./G10-SECOND-PASS-DISPOSITIONS.md) assessed all 21
previously unproposed stronger-gameplay-cue examples and all 35 mixed-risk
examples. **14 additional provisional game-only correction proposals** are now
prepared (including game-only cheating-report and account-rule leverage); **7**
stronger-gameplay cases remain unproposed due to missing scope evidence. All 35
mixed/real-world-risk examples remain pending; none are accepted as game-only.

**Current totals: 100 provisional SAFE/ALLOW proposals, 241 unresolved review
candidates, zero independent approvals, zero training admissions.** Of the 241,
7 have ambiguous strong game cues, 35 have possible mixed/IRL stakes, and 199
still have insufficient scope evidence. Prior queue tables with 86 proposals
remain a historical snapshot, not current queue totals.

The optional coordinator-only 56-case second-pass JSONL manifest is produced
by `python -m tools.dataset_qa.gameplay_blackmail_second_pass` and refuses
source byte drift. No source data, model weights or production settings change.
