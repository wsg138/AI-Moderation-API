# DATA-V2-02 — blinded synthetic review packet boundary (draft)

Tracking: [#57](https://github.com/wsg138/AI-Moderation-API/issues/57).
Source: synthetic-only candidate repair [PR #56](https://github.com/wsg138/AI-Moderation-API/pull/56), originally pinned to `cec977a69de0c891a1041d7af529cb0721eeb5bd`.
This preparatory tool is **not** a label review, a human adjudication, training permission, or deployment approval.

## What the packet contains

`tools/dataset_qa/blind_review.py` prepares review packets using the existing
`serialize_as_of_target` boundary. Each packet carries only an opaque `R-...`
ID, trusted `platform_hint`, `channel_profile`, chronological messages **up
to and including** the target (with speaker alias, offset and text), and
`target_index`. The target is the last message visible inside the packet.

**Deliberately excluded:** original `Gxx` ID/batch identity, semantic label,
action, review priority, strike, containment, support flow, reason codes,
notes, difficulty, domain, family identifiers, model predictions, and all
post-target messages or post-target message metadata. Source authorization
is constrained to the 18 public G10–G27 synthetic candidate batches.
The tool refuses missing/duplicate batches or anything other than exactly
9,000 distinct candidate IDs, and will fail closed on invalid earlier-time
context.

It writes **two separate outputs**: blinded packets for independent reviewers,
and a *private coordinator-only crosswalk* listing opaque ID to synthetic ID,
source filename, source file SHA-256, and original line number. Neither output
may be written inside the Git checkout; do **not** commit review answers or
the mapping before adjudication. The HMAC key must remain coordinator-only.

## Controlled run, outside Git checkout only

Run only against this branch's public synthetic candidate files, not private
player messages, W20/W27, sealed holdouts, or any previously model-mined
holdout. Example in a disposable, permission-restricted environment:

```bash
export ENTHUSIA_REVIEW_PACKET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m tools.dataset_qa.blind_review \
  --packet-out /tmp/enthusia-reviewer/packets.jsonl \
  --crosswalk-out /tmp/enthusia-coordinator/private-crosswalk.jsonl
```

**The sample paths above are illustrative.** The crosswalk should be stored
with stricter access than the review packets, not merely in a second visible
folder. Keep the key away from reviewers; reuse the same secret only if
reproducing exactly the same packet-ID mapping is necessary. The console
prints only the number of packets produced, not hidden labels or secret.

## Independent review sequence

1. Freeze exact source commit and file hashes (crosswalk). Before distribution,
   spot-check packet content against the target-time projection, especially
   cases where the source includes follow-up messages.
2. Randomize reviewer order. Do not disclose underlying G10–G27 batch focus,
   gold source fields, prior model labels, heuristic alert category or a
   second reviewer's response. A blind reviewer should record semantic facts
   first and only then apply Policy v1. Do not assume quoted actual slurs are
   safe: check Policy v1 §10. Do not infer verified age from a player's claim.
3. Each reviewer submits a **separate immutable decision record** keyed only
   by opaque packet ID: proposed semantic facts, narrow semantic label,
   outcome dimensions, evidence references, confidence/ambiguity, accepted
   Policy-v1 rule or unresolved owner-policy question. There is no training
   admission field that a reviewer can unilaterally set.
4. Blindly collect **two independent decisions** for severe/safety categories,
   suspected false punishments, and disputed/ambiguous cases. Preserve both
   original submissions. After review answers are locked, a coordinator
   reveals source labels and the crosswalk. Record disagreement, any
   adjudicator's ruling, exact policy version, and proposed source change.
5. Put unresolved policy edges in an owner decision queue, *not* an automatic
   plurality vote. Retain questionable cases as candidate-only. Group exact
   and near family matches before assigning train/development/evaluation
   partitions. Never tune against W20/W27 or protected real holdout.
6. Publish only sanitized aggregate counts and methodology until each
   approved label is attributable to independently reviewed evidence.
   Production-derived examples require separate consent, privacy and source
   eligibility review.

## Known next review priorities

At the pinned source: 2 SAFE/self-harm-directive flags, 26 SAFE/severe-reason
flags, 10 staff/SAFE disagreement flags, 354 grooming/minor-cue flags,
one cross-batch duplicate context, five shared-target groups, 109
single-speaker realism candidates, and 1,584 nonterminal target cases.
These are **heuristic review queues, not proof of wrong labels**. Start with
the safety/false-punishment flags, then stratify randomly across all source
categories and ordinary SAFE examples. Document sample denominators and do
not use enriched candidate samples to estimate live false-BLOCK rates.

## Limitations and controls

- **Procedural blindness, not cryptographic secrecy of the text**: reviewers
  with GitHub access could search for text in the public synthetic corpus.
  Reviewer instructions must prohibit consulting the gold files. HMAC IDs
  conceal the revealing batch prefix only when the secret/crosswalk is kept
  private.
- The current `policy/POLICY-v1.md` still includes unresolved edge decisions.
  This tool does **not** settle them or substitute for human policy adjudication.
- This is an *offline packet preparer*. It does not implement or test model
  training, runtime classification, predictions, or the deterministic policy
  resolver.
- Do not treat these packets or any single AI model's responses as verified
  truth. Codacy findings on #52/#56 are separately blocking acceptance.

## Deterministic priority + stratified audit cohort

`tools/dataset_qa/review_sampling.py` builds a **review subset** from the full
candidate-only corpus; it does not assign or correct labels. The cohort draws:

- all SAFE/self-harm-directive, SAFE/severe-reason-code, and staff-reason
  disagreement flags detected by deterministic heuristics;
- up to 32 grooming/minor-cue candidates (the others remain pending review);
- up to 12 keyed-random examples **per source semantic label**, and up to 8
  keyed-random examples per channel profile;
- all exact cross-batch context duplicates and cross-batch target/family
  overlaps detected by the current candidate auditor.

Selection is deterministic for the same source files and HMAC key. Changing
the source or key changes the cohort; store and lock the coordinator-only
crosswalk. This is **stratified and priority-enriched**, not random live-server
traffic. It must NEVER be used to estimate real-world production accuracy
or false-BLOCK incidence. The complete 9,000-record review backlog and
the excluded remainder must stay open.

Run against public synthetic data only. All output files must be outside the
Git repository and **must not already exist**:

```bash
export ENTHUSIA_REVIEW_PACKET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m tools.dataset_qa.review_sampling \
  --packet-out /tmp/enthusia-reviewer/sample-packets.jsonl \
  --coordinator-map-out /tmp/enthusia-coordinator/private-selection-map.jsonl
```

The reviewer packet output contains **no selection reason, existing source
label, original Gxx ID, review priority, later chat context or retrospective
outcomes**. A keyed-random order interleaves the categories. The protected
selection map (never shared with reviewers) records original source IDs,
file hashes, line numbers and selection reasons. The high-risk source
categories are used **only to sample**, never as revealed answers.

## Decision intake safety

`tools/dataset_qa/review_decisions.py` exposes
`validate_decision(decision, packet)` and
`review_summary(packets, decisions)`. These are offline validation helpers,
not a reviewer-authentication service or an adjudicator. A valid reviewer
record must contain exactly:

- `packet_id`, `reviewer_id`, `policy_version="v1"`,
  `semantic_facts` (1–32 nonblank observed facts, each ≤200 characters),
  `evidence_message_indices` limited to the visible earlier/target context;
- `semantic_label`, `action`, `review_priority`, `strike`,
  `containment`, `containment_duration_seconds`, `support_flow`;
- `uncertainty`: `CLEAR`, `EVIDENCE_INSUFFICIENT`, or
  `POLICY_UNRESOLVED`.

Missing fields and **any extra field** (including gold labels and
`training_eligible`) are rejected. A duplicate decision under the same
reviewer ID is rejected. Distinct reviewer IDs are a necessary but
**not sufficient** independence check; the coordinator must separately
verify actual reviewer identity, isolation, and that no answer copying took
place. The status view can distinguish `awaiting_first_review`,
`awaiting_second_review`, `independent_agreement`,
`evidence_insufficient`, `adjudication`, and `owner_policy_question`.
Any of two decisions marked `EVIDENCE_INSUFFICIENT` prevents
`independent_agreement` and instead requires more evidence, even when the
two outcome tuples are otherwise identical. `POLICY_UNRESOLVED` takes
precedence and routes to `owner_policy_question`; before a second review,
the item still waits for that submission unless policy is already unresolved.
**Every status keeps `training_eligible: false`**. Even exact agreement
never promotes examples to supervised training, and an unresolved Policy-v1
question needs the owner's ruling.

Do not reveal the source gold labels, cohort selection reasons or either
reviewer's answer before both independent decisions have been irreversibly
recorded. Reviewers should not share accounts or use the coordinator's
private crosswalk. Any later promotion requires a *separate* gated
adjudication/admission implementation and explicit source/split authorization.

## Operational two-reviewer assignment and intake

After the synthetic-only `review_sampling` command has prepared a
candidate subset, run the offline assignment tool with **two or more
genuinely independent reviewers**. These IDs should be pseudonymous aliases
with identity, role, and conflict-of-interest checks kept securely by the
coordinator, not posted to GitHub. Example (illustrative files, **no commands
have been executed on owner hardware**):

```bash
python -m tools.dataset_qa.review_assignments \
  --packet-input /tmp/enthusia-reviewer/sample-packets.jsonl \
  --reviewers reviewer01,reviewer02,reviewer03 \
  --reviewer-out-dir /tmp/enthusia-reviewer-assigned \
  --coordinator-manifest-out /tmp/enthusia-coordinator/assignment-manifest.jsonl
```

Use the **same coordinator-only HMAC key** for sample creation and
assignment. Each packet goes to two distinct aliases, balanced across the
roster. The packet-assignment and coordinator-intake boundaries also reject
malformed scope, nonstring speaker/text values, boolean/fractional timestamp
or target-index values, nested source-label objects, and earlier messages
whose offset occurs after the target's timestamp (even if the target index
is the final array element). This is defense in depth beyond the original
as-of-target serializer; the packet manifest hash is not itself proof that
input content was eligible. Every reviewer gets a separate file containing only their blinded
packets; the coordinator manifest (never distributed) records packet ID,
SHA-256 of the canonical packet, and two assigned reviewer aliases. The
assignment manifest is not the source-ID crosswalk; keep both separated
from reviewers and gold/source labels.

Each reviewer independently completes records with the exact
`review_decisions.py` schema described above. Collect those files only
after decisions are complete; do not give reviewers access to another
reviewer's submissions. On the coordinator side, run:

```bash
python -m tools.dataset_qa.review_intake \
  --packet-input /tmp/enthusia-reviewer/sample-packets.jsonl \
  --manifest-input /tmp/enthusia-coordinator/assignment-manifest.jsonl \
  --decision-input /tmp/reviews/reviewer01-decisions.jsonl \
  --decision-input /tmp/reviews/reviewer02-decisions.jsonl \
  --status-out /tmp/enthusia-coordinator/intake-status.jsonl
```

`review_intake` verifies that the packet bytes match their original
assignment digest, that submissions come from the assigned reviewer aliases,
and that there are no duplicates or out-of-range evidence indices. It
provides a status report of pending, agreement, disagreement or unresolved
policy questions. The status output **does not include source gold labels**
and every row remains `training_eligible: false`. Do not hand source/gold
labels to reviewers before their independent decisions have been locked.

**Security limitation:** the CLI does not authenticate a remote human.
Someone in possession of both reviewer files can impersonate both aliases.
The coordinator must confirm real, distinct reviewers and control storage,
permissions, and submission provenance outside this code. No live review
service or identity provider is implemented; do not claim an automated
two-human consensus from two aliases alone.

**Further acceptance blockers:** even two matching independent decisions do
not satisfy owner Policy-v1 adjudication for every safety/critical case,
Codacy issue-level triage, permission/source gates, cross-source duplicate
and family split isolation, or heldout evaluation independence. None of
these commands trigger training, merge, staff punishments or deployment.
