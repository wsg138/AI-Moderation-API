# W11 dataset integration report

- Algorithm: `w11-v2`
- Synthetic records: **4500**
- Integration families: **1883**
- Largest integration family: **45** records
- Text-only exact groups: **83**
- Near candidates (>= 0.75): **2722**
- Cross-source near candidates: **27**
- Decision-contrast lexical candidates: **68**
- Cross-worker differing-decision pairs reviewed: **12**
- Unresolved cross-worker contradictions: **0**
- Golden near/exact candidates: **1**
- Golden-sensitive (>= 0.88): **0**

## Frozen split counts

- train: **3269**
- validation: **385**
- test: **410**
- frozen_adversarial: **436**

## Cross-worker near-pair policy review

| Pair | Similarity | Disposition | Policy source |
|---|---:|---|---|
| `G01-0285 ↔ G08-0460` | 0.8 | `intentional_policy_contrast` | policy/POLICY-v1.md §6 |
| `G01-0287 ↔ G08-0459` | 0.8 | `intentional_policy_contrast` | policy/POLICY-v1.md §6 |
| `G01-0287 ↔ G08-0461` | 0.807018 | `intentional_policy_contrast` | policy/POLICY-v1.md §6 |
| `G01-0295 ↔ G08-0456` | 0.756757 | `intentional_policy_contrast` | policy/POLICY-v1.md §6 |
| `G01-0296 ↔ G08-0444` | 0.765957 | `intentional_policy_contrast` | policy/POLICY-v1.md §6 |
| `G01-0315 ↔ G08-0444` | 0.75 | `intentional_policy_contrast` | policy/POLICY-v1.md §6 |
| `G06-0136 ↔ G09-0356` | 0.847458 | `intentional_policy_contrast` | policy/POLICY-v1.md §11 |
| `G06-0157 ↔ G09-0355` | 0.805556 | `intentional_policy_contrast` | policy/POLICY-v1.md §11 |
| `G06-0176 ↔ G09-0356` | 0.774194 | `intentional_policy_contrast` | policy/POLICY-v1.md §11 |
| `G06-0256 ↔ G09-0388` | 0.918919 | `intentional_policy_contrast` | policy/POLICY-v1.md §11 |
| `G08-0333 ↔ G09-0355` | 0.782609 | `intentional_policy_contrast` | policy/POLICY-v1.md §11 |
| `G08-0469 ↔ G09-0355` | 0.75 | `intentional_policy_contrast` | policy/POLICY-v1.md §11 |


## Whole-corpus distributions

### Domain

| Value | Count |
|---|---:|
| `age_discussion` | 10 |
| `age_evidence` | 50 |
| `benign_chat` | 120 |
| `consent` | 80 |
| `context_linkage` | 120 |
| `dangerous_instructions` | 435 |
| `dogpile` | 70 |
| `doxxing` | 10 |
| `gameplay_violence` | 571 |
| `grooming` | 20 |
| `harassment` | 255 |
| `hate_identity` | 160 |
| `hate_reference` | 100 |
| `hate_slur` | 370 |
| `minecraft_gameplay` | 155 |
| `property_gameplay` | 30 |
| `real_world_threat` | 503 |
| `relationship_controls` | 50 |
| `self_harm` | 550 |
| `sexual_content` | 391 |
| `sexual_minor` | 85 |
| `social` | 30 |
| `social_dating` | 40 |
| `staff_abuse` | 70 |
| `staff_discussion` | 60 |
| `stalking_intimidation` | 50 |
| `toxicity` | 115 |

### Semantic label

| Value | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 220 |
| `DANGEROUS_REAL_WORLD_INSTRUCTIONS` | 289 |
| `DOXXING` | 10 |
| `GAMEPLAY_VIOLENCE` | 631 |
| `GROOMING` | 20 |
| `HATE` | 160 |
| `LOW_LEVEL_HARASSMENT` | 290 |
| `REAL_WORLD_THREAT` | 418 |
| `SAFE` | 1212 |
| `SELF_HARM_INSTRUCTION` | 190 |
| `SELF_HARM_INTENT` | 150 |
| `SEVERE_HARASSMENT` | 185 |
| `SEXUAL_CONTENT` | 190 |
| `SEXUAL_MINOR` | 110 |
| `SLUR_USE` | 310 |
| `STAFF_TARGETED_ABUSE` | 45 |
| `THIRD_PARTY_SELF_HARM_CONCERN` | 70 |

### Action

| Value | Count |
|---|---:|
| `ALLOW` | 1995 |
| `BLOCK` | 2140 |
| `REVIEW` | 365 |

### Review priority

| Value | Count |
|---|---:|
| `NONE` | 3374 |
| `NORMAL` | 824 |
| `URGENT` | 302 |

### Strike

| Value | Count |
|---|---:|
| `false` | 3558 |
| `true` | 942 |

### Containment

| Value | Count |
|---|---:|
| `MUTE` | 195 |
| `NONE` | 4305 |

### Containment duration seconds

| Value | Count |
|---|---:|
| `604800` | 160 |
| `1209600` | 6 |
| `1814400` | 25 |
| `2592000` | 4 |
| `null` | 4305 |

### Support flow

| Value | Count |
|---|---:|
| `NONE` | 4280 |
| `SELF_HARM_CHECK` | 215 |
| `TARGET_SAFETY_CHECK` | 5 |

### Channel profile

| Value | Count |
|---|---:|
| `discord_gaming` | 716 |
| `discord_general` | 999 |
| `minecraft_private` | 805 |
| `minecraft_public` | 1980 |

