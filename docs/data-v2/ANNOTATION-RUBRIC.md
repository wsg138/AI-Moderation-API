# Data/Model v2 — provisional independent-labeling rubric

**Provisional process document**. Read and apply the accepted owner [Policy v1](../../policy/KNOWN-DECISIONS.md), `policy/` interview/decision records, and [dataset schema](../DATASET-SCHEMA.md). If this rubric conflicts with authoritative policy, **pause and log an owner question**; do not invent a new punishment rule. This rubric is for offline human/independent review, **not live enforcement**.

## Reviewer packet and privacy boundary

A reviewer receives only an *approved-for-that-reviewer*, minimally necessary, privacy-reviewed example:
- One target message index; prior messages available before that target, in original chronological order (ordinary SAFE traffic remains present).
- Channel/platform and trusted context facts when actually known, with a timestamp offset and stable **within-window** speaker aliases.
- No subsequent messages, source gold label, previous model prediction/confidence, user identity, private staff information, raw source path, or real IP/UUID.
- Source group and privacy/consent clearance are verified outside the public JSONL.

**Caution:** Real-chat v4 currently has some potentially unredacted names in text. Do not forward raw/review windows to outside collaborators, third-party labelers, or cloud models without clearance; synthetic fixtures are safe discussion material.

## Annotation order (facts before enforcement)

1. Confirm the target and available context, including whether a long gap or change of server/channel breaks the conversation.
2. Identify **literal meaning**: Minecraft gameplay vs real-world, quote/report vs endorsement, self-directed vs directed at another player, role/identity targeting, age reliability, whether harm is genuinely actionable.
3. Assign the narrowest policy semantic label; mark uncertainty when the evidence doesn't settle the distinction.
4. Record structured evidence *reason codes* from the canonical schema; notes should explain relevant visible facts, not hidden reasoning. No fabricated prior incidents.
5. Only after semantic consensus, apply the **versioned deterministic policy resolver** to derive final action/review/strike/containment/support dimensions. For a contested/unresolved policy edge, send to adjudication rather than guessing.
6. Do not let a prior model's answer, lexical search bucket, or generator's desired category determine the label.

## Decision distinctions that must be checked

| Distinction | Review evidence |
|---|---|
| SAFE vs gameplay violence | Threat-like wording in Minecraft PvP/TNT/swords/mace/respawn context is normally gameplay, not real-world harm. Harmless combat/death references may be SAFE depending on policy. |
| Gameplay vs real-world threat | Real-world location, school, arrival/time cues, credible intent, split-message `irl` follow-ups and reliable channel context matter. The target may be a continuation of an earlier threat. |
| Low vs severe harassment | Distinguish ordinary banter/insults, repeated unwanted targeting, coordination/dogpiling and known requests to stop. Duration and evidence of repetition matter. |
| Staff-targeted abuse | Must actually target staff in their capacity as staff, not merely criticize server operation or use a staff label in benign speech. |
| Self-harm instruction vs first-person intent vs third-party concern | Directed encouragement to harm oneself is not the same as someone's disclosure or another person's report of concern. Preserve support routing and avoid punishment of disclosures. |
| Actual slur vs euphemistic reference | **Current Policy v1 §10 says any actual slur is BLOCK + strike even in quotes, reports, counterspeech, jokes, reclaimed use, and deliberate masking/obfuscation.** A euphemism such as “the n-word” may be SAFE when genuinely discussing the term, not using it as a derogatory substitute. Record quote/report/reclaimed *intent facts* without letting them override the owner’s actual-slur block rule. |
| Identity hate vs generic insult | Requires hostility toward a protected identity; a normal interpersonal argument isn't automatically identity hate. |
| Adult sexual content vs sexual-minor vs grooming | Distinguish adult explicit content, reliable minor evidence, coercion or a grooming *pattern*. Mere age mention or one ambiguous conversational line is not sufficient. |
| Doxxing/blackmail vs discussion | Actual exposure or credible threat to reveal private data, invasive request, or coercive demand; merely mentioning the concept of doxxing or asking innocently about a server IP is not proof. |
| Dangerous real-world instructions vs game crafting | Requests/instructions involving real-world harm and actionable detail versus TNT/redstone builds, historical/high-level discussion, or non-actionable quotes. |
| REVIEW vs SAFE | `AMBIGUOUS_REVIEW` requires a genuinely unresolved decision-relevant ambiguity, not “it's short,” “maybe,” or “could eventually escalate.” Innocuous isolated messages are SAFE under owner rulings. |

**Policy alignment warning:** Some early local Qwen annotation prompts and exploratory heuristics treated reported actual slurs as SAFE; that conflicts with accepted Policy v1 §10. Those pseudo-labels are quarantined and must not be copied into supervised truth. Distinguish actual slur occurrence from an indirect reference without repeating the words in public GitHub artifacts.

## Review/adjudication protocol

- **Two independent reviewers** for every critical/safety example selected for authoritative training, and for any model disagreement, severe false-block candidate, policy exception or uncertain label. Each starts blind to the other reviewer's answer.
- The first two reviews must separately record semantic label, evidence/facts, ambiguity level, and confidence. Do not expose gold/model outcome to either reviewer during first pass.
- If reviews disagree, an **owner-policy adjudicator** resolves them using accepted policy; no compromise label by automatic majority vote. Unresolved cases remain excluded from supervised training or explicitly marked REVIEW per policy.
- Track the reviewed **target index**, whether an earlier context message changed classification, and whether a case spans several messages. Audit unlabeled normal context as normal context, not additional harmful targets.
- Staff decisions/appeal reversals are high-value examples but require privacy and provenance clearance, not automatic retraining.
- Keep review approvals, lineage, and exact source hashes in a **private** manifest. Public GitHub may contain schema, aggregate QA counts, synthetic fixtures, and sanitized audit conclusions only.
- Reviewer prompts should be precommitted before blind review and change-controlled; do not include test-set gold examples when claiming independent labeler accuracy.
- Inter-annotator agreement is a **quality signal**, not ground truth. Report disagreement rates *by category* and an adjudication log.

## Suggested private adjudication record (schema sketch; **not** a public real-chat record)

```json
{
  "candidate_id": "PRIVATE-CANDIDATE-ID",
  "source_registry_id": "real-review-train-dev-v1",
  "split": "train",
  "target_index": 3,
  "privacy_review": "APPROVED_LOCAL_ONLY",
  "reviewer_a": {"semantic_label": "SAFE", "confidence": 0.9, "reason_codes": []},
  "reviewer_b": {"semantic_label": "SAFE", "confidence": 0.9, "reason_codes": []},
  "adjudication": {"status": "AGREED", "policy_version": "v1", "final_semantic_label": "SAFE"},
  "supervised_training_admission": false
}
```

The example is schematic. `supervised_training_admission` becomes `true` only after privacy, independent labels, provenance, split/leakage and owner-policy checks are complete.

## Recommended minimum audit before experimental training

- A **random traffic-representative** benign/ordinary sample for specificity and false-block measurement.
- Stratified rare-category candidates *from real conversation windows*; prioritize quality and honest “insufficient evidence” outcomes.
- Hard contrast pairs that differ only in trusted context, but come from synthetic generation or actual independently reviewed real logs.
- Recorded disagreements, corrected examples and remaining uncertainty—not just a large “label count”.
- A prospective untouched test set for claims of real-world accuracy. The current date-grouped real holdout was created after earlier mining and is **not** a pristine never-scored benchmark.

**Promotion gate:** until independent verification and the source registry approval state pass, all Qwen/DeBERTa/Codex/other model outputs remain proposed labels only and are not automatically training truth.
