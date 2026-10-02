# G05 — Hate / identity synthetic dataset report

## Scope

This package contains exactly **500** synthetic Policy-v1 examples for IDs `G05-0001..G05-0500`. It covers actual slur use, identity-targeted hate/discrimination, safe term references, deliberate obfuscation/evasion, contextual identity attacks, and explicit minimal-pair families. No production chat data is used.

## Coverage bucket counts

| Bucket | Count |
| --- | ---: |
| Actual-slur examples across direct/quoted/counterspeech/reclaimed/masked/misspelled contexts | 160 |
| Identity-targeted hate/discrimination without slurs | 100 |
| Safe reference/education/report examples without an actual prohibited slur | 80 |
| Deliberate obfuscation/evasion examples | 60 |
| Multi-message/contextual identity-attack examples | 50 |
| Minimal-pair records separating references, actual use, and identity attacks | 50 |
| **Total** | **500** |

No bucket shift was used.

## Label distribution

| Label | Count |
| --- | ---: |
| HATE | 160 |
| SAFE | 100 |
| SLUR_USE | 240 |

## Action distribution

| Action | Count |
| --- | ---: |
| ALLOW | 100 |
| BLOCK | 400 |

BLOCK proportion: **80.0%**.

## Channel distribution

| Channel profile | Count |
| --- | ---: |
| discord_gaming | 125 |
| discord_general | 125 |
| minecraft_private | 125 |
| minecraft_public | 125 |

## Review distribution

| Review priority | Count |
| --- | ---: |
| NONE | 494 |
| NORMAL | 6 |

## Difficulty distribution

| Difficulty | Count |
| --- | ---: |
| adversarial | 80 |
| easy | 32 |
| hard | 256 |
| medium | 132 |

## Context and family coverage

- Multi-message examples: **71/500 (14.2%)**.
- Explicit family IDs: **113 distinct families**.
- Every family contains **2–8 records**. Families group real paraphrase/contrast/evasion sets instead of serving as per-record tags.
- Automated-mute anchor examples: **6**, limited to repeated serious racial/ethnic slur behavior after a prior warning and fixed at the Policy-v1 ~14-day anchor.
- Minimal-pair block: **10 five-record families / 50 records**, each contrasting safe term reference, actual-term use, non-slur identity attack, safe report, and counterspeech that reproduces the actual term.
- The 100 non-slur identity attacks use 25 distinct semantic/linguistic patterns across varied identities and server contexts; the 80 safe-reference examples use 20 distinct reference/report/education patterns.
- Platform/channel rotation covers Minecraft public/private plus Discord general/gaming. Exempt Discord surfaces are intentionally omitted because they are policy-engine/runtime state rather than ordinary semantic-classifier inputs.

## Policy decisions represented

- Any actual slur is `BLOCK + strike`, including quote/report, counterspeech, joke, reclaimed/self-reference, masking, misspelling, and deliberate evasion.
- A reference such as “the n-word” or “the f-slur” is allowed when it clearly names the term instead of acting as a derogatory substitute.
- Identity-targeted racist, sexist, bigoted, discriminatory, exclusionary, and dehumanizing statements are blocked even without a slur.
- Non-slur hate records do **not** invent the slur-specific automatic strike.
- Repeated serious racial/ethnic slur behavior after a prior warning includes the documented ~14-day containment anchor; ordinary single slur uses do not invent a mute.
- Context examples preserve speaker boundaries and use same-sender continuation/reply context without stitching unrelated speakers into one intent.

## QA warnings and disposition

The canonical repository validator is run on this file by PR CI using the same `python -m tools.dataset_qa validate` path required by the launch packet.

The earlier exact-head validation was already clean at **500 records, 0 errors, 0 warnings, 0 exact-duplicate groups** before this wording-diversity pass. This pass changes only synthetic wording/family organization while preserving schema and policy outcomes; final exact-head CI is the authoritative acceptance gate.

Near-candidate pairs are advisory rather than validator warnings. Close examples are expected in the intentionally dense minimal-pair, quote/counterspeech, masking, and evasion families, and those examples are grouped under explicit 2–8-record family IDs for W11 review.

## Golden-set leakage review

The protected owner golden set was read only to learn resolved boundaries. None of its hate/slur message sequences are copied exactly, and the synthetic file does not use trivial one-word edits of the golden placeholder fixtures. Conceptually related contrasts are grouped under explicit family IDs so W11 can keep leakage-safe groups together during splitting.

## Deliberately omitted unresolved Policy-v1 edges

This package does not create examples whose correct outcome depends on Discord bot DMs, graphic first-person self-harm disclosure, consensual explicit adult PM content, uncertain-age grooming, broader dangerous-instruction domains, fake-doxxing strike cleanup, a complete threat-duration matrix, blackmail mute duration, or accidental lexical slur-substring behavior.

The accidental lexical-match edge is especially excluded: safe references are explicit term references, not substring tricks.

## Known limitations

- This worker guarantees uniqueness inside G05 only; W11 still owns cross-worker exact/near-duplicate and leakage integration.
- Actual slurs are included only where required to train the resolved Policy-v1 distinction. The surrounding scenarios stay moderation-focused rather than gratuitous.
- Non-slur hate strike escalation beyond the explicit slur rule is not invented; future owner policy could add a separate severe-hate strike rule.
- The dataset intentionally does not model exempt Discord channels as normal semantic-classifier examples.

## Acceptance evidence

- Dataset: `data/synthetic/G05-hate-identity.jsonl`
- Report: `data/synthetic/G05-report.md`
- Records: **500**
- Generator range: **G05-0001..G05-0500**
- Production data: **none**
- Runtime/API/client changes: **none**
- Policy or golden-set changes: **none**
- Model training/deployment: **none**
- Secrets: **none**
- Self-merge: **prohibited**
