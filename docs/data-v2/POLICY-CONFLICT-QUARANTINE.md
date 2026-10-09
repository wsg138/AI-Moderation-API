# DATA-V2-07 — Policy conflict reconciliation and training quarantine

**State: read-only candidate audit, not new moderation policy.**
Tracking issue #53 and owner quick-review issues #57. Stacked on draft PR #70.
No merges to production, no automatic label revisions, no training admission.

## Purpose

The owner has now reviewed 50 + 36 distinct, deliberately enriched synthetic
examples, **action-only**. Review agreement is not model accuracy or a
population-level error estimate. All 9,000 original synthetic cases still
lack complete independently verified semantic/strike/mute/support outcomes.

`tools/data_v2/policy_conflict_quarantine.py` generates a deterministic,
source-anchored **private quarantine queue** and prints **aggregate counts
only**. It consumes exactly the existing 18 SHA-256-pinned synthetic G10–G27
batches; optionally imports BOTH earlier private owner ledgers through the
validated action-only intake from PR #70. There is no public case-by-case
answer data, review note, packet ID, or private source mapping in this PR.

Every resulting row explicitly says `quarantined_unverified` and
`training_eligible=false`, even where the source label and owner action
agree. The original source action/semantic fields are tagged for comparison
and routing only. No rule here decides final enforcement outcomes.

## Separate policy issues from case interpretation

| Review track | Status | Meaning |
|---|---|---|
| language_enforcement | **Owner action, scope and block-only consequence confirmed; detector still unvalidated** | BLOCK primarily non-English chat on all currently moderated Minecraft public/private and Discord public/gaming surfaces; ALLOW occasional foreign words/greetings, names, and game terms. Existing ticket/staff exemptions remain. **No strike, mute, punishment, staff alert, or repeat escalation for language-only violations.** Independently harmful content follows its own rules. G21 is a **source-batch proxy**, not a language detector. |
| self_published_contact | **New scope decision needed** | First-person contact disclosure must not silently inherit third-party doxxing strike/mute rules. Lexical hints are not verification. |
| uncertain_minor_context | **Existing policy gap** | Policy v1 protects reliably known minors; uncertain minor age and secrecy/contact patterns need distinct policy adjudication. |
| dangerous_domain_scope | **Existing policy gap** | Actionable real-world explosives are covered; domains beyond explosives require explicit handling. |
| private_sexual_boundary | **Existing policy gap** | Consensual adult explicit PM boundary remains unresolved; nude solicitation remains prohibited. |
| real_world_threat_evidence | **Settled core policy, apply with context** | Review threat evidence, including school, location and reliable time cues; do not classify obvious gameplay as IRL threats. |
| third_party_private_information | **Settled core policy, apply with context** | Apparent third-party doxxing/solicitation requires careful source evidence and staff response; review false alarms separately. |
| gameplay_blackmail_scope | **Settled owner clarification** | Clearly game-only Minecraft asset leverage allowed; real-world extortion prohibited; mixed/unknown stakes require review. |
| self_harm_safety_flow | **Settled support vs punishment distinction** | ALLOW can still require a separate supportive safety response; NEVER infer lack of concern from message visibility. |
| harassment_incident_context | **Settled core policy, case-level evidence** | Repeated unwanted contact, stop requests, mutual banter and specific targeting are context-dependent. |

The *category routing* relies in part on **unverified source candidate labels**.
It is a search hint, not a finding of misconduct. The G21 language bucket uses
a known batch prefix, not language inference. The owner-approved language rule is
versioned in `policy/english-primary-message-action-v1.json` and is **not**
a source of new approved training labels, detection confidence, or automatic
strikes/mutes. Classification of predominantly non-English text has not been
validated. The rule's outcome is distinct from the underlying harmful-content
semantic classification. The first-person contact pattern
search is conservative and only inspects target-time-visible text.

## Prioritization

1. **01_safety_policy_conflict_review**: owner action ALLOW disagrees with a
   candidate BLOCK in a potentially severe policy category. This prompts a
   careful high-stakes review, never silent override of either the owner or
   the policy. No rule invents a strike or human reviewer.
2. **02_owner_vs_candidate_action_review**: another action disagreement.
3. **03_unresolved_policy_boundary**: source candidate touches a known open
   scope decision, regardless of label agreement. The already decided
   English-primary message-action rule is no longer treated as an undecided
   rule, though its technical detection and deployment remain blocked.
4. **04_contextual_policy_application_review**: settled policy still
   requires interpreting the specific situation.
5. **05_other_unverified_candidate**: everything else still unverified.

These are ordering buckets, not classifier confidence, risk probabilities
or punishments. All five tiers remain training-ineligible.

## Coordinator-only operation

Aggregate-only (no owner answers):

```sh
python -m tools.data_v2.policy_conflict_quarantine
```

Validated private Rounds 3+4 import with optional new coordinator manifest:

```sh
python -m tools.data_v2.policy_conflict_quarantine \
  --round3-ledger /private/Round3-Ledger.json \
  --round4-ledger /private/Round4-Ledger.json \
  --private-manifest-out /private/coordinator/policy-quarantine.jsonl
```

Always supply **both** private ledgers if accounting for reviewed decisions.
The destination must be a previously unused path outside Git checkout.
Private manifest includes source IDs, untrusted candidate classifications,
owner action-only decisions when available, source byte SHA/line and policy
routing hypotheses. It is **not** a blind reviewer packet. Keep it separate
from reviewer files and do not publish it to GitHub or Discord.

## Evidence and blocked transitions

- Source file SHA-256 and 9,000-case count checked by the already pinned loader.
  Every source ID position is verified to match its original JSONL line.
- Owner Round 3 and reconstructed Round 4 ledger schemas verified separately
  using their prior validators. Round 4 original HMAC/crosswalk limitation
  remains explicitly recorded and unchanged; no authenticity claim is added.
- The target text inspection uses the tested **as-of-target** feature
  projection. Later messages can never influence these candidate flags.
- Quarantined synthetic records cannot be admitted by this tool, even when an
  owner action matches an original candidate. No generalization across
  shared family IDs or nearly identical wording.
- Existing limits still apply: rights/privacy clearance, complete independent
  semantic/punishment annotations, policy version signoff, contextual
  equivalence evidence, group-safe train/dev partitioning, protected
  W20/W27 isolation and robust false-punishment evaluation.

**Next dependency:** Version the open rule boundaries with the owner before
adjudicating high-risk cases. Keep the response small and specific, e.g.,
which chat surfaces receive the English-only rule, whether language-only
violations trigger any additional sanctions, and how self-disclosed personal
contact details should be treated. Do not bury
these safety decisions inside a new round of random sample labeling.
