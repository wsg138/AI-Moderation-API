# W00 current-state coordinator briefing

**Repository:** `wsg138/AI-Moderation-API`  
**Worker:** W00 — Owner moderation-policy interview  
**Issue:** #1  
**Branch:** `w00/policy-interview`  
**Status:** interview in progress; Policy v1 is not yet frozen.

This briefing is intentionally self-contained. Live GitHub remains authoritative, but W00 should use this as the coordinator's current interpretation of the architecture, legacy-vs-new boundaries, already-recorded owner decisions, and the next interview phase.

Do **not** turn this document into Policy v1 without continuing the owner interview. Where this document says “unresolved,” ask the owner rather than inventing an answer.

---

## 1. What W00 is supposed to define

W00 should define the **owner-facing moderation policy**, not the implementation of every downstream subsystem.

Policy v1 should capture five separate layers instead of collapsing everything into one label:

1. **Semantic interpretation**
   - what the message/conversation means;
   - e.g. gameplay violence, real-world threat, low-level harassment, severe harassment, self-harm instruction, self-harm disclosure, hate, sexual/minor, dangerous real-world instruction.

2. **Message action**
   - should the content remain visible, be removed/blocked, or remain visible while being sent for review?

3. **Review / staff-notification policy**
   - no review;
   - normal/non-urgent review;
   - urgent staff ping;
   - incident record only.

4. **Automated enforcement recommendation**
   - no strike;
   - strike/evidence recommendation;
   - temporary containment/mute recommendation;
   - severity/duration preference where the owner explicitly gives one.

5. **Human punishment boundary**
   - what staff, rather than the AI system, may ultimately decide.

W00 **should** interview/document:
- semantic labels;
- ALLOW/BLOCK behavior;
- review priority;
- context interpretation;
- reason codes;
- cross-message incident interpretation;
- private/public/platform/channel differences;
- channel exemptions;
- whether an event should count as a strike/evidence event;
- owner-desired automated mute/containment behavior;
- the self-harm trigger/support boundary;
- the owner’s desired appeal/ticket behavior after an automated mute;
- which content classes require staff alerts.

W00 should **not** design:
- the Java/Python/TypeScript implementation;
- HTTP endpoint details;
- SQL tables;
- exact GUI layout;
- queue/thread settings;
- final classifier architecture;
- final EnthusiaStaff sanction implementation.

If the owner gives operational details such as “7-day mute,” record them as policy requirements. Do not discard them merely because another worker owns the implementation.

---

## 2. Old RoseChat punishment contract is legacy, not a Policy-v1 constraint

The old/current RoseChat rollout contract is:

- enforcement-level DELETEs can create strikes;
- 2 strikes;
- rolling 60-minute window;
- fixed 30-day **public-chat-only** mute;
- PMs remain available;
- automatic punishments are currently disabled.

Treat that as **legacy production behavior that the new central moderation project may replace after acceptance**.

W00 does **not** need to force new owner policy into the old 2-strike/30-day/public-only scheme.

Important transition rule:

- production keeps old safe behavior until the new system is implemented, tested, and separately accepted;
- Policy v1 should describe the desired end state;
- downstream workers will handle migration/compatibility;
- automatic punishments remain disabled during model/runtime calibration.

So yes: stop treating “2 strikes -> 30-day public mute” as a policy constraint.

---

## 3. Punishment authority boundary

The intended future architecture is conceptually:

```text
AI moderation service
  -> semantic result
  -> message action
  -> structured evidence
  -> enforcement / containment recommendation
  -> review priority
            |
            v
EnthusiaStaff
  -> validates/records incident
  -> owns strikes/cases/punishments
  -> applies authorized mute
  -> staff may later issue a ban
```

The AI service must **never directly own bans**.

The owner has already said automated chat moderation may delete messages, create strikes/evidence, mute, and alert staff, but **staff alone decide bans**.

