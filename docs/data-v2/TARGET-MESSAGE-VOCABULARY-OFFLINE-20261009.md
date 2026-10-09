# DATA-V2-22 — Offline target-message literal vocabulary contract

**DRAFT ONLY / 2026-10-09. Not production code, training, or an
actual slur-classifier accuracy evaluation.**

## Motivation

After the owner requested actual slur spellings for model evaluation, a
private (workstation-only) 18-case *fictional* corpus was created and checked
against its private SHA-256 manifest. It contains three lexical categories,
direct use, friend joking, quoted reports, deliberate obfuscations, mere
references without the actual expression, and cases where a prohibited word
occurs **only in prior chat**.

Local Qwen3 8B with the fixed offline policy prompt matched **11/18** of the
developer-expected actions. Qwen3 14B matched **16/18**. These are deliberately
constructed, development-exposed, non-adjudicated cases. They do **not**
estimate performance on real moderation traffic or justify deployment.

Observed failure pattern: 8B frequently ALLOWed a quoted or friendly-use
prohibited expression and missed certain obfuscations. 14B handled those
categories better but ALLOWed one disguise and BLOCKed an innocent target
whose **preceding** message contained the expression.

## What the code does

`tools/data_v2/target_message_lexical_probe.py` is a **pure proposed
visibility-only contract** with a **caller-provided, restricted, separately
reviewed list of exact literal strings**. No real prohibited vocabulary or
sensitive example text is embedded in Git.

- Only the **current target message** is searched. No earlier messages
  are read by this guard, so previous-context-only lexical hits cannot
  cause it to block an innocent follow-up.
- A match returns a **BLOCK proposal** even when inside a quote/report;
  **no strike/mute/staff alert, no assumption the reporter committed abuse**.
- No match returns **ABSTAIN**, *not ALLOW*. Other serious threats,
  harassment or sexual-minor harm still need independent moderation.
- Existing Minecraft public/private and Discord general/gaming channel
  scopes apply; staff/ticket/unknown profiles return ABSTAIN.
- Only exact, case-normalized, bounded literal tokens are matched.
  Regex metacharacters in a token are escaped rather than interpreted.
  Word-boundary checks protect against simple embedded-substring false
  positives. Approved alternate/masked literal spellings must be
  supplied separately; this does NOT claim to catch unseen disguises.
- The output cannot authorize live enforcement, punishment, training
  admission or interpretation of consent/culpability.

A deterministic lexical hit is not a replacement for semantic context.
Automatically promoting this offline rule would still risk mistaken
positive identification in names, acronyms or other rare contexts. Before
any runtime implementation, a security review, independent curated
negative examples, and actual validation are required.

## Private evaluation boundary

The actual lexical corpus, terms, model result files and private owner
review crosswalk remain on the authorized Windows workstation outside Git.
No player conversations, protected attribute data, or prohibited vocabulary
must enter a public source, issue, CI artifact, or unapproved remote service.

The first-owner 30-case pilot and the second 12-case action-only owner review
remain unchanged. This rule has not been measured on an independently
blinded heldout cohort and should **not** be credited with accuracy gain.

## Development tests

```sh
python -m unittest discover -s tests -p test_target_message_lexical_probe.py
python -m ruff check tools/data_v2/target_message_lexical_probe.py tests/test_target_message_lexical_probe.py
```

Tests cover target only vs context-only, direct vs quoted expression,
false substring matching, escaped punctuation, casefolding, scoped
exemptions, no automatic punishment and configuration limits.
