# Dataset schema

Training/evaluation files use JSONL: one JSON object per example.

## Record

```json
{
  "example_id": "G01-000001",
  "policy_version": "draft",
  "source": "synthetic",
  "domain": "gameplay_violence",
  "difficulty": "hard",
  "platform_hint": "minecraft",
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
  "reason_codes": [
    "split_message_context",
    "explicit_real_world_cue",
    "targeted_violence"
  ],
  "notes": "Synthetic hard pair."
}
```

## Initial label vocabulary

The policy interview may refine this before dataset generation starts.

- `SAFE`
- `GAMEPLAY_VIOLENCE`
- `LOW_LEVEL_HARASSMENT`
- `SEVERE_HARASSMENT`
- `REAL_WORLD_THREAT`
- `SELF_HARM_INSTRUCTION`
- `SELF_HARM_INTENT`
- `HATE`
- `SEXUAL_MINOR`
- `DANGEROUS_REAL_WORLD_INSTRUCTIONS`
- `AMBIGUOUS_REVIEW`

Actions:
- `ALLOW`
- `REVIEW`
- `BLOCK`

## Reason codes

Reason codes are short, auditable facts such as:
- `minecraft_gameplay_explicit`
- `real_world_location`
- `real_world_time`
- `explicit_real_world_cue`
- `targeted_violence`
- `split_message_context`
- `self_harm_instruction`
- `self_harm_disclosure`
- `identity_target`
- `sexual_minor`
- `dangerous_instruction_request`
- `quoted_or_condemned`
- `low_severity_insult`
- `obfuscated_evasion`
- `insufficient_context`

Do not store free-form hidden reasoning. Human notes may explain a policy decision in ordinary concise language.

## Uniqueness

Every generator owns a fixed ID prefix/range. Exact duplicate normalized message sequences are forbidden. The integration worker also performs near-duplicate checks before merge.

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
