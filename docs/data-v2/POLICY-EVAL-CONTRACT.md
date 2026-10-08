# Policy-v1 offline evaluation contract (W3)

**Status:** proposed benchmark + synthetic unit tests, NOT a real-model score, label-admission gate, or production resolver. Tracks [#62](https://github.com/wsg138/AI-Moderation-API/issues/62) and [#53](https://github.com/wsg138/AI-Moderation-API/issues/53).

## What exists vs what is missing

- The live `service/moderation_api/models.py` defines six policy response dimensions (semantic label, message action, review, strike/evidence, containment, safety support) plus duration. Runtime `MessageAction` permits ALLOW/BLOCK; the offline dataset's REVIEW means **abstain / staff-review recommendation**, not a drop-in API action. Do not retrofit it into the live response without a separately reviewed contract change.
- W12 and W25 have experimental multi-head and routing implementations on *other branches*, plus development/aggregate reports. W25's 991-item development headline (~93.7% action and ~77.0% six-field exact for its cited DeBERTa seed) is **not** an independent prospective acceptance score.
- `tools/data_v2/policy_eval_contract.py` is a **pure, non-production probe** with typed `SemanticFacts` and `PolicyDecision`. It covers only selected settled policy cases. `PARTIAL` means policy defines some outputs but leaves others unspecified. `UNRESOLVED` routes to offline REVIEW; neither is executable punishment approval.
- Actual semantic facts must later include provenance of *as-of-target evidence*, channel profile, relevant prior context, incident link, minor-evidence reliability, quote/reference distinction, credible risk cues, and human adjudication where needed. The draft's coarse `kind` and `scope` are intentionally insufficient for general automation. Actual slur **quoted/reported use** still BLOCK + strike per §10, unlike a literal reference to the term. Clearly game-only Minecraft blackmail is ALLOW under the 2026-10-08 owner clarification **regardless of whether it is posted in Minecraft public/private chat or Discord public/gaming**; the all-in-game stakes must be actually established by as-of-target evidence. Clear IRL blackmail is BLOCK + urgent review with temporary containment regardless of channel, and mute duration remains open. Unclear game-versus-real stakes remain REVIEW in this partial offline probe. Do not infer real-world scope from generic game terms.

## Benchmark input (private local use only)

Run **only after** an independent two-reviewer/adjudication and source-usage approval process provides a versioned, authorized heldout set and predictions from the *same fixed policy/model checkpoint*:

```sh
python -m tools.data_v2.policy_eval_metrics --truth /private/adjudicated.jsonl --predictions /private/predictions.jsonl > /private/aggregate.json
pytest tests/test_policy_eval_offline.py
```

Paths above are generic illustrations, not actual player-data locations. Input files must remain outside GitHub. The CLI never loads a model and never calls a network endpoint. A truth JSONL row is:

```json
{"case_id":"TOY-1","slice":"minecraft_gameplay","truth_source":"independently_adjudicated","policy_version":"v1","split":"heldout","decision":{"semantic_label":"SAFE","action":"ALLOW","review_priority":"NONE","strike":false,"containment":"NONE","containment_duration_seconds":null,"support_flow":"NONE"}}
```

The matching prediction row has exactly `case_id` and `decision` with the same seven fields. **TOY-1 is invented, not admitted gold.** Inputs are *structurally* validated (including exact case-ID matching, no extra raw-text fields, no duplicate case IDs within an input, bounded size, explicit heldout/adjudicated marker, allowlisted non-identifying slice names). Metadata strings cannot independently prove reviewer identity, policy consistency, label correctness, source rights, frozen split, or unseen model exposure. A separate trusted signed/private provenance gate must authorize the benchmark. The CLI emits **aggregates only**, never sample text or IDs; private per-error investigation belongs in the authorized private workflow, not its public stdout.

## Definitions / reporting guarantees

- `action_accuracy`: correct ALLOW / REVIEW / BLOCK over **all** adjudicated targets. The offline REVIEW is abstention; it counts wrong if gold action differs. `review_abstention_rate` counts all predicted REVIEW; deployment coverage = 1 - that rate (not necessarily an error).
- `semantic_accuracy`: exact semantic category match on all targets.
- `full_decision_exact_match`: exact equality of **seven** fields (label, action, review priority, strike, containment, mute duration, support), including the full duration. Unresolved mute duration is rejected from fully adjudicated truth; no partial-field scoring or filling policy nulls.
- `block_precision`: true gold BLOCK among predicted BLOCK. `block_recall`: predicted BLOCK among gold BLOCK.
- `false_blocks_per_1000_benign`: predicted BLOCK among **gold ALLOW** divided by **all gold ALLOW**, multiplied by 1,000. Includes legitimately allowed PvP, banter and gameplay blackmail. A mixed or risk-enriched set is *not* a prevalence estimate.
- `false_strikes` and `false_mutes`: recommended new punishment where adjudicated truth recommends none. `incorrect_punishment_field_sets`: strike, containment or duration differing from truth, including missed necessary penalties. These are offline recommendation errors, **not** a record of actual enforced punishments.
- Critical categories: semantic recall and required-BLOCK recall (only gold-BLOCK subset) for threats, directed self-harm abuse, disclosure/third-party concern, slurs, sexual-minor, doxxing, blackmail, grooming and dangerous instructions. For support-only cases, required-BLOCK recall is legitimately undefined; measure safety-flow exact match separately.
- Per-slice metrics, counts and action confusion are included; count/denominator and 95% Wilson binomial confidence intervals accompany each proportion and the per-1,000 false-BLOCK rate. Empty denominators become `null` rather than a deceptive 0%; Wilson assumes independent Bernoulli trials and may be overconfident for correlated sessions/families, so a later analysis must use **session-clustered** uncertainty or bootstrap over heldout groups as well.
- Selection must preserve naturally sampled traffic prevalence, and report **separate** Minecraft public/PM, Discord general/gaming, gameplay language, novel session/text, protected-safety, and severe slices. Artificial tests exercise only arithmetic and policy plumbing; they say nothing about model accuracy or rare-class reliability.

## Freeze and acceptance barriers

1. Version/freeze Policy v1 + later owner clarification and its unresolved list. Resolve duration, unknown-age grooming, PM adult content, and threat severity questions before treating those fields as full gold.
2. Source permissions and private PII/redaction review; only independently adjudicated records allowed. No model-/Qwen-labeled gold.
3. Freeze group-aware train/dev/heldout split and immutable hashes **privately**, with cross-source and family overlap audits. No model selection on prospective real holdout or W20/W27.
4. Evaluate a single predeclared frozen checkpoint/threshold/policy revision on a properly prospective, never-mined cohort. Report all misses and confidence bounds before any ~99% claim. No claimed acceptance based on the example tests in this PR.
5. Require human and owner review for false strikes, false BLOCKs and critical recalls; no new automatic punishments, merges, rollout or model training from this document.

Test cases use *only invented synthetic objects*, including Minecraft game-only versus IRL blackmail; Minecraft versus Discord generic threat; quoted slur §10; self-harm support versus directed abuse; staff abuse; reliable-minor vs unsupported age; and unresolved grooming.
