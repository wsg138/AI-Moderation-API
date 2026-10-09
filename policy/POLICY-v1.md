# Enthusia AI Moderation Policy v1

Status: proposed owner policy from W00; requires coordinator review before dataset generation.

This policy describes the desired end state. Existing RoseChat punishment behavior remains legacy production behavior until the new system is implemented, tested, and separately accepted. Automatic punishments remain disabled during calibration.

## 1. Policy model

Every moderation decision has separate dimensions:

1. **Semantic interpretation** — what the message or incident means.
2. **Message action** — allow/remain visible or block/delete.
3. **Review priority** — none, normal queue, or urgent staff ping.
4. **Evidence / strike recommendation** — no strike, incident evidence, or strike.
5. **Automated containment** — none or a temporary mute recommendation/application through EnthusiaStaff.
6. **Human punishment** — staff-only final sanctions, including bans.

The AI moderation service must never directly own bans. EnthusiaStaff owns authoritative cases, strikes, mutes, appeals, and punishment state.

## 2. Core principles

- Be tolerant of ordinary Minecraft gameplay language, profanity, and low-level banter.
- Do not let generic safety-model scores override obvious Minecraft context.
- Catch clear real-world threats, self-harm abuse, slurs, serious harassment, sexual/minor violations, doxxing, blackmail, grooming, and dangerous real-world instruction requests.
- Use ambiguity and review honestly. Missing context is not proof of wrongdoing.
- Later context may change an earlier interpretation and may justify retroactive deletion of related messages.
- Fail open for chat availability when the moderation service, classifier, or long-term memory is unavailable.
- Do not invent player history when durable memory is unavailable.
- Preserve structured, reviewable evidence rather than hidden free-form reasoning.
- Human corrections are high-value training data.

## 3. Moderated and exempt surfaces

### Moderated
- Minecraft public/global and other configured RoseChat channels.
- Minecraft private player messages such as /msg, /tell, and /r.
- Discord public/general channels unless configured exempt.
- Discord gaming channels unless configured exempt.

### Exempt
- Discord ticket channels.
- Discord staff-only channels.
- Any additional explicitly configured exempt Discord channel.

Exempt content is not classified, does not generate moderation incidents, and is not used as semantic context for later moderated messages.

Discord DMs involving the bot are not yet defined by this policy.

### Mirrors
Minecraft/Discord mirrors are one canonical moderation event. Do not double-count mirrored copies in context, harassment history, or strikes. Linked copies may be deleted together when the canonical event is blocked.

### English-primary chat rule (owner update 2026-10-08)

**Message action on every currently moderated surface (owner confirmed
"everywhere", 2026-10-08):** Minecraft public/global and configured RoseChat
channels; Minecraft private player messages (/msg, /tell, /r); Discord public,
general, and gaming channels unless exempt. The established Discord staff-only,
ticket, and separately exempt channel exclusions still apply: exempt content is
not classified. Discord bot DMs remain undefined rather than being silently
added. Minecraft/Discord mirror events count only once.

**BLOCK** a message that is **primarily non-English**. ALLOW occasional foreign
words, short greetings (such as `hola` and `bonjour`), player names, recognized
game terms, and messages otherwise primarily in English with minor
code-switching. A single greeting is not a violation solely because it is
not an English word. Do not interpret this as a ban on every foreign word.

A short or mixed-language example that cannot be judged reliably must not
be automatically blocked on a crude script/keyword test. Language-only
enforcement is conceptually separate from the semantic detection of hate,
harassment, threats, doxxing, grooming, and self-harm; those rules still
apply independently.

**Owner consequence decision (2026-10-08): for a language-only violation,
just block/delete the offending message. Do not issue strikes, mutes,
punishment, automatic staff alerts, or repeated-violation escalation solely
because of the language rule.** Repeated language-only violations remain
message-block-only, not a new sanction category. A message that separately
violates a serious safety or misconduct rule is still evaluated under that
independent rule. The applicable moderated chat surfaces are confirmed above.

An English-primary language detector has not been validated or enabled
for production.

This is a versioned message-action decision, **not training approval** for
any G21 synthetic labels; G21 is a synthetic source-batch hint and not
a reliable language classifier.

## 4. Context and incident linkage

Relevant context may include:
- same-sender recent messages;
- target/recipient relationship;
- reply/reply-to links;
- recent same-conversation messages;
- recent PM/public messages between the same participants;
- related messages across moderated scopes;
- authoritatively linked Minecraft/Discord identities;
- structured player and relationship history.

Context must not become unrestricted history. Require a meaningful participant, target, reply, topic, or incident relationship.

