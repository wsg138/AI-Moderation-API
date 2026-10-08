# Enthusia AI Moderation — start the 16-case blind-review pilot

**Status:** reviewer-ready **pilot only**. This is not model training, approved annotation, or a production deployment.

This pilot uses **16 public synthetic candidate records** from G10, G12, G13, G17, G18, G20, G24 and G26 (two source examples from each). The case order is mixed and original labels, source IDs, source categories, future messages and notes are removed. It is **deliberately category-enriched** and not representative of ordinary server chat. **No real player messages are included.**

## For each reviewer

1. Download [BLIND-REVIEW-OFFLINE.html](./BLIND-REVIEW-OFFLINE.html) using the GitHub **Download raw file** control, then open the saved `.html` file locally in Chrome or Edge. No app install or account is required for the local review.
2. Get the **Enthusia-reviewer-pilot16-KIT.zip** from the owner/coordinator privately. Unzip it, and use the form's **Assigned packet file** picker to open `Enthusia-blind-pilot16.jsonl`.
3. The coordinator will give two *different people* separate reviewer aliases: `reviewer01` and `reviewer02`. Use exactly your assigned alias. Two aliases alone do not establish two humans or independent review.
4. Read [Policy v1](../../policy/POLICY-v1.md) and review **only the chat messages that are visible up to and including the highlighted target**. Decide what the **target** means with the provided context, not what a later message might reveal.
5. For **each case**, enter short factual observations (not invented history or verified age), choose supporting message indices, and decide the semantic label, allow/block/review action, staff priority, strike recommendation, containment and possible duration, support flow, and uncertainty. Click **Save this decision**. Move through all 16 cases.
6. Click **Export completed decisions** *before closing or reloading the browser tab*. The local form does not upload, transmit, or persist answers. Send the exported `enthusia-review-reviewerXX.jsonl` **privately** to the owner/coordinator. Do **not** attach it to a public PR/issue or show it to the other reviewer until both review submissions are locked.

## What to look for

The goal is not "block anything bad-sounding." Use Policy v1 when distinguishing Minecraft gameplay from credible real-world threats, factual age *claims* from reliable evidence, private versus public harassment, concerning self-harm disclosure from abuse directed at others, quoted actual slurs under §10, and uncertainty requiring review instead of punishment.

A case can legitimately be ambiguous. Mark `EVIDENCE_INSUFFICIENT` or `POLICY_UNRESOLVED` when appropriate. If you are unsure how to interpret a rule, write that uncertainty among the observable facts, rather than inventing a more specific policy rule.

The examples contain synthetic demonstrations of threats, self-harm language and harassment; participants can opt out of reviewing categories that they are uncomfortable reading.

## For the coordinator (keep separate from reviewers)

The owner received the reviewer kit and an **entirely separate coordinator-only** mapping/assignment archive in ChatGPT. The coordinator archive includes opaque ID → source identity and the frozen assignment manifest; it must **never** be given to either reviewer. A duplicate of the private archive is stored in the owner's private ChatGPT Library under:

`/Enthusia AI Moderation/Coordinator review artifacts/Enthusia-coordinator-pilot16-PRIVATE.zip`

The source commit is `cc5d928707f20cf24bb7fd561c690ce9fecb572d`. The hand-picked pilot is a **UI/semantic-review rehearsal**, *not* the deterministic 9k-cohort sampler described in [BLIND-REVIEW-PACKET-PROTOCOL.md](./BLIND-REVIEW-PACKET-PROTOCOL.md).

When both independent decisions are received:

1. Verify their separate human identity and that they independently completed the task.
2. Validate packet IDs, packet SHA-256, and assigned aliases against the **private assignment manifest**. The `review_intake.py` helper can validate the decisions and produce agreement, disagreement, missing-review, or owner-policy-question statuses. Note that source/pilot crosswalk and assignment manifest may be repackaged as JSONL files for the offline helper.
3. **Only after both are locked**, unblind the original source ID/labels in the private mapping, compare with Policy v1, and prepare *proposals*, not automatic source edits. Queue severe/contested cases for adjudication and owner decisions.
4. Preserve the original independent decisions; require another explicit training-admission gate with Codacy triage, source lineage, split isolation, and policy adjudication. No pilot case becomes training-eligible from two reviewers alone.

### Boundaries

- Public synthetic only. No private Minecraft/Discord logs or W20/W27/protected real holdouts.
- The offline form does **not** authenticate the reviewer. The owner must independently confirm two people, isolate submissions, and protect the coordinator files.
- No model training, merge, deployment, punishment automation, owner-PC heavy workload or paid service is authorized.
- PR #58 remains a draft stacked on #56's branch; the production system is unchanged.
