# Dataset QA report

- File: `data/synthetic/G10-blackmail-extortion.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **397**
- Exact duplicate groups: **0**
- Near candidates: **41**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.550000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `blackmail` | 500 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 63 |
| `easy` | 75 |
| `hard` | 236 |
| `medium` | 126 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 158 |
| `minecraft` | 342 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 109 |
| `discord_general` | 49 |
| `minecraft_private` | 196 |
| `minecraft_public` | 146 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 25 |
| `BLACKMAIL` | 397 |
| `SAFE` | 78 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 78 |
| `BLOCK` | 397 |
| `REVIEW` | 25 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 78 |
| `NORMAL` | 25 |
| `URGENT` | 397 |

### containment

| Value | Count |
|---|---:|
| `MUTE` | 397 |
| `NONE` | 103 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 472 |
| `TARGET_SAFETY_CHECK` | 28 |

### Strike

| Value | Count |
|---|---:|
| `false` | 103 |
| `true` | 397 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `mute_without_duration` | 397 |
| `null` | 500 |

### Reason codes

| Value | Count |
|---|---:|
| `blackmail` | 397 |
| `discord_gameplay_explicit` | 1 |
| `explicit_real_world_cue` | 28 |
| `gameplay_death_context` | 15 |
| `insufficient_context` | 25 |
| `minecraft_gameplay_explicit` | 443 |
| `mutual_banter_evidence` | 31 |
| `obfuscated_evasion` | 34 |
| `private_context_relevant` | 28 |
| `split_message_context` | 245 |

### Message count

| Value | Count |
|---|---:|
| `1` | 225 |
| `2` | 119 |
| `3` | 151 |
| `4` | 5 |

### Diagnostic codes

| Value | Count |
|---|---:|
| `mute_duration_unspecified` | 397 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G10-0003` | `G10-0032` | 0.973684 | `near_duplicate_candidate` |
| `G10-0006` | `G10-0013` | 0.942308 | `near_duplicate_candidate` |
| `G10-0006` | `G10-0017` | 0.990000 | `near_duplicate_candidate` |
| `G10-0006` | `G10-0034` | 0.980000 | `near_duplicate_candidate` |
| `G10-0010` | `G10-0021` | 0.978947 | `near_duplicate_candidate` |
| `G10-0013` | `G10-0017` | 0.942308 | `near_duplicate_candidate` |
| `G10-0013` | `G10-0034` | 0.942308 | `near_duplicate_candidate` |
| `G10-0017` | `G10-0034` | 0.980000 | `near_duplicate_candidate` |
| `G10-0023` | `G10-0026` | 0.925000 | `near_duplicate_candidate` |
| `G10-0044` | `G10-0072` | 0.940594 | `near_duplicate_candidate` |
| `G10-0059` | `G10-0068` | 0.927203 | `near_duplicate_candidate` |
| `G10-0076` | `G10-0082` | 0.934579 | `near_duplicate_candidate` |
| `G10-0076` | `G10-0102` | 0.945946 | `near_duplicate_candidate` |
| `G10-0080` | `G10-0090` | 0.938389 | `near_duplicate_candidate` |
| `G10-0102` | `G10-0105` | 0.932203 | `near_duplicate_candidate` |
| `G10-0109` | `G10-0112` | 0.930041 | `near_duplicate_candidate` |
| `G10-0112` | `G10-0118` | 0.937759 | `near_duplicate_candidate` |
| `G10-0155` | `G10-0156` | 0.924731 | `near_duplicate_candidate` |
| `G10-0176` | `G10-0191` | 0.981481 | `near_duplicate_candidate` |
| `G10-0195` | `G10-0206` | 0.945946 | `near_duplicate_candidate` |
| `G10-0195` | `G10-0215` | 0.986111 | `near_duplicate_candidate` |
| `G10-0200` | `G10-0204` | 0.926554 | `near_duplicate_candidate` |
| `G10-0206` | `G10-0215` | 0.945946 | `near_duplicate_candidate` |
| `G10-0210` | `G10-0213` | 0.924528 | `near_duplicate_candidate` |
| `G10-0222` | `G10-0229` | 0.977778 | `near_duplicate_candidate` |
| `G10-0226` | `G10-0236` | 0.938931 | `near_duplicate_candidate` |
| `G10-0226` | `G10-0242` | 0.951613 | `near_duplicate_candidate` |
| `G10-0233` | `G10-0237` | 0.929134 | `near_duplicate_candidate` |
| `G10-0233` | `G10-0239` | 0.923664 | `near_duplicate_candidate` |
| `G10-0235` | `G10-0237` | 0.920635 | `near_duplicate_candidate` |
| `G10-0257` | `G10-0269` | 0.938144 | `near_duplicate_candidate` |
| `G10-0278` | `G10-0289` | 0.936842 | `near_duplicate_candidate` |
| `G10-0310` | `G10-0316` | 0.978022 | `near_duplicate_candidate` |
| `G10-0347` | `G10-0357` | 0.933333 | `near_duplicate_candidate` |
| `G10-0372` | `G10-0389` | 0.943396 | `near_duplicate_candidate` |
| `G10-0373` | `G10-0383` | 0.927083 | `near_duplicate_candidate` |
| `G10-0373` | `G10-0386` | 0.989583 | `near_duplicate_candidate` |
| `G10-0382` | `G10-0393` | 0.970588 | `near_duplicate_candidate` |
| `G10-0383` | `G10-0386` | 0.927083 | `near_duplicate_candidate` |
| `G10-0384` | `G10-0387` | 0.987952 | `near_duplicate_candidate` |
| `G10-0442` | `G10-0497` | 0.930233 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G10-0003`, `G10-0032`
- `SUGGESTED-0002`: `G10-0006`, `G10-0013`, `G10-0017`, `G10-0034`
- `SUGGESTED-0003`: `G10-0010`, `G10-0021`
- `SUGGESTED-0004`: `G10-0023`, `G10-0026`
- `SUGGESTED-0005`: `G10-0044`, `G10-0072`
- `SUGGESTED-0006`: `G10-0059`, `G10-0068`
- `SUGGESTED-0007`: `G10-0076`, `G10-0082`, `G10-0102`, `G10-0105`
- `SUGGESTED-0008`: `G10-0080`, `G10-0090`
- `SUGGESTED-0009`: `G10-0109`, `G10-0112`, `G10-0118`
- `SUGGESTED-0010`: `G10-0155`, `G10-0156`
- `SUGGESTED-0011`: `G10-0176`, `G10-0191`
- `SUGGESTED-0012`: `G10-0195`, `G10-0206`, `G10-0215`
- `SUGGESTED-0013`: `G10-0200`, `G10-0204`
- `SUGGESTED-0014`: `G10-0210`, `G10-0213`
- `SUGGESTED-0015`: `G10-0222`, `G10-0229`
- `SUGGESTED-0016`: `G10-0226`, `G10-0236`, `G10-0242`
- `SUGGESTED-0017`: `G10-0233`, `G10-0235`, `G10-0237`, `G10-0239`
- `SUGGESTED-0018`: `G10-0257`, `G10-0269`
- `SUGGESTED-0019`: `G10-0278`, `G10-0289`
- `SUGGESTED-0020`: `G10-0310`, `G10-0316`
- `SUGGESTED-0021`: `G10-0347`, `G10-0357`
- `SUGGESTED-0022`: `G10-0372`, `G10-0389`
- `SUGGESTED-0023`: `G10-0373`, `G10-0383`, `G10-0386`
- `SUGGESTED-0024`: `G10-0382`, `G10-0393`
- `SUGGESTED-0025`: `G10-0384`, `G10-0387`
- `SUGGESTED-0026`: `G10-0442`, `G10-0497`
