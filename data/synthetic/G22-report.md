# Dataset QA report

- File: `data/synthetic/G22-dangerous-instructions-2.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **7**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.478000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `dangerous_instructions` | 500 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 73 |
| `easy` | 87 |
| `hard` | 217 |
| `medium` | 123 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 255 |
| `minecraft` | 245 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 119 |
| `discord_general` | 136 |
| `minecraft_private` | 121 |
| `minecraft_public` | 124 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 8 |
| `DANGEROUS_REAL_WORLD_INSTRUCTIONS` | 403 |
| `SAFE` | 89 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 89 |
| `BLOCK` | 403 |
| `REVIEW` | 8 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 492 |
| `NORMAL` | 8 |

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
| `dangerous_instruction_request` | 403 |
| `explicit_real_world_cue` | 400 |
| `historical_or_high_level_context` | 78 |
| `insufficient_context` | 8 |
| `minecraft_gameplay_explicit` | 11 |

### Message count

| Value | Count |
|---|---:|
| `1` | 261 |
| `3` | 175 |
| `4` | 64 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G22-0002` | `G22-0038` | 0.937500 | `near_duplicate_candidate` |
| `G22-0412` | `G22-0458` | 0.935484 | `near_duplicate_candidate` |
| `G22-0412` | `G22-0475` | 0.953846 | `near_duplicate_candidate` |
| `G22-0419` | `G22-0426` | 0.923077 | `near_duplicate_candidate` |
| `G22-0428` | `G22-0458` | 0.935484 | `near_duplicate_candidate` |
| `G22-0458` | `G22-0475` | 0.950820 | `near_duplicate_candidate` |
| `G22-0470` | `G22-0471` | 0.963636 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G22-0002`, `G22-0038`
- `SUGGESTED-0002`: `G22-0412`, `G22-0428`, `G22-0458`, `G22-0475`
- `SUGGESTED-0003`: `G22-0419`, `G22-0426`
- `SUGGESTED-0004`: `G22-0470`, `G22-0471`
