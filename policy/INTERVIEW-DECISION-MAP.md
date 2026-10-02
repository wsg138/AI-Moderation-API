# W00 interview decision map

Status: consolidated after owner interview; Policy v1 is the normative draft.

This file is a compact trace of the major owner decisions. Earlier raw interview records remain evidence; when answers changed, the latest owner answer controls.

## Authority and rollout

- Full Minecraft + Discord moderation system, not a narrow OpenAI filter.
- AI may block/delete, create incidents/strikes, recommend/apply temporary mutes through EnthusiaStaff, and alert staff.
- AI never bans; staff own bans and serious final sanctions.
- Every automated mute alerts staff and provides an appeal/ticket path.
- Old RoseChat 2-strike/60-minute/30-day public-only mute contract is legacy, not Policy-v1 truth.
- Automatic punishments remain disabled until separately accepted.

## Surfaces

- Moderate Minecraft public chat and PMs.
- Moderate Discord public/general and gaming channels unless exempt.
- Discord tickets and staff-only channels are completely exempt and do not enter moderation context.
- Configurable additional exempt channels are allowed.
- Mirrored messages are one offense/event, not duplicates.
- Authoritatively linked Minecraft/Discord identities may provide cross-platform context; punishment histories remain platform-separated.

## Context

- Use replies, sender continuity, targets, participants, topic continuity, and relevant PM/public context.
- Split messages can combine; later context can retroactively delete earlier related messages.
- More than roughly 20 unrelated intervening messages normally breaks speculative linkage.
- Different speakers are not combined into one person's intent, but multi-sender harassment/dogpiling can form one incident.
- Missing context is not evidence of wrongdoing.

## Structured memory

- Persist relevant moderation memory across days when practical.
- Track player-global and target-specific history, incidents, consent/stop patterns, staff corrections, account links, and age clues.
- Current severity overrides friendly-history memory.
- Mild history decays faster; first mild harassment may effectively fade after ~7 days; repeat/severe history lasts longer.
- Safety/self-harm history is restricted and has zero punishment effect.
- Staff-overturned false positives lose all punishment effect but remain negative training examples.
- Accepted corrections affect system-wide moderation; normal staff require two-person confirmation, Admin+ may override immediately.
- Age claims are clues only; contradictory claims reduce trust.

## Harassment and consent

- Profanity/ordinary Minecraft toxicity is allowed.
- Repeated harassment can span days and targets.
- Mutual banter can lower sensitivity when both sides clearly consent.
- Repeated genuine stop requests end banter tolerance; mutual joking can later reset it.
- Private consent surveys are allowed; if one participant is uncomfortable, that controls.
- Coordinated dogpile participants: block + strike each.
- Uncoordinated mild pile-on: no automatic strike; rude messages may be blocked and target controls offered.
- Stronger target filtering blocks extra rude content only for that target, with no extra strike.
- /ignore means direct sender->ignored-recipient messages are not moderated for that relationship.

## Violence and threats

- Generic Minecraft violence has a strong gameplay prior and is usually allowed.
- Discord general does not get that prior; Discord gaming can.
- Explicit real-world cues, school/work/location/time/address/proximity/delivery context can flip to real-world threat.
- Immediate connected IRL continuation can retroactively block related messages and may justify ~7-day mute.
- Severe credible real-world threat: block + strike + urgent staff ping.
- Minecraft "burn your house" alone remains gameplay-ambiguous/allow.
- "Outside your house right now" is block + strike.
- Sending an explosive to a house is block + review by default; strike when clearly real-world.
- Recent staff-confirmed serious threats may trigger a target safety check (working default ~24h).

## Self-harm

- Directed self-harm instruction/encouragement: block; directed shorthand such as KYS creates a strike.
- Credible first-person disclosure generally remains visible and starts a support flow, not punishment.
- Negative safety response: log, no urgent ping.
- Positive danger response: ping staff and continue supportive information.
- Third-party concern triggers a broad safety check for the sender/everyone around them; help request leads to support info + staff ping.
- Recent safety history does not bias later gameplay-death language.
- Repeated low-risk prompts may cool down; escalation can retrigger.

## Hate/slurs

- Any actual slur: block + strike even quoted, condemned, joking, reclaimed, abbreviated, masked, misspelled, or obfuscated.
- Non-derogatory reference names like "the n-word" may be allowed.
- Slur severity affects escalation; serious/repeated racist slur behavior can reach ~14-day mute.

## Sexual/minor

- Public NSFW/sexual content is blocked.
- Ordinary non-explicit flirting is blocked in public with a prompt to move to PM.
- Ordinary non-explicit flirting is allowed in PM.
- Nude solicitation is always block + strike.
- Reliably known minor + sexualized comment: block + strike.
- Reliably known 16-year-old + nude solicitation: block + 7-day mute + staff alert.
- Minor consent does not override the rule.
- Age self-report alone is never proof.

## Doxxing/blackmail/grooming

- Apparent doxxing: block + strike + urgent staff ping, initially no automatic mute because fake doxxing exists.
- Confirmed real doxxing: 30-day mute, staff alert, appeal path, regardless of target preference.
- Clear blackmail: block/delete related messages + urgent review + mute pending review.
- Clear grooming involving reliably known minor: block, staff alert, severity-adjusted temporary mute anchor ~7 days.
- AI never bans.

## Dangerous instructions

- Minecraft crafting/game mechanics: allow.
- Actionable real-world explosive construction request: block.
- Benign high-level historical discussion: allow.
- No automatic strike/mute is attached to the simple dangerous-instruction example.

## Player controls and review

- REVIEW is not one overloaded state: visibility, review priority, evidence/strike, containment, and human punishment are separate dimensions.
- Every automated mute alerts staff.
- Accepted human corrections are retained as training data and remove incorrect punishment effects.
