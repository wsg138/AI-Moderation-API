# Dataset QA report

- File: `data/synthetic/G14-self-harm-third-party.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **32**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.572000**

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
| `easy` | 84 |
| `hard` | 216 |
| `medium` | 125 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 211 |
| `minecraft` | 289 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 137 |
| `discord_general` | 74 |
| `minecraft_private` | 62 |
| `minecraft_public` | 227 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 16 |
| `SAFE` | 84 |
| `THIRD_PARTY_SELF_HARM_CONCERN` | 400 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 84 |
| `REVIEW` | 416 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 84 |
| `NORMAL` | 16 |
| `URGENT` | 400 |

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
| `discord_general_no_game_context` | 10 |
| `explicit_real_world_cue` | 24 |
| `gameplay_death_context` | 31 |
| `insufficient_context` | 26 |
| `minecraft_gameplay_explicit` | 40 |
| `mutual_banter_evidence` | 36 |
| `obfuscated_evasion` | 12 |
| `private_context_relevant` | 14 |
| `quoted_or_condemned` | 54 |
| `reply_context` | 219 |
| `third_party_self_harm_concern` | 400 |

### Message count

| Value | Count |
|---|---:|
| `1` | 214 |
| `2` | 166 |
| `3` | 120 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G14-0201` | `G14-0202` | 0.949309 | `near_duplicate_candidate` |
| `G14-0201` | `G14-0206` | 0.926606 | `near_duplicate_candidate` |
| `G14-0201` | `G14-0212` | 0.930876 | `near_duplicate_candidate` |
| `G14-0202` | `G14-0206` | 0.931507 | `near_duplicate_candidate` |
| `G14-0202` | `G14-0212` | 0.935780 | `near_duplicate_candidate` |
| `G14-0202` | `G14-0216` | 0.926606 | `near_duplicate_candidate` |
| `G14-0203` | `G14-0205` | 0.945736 | `near_duplicate_candidate` |
| `G14-0204` | `G14-0213` | 0.924731 | `near_duplicate_candidate` |
| `G14-0206` | `G14-0212` | 0.922374 | `near_duplicate_candidate` |
| `G14-0206` | `G14-0216` | 0.931507 | `near_duplicate_candidate` |
| `G14-0207` | `G14-0209` | 0.955017 | `near_duplicate_candidate` |
| `G14-0210` | `G14-0214` | 0.930481 | `near_duplicate_candidate` |
| `G14-0212` | `G14-0216` | 0.926606 | `near_duplicate_candidate` |
| `G14-0215` | `G14-0218` | 0.934708 | `near_duplicate_candidate` |
| `G14-0313` | `G14-0321` | 0.935484 | `near_duplicate_candidate` |
| `G14-0335` | `G14-0337` | 0.955752 | `near_duplicate_candidate` |
| `G14-0335` | `G14-0343` | 0.921739 | `near_duplicate_candidate` |
| `G14-0356` | `G14-0357` | 0.920354 | `near_duplicate_candidate` |
| `G14-0356` | `G14-0364` | 0.933921 | `near_duplicate_candidate` |
| `G14-0356` | `G14-0366` | 0.934498 | `near_duplicate_candidate` |
| `G14-0356` | `G14-0367` | 0.933921 | `near_duplicate_candidate` |
| `G14-0357` | `G14-0364` | 0.933333 | `near_duplicate_candidate` |
| `G14-0357` | `G14-0366` | 0.933921 | `near_duplicate_candidate` |
| `G14-0357` | `G14-0367` | 0.933333 | `near_duplicate_candidate` |
| `G14-0359` | `G14-0363` | 0.941704 | `near_duplicate_candidate` |
| `G14-0360` | `G14-0365` | 0.949153 | `near_duplicate_candidate` |
| `G14-0364` | `G14-0367` | 0.938053 | `near_duplicate_candidate` |
| `G14-0366` | `G14-0367` | 0.921053 | `near_duplicate_candidate` |
| `G14-0373` | `G14-0374` | 0.934211 | `near_duplicate_candidate` |
| `G14-0373` | `G14-0375` | 0.927152 | `near_duplicate_candidate` |
| `G14-0374` | `G14-0375` | 0.965517 | `near_duplicate_candidate` |
| `G14-0384` | `G14-0385` | 0.933333 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G14-0201`, `G14-0202`, `G14-0206`, `G14-0212`, `G14-0216`
- `SUGGESTED-0002`: `G14-0203`, `G14-0205`
- `SUGGESTED-0003`: `G14-0204`, `G14-0213`
- `SUGGESTED-0004`: `G14-0207`, `G14-0209`
- `SUGGESTED-0005`: `G14-0210`, `G14-0214`
- `SUGGESTED-0006`: `G14-0215`, `G14-0218`
- `SUGGESTED-0007`: `G14-0313`, `G14-0321`
- `SUGGESTED-0008`: `G14-0335`, `G14-0337`, `G14-0343`
- `SUGGESTED-0009`: `G14-0356`, `G14-0357`, `G14-0364`, `G14-0366`, `G14-0367`
- `SUGGESTED-0010`: `G14-0359`, `G14-0363`
- `SUGGESTED-0011`: `G14-0360`, `G14-0365`
- `SUGGESTED-0012`: `G14-0373`, `G14-0374`, `G14-0375`
- `SUGGESTED-0013`: `G14-0384`, `G14-0385`
