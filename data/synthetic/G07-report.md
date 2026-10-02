# Dataset QA report

- File: `data/synthetic/G07-dangerous-instructions.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **0**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.144000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `dangerous_instructions` | 345 |
| `minecraft_gameplay` | 155 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 70 |
| `easy` | 114 |
| `hard` | 166 |
| `medium` | 150 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 182 |
| `minecraft` | 234 |
| `mixed` | 84 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 24 |
| `discord_general` | 242 |
| `minecraft_private` | 36 |
| `minecraft_public` | 198 |

### label

| Value | Count |
|---|---:|
| `DANGEROUS_REAL_WORLD_INSTRUCTIONS` | 265 |
| `SAFE` | 235 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 235 |
| `BLOCK` | 265 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 500 |

### containment

| Value | Count |
|---|---:|
| `NONE` | 500 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 500 |

### Strike

| Value | Count |
|---|---:|
| `false` | 500 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `null` | 500 |

### Reason codes

| Value | Count |
|---|---:|
| `dangerous_instruction_request` | 265 |
| `discord_gameplay_explicit` | 21 |
| `explicit_real_world_cue` | 265 |
| `historical_or_high_level_context` | 80 |
| `minecraft_gameplay_explicit` | 134 |
| `obfuscated_evasion` | 50 |
| `reply_context` | 51 |
| `split_message_context` | 56 |

### Message count

| Value | Count |
|---|---:|
| `1` | 428 |
| `2` | 32 |
| `3` | 35 |
| `4` | 5 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| _(none)_ |  |  |  |

### Family suggestions

_(none)_

## W08 coverage summary

### Coverage bucket counts

| Bucket | Records |
|---|---:|
| Real-world explosive-construction requests — BLOCK, request phrasing only | 140 |
| Minecraft TNT/explosive/gameplay — ALLOW | 120 |
| Benign historical/high-level explanation — ALLOW | 80 |
| Minecraft vs Discord/general context contrasts | 70 |
| Obfuscated/evasive real-world explosive requests — BLOCK | 50 |
| Multi-message real-world-intent sequences — BLOCK | 40 |
| **Total** | **500** |

### Action / label / channel distribution

- Actions: **265 BLOCK**, **235 ALLOW**, **0 REVIEW**.
- Labels: **265 DANGEROUS_REAL_WORLD_INSTRUCTIONS**, **235 SAFE**.
- Channels: **242 discord_general**, **198 minecraft_public**, **36 minecraft_private**, **24 discord_gaming**.
- Platforms: **234 minecraft**, **182 discord**, **84 mixed**.

### Multi-message coverage

- **72 / 500** records are multi-message (**14.4%**).
- The required context-only dangerous bucket contributes 40 of those records; additional benign gameplay/history conversations exercise reply and split-message context.

### Family / minimal-pair coverage

- **35 deliberate contrast families** (`dangerous.channel-contrast.001` through `.035`) cover 70 records.
- The canonical QA similarity detector reports **0 near/minimal-pair candidates**. That is expected here because cross-platform contrasts use different platform structural keys and the wording was deliberately varied to avoid template spam.

### QA warnings and disposition

- Pre-PR QA result against the merged Policy-v1 schema/duplicate rules: **0 errors, 0 warnings, 0 exact duplicate groups, 0 near candidates**.
- No warning suppression or invented policy values were used.

### Golden-set leakage review

- Reviewed the protected owner-policy dangerous-instruction fixtures before generation.
- Normalized exact-text comparison found **no copied golden message sequence**.
- Manual review found no trivial one-word edits of the protected dangerous-instruction fixtures; synthetic wording and scenarios were generated independently.
- Conceptually related channel contrasts are explicitly grouped with `family_id` values so downstream split logic can keep families together.

### Notable hard boundaries represented

- Explicit Minecraft TNT/redstone/PvP mechanics remain ALLOW even when explosive vocabulary is prominent.
- Real-world construction intent flips the outcome to BLOCK without adding an automatic strike, mute, or support flow.
- Discord gaming receives explicit game-context ALLOW examples while Discord general carries real-world request BLOCK examples.
- Historical, museum, safety-policy, and high-level chemistry/history discussion remains ALLOW when it does not ask for construction steps.
- Obfuscated requests and attempts to disguise a real-world request as Minecraft/props remain BLOCK.
- Split/reply sequences cover cases where an otherwise vague request becomes a real-world explosive-construction request only after context.

### Deliberately omitted unresolved Policy-v1 edges

- No weapon-construction, poison, malicious-file, or other broader dangerous-instruction domains were added; Policy v1 leaves those unresolved.
- No Discord bot-DM examples were added because that moderation surface remains unresolved.
- No strike/mute duration was invented for simple dangerous-instruction requests; all such records use `strike=false`, `containment=NONE`, and null duration as required by the resolved explosive policy.

### Known limitations

- This is synthetic data only; it contains no production chat, private user data, or operational explosive recipes/components/quantities.
- Cross-worker semantic deduplication and golden-set split hygiene remain W11 integration responsibilities.
- The dataset teaches the resolved explosive boundary only and should not be treated as policy coverage for other dangerous real-world domains.