### Split messages
Split messages can form one semantic act. Immediate same-sender continuation is strong evidence. At longer gaps, consider intervening messages, replies, topic continuity, target changes, and whether the later fragment naturally refers back.

If more than roughly 20 unrelated messages separate fragments, do not connect them merely because they could form a violation.

Different speakers must not be stitched together as if they expressed one person's intent unless the incident semantics genuinely require multi-speaker aggregation, such as coordinated dogpiling.

### Retroactive deletion
Later context may cause an earlier related message to be deleted. The system should preserve related message IDs for this purpose.

## 5. Structured player and relationship memory

Persistent moderation memory is desired when technically practical. It should live in durable structured storage rather than in model weights.

Useful memory includes:
- recent incidents and their categories/severity;
- strike/evidence history;
- target-specific harassment history;
- repeated stop/unwanted-contact patterns;
- mutual-banter/consent state;
- staff-confirmed or staff-overturned decisions;
- active moderation preferences such as stronger target filtering;
- authoritative account linkage;
- age claims with provenance/confidence;
- recent safety-check state in a restricted safety area.

### Decay
History must decay rather than permanently branding a player.

- A first/lone mild harassment incident may effectively stop mattering after roughly 7 days.
- Repeated mild behavior remains relevant longer.
- Severe confirmed threats/doxxing remain relevant substantially longer and decay gradually.
- Exact decay curves are calibration/implementation details.

### Corrections
When an AI decision is overturned:
- remove its punishment/escalation effect;
- keep the example as a human-confirmed negative training example;
- preserve enough context to learn from it;
- apply the accepted correction system-wide rather than only to one player.

Ordinary staff corrections require agreement from two staff members. Admins and above may override immediately.

### Self-harm memory separation
Safety/self-harm history must not contribute to punishment reputation and must not bias unrelated moderation. It belongs in a separate restricted safety area.

### Age memory
A player's age statement is a clue, not proof. Repeated contradictory claims reduce trust in that player's self-reported age. Treat age as authoritative only with strong, reliable supporting evidence or a genuinely authoritative source.

## 6. Gameplay violence and real-world threats

### Minecraft gameplay prior
Ordinary Minecraft violence language is generally allowed when plausibly gameplay, including generic threats to kill/stab/shoot during play and game-specific references to TNT, bases, respawning, rounds, weapons, or builds.

A generic Minecraft statement equivalent to "I'm going to kill you" is allowed even without immediate PvP context.

### Discord
Discord general does not receive the same automatic gameplay prior. A generic violent threat without game context is blocked but does not automatically create a strike.

Discord gaming may allow the same wording when active game context makes the meaning clearly in-game.

### Real-world cues
Real-world school, workplace, location, delivery, proximity, time, address, or explicit IRL cues increase real-world threat interpretation.

Examples:
- a connected threat followed immediately by an explicit IRL cue: block related messages; a clearly connected real-world threat may receive about a 7-day mute;
- a threat tied to school/time/location: block;
- a severe credible threat with address/proximity/weapon context: block + strike + urgent staff ping;
- a standalone Minecraft threat to burn someone's "house" with no other real-world cue: allow as Minecraft-ambiguous;
- a statement that the sender is outside the target's house right now: block + strike;
- a threat to send an explosive item to a house: block + review by default; add a strike when context clearly establishes real-world targeting.

Private real-world threats use the same safety policy as public threats.

### Victim safety check
A staff-confirmed serious recent threat may trigger a private safety check for the target. Working recency default: about 24 hours. The flow should ask whether the target feels safe/needs help and provide useful emergency/support information when appropriate.

## 7. Harassment, toxicity, consent, and player controls

### Low-level toxicity
Profanity alone is not a violation. Ordinary Minecraft toxicity such as telling someone they are bad at the game is allowed.

### Incident-level harassment
Harassment may be a multi-message or multi-day incident. Track:
- repeated same-sender targeting;
- repeated unwanted contact;
- escalation in tone;
- target-specific history;
- multiple senders targeting one person;
- whether the target asks the sender to stop;
- mutual banter/consent.

A prior confirmed harassment incident may cause later borderline behavior toward another target to reach review sooner, but current-target evidence is still required.

### Mutual banter
If both players clearly participate willingly, the system may be more permissive. A single isolated "stop" does not automatically prove consent ended; use evidence.

Repeated/consistent stop requests that are ignored are strong evidence the behavior is unwanted. If the players later clearly return to mutual joking, the relationship state may reset.

The system may privately survey involved players about whether they are comfortable. If one says the behavior is fine and the other says they are uncomfortable, the uncomfortable player's answer controls the consent state.

Current severe behavior always overrides friendly-history memory.

