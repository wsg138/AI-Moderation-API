# Moderation source baseline

This file tells policy/interview/dataset workers which current Enthusia sources must be reviewed before changing the moderation policy.

## 1. Public Enthusia rules

Canonical website source:
- repository: `wsg138/enthusia-site`
- file: `public/rules.html`

Important current conduct rules include:

- Slurs are prohibited, including the R-slur, even when abbreviated, misspelled, masked, quoted, used as a joke, or not directed at a specific person.
- Racism, sexism, bigotry, threats, targeted harassment, sexual harassment, and repeated unwanted contact are prohibited.
- Swearing is allowed when it is not used to harass or attack someone.
- Names/messages/signs/builds/media may not contain sexual content, nudity, hate symbols, offensive caricatures, filter bypasses, or other clearly inappropriate material.
- Public chat must stay in English.
- Grooming, doxxing, blackmail, credible threats, malicious files, and illegal content are zero-tolerance rules.
- The public rules explicitly say examples are not exhaustive and staff enforce the purpose of rules, not merely exact wording.

The AI policy does not automatically equal the punishment policy. The interview must determine:
- what should be **blocked automatically**;
- what should be **allowed but logged/reviewed**;
- what should be **staff-review only**;
- what should later count toward a punishment.

## 2. Current RoseChat AI behavior

Canonical source:
- repository: `wsg138/Enthusia-RoseChat`
- file: `src/main/resources/ai-moderation.yml`
- plus current AI moderation source/tests.

Current important behavior includes:
- AI is optional/fail-open.
- Message enforcement and punishment escalation are separate controls.
- Automatic punishments are currently disabled.
- OpenAI model: `omni-moderation-latest`.
- Existing context target: 6 prior / 3 after, max age 45s.
- Existing policy was tuned to avoid Minecraft false positives.
- Dedicated staff alert permission: `rosechat.ai.alerts`.

Known production failures that must become interview/training examples:
- low-level insult false positive (`you suck`);
- `kys` initially too weak;
- ordinary PvP phrases receiving very high violence scores;
- real-world threat phrasing sometimes scoring lower than PvP;
- split-message threat context;
- real-world school/time context missed by simple phrase rules;
- house/base ambiguity;
- real-world bomb threat vs Minecraft TNT ambiguity.

## 3. EnthusiaStaff

Canonical source:
- `wsg138/EnthusiaStaff`

Relevant principle:
- EnthusiaStaff owns evidence/cases/strikes/punishments.
- The AI service should provide structured evidence and review items.
- The AI service does not directly own bans/mutes.
- Normal EnthusiaStaff functionality must not depend on AI uptime.

## 4. Discord/Ticket Bot

Canonical source:
- `wsg138/enthusia-support-bot`

The current production Ticket Bot already receives message content and is the intended Discord-side client of the central AI service. Do not build a second semantic classifier inside the bot.

## 5. Central design

Canonical source:
- this repository's `docs/ARCHITECTURE.md`.

One central service owns:
- semantic context;
- local classifier;
- OpenAI advisory results;
- durable event/review storage;
- structured reason codes;
- training-data review/export pipeline.

## Conflict handling

Workers must actively compare these sources.

Example: the public website says slurs are disallowed even when quoted. If an interview answer appears to conflict with that, do not silently rewrite either source. Ask whether:
- the website policy should govern AI blocking exactly;
- AI should only review/flag quoted instances;
- the website rule itself is intended to change.

The purpose of the policy interview is partly to expose and resolve these mismatches.
