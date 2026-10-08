# G10 independent-review handoff — all 500 synthetic cases

**Status: preparation only; no independent decisions have been collected.**
Owner Policy-v1 decision (2026-10-08): blackmail *strictly inside Minecraft gameplay* is allowed, whereas real-world coercion/doxxing remains prohibited even on Minecraft or Discord. Unclear scope needs review. The policy clarification does not automatically correct any candidate labels.

## Why review all 500 rather than only 341?

G10 includes 500 public synthetic cases with existing candidate labels. The prior coordinator screens flagged **341** `BLACKMAIL/BLOCK` rows carrying `minecraft_gameplay_explicit` and no `explicit_real_world_cue` metadata, of which **216 have preliminary correction proposals** and **125 still require clarification**. These candidate labels and reason tags are *not* independently verified. Supplying only the 341 originally flagged cases to reviewers would advertise the selection and omit G10's SAFE/AMBIGUOUS and real-world blackmail comparisons. Instead, the full **500** are mixed and randomly ordered using a coordinator-only key, so the reviewers can encounter in-game allowances, actual IRL threats, and non-violating examples in one balanced *source-complete* set (not representative of production traffic).

Run only from this draft branch's **public synthetic data**; G10 is pinned to Git blob `3604b8e139892595fd280764869dc3ca1786044d`. Source byte drift fails closed.

## Make the offline handoff (no paid service or owner PC required here)

In a secure review environment with a Git checkout, set a **new randomly generated** HMAC key and create two distinct destinations *outside* the repository. Store the key and coordinator crosswalk out of reviewers' reach.

```bash
export ENTHUSIA_REVIEW_PACKET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

python -m tools.dataset_qa.g10_independent_cohort \
  --packet-out /tmp/g10-reviewer/g10-blind-packets.jsonl \
  --coordinator-map-out /tmp/g10-coordinator/private-crosswalk.jsonl

python -m tools.dataset_qa.review_assignments \
  --packet-input /tmp/g10-reviewer/g10-blind-packets.jsonl \
  --reviewers reviewer01,reviewer02 \
  --reviewer-out-dir /tmp/g10-reviewer-assigned \
  --coordinator-manifest-out /tmp/g10-coordinator/assignment-manifest.jsonl
```

Only the **blinded packets** go to assigned reviewers. Do **not** share the map, selection reason, GitHub candidate labels, original `G10-xxxx` IDs, draft proposals, or other reviewers' decisions. Reviewer aliases are not identity verification; the coordinator must separately confirm **two distinct independent people** and prevent shared answers or source peeking. The primary blind output can be passed to the existing `review_assignments.py` and `review_intake.py` scripts.

Packets expose `packet_id`, platform, channel profile, and target plus earlier messages only; no gold labels, policy outcomes, source identifiers, post-target messages, or prior proposed corrections. Crosswalk records the exact source file SHA-256, line, synthetic ID and opaque packet ID, but no gold labels. Every packet remains candidate-only.

## Independent review then adjudication

1. Two distinct reviewers read their own assigned packet file, independently record semantic facts, evidence indices, uncertainty, and their proposed Policy-v1 action. Use the strict schema documented in [blind review packet protocol](./BLIND-REVIEW-PACKET-PROTOCOL.md); do not publish personal reviewer identities, source crosswalks or decisions.
2. Collect submissions privately. Call `python -m tools.dataset_qa.review_intake` with the 500 packets, assignment manifest and decision JSONL files to reject out-of-scope submissions and calculate status. This **never marks training eligibility true**.
3. Only after both reviewers have submitted should the coordinator privately join the source mapping and compare with the 216 preliminary game-only proposals, 125 pending scope cases and all other original G10 labels. **Agreement does not itself certify training admission.** Disagreements and real-world harm require further adjudication and source/split checks.
4. Separately resolve identity/independence, privacy and rights, near-duplicate family splits, parent PR security triage and owner release approval before considering training.

## Outstanding authorization

Owner feedback from the prior **16-case solo pilot** is useful Policy-v1 input but is not two independent submissions. **No owner action is required to run QA or prepare reviewer materials.** Before independent adjudication can be completed, the owner/coordinator must arrange real independent human reviewers or explicitly revise the review requirement through a documented, scoped risk decision; neither alias generation nor AI decisions may be misrepresented as independent people.

**Boundaries:** no G10 edits, no training, no merging PR #58, no private Minecraft/Discord logs or player IDs, no W20/W27 heldouts, no production changes, no payment or automatic punishment.
