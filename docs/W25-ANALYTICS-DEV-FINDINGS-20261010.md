# W25 analytics-first development findings — October 10, 2026

**Status:** experimental, PRIVATE underlying evidence, no automatic enforcement.
This is a reproducibility report from already saved development predictions,
not a newly certified model release, an acceptance result, or a go-live decision.

## Evidence and leakage controls

- W11 base lexical training: **3,269 train / 385 development**.
- Verified W11 + role-admitted W21/W26 training: **5,978 train / 991 development**.
- Admitted source files and group partition manifests were verified against
  their pinned SHA-256 values before data use. W26 was read locally from
  approved private storage; **W20/W27 were not read, trained on, or tuned on**.
- Eight saved W25 prediction bundles were checked against **exact same 991-case
  development suite fingerprint**
  `1b85c8775025987b7414a78e49909cb696cd4eca43ee634fcd2de2f16752fa27`.
- The W25 retrospective archive contains **postprocessed predictions**, with
  potentially different selective thresholds and preprocessing. The saved
  bundle SHA is recorded as `saved_prediction_bundle`; the dev report digest
  is explicitly `saved_evaluation_report`, **not proof of model-weight SHA
  or original training settings**. No neural inference or paid GPU work.
- All per-case probabilities, mismatch flags and pseudonymous join keys are
  private. Do not publish raw chats, source example IDs, private ledgers, or
  HMAC keys. One ephemeral key permits within-run comparisons only; a future
  reviewer-controlled stable key/mapping workflow is necessary for cross-run
  evidence and staff adjudication.

## W11-only inexpensive word-vs-character test

| W11 development, n=385 | Word TF-IDF | Character TF-IDF |
|---|---:|---:|
| Action decisions correct | 359 | 345 |
| Complete six-head correct | 316 | 296 |
| Wrongful BLOCK on gold ALLOW | 9 | 8 |
| Missed BLOCK | 13 | 24 |

The character classifier uniquely corrected **8** word-classifier action
mistakes but introduced **22** errors where word was right. Both were wrong
on **18**. Seeds 42, 138 and 2026 had identical fitted-weight SHA-256 values
and metrics; do not count them as three independent training results.

## Role-admitted lexical test

| W11/W21/W26 development, n=991 | Word TF-IDF | Character TF-IDF |
|---|---:|---:|
| Action decisions correct | 918 | 889 |
| Complete six-head correct | 731 | 685 |
| Wrongful BLOCK on gold ALLOW | 53 | 50 |
| Missed BLOCK | 10 | 28 |

**Failure localization:** word model had 40 wrongful BLOCKs in adversarial
difficulty, 21 in sexual-content domain and 20 in self-harm domain; these
dimensions overlap and must not be added. In the 506-example curated
real-chat development slice, the word model got **500 actions** right but
only **413 complete six-head outputs** right. It made **zero** wrongful BLOCKs
on the 499 labeled ALLOW records, but its Wilson 95% false-block upper
bound was still **7.64 per 1,000**, not the target of 1 per 1,000.
Its whole-action accuracy lower bound was about **97.44%**.
This slice was curated and ALLOW-heavy, not a pristine prospective sample.

## Eight saved W25 candidate configurations on identical development records

| Candidate, n=991 | Correct actions | Complete six-head matches | Wrongful BLOCK on gold ALLOW |
|---|---:|---:|---:|
| DeBERTa-v3-xsmall selective | 929 | 763 | 1 |
| ModernBERT normalized selective | 905 | 780 | 1 |
| DeBERTa-v3-small selective | 893 | 713 | 1 |
| Xsmall stacked router | 830 | 648 | 2 |
| Xsmall balanced | 826 | 714 | 0 |
| ModernBERT raw selective | 801 | 712 | 0 |
| Archived word/character TF-IDF | 793 | 679 | 0 |
| CANINE-S selective | 691 | 592 | 0 |

These differ in review-routing/threshold behavior; a single accuracy ranking
does not establish model superiority. The raw pre-calibration models and
end-to-end postprocessed candidates must be differentiated.

## A real neural-model complement, not a gold-label oracle

