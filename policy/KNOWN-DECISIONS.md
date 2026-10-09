# Known owner decisions

These are policy anchors already established before the formal interview. They are not a substitute for the full interview.

## English-only chat — owner message-action decision (2026-10-08)

- **BLOCK** a message when its content is **primarily non-English**, across **all currently moderated chat surfaces**: Minecraft public/global and configured RoseChat channels, Minecraft private player messages (/msg, /tell, /r), and Discord public/general and gaming channels. Owner confirmed "everywhere" on 2026-10-08.
- Existing Discord ticket, staff-only and other explicitly exempt channels remain exempt; the policy does not silently add Discord bot DMs, whose moderation remains undefined.
- **ALLOW** occasional foreign-language words or short greetings (for example `hola` or `bonjour`), player names, recognized game terms, or an otherwise English message containing a small foreign-language phrase.
- Do not interpret the rule as "block any non-English word." Mixed-language or short content without reliable evidence of which language predominates must not be automatically punished by a lexical guess.
- This is a **message-visibility rule**, not a finding of hate speech, harassment, doxxing, or dangerous behavior. Independently prohibited content still follows its own policy.
- **Owner-decided channel coverage:** all currently moderated surfaces noted above. **Not yet owner-decided:** language-only strike/mute/escalation rules. A previous no-strikes/no-mutes suggestion was *not* selected in the owner's answer. No strike or mute is authorized by this message-action decision alone.
- **Implementation guard:** language identification is not validated; G21 membership or non-ASCII characters alone are not evidence a message violates this rule. No production enforcement or bulk relabeling until detector validation and rollout authorization.

## Allow / generally allow

- **Owner decision (2026-10-08):** Blackmail/extortion involving **only Minecraft gameplay stakes** (e.g. threatening to reveal another player's Minecraft base coordinates unless paid diamonds or ancient debris) is fully allowed: ALLOW with no blackmail-related strike, staff ping, or mute. This applies in Minecraft and gaming Discord when the case is clearly only in-game. The same words involving real money, personal information, real-world harm or exposure remain prohibited real-world blackmail regardless of channel. Ambiguous mixed/unknown stakes require additional context or staff review. Does not override separately prohibited conduct.


- Ordinary Minecraft combat language should not be blocked merely because it sounds violent in isolation.
- Examples such as `im gonna kill you`, `im gonna stab you`, or `im gonna shoot you` are generally acceptable when they are plausibly gameplay.
- Explicit game context such as swords, bows, TNT, rounds, bases, respawning, or Minecraft builds should strongly favor gameplay interpretation.
- Mild toxicity such as `you suck` should be allowed.
- The system should tolerate the generally toxic tone common to Minecraft rather than over-moderating ordinary banter.

## Block

- `kys` / telling another person to kill themselves should be blocked.
- Clear real-world threats should be blocked.
- Split-message context counts: `im gonna stab you` followed immediately by `irl` must be treated as one semantic sequence and can cause both messages to be removed.
- A threat tied to real-world school/location/time context should be blockable even if no single message independently crosses a threshold.
- Real-world dangerous instruction requests are different from Minecraft crafting/gameplay questions.

## Review / care-sensitive

- First-person self-harm intent/disclosure should not be treated the same as abusive instructions directed at another user.
- Human review/alerting is preferred for credible self-harm intent rather than silently deleting the disclosure.

## System behavior

- AI moderation is an add-on and must fail open for chat availability.
- Automatic long punishments are not enabled until accuracy is demonstrated.
- Staff should be able to review decisions and correct them.
- Review corrections become high-value training data.
- Decisions must preserve structured evidence explaining which category, scores, context, and reason codes caused the action.
- Curiosity questions about religious/cultural practice (e.g. "is it true you can't eat pork? why not?", "why do you pray five times a day? just curious", "so you really believe all that stuff? like actually?", "do you wear that headscarf even when gaming lol") are SAFE/ALLOW — even skeptical or casually-worded variants. A single question is never a violation on its own. Watch subsequent conversation for escalation to mockery or harassment; flag only if it turns. (Owner decision 2026-10-07; applied to G17-0469 through G17-0472.)
- "check your dms" and similar DM-pivot phrases are never violations on their own — they are ordinary messages used for innocent reasons constantly. In harassment-conversation examples the target_index must point at the actual cruel/threatening message, not the pivot phrase. Label the conversation's actual content. (Owner decision 2026-10-07; applied to G27-0424.)
