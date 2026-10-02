# Dataset QA report — G08 evasion/context

- File: `data/synthetic/G08-evasion-context.jsonl`
- Records: **500**
- Canonical validator errors: **0**
- Canonical validator warnings: **0**
- Exact duplicate groups: **0**
- Near/minimal-pair candidates: **103**
- Multi-message records: **276**
- Multi-message proportion: **0.552000**
- Explicit family count: **295**

The canonical repository validator ran against the finalized dataset content in `service-ci` run **37024834160** and reported:

```text
summary: records=500 errors=0 warnings=0 exact_duplicate_groups=0 near_candidates=103
```

## Coverage buckets

| Bucket | Count |
|---|---:|
| Split-message real-world threat/context reversal | 100 |
| Directed-self-harm obfuscation/spacing/evasion | 80 |
| Slur obfuscation/masking/reference | 80 |
| Harassment/dogpile multi-message or multi-sender context | 70 |
| Sexual/minor euphemism/context within resolved policy | 60 |
| Dangerous-request euphemism/split intent, explosives only | 50 |
| Platform/channel-profile context flips | 40 |
| Quote/report/reply-vs-endorsement context | 20 |
| **Total** | **500** |

## Action distribution

| Action | Count |
|---|---:|
| `ALLOW` | 175 |
| `BLOCK` | 250 |
| `REVIEW` | 75 |

This is 35% ALLOW, 50% BLOCK, and 15% REVIEW, matching the requested deliberately adversarial balance.

## Label distribution

| Label | Count |
|---|---:|
| `AMBIGUOUS_REVIEW` | 40 |
| `DANGEROUS_REAL_WORLD_INSTRUCTIONS` | 24 |
| `GAMEPLAY_VIOLENCE` | 71 |
| `LOW_LEVEL_HARASSMENT` | 15 |
| `REAL_WORLD_THREAT` | 38 |
| `SAFE` | 112 |
| `SELF_HARM_INSTRUCTION` | 40 |
| `SEVERE_HARASSMENT` | 55 |
| `SEXUAL_CONTENT` | 10 |
| `SEXUAL_MINOR` | 25 |
| `SLUR_USE` | 70 |

## Channel distribution

| Channel profile | Count |
|---|---:|
| `discord_gaming` | 38 |
| `discord_general` | 153 |
| `minecraft_private` | 79 |
| `minecraft_public` | 230 |

No exempt Discord profile appears in this semantic dataset.

## Review / strike / containment distribution

| Dimension | Value | Count |
|---|---|---:|
| Review priority | `NONE` | 360 |
| Review priority | `NORMAL` | 85 |
| Review priority | `URGENT` | 55 |
| Strike | `false` | 315 |
| Strike | `true` | 185 |
| Containment | `NONE` | 490 |
| Containment | `MUTE` | 10 |
| Support flow | `NONE` | 500 |

All 10 mutes use the resolved seven-day known-16 nude-solicitation anchor. No null-duration mute was introduced.

## Multi-message coverage

**276 / 500 (55.2%)** records use multi-message context. The set includes immediate same-sender continuations, reply context, long-gap non-linkage, target changes, public/private context, reliable age context, and true multi-sender incidents.

Different speakers are not stitched into one person's intent except where Policy v1 explicitly permits incident-level multi-sender harassment/dogpile aggregation.

## Families / minimal-pair coverage

There are **295 explicit `family_id` groups**. The canonical validator found **103 advisory near/minimal-pair candidates** and no warning-level near contradictions.

Major contrast families include:

- gameplay cue → real-world cue;
- immediate continuation → long unrelated gap;
- Minecraft → Discord general → Discord gaming;
- public flirting → private flirting;
- actual slur → masked/quoted/reclaimed actual slur → reference-only wording;
- coordinated dogpile → uncoordinated pile-on → mutual banter;
- real explosive-instruction request → Minecraft explosive mechanics → high-level historical discussion.

The near-candidate count is intentionally nonzero because this worker is specifically responsible for adversarial minimal pairs.

## QA warnings and disposition

Canonical validation produced **0 warnings** and **0 errors**. Therefore there are no unresolved-duration, exempt-profile, empty-reason-code, duplicate-reason-code, or warning-level near-contradiction findings to disposition.

The 103 near/minimal-pair candidates are advisory rather than warnings. They are intentional contrast families and are grouped where appropriate so W11 can preserve leakage-safe splits.

## Golden-set leakage review

The 52-record owner golden set was used only to learn policy boundaries.

A direct normalized message-sequence comparison between the final G08 file and `data/eval/owner-policy-v1.jsonl` found **0 exact golden sequence matches**. A targeted manual pass also rewrote the closest seed-like phrases before finalization rather than retaining trivial one-line variants. The final dataset therefore does not intentionally copy owner interview wording as a training template.

Conceptually close families remain explicitly grouped so W11 can keep them separated from frozen evaluation fixtures during final splitting.

## Notable hard boundaries represented

- Immediate connected fragments can retroactively turn Minecraft-looking threat language into a real-world threat.
- Long unrelated conversational gaps break speculative threat linkage.
- Discord general does not inherit Minecraft's automatic gameplay prior; Discord gaming can regain it with explicit game context.
- Directed self-harm evasion remains block + strike, while clearly game-mechanics death language is allowed.
- Actual slurs remain block + strike when masked, misspelled, quoted, condemned, or reclaimed; reference-only names such as “the n-word” remain allowed.
- Coordinated dogpiles differ from uncoordinated pile-ons and clearly mutual banter.
- Public non-explicit flirting is blocked while equivalent private flirting is allowed.
- Minor-specific outcomes are used only with reliable minor context, not unsupported self-report.
- Dangerous examples are requests or context only; no operational explosive recipe appears.

## Deliberately omitted unresolved Policy-v1 edges

The dataset does not create outcomes that depend on:

- Discord bot DMs;
- graphic first-person self-harm disclosure;
- consensual explicit adult PM content;
- grooming with uncertain minor status;
- dangerous-instruction domains beyond the resolved explosive examples;
- fake-doxxing strike cleanup after information is proven fake;
- an invented complete threat severity/duration matrix;
- exact blackmail mute duration;
- accidental lexical slur-substring handling.

## Known limitations

This worker guarantees uniqueness and policy consistency within G08 only. W11 still owns cross-worker exact/near-duplicate analysis, semantic deduplication, and final golden leakage integration. The deliberately balanced action distribution is adversarial test/training design and should not be interpreted as production prevalence.

## Scope / safety confirmation

Only the owned synthetic JSONL and this report are part of the worker deliverable. No production chat data, secrets, model training, runtime/client code, policy files, golden-set files, deployment, live configuration, or production action is included.
