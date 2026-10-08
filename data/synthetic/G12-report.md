# Dataset QA report

- File: `data/synthetic/G12-grooming.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **5**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.962000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `grooming` | 500 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 75 |
| `easy` | 83 |
| `hard` | 225 |
| `medium` | 117 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 111 |
| `minecraft` | 389 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 75 |
| `discord_general` | 36 |
| `minecraft_private` | 242 |
| `minecraft_public` | 147 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 12 |
| `GROOMING` | 400 |
| `SAFE` | 88 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 88 |
| `BLOCK` | 400 |
| `REVIEW` | 12 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 88 |
| `NORMAL` | 12 |
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
| `age_reliable_minor` | 151 |
| `age_self_report_clue` | 135 |
| `cross_platform_linked_context` | 55 |
| `discord_gameplay_explicit` | 2 |
| `grooming_pattern` | 400 |
| `insufficient_context` | 12 |
| `minecraft_gameplay_explicit` | 255 |
| `reply_context` | 78 |
| `split_message_context` | 418 |

### Message count

| Value | Count |
|---|---:|
| `1` | 19 |
| `2` | 89 |
| `3` | 128 |
| `4` | 92 |
| `5` | 67 |
| `6` | 37 |
| `7` | 68 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G12-0213` | `G12-0218` | 0.923077 | `near_duplicate_candidate` |
| `G12-0452` | `G12-0454` | 0.933333 | `near_duplicate_candidate` |
| `G12-0457` | `G12-0470` | 0.926108 | `near_duplicate_candidate` |
| `G12-0459` | `G12-0467` | 0.945055 | `near_duplicate_candidate` |
| `G12-0488` | `G12-0500` | 0.927273 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G12-0213`, `G12-0218`
- `SUGGESTED-0002`: `G12-0452`, `G12-0454`
- `SUGGESTED-0003`: `G12-0457`, `G12-0470`
- `SUGGESTED-0004`: `G12-0459`, `G12-0467`
- `SUGGESTED-0005`: `G12-0488`, `G12-0500`
