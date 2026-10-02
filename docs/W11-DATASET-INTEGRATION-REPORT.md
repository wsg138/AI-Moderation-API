# W11 dataset integration report

- Algorithm: `w11-v1`
- Synthetic records: **4500**
- Integration families: **1899**
- Largest integration family: **45** records
- Text-only exact groups: **83**
- Near candidates (>= 0.75): **2722**
- Cross-source near candidates: **27**
- Decision-contrast lexical candidates: **578**
- High-similarity cross-worker contrasts reviewed: **2**
- Unresolved cross-worker contradictions: **0**
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
outcome dimensions differ. These are lexical candidates, not automatically defects.
The only cross-worker differing-outcome pairs at the >=0.90 family-link threshold
are G06-0152↔G09-0382 and G06-0256↔G09-0388. Both are intentional public-vs-private
flirting contrasts supported by Policy v1 §11, so they are family-linked rather than
relabeled. No unresolved cross-worker policy contradiction remains from this audit.

## Known limitation

Near-duplicate detection is deterministic lexical candidate finding, not semantic
embedding similarity. It uses shared normalized token bigrams followed by
normalized character-trigram Dice similarity. Human review remains required.

## Files

- `data/integration/W11-audit.json`
- `data/integration/W11-split-manifest.json`
- `data/integration/W11-adversarial-eval-manifest.json`
