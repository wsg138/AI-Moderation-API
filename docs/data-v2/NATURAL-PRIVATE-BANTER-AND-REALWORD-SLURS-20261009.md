# DATA-V2-21 — Natural PM banter and real-word slur coverage

**2026-10-09 — developer candidates only, no model-training admission.**

## Owner feedback from 12 blinded fictional chats

All 12 owner's actions were privately reconciled to the original private
crosswalk and pinned candidate JSONL digest. **9/12 matched**. All 3
disagreements: the dataset expected REVIEW on the first continued insult
following a stop request, but the owner chose **ALLOW** and specified to start
BLOCKing and potentially flag staff **if the unwanted insults continue**.

The original 96-example corpus in PR #84 is kept unchanged for historical
comparison. This new batch does not claim that its candidate actions are
owner adjudications; specific thresholds remain subject to review.

## 52 additional, more natural fictional Minecraft PM examples

- 8 independent families × 5 temporal phases = 40 contrasts, including
  reciprocal joking, short stop requests, a first continued quip, repeated
  targeting after an additional stop request, and an apology.
- 12 further varied cases: `stop`, `stop lol`, `STOPP 💀`,
  `stop messaging me`, explicit no-contact requests, ignored no-contact,
  restorative willingness to joke again, and plain criticism.
- Proposed actions are **40 ALLOW / 11 BLOCK / 1 REVIEW**.
- **Every row** is synthetic and unverified, with
  `training_eligible=false`, `owner_reviewed=false` and
  `semantic_label_verified=false`.
- The `family_id` keeps related conversation contrasts in the **same**
  future train/dev/test split to prevent minimal-pair leakage.
- Only preceding messages and the target are available to the model,
  generated through `serialize_as_of_target`. We never include post-target
  replies, owner labels, candidate flags or family IDs as model features.

## Why real slur spellings belong in testing

**Real lexical forms are necessary** to evaluate detection of actual slurs,
variants, quotes/reports, friendly usage, and false positives such as
references to slurs without actual offensive words. The original PR #84
placeholder cases test a logical policy exception only and are insufficient
for training real slur recognition.

A separate **private, synthetic, real-word** development set has been built
on the owner's workstation outside the Git repository: 18 invented cases
across three lexical categories. It includes explicit words, obfuscations,
quoted reports, ordinary references, and slurs visible only in preceding
context (not in the message being judged). There is **no real player
transcript**, player identifier or claim of true population frequency. The
raw slur-containing content is **not committed to public GitHub, CI, or
issue comments**. Its private manifest pins a file digest and confirms
`training_eligible=false`, with independently verified labels still
pending. The intended policy is to BLOCK actual slur content even among
friends or in a quoted report, without automatically attributing a quote to
the reporting player.

This private fixture is not a validated model benchmark or complete
coverage of slur categories; slur detection needs careful context and
false-positive evaluation before any rollout.

## Candidate tests and promotion gates

```sh
python -m tools.data_v2.private_banter_natural_candidates
python -m unittest discover -s tests -p test_private_banter_natural_candidates.py
```

Prior development cases remain untouched. All new candidate text is fictional
and is **not** actual player moderation data. Before training, obtain
independent human-reviewed action and semantic labels, decide uncertain stop
and no-contact thresholds, construct family-grouped splits, and freeze a
separate truly unfamiliar blinded test set. No new training run, remote data
upload, moderation deployment, strike/mute, 9,000-example sweep or Policy v2
activation is authorized.