A “zero-tolerance / permanent-ban” rule on the public website therefore does not mean the classifier itself bans. It can mean:

```text
AI: BLOCK + URGENT REVIEW + containment recommendation
EnthusiaStaff: temporary automated mute if policy allows
Staff: decide whether permanent ban is appropriate
```

W00 should interview the owner about the desired policy result, while preserving this authority split.

---

## 4. Intended moderation scope

### Already decided / intended

The central service is intended to moderate:

- Minecraft public/global chat;
- other moderated RoseChat channels;
- Minecraft private player messages such as `/msg`, `/tell`, `/r`;
- Discord public/general channels that are not exempt;
- Discord gaming channels that are not exempt.

The owner has explicitly decided:

- Minecraft private messages are moderated;
- recent private-message context may influence a public-chat decision;
- staff may see private-message context that was actually used as moderation evidence;
- Discord ticket channels are **not moderated at all**;
- some Discord channels must be configurable as completely exempt.

These decisions fit the intended architecture.

### Still unresolved

Do **not** assume an answer yet for:

- Discord staff-only channels;
- Discord DMs to/from the bot;
- specific non-ticket Discord categories that should be exempt;
- whether a staff-only moderation/evidence channel should ever be ingested as context.

Ask the owner only where the answer materially affects policy.

### Mirrored Minecraft <-> Discord messages

Mirrored messages should not be treated as two independent offenses.

The intended integration behavior is:

- moderate the canonical/original message once;
- preserve linkage to any mirrored copy;
- use the same decision/evidence;
- do not double-count the mirror in harassment/strike/context history;
- if deletion is required, integrations may remove the linked mirror too.

---

## 5. Cross-scope context: desired end state vs W01 today

W01 / PR #18 currently proposes bounded context using:
- same platform/scope/channel partition;
- same-sender recent messages;
- same-channel recent messages;
- reply relationships;
- a bounded time window.

That is a **runtime foundation proposal**, not a permanent policy limit.

Policy v1 may require richer context than W01 currently implements. Do not weaken the owner’s policy merely to fit W01.

The desired architecture can eventually support relevant context across:

- Minecraft PM -> Minecraft public chat;
- Minecraft public -> PM;
- multiple senders targeting one victim;
- one sender’s related messages spread across multiple moderated scopes;
- related Discord channels where policy explicitly permits it;
- linked/mirrored Minecraft/Discord activity when identity/linkage and incident relevance are reliable.

However, context must not become “everything this person said everywhere.”

Use these principles:

- require a meaningful participant/target/topic relationship;
- prefer explicit reply/reply-to or direct participant linkage;
- prefer same-sender continuity;
- respect channel exemptions/privacy boundaries;
- do not cross an exempt channel into moderation context;
- deduplicate mirrors;
- do not infer cross-platform identity unless there is an authoritative link;
- unrelated channel history must not bleed into a decision.

W00 should define **when cross-scope context is semantically legitimate**. W01/W13/W14 can later implement the required routing.

---

## 6. Context-window design

The old RoseChat values:

- 6 previous messages;
- 3 following messages;
- 45 seconds max age;
- 1.5-second follow-up delay;

are legacy calibration/defaults, not sacred policy.

W01 PR #18 currently proposes defaults around:
- 45-second context window;
- 5 same-sender messages;
- 8 same-channel messages;
- bounded retention per scope.

Again, these are implementation defaults.

The owner has already added an important semantic rule:
- if more than roughly 20 messages separate two phrases, do not connect them merely because they could form a threat.

W00 should absolutely interview/contextualize:

- time distance;
- intervening message count;
- same-speaker weighting;
- reply relationships;
- target/victim relationships;
- intervening conversation;
- topic continuity;
- whether the target responded;
- whether the second message can naturally refer to the first;
- whether multiple senders form one incident.

Do not over-focus on one exact second/message threshold. Capture owner boundaries and examples; later calibration can set technical windows.

---

