# Dataset QA report

- File: `data/synthetic/G04-self-harm.jsonl`
- Records: **500**
- Errors: **0**
- Warnings: **0**
- Exact duplicate groups: **0**
- Near candidates: **7**
- Minimal-pair candidates: **0**
- Multi-message proportion: **0.718000**
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
| `adversarial` | 65 |
| `hard` | 325 |
| `medium` | 110 |

### platform_hint

| Value | Count |
|---|---:|
| `discord` | 200 |
| `minecraft` | 300 |

### channel_profile

| Value | Count |
|---|---:|
| `discord_gaming` | 100 |
| `discord_general` | 100 |
| `minecraft_private` | 100 |
| `minecraft_public` | 200 |

### label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 25 |
| `GAMEPLAY_VIOLENCE` | 30 |
| `SAFE` | 75 |
| `SELF_HARM_INSTRUCTION` | 150 |
| `SELF_HARM_INTENT` | 150 |
| `THIRD_PARTY_SELF_HARM_CONCERN` | 70 |

### action

| Value | Count |
|---|---:|
| `ALLOW` | 200 |
| `BLOCK` | 230 |
| `REVIEW` | 70 |

### review_priority

| Value | Count |
|---|---:|
| `NONE` | 385 |
| `NORMAL` | 75 |
| `URGENT` | 40 |

### containment

| Value | Count |
|---|---:|
| `NONE` | 500 |

### support_flow

| Value | Count |
|---|---:|
| `NONE` | 285 |
| `SELF_HARM_CHECK` | 215 |

### Strike

| Value | Count |
|---|---:|
| `false` | 350 |
| `true` | 150 |

### Containment duration coverage

| Value | Count |
|---|---:|
| `null` | 500 |

### Reason codes

| Value | Count |
|---|---:|
| `discord_gameplay_explicit` | 42 |
| `explicit_real_world_cue` | 71 |
| `gameplay_death_context` | 105 |
| `insufficient_context` | 25 |
| `minecraft_gameplay_explicit` | 63 |
| `obfuscated_evasion` | 60 |
| `private_context_relevant` | 100 |
| `reply_context` | 196 |
| `safety_check_recent` | 10 |
| `self_harm_disclosure` | 150 |
| `self_harm_instruction` | 150 |
| `split_message_context` | 123 |
| `third_party_self_harm_concern` | 70 |

### Message count

| Value | Count |
|---|---:|
| `1` | 141 |
| `2` | 319 |
| `3` | 30 |
| `4` | 10 |

### Diagnostic codes

| Value | Count |
|---|---:|
| _(none)_ | 0 |

### Exact duplicate groups

_(none)_

### Near/minimal-pair candidates

| Left | Right | Similarity | Kind |
|---|---|---:|---|
| `G04-0211` | `G04-0212` | 0.955556 | `near_duplicate_candidate` |
| `G04-0236` | `G04-0237` | 0.961039 | `near_duplicate_candidate` |
| `G04-0261` | `G04-0262` | 0.956522 | `near_duplicate_candidate` |
| `G04-0431` | `G04-0435` | 0.948454 | `near_duplicate_candidate` |
| `G04-0461` | `G04-0465` | 0.924471 | `near_duplicate_candidate` |
| `G04-0466` | `G04-0470` | 0.920128 | `near_duplicate_candidate` |
| `G04-0476` | `G04-0479` | 0.921136 | `near_duplicate_candidate` |

### Family suggestions

- `SUGGESTED-0001`: `G04-0211`, `G04-0212`
- `SUGGESTED-0002`: `G04-0236`, `G04-0237`
- `SUGGESTED-0003`: `G04-0261`, `G04-0262`
- `SUGGESTED-0004`: `G04-0431`, `G04-0435`
- `SUGGESTED-0005`: `G04-0461`, `G04-0465`
- `SUGGESTED-0006`: `G04-0466`, `G04-0470`
- `SUGGESTED-0007`: `G04-0476`, `G04-0479`

