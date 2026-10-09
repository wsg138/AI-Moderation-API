# DATA-V2-18 — private first-wave owner action intake

**Status:** experimental, offline, candidate-only. Not verified semantic labels,
training gold, Policy v2, or live moderation.

## Motivation

The owner submitted five action-only decisions from the first-wave blinded
questionnaire. They were previously reconciled with a one-off script. This tool
makes that check reusable and fail-closed, before any action-only owner decisions
can enter the private coordinator registry.

Run only on an authorized private workstation. Never commit owner answers,
review packets, crosswalks, private registries, or opaque case IDs to GitHub.

## Local usage

```powershell
python -m tools.data_v2.owner_blind_action_intake `
  --packet-input "C:\Private\reviewer\round1-blind.jsonl" `
  --crosswalk-input "C:\Private\coordinator\round1-crosswalk.jsonl" `
  --owner-input "C:\Private\coordinator\owner-five-decisions.json" `
  --private-registry-out "C:\Private\coordinator\owner-verified.jsonl"
```

All paths must be outside the current Git checkout. The destination must
not exist or alias an input. The tool never mutates the original candidate
dataset, questionnaire inputs, first-wave selection or existing registry.

## Verification steps

1. Load and SHA-256-verify all 9,000 source-pinned synthetic G10–G27 rows.
2. Independently recreate the **frozen, ordered 180-case first wave**.
3. Verify that all 180 private crosswalk entries map to those exact source
   examples in order, with unique blinded IDs and source provenance.
4. Reconstruct every review packet using the strict as-of-target projection.
   Reject any changed message, speaker, index, channel or extra field.
5. Validate owner JSON fields, count, packet IDs, three-valued action,
   duplicate submissions, and short optional reasons. Reject any
   `training_eligible: true` or unauthorized label/punishment fields.
6. Write a fresh coordinator-only JSONL registry with
   `semantic_label_verified: false`, `punishment_fields_verified: false`
   and `training_eligible: false`; print aggregate numbers only.

An owner REVIEW action is not an automatic block, strike or mute. This
tool does **not** authenticate the owner identity or rederive the original
secret-derived HMAC mapping (its secret was ephemeral). It explicitly reports
`opaque_crosswalk_key_authenticated: false`.

## Test results

Nine new tests passed locally on Windows, including source metadata
tampering, crosswalk reordering, post-target or target-context modification,
duplicate/unknown owner packet IDs, non-answer responses, extra semantic
fields and attempted training admission. Ruff and repository complexity
checks passed.

The existing **private** five-answer questionnaire also passed end-to-end
intake: 2 ALLOW, 3 REVIEW, 4 differences from initial *candidate* actions;
0 semantic labels or punishments verified, 0 training approvals. No
case-level result, private file path or packet ID belongs in GitHub.

## Next boundaries

The source is public synthetic data, not real player conversations.
Action-only owner judgments are not complete policy annotations. The
existing two related-family local AI reviewers are not independent gold.
Held-out estimates require genuinely independent reviewers, family-safe
splits and additional source checks. Do not merge, deploy, activate policy,
train models or generate automatic punishments based on this proposal.