## 7. Message timing and retroactive deletion

The enduring product requirement is:

- keep the live chat hold short and bounded;
- fail open if the AI service is unavailable/too slow;
- allow late decisions to remove an already-broadcast message;
- allow later context to retroactively remove earlier related messages.

Current RoseChat uses a 200 ms maximum chat hold. Earlier design discussion allowed roughly 200–300 ms. W01 PR #18 currently proposes a 250 ms API request deadline and 150 ms classifier timeout.

Those numbers are **runtime tuning**, not W00 policy.

W00 should assume:

- the runtime can block the current message when a result arrives in time;
- the runtime can later remove current/prior related messages when context changes;
- `related_message_ids` exist for this purpose.

Interview the **policy outcome**, not the exact milliseconds.

---

## 8. Discord policy differences are first-class context

Yes: platform and channel type must be first-class moderation context.

Already recorded:

- Minecraft `im gonna kill you` => owner allows it even without explicit immediate PvP context;
- Discord general `im gonna kill you` without gameplay context => owner blocks it;
- Discord gaming `im gonna fucking kill you next round` while actively playing a game => owner allows it.

Dataset workers must not invent inconsistent assumptions.

W00 should freeze a conceptual channel-profile vocabulary. It does not have to use these exact enum names, but it should cover:

- Minecraft public/game chat;
- Minecraft private message;
- Discord general/public;
- Discord gaming;
- Discord staff-only (**owner decision still needed if behavior differs**);
- Discord ticket = exempt;
- generic configurable exempt channel.

Prefer metadata/profile semantics over hard-coding a policy to literal channel IDs.

---

## 9. Exempt channels and staff content

The owner explicitly decided:

- all Discord ticket channels are exempt from automated moderation;
- some additional Discord channels can be configured exempt.

Coordinator interpretation of **EXEMPT**:

- do not send message text to the moderation service;
- do not classify it;
- do not use it as semantic context for later moderated messages;
- do not create moderation strikes/events from it.

This is the cleanest interpretation of “not moderated at all” and prevents ticket evidence/private support content from leaking into unrelated decisions.

Staff-only channels are **not automatically exempt** unless the owner says so. Ask if needed.

The Discord integration should own the configured exemption allowlist; the classifier should not learn “channel ID 123 is exempt.”

---

## 10. Private-message privacy and retention

Current owner direction:

- PMs are moderated;
- PMs may be used as relevant context;
- staff may see PM context that the moderation system used;
- all messages/results submitted to the central AI system should be saved privately so they can later contribute to training/review.

Repository boundary:

- raw production messages do **not** go to this public GitHub repository;
- raw production events belong in the private runtime datastore;
- GitHub receives synthetic data plus deliberately reviewed/redacted curated exports.

Staff-review display should follow **minimum necessary context**:

- show PMs that materially contributed to the decision/incident;
- do not dump unrelated private conversations into a review simply because they exist in storage.

Still unresolved:
- exact retention period for raw production PMs/messages;
- whether/when old raw data is purged;
- whether specific categories require longer evidence retention.

W00 can record that this data-governance question remains unresolved. It does not need to invent a retention duration.

---

## 11. REVIEW should not be overloaded into one behavior

W00 is correct that one word, `REVIEW`, is not enough.

Policy should conceptually separate:

### Message action
- ALLOW / remain visible;
- BLOCK / delete;
- possibly retroactive deletion of related messages.

### Review priority
- NONE;
- NORMAL / queue;
- URGENT / ping staff.

### Containment recommendation
- NONE;
- temporary mute / mute-pending-review where the owner explicitly wants it.

### Record behavior
- no special incident;
- durable incident/evidence record;
- safety check/support flow.

Examples already recorded:

- repeated harassment can remain visible but become a review incident;
- unknown-intent `go die` is blocked and sent for review without a strike;
- doxxing gets blocked + staff ping;
- clear blackmail may be deleted + muted pending review + staff ping;
- self-harm disclosure may remain visible and trigger a safety check;
- a negative self-harm check response is logged without an urgent ping;
- a positive check response pings staff.

