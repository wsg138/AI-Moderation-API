# G06 sexual/minor synthetic dataset report

## Worker summary

- Dataset: `data/synthetic/G06-sexual-minor.jsonl`
- Range: `G06-0001..G06-0500`
- Records: **500**
- Policy version: `v1`
- Source: `synthetic`
- Schema-equivalent local preflight: **0 errors, 0 warnings**
- Exact normalized duplicate groups: **0**
- Near/minimal-pair candidates: **3**, all deliberate public/private flirting boundary contrasts
- Multi-message records: **287 / 500 (57.4%)**
- Family IDs: **145 distinct families**, covering **320 records**

## Coverage bucket counts

| Bucket | Count |
|---|---:|
| public sexual/NSFW | 100 |
| public non-explicit flirting | 80 |
| private non-explicit flirting | 80 |
| nude-image solicitation | 80 |
| reliably-known-minor sexualized/grooming | 80 |
| age-evidence minimal pairs | 50 |
| safe ordinary age/social/nonsexual | 30 |

## Distributions

### Action

| Value | Count |
|---|---:|
| `ALLOW` | 135 |
| `BLOCK` | 365 |

### Label

| Value | Count |
|---|---:|
| `GROOMING` | 20 |
| `SAFE` | 215 |
| `SEXUAL_CONTENT` | 180 |
| `SEXUAL_MINOR` | 85 |

### Channel profile

| Value | Count |
|---|---:|
| `discord_gaming` | 55 |
| `discord_general` | 98 |
| `minecraft_private` | 216 |
| `minecraft_public` | 131 |

### Review priority

| Value | Count |
|---|---:|
| `NONE` | 395 |
| `NORMAL` | 65 |
| `URGENT` | 40 |

### Strike

| Value | Count |
|---|---:|
| `false` | 335 |
| `true` | 165 |

### Containment

| Value | Count |
|---|---:|
| `MUTE` | 40 |
| `NONE` | 460 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `concrete` | 40 |
| `mute_with_duration` | 40 |
| `null` | 460 |

### Message count

| Value | Count |
|---|---:|
| `1` | 213 |
| `2` | 252 |
| `3` | 15 |
| `4` | 20 |

## Multi-message coverage

287 records use 2–4 message sequences. These cover reply context, split nude solicitation, reliable-age context followed by a target message, minor-consent context, and multi-step secrecy/private-contact grooming patterns. The remaining 213 records are intentionally single-message cases for ordinary public/private surface boundaries and safe controls.

## Family / minimal-pair coverage

145 explicit `family_id` values group 320 records. The age-evidence bucket contains 25 two-record clue-vs-reliable-evidence families. The QA similarity scan retains three intentional public/private flirting candidates: `G06-0133`↔`G06-0213`, `G06-0133`↔`G06-0253`, and `G06-0138`↔`G06-0218`. They are retained because surface/context changes policy action while the flirt remains non-explicit.

## QA warnings and disposition

The final local schema/duplicate preflight produced no errors and no warnings. No `MUTE + null`, exempt-channel, empty-reason-code, duplicate-reason-code, or near-contradiction warning remains. The three similarity candidates above are informational near/minimal-pair candidates, not QA warnings.

## Golden-set leakage review

The owner-policy golden set was read only to learn resolved boundaries. No exact golden message sequence was copied, and the synthetic records avoid trivial one-word rewrites of the protected fixtures. Conceptually close cases use fresh scenarios and family grouping so W11 can preserve leakage-safe splits.

## Notable hard boundaries represented

- Public sexual/NSFW discussion blocks even when non-graphic.
- Ordinary non-explicit flirting blocks in public but is allowed in Minecraft PMs.
- Nude-image solicitation blocks and creates a strike on both public and private moderated surfaces.
- Reliable minor evidence changes sexualized comments to `SEXUAL_MINOR` block + strike; the minor saying they are comfortable does not override that rule.
- Reliably known 16-year-old + nude solicitation uses the owner’s seven-day mute anchor and urgent staff review.
- Clear secrecy/private-contact grooming with reliable minor evidence blocks, alerts staff through urgent review, and uses the owner’s approximately seven-day containment anchor.
- Self-reported age alone remains a clue rather than proof; contradictory self-reports are explicitly represented.
- Ordinary age, family, school, gaming, birthday, and eligibility discussion stays allowed when it is nonsexual.

## Deliberately omitted unresolved Policy-v1 edges

Consensual explicit-adult PM content and grooming-like behavior with genuinely uncertain age are deliberately excluded. This worker also does not invent behavior for Discord bot DMs or any unrelated unresolved policy edge.

## Known limitations

This worker can guarantee within-file uniqueness and leakage review against the frozen owner golden set, but not cross-worker semantic uniqueness. W11 remains responsible for cross-worker exact/near-deduplication and final family-safe splitting. Reliable-age examples use synthetic staff/system evidence rather than production identity data.

## Canonical QA tables

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `age_evidence` | 50 |
| `grooming` | 20 |
| `sexual_content` | 340 |
| `sexual_minor` | 60 |
| `social` | 30 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 63 |
| `easy` | 123 |
| `hard` | 178 |
| `medium` | 136 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 153 |
| `minecraft` | 347 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 55 |
| `discord_general` | 98 |
| `minecraft_private` | 216 |
| `minecraft_public` | 131 |

### label

| Value | Count |
|---|---:|
| `GROOMING` | 20 |
| `SAFE` | 215 |
| `SEXUAL_CONTENT` | 180 |
| `SEXUAL_MINOR` | 85 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 135 |
| `BLOCK` | 365 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 395 |
| `NORMAL` | 65 |
| `URGENT` | 40 |

### containment

| Value | Count |
|---|---:|
| `MUTE` | 40 |
| `NONE` | 460 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 500 |

### Strike

| Value | Count |
|---|---:|
| `false` | 335 |
| `true` | 165 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `concrete` | 40 |
| `mute_with_duration` | 40 |
| `null` | 460 |

### Reason codes

| Value | Count |
|---|---:|
| `age_disputed` | 5 |
| `age_reliable_minor` | 105 |
| `age_self_report_clue` | 45 |
| `grooming_pattern` | 20 |
| `insufficient_context` | 10 |
| `private_context_relevant` | 216 |
| `private_flirting` | 105 |
| `public_flirting` | 80 |
| `public_sexual_content` | 158 |
| `reply_context` | 20 |
| `sexual_minor` | 85 |
| `sexual_solicitation` | 100 |
| `split_message_context` | 40 |

### Message count

| Value | Count |
|---|---:|
| `1` | 213 |
| `2` | 252 |
| `3` | 15 |
| `4` | 20 |

### Diagnostic codes

| Value | Count |
|---|---:|

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G06-0133` | `G06-0213` | 0.962963 | `minimal_pair_candidate` |
| `G06-0133` | `G06-0253` | 0.951220 | `minimal_pair_candidate` |
| `G06-0138` | `G06-0218` | 0.934579 | `minimal_pair_candidate` |

### Family suggestions

- Intentional public/private surface pairs and all age-evidence clue/reliable contrasts already have explicit family design; W11 owns final integration grouping.
