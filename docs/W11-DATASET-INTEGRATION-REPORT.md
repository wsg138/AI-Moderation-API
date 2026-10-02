# W11 dataset integration report

- Algorithm: `w11-v1`
- Synthetic records: **4500**
- Integration families: **1899**
- Largest integration family: **45** records
- Text-only exact groups: **83**
- Near candidates (>= 0.75): **2722**
- Cross-source near candidates: **27**
- Decision-contrast candidates requiring review: **578**
- Golden near/exact candidates: **1**
- Golden-sensitive (>= 0.88): **0**

## Frozen split counts

- train: **3294**
- validation: **431**
- test: **391**
- frozen_adversarial: **384**

## Leakage and family safety

- Redundant same-outcome text-only exact groups: **0**.
- Every source `family_id`, text-only exact group, and >=0.90 near group is kept
  in one integration family before splitting.
- Owner golden fixtures are never copied into these manifests. Synthetic records
  with >=0.88 similarity to a golden fixture are forced into frozen evaluation.
- Golden-sensitive synthetic records forced out of training: **0**.

## Decision contrasts

The machine-readable audit records exact and >=0.88 near pairs whose Policy-v1
outcome dimensions differ. These are candidates for intentional minimal pairs or
data defects; W11 does not silently relabel them.

## Known limitation

Near-duplicate detection is deterministic lexical candidate finding, not semantic
embedding similarity. It uses shared normalized token bigrams followed by
normalized character-trigram Dice similarity. Human review remains required.

## Files

- `data/integration/W11-audit.json`
- `data/integration/W11-split-manifest.json`
- `data/integration/W11-adversarial-eval-manifest.json`