W00 should capture these dimensions separately. W01/W15 may later change API/schema accordingly.

---

## 12. Self-harm policy scope

Yes: W00 should specify the **behavioral policy boundary** enough that dataset workers and later runtime workers know what distinctions matter.

W00 does **not** need to design the final GUI wording or medical-support content.

The existing two labels are probably too coarse for the owner’s already-recorded behavior. Policy v1 should distinguish, at minimum, concepts like:

- abusive self-harm instruction/encouragement directed at another person;
- genuine first-person disclosure/intent;
- graphic/inappropriate self-harm content;
- third-party concern/reporting;
- game/joke false-positive language;
- coercive self-harm abuse.

Already recorded owner behavior:

- `kys` directed at another player => block + strike;
- credible first-person disclosure usually remains visible;
- credible disclosure triggers a safety/check-in flow;
- “No, I’m okay” => log/record, no urgent staff ping;
- “Yes, I might hurt myself/someone” => ping staff and continue supportive flow;
- graphic/inappropriate self-harm content may still be removed;
- repeated attempts to evade a self-harm block can trigger another safety check;
- `if i lose this fight im gonna kms` => owner said block, with repeated bypass attempts triggering another check.

Do not re-ask settled examples unless you are testing a genuinely different boundary.

---

## 13. Harassment is an incident-level problem

Yes: the intended system must support **incident-level moderation**, not only one-message classification.

Already recorded:

- repeated harassment over ~10 minutes can form one incident even when each line alone would not justify deletion;
- multiple senders can form one dogpiling incident against one target;
- the owner wants related messages and timestamps compiled for review.

W00 should interview the semantic rules for:

- incident time/message windows;
- target identity;
- repeated same-sender behavior;
- multi-sender dogpiling;
- escalation in tone;
- target asking someone to stop;
- unwanted contact continuing after a stop request;
- whether different channels/scopes can belong to the same incident;
- whether long intervening unrelated conversation breaks the incident.

The final runtime may implement this as an incident aggregator above the per-message classifier. W00 should not assume “one target message + context” is the only model.

---

## 14. Strikes: do not force a generic counter yet

Do not make W00 invent a complete strike arithmetic system just because the old code had one.

The owner has already described category/severity differences:

- `kys` => strike;
- deliberate slur evasion => strike;
- actual slur => strike;
- slur severity can affect escalation;
- unknown-intent `go die` => block/review without strike;
- clearly real-life `go die` => strike;
- targeted staff abuse => strike;
- sexual solicitation such as `send nudes` => strike;
- known-minor sexualized content => strike;
- severe real-world threat => strike;
- some harassment can directly justify a time-bounded mute based on the incident.

Coordinator recommendation for downstream architecture:

- store incidents with category, severity, confidence/evidence, and owner-defined strike recommendation;
- do not make one generic integer counter the only representation;
- EnthusiaStaff can later implement category/severity-aware escalation.

W00 should continue recording “strike / no strike / unresolved” and any owner-stated severity/duration, but should not invent unasked formulas.

---

## 15. Public rules vs AI rules

Yes. Policy v1 must distinguish these layers:

1. **Server-rule violation**
2. **AI message action**
3. **AI evidence / strike recommendation**
4. **Automatic containment recommendation**
5. **Human punishment decision**

Also add a sixth orthogonal dimension:

6. **Review priority / staff notification**

This resolves the apparent conflict between the website saying a category can justify a permanent ban and the owner saying automated AI must never ban.

Example:

```text
Doxxing
Server rule: zero tolerance / severe violation
Message action: BLOCK
Evidence: severe safety incident
Containment: temporary mute if policy says so
Review: URGENT
Human punishment: staff may decide permanent ban
```

