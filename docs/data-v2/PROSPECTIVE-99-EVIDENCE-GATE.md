# DATA-V2: prospective 99% accuracy evidence gate (proposal, offline only)

**Status:** unapproved development/research gate. This does **not** authorize
training, spending, merging a model, live message blocking, strikes, mutes or bans.
Automatic punishments remain disabled. The numerical floors below are
**provisional engineering acceptance hypotheses** for owner review.

## Why substantially more data and testing are necessary

A 99% accuracy figure can hide a model that simply ALLOWs everything when
most real messages are benign. Likewise, 99% precision on emitted BLOCKs
does not establish 99% recall, whole-decision correctness, or fairness to
ordinary Minecraft gameplay. A model with errors in the semantic label,
review routing, strike, containment or support flow has not made an entirely
correct moderation decision even when it chose the right visibility action.

A retrospective real-data holdout sampled *after* earlier model scoring/mining
can be useful for development but is **not a pristine unseen acceptance set**.
Never use W20, W27, or any sealed holdout for development, automatic tooling
smoke tests, threshold selection, or repeated evaluation without their separate
owner-authorized acceptance protocol.

## Two independently frozen populations (never combine their denominators)

**Cohort A: prospective, prevalence-preserving normal traffic.** Collect only
new authorized chat messages *after the candidate/model/thresholds are frozen*,
under privacy restrictions and real chronological context. Random or otherwise
predeclared temporal/session-based inclusion must preserve the actual ALLOW
prevalence and Minecraft/Discord/channel split, not select cases by the model's
own score. Separately record normal gameplay, private friendship banter and
ordinary disagreement so false-block rates are believable. Independent
reviewers must adjudicate each visible target as of its message timestamp.
Avoid raw chat or identifiers in public GitHub.

**Cohort B: prospective rare-risk challenge suite.** Recruit independently
written/adjudicated, natural-context threat, directed self-harm abuse, slur,
sexual-minor, doxxing and grooming scenarios, with contextually close benign
contrasts, paraphrases, evasion and splits across messages. Predeclare families
and sources and keep this suite out of training and threshold fitting. The
challenge distribution intentionally enriches rare cases and **cannot** be
used to estimate production prevalence or false alarms per ordinary message.
Existing owner golden, W20, and W27 remain separately reserved.

Both are held out from iterative model selection. If results motivate model
changes, retire these exact cohorts as pristine acceptance evidence. Collect
new unseen cohorts for the next acceptance claim. Prevent same-session,
same-family, temporal and exact/near-duplicate overlap across train, dev and
either cohort. Double-review safety-critical cases and adjudicate disagreement
without revealing the candidate prediction to reviewers.

## Provisional evidence floors in the new offline tool

The gate deliberately requires **both** sources, not one combined benchmark.
All intervals are Wilson **95% two-sided** intervals.

| Population | Required provisional evidence |
|---|---|
| A: natural chat | At least 1,000 targets and 3,500 adjudicated ALLOW targets |
| A: whole decision | Lower 95% confidence bound at least **99%** for exact match across all seven fields: semantic label, action, review priority, strike, containment, mute duration, support flow |
| A: action | Lower 95% bound at least **99%** for ALLOW/REVIEW/BLOCK action accuracy |
| A: false blocks | Upper 95% bound at most **1 wrongful BLOCK / 1,000 truly ALLOW messages** |
| B: consequence | Lower 95% bound at least **99% BLOCK precision** and **95% BLOCK recall** |
| B: critical labels | At least **80** confirmed BLOCK targets per each of six enumerated risk classes; lower 95% bound at least **95%** correct BLOCK routing in each |
| A + B: punishments | **Zero** suggested false strikes or false mutes in either cohort; this is **not** sufficient evidence to switch automatic punishments on |

With **zero** observed false BLOCKs, a 95%-upper FPR bound below
1/1,000 requires approximately 3,840 benign examples; small perfect
test sets do not demonstrate that rate. Confidence requirements may demand
far more cases when errors exist. A rare category with seven test items can
never substantiate 99% category reliability.

