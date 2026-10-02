# Dataset schema

Training/evaluation files use JSONL: one JSON object per example.

## Generator record requiredness

Every W02–W10 generator record (`G01` through `G09`) must include every field shown in the record example below except `family_id`.

All Policy-v1 outcome dimensions are required so records cannot silently omit owner-policy state. `containment_duration_seconds` is a required field with a nullable value: use `null` when there is no containment or when Policy v1 explicitly leaves the mute duration unresolved. Do not omit the field and do not invent a duration from a nearby policy example.

## Record

```json
{
  "example_id": "G01-0001",
  "policy_version": "v1",
  "source": "synthetic",
  "domain": "real_world_threat",
  "difficulty": "hard",
  "platform_hint": "minecraft",
  "channel_profile": "minecraft_public",
  "messages": [
    {
      "speaker": "A",
      "offset_ms": -1800,
      "text": "im gonna stab you"
    },
    {
      "speaker": "A",
      "offset_ms": 0,
      "text": "irl"
    }
  ],
  "target_index": 1,
  "label": "REAL_WORLD_THREAT",
  "action": "BLOCK",
  "review_priority": "URGENT",
  "strike": true,
  "containment": "MUTE",
  "containment_duration_seconds": 604800,
  "support_flow": "NONE",
  "reason_codes": [
    "split_message_context",
    "explicit_real_world_cue",
    "targeted_violence"
  ],
  "notes": "Synthetic hard pair.",
  "family_id": "threat.real-world-cue.001"
}
```

`family_id` is optional. When present, it groups paraphrases/minimal pairs that should remain together during later leakage-safe splitting. The dataset QA tooling validates its syntax but W11 owns final family decisions and splits.

## Semantic labels

Policy v1 refines the initial vocabulary. Dataset workers may use:

- `SAFE`
- `GAMEPLAY_VIOLENCE`
- `LOW_LEVEL_HARASSMENT`
- `SEVERE_HARASSMENT`
- `STAFF_TARGETED_ABUSE`
- `REAL_WORLD_THREAT`
- `SELF_HARM_INSTRUCTION`
- `SELF_HARM_INTENT`
- `THIRD_PARTY_SELF_HARM_CONCERN`
- `HATE`
- `SLUR_USE`
- `SEXUAL_CONTENT`
- `SEXUAL_MINOR`
- `DOXXING`
- `BLACKMAIL`
- `GROOMING`
- `DANGEROUS_REAL_WORLD_INSTRUCTIONS`
- `AMBIGUOUS_REVIEW`

Use the narrowest label that expresses semantic truth. Policy/action fields remain separate.

## Policy outcome fields

### `action`
- `ALLOW` — remain visible/no block.
- `REVIEW` — remain visible under the example's intended behavior but create review work. Do not use this field alone to encode urgency.
- `BLOCK` — prevent/retroactively remove the target message as policy requires.

### `review_priority`
- `NONE`
- `NORMAL`
- `URGENT`

### `strike`
Boolean owner-desired strike/evidence escalation for this example. Use only JSON `true` or `false`, never integer or string stand-ins.

### `containment`
- `NONE`
- `MUTE`

### `containment_duration_seconds`
Required field with a nullable value.

- `containment: NONE` requires `containment_duration_seconds: null`.
- `containment: MUTE` uses a positive integer when owner policy gives a concrete duration for that example.
- `containment: MUTE` may use `null` only when Policy v1 explicitly leaves that duration unresolved. Dataset QA permits this but emits a warning for human confirmation.
- Zero, negative, boolean, string, and fractional durations are invalid.

### `support_flow`
- `NONE`
- `SELF_HARM_CHECK`
- `TARGET_SAFETY_CHECK`

These fields intentionally separate message visibility, staff review, strike recommendation, temporary containment, and care/support behavior.

## Channel profiles

Normalized profiles:

- `minecraft_public`
- `minecraft_private`
- `discord_general`
- `discord_gaming`
- `discord_staff_exempt`
- `discord_ticket_exempt`
- `discord_configured_exempt`

Exempt profiles are deterministic integration/runtime state and normally should not be sent to the semantic classifier. They may still appear in deliberate policy-engine fixtures, but dataset QA warns whenever an exempt profile appears so reviewers can verify that it was intentional.

## Reason codes

Reason codes are short, auditable facts. They are not hidden reasoning.

### Context / platform
- `minecraft_gameplay_explicit`
- `discord_gameplay_explicit`
- `discord_general_no_game_context`
- `private_context_relevant`
- `cross_platform_linked_context`
- `reply_context`
- `split_message_context`
- `long_gap_breaks_linkage`
- `insufficient_context`

### Real-world / gameplay distinction
- `explicit_real_world_cue`
- `real_world_location`
- `real_world_time`
- `real_world_proximity`
- `real_world_delivery_cue`
- `real_world_address_cue`
- `house_ambiguous_gameplay`
- `targeted_violence`

### Harassment / relationship
- `low_severity_insult`
- `repeated_targeting`
- `target_requested_stop`
- `mutual_banter_evidence`
- `consent_uncomfortable`
- `multi_sender_dogpile`
- `coordinated_dogpile`
- `prior_confirmed_incident`
- `target_strict_filter`
- `ignored_relationship`
- `staff_targeted_abuse`

### Self-harm / care
- `self_harm_instruction`
- `self_harm_disclosure`
- `third_party_self_harm_concern`
- `gameplay_death_context`
- `safety_check_recent`

### Hate / slurs
- `identity_target`
- `actual_slur`
- `slur_reference_only`
- `quoted_or_condemned`
- `reclaimed_slur`
- `obfuscated_evasion`

### Sexual / age
- `public_sexual_content`
- `public_flirting`
- `private_flirting`
- `sexual_solicitation`
- `sexual_minor`
- `age_self_report_clue`
- `age_reliable_minor`
- `age_disputed`

### Severe safety / dangerous instructions
- `apparent_doxxing`
- `confirmed_doxxing`
- `blackmail`
- `grooming_pattern`
- `dangerous_instruction_request`
- `historical_or_high_level_context`

### Review/correction
- `staff_confirmed`
- `staff_overturned_false_positive`

Do not store free-form hidden reasoning. Human notes may explain a policy decision in ordinary concise language.

## Memory-derived context

If an example uses structured moderation memory, record only the minimum facts needed in `notes` or a future structured context field. Do not fabricate history. Self-harm/safety history must not be used as punishment reputation.

## Uniqueness

Every generator owns a fixed ID prefix/range. Current generator issues define `G01-0001..G01-0500` through `G09-0001..G09-0500`. Exact duplicate normalized message sequences are forbidden. The integration worker also performs near-duplicate checks before merge.

## Splits

Do not randomly split near-variants across train and eval. Families of paraphrases/hard pairs must remain grouped to avoid evaluation leakage.

The final integrator creates:
- training;
- validation;
- frozen evaluation;
- adversarial/split-message evaluation.

## Production-derived examples

Production records are never automatically committed.

A reviewed export must:
1. remove/pseudonymize identifiers;
2. remove secrets/private staff data;
3. receive a human label/action;
4. include only the minimum context needed;
5. be deliberately added to `data/curated/`.

Staff-overturned AI false positives are especially valuable negative examples once reviewed/redacted.