### Dogpiling
- Coordinated dogpiling: block participating messages and give each participating player a strike.
- Uncoordinated mild negative pile-on: do not automatically strike every participant. Rude messages may be blocked, and the target may be offered player controls.

### Example containment anchors
- lighter repeated harassment that crosses the incident threshold: around 7 days;
- severe sustained targeted harassment: around 21 days;
- excessive lower-level "die" spam: around 24 hours.

These are policy anchors, not a complete arithmetic strike table.

### Stronger target filtering
A target may opt into stronger moderation against a sender instead of fully ignoring them. In that mode:
- standard serious-category rules still apply normally;
- additional rude/unfriendly content that would otherwise be tolerated may be blocked only for that target;
- those extra blocks do not create strikes by themselves;
- the stricter relationship state may persist until mutual friendliness clearly resumes.

### /ignore
If a recipient ignores a sender, direct messages sent to that ignored recipient are not moderated for that ignored relationship. /ignore is a delivery/user-control boundary rather than a new punishment rule.

## 8. Staff-targeted abuse

Targeted abuse toward staff is stricter than ordinary player banter. Direct targeted staff abuse is BLOCK + strike.

Good-faith criticism, appeals, and disagreement with staff decisions are not automatically abuse merely because they criticize staff.

## 9. Self-harm and directed self-harm abuse

### Directed abuse
Telling another person to kill themselves is BLOCK + strike.

A phrase equivalent to "go die":
- clearly gameplay-only: allow;
- clearly real-world: block + strike;
- unclear: block without strike + normal review.

A death wish that remains ambiguous can be blocked without a strike unless later context establishes real-world intent.

### First-person disclosure
Credible first-person self-harm disclosure is a safety/support event, not a punishment event.

Default:
- allow/remain visible unless excessively graphic/inappropriate;
- trigger a supportive safety check;
- if the player says they are okay: log/record without urgent ping;
- if the player says they may hurt themselves or someone else: ping staff and continue a supportive flow with emergency/help-line/trusted-person options.

Indirect statements about not wanting to be alive enter the same safety flow.

Obvious later gameplay-death language must not become more suspicious merely because the player had a safety event days earlier.

A recent completed safety check may suppress repeated low-risk prompts for a cooling-off period, but genuinely escalating language should trigger the flow again.

### Third-party concern
When a player reports concern that someone else may be at risk, use a broad safety check asking whether the sender and everyone around them are okay and whether help is needed. If help is needed, provide useful emergency/support information and ping staff.

### Game/joke self-reference
A gameplay joke using self-harm shorthand may still be blocked under owner policy. Repeated attempts to evade that block can trigger another safety check.

Exact handling of graphic self-harm disclosure before the safety response remains unresolved.

## 10. Hate, discrimination, and slurs

Racist, sexist, bigoted, discriminatory, or identity-targeted attacks are blocked.

Any actual slur is BLOCK + strike, including:
- direct use;
- quote/report/counterspeech;
- joke;
- reclaimed/self-reference;
- masked/misspelled/abbreviated use;
- deliberate obfuscation/evasion.

A reference such as "the n-word" may be allowed when it refers to the term rather than acting as a derogatory substitute.

Slur severity affects escalation. Less severe slurs may escalate more gradually; serious/repeated racist slur behavior can justify about a 14-day mute. The system should preserve category/severity rather than relying on one generic counter.

Accidental substring/lexical false-positive handling remains a dataset/calibration edge and must not be implemented as naive substring matching.

## 11. Sexual content, flirting, and minors

### Public chat
NSFW/sexual content is blocked in public chat.

Ordinary non-explicit flirting between unknown-age players, such as a simple compliment or asking to date, is blocked in public chat with a warning to move the conversation to private messages.

### Private messages
Ordinary non-explicit flirting is allowed in PMs. PMs are still moderated for separately prohibited sexual content/solicitation and safety violations.

### Sexual solicitation
A solicitation for nude images is always BLOCK + strike regardless of age.

### Known/reliably evidenced minor
When reliable context establishes the target is a minor:
- sexualized comments are BLOCK + strike;
- the minor saying they are comfortable does not make the behavior acceptable;
- soliciting nude images from a known 16-year-old is an immediate block with a 7-day mute and staff alert.

Age self-report alone is not proof.

The exact boundary for consensual explicit adult PM content and grooming behavior when age is uncertain remains unresolved.

## 12. Doxxing, blackmail, grooming, and severe safety violations

### Doxxing
Apparent doxxing:
- BLOCK;
- strike;
- urgent staff ping;
- no automatic mute based only on the detector because fake doxxing exists.

When there is a clear apparent target, the system may privately ask whether the information is real.

Confirmed real doxxing:
- 30-day automated mute;
- staff alert;
- normal appeal/ticket path;
- punishment applies even if the target says they do not personally want further punishment.