Do not use one label to represent all of those meanings.

---

## 16. Dataset/model target

Coordinator recommendation:

The local model should primarily predict **semantic risk classes / contextual attributes**, while a policy layer maps those signals plus platform/channel/context metadata to the final action.

Do not train the model to be the sole authority for `ALLOW/REVIEW/BLOCK`.

However, the dataset should still store the owner’s desired action and enforcement dimensions because they are valuable for:
- end-to-end policy evaluation;
- policy-engine tests;
- measuring whether semantic predictions lead to the correct final decision.

So dataset records should preserve both:

```text
semantic truth
+
owner-desired policy outcome
```

W12 may implement one multi-task model or several heads, but W00 does not need to choose the architecture.

This is especially important because identical text can map differently by context:

```text
"im gonna kill you"
Minecraft -> ALLOW
Discord general -> BLOCK
Discord gaming with active game context -> ALLOW
```

The semantic/context representation must therefore be richer than one direct action class.

---

## 17. Deterministic rules vs learned model

Treat these as primarily deterministic/runtime policy:

- configured Discord channel exemptions;
- ticket-channel exemption;
- mirror/duplicate suppression;
- permissions/authentication;
- staff-alert-on-mute;
- authoritative linked-account identity;
- storage/retention;
- rate limits/queue behavior.

Some textual rules should have **both** deterministic and learned coverage:

- exact/common slur variants;
- `kys` and common evasion forms;
- explicit `irl` / real-world cues;
- known Minecraft gameplay cues.

Why both?

- deterministic rules give high-confidence fast handling for known cases;
- the learned classifier catches paraphrases, context, and unseen evasions;
- the dataset must still include these examples so the semantic model understands them.

W00 defines the moderation meaning. Downstream runtime/model workers decide whether a settled rule is implemented deterministically, learned, or both.

---

## 18. Known production failures / surprising OpenAI scores

These are high-value hard examples. Turn them into contrast families.

### Plain harassment false positive

`you suck`

Observed target harassment score in calibration: approximately **0.8918**.

Old behavior could be promoted by surrounding harassment context into enforcement even though this is normal tolerated Minecraft toxicity.

Desired result: **ALLOW**.

Related hard pair:
- `you suck`
- `youre trash`
- `youre a fucking idiot`
- repeated targeted abuse across many messages.

### Casual game/self-harm false positive

`kill me bro`

Observed old result:
- `ALERT_ONLY`
- self-harm/intent about **0.7173**.

Owner direction from the broader project: ordinary gameplay/death language should not be treated as genuine self-harm merely because the generic moderation model sees intent.

### KYS false negative / under-enforcement

`kys`

Observed old result:
- `ALERT_ONLY`;
- self-harm/intent around **0.7481**;
- self-harm/instructions score observed around **0.7879**, just under the old 0.80 threshold.

Desired/now-owner-confirmed result: **BLOCK + strike**.

### Generic PvP language receives very high violence scores

Observed:

- `im gonna kill you` -> violence about **0.9442**
- `im gonna stab you` -> violence about **0.9523**
- `im gonna shoot you` -> violence about **0.9441**

Desired Minecraft result: generally **ALLOW**.

This is the core reason raw OpenAI violence scores cannot be the final Minecraft policy.

### Real-world threat can score lower than gameplay violence

Examples after the Minecraft-aware patch:

- `i know where you live and im going to kill you` -> harassment/threatening about **0.7419**, desired BLOCK.
- `i will find you in real life and hurt you` -> harassment/threatening about **0.5505**, desired BLOCK.

Meanwhile generic PvP violence scored >0.94.

This demonstrates that absolute generic scores are not enough.

### Ambiguous “house” false negative

`im at your house and im going to stab you`

Observed local-policy replay:
- allowed;
- strongest generic violence around **0.9443**.

This was intentionally left ambiguous at one stage because “house” can mean a Minecraft build. W00 should determine where wording changes it into a real-world threat.

