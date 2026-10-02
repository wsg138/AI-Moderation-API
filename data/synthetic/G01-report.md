# Dataset QA report

- File: `data/synthetic/G01-gameplay.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **20**
- Exact duplicate groups: **0**
- Near candidates: **0**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.140000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `context_linkage` | 55 |
| `gameplay_violence` | 300 |
| `property_gameplay` | 30 |
| `real_world_threat` | 115 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 85 |
| `easy` | 135 |
| `hard` | 205 |
| `medium` | 75 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 60 |
| `minecraft` | 430 |
| `mixed` | 10 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 20 |
| `discord_general` | 40 |
| `minecraft_private` | 5 |
| `minecraft_public` | 435 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 40 |
| `GAMEPLAY_VIOLENCE` | 330 |
| `REAL_WORLD_THREAT` | 115 |
| `SAFE` | 15 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 345 |
| `BLOCK` | 115 |
| `REVIEW` | 40 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 365 |
| `NORMAL` | 103 |
| `URGENT` | 32 |

### containment

| Value | Count |
|---|---:|
| `MUTE` | 5 |
| `NONE` | 495 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 500 |

### Strike

| Value | Count |
|---|---:|
| `false` | 468 |
| `true` | 32 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `concrete` | 5 |
| `mute_with_duration` | 5 |
| `null` | 495 |

### Reason codes

| Value | Count |
|---|---:|
| `discord_gameplay_explicit` | 20 |
| `discord_general_no_game_context` | 40 |
| `explicit_real_world_cue` | 24 |
| `house_ambiguous_gameplay` | 4 |
| `insufficient_context` | 45 |
| `long_gap_breaks_linkage` | 10 |
| `minecraft_gameplay_explicit` | 289 |
| `real_world_address_cue` | 2 |
| `real_world_delivery_cue` | 2 |
| `real_world_location` | 71 |
| `real_world_proximity` | 26 |
| `real_world_time` | 24 |
| `split_message_context` | 55 |
| `targeted_violence` | 115 |

### Message count

| Value | Count |
|---|---:|
| `1` | 430 |
| `2` | 49 |
| `3` | 21 |

### Diagnostic codes

| Value | Count |
|---|---:|
| `empty_reason_codes` | 20 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| _(none)_ |  |  |  |

### Family suggestions

_(none)_

## Worker coverage notes

### Coverage bucket counts

| Bucket | Count |
|---|---:|
| Clear Minecraft gameplay/PvP/property ALLOW | 180 |
| Gameplay ↔ real-world minimal pairs/boundaries | 100 |
| Minecraft / Discord-general / Discord-gaming contrasts | 80 |
| Multi-message / split-message sequences | 70 |
| Griefing / base / house / TNT / roleplay property | 40 |
| Slang / typo / noisy Minecraft language | 30 |

No bucket shift was required.

### Action / label / channel distribution

- Actions: ALLOW 345 (69.0%), BLOCK 115 (23.0%), REVIEW 40 (8.0%).
- Labels: GAMEPLAY_VIOLENCE 330, REAL_WORLD_THREAT 115, AMBIGUOUS_REVIEW 40, SAFE 15.
- Channel profiles: minecraft_public 435, minecraft_private 5, discord_general 40, discord_gaming 20.

### Multi-message coverage

70 / 500 records (14.0%) contain 2–3 connected messages. These cover immediate continuation, disconnected long gaps, same-sender linkage, different-speaker non-stitching, real-world cue flips, location buildup, and severe proximity/address escalation.

### Family / minimal-pair coverage

160 explicit `family_id` groups cover 270 records. Families are used for deliberate contrast/minimal-pair and split-message groupings; standalone easy gameplay records are intentionally not assigned arbitrary families.

### QA warnings and disposition

The expected 20 warnings are all `empty_reason_codes` on the Minecraft side of the channel-profile contrast families. Those records intentionally test Policy v1's strong generic Minecraft gameplay prior with no explicit gameplay cue; assigning `minecraft_gameplay_explicit` would falsely claim evidence that is deliberately absent. No mute-duration, exempt-profile, duplicate-reason, contradiction, or exact-duplicate warning is intentionally present.

### Golden-set leakage review

The protected 52-fixture owner-policy golden set was read before generation. Synthetic wording was created independently; no exact golden message sequence was copied, and obvious trivial one-word variants of the golden threat fixtures were removed during review. Conceptually adjacent families use explicit family IDs so W11 can keep leakage-safe groups together.

### Notable hard boundaries represented

- Generic Minecraft violence versus the same wording in Discord general.
- Discord gaming with explicit game context versus Discord general without it.
- Game locations/times/weapons versus school, work, address, street, proximity, and explicit-IRL cues.
- Immediate same-sender continuations versus unrelated long gaps and different-speaker fragments.
- Minecraft house/base/TNT destruction versus real-home/proximity/delivery language.
- Noisy slang and typos that preserve either gameplay or real-world meaning.

### Deliberately omitted unresolved Policy-v1 edges

Discord bot DMs; graphic first-person self-harm disclosure; consensual explicit adult PM content; grooming with genuinely uncertain minor status; broader dangerous-instruction domains; fake-doxxing strike cleanup; a complete threat severity-to-duration matrix; exact blackmail duration; and accidental lexical slur-substring behavior are excluded. No unresolved outcome was invented.

### Known limitations

This file guarantees uniqueness and coverage within G01 only. Cross-worker semantic deduplication and final leakage-safe train/validation/evaluation splitting remain W11 responsibilities. Real production chat was not used.
