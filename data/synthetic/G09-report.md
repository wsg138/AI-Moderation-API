# Dataset QA report

- File: `data/synthetic/G09-benign-hard-negatives.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **0**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.320000**

### source

| Value | Count |
|---|---:|
| `synthetic` | 500 |

### domain

| Value | Count |
|---|---:|
| `age_discussion` | 10 |
| `benign_chat` | 120 |
| `context_linkage` | 30 |
| `dangerous_instructions` | 40 |
| `gameplay_violence` | 100 |
| `harassment` | 35 |
| `hate_slur` | 30 |
| `social_dating` | 40 |
| `staff_discussion` | 60 |
| `toxicity` | 35 |

### difficulty

| Value | Count |
|---|---:|
| `adversarial` | 111 |
| `easy` | 31 |
| `hard` | 258 |
| `medium` | 100 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 183 |
| `minecraft` | 317 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 90 |
| `discord_general` | 93 |
| `minecraft_private` | 25 |
| `minecraft_public` | 292 |

### label

| Value | Count |
|---|---:|
| `GAMEPLAY_VIOLENCE` | 100 |
| `LOW_LEVEL_HARASSMENT` | 35 |
| `SAFE` | 365 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 485 |
| `BLOCK` | 15 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 500 |

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
| `age_self_report_clue` | 6 |
| `discord_gameplay_explicit` | 80 |
| `historical_or_high_level_context` | 40 |
| `house_ambiguous_gameplay` | 1 |
| `insufficient_context` | 30 |
| `low_severity_insult` | 35 |
| `minecraft_gameplay_explicit` | 195 |
| `mutual_banter_evidence` | 15 |
| `private_context_relevant` | 25 |
| `private_flirting` | 25 |
| `public_flirting` | 15 |
| `quoted_or_condemned` | 16 |
| `reply_context` | 160 |
| `slur_reference_only` | 30 |

### Message count

| Value | Count |
|---|---:|
| `1` | 340 |
| `2` | 160 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| _(none)_ |  |  |  |

### Family suggestions

_(none)_

## W10 coverage summary

| Coverage bucket | Count |
|---|---:|
| Ordinary server/social/everyday chat | 120 |
| Minecraft violence/gameplay hard negatives | 100 |
| Profanity/heated arguments below harassment threshold | 70 |
| Good-faith staff criticism/appeal/moderation discussion | 60 |
| Nonsexual social/age/dating discussion | 50 |
| Benign historical/high-level safety or explosive discussion | 40 |
| Safe slur-reference/report terminology without an actual slur | 30 |
| Vague replies/fragments/insufficient context | 30 |

### Action / label / channel disposition

- ALLOW: **485 / 500 (97.0%)**; BLOCK: **15 / 500**; REVIEW: **0**.
- Labels: SAFE 365, GAMEPLAY_VIOLENCE 100, LOW_LEVEL_HARASSMENT 35.
- Channel profiles: minecraft_public 292, minecraft_private 25, discord_general 93, discord_gaming 90.

### Multi-message coverage

- **160 / 500 (32.0%)** records contain 2-message conversation context; the remaining 340 are single-message cases.

### Families / minimal pairs

- **100** explicit family IDs are present, normally 5 records per family.
- The local preflight mirror found no >=0.92 near-duplicate candidates; the public/private flirting families still encode the resolved surface boundary without copying the golden wording.

### QA warnings and disposition

- Local preflight: **0 errors, 0 warnings, 0 exact duplicate groups, 0 near-duplicate candidates**.
- GitHub CI is expected to run the repository's canonical `python -m tools.dataset_qa validate` command on the PR head; this report will be reconciled if canonical CI finds anything different.

### Golden-set leakage review

- Compared normalized complete message sequences against all 52 owner-policy golden fixtures: **0 exact sequence matches**.
- A separate similarity review of the generated text found no >=0.90 synthetic-to-golden sequence match; wording was written independently rather than produced as one-word edits of golden fixtures.

### Notable hard boundaries represented

- Minecraft/Discord-gaming violent vocabulary with explicit game mechanics remains allowed.
- One-off profanity and low-level gameplay insults remain allowed; mutual banter examples remain below the incident threshold.
- Good-faith disagreement with staff decisions remains allowed and is kept distinct from staff-targeted abuse.
- Ordinary non-explicit flirting is allowed in private messages but blocked in public chat with no strike.
- Benign age discussion treats self-report as a clue only and includes no sexualized minor content.
- Historical, conceptual, and safety-oriented explosive discussion is allowed without operational construction steps.
- Reference-only slur terminology and reporting language is allowed only when no actual prohibited slur appears.
- Vague replies are not treated as proof of harmful intent when required context is missing.

### Deliberately omitted unresolved Policy-v1 edges

- Discord bot DMs.
- Graphic first-person self-harm disclosure.
- Consensual explicit adult PM content.
- Grooming where minor status is genuinely uncertain.
- Broader dangerous-instruction domains beyond resolved explosive discussion.
- Fake-doxxing strike cleanup.
- Any invented full threat-severity-to-duration matrix.
- Exact blackmail mute duration.
- Accidental lexical slur-substring rules.

### Known limitations

- This worker guarantees uniqueness and leakage review within G09 and against the frozen golden messages; W11 still owns cross-worker semantic deduplication.
- This file intentionally emphasizes hard negatives. Its 15 BLOCK records are the resolved public-flirting contrast, not a broad positive-violation sample.
- No production chat data was used.
