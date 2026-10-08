# Owner ruling — Minecraft-only extortion vs real-world blackmail

**Decision date:** 2026-10-08. **Authority:** explicit owner answer after the 16-case solo screening. **Candidate revision:** `cc5d928707f20cf24bb7fd561c690ce9fecb572d`. **Status:** policy decision **settled**; candidate label corrections **not yet independently adjudicated**.

## Rule

- If **every aspect** of a blackmail/extortion demand or threatened consequence is clearly **inside Minecraft gameplay** (items, in-game bases, in-game base coordinates, builds, or in-game payment), **ALLOW**. Do not issue blackmail-related strikes, staff pings, or mutes. Applies in Minecraft and Discord when clear gameplay context is established.
- If the demand, leverage, or threatened harm concerns **real-world** money, identifying/private real-life information, photos, safety, or offline consequences, the gameplay exemption does **not** apply. Clearly real-world blackmail is **BLOCK**, urgent staff review, and temporary mute pending staff review as already specified by Policy v1. Posting it in Minecraft does not change its nature.
- When game-versus-real stakes cannot be determined from the as-of-target context, require additional context or **REVIEW** rather than an automatic punitive label. Do not treat "coords" alone as proof of real-world location or proof of Minecraft location when game context is absent.
- Unrelated safety prohibitions still apply to slurs, IRL threats, real personal-data doxxing, and directed self-harm abuse.

## Policy minimal pairs (illustrative, not additional training data)

| Example target/context | Intended owner outcome | Why |
|---|---|---|
| "Give me 64 diamonds or I tell everyone where your Minecraft base is." | **ALLOW**, no blackmail punishment | Entirely game items and in-game coordinates |
| "Pay a stack of ancient debris or your secret Minecraft base gets revealed." | **ALLOW**, no blackmail punishment | In-game leverage only |
| Minecraft player: "Send me $50 in real money or I'll post your private personal photos." | **BLOCK**, urgent staff review | Real-world financial and privacy threat, despite game platform |
| Discord gaming: "Pay diamonds or I post your real-life home address." | **BLOCK**, urgent staff review | Personal real-world data, despite in-game currency |
| "Pay up or I'm leaking your coords." with no other context | **REVIEW** | Unclear whether this concerns Minecraft coordinates or real-life information |

These examples are *expected policy decisions*, not classifier performance tests or gold labels for any source record.

## Consequence for public synthetic batch G10

Read-only review of the G10 candidate file found:
- 500 synthetic records in the batch.
- 397 existing `BLACKMAIL / BLOCK` records.
- **341** `BLACKMAIL / BLOCK` records already tagged `minecraft_gameplay_explicit`, with no `explicit_real_world_cue` reason tag. They are **potentially mislabeled under this owner rule**.
- 28 `BLACKMAIL / BLOCK` records already tagged with an explicit real-world cue and therefore **not included** in that 341-case candidate bucket.

**These counts use the original synthetic labels/reason codes, which are precisely what require QA.** A record with no `explicit_real_world_cue` tag is not proved free of real-world cues; inspect the source text/target-time context before final disposition. Do not blindly relabel 341 cases and do not treat the pilot as a statistically representative accuracy measurement. The two disputed game-only pilot examples require correction proposals; their original source mapping remains in the coordinator-only archive until the independent-review gate.

Run `python -m tools.dataset_qa.owner_blackmail_audit` to regenerate an aggregate read-only count from G10. The script cannot mutate labels or admit training examples. It excludes source records with an explicit IRL cue tag from its game-only review queue but **does not establish that the tags are correct**.

## Workflow

1. Add candidate G10 game-only examples to the owner-policy semantic correction queue, prioritizing fully clear game-only cases and game/real minimal pairs.
2. Have review workers verify as-of-target context and separately flag real-world threats, doxxing, mixed-stakes, and ambiguous contexts. Keep source labels frozen until proper adjudication.
3. Propose `SAFE / ALLOW / review_priority NONE / no strike / no mute / support NONE` for examples confirmed **entirely in-game**. Do not auto-label every tagged item SAFE.
4. Preserve real-world blackmail as forbidden and annotate unresolved mixed cases `AMBIGUOUS_REVIEW / REVIEW` if defensible after review. The separate independent-review and release/split/source/privacy gates remain required for training authority.

**Scope boundary:** no player logs, private W20/W27, real-world holdouts, training, deployment, automatic punishments or PR merges have been authorized.
