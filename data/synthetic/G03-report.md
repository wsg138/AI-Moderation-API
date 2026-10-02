# Dataset QA report

- File: `data/synthetic/G03-harassment.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **7**
- Minimal-pair candidates: **7**
- Multi-message proportion: **0.634000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `consent` | 80 |
| `dogpile` | 70 |
| `harassment` | 150 |
| `relationship_controls` | 50 |
| `staff_abuse` | 70 |
| `toxicity` | 80 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 40 |
| `easy` | 86 |
| `hard` | 269 |
| `medium` | 105 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 185 |
| `minecraft` | 315 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 150 |
| `discord_general` | 35 |
| `minecraft_private` | 109 |
| `minecraft_public` | 206 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 10 |
| `LOW_LEVEL_HARASSMENT` | 240 |
| `SAFE` | 75 |
| `SEVERE_HARASSMENT` | 130 |
| `STAFF_TARGETED_ABUSE` | 45 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 200 |
| `BLOCK` | 225 |
| `REVIEW` | 75 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 255 |
| `NORMAL` | 245 |

### containment

| Value | Count |
|---|---:|
| `MUTE` | 90 |
| `NONE` | 410 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 500 |

### Strike

| Value | Count |
|---|---:|
| `false` | 420 |
| `true` | 80 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `null` | 410 |
| `concrete` | 90 |
| `mute_with_duration` | 90 |

### Reason codes

| Value | Count |
|---|---:|
| `consent_uncomfortable` | 30 |
| `coordinated_dogpile` | 35 |
| `discord_gameplay_explicit` | 42 |
| `discord_general_no_game_context` | 10 |
| `ignored_relationship` | 25 |
| `insufficient_context` | 10 |
| `low_severity_insult` | 140 |
| `minecraft_gameplay_explicit` | 78 |
| `multi_sender_dogpile` | 70 |
| `mutual_banter_evidence` | 60 |
| `private_context_relevant` | 33 |
| `repeated_targeting` | 135 |
| `reply_context` | 37 |
| `staff_targeted_abuse` | 45 |
| `target_requested_stop` | 105 |
| `target_strict_filter` | 25 |

### Message count

| Value | Count |
|---|---:|
| `1` | 183 |
| `2` | 37 |
| `3` | 85 |
| `4` | 150 |
| `5` | 45 |

### Diagnostic codes

| Value | Count |
|---|---:|
| `(none)` | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G03-0425` | `G03-0462` | 0.936170 | `minimal_pair_candidate` |
| `G03-0426` | `G03-0439` | 0.941176 | `minimal_pair_candidate` |
| `G03-0429` | `G03-0466` | 0.945455 | `minimal_pair_candidate` |
| `G03-0430` | `G03-0443` | 0.945455 | `minimal_pair_candidate` |
| `G03-0438` | `G03-0451` | 0.947368 | `minimal_pair_candidate` |
| `G03-0442` | `G03-0455` | 0.923077 | `minimal_pair_candidate` |
| `G03-0454` | `G03-0467` | 0.938776 | `minimal_pair_candidate` |

### Family suggestions

_(Explicit family IDs are assigned in the records; W11 owns final leakage-safe grouping.)_

## Worker coverage summary

### Coverage bucket counts

- ordinary_toxicity_allow: **100**
- repeated_targeting: **100**
- consent_banter_stop: **80**
- staff_abuse: **70**
- dogpile: **70**
- ignore_strict_filter: **50**
- heated_hard_negatives: **30**

### Action / label / channel distribution

The canonical-style tables above contain the exact distributions. Action balance is **200 ALLOW / 225 BLOCK / 75 REVIEW**.

### Multi-message coverage

**317/500 (63.4%)** records contain 2–5 messages. Repeated-targeting, consent, staff-contrast, dogpile, and heated-argument families deliberately exercise conversation context rather than only isolated strings.

### Family / minimal-pair coverage

**223 explicit family IDs** are present. Families cover tolerated toxicity vs incident escalation, mutual banter vs withdrawn consent, criticism vs staff abuse, coordinated vs uncoordinated dogpiles, and /ignore vs stronger-target-filter behavior.

### QA warnings and disposition

Pre-push validation found **0 structural errors** and **0 warning(s)** under the merged QA contract. No unresolved mute-duration, exempt-channel, empty-reason, duplicate-reason, or very-close contradictory warning was produced. The repository's canonical `python -m tools.dataset_qa validate` command is also required on the exact PR head by CI.

### Golden-set leakage review

The frozen owner-policy golden set was read for boundaries but not copied. Automated review found **0 exact message-sequence matches** and **0 >= 0.985 text-similarity candidates** against the golden fixtures. Synthetic families use new wording and explicit `family_id` values so W11 can keep related concepts leakage-safe.

### Notable hard boundaries represented

- Profanity and ordinary game insults remain ALLOW when they are isolated low-level toxicity.
- Repeated same-target behavior can become reviewable or blockable harassment, with the 7-day lighter and 21-day severe containment anchors used only for clearly matching incidents.
- Clear mutual banter remains permissive; repeated genuine stop requests or an uncomfortable participant end that tolerance.
- Direct staff-targeted abuse is BLOCK + strike, while criticism, disagreement, and appeals remain ALLOW.
- Coordinated dogpile participation is BLOCK + strike; uncoordinated mild pile-ons are REVIEW without automatic strikes.
- /ignore is treated as a delivery/user-control boundary for that direct relationship; stronger target filtering can block otherwise tolerated rude content for that target without a strike.

### Deliberately omitted unresolved Policy-v1 edges

This package does not create cases that depend on Discord bot DMs, graphic first-person self-harm disclosure, consensual explicit adult PM content, uncertain-age grooming, broader dangerous-instruction domains, fake-doxxing strike cleanup, an invented threat-duration matrix, blackmail mute duration, or accidental lexical slur-substring rules.

### Known limitations

This worker guarantees within-file uniqueness and checks leakage against the frozen golden set, but it cannot guarantee cross-worker semantic uniqueness. W11 still owns cross-worker exact/near-duplicate review and final split grouping. Relationship-control examples encode the relevant structured state in concise notes because the current generator schema has no dedicated relationship-state object.
