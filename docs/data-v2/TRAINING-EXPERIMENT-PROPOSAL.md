# W3 — proposed bounded DeBERTa experiment (NOT authorized)

**Status (2026-10-08): proposal only.** No model download, GPU allocation, training, upload, spend, or owner-computer access was performed. Tracks [#62](https://github.com/wsg138/AI-Moderation-API/issues/62), parent [#53](https://github.com/wsg138/AI-Moderation-API/issues/53), and the [v2 training order](TRAINING-ORDER.md).

## Before scheduling anything

Require **all** of the following, recorded privately with only aggregate checkpoints on GitHub:

1. Registry rights/consent and privacy/data-minimization clearance **for the specific compute location**. No private player content, IDs, private annotation or raw chat in GitHub, public Actions artifacts or third-party GPU without approved transfer rights and privacy review.
2. Independent adjudication of every admitted training/evaluation label; severe categories and false-punishment candidates require policy-grounded review. G10–G27 **remain synthetic candidates**, and Qwen/W25 predictions are not gold. Preserve the settled game-only Minecraft-blackmail ALLOW rule; disputed scope stays unadmitted until resolved.
3. Leakage-safe **family/session/cross-source** split, no downstream target-overlap or post-target context, exact source and split revision/digests, token serialization and redaction code SHAs. Group minimal pairs and all paraphrases in one split. Newly prospective, never-scored traffic-heldout must be frozen **before** experimentation.
4. Freeze policy version, evaluation schema and gold provenance. No W20/W27 queries, no repeat selection on the mined-then-split 552 real heldout, no W25 PR #48 branch modification. Keep sealed tests closed for a separately authorized final gate.
5. Owner approves the specific bounded job, machine/location, power/runtime/money limit, download, accepted dataset manifest, output location and stop policy. No approval is implied by this proposal or a green PR.

## Baseline and one-variable experiments

Keep a single *immutable* architecture to begin: **`microsoft/deberta-v3-xsmall` at W25 pinned revision `79c19681226cddc96fe1d9625c8a3ed6dac79624` (MIT, max 512 tokens)**. Use the established W25/W12 serialization/router as the historical comparator, not a claim it already meets acceptance. Record Python/CUDA/torch/transformers versions and exact W25 source revision. Prefer already cached weights *only after approval*; this task did not check local cache.

| Stage | Train/dev usage | Changed variable | Stop/decision |
|---|---|---|---|
| 0 — no-training reproduction | Approved v2 dev only; pinned historical predictions or re-evaluation where authorized | No training, freeze reported baseline | Record target count/splits/metrics and code hashes; if provenance fails, stop |
| 1 — supervised pilot | Admitted real + separately accepted synthetic **train**; independent **dev** | One lightweight encoder; first fixed data mix | Compare false BLOCKs, wrong strikes, macro/action/semantic/full-decision, severe recall |
| 2 — weighting ablation | Same admitted examples, schedule, seed | Real:synth sampling weight only (illustrative 1:1 vs 3:1, not source admission) | Keep lower wrong-punishment risk; no test-set tuning |
| 3 — hard-pair ablation | Same family-isolated training, dev | Add reviewed PvP/IRL, game/IRL blackmail, slur reference/quote, minor evidence contrasts | Halt if gameplay false BLOCKs rise or critical recall regresses |
| 4 — architecture of output | Same admitted source/split | Fact-head -> **versioned offline policy resolver** vs direct six-field head | Only settled policy fields auto-resolve; unresolved -> staff review |
| 5 — seed check | Same chosen recipe | Seeds **42, 138, 2026** | Compare mean, range and worst seed, context-slice stability; no winner from one lucky seed |
| 6 — optional domain adaptation | **Train-only**, rights-cleared unlabeled text; not a fresh pseudo-label source | Extra MLM adaptation vs no DAPT (match other variables) | Skip unless error evidence shows domain vocabulary gap and bounded pilot is approved |

Predeclare a **starting hypothesis**, not immutable hyperparameters: target plus at most 8 prior in-scope messages / 120 seconds, max sequence length 256, then compare 512 for truncation on dev if it fits memory. No future messages or exempt staff/ticket context. Start microbatch 2, gradient accumulation 8–16, 2–3 epochs, early stopping with patience ~1 on a *predeclared dev selection score*, mixed precision when supported, checkpoint one best + one rollback artifact. Keep effective batch and samples/epoch logged. If an OOM occurs, **stop first**, then request a new approved lower-token/microbatch experiment instead of silently rerunning with changed settings.

**Decision selection:** prioritize minimal false BLOCK/false strike/false mute and critical safety recall; report action and semantic accuracy plus complete policy decision agreement and abstention. A 99% aggregate action number is not sufficient in traffic dominated by ALLOW. Proposed automatic-enforcement gate is *not established*; no punishment activation from this experiment.

## Preliminary resources (planning ranges, not measured benchmarks)

| Option | GPU / VRAM | Host RAM | Working disk | Illustrative per-run time | Compute cost |
|---|---|---|---|---|---|
| Owner RTX 4060 Ti 8 GB | Single 8 GB card, estimated ~5–8 GB for carefully capped xsmall training; optimizer/sequence settings can still OOM | ~12–32 GB | ~10–30 GB private workspace, more if optimizer checkpoints kept | ~1–8 hours for an **assumed** 10k–30k admitted samples, 2–3 epochs, 256-token windows | $0 rental; electricity/wear not included |
| Owner CPU fallback | No GPU | ~16–32 GB | ~10–30 GB | Much slower, likely impractical for multiple seeds | $0 rental; energy/time not included |
| Separately approved rented 16–24+ GB GPU | Requires explicit vendor/privacy/security approval first | ~16–32 GB | ~20–50 GB + temporary secure storage | Could be faster; benchmark before budgeting | Hypothetical **$0.25–$1.50 per GPU-hour**, about **$1–$12 for 4–8 hours** per trial, excluding startup, transfer and storage; **not a current quotation** |

These are **wide planning assumptions**, not verified device measurements or current provider prices. Dataset size is not known until admission. A source change, context length increase, gradient checkpointing choice, extra heads, optimizer selection, or Windows CUDA setup can materially change resource use. Three seeds across multiple ablations may multiply time/cost; **do not approve all stages as one unlimited job**. Suggested first permission, *if all gates pass*, is **one** pilot capped at 2 hours wall time, one GPU, no remote spend, 256 tokens, <=8 GB VRAM, <=24 GB RAM and <=20 GB temporary disk; record progress at bounded intervals and stop on OOM/time cap, repeated non-finite loss, missing digests, privacy/revocation change or unacceptable dev false punishment. Any continuation or cloud option needs renewed authorization.

## Reproducibility and privacy

Before a pilot: privately record source-approval references, group-split algorithm and digest, train/dev IDs and digests, context builder version, canonicalization/tokenizer revision, model revision and license, dataloader sampler, seed, precision/batch/accumulation/steps, run manifest, max resources, effective source weights, acceptance metrics and rollback target. Evaluate on the **same heldout/adjudicated fixed dev** for comparisons; only after a final development freeze request separate independent prospective acceptance.

Put weights/checkpoints/optimizer state/logs and per-example predictions in an **owner-approved local private encrypted/restricted workspace outside the repository**, named by a non-identifying run ID. Store only non-sensitive aggregate tables and code/manifest-scheme on GitHub; no usernames, raw text, file paths, identifying digests or private error examples. Disable public experiment trackers, third-party telemetry and indiscriminate logging. Retain previous accepted runtime artifact untouched; the experimental model is **never installed in production by this workstream**. If training is cancelled, remove orphan temporary staging data according to source permission policy without modifying existing runtime state.

## Prerequisites still open at the time of this proposal

- PR #52/#56 Codacy findings need specific evidence-based triage; PR #58 blind workflow remains preparation, **not** a certified source of independent labels.
- G10 gameplay-blackmail source corrections/adjudication and cross-batch family isolation pending; W1/W2 separately own QA/security changes.
- Private real-chat rights, redaction and genuine independent labels are not approved through this PR.
- Resolver completeness and reviewer-handled unknown policy edges; no supported automatic punishment duration/threshold table.
- Prospective representative heldout, trustworthy rare-category coverage and confidence intervals required for ~99% claim.

**No training request is being made now.** Once prerequisites pass, present the owner with the exact first-job manifest and approval request before any heavy work.
