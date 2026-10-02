# Owner policy interview protocol

The interview worker's job is to learn the owner's actual moderation boundary, especially where generic safety models and Minecraft norms disagree.

## Format

Use short batches of 12–20 examples. Do not dump hundreds of prompts at once.

For each example, ask the owner to choose:
- **ALLOW**
- **REVIEW**
- **BLOCK**
- **Depends** (and explain what missing context changes it)

Also ask, when useful:
- should an earlier message be retroactively removed?
- should staff be notified?
- should this count toward a future punishment/strike?
- what nearby wording would change the answer?

## Interview dimensions

Cover hard contrasts rather than obvious duplicates:

- gameplay threat vs real-world threat;
- Minecraft house/base vs real home;
- immediate/specific school/work/location/time cues;
- low-level insults vs sustained harassment;
- profanity alone vs targeted abuse;
- self-harm disclosure vs encouragement/instruction;
- hate vs quoted/counterspeech/reclaimed language;
- sexual content vs sexual/minor;
- dangerous Minecraft crafting vs real-world instructions;
- jokes/sarcasm/roleplay;
- replies/quotes;
- obfuscation/leetspeak/spaced letters;
- split messages;
- one sender vs multiple speakers;
- long-gap vs immediate follow-up;
- Discord context vs Minecraft context.

## Recording

Every asked scenario is saved as JSONL in `policy/interviews/` with:
- interview item ID;
- exact messages/context shown;
- owner action;
- owner explanation in concise ordinary language;
- any retroactive-delete choice;
- staff-alert choice;
- strike/punishment relevance;
- date/policy version.

Do not infer an answer the owner did not give. Mark unresolved items explicitly.

## Deliverable

The worker converts the interview into `policy/POLICY-v1.md` containing:
- concrete ALLOW/BLOCK/REVIEW rules;
- context rules;
- ambiguous cases;
- reason-code definitions;
- examples;
- unresolved questions.

The coordinator reviews Policy v1 before any 500-example generation workers begin.