If the target says the information is fake, whether the initial strike is automatically removed remains unresolved.

### Blackmail

**Owner clarification (2026-10-08): Blackmail restricted entirely to in-game Minecraft assets or gameplay consequences is ALLOWED.** The policy does not punish players for threatening to disclose another player's Minecraft base coordinates or secret base, steal/grief an in-game base, or otherwise leverage only Minecraft items, currency, builds, or game information to demand in-game payment. This applies in Minecraft chat and Discord when the context clearly establishes the exchange is exclusively in-game. Such game-only coercion is **ALLOW; no strike, mute, or staff alert for blackmail alone**, even when the wording resembles real-world extortion. In-game base coordinates are not a real-world street address.

**Real-world blackmail/extortion remains prohibited**, even when the demand is posted in Minecraft or gaming Discord. Examples include coercion involving real money, actual names/addresses/contact details, private personal photos, real-life safety, or other real-world exposure, threats, or consequences. Clear real-world blackmail/extortion:
- block/delete related messages;
- urgent staff review;
- temporary mute pending staff review;
- tell the player how to appeal through a ticket.

If it is unclear whether the threatened material or demanded payment is in-game or real-world, seek additional context / staff review rather than assume the message is a real-world violation. The game-only allowance does not exempt separate violations (e.g., threats of real-world harm, doxxing, prohibited hate speech or directed self-harm abuse). Exact containment duration for **real-world** blackmail is not yet frozen.

### Grooming
Clear grooming/secrecy behavior involving a reliably known minor is blocked, may justify a severity-adjusted temporary mute (owner anchor about 7 days), and alerts staff. Staff alone decide any ban.

The policy does not assume age merely because a player claims one.

## 13. Dangerous real-world instructions

Minecraft crafting/gameplay questions are allowed when clearly about game mechanics.

Actionable real-world explosive-construction requests are blocked. A simple real-world dangerous-instruction request does not automatically create a strike/mute under current owner decisions.

Benign historical/high-level discussion that does not request actionable construction steps is allowed.

Broader dangerous-instruction domains beyond the interviewed explosive examples remain a follow-up policy area.

## 14. Review, appeals, and staff corrections

### Review priority
- **NONE** — no special staff review.
- **NORMAL** — queue for staff review; no urgent interruption.
- **URGENT** — immediate staff ping.

### Automated mutes
Every automated mute alerts staff.

Players must receive a clear appeal/ticket path after an automated mute.

### Human corrections
Accepted staff corrections:
- remove incorrect punishment effects;
- retain the original event and correction as supervised training/evaluation data;
- influence system-wide behavior rather than only the corrected player;
- remain auditable.

Normal staff require two-person agreement to finalize a correction. Admin+ may finalize/override immediately.

## 15. Failure behavior

Chat must fail open when the AI service is unavailable or too slow.

If long-term player memory is unavailable:
- continue moderating with current/recent context;
- do not assume historical incidents, age, consent, or relationship state;
- do not invent missing facts.

Normal EnthusiaStaff functionality must remain independent of AI uptime.

## 16. Public-rule alignment

Policy v1 intentionally aligns with the current public rules on:
- quoted/masked slurs being prohibited;
- profanity being allowed when not harassment;
- threats, targeted harassment, sexual harassment, and repeated unwanted contact being prohibited;
- doxxing, blackmail, grooming, credible threats, malicious/illegal safety violations being serious staff matters.

The public rules' "zero tolerance/permanent ban" language describes possible human enforcement. It does **not** authorize the AI service to ban. AI may block, strike, contain temporarily, and urgently alert staff; staff decide permanent sanctions.

## 17. Dataset semantics

The semantic dataset should preserve both:
- contextual semantic truth; and
- owner-desired policy outcome dimensions.

Identical text may map differently by platform/channel/context. Dataset workers must include minimal pairs for:
- Minecraft vs Discord general vs Discord gaming;
- gameplay vs real-world threat cues;
- split-message timing/linkage;
- house/base/home ambiguity;
- same-sender vs multi-sender incidents;
- mutual banter vs repeated stop requests;
- PM/public context;
- slur quote/reference/obfuscation;
- self-harm instruction vs disclosure vs third-party concern;
- public flirting vs private flirting;
- age clue vs reliable minor evidence;
- apparent vs confirmed doxxing;
- corrected false positives.

## 18. Superseded legacy behavior

Do not encode these as Policy-v1 constraints:
- fixed two strikes within 60 minutes;
- fixed 30-day public-only mute;
- PMs remaining unmoderated;
- old OpenAI score thresholds as owner policy.

They are legacy calibration/rollout behavior only.