DeBERTa-xsmall and normalized ModernBERT disagreed on **99** actions.
ModernBERT was uniquely correct on **31**, DeBERTa uniquely correct on
**55**, and both were wrong on **31**. The unattainable gold-label oracle
would choose whichever knew the answer; do not treat that as a deployable
ensemble.

Fixed, untuned equal-probability averaging of these two saved output
distributions correctly classified **962/991 action decisions (97.07%)**,
vs 929 and 905 individually. It made **three BLOCK false positives**
against gold non-BLOCK, including two gold ALLOW, and missed **16** of
the 224 gold BLOCKs:

- Observed BLOCK precision **208/211 = 98.58%**, Wilson lower 95% **95.90%**.
- Observed BLOCK recall **208/224 = 92.86%**, Wilson lower 95% **88.71%**.
- Full six-head match **830/991 = 83.75%**, Wilson lower 95% **81.33%**.
- Head mismatches: label 105, review priority 69, action 29,
  containment 22, strike 13.
- No false strike/mute recommendations in this exploratory mix, but
  **one ALLOW/punitive-head contradiction**. The experimental allow
  suppression guard removes this contradiction without changing the
  complete six-head match count. It is not yet an approved Policy-v1 engine.

Critical BLOCK action counts in the same development data:
threat **73/75**, self-harm instruction **22/23**, slur **20/22**,
grooming **4/4**, sexual-minor **3/3**, doxxing **0 gold BLOCK support**.
These rare-category denominators are much too small for reliability claims.

## Threshold-sweep diagnostic, not a selected release threshold

The fixed threshold grid (0.40 through 0.90) was analyzed on **development
only**. A **0.50 averaged BLOCK score** yielded **961/991 action matches**,
**2** total false BLOCKs, **207/224 BLOCK recalls** (92.41%) and
**207/209 = 99.04% observed BLOCK precision**. However, the Wilson lower
95% precision bound is only **96.58%**, far below a statistically supported
99% guarantee. Raising the threshold to 0.85 removed observed false
BLOCKs but dropped recall to **80.36%**.

Repeatedly choosing a threshold on this development set creates selection
bias; any proposed decision rule must be frozen and evaluated on **fresh,
independently adjudicated, unseen material**. Never use W20/W27 during
candidate and threshold selection.

## Specific next engineering/research tasks

1. Protect and audit **one canonical private event lineage** (input,
   policy/model version, model votes, calibrated probabilities, reason codes,
   timing and false-retry/loss metrics). Existing source ledgers are
   pseudonymous but **do not support retroactive raw-example drill-down**
   when their ephemeral key is discarded. Design a reviewer-controlled
   consent/retention-bound re-identification workflow before claiming every
   incorrect case can be explained.
2. Separate **policy consistency** from learned semantic/action predictions:
   the experimental ALLOW punitive-head guard closes an invariant but does
   not raise semantic accuracy. Any full policy engine needs dedicated tests
   for support flow, strike, mute duration and uncertain REVIEW routing.
3. Run approved **new independent folds/holdouts** for action calibration
   and conditional review routing. Track both observed BLOCK precision
   **and lower confidence bounds**, recall, false sanctions, and staff
   review load. Never substitute 99% action accuracy for 99% seven-field
   correctness.
4. Investigate **semantic-label confusion** and review-priority failures
   specifically (105 and 69 in the best simple neural mix), and improve
   supervision, labeling consistency and context. Independently adjudicate
   rare/severe slices and hard-negative harmless messages before using
   them as training gold.
5. Open the model search beyond existing W25 (see
   `workers/w25/candidate_exploration.json`) to stronger contextual,
   multilingual, byte/character, calibrated, and retrieval-assisted
   approaches. Evaluate each by **unique corrected errors**, added mistakes,
   cost, latency, privacy and drift—not architecture popularity.
6. Finish GitHub PR review, static-analysis findings and isolated TEST
   shadow-mode instrumentation. Actual punishment/enforcement is **not**
   authorized by these experiments.

No model has achieved verified near-99% **complete decision** reliability
here. No cloud spend, live enforcement, policy activation or frozen
acceptance evaluations were performed in these analyses.