# W05 worker report

## Coverage bucket counts

| Bucket | Count |
| --- | ---: |
| Directed self-harm abuse/instruction | 100 |
| First-person disclosure/intent | 100 |
| Gameplay/death/respawn hard negatives | 80 |
| Third-party concern/report | 70 |
| Obfuscation/split-message/evasion | 60 |
| Ambiguous death-wish / go-die context | 50 |
| Safety-check response sequences | 40 |
| **Total** | **500** |

No bucket shift was required.

## Action, label, and channel distribution

The canonical tables above are the authoritative distributions. In summary: BLOCK=230, ALLOW=200, REVIEW=70. Labels are SELF_HARM_INSTRUCTION=150, SELF_HARM_INTENT=150, THIRD_PARTY_SELF_HARM_CONCERN=70, SAFE=75, GAMEPLAY_VIOLENCE=30, and AMBIGUOUS_REVIEW=25. Channels are minecraft_public=200, minecraft_private=100, discord_general=100, and discord_gaming=100.

The resulting action mix is 46.0% BLOCK, 40.0% ALLOW, and 14.0% REVIEW.

## Multi-message coverage

**359/500 (71.8%)** examples contain multiple messages. They exercise replies, same-sender continuation, split/evasive wording, third-party reports, safety-check answers, and cooldown/escalation sequences. Different speakers are not combined as though they supplied one person's intent.

## Families and minimal-pair review

The dataset contains **100** explicit `family_id` groups. The canonical analyzer reports **7** near candidates and **0** minimal-pair candidates.

All 7 near candidates are intentional variants inside the same declared family; none crosses a family boundary. They are retained because they vary punctuation, framing, or conversational context while preserving the same owner-policy outcome. W11 should keep each declared family together during leakage-safe splitting.

## QA warnings and disposition

Canonical QA reports **0 errors and 0 warnings**, with **0 exact duplicate groups**. There are no validator warnings requiring a false-positive disposition. The 7 near candidates are advisory candidates, not warnings.

Exact-head GitHub Actions CI is recorded on PR #36; the durable PR completion comment records the final run and conclusion so this file does not need to embed its own commit SHA.

## Golden-set leakage review

The owner-policy golden set was used only to understand resolved boundaries. No exact golden message sequence was copied, and the synthetic file avoids trivial one-word edits of the golden fixtures. Golden-adjacent concepts are expressed with new wording/scenarios and explicit family IDs.

## Notable hard boundaries represented

- Directed self-harm encouragement/instruction is BLOCK + strike, including shorthand and evasion.
- Credible non-graphic first-person disclosure remains visible, creates no strike, and starts a support flow.
- Clear gameplay death/respawn language remains allowed.
- Gameplay/joke self-harm shorthand is separately represented as semantically non-genuine but still BLOCK without strike under owner policy.
- Third-party concern remains visible while creating safety-review/check work; immediate-danger/help variants use urgent review.
- Gameplay vs explicit real-world vs insufficient-context death wishes are represented as contrasting families.
- Recent safety history is isolated from punishment reputation.
- A recent completed low-risk safety check may suppress another prompt; genuine escalation retriggers support and urgency.

## Deliberately omitted unresolved Policy-v1 edges

No example depends on Discord bot DMs, graphic first-person self-harm disclosure, consensual explicit adult PM content, uncertain-age grooming, broader dangerous-instruction domains, fake-doxxing strike cleanup, a complete threat-duration matrix, blackmail mute duration, or accidental slur-substring rules.

Self-harm examples remain non-graphic. No mute duration or other unresolved policy outcome was invented.

## Known limitations

W11 still owns cross-worker exact/semantic deduplication and final leakage-safe train/validation/evaluation grouping. Synthetic examples cannot represent every live conversational style, and no production chat data is included.
