# W00 unresolved decisions

Status: concise post-interview checklist.

These items do not invalidate the settled policy above. They are either genuinely unanswered policy edges or downstream calibration/implementation decisions that should not be invented by dataset workers.

## Remaining policy edges

1. **Discord bot DMs**
   - Whether DMs to/from the Discord bot are moderated and under which channel profile.

2. **Graphic self-harm disclosure**
   - Exact message action and alert timing for excessively graphic first-person disclosure before the player answers the safety check.

3. **Private explicit sexual content**
   - Ordinary non-explicit flirting is allowed in PMs and nude solicitation is prohibited, but the exact boundary for consensual explicit adult PM conversation is not frozen.

4. **Grooming with uncertain age**
   - Age claims are clues, not proof. Exact behavior when grooming-like secrecy/contact patterns exist but minor status is uncertain needs a later policy decision.

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

10. **English-only rule: channel coverage resolved; sanctions and ambiguity still open**
    - Owner approved (2026-10-08): BLOCK messages primarily non-English while ALLOWING occasional foreign words, short greetings, names and game terms.
    - Owner also confirmed **"everywhere"**: all currently moderated Minecraft public/global, other configured RoseChat channels, Minecraft /msg /tell /r private messages, and Discord public/general/gaming channels. Existing exempt Discord ticket/staff and other exempt channels remain excluded; Discord bot DMs remain undefined by the broader moderation policy.
    - Still unresolved: language-only strikes, mutes and staff escalation; handling of short/mixed-language content when predominant language cannot be assessed reliably.
    - The channel scope is now settled. No strike or mute is authorized by this message-action/scope decision alone. Detection and calibration must be validated before production use.

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