### Platform hint

| Value | Count |
|---|---:|
| `discord` | 1631 |
| `minecraft` | 2775 |
| `mixed` | 94 |

### Difficulty

| Value | Count |
|---|---:|
| `adversarial` | 1118 |
| `easy` | 521 |
| `hard` | 1900 |
| `medium` | 961 |

### Message count

| Value | Count |
|---|---:|
| `1` | 2798 |
| `2` | 1021 |
| `3` | 371 |
| `4` | 250 |
| `5` | 60 |

### Multi-message coverage

- Single-message: **2798**
- Multi-message: **1702**
- Multi-message proportion: **0.378222**

### Integration family sizes

| Value | Count |
|---|---:|
| `1` | 985 |
| `2` | 313 |
| `3` | 102 |
| `4` | 157 |
| `5` | 274 |
| `6` | 16 |
| `7` | 2 |
| `8` | 5 |
| `9` | 2 |
| `10` | 14 |
| `12` | 1 |
| `14` | 1 |
| `15` | 4 |
| `20` | 2 |
| `21` | 1 |
| `25` | 1 |
| `30` | 2 |
| `45` | 1 |

### Label × channel profile

| Value | `discord_gaming` | `discord_general` | `minecraft_private` | `minecraft_public` |
|---|---:|---:|---:|---:|
| `AMBIGUOUS_REVIEW` | 35 | 71 | 34 | 80 |
| `DANGEROUS_REAL_WORLD_INSTRUCTIONS` | 0 | 198 | 36 | 55 |
| `DOXXING` | 3 | 3 | 2 | 2 |
| `GAMEPLAY_VIOLENCE` | 106 | 6 | 20 | 499 |
| `GROOMING` | 0 | 10 | 10 | 0 |
| `HATE` | 39 | 39 | 41 | 41 |
| `LOW_LEVEL_HARASSMENT` | 81 | 9 | 71 | 129 |
| `REAL_WORLD_THREAT` | 60 | 118 | 77 | 163 |
| `SAFE` | 157 | 275 | 213 | 567 |
| `SELF_HARM_INSTRUCTION` | 30 | 40 | 40 | 80 |
| `SELF_HARM_INTENT` | 30 | 30 | 30 | 60 |
| `SEVERE_HARASSMENT` | 52 | 23 | 35 | 75 |
| `SEXUAL_CONTENT` | 40 | 45 | 35 | 70 |
| `SEXUAL_MINOR` | 0 | 31 | 73 | 6 |
| `SLUR_USE` | 61 | 80 | 74 | 95 |
| `STAFF_TARGETED_ABUSE` | 8 | 7 | 0 | 30 |
| `THIRD_PARTY_SELF_HARM_CONCERN` | 14 | 14 | 14 | 28 |

### Action × domain

| Value | `ALLOW` | `BLOCK` | `REVIEW` |
|---|---:|---:|---:|
| `age_discussion` | 10 | 0 | 0 |
| `age_evidence` | 25 | 25 | 0 |
| `benign_chat` | 120 | 0 | 0 |
| `consent` | 20 | 50 | 10 |
| `context_linkage` | 80 | 0 | 40 |
| `dangerous_instructions` | 146 | 289 | 0 |
| `dogpile` | 0 | 35 | 35 |
| `doxxing` | 0 | 10 | 0 |
| `gameplay_violence` | 571 | 0 | 0 |
| `grooming` | 0 | 20 | 0 |
| `harassment` | 100 | 80 | 75 |
| `hate_identity` | 0 | 160 | 0 |
| `hate_reference` | 100 | 0 | 0 |
| `hate_slur` | 60 | 310 | 0 |
| `minecraft_gameplay` | 155 | 0 | 0 |
| `property_gameplay` | 30 | 0 | 0 |
| `real_world_threat` | 0 | 388 | 115 |
| `relationship_controls` | 25 | 25 | 0 |
| `self_harm` | 200 | 280 | 70 |
| `sexual_content` | 98 | 293 | 0 |
| `sexual_minor` | 0 | 85 | 0 |
| `social` | 30 | 0 | 0 |
| `social_dating` | 25 | 15 | 0 |
| `staff_abuse` | 25 | 45 | 0 |
| `staff_discussion` | 60 | 0 | 0 |
| `stalking_intimidation` | 0 | 30 | 20 |
| `toxicity` | 115 | 0 | 0 |


## Leakage and family safety

- Redundant same-outcome text-only exact groups: **0**.
- Every source `family_id`, text-only exact group, >=0.90 same-worker near group,
  and every >=0.75 cross-worker near pair is kept in one integration family before
  splitting.
- Owner golden fixtures are never copied into these manifests. Synthetic records
  with >=0.88 similarity to a golden fixture are forced
  into frozen evaluation.
- Golden-sensitive synthetic records forced out of training: **0**.

## Decision contrasts

The machine-readable audit records exact and >=0.88 near pairs whose Policy-v1
outcome dimensions differ. These are candidates for intentional minimal pairs or
data defects; W11 does not silently relabel them.

## Known limitation

Near-duplicate detection is deterministic lexical candidate finding, not semantic
embedding similarity. It uses shared normalized token bigrams followed by
normalized character-trigram Dice similarity. Human review remains required.

## Files

- `data/integration/W11-audit.json`
- `data/integration/W11-split-manifest.json`
- `data/integration/W11-adversarial-eval-manifest.json`
