# Dataset QA report

- File: `data/synthetic/G19-sexual-content.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **19**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.594000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `sexual_content` | 500 |

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
| `discord` | 275 |
| `minecraft` | 225 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 149 |
| `discord_general` | 126 |
| `minecraft_private` | 66 |
| `minecraft_public` | 159 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 25 |
| `SAFE` | 75 |
| `SEXUAL_CONTENT` | 400 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 75 |
| `BLOCK` | 400 |
| `REVIEW` | 25 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 475 |
| `NORMAL` | 25 |

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
| `false` | 244 |
| `true` | 256 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `null` | 500 |

### Reason codes

| Value | Count |
|---|---:|
| `discord_general_no_game_context` | 14 |
| `historical_or_high_level_context` | 18 |
| `insufficient_context` | 25 |
| `minecraft_gameplay_explicit` | 19 |
| `mutual_banter_evidence` | 22 |
| `obfuscated_evasion` | 56 |
| `private_context_relevant` | 78 |
| `public_flirting` | 84 |
| `public_sexual_content` | 324 |
| `quoted_or_condemned` | 2 |
| `sexual_solicitation` | 256 |
| `split_message_context` | 18 |

### Message count

| Value | Count |
|---|---:|
| `1` | 203 |
| `2` | 209 |
| `3` | 88 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G19-0012` | `G19-0095` | 0.963855 | `near_duplicate_candidate` |
| `G19-0017` | `G19-0065` | 0.965517 | `near_duplicate_candidate` |
| `G19-0024` | `G19-0320` | 0.928571 | `near_duplicate_candidate` |
| `G19-0044` | `G19-0191` | 0.929577 | `near_duplicate_candidate` |
| `G19-0073` | `G19-0353` | 0.931818 | `near_duplicate_candidate` |
| `G19-0075` | `G19-0186` | 0.925926 | `near_duplicate_candidate` |
| `G19-0115` | `G19-0285` | 0.937500 | `near_duplicate_candidate` |
| `G19-0120` | `G19-0266` | 0.963855 | `near_duplicate_candidate` |
| `G19-0125` | `G19-0332` | 0.938272 | `near_duplicate_candidate` |
| `G19-0141` | `G19-0346` | 0.966667 | `near_duplicate_candidate` |
| `G19-0142` | `G19-0157` | 0.960000 | `near_duplicate_candidate` |
| `G19-0149` | `G19-0254` | 0.942857 | `near_duplicate_candidate` |
| `G19-0159` | `G19-0424` | 0.962264 | `near_duplicate_candidate` |
| `G19-0177` | `G19-0239` | 0.927273 | `near_duplicate_candidate` |
| `G19-0206` | `G19-0315` | 0.924528 | `near_duplicate_candidate` |
| `G19-0248` | `G19-0471` | 0.947368 | `near_duplicate_candidate` |
| `G19-0279` | `G19-0322` | 0.960000 | `near_duplicate_candidate` |
| `G19-0366` | `G19-0420` | 0.933333 | `near_duplicate_candidate` |
| `G19-0453` | `G19-0463` | 0.941176 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G19-0012`, `G19-0095`
- `SUGGESTED-0002`: `G19-0017`, `G19-0065`
- `SUGGESTED-0003`: `G19-0024`, `G19-0320`
- `SUGGESTED-0004`: `G19-0044`, `G19-0191`
- `SUGGESTED-0005`: `G19-0073`, `G19-0353`
- `SUGGESTED-0006`: `G19-0075`, `G19-0186`
- `SUGGESTED-0007`: `G19-0115`, `G19-0285`
- `SUGGESTED-0008`: `G19-0120`, `G19-0266`
- `SUGGESTED-0009`: `G19-0125`, `G19-0332`
- `SUGGESTED-0010`: `G19-0141`, `G19-0346`
- `SUGGESTED-0011`: `G19-0142`, `G19-0157`
- `SUGGESTED-0012`: `G19-0149`, `G19-0254`
- `SUGGESTED-0013`: `G19-0159`, `G19-0424`
- `SUGGESTED-0014`: `G19-0177`, `G19-0239`
- `SUGGESTED-0015`: `G19-0206`, `G19-0315`
- `SUGGESTED-0016`: `G19-0248`, `G19-0471`
- `SUGGESTED-0017`: `G19-0279`, `G19-0322`
- `SUGGESTED-0018`: `G19-0366`, `G19-0420`
- `SUGGESTED-0019`: `G19-0453`, `G19-0463`
