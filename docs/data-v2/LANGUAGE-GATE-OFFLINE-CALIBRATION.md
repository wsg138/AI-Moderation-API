# DATA-V2-11 — Offline English-primary rule gate and detector calibration protocol

**DRAFT, NOT A DETECTOR.** This work does not invoke an ML language model,
infer a message's language, join the production moderation API, access private
server messages, admit training records or enable live message blocking.

Owner-approved policy is versioned in
`policy/english-primary-message-action-v1.json`: all currently moderated
Minecraft public/private and Discord public/gaming chats (retaining explicit
staff/ticket exemptions), BLOCK only *primarily non-English* messages, ALLOW
short greetings and occasional foreign words/names/game terms, and **no**
language-only strikes, mutes, staff alerts or repeated-violation escalation.
The independent safety/harm policy continues to apply on its own.

## What was implemented

- `tools/data_v2/language_rule_probe.py` maps a **supplied, separately
  assessed** language category to message action, while enforcing exact
  runtime `channel_profile` routing from `docs/API-CONTRACT.md`.
- Only `minecraft_public`, `minecraft_private`, `discord_general`, and
  `discord_gaming` are eligible. Exempt runtime profiles
  `discord_staff_exempt`, `discord_ticket_exempt`, and
  `discord_configured_exempt` are always skipped. Unknown profiles and
  undefined Discord bot DMs are out of scope.
- Unknown, unavailable, short/mixed ambiguous assessments **ABSTAIN**
  rather than guess or block. A provider's assessment is input to the
  offline gate; **there is no validated provider or language detection
  inference here**.
- The mapping can never output a strike/mute/staff alert/other sanction
  from a language-only rule. Exempt/no-decision outcomes do not override
  independently applicable serious-safety policies.
- A public suite of 20 **developer-only matrix probes** covers all allowed,
  blocked, abstaining, exempt and unknown-scope routes. These probes contain
  no chat text, user identifiers, model predictions, or gold training data.
- `tools/data_v2/language_detector_benchmark.py` is an **aggregate-only
  private evaluation protocol**. It accepts externally supplied,
  independently human-reviewed cases with detector-predicted assessment
  categories and measures *false blocks*, *false allows* and abstentions.
  This is **not** a classifier implementation. The independent-review
  provenance field is claimed by the caller and is not cryptographically
  verified. The protocol does not approve any release or training.

## Smoke test

```sh
python -m tools.data_v2.language_rule_probe
```

This must print aggregate probe counts only, with
`language_detector_evaluated=false`, `independent_holdout_evaluated=false`,
`runtime_enabled=false`, `training_eligible=false`.

**Passing smoke probes does not establish language detection quality.**
No language detector is called or evaluated. The tests merely verify that
a future *correct* externally supplied language assessment would map to
the owner-specified action on the intended channel.

## Private detector benchmark

Only after an independently reviewed, consented, private benchmark exists,
and a chosen real detector has provided an assessment for those same cases,
create a **private** newline-delimited JSON file **outside Git checkout**.
Each record uses this exact schema, with no raw message or player ID:

```json
{"case_id":"private-eval-0001","review_provenance":"independent_human_review","human_reviewed":true,"channel_profile":"minecraft_private","human_expected_action":"ALLOW","detector_assessment":"primarily_english"}
```

Allowed expected actions: `ALLOW`, `BLOCK`. Valid detector assessments:
`primarily_non_english`, `primarily_english`,
`occasional_foreign_words_or_short_greetings`,
`player_names_and_recognized_game_terms`,
`unreliably_assessed_or_ambiguous`, `unavailable`.
Records are *not* marked training-eligible.

```sh
python -m tools.data_v2.language_detector_benchmark \
  --private-predictions /private/language-predictions.jsonl
```

CLI reports **counts/rates only**, no case text or IDs. Inputs are rejected
when inside Git checkout, when source-provenance/review flags are absent,
when duplicate IDs or extra fields appear, or when an exempt/unknown
profile is erroneously treated as moderated. It reports abstentions
separately rather than counting them as correct decisions. It refuses
to claim that caller-supplied provenance has been independently verified.

## Next actions (not authorized by this PR)

1. Select an actual language detection provider/model suitable for mixed
   English/game jargon and short Minecraft messages, with bounded
   latency/memory and a documented license. No model is selected here.
2. Prepare independently human-adjudicated, privacy-cleared **blind**
   calibration and held-out records, including English, Spanish and other
   common languages, code-switching, names, usernames, slang, links,
   emoji, Minecraft item/command tokens, and short greetings. Separate
   player identity and train/test family leakage.
3. Run that detector **offline**, verify false-block risks separately
   per language/profile/length, and obtain owner/team release criteria.
   No single arbitrary confidence threshold is encoded in these probes.
4. Security/privacy review and shadow mode before an explicitly
   authorized production rollout; preserve existing fail-open behavior.

Other moderation categories remain separate. Do not reinterpret action-only
owner feedback as semantic gold or release 9,000 quarantined synthetic
cases through this rule.
