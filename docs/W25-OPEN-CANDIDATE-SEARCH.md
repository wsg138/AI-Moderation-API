# W25 open candidate search and complementarity evidence

**Status:** research + offline development analytics, not a selected model, deployment
approval, or permission to use private acceptance records. The original W25
"five approaches" are a baseline portfolio, not a closed five-model limit.

## Why expand

The existing W25 code tests ModernBERT-base, DeBERTa-v3 xsmall/small, CANINE-S,
W12 baselines and lexical/fusion/cascade variants. This spans important
techniques but cannot establish that these are globally optimal for
Minecraft/Discord moderation, multilingual chat, typo evasion, contextual
banter, or runtime latency. The relevant quantity is each candidate's
**marginal reduction in errors at fixed false-block, recall, privacy and
latency constraints**. A weaker overall model might still uniquely catch an
important class of mistakes.

## Open proposed research candidates

The auditable, **unapproved** list lives in
`workers/w25/candidate_exploration.json`. It includes:

- DeBERTa-v3-base and ModernBERT-large to test whether model capacity and
  greater context improve difficult ambiguous cases enough to justify cost
- XLM-RoBERTa-base for multilingual/code-switching robustness
- ByT5-small as a byte-level, noisy-text/Unicode challenger, **requiring a
  seq2seq-to-policy adapter** before Policy-v1 comparisons
- Unitary toxic-bert as an independent pre-trained toxicity reference, not
  as ready-made Enthusia semantic labels or a punishment judge
- Cheap character n-gram + linear classification, as a distinct evasion
  baseline not reducible to neural tokenization
- Multilingual-E5-small retrieval using *approved TRAIN-only examples* plus
  an auditable policy resolver, never retrieved acceptance examples

Candidate architecture and license references:
https://huggingface.co/microsoft/deberta-v3-base
https://huggingface.co/answerdotai/ModernBERT-large
https://huggingface.co/FacebookAI/xlm-roberta-base
https://huggingface.co/google/byt5-small
https://huggingface.co/unitary/toxic-bert
https://huggingface.co/intfloat/multilingual-e5-small

No external model has been downloaded, fine-tuned, benchmarked, approved or
licensed for deployment by the registry. The source revision, intended use
and resource/license terms need independent pinning and verification before
a specific experiment. An optional privacy-preserving, locally hosted
instruction-following verifier may also be explored **only after** resource
and source-license review; do not send player chat to external services.

## Test families and combinations, not just a list of weights

- **Capacity ablation:** Small vs base vs large encoder, keeping input,
  data families, seeds and supervised targets constant
- **Language/obfuscation ablation:** English, multilingual, byte/character,
  Unicode and spelling variants, with *benign contrasts* preserved
- **Context ablation:** Standalone message vs realistic speaker/time/channel
  context, never fabricating context the runtime would not actually have
- **Ensemble ablation:** Single model, calibrated averaging, two-model
  disagreement-to-REVIEW, lexical + semantic, and tiered verifiers with
  a fast model followed by a specialist on only uncertain cases
- **Retrieval ablation:** Curated policy snippets and approved, split-safe
  train-only examples vs no retrieval; no train/test neighbor leakage
- **Operational ablation:** Calibration, abstention coverage, memory,
  cost-per-1,000 messages, CPU p95/p99 and fail-open outcomes

No ensemble may be selected based on its hypothetical oracle result,
because an oracle uses the correct label to decide which prediction to
trust. Any trainable ensemble/mediator must be learned and calibrated on
separate, family-isolated development folds.

## New private complementarity command

```bash
python -m workers.w25.candidate_diagnostics candidate-registry

python -m workers.w25.candidate_diagnostics compare-development \
  /private/w25/modelA-development.jsonl \
  /private/w25/modelB-development.jsonl
```

The second command accepts only private W25 ledger **schema v2** and
`suite_name=development`, with identical policy revision, source-suite
fingerprint, keyed full ordered input/context fingerprint, case pseudonyms,
and gold labels. It rejects non-development / frozen suite names. It does
not read W20, W27, private production chat, or raw model input and never
runs model inference or downloads weights.

Outputs include sample supports, head-specific and visibility errors,
channel/domain/difficulty slices, action-only disagreement, each model's
uniquely correct actions, jointly incorrect actions, and the **hypothetical
action oracle ceiling**. Small slices under 20 are marked
`INSUFFICIENT_SUPPORT`. The same-case gold labels may be imperfect.
These statistics show *where* models disagree, not why a model made a
decision or whether an ensemble is genuinely better.

## Stage gates before expensive W25 retraining

1. **Evidence inventory:** enumerate existing immutable checkpoints and
   development bundles with checksum, source restrictions, cost and missing
   analytics; no guessing that a model was successfully trained
2. **Development screening:** cheap baseline + saved predictions first;
   compare mistakes and unique strengths on permitted train/dev partitions
   without touching W20, W27, later prospective or independent acceptance
3. **New architecture pilots:** only after reviewer-approved licenses,
   pinned checkpoints, privacy-controlled resources, source-family splits
   and a declared cost cap. Cap candidate width via engineering feasibility
4. **Measured complementarity:** rank *actual* tested single models and
   trainable ensembles by severity-sensitive error rates, uncertain
   decisions, false strikes, review volume, 95% bounds, latency and costs.
   Do not choose by highest overall accuracy in an imbalanced corpus
5. **Freeze then independently test:** one model/policy/threshold version,
   fresh unseen human-adjudicated samples and prospective natural traffic.
   Do not feed a failed acceptance set back into tuning and then retest
   it as if still unseen
6. **Shadow-only staging:** monitor decision drift, lost events, stress,
   runtime cost and staff correction patterns before any owner-approved
   escalation. Automatic sanctions remain off

The target is robust moderation with conservative escalation, not a
promise of literal 100% comprehension. See analytics issue #91 and
prospective acceptance draft PR #88.
