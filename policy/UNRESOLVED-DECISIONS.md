# W00 unresolved decisions

Status: concise post-interview checklist.

These items do not invalidate the settled policy above. They are either genuinely unanswered policy edges or downstream calibration/implementation decisions that should not be invented by dataset workers.

## Remaining policy edges

1. **Discord bot DMs**
   - Whether DMs to/from the Discord bot are moderated and under which channel profile.

2. **Graphic self-harm disclosure**
   - Exact message action and alert timing for excessively graphic first-person disclosure before the player answers the safety check.

3. **Private explicit sexual content**
   - Owner clarified 2026-10-09: adult-compatible private romantic/intimate discussion and some isolated picture requests may be ALLOW; the old universal private-request BLOCK rule is superseded. Exact consent evidence, explicit-content threshold, and sanction matrix still need case-sensitive adjudication; no automatic strike.

4. **Grooming with uncertain age**
   - Owner clarified 2026-10-09: rare-event false positives are especially costly; a generic private picture request, unknown age, or one age clue alone must not imply grooming. Track meaningful subsequent escalation, pressure, coercion, secrecy, and exploitation cues. Exact thresholds for BLOCK vs staff REVIEW, and verified age evidence, still need evaluation.

5. **Broader dangerous-instruction domains**
   - Explosive examples are covered. Weapons, poisons, malicious files, and other real-world dangerous instruction classes need explicit dataset/policy treatment rather than assumption.

6. **Doxxing false alarm cleanup**
   - Apparent doxxing initially creates a strike. If the apparent target says the information is fake, the policy has not explicitly said whether that strike is automatically reversed.

7. **Threat containment matrix**
   - Several anchors exist (including ~7-day clear real-world threat examples and urgent handling for severe threats), but there is no complete severity-to-duration table.

8. **Real-world blackmail containment duration**
   - Only real-world blackmail is muted pending staff review; exact maximum/default duration is not frozen. Gameplay-only blackmail is allowed under owner decision 2026-10-08.

9. **Accidental slur lexical matches**
   - Actual/obfuscated slurs are blocked and struck. Naive substring false positives must be avoided, but exact lexical disambiguation examples still belong in dataset calibration.

10. **English-only rule: action, coverage, and no-penalty consequences resolved; detection ambiguity remains**
    - Owner approved (2026-10-08): BLOCK primarily non-English messages; ALLOW occasional foreign words, greetings, names, recognized game terms, and English-primary text with minor code-switching.
    - Owner confirmed **"everywhere"**: all currently moderated Minecraft public/global, configured RoseChat, private /msg /tell /r, and Discord public/general/gaming channels. Previously exempt Discord tickets/staff/other exempt channels remain outside scope; Discord bot DMs remain undefined.
    - Owner confirmed **"just block it"**: BLOCK/DELETE a language-only violating message, with **no strike, mute, other punishment, staff alert, or repeat-violation escalation** for that rule alone. Independent serious violations still follow their own policy.
    - Owner clarified 2026-10-09: a substantive standalone foreign-language word or sentence is blocked even if short; familiar greetings like `hola` are allowed. Remaining implementation/calibration: validated assessment of short/ambiguous content, not language keyword guessing. This does not authorize live deployment or admission of G21 synthetic labels.

## Downstream implementation/calibration, not owner-policy blockers

- Exact player-memory decay curves beyond the policy anchors.
- Exact survey/check-in cadence for harassment consent.
- Exact classifier confidence thresholds.
- Exact retrieval strategy for structured memory.
- Whether an internal aggregate risk score is useful; explicit evidence must remain available regardless.
- Exact copy/layout of self-harm and target-safety GUIs.
- Exact configured list of non-ticket/non-staff exempt Discord channels.
- How accepted staff corrections are applied immediately system-wide without unsafe one-example model updates.
- Runtime timeouts, queue limits, and context-buffer sizes.
