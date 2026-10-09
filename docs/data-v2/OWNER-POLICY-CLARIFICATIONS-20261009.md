# DATA-V2-19: owner calibration after the sealed 30-case pilot

**DRAFT / OFFLINE ONLY.** No model training, source-label admission, bulk
9,000-case inference, service integration, automatic sanctions or deployment.

## Owner clarification on 2026-10-09

- A message repeating prohibited directed abuse remains BLOCK as content even
  if the writer says they are reporting another player. **Do not treat the
  good-faith reporter as the original offender or punish them for quoting.**
- A report quoting an *other* real-world threat is preferably ALLOW when
  clearly condemning the statement; a contextual block may be acceptable.
- Familiar foreign greetings remain ALLOW. A reliably identified
  substantive foreign-language word or phrase, including an isolated insult,
  is BLOCK. Avoid guessed language decisions on unclear short strings.
  Language-only deletion does not create a strike, mute or repeat sanction.
- Private chat allows ordinary adult-compatible intimacy and ambiguous
  picture requests without automatically inferring grooming. Unknown age and
  one generic photo request are not enough for punishment. Follow genuine
  relevant escalation: refusal, coercion, pressure, secrecy or independently
  supported child-safety concerns. Allow normal messages while maintaining
  high sensitivity for credible later escalation.
- Policy decisions above are message-action anchors, NOT adjudicated semantic
  labels, punitive authorizations or model-validation evidence.

## Developer-only evidence

The original sealed 30-case pilot stays frozen: owner decisions were
21 ALLOW, 5 BLOCK, 4 REVIEW; Qwen3 8B matched 19/26 decisive cases,
Qwen3 14B matched 20/26. Neither predicted REVIEW for owner REVIEW cases.
These are nonrepresentative synthetic examples, not traffic accuracy.

Two fixed-prompt local models were checked on 13 **new invented developer
probes**, not independent heldout owner cases: 8B matched 10/13 toy
expectations, 14B 12/13. Both failed the same quotation-visibility toy,
despite revised written instructions. This prompted a narrow offline
`propose_visibility` experiment: it accepts a *coordinator-supplied exact
policy token*, ignores exempt/unknown surfaces, never matches substrings,
and cannot authorize a live action, strike, or mute. It has **not**
been connected to the moderation API; it does not identify other prohibited
expressions or replace a validated language/safety detector.

The prompt and toy data are versioned in `policy/owner-offline-calibration-v1.1.txt`
and `policy/owner-offline-probes-v1.1.json`. The latter consists solely of
invented development cases and must not be treated as gold or reused as a
prospective acceptance set.

## Next required evidence

Freeze the revised prompt and any proposed policy guard, then obtain
**fresh unfamiliar blinded owner decisions** and evaluate by category:
wrongly blocked allowed messages, missed required blocks, excessive staff
review, and escalation detection. Use family-safe independent heldout
samples and confirm real-world prevalence before any deployment decision.
The previous thirty cases are **development feedback**, not a fresh holdout.
