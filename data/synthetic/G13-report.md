# Dataset QA report

- File: `data/synthetic/G13-staff-abuse.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **45**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.502000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `staff_abuse` | 400 |
| `staff_feedback` | 100 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 82 |
| `easy` | 72 |
| `hard` | 220 |
| `medium` | 126 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 247 |
| `minecraft` | 253 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 124 |
| `discord_general` | 123 |
| `minecraft_private` | 125 |
| `minecraft_public` | 128 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 24 |
| `SAFE` | 101 |
| `STAFF_TARGETED_ABUSE` | 375 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 101 |
| `BLOCK` | 375 |
| `REVIEW` | 24 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 101 |
| `NORMAL` | 101 |
| `URGENT` | 298 |

### containment

| Value | Count |
|---|---:|
| `MUTE` | 315 |
| `NONE` | 185 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 420 |
| `TARGET_SAFETY_CHECK` | 80 |

### Strike

| Value | Count |
|---|---:|
| `false` | 125 |
| `true` | 375 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `concrete` | 315 |
| `mute_with_duration` | 315 |
| `null` | 185 |

### Reason codes

| Value | Count |
|---|---:|
| `coordinated_dogpile` | 50 |
| `discord_gameplay_explicit` | 11 |
| `explicit_real_world_cue` | 79 |
| `insufficient_context` | 24 |
| `low_severity_insult` | 62 |
| `minecraft_gameplay_explicit` | 80 |
| `multi_sender_dogpile` | 5 |
| `obfuscated_evasion` | 31 |
| `quoted_or_condemned` | 10 |
| `real_world_location` | 19 |
| `real_world_proximity` | 25 |
| `repeated_targeting` | 96 |
| `self_harm_instruction` | 80 |
| `staff_targeted_abuse` | 385 |
| `target_requested_stop` | 34 |
| `targeted_violence` | 79 |

### Message count

| Value | Count |
|---|---:|
| `1` | 249 |
| `2` | 89 |
| `3` | 160 |
| `4` | 2 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G13-0011` | `G13-0012` | 0.941860 | `near_duplicate_candidate` |
| `G13-0017` | `G13-0021` | 0.926829 | `near_duplicate_candidate` |
| `G13-0053` | `G13-0333` | 0.937500 | `near_duplicate_candidate` |
| `G13-0056` | `G13-0080` | 0.944444 | `near_duplicate_candidate` |
| `G13-0058` | `G13-0070` | 0.939394 | `near_duplicate_candidate` |
| `G13-0058` | `G13-0090` | 0.938462 | `near_duplicate_candidate` |
| `G13-0060` | `G13-0072` | 0.931298 | `near_duplicate_candidate` |
| `G13-0061` | `G13-0082` | 0.929134 | `near_duplicate_candidate` |
| `G13-0062` | `G13-0069` | 0.922078 | `near_duplicate_candidate` |
| `G13-0064` | `G13-0079` | 0.945205 | `near_duplicate_candidate` |
| `G13-0067` | `G13-0068` | 0.944882 | `near_duplicate_candidate` |
| `G13-0067` | `G13-0087` | 0.936508 | `near_duplicate_candidate` |
| `G13-0068` | `G13-0087` | 0.960000 | `near_duplicate_candidate` |
| `G13-0070` | `G13-0090` | 0.938462 | `near_duplicate_candidate` |
| `G13-0073` | `G13-0078` | 0.928571 | `near_duplicate_candidate` |
| `G13-0077` | `G13-0078` | 0.928571 | `near_duplicate_candidate` |
| `G13-0092` | `G13-0096` | 0.935484 | `near_duplicate_candidate` |
| `G13-0110` | `G13-0113` | 0.939394 | `near_duplicate_candidate` |
| `G13-0114` | `G13-0117` | 0.920635 | `near_duplicate_candidate` |
| `G13-0122` | `G13-0145` | 0.929293 | `near_duplicate_candidate` |
| `G13-0176` | `G13-0184` | 0.935252 | `near_duplicate_candidate` |
| `G13-0196` | `G13-0215` | 0.971098 | `near_duplicate_candidate` |
| `G13-0196` | `G13-0223` | 0.926554 | `near_duplicate_candidate` |
| `G13-0196` | `G13-0228` | 0.965517 | `near_duplicate_candidate` |
| `G13-0196` | `G13-0240` | 0.960000 | `near_duplicate_candidate` |
| `G13-0200` | `G13-0219` | 0.923077 | `near_duplicate_candidate` |
| `G13-0200` | `G13-0239` | 0.925000 | `near_duplicate_candidate` |
| `G13-0201` | `G13-0221` | 0.948718 | `near_duplicate_candidate` |
| `G13-0205` | `G13-0229` | 0.927273 | `near_duplicate_candidate` |
| `G13-0206` | `G13-0237` | 0.925234 | `near_duplicate_candidate` |
| `G13-0207` | `G13-0232` | 0.946429 | `near_duplicate_candidate` |
| `G13-0209` | `G13-0237` | 0.952830 | `near_duplicate_candidate` |
| `G13-0213` | `G13-0238` | 0.977273 | `near_duplicate_candidate` |
| `G13-0214` | `G13-0237` | 0.943925 | `near_duplicate_candidate` |
| `G13-0215` | `G13-0223` | 0.920455 | `near_duplicate_candidate` |
| `G13-0215` | `G13-0228` | 0.971098 | `near_duplicate_candidate` |
| `G13-0215` | `G13-0240` | 0.965517 | `near_duplicate_candidate` |
| `G13-0217` | `G13-0226` | 0.947368 | `near_duplicate_candidate` |
| `G13-0223` | `G13-0224` | 0.944444 | `near_duplicate_candidate` |
| `G13-0225` | `G13-0233` | 0.937500 | `near_duplicate_candidate` |
| `G13-0227` | `G13-0240` | 0.932584 | `near_duplicate_candidate` |
| `G13-0228` | `G13-0240` | 0.948571 | `near_duplicate_candidate` |
| `G13-0377` | `G13-0385` | 0.953020 | `near_duplicate_candidate` |
| `G13-0378` | `G13-0383` | 0.947368 | `near_duplicate_candidate` |
| `G13-0380` | `G13-0384` | 0.922374 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G13-0011`, `G13-0012`
- `SUGGESTED-0002`: `G13-0017`, `G13-0021`
- `SUGGESTED-0003`: `G13-0053`, `G13-0333`
- `SUGGESTED-0004`: `G13-0056`, `G13-0080`
- `SUGGESTED-0005`: `G13-0058`, `G13-0070`, `G13-0090`
- `SUGGESTED-0006`: `G13-0060`, `G13-0072`
- `SUGGESTED-0007`: `G13-0061`, `G13-0082`
- `SUGGESTED-0008`: `G13-0062`, `G13-0069`
- `SUGGESTED-0009`: `G13-0064`, `G13-0079`
- `SUGGESTED-0010`: `G13-0067`, `G13-0068`, `G13-0087`
- `SUGGESTED-0011`: `G13-0073`, `G13-0077`, `G13-0078`
- `SUGGESTED-0012`: `G13-0092`, `G13-0096`
- `SUGGESTED-0013`: `G13-0110`, `G13-0113`
- `SUGGESTED-0014`: `G13-0114`, `G13-0117`
- `SUGGESTED-0015`: `G13-0122`, `G13-0145`
- `SUGGESTED-0016`: `G13-0176`, `G13-0184`
- `SUGGESTED-0017`: `G13-0196`, `G13-0215`, `G13-0223`, `G13-0224`, `G13-0227`, `G13-0228`, `G13-0240`
- `SUGGESTED-0018`: `G13-0200`, `G13-0219`, `G13-0239`
- `SUGGESTED-0019`: `G13-0201`, `G13-0221`
- `SUGGESTED-0020`: `G13-0205`, `G13-0229`
- `SUGGESTED-0021`: `G13-0206`, `G13-0209`, `G13-0214`, `G13-0237`
- `SUGGESTED-0022`: `G13-0207`, `G13-0232`
- `SUGGESTED-0023`: `G13-0213`, `G13-0238`
- `SUGGESTED-0024`: `G13-0217`, `G13-0226`
- `SUGGESTED-0025`: `G13-0225`, `G13-0233`
- `SUGGESTED-0026`: `G13-0377`, `G13-0385`
- `SUGGESTED-0027`: `G13-0378`, `G13-0383`
- `SUGGESTED-0028`: `G13-0380`, `G13-0384`