### Burn-house ambiguity

`im going to burn your house down`

Observed local-policy replay:
- allowed;
- generic violence around **0.8507**.

Again, “house” is ambiguous in Minecraft. Build hard pairs around Minecraft base/build cues vs real-world delivery/location/time cues.

### Minecraft TNT is misread as dangerous/illicit

`how do i make tnt`

Observed strongest illicit score around **0.9444**.

Desired result: **ALLOW**.

### Real-world bomb instruction

`how do i make a bomb in real life`

Observed illicit/violent score around **0.9167**.

Desired result: **BLOCK**.

### Serious false negatives discovered after that replay

The owner later tested:

- `im gonna send a bomb to your house` -> system allowed it; owner considered that unacceptable.
- `im going to stab you when i see you at school on monday` -> system allowed it; owner considered that unacceptable.

These are critical W00/W02–W10 hard families because they show why a small hand-written list of `irl` cues is insufficient.

### Other useful calibrated examples

- `youre a fucking idiot` -> harassment about **0.9756**, old policy DELETE.
- `i hope you die` -> harassment/threatening about **0.7958**, DELETE; owner later said BLOCK by default, no strike unless real-life intent is established.
- `go kill yourself` -> self-harm/instructions about **0.8487**, DELETE.
- `shes 15 but shes hot` -> sexual/minors score was only about **0.2036**, but OpenAI category flag was true and the patched policy hard-blocked it. This is another warning that score magnitude and model boolean flags do not map cleanly to owner policy.

OpenAI’s alias can drift over time, so treat these numbers as dated calibration evidence, not eternal thresholds.

---

## 19. Additional coordinator context / moderation philosophy

### Overall product goal

The owner wants this to become a **full chat moderation system**, not merely a narrow OpenAI filter.

The long-term goal is:
- central moderation for Minecraft + Discord;
- strong automatic message decisions;
- context-aware incident detection;
- staff review/correction;
- human-reviewed data improving the local model;
- eventual automated temporary mutes for well-defined/high-confidence cases;
- staff retaining final authority for bans and serious case disposition.

This may reduce routine manual chat moderation substantially, but it is **not intended to replace staff judgment for serious sanctions/appeals**.

### Tolerance philosophy

Minecraft is intentionally more tolerant than generic online-safety models assume.

Examples:
- profanity itself is not automatically bad;
- low-level Minecraft toxicity can be allowed;
- violent gameplay language is common and often harmless.

At the same time, the owner does **not** want clear serious abuse missed:
- `kys`;
- doxxing;
- blackmail;
- sexual/minor behavior;
- clearly real-world threats;
- repeated harassment;
- deliberate slur/filter evasion.

So do not characterize the priority as simply “minimize false positives” or “maximize recall.” The policy is **context-sensitive**:
- aggressively avoid Minecraft/gameplay false positives;
- aggressively catch clear real-world/safety violations;
- use review for ambiguity rather than pretending confidence.

### Age assumptions

Do not assume users are adults.

Also do not invent age knowledge. Age-sensitive policy should rely on context/evidence the system actually has. The owner explicitly noted that reliable age knowledge may often be absent.

### Appeals

Already recorded:
- if a player is automatically muted and believes it is wrong, direct them to make a ticket;
- every automated mute alerts staff;
- staff remain able to review/correct the AI decision.

### Known design limitations to plan around

- generic OpenAI moderation does not understand Minecraft context well enough to be the judge;
- model scores are not comparable to owner policy thresholds in a simple way;
- split messages can change meaning;
- cross-scope context can matter;
- long-term harassment needs incident aggregation;
- channel/platform context changes meaning;
- mirrored messages can double-count if not deduplicated;
- exempt/private content needs deliberate privacy boundaries;
- the local classifier will still make mistakes, so structured review/correction is essential.

---

## 20. Sources W00 should still consult when needed

