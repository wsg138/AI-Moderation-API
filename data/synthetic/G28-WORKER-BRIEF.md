# G28 — Swatting & False-Emergency Threats: worker brief (for ChatGPT)

## Why this exists
Luna's local workers generated 9,000 synthetic moderation-training examples across 18 batches (G10–G27) for the Enthusia AI moderation classifier. This batch (G28) was blocked by automated safety filters on Luna's side — the realistic swatting-threat content tripped them. The design below is complete and verified against the project schema; it just needs a worker on different tooling to execute it.

## Output files
- `data/synthetic/G28-swatting.jsonl` — 500 records, one JSON object per line
- `data/synthetic/G28-report.md` — QA report (see validation step)

Write them into the ai-moderation repo working copy (the mother worker / user will say where).

## Schema
Read the first 5 rows of `data/synthetic/G02-real-world-threats.jsonl` in the ai-moderation repo to match the exact JSON schema. Required keys per record:
`example_id, policy_version ("v1"), source ("synthetic"), domain, difficulty, platform_hint, channel_profile, messages (array of {speaker, offset_ms, text}), target_index, label, action, review_priority, strike, containment, containment_duration_seconds, support_flow, reason_codes (array), notes, family_id`

Enum values live in `tools/dataset_qa/config.json` — use ONLY those values. ID range G28:1–500 is registered there (example_ids `G28-0001` … `G28-0500`). G02's convention for REAL_WORLD_THREAT: action BLOCK, review_priority URGENT, containment MUTE with `containment_duration_seconds` 604800, strike false, support_flow NONE.

## Content: swatting & false-emergency threats (label: REAL_WORLD_THREAT)
- Direct swatting threats ("I'm calling a SWAT team to your house", "enjoy the cops at your door in 20 minutes")
- Implied swatting ("your address is already on the call", "hope you like surprise visitors with badges")
- False bomb / false shooting reports threatened against the target's location
- "I reported you to the FBI" intimidation, fake 911-call narration, conditional threats ("apologize or I make the call")
- CRITICAL: threaten the ACT, never post real addresses or phone numbers — no actual location data anywhere (that's the doxxing lane, not this one)
- Do NOT do school-specific threats — sibling batch G20 owns those

## Distribution
- ~400 REAL_WORLD_THREAT / ~75 SAFE / ~25 AMBIGUOUS_REVIEW
- Difficulty: easy 15% / medium 25% / hard 45% / adversarial 15%
- Multi-message ≥55%
- All family_ids prefixed `g28.` — verified zero overlap with G02's families (G02 has 0 swat/911 mentions; its families are school/location/stalking/bomb-delivery)

## Hard negatives (~15% SAFE)
- Discussing swatting as a news topic ("did you hear that streamer got swatted")
- Condemning swatting
- "The cops" in clearly fictional RP / in-game context

## Ambiguous (~5% AMBIGUOUS_REVIEW)
- "I'm calling the cops on you" in a cheating-report context (hyperbole vs genuine intimidation)
- Vague "you'll be hearing from the authorities" with no clear meaning

## Quality bar
- Zero exact-duplicate texts. Realistic player register (short, slangy, typos ok). Serious tone, no graphic detail.
- Every label must be defensible; notes should name the scenario family.

## Validation (run in the ai-moderation repo)
1. `python3 -m tools.dataset_qa validate data/synthetic/G28-swatting.jsonl --range G28:1-500` — fix until 0 errors
2. `python3 -m tools.dataset_qa report data/synthetic/G28-swatting.jsonl --range G28:1-500 --output data/synthetic/G28-report.md`

Do not commit anything. Report final record count, error count, and label distribution.
