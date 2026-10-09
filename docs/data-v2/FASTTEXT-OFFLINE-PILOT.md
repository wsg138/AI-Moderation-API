# DATA-V2-12: Real compact language detector — isolated offline pilot

**Status: experimental; zero production authority.** This stage extends the
policy-only trial in DATA-V2-11 by actually using the original fastText
`lid.176.ftz` classifier in an isolated *pull-request* GitHub Actions job,
where downloads are possible. It never joins the moderation API, calls
EnthusiaStaff, reads private chat or changes the policy.

## Candidate and provenance

- **Candidate:** upstream fastText language-identification model
  `lid.176.ftz`, supporting 176 languages and sized at **938,013 bytes**.
- **Source:** https://fasttext.cc/docs/en/language-identification.html
- **Pinned official download:** https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz
- **Verified SHA-256:** `8f3472cfe8738a7b6099e8e999c3cbfae0dcd15696aac7d7738a8039db603e83`
- **Model license:** Creative Commons Attribution-ShareAlike **3.0**
  (CC-BY-SA-3.0); maintain upstream attribution and share-alike obligations
  for any distribution of the model. **The model is not committed or
  redistributed here.** fastText engine is MIT-licensed; the candidate
  Python package `fasttext-community==0.11.8` also reports MIT licensing.
- The larger `lid218e.bin` model is **not** used; that model has a
  different, noncommercial license and substantially greater memory needs.

This package is installed only in the isolated offline smoke job, **not**
in the production service dependencies or runtime container.

## Pilot

`tools/data_v2/fasttext_language_candidate.py` verifies the exact bytes
before loading via an optional fastText Python binding. With a real
model in memory, it predicts the two top languages on each public toy
message and conservatively maps scores to a candidate assessment:

- A small exact list of harmless standalone greetings maps to ALLOW.
- Very short messages (fewer than three alphabetic words), messages
  including commands (`/`), mentions (`@`), Minecraft formatting
  (`§`), missing/invalid inputs and low-confidence/marginal predictions
  **ABSTAIN**. A future model will need to identify more of these cases
  while preserving a low false-block rate.
- A top English prediction of at least **0.90** with a separation
  of at least **0.30** maps to candidate English (ALLOW).
- A top non-English prediction meeting those heuristic conditions
  additionally requires at least **five alphabetic words** before it
  maps to candidate primarily non-English (BLOCK).
- **The 0.90, 0.30 and five-word choices are merely conservative
  engineering hypotheses, not calibrated accuracy/confidence claims or
  permission to block anyone's message.** They must not be transplanted
  into runtime without real evaluation.
- The final action still passes through DATA-V2-11 exact channel-profile
  policy mapping. Exempt profiles are skipped; unknown/undefined
  profiles are out of scope. **No strike, mute, staff alert, repeat
  penalty or other language-only punishment can be produced.**

Public developer file
`data/policy-probes/fasttext-language-pilot-v1.jsonl` contains **34
short illustrative English, Spanish, French, German, Portuguese, Italian,
Russian, Chinese and mixed-language Minecraft/Discord-style messages**,
including harmless greetings, game words, coordinates, commands, a
username and exempt Discord profiles. These illustrative labels are
**not independently reviewed gold**, do **not** measure deployment-grade
accuracy and may not be used as training data.

Run locally after separately obtaining and validating the official model:

```sh
python -m pip install --only-binary=:all: fasttext-community==0.11.8
python -m tools.data_v2.fasttext_language_candidate \
  --model /private/model-dir/lid.176.ftz
```

Or view the `language-detector-offline-pilot` GitHub Actions job for
the matching PR. The output is only aggregate action counts and
illustrative disagreements, explicitly
`independent_human_gold_evaluated=false`,
`accuracy_validated=false`, `thresholds_validated=false`,
`approved_to_block_live_chat=false`, `training_eligible=false`.

## Important constraints

- FastText chooses the most likely **single** language and can fail on
  mixed text, player names, Minecraft terminology, short messages,
  transliterations and unsupported languages. A high model score is
  not an independently calibrated probability that English-only
  policy is violated.
- Toy case counts cannot be treated as model precision, recall, false
  block rate or population prevalence. Actual owner-reviewed
  examples must be independently adjudicated and privacy-cleared.
- Even if toy examples look good, this PR cannot enable automatic
  blocking. Protected evaluation partitions, real-world false block
  testing, a deployment gate and an explicit shadow-mode rollout
  decision remain outstanding.
- This experiment's public fixtures contain no real player identifiers,
  live server evidence, staff cases, or private owner answer crosswalks.

## Next independent acceptance requirements

1. Assemble a multilingual privacy-cleared **blind gold benchmark**
   with realistic Minecraft/Discord distributions, short messages,
   code-switching, translated greetings, usernames, game jargon,
   commands and exempt profiles.
2. Run fastText candidate offline over that benchmark and evaluate with
   the DATA-V2-11 private aggregate-only protocol. Measure false
   blocks especially on legitimate primarily English chat and
   harmless greetings.
3. Compare with a second licensed detector (e.g. Lingua) if false
   positives or abstention rates are unacceptable, and measure CPU
   latency, package footprint and peak memory on the actual host.
4. Review model attribution and software supply chain before any
   deployment; no full model is included in repository.
5. Only after policy/QA/security approval, add a **shadow-only**
   integration that logs counterfactual classifications without
   deleting chat. Production blocking requires an additional
   explicit release approval.

No new owner policy choices are needed for the English-only message
action, coverage, or lack of punishments. The remaining gate is
detector quality and implementation safety.
