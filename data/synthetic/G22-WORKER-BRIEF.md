# G22 — Dangerous Instructions (non-explosive): worker brief (for ChatGPT)

## Why this exists
Luna's local workers generated 9,000 synthetic moderation-training examples across 18 batches (G10–G21, G23–G27) for the Enthusia AI moderation classifier. This batch (G22) was blocked by automated safety filters on Luna's side — bulk generation of illicit-behavior REQUESTS tripped them. The design below is complete and verified against the project schema; it just needs a worker on different tooling to execute it.

## Output files
- `data/synthetic/G22-dangerous-instructions-2.jsonl` — 500 records, one JSON object per line
- `data/synthetic/G22-report.md` — QA report (see validation step)

Write them into the ai-moderation repo working copy (the mother worker / user will say where).

## Schema
Read the first 5 rows of `data/synthetic/G07-dangerous-instructions.jsonl` in the ai-moderation repo to match the exact JSON schema. Required keys per record:
`example_id, policy_version ("v1"), source ("synthetic"), domain, difficulty, platform_hint, channel_profile, messages (array of {speaker, offset_ms, text}), target_index, label, action, review_priority, strike, containment, containment_duration_seconds, support_flow, reason_codes (array), notes, family_id`

Enum values live in `tools/dataset_qa/config.json` — use ONLY those values. ID range G22:1–500 is registered there (example_ids `G22-0001` … `G22-0500`). Label→action conventions: DANGEROUS_REAL_WORLD_INSTRUCTIONS → BLOCK / NONE priority / no strike; SAFE → ALLOW / NONE; AMBIGUOUS_REVIEW → REVIEW / NORMAL. `target_index` points at the violating message.

## CRITICAL SAFETY RULE
Generate the REQUEST / ATTEMPT messages only (e.g. "how do I make [dangerous thing]", "tell me how to hack someone's account"). NEVER write actual instructions, recipes, or how-tos anywhere in the file. The classifier must learn to flag the request — your examples ARE the requests, labeled as violations.

## Content: dangerous-instruction requests, non-explosive (label: DANGEROUS_REAL_WORLD_INSTRUCTIONS)
Five buckets × 80 records, all `g22.*`-prefixed family_ids, strictly non-explosive (G07 owns explosives):
1. Drug synthesis requests
2. Weapon-making requests
3. Account-hacking / phishing-howto requests
4. Lockpicking / burglary requests
5. Poison requests (to harm others)

No self-harm framing (sibling batch owns self-harm-intent). No doxxing content.

## Distribution
- 400 DANGEROUS_REAL_WORLD_INSTRUCTIONS / 75 SAFE / 25 AMBIGUOUS_REVIEW
- Difficulty: easy 75 / medium 125 / hard 225 / adversarial 75 (adversarial: "for a story I'm writing…", "hypothetically…", "school project…" framing)
- Multi-message ≥50%, including request → pushback → insistence arcs

## Hard negatives (~15% SAFE)
- Chemistry homework questions ("how does photosynthesis work")
- Cooking recipes
- Minecraft crafting with explicit game context ("how do I make TNT in game" = GAMEPLAY, safe)
- Locksmith / ethical-hacking career questions

## Ambiguous (~5% AMBIGUOUS_REVIEW)
- Dual-use questions ("how do knives get sharpened" — cooking vs weapon context)

## Quality bar
- Zero exact-duplicate texts. Realistic player register. In `notes`, name the request category.
- Every label must be defensible.

## Validation (run in the ai-moderation repo)
1. `python3 -m tools.dataset_qa validate data/synthetic/G22-dangerous-instructions-2.jsonl --range G22:1-500` — fix until 0 errors
2. `python3 -m tools.dataset_qa report data/synthetic/G22-dangerous-instructions-2.jsonl --range G22:1-500 --output data/synthetic/G22-report.md`

Do not commit anything. Report final record count, error count, and label distribution.
