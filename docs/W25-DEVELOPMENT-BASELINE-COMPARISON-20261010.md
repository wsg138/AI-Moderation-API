# W25 open-candidate development checkpoint — 2026-10-10

**Status:** actual CPU-only W11 training+validation smoke test. Not an acceptance, production, privacy, deployment, or 99% accuracy claim. No W20/W26/W27/frozen owner golden, private admitted records, paid inference, or remote model weights were accessed. Normal W11 source train and validation only.

## Source and provenance

- W11 training examples: **3,269**; W11 validation examples: **385**.
- Two independently fitted, six-head, TF-IDF + logistic regression models on identical partitions:
  - `word-tfidf` (word 1–2 grams, max features 30,000) fitted weights SHA-256 `3dea5615249023297a37e0fd07bedf0d761df616c3036254c117b10615da96a1`.
  - `char-tfidf` (character 3–5 grams, max features 12,000) fitted weights SHA-256 `70f787f07e32b2a3a35ad831dea6dc7d859c0b512fa771202119dd339bf71296`.
- `workers/w25/development_probe.py` runs both locally, verifies disjoint W11 train/development example IDs, archives complete predictions and probabilities to separately access-controlled output outside Git, and generates a private complementary-error report.
- Run IDs: `w11-word-tfidf-s42`, `w11-char-tfidf-s42`, `w11-word-tfidf-s138`, `w11-char-tfidf-s138`. The latter pair also wrote the private comparison JSON. An ephemeral, never-persisted HMAC key was used **per paired run**, so cross-session pseudonymous joins are intentionally not possible; a separately managed persistent key is required for the full bakeoff.
- Word and character fitted-weight hashes are respectively **identical across seeds 42 and 138**. These deterministic logistic regression runs are *not* evidence of robustness to data sampling, source drift, architecture choice or distinct seeds.

## Development results: W11 validation only (385 cases)

| Metric | Word TF-IDF | Character TF-IDF |
|---|---:|---:|
| Action correct (ALLOW/BLOCK/REVIEW) | 359 / 385 (**93.25%**) | 345 / 385 (**89.61%**) |
| All six heads simultaneously correct | 316 / 385 (**82.08%**) | 296 / 385 (**76.88%**) |
| Wrongful BLOCK recommendations on gold ALLOW | 9 | 8 |
| Missed gold BLOCK messages | 13 | 24 |
| Incorrect strike recommendations where gold did not strike | 8 | 7 |
| Incorrect mute recommendation where gold did not mute | 1 | 2 |

Cross-model complementarity:
- **30** action disagreements.
- Word correct, character wrong: **22**.
- Character correct, word wrong: **8**.
- Both action wrong: **18**.
- Both action correct: **337**.
- **Hypothetical oracle**, knowing which result is right for each case: `367/385 = 95.32%` action correct. This is an upper bound on choosing between **these two existing predictions**, **not a real deployable ensemble**, and not whole-decision accuracy.

These are W11 development labels and synthetic/original accepted W11 source records, **not an independently double-reviewed prospective real-traffic sample**. The W11 distribution is artificially balanced for policy coverage, not representative of real chat. No extrapolation to production accuracy, FPR or strike safety is justified.

## Failure analysis and next experiment

Character n-grams do **add unique correct cases**, but are worse overall and miss notably more gold BLOCK messages on these inputs. Blindly averaging the two without a held-out validation protocol is therefore not supported by the evidence. The persistent shared false decisions motivate stronger *contextual* model families, better admission of independently reviewed natural conversational examples, and specialized verification/cascade routing.

Open architecture registry already includes DeBERTa-v3-base, ModernBERT-large, XLM-R-base, ByT5-small, byte/character and reference/retrieval variants. These are untrained **proposals**, not winners. Official published descriptions confirm:
- ModernBERT-large is a long-context English/code-focused encoder (395M parameters). A larger backbone may require reduced batch size, limited sequence length, or memory-efficient tuning on an 8GB card.
- XLM-R-base is multilingual; multilingual strength must be validated on actual target-language cases rather than assumed.
- ByT5-small is a byte-oriented sequence-to-sequence backbone requiring task-specific fine-tuning and a new W25 task adapter; it cannot be dropped in as an existing six-head encoder.

Before allocating significant GPU time: finish run-level private telemetry, verify actual accessible training datasets and source permissions, pin exact architecture revisions and licenses, predeclare development split/metric objectives, then run measured small sharded trials with the same W11/W26 **authorized training** data and appropriate development-only calibration. Do not open W20 or reserved acceptance data for model selection.

**Risk:** W25's original ranked `real_distribution` and `context` suites include evaluation records reserved for frozen comparisons. The new candidate-search diagnostics intentionally require a `suite_name=development` ledger and reject final/frozen suite names for architecture choice. Independent prospective acceptance remains separate from model exploration.
