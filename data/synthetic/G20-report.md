# Dataset QA report

- File: `data/synthetic/G20-school-threats.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **12**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.678000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `real_world_threat` | 500 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 75 |
| `easy` | 75 |
| `hard` | 225 |
| `medium` | 125 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 128 |
| `minecraft` | 372 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 67 |
| `discord_general` | 61 |
| `minecraft_private` | 54 |
| `minecraft_public` | 318 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 25 |
| `REAL_WORLD_THREAT` | 400 |
| `SAFE` | 75 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 75 |
| `BLOCK` | 400 |
| `REVIEW` | 25 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 75 |
| `NORMAL` | 25 |
| `URGENT` | 400 |

### containment

| Value | Count |
|---|---:|
| `MUTE` | 400 |
| `NONE` | 100 |

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
| `concrete` | 400 |
| `mute_with_duration` | 400 |
| `null` | 100 |

### Reason codes

| Value | Count |
|---|---:|
| `coordinated_dogpile` | 35 |
| `explicit_real_world_cue` | 212 |
| `historical_or_high_level_context` | 25 |
| `insufficient_context` | 50 |
| `mutual_banter_evidence` | 25 |
| `quoted_or_condemned` | 20 |
| `real_world_location` | 400 |
| `real_world_proximity` | 30 |
| `real_world_time` | 310 |
| `reply_context` | 40 |
| `targeted_violence` | 383 |

### Message count

| Value | Count |
|---|---:|
| `1` | 161 |
| `2` | 299 |
| `3` | 37 |
| `4` | 3 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G20-0002` | `G20-0038` | 0.967213 | `near_duplicate_candidate` |
| `G20-0016` | `G20-0021` | 0.945736 | `near_duplicate_candidate` |
| `G20-0132` | `G20-0137` | 0.954955 | `near_duplicate_candidate` |
| `G20-0148` | `G20-0153` | 0.921986 | `near_duplicate_candidate` |
| `G20-0152` | `G20-0171` | 0.921569 | `near_duplicate_candidate` |
| `G20-0227` | `G20-0229` | 0.938053 | `near_duplicate_candidate` |
| `G20-0373` | `G20-0398` | 0.945455 | `near_duplicate_candidate` |
| `G20-0373` | `G20-0400` | 0.921739 | `near_duplicate_candidate` |
| `G20-0398` | `G20-0400` | 0.954955 | `near_duplicate_candidate` |
| `G20-0429` | `G20-0442` | 0.950000 | `near_duplicate_candidate` |
| `G20-0429` | `G20-0445` | 0.991304 | `near_duplicate_candidate` |
| `G20-0442` | `G20-0445` | 0.942149 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G20-0002`, `G20-0038`
- `SUGGESTED-0002`: `G20-0016`, `G20-0021`
- `SUGGESTED-0003`: `G20-0132`, `G20-0137`
- `SUGGESTED-0004`: `G20-0148`, `G20-0153`
- `SUGGESTED-0005`: `G20-0152`, `G20-0171`
- `SUGGESTED-0006`: `G20-0227`, `G20-0229`
- `SUGGESTED-0007`: `G20-0373`, `G20-0398`, `G20-0400`
- `SUGGESTED-0008`: `G20-0429`, `G20-0442`, `G20-0445`
