# Dataset QA report

- File: `data/synthetic/G11-doxxing.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **46**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.502000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `doxxing` | 500 |

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
| `discord` | 205 |
| `minecraft` | 295 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 205 |
| `minecraft_public` | 295 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 25 |
| `DOXXING` | 400 |
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
| `NONE` | 500 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 500 |

### Strike

| Value | Count |
|---|---:|
| `false` | 100 |
| `true` | 400 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `null` | 500 |

### Reason codes

| Value | Count |
|---|---:|
| `apparent_doxxing` | 129 |
| `confirmed_doxxing` | 275 |
| `discord_gameplay_explicit` | 9 |
| `explicit_real_world_cue` | 215 |
| `insufficient_context` | 73 |
| `minecraft_gameplay_explicit` | 18 |
| `real_world_address_cue` | 20 |
| `real_world_location` | 165 |

### Message count

| Value | Count |
|---|---:|
| `1` | 249 |
| `2` | 201 |
| `4` | 25 |
| `5` | 25 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G11-0003` | `G11-0154` | 0.926829 | `near_duplicate_candidate` |
| `G11-0003` | `G11-0286` | 0.922156 | `near_duplicate_candidate` |
| `G11-0005` | `G11-0062` | 0.991667 | `near_duplicate_candidate` |
| `G11-0010` | `G11-0087` | 0.968750 | `near_duplicate_candidate` |
| `G11-0014` | `G11-0221` | 0.966667 | `near_duplicate_candidate` |
| `G11-0021` | `G11-0111` | 0.929825 | `near_duplicate_candidate` |
| `G11-0021` | `G11-0320` | 0.929825 | `near_duplicate_candidate` |
| `G11-0023` | `G11-0137` | 0.939394 | `near_duplicate_candidate` |
| `G11-0032` | `G11-0242` | 0.950000 | `near_duplicate_candidate` |
| `G11-0036` | `G11-0143` | 0.952381 | `near_duplicate_candidate` |
| `G11-0036` | `G11-0174` | 0.952381 | `near_duplicate_candidate` |
| `G11-0045` | `G11-0353` | 0.952381 | `near_duplicate_candidate` |
| `G11-0050` | `G11-0257` | 0.962264 | `near_duplicate_candidate` |
| `G11-0050` | `G11-0406` | 0.962264 | `near_duplicate_candidate` |
| `G11-0058` | `G11-0155` | 0.952381 | `near_duplicate_candidate` |
| `G11-0069` | `G11-0372` | 0.950000 | `near_duplicate_candidate` |
| `G11-0084` | `G11-0342` | 0.976190 | `near_duplicate_candidate` |
| `G11-0089` | `G11-0120` | 0.970760 | `near_duplicate_candidate` |
| `G11-0089` | `G11-0332` | 0.941176 | `near_duplicate_candidate` |
| `G11-0103` | `G11-0234` | 0.948905 | `near_duplicate_candidate` |
| `G11-0120` | `G11-0332` | 0.923977 | `near_duplicate_candidate` |
| `G11-0122` | `G11-0181` | 0.930693 | `near_duplicate_candidate` |
| `G11-0122` | `G11-0204` | 0.930693 | `near_duplicate_candidate` |
| `G11-0129` | `G11-0241` | 0.936937 | `near_duplicate_candidate` |
| `G11-0140` | `G11-0196` | 0.933333 | `near_duplicate_candidate` |
| `G11-0143` | `G11-0174` | 0.976190 | `near_duplicate_candidate` |
| `G11-0152` | `G11-0339` | 0.934010 | `near_duplicate_candidate` |
| `G11-0161` | `G11-0437` | 0.965909 | `near_duplicate_candidate` |
| `G11-0170` | `G11-0211` | 0.931034 | `near_duplicate_candidate` |
| `G11-0170` | `G11-0328` | 0.920455 | `near_duplicate_candidate` |
| `G11-0171` | `G11-0376` | 0.929936 | `near_duplicate_candidate` |
| `G11-0178` | `G11-0441` | 0.967742 | `near_duplicate_candidate` |
| `G11-0181` | `G11-0204` | 0.925926 | `near_duplicate_candidate` |
| `G11-0211` | `G11-0419` | 0.942529 | `near_duplicate_candidate` |
| `G11-0218` | `G11-0241` | 0.946429 | `near_duplicate_candidate` |
| `G11-0243` | `G11-0275` | 0.942085 | `near_duplicate_candidate` |
| `G11-0251` | `G11-0322` | 0.922078 | `near_duplicate_candidate` |
| `G11-0256` | `G11-0431` | 0.960000 | `near_duplicate_candidate` |
| `G11-0257` | `G11-0406` | 0.981132 | `near_duplicate_candidate` |
| `G11-0261` | `G11-0288` | 0.937500 | `near_duplicate_candidate` |
| `G11-0262` | `G11-0324` | 0.925170 | `near_duplicate_candidate` |
| `G11-0285` | `G11-0404` | 0.955975 | `near_duplicate_candidate` |
| `G11-0292` | `G11-0434` | 0.943396 | `near_duplicate_candidate` |
| `G11-0297` | `G11-0317` | 0.980132 | `near_duplicate_candidate` |
| `G11-0350` | `G11-0428` | 0.943396 | `near_duplicate_candidate` |
| `G11-0362` | `G11-0432` | 0.928000 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G11-0003`, `G11-0154`, `G11-0286`
- `SUGGESTED-0002`: `G11-0005`, `G11-0062`
- `SUGGESTED-0003`: `G11-0010`, `G11-0087`
- `SUGGESTED-0004`: `G11-0014`, `G11-0221`
- `SUGGESTED-0005`: `G11-0021`, `G11-0111`, `G11-0320`
- `SUGGESTED-0006`: `G11-0023`, `G11-0137`
- `SUGGESTED-0007`: `G11-0032`, `G11-0242`
- `SUGGESTED-0008`: `G11-0036`, `G11-0143`, `G11-0174`
- `SUGGESTED-0009`: `G11-0045`, `G11-0353`
- `SUGGESTED-0010`: `G11-0050`, `G11-0257`, `G11-0406`
- `SUGGESTED-0011`: `G11-0058`, `G11-0155`
- `SUGGESTED-0012`: `G11-0069`, `G11-0372`
- `SUGGESTED-0013`: `G11-0084`, `G11-0342`
- `SUGGESTED-0014`: `G11-0089`, `G11-0120`, `G11-0332`
- `SUGGESTED-0015`: `G11-0103`, `G11-0234`
- `SUGGESTED-0016`: `G11-0122`, `G11-0181`, `G11-0204`
- `SUGGESTED-0017`: `G11-0129`, `G11-0218`, `G11-0241`
- `SUGGESTED-0018`: `G11-0140`, `G11-0196`
- `SUGGESTED-0019`: `G11-0152`, `G11-0339`
- `SUGGESTED-0020`: `G11-0161`, `G11-0437`
- `SUGGESTED-0021`: `G11-0170`, `G11-0211`, `G11-0328`, `G11-0419`
- `SUGGESTED-0022`: `G11-0171`, `G11-0376`
- `SUGGESTED-0023`: `G11-0178`, `G11-0441`
- `SUGGESTED-0024`: `G11-0243`, `G11-0275`
- `SUGGESTED-0025`: `G11-0251`, `G11-0322`
- `SUGGESTED-0026`: `G11-0256`, `G11-0431`
- `SUGGESTED-0027`: `G11-0261`, `G11-0288`
- `SUGGESTED-0028`: `G11-0262`, `G11-0324`
- `SUGGESTED-0029`: `G11-0285`, `G11-0404`
- `SUGGESTED-0030`: `G11-0292`, `G11-0434`
- `SUGGESTED-0031`: `G11-0297`, `G11-0317`
- `SUGGESTED-0032`: `G11-0350`, `G11-0428`
- `SUGGESTED-0033`: `G11-0362`, `G11-0432`
