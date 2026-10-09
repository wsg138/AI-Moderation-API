# DATA-V2-20 — Friendship banter, stop boundaries and slur invariants

**Status: 96 unverified developer-authored synthetic candidates, not training gold.**
Created 2026-10-09 following the owner's explicit moderation-rule update.
Stacked on owner-policy clarification draft PR #83.

## Owner intent

Minecraft private messages between friends can be rude, profane or teasing
without being harassment. The AI should use *actual mutual context*, not
infer friendship simply from two usernames having chatted previously. A
genuine request to stop changes how following insults should be interpreted:

- Mutual joking with clear willing replies: **ALLOW** normal rude banter.
- Recipient clearly asks for the joking/targeting to stop: **ALLOW** the
  boundary request itself; track relevant boundary state without punishment.
- First targeted repetition after that clear request: **REVIEW**, rather than
  automatically block or strike on one uncertain continuation.
- Another unmistakable stop request followed by further unwanted insults:
  **BLOCK** the continuing message; no new automatic strike or mute is
  authorized by these candidate action labels.
- The first speaker apologizes and stops: **ALLOW**.
- A genuinely present protected slur: **BLOCK** regardless of friendship,
  consent, apology, quotation, or whether someone asked for it to stop.
  Message visibility and responsibility for a quoted report are distinct.

A prior friendship does not permanently exempt a sender from harassment
moderation. Also do not label every insult or every playful "stop haha" as
a credible boundary violation. Look for earnest language, acknowledgment,
subsequent conduct, repeated explicit stop requests and relevant context.

## Included dataset

`data/development/private_banter_candidate_v1.jsonl`: 96 fictional records,
20 distinct `family_id` groups:

- 16 banter topic families x five deliberate contrast phases = **80 rows**.
- 4 explicit-slur-placeholder families x four contrast phases = **16 rows**.

Candidate action counts: **52 ALLOW, 16 REVIEW, 28 BLOCK**. Every record has
`training_eligible=false`, `owner_reviewed=false`,
`semantic_label_verified=false`, and the explicit
`annotation_status=unverified_policy_candidate`.

Contexts contain only invented Friend_A and Friend_B messages in the
existing `minecraft_private` channel profile. `discord_bot_dms` and
arbitrary Discord private-message profiles remain undefined and have not
been silently introduced. Each case's target is its last message, so no
post-target information can be accidentally read; model inputs should be
serialized via `serialize_as_of_target`, which removes candidate action,
reason, family identifiers and synthetic answer flags.

No actual slur text appears in the example dataset. The exact marker
`[EXPLICIT_SLUR_PLACEHOLDER]` is *not* a real-world language/safety detector
test and would be inappropriate as positive lexical training data. Those
examples teach the **logical policy invariant only**. Replace these with
source-rights-cleared and independently reviewed explicit-content examples
before considering lexical classifier training. Never generate actual slurs
from placeholders automatically or misrepresent marker recognition as real
slur recall.

## Intended usage and quality checks

Inspect the committed candidates and verify their generated contents
without overwriting the checked-in dataset, with:

```sh
python -m tools.data_v2.private_banter_candidates
python -m unittest discover -s tests -p test_private_banter_candidates.py
```

The committed fixture is required to be **byte-identical** to generator
output and includes ten invariant tests: all family contrasts, immutable
source projections, no accidental punishment fields, strict placeholder
BLOCK/word-reference ALLOW, explicit boundary context, chronological messages,
family grouping and no training admission.

**Do not randomly split the 96 rows into training and heldout individually.**
All phases, paraphrases, later conversation continuations and related near
duplicates must remain in the **same family/session split**. This corpus is
intentionally highly patterned and cannot establish prevalence or generalize
to real player friendships, slur incidence, or abuse. Contrast balances are
artificial. No generator record is automatically accepted as owner gold.

Before any model training: independently confirm actions and all semantic
dimensions, enrich naturally varied conversations including uncertain/friendly
"stop" and one-sided harassment, test privacy/rights, freeze a different
never-exposed blind holdout, and acquire bounded job approval. No real user
messages, model guesses or original 9,000 candidate labels were imported.

## Decision thresholds to calibrate later

- Prefer **minimal false BLOCK and staff-flag rates** for clearly consensual
  private jokes; ordinary friendship should not cause repeated false alarms.
- For credible boundaries, measure separate REVIEW precision and harassment
  detection after repeat/ignored stop requests. Distinguish the person's
  "stop" message itself from the following offender response.
- Maintain high slur BLOCK recall even when banter is reciprocal.
- Store consent/boundary memory as limited, incident-linked facts with decay,
  with no hidden presumption from age/friendship history.
- No bulk 9,000-case model inference, training, merge, deployment or live
  policy activation is authorized by these developer examples.
