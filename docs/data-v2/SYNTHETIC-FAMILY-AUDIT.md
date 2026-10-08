# DATA-V2-W1 — public synthetic family / target-time leakage preflight

**Status:** read-only audit, candidate only; not reviewed, admitted, trained, or evaluated.  
**Source pin:** `a77fdaf15a90123225311ebc4c8823191655bc69` (draft PR #58 head at audit setup).  
**Input:** exactly 18 public synthetic G10–G27 JSONL batches, 500 records each. All 18 bytewise SHA-256 digests match the existing final-byte table in [PR52-QA-READINESS](PR52-QA-READINESS.md). No other sources are searched.

## Confirmed structural overlap and heuristic candidates

| Evidence | Groups / candidate pairs | Distinct affected cases | Cross-batch groups / pairs | Interpretation |
|---|---:|---:|---:|---|
| Exact target-as-of visible context | 27 | 57 | 1 | Same target-time context regardless of later messages |
| Identical normalized target (18+ characters) | 483 | 1,666 | 5 | Text repeated, potentially with a different earlier context |
| Exact declared family ID | 710 | 5,377 | 0 | Existing explicit family annotation; not independently validated |
| Shared declared family stem | 372 | 9,000 | 0 | **Heuristic** prefix before numeric suffix; often broad themes, not proven paraphrases |
| High-overlap target wording | approximately 1,319 | computed by audit CLI | approximately 2 | **Heuristic** pairs; deterministic rare-token indexing and set overlap |

The first four rows were audited on the pinned public snapshot. The final row is an initial deterministic match count and must be reconciled against the committed Python audit output in CI. Counts **overlap across categories** and must not be summed as independent cases. There are **1,584 nonterminal targets**, which are not automatically labeling defects but are dangerous if post-target messages become features.

The previously published full-conversation normalized exact scan found only **one** cross-batch group (G18-0327, G23-0451). The new target-as-of scan finds **27** matching groups overall; the cross-batch as-of example includes G16-0484 and G23-0497. A full-context comparison can miss cases when a later synthetic response differs. This is a *real input-boundary difference*, not evidence that two source labels are incorrect.

## Implementation and thresholds

- Reuse `serialize_as_of_target`, `normalize_text`, and `batch_files`; never index post-target content, gold labels, notes, outcomes, or scores.
- Treat exact as-of matches, identical target text and exact declared family IDs as strong **structural** overlap signals. No signal is independent semantic ground truth.
- Treat family stems and near wording as **review candidates**, never authoritative lineage. Stems strip only a terminal numeric suffix separated by a dot. The 372 stem buckets may be large (maximum 220 cases) and therefore require human/manual grouping before any credible final split.
- Near-wording candidates need at least 30 normalized target characters, six unique words, five shared words, Jaccard set overlap of at least 0.80 and a unique-word-count ratio of at least 0.80. Up to six rare-word anchors per target (document frequency up to 64) keep this a bounded public-data scan. No semantic embeddings, model inference or private corpus are involved.
- This method **cannot detect all semantic paraphrases** (lexically different rewrites, context-only implications, multilingual equivalents), and it can flag false-positive template overlaps. A report with zero detected risks would not establish an uncontaminated real evaluation.
- Raw data remain immutable. Source byte changes cause a hard failure until reviewed and explicitly re-pinned; do not silently update source hashes.

## Grouped candidate split preflight

The checker accepts a JSON object with exactly `status`, `source_commit` and `assignments`. The first two must equal `candidate` and the source pin above. `assignments` must cover **all 9,000** public candidate IDs exactly, with both `candidate_a` and `candidate_b` present. It rejects `train`, `test`, labels, other fields, incomplete assignment, altered source, and malformed input.

Run on an explicitly prepared **synthetic-only** draft manifest (no private IDs):

```sh
python -m tools.data_v2.synthetic_family_audit
python -m tools.data_v2.synthetic_family_preflight --proposal /path/to/public-synthetic-candidate-proposal.json
```

The preflight returns an aggregate, category-separated count of all evidence groups straddling both candidate partitions. Exit code **1** indicates overlap requiring review; **2** indicates invalid/stale inputs. Exit **0** means only that these narrow checks detected no split overlap. Output always reports `training_eligible: false`. The checker **does not construct a split** or expose reviewer answers.

## Pending owner / independent reviewer decisions

1. Resolve reported cross-batch target-time and near-wording collisions before accepting any grouped split. Check contextual differences and whether shared wording is a true family rather than normal repeated Minecraft phrasing.
2. Decide whether broad family stems should be reduced to finer, independently documented lineage groups; never equate a large topic bucket to a single semantic family automatically.
3. Independently adjudicate Policy-v1 labels, especially gameplay-only versus real-world blackmail, with the existing blinded review protocol. The **216 G10 provisional proposals** and **125 unresolved cases** remain unadmitted; this worker does not alter them.
4. Complete source/permission checks, private development-only provenance and session isolation *in their authorized workstreams*. W20, W27, private player logs, previously mined private holdouts, and sealed evaluation data were not accessed.

## Reproduction and security

Run `ruff check .`, `mypy`, `python tools/check_complexity.py`, `pytest`, `python -m tools.dataset_qa.freshness --require-complete`, and the existing dataset validation job. GitHub Actions and hosted Codacy results must be linked on the draft PR for its **exact head SHA**. Existing PR #52/#56 Codacy triage is not discharged by this audit.

No human-review credentials or source annotations are inferred from these heuristic groups. Final decisions and split admission require a later explicitly authorized gate.
