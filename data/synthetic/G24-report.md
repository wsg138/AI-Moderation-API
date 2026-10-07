# Dataset QA report

- File: `data/synthetic/G24-self-harm-intent.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **8**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.722000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `self_harm` | 500 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 75 |
| `easy` | 75 |
| `hard` | 200 |
| `medium` | 150 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 200 |
| `minecraft` | 300 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 77 |
| `discord_general` | 123 |
| `minecraft_private` | 128 |
| `minecraft_public` | 172 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 25 |
| `SAFE` | 75 |
| `SELF_HARM_INTENT` | 400 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 475 |
| `REVIEW` | 25 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 402 |
| `NORMAL` | 25 |
| `URGENT` | 73 |

### containment

| Value | Count |
|---|---:|
| `NONE` | 500 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 100 |
| `SELF_HARM_CHECK` | 400 |

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
| `dangerous_instruction_request` | 45 |
| `gameplay_death_context` | 30 |
| `insufficient_context` | 55 |
| `private_context_relevant` | 121 |
| `quoted_or_condemned` | 15 |
| `reply_context` | 312 |
| `self_harm_disclosure` | 400 |

### Message count

| Value | Count |
|---|---:|
| `1` | 139 |
| `2` | 270 |
| `3` | 91 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G24-0061` | `G24-0219` | 0.985075 | `near_duplicate_candidate` |
| `G24-0075` | `G24-0146` | 0.993548 | `near_duplicate_candidate` |
| `G24-0113` | `G24-0395` | 0.990099 | `near_duplicate_candidate` |
| `G24-0284` | `G24-0497` | 0.965909 | `near_duplicate_candidate` |
| `G24-0316` | `G24-0409` | 0.932203 | `near_duplicate_candidate` |
| `G24-0335` | `G24-0500` | 0.980769 | `near_duplicate_candidate` |
| `G24-0377` | `G24-0428` | 0.948718 | `near_duplicate_candidate` |
| `G24-0379` | `G24-0407` | 0.983607 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G24-0061`, `G24-0219`
- `SUGGESTED-0002`: `G24-0075`, `G24-0146`
- `SUGGESTED-0003`: `G24-0113`, `G24-0395`
- `SUGGESTED-0004`: `G24-0284`, `G24-0497`
- `SUGGESTED-0005`: `G24-0316`, `G24-0409`
- `SUGGESTED-0006`: `G24-0335`, `G24-0500`
- `SUGGESTED-0007`: `G24-0377`, `G24-0428`
- `SUGGESTED-0008`: `G24-0379`, `G24-0407`