W00 says it has already reviewed the main sources. Keep these as the canonical source map:

### Central project
- `wsg138/AI-Moderation-API`
- issue #1
- issue #1 coordinator correction
- `README.md`
- `COORDINATOR-STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DATASET-SCHEMA.md`
- `docs/WORKER-SYSTEM.md`
- `docs/WORKER-LAUNCH-STANDARD.md`
- `policy/KNOWN-DECISIONS.md`
- `policy/INTERVIEW-PROTOCOL.md`
- `policy/SOURCE-BASELINE.md`
- this briefing
- W00’s own interview JSONL on `w00/policy-interview`

### Current public rules
- `wsg138/enthusia-site/public/rules.html`

### Existing Minecraft moderation
- `wsg138/Enthusia-RoseChat`
- current `ai-moderation.yml`
- AI policy/context/tests
- late-deletion / linked-message behavior where relevant

### Punishment/review authority
- `wsg138/EnthusiaStaff`
- moderation/punishment contracts
- review/evidence architecture

### Discord client
- `wsg138/enthusia-support-bot`
- current Discord message/content runtime
- ticket-channel behavior/exemptions

### Runtime foundation in progress
- AI-Moderation-API PR #18 / W01

Important: PR #18 is **open**, not merged. Treat its API/context implementation as the current W01 proposal, not immutable Policy-v1 truth.

---

# Recommended next interview phase

Do not continue with generic isolated questions. Use **contrast families that isolate one semantic change at a time**.

The next phase should concentrate on unresolved boundaries that downstream dataset workers cannot safely invent.

## A. Real house vs Minecraft house vs delivery threat

Ask a family like:

```text
1. im gonna blow up your house
2. im gonna blow up your minecraft house
3. im gonna blow up your house with tnt
4. im gonna send a bomb to your house
5. im gonna mail something to your house that explodes
6. im coming to your house tonight
7. im coming to your base tonight
8. i know your real address
```

Vary only one cue at a time.

Determine:
- block threshold;
- review vs strike;
- when “house” alone is Minecraft-ambiguous;
- when delivery/mail/real-address wording makes real-world intent clear.

## B. School/work/location/time specificity

```text
1. im gonna stab you
2. im gonna stab you when i see you
3. im gonna stab you at school
4. im gonna stab you when i see you at school
5. im gonna stab you when i see you at school monday
6. see you monday
7. youre dead monday
8. see you at spawn monday
```

Ask what exact cue changes:
- ALLOW -> BLOCK;
- BLOCK -> urgent review;
- no strike -> strike/mute.

## C. Split-message linkage limits

Use identical semantic content with different structure:

```text
A: im gonna shoot you
A: irl

A: im gonna shoot you
[5 unrelated messages]
A: irl

A: im gonna shoot you
[21 unrelated messages]
A: irl

A: im gonna shoot you
B: irl
```

Also test:
- reply vs no reply;
- 2 seconds vs 30 seconds vs several minutes;
- same sender vs different sender;
- target changes.

This should refine the owner’s “20 intervening messages” rule.

## D. Public/PM cross-scope context

```text
PM A->B: did you kill my dog in minecraft
PUBLIC B: yeah and ill kill yours too
```

Then:

```text
PM A->B: i know where you live
PUBLIC A: see you tonight
```

Then reverse public/private order.

Ask:
- which messages may be deleted;
- which PM context staff may see;
- whether unrelated PMs should remain hidden;
- how much time/context separation breaks linkage.

## E. Harassment incident threshold

Build a ladder, not repeated obvious insults:

```text
1. leave
2. leave + i dont like you
3. leave repeated 5 times after target says stop
4. nobody likes you + leave + ur pathetic
5. same content spread over 2 minutes
6. same content spread over 30 minutes
7. 4 different users each say one mild thing
8. 4 users coordinate after someone says "everyone spam him"
```

Determine:
- incident formation;
- message visibility;
- review priority;
- strike/mute threshold;
- how a target saying “stop” changes it.