These are **not** thresholds approved by the owner, a full fairness audit,
or proof of future reliability. Before production action, separately assess
latency, fail-open behavior, server load, false positives per channel,
appeals/recourse, targeted abuse rates, review volume and drift. Revisit
the targets with the owner before treating any numbers as release policy.

## Proposed model/retraining strategy, in priority order

1. **Independent labels before compute.** Triage G10–G27's 9,000 candidate
   synthetic labels. Resolve documented conflicts, use two human reviewers for
   difficult cases, and admit only approved source/family groups. Capture
   correctly consented and privacy-reviewed natural chat. Never treat Qwen,
   OpenAI or an earlier classifier output as ground truth.
2. **Compare candidates on the same development splits.** Finish W25's five
   model architectures, including transformer/context, character/obfuscation
   handling, a word baseline, deterministic policy routing, and a calibrated
   precision-first cascade. Do not choose a model from repeated W20 checks.
3. **Three-way conservative policy:** high-confidence ALLOW, sufficiently
   verified BLOCK, uncertain REVIEW. Cross-model disagreement and incomplete
   chronology lower certainty; avoid punishing uncertainty. Deterministic
   policy boundaries must override unsupported predictions, with provenance
   and isolated care/support flows.
4. **Active learning without contamination:** sample new, authorized,
   diverse mistakes and disagreements for *future training*, ensure source
   groups are split once, and retire used eval records. Favor hard-negative
   gameplay/private-friend pairs and rare severe false negatives.
5. **One frozen independent acceptance event, then shadow-only rollout.**
   Shadow runs must expose counts, disagreement, appeal outcomes, availability
   and latency. Automatic sanctions require an entirely separate explicit
   safety review; automatic bans remain prohibited under Policy v1.

## Tool: offline *evidence preflight* only

Existing `tools/data_v2/policy_eval_metrics.py` strictly validates private
seven-field, independently adjudicated Policy-v1 heldout truth vs predictions
and reports only aggregates. The additive
`tools/data_v2/prospective_accuracy_gate.py` consumes **two disjoint
truth/prediction pairs** plus a separate, private cohort attestation:

```bash
python -m tools.data_v2.prospective_accuracy_gate \
  --natural-truth /private/natural-truth.jsonl \
  --natural-predictions /private/natural-predictions.jsonl \
  --challenge-truth /private/challenge-truth.jsonl \
  --challenge-predictions /private/challenge-predictions.jsonl \
  --attestation /private/prospective-attestation.json
```

The attestation JSON needs the exact keys below. Example values are only
schema illustrations, **not verified authorizations**:

```json
{
  "schema_version": "prospective-accuracy-evidence/1",
  "model_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "natural_cohort_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "challenge_cohort_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "natural_cases": 4100,
  "challenge_cases": 600,
  "independent_audit_reference": "PRIVATE-case-review-ledger-reference",
  "candidate_frozen_before_both_cohorts": true,
  "natural_prospective_never_scored": true,
  "challenge_fresh_and_predeclared": true,
  "sessions_and_families_disjoint_from_training": true,
  "cohorts_disjoint_from_each_other": true,
  "independently_double_adjudicated": true,
  "reviewers_blind_to_model_predictions": true,
  "neither_cohort_used_for_tuning": true,
  "privacy_and_source_rights_verified": true,
  "natural_sample_preserves_actual_prevalence": true
}
```

Never generate this attestation by simply setting booleans to true: the
assertions must be independently checked against source rights, immutable
manifests, actual reviewer ledgers, frozen candidate SHA, and private
split fingerprints. This Python tool **cannot verify those claims** and
therefore returns only `NOT_ESTABLISHED` or
`PROVISIONAL_EVIDENCE_THRESHOLDS_MET`. The latter still explicitly says
`not_a_deployment_authorization: true` and
`never_authorizes_automatic_punishments: true`.

Do not commit raw chat, private attestations, reviewer decisions,
heldout case IDs, member identities, personal details or model prompts.
Unit tests use invented decisions only and have **no real accuracy claim**.
