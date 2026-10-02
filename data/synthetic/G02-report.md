# Dataset QA report

- File: `data/synthetic/G02-real-world-threats.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **61**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.180000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `context_linkage` | 20 |
| `doxxing` | 10 |
| `gameplay_violence` | 100 |
| `real_world_threat` | 320 |
| `stalking_intimidation` | 50 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 104 |
| `hard` | 243 |
| `medium` | 153 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 227 |
| `minecraft` | 273 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 114 |
| `discord_general` | 113 |
| `minecraft_private` | 110 |
| `minecraft_public` | 163 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 105 |
| `DOXXING` | 10 |
| `GAMEPLAY_VIOLENCE` | 100 |
| `REAL_WORLD_THREAT` | 265 |
| `SAFE` | 20 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 120 |
| `BLOCK` | 275 |
| `REVIEW` | 105 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 120 |
| `NORMAL` | 245 |
| `URGENT` | 135 |

### containment

| Value | Count |
|---|---:|
| `MUTE` | 44 |
| `NONE` | 456 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 495 |
| `TARGET_SAFETY_CHECK` | 5 |

### Strike

| Value | Count |
|---|---:|
| `false` | 410 |
| `true` | 90 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `concrete` | 44 |
| `mute_with_duration` | 44 |
| `null` | 456 |

### Reason codes

| Value | Count |
|---|---:|
| `apparent_doxxing` | 6 |
| `confirmed_doxxing` | 4 |
| `discord_gameplay_explicit` | 21 |
| `discord_general_no_game_context` | 20 |
| `explicit_real_world_cue` | 110 |
| `house_ambiguous_gameplay` | 42 |
| `insufficient_context` | 110 |
| `long_gap_breaks_linkage` | 10 |
| `minecraft_gameplay_explicit` | 84 |
| `prior_confirmed_incident` | 5 |
| `real_world_address_cue` | 31 |
| `real_world_delivery_cue` | 25 |
| `real_world_location` | 204 |
| `real_world_proximity` | 49 |
| `real_world_time` | 169 |
| `split_message_context` | 70 |
| `staff_confirmed` | 9 |
| `targeted_violence` | 265 |

### Message count

| Value | Count |
|---|---:|
| `1` | 410 |
| `2` | 30 |
| `3` | 60 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G02-0071` | `G02-0115` | 0.927152 | `near_duplicate_candidate` |
| `G02-0086` | `G02-0130` | 0.924138 | `near_duplicate_candidate` |
| `G02-0095` | `G02-0139` | 0.925926 | `near_duplicate_candidate` |
| `G02-0142` | `G02-0157` | 0.966292 | `near_duplicate_candidate` |
| `G02-0144` | `G02-0159` | 0.961039 | `near_duplicate_candidate` |
| `G02-0146` | `G02-0161` | 0.961039 | `near_duplicate_candidate` |
| `G02-0148` | `G02-0163` | 0.955224 | `near_duplicate_candidate` |
| `G02-0150` | `G02-0165` | 0.960000 | `near_duplicate_candidate` |
| `G02-0152` | `G02-0167` | 0.957746 | `near_duplicate_candidate` |
| `G02-0154` | `G02-0169` | 0.963855 | `near_duplicate_candidate` |
| `G02-0231` | `G02-0251` | 0.967213 | `near_duplicate_candidate` |
| `G02-0231` | `G02-0271` | 0.921875 | `near_duplicate_candidate` |
| `G02-0231` | `G02-0311` | 0.959350 | `near_duplicate_candidate` |
| `G02-0232` | `G02-0252` | 0.962264 | `near_duplicate_candidate` |
| `G02-0232` | `G02-0312` | 0.953271 | `near_duplicate_candidate` |
| `G02-0233` | `G02-0253` | 0.966102 | `near_duplicate_candidate` |
| `G02-0233` | `G02-0313` | 0.957983 | `near_duplicate_candidate` |
| `G02-0234` | `G02-0254` | 0.962963 | `near_duplicate_candidate` |
| `G02-0234` | `G02-0314` | 0.954128 | `near_duplicate_candidate` |
| `G02-0235` | `G02-0255` | 0.957447 | `near_duplicate_candidate` |
| `G02-0235` | `G02-0315` | 0.947368 | `near_duplicate_candidate` |
| `G02-0236` | `G02-0256` | 0.961538 | `near_duplicate_candidate` |
| `G02-0236` | `G02-0316` | 0.952381 | `near_duplicate_candidate` |
| `G02-0237` | `G02-0257` | 0.962963 | `near_duplicate_candidate` |
| `G02-0237` | `G02-0317` | 0.954128 | `near_duplicate_candidate` |
| `G02-0238` | `G02-0258` | 0.964286 | `near_duplicate_candidate` |
| `G02-0238` | `G02-0318` | 0.955752 | `near_duplicate_candidate` |
| `G02-0239` | `G02-0259` | 0.962963 | `near_duplicate_candidate` |
| `G02-0239` | `G02-0319` | 0.954128 | `near_duplicate_candidate` |
| `G02-0240` | `G02-0260` | 0.966102 | `near_duplicate_candidate` |
| `G02-0240` | `G02-0320` | 0.957983 | `near_duplicate_candidate` |
| `G02-0241` | `G02-0261` | 0.958333 | `near_duplicate_candidate` |
| `G02-0242` | `G02-0262` | 0.962264 | `near_duplicate_candidate` |
| `G02-0243` | `G02-0263` | 0.941176 | `near_duplicate_candidate` |
| `G02-0244` | `G02-0264` | 0.954545 | `near_duplicate_candidate` |
| `G02-0245` | `G02-0265` | 0.955556 | `near_duplicate_candidate` |
| `G02-0246` | `G02-0266` | 0.965517 | `near_duplicate_candidate` |
| `G02-0247` | `G02-0267` | 0.957447 | `near_duplicate_candidate` |
| `G02-0248` | `G02-0268` | 0.962264 | `near_duplicate_candidate` |
| `G02-0249` | `G02-0269` | 0.961538 | `near_duplicate_candidate` |
| `G02-0250` | `G02-0270` | 0.964286 | `near_duplicate_candidate` |
| `G02-0251` | `G02-0311` | 0.929134 | `near_duplicate_candidate` |
| `G02-0253` | `G02-0313` | 0.926829 | `near_duplicate_candidate` |
| `G02-0254` | `G02-0314` | 0.920354 | `near_duplicate_candidate` |
| `G02-0257` | `G02-0317` | 0.920354 | `near_duplicate_candidate` |
| `G02-0258` | `G02-0318` | 0.923077 | `near_duplicate_candidate` |
| `G02-0259` | `G02-0319` | 0.920354 | `near_duplicate_candidate` |
| `G02-0260` | `G02-0320` | 0.926829 | `near_duplicate_candidate` |
| `G02-0271` | `G02-0291` | 0.920863 | `near_duplicate_candidate` |
| `G02-0271` | `G02-0311` | 0.932331 | `near_duplicate_candidate` |
| `G02-0272` | `G02-0312` | 0.923077 | `near_duplicate_candidate` |
| `G02-0273` | `G02-0313` | 0.930233 | `near_duplicate_candidate` |
| `G02-0274` | `G02-0314` | 0.924370 | `near_duplicate_candidate` |
| `G02-0276` | `G02-0316` | 0.921739 | `near_duplicate_candidate` |
| `G02-0277` | `G02-0317` | 0.924370 | `near_duplicate_candidate` |
| `G02-0278` | `G02-0318` | 0.926829 | `near_duplicate_candidate` |
| `G02-0279` | `G02-0319` | 0.924370 | `near_duplicate_candidate` |
| `G02-0280` | `G02-0320` | 0.930233 | `near_duplicate_candidate` |
| `G02-0291` | `G02-0311` | 0.925373 | `near_duplicate_candidate` |
| `G02-0293` | `G02-0313` | 0.923077 | `near_duplicate_candidate` |
| `G02-0300` | `G02-0320` | 0.923077 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G02-0071`, `G02-0115`
- `SUGGESTED-0002`: `G02-0086`, `G02-0130`
- `SUGGESTED-0003`: `G02-0095`, `G02-0139`
- `SUGGESTED-0004`: `G02-0142`, `G02-0157`
- `SUGGESTED-0005`: `G02-0144`, `G02-0159`
- `SUGGESTED-0006`: `G02-0146`, `G02-0161`
- `SUGGESTED-0007`: `G02-0148`, `G02-0163`
- `SUGGESTED-0008`: `G02-0150`, `G02-0165`
- `SUGGESTED-0009`: `G02-0152`, `G02-0167`
- `SUGGESTED-0010`: `G02-0154`, `G02-0169`
- `SUGGESTED-0011`: `G02-0231`, `G02-0251`, `G02-0271`, `G02-0291`, `G02-0311`
- `SUGGESTED-0012`: `G02-0232`, `G02-0252`, `G02-0272`, `G02-0312`
- `SUGGESTED-0013`: `G02-0233`, `G02-0253`, `G02-0273`, `G02-0293`, `G02-0313`
- `SUGGESTED-0014`: `G02-0234`, `G02-0254`, `G02-0274`, `G02-0314`
- `SUGGESTED-0015`: `G02-0235`, `G02-0255`, `G02-0315`
- `SUGGESTED-0016`: `G02-0236`, `G02-0256`, `G02-0276`, `G02-0316`
- `SUGGESTED-0017`: `G02-0237`, `G02-0257`, `G02-0277`, `G02-0317`
- `SUGGESTED-0018`: `G02-0238`, `G02-0258`, `G02-0278`, `G02-0318`
- `SUGGESTED-0019`: `G02-0239`, `G02-0259`, `G02-0279`, `G02-0319`
- `SUGGESTED-0020`: `G02-0240`, `G02-0260`, `G02-0280`, `G02-0300`, `G02-0320`
- `SUGGESTED-0021`: `G02-0241`, `G02-0261`
- `SUGGESTED-0022`: `G02-0242`, `G02-0262`
- `SUGGESTED-0023`: `G02-0243`, `G02-0263`
- `SUGGESTED-0024`: `G02-0244`, `G02-0264`
- `SUGGESTED-0025`: `G02-0245`, `G02-0265`
- `SUGGESTED-0026`: `G02-0246`, `G02-0266`
- `SUGGESTED-0027`: `G02-0247`, `G02-0267`
- `SUGGESTED-0028`: `G02-0248`, `G02-0268`
- `SUGGESTED-0029`: `G02-0249`, `G02-0269`
- `SUGGESTED-0030`: `G02-0250`, `G02-0270`

## W03 coverage notes

- Exact requested bucket counts: 140 clear targeted real-world threats; 90 ambiguous/no-strike threat cases; 90 Minecraft/gameplay hard negatives; 80 split-message/contextual sequences; 50 stalking/location/intimidation cases; 50 bomb-delivery/house/address/doxxing-adjacent contrasts.
- Action mix: 275 BLOCK (55%), 105 REVIEW (21%), 120 ALLOW (24%).
- Multi-message examples: 90/500 (18.0%).
- Explicit family IDs: 112.
- Canonical validator on the exact prior corpus head reported `records=500 errors=0 warnings=0 exact_duplicate_groups=0 near_candidates=61`; this report is rendered from the same merged QA algorithm and corpus.

## Warning disposition

- Dataset QA warnings: **0**. No unresolved `MUTE + null`, exempt-channel, empty-reason, duplicate-reason, or near-contradiction warnings are present.
- The 61 near/minimal-pair candidates are advisory similarity candidates, not warnings. They are retained intentionally for contrast/family review; W11 owns cross-worker deduplication and leakage-safe splitting.

## Manual quality review

- Cross-bucket sampling corrected benign clarification targets that had been labeled too narrowly, mechanical doubled timing phrases, one severe stalking line whose harm cue was too weak, and five target-safety fixtures so recent confirmed history triggers urgent review/support without manufacturing a new strike.

## Golden-set leakage review

- The owner-policy golden set was used for policy boundaries only. No golden message sequence was copied exactly or reduced to a trivial one-word edit; related synthetic examples use explicit `g02.*` families so W11 can keep them away from frozen acceptance fixtures.

## Deliberately omitted unresolved Policy-v1 edges

- Discord bot DMs; graphic first-person self-harm disclosure; consensual explicit adult PM content; uncertain-age grooming; broader dangerous-instruction domains; fake-doxxing strike cleanup; a complete threat severity-to-duration matrix; blackmail duration; and accidental lexical slur matching were not decided here.

## Safety/privacy notes

- Address/doxxing fixtures use placeholders such as `<address>`. No production chat, real personal data, secrets, model/runtime code, deployment configuration, or live systems were touched.
- Bomb-delivery examples are threat statements only and contain no construction recipe or operational explosive instructions.