## F. Staff-targeted abuse vs ordinary-player abuse

Current owner decision says `ModName is a fucking loser and should quit` => block + strike.

Probe whether identical abuse toward a normal player gets the same action.

This matters because the website separately says staff abuse is punishable.

## G. Slurs: content removal vs strike severity

Do not ask whether obvious slurs are blocked; that is settled.

Ask:
- actual slur in a quote/report;
- actual slur in counterspeech;
- “n-word” reference;
- obfuscated actual slur;
- accidental substring;
- reclaimed/self-reference;
- lower-severity slur repeated;
- one severe slur once.

Separate:
- message removal;
- strike;
- severity;
- mute escalation.

## H. Sexual content vs sexual harassment vs known minor

Build minimal age/context pairs:

```text
send nudes
send me a pic
youre hot
youre hot + known age 16
youre cute + known age 16
dm me privately + known minor
dont tell your parents + known minor
```

Avoid graphic content. Determine what requires:
- block only;
- strike;
- mute;
- urgent staff ping.

## I. Self-harm instruction vs disclosure vs game/joke

Use:

```text
kill me bro
kys
go die
i want to die
i want to die after losing this fight
i genuinely want to die tonight
my friend said they want to die
dont tell people to kys
```

Then vary:
- graphic detail;
- repeated evasion;
- positive/negative safety-check response.

Focus on message action vs support flow vs staff alert.

## J. Dangerous instructions vs benign discussion

```text
how do i make tnt
how do i make a bomb in minecraft
how do real bombs work
how did historical bombs work
how do i make a real bomb
for a history project, what made WWII explosives dangerous
```

Determine how intent/instruction specificity changes the action.

## K. Discord channel profiles

Use the exact same phrase in:
- Minecraft public;
- Minecraft PM;
- Discord general;
- Discord gaming with active game context;
- Discord staff;
- Discord ticket;
- configurable exempt channel.

This is more valuable than generating different phrases because it isolates channel semantics.

## L. Exempt-content boundary

Ask:
- are ticket messages excluded entirely from context? Coordinator recommendation is yes;
- are staff-only channels exempt?
- if someone threatens another person in an exempt ticket, should the AI truly do nothing automatically and leave it to staff?
- should the existence of the ticket ever influence public-channel moderation? Coordinator recommendation is no unless staff deliberately attaches evidence.

## M. Review/containment matrix

Give the owner the **same semantic event** at different certainty levels:

```text
possible threat / 55% confidence
likely threat / 80%
clear threat / 99%
clear doxxing
clear blackmail
repeated harassment
```

Ask separately:
- delete?
- normal review?
- urgent ping?
- temporary mute?
- strike?
- ticket/appeal instruction?

This will prevent one overloaded REVIEW state.

## N. Cross-platform identity and context

Only ask if the owner actually wants cross-platform context:

```text
Minecraft linked player: im gonna get you
Discord linked account 5 seconds later: irl
```

Contrast with an unlinked Discord account.

Do not assume cross-platform context should affect punishment without an authoritative account link.

---

# What W00 should do next

1. Continue writing every owner answer into the interview JSONL.
2. Do not re-ask already-settled examples unless the new scenario isolates a different variable.
3. Use the contrast families above to close **unresolved policy dimensions**, not to inflate question count.
4. When the owner answer conflicts with the public website rule, record the conflict explicitly and ask whether:
   - AI behavior intentionally differs from human/server-rule enforcement; or
   - the website rule itself should later change.
5. Before drafting Policy v1, produce an internal “unresolved decisions” checklist and ask only those remaining questions.
6. Policy v1 should clearly separate semantic meaning, message action, review priority, automated containment/strike recommendation, and human punishment authority.
7. Do not design implementation details that belong to W01/W13–W16.
8. Do not assume W01 PR #18’s current context partitioning is the maximum capability of the final system.
