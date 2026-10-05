# Coordinator state

Last updated: 2026-10-05

## Current phase

**Phase 4 — Client integrations mostly complete; W12 final acceptance and W15 review remain before shadow deployment**

The repository has been initialized and the worker system is live.

## Canonical decisions

- Central standalone moderation API/service hosted in the existing Discord Ticket Bot Pterodactyl server.
- RoseChat, Discord, and EnthusiaStaff call the same service.
- Local semantic classifier is the intended live decision path.
- OpenAI Moderation remains optional/advisory and must not add chat latency.
- AI failure must fail open for normal Minecraft/Discord chat.
- AI does not directly own bans/mutes.
- EnthusiaStaff owns eventual evidence/strike/punishment policy.
- Raw production moderation events stay in private runtime storage, not this public repository.
- Human-reviewed/redacted training examples may be promoted into GitHub.
- Structured reason codes/scores/context are stored; hidden chain-of-thought is not.

## Open work packages

- #1 W00 — Owner moderation-policy interview
- #2 W01 — Central API/runtime foundation — **complete/merged via PR #18**
- #3 W02 — Gameplay dataset (500)
- #4 W03 — Real-world threats dataset (500)
- #5 W04 — Harassment dataset (500)
- #6 W05 — Self-harm dataset (500)
- #7 W06 — Hate/identity dataset (500)
- #8 W07 — Sexual/minor dataset (500)
- #9 W08 — Dangerous instructions dataset (500)
- #10 W09 — Evasion/context dataset (500)
- #11 W10 — Benign/hard-negative dataset (500)
- #12 W11 — Dataset integration/QA
- #13 W12 — Model training/evaluation
- #14 W13 — RoseChat integration
- #15 W14 — Discord integration
- #16 W15 — EnthusiaStaff review GUI/workflow
- #17 W16 — Deployment/supervisor/operations — **complete/merged**
- #20 W17 — Dataset QA tooling — **complete/merged via PR #22**
- #19 W01 follow-up — Reconcile runtime contract after Policy v1

## Gates

1. W00 must finish and Policy v1 must be merged before W02–W10 generate labeled data.
2. W01 foundation is merged. Issue #19 is blocked on Policy v1 and will reconcile the provisional API/context contract with final owner policy.
3. W11 starts after approved G01–G09 datasets are merged.
4. W12 starts after W11 produces accepted leakage-safe splits.
5. W13–W15 may start once the API/review contracts from W01 stabilize.
6. W16 starts after W01 runtime shape is accepted.
7. No production deployment without explicit authorization.
8. Automatic punishments remain disabled until a separate acceptance decision.

## Dataset strategy

Do not split by first letter. The generator work is partitioned by semantic domain because that produces more even useful coverage and avoids strong letter-distribution bias.

Nine generator workers × 500 examples = **4,500 synthetic examples** before curated production-derived samples.

## Next coordinator actions

1. Launch W12 from the accepted W11 leakage-safe manifests and frozen evaluation sets.
2. Release W13–W15 against the now-stable post-W19 API/review contract where parallel work is useful.
3. Keep all training/evaluation and client work pre-deployment; no live AI service or punishment enablement without a separate authorization.
4. Require exact-head CI and independent coordinator review before each downstream merge.


## Worker handoff correction

Future worker launch packets must follow `docs/WORKER-LAUNCH-STANDARD.md`: either one downloadable file or one self-contained copy/paste message containing the complete project/task context. Do not rely on workers inferring missing information from the coordinator chat.

W00/W01 received corrective issue comments after launch. Policy work must review `policy/SOURCE-BASELINE.md`, including the current public website rules and current RoseChat/EnthusiaStaff behavior.

Interview/data work must emphasize minimal contrasting pairs, split-message cases, false-positive traps, false-negative traps, and source-policy conflicts rather than isolated obvious examples.


## W01 merge checkpoint

PR #18 was coordinator-reviewed and merged on 2026-10-01.

- Final PR head: `6ba61295c41e231f03693cbb22f5cd2739a727a6`
- Merge commit on `main`: `11f3eaa7b43a830ade0255a375edcce6fc85b13f`
- Exact-head PR CI: success
- Post-merge `main` CI run #7: success
- W01 issue #2: closed/completed
- No production deployment was authorized or performed.

The merged runtime is a foundation, not the frozen Policy-v1 API contract. Follow-up issue #19 tracks post-policy reconciliation for:
- action vs review/containment separation;
- richer final labels/reason metadata;
- cross-scope/incident context;
- restart context continuity;
- exempt-scope handling;
- schema migrations;
- final retroactive/related-message contract.


## W17 merge checkpoint

PR #22 was coordinator-reviewed and merged on 2026-10-02.

- Final PR head: `90bc437a1de08ef89bf4dcf5e599e5327d188928`
- Merge commit on `main`: `1c1e5de63b0952ce6b6bd52d68c1ccb741118605`
- Exact-head service-ci run #14: success
- 16 focused dataset-QA tests
- CodeRabbit Unicode JSONL parsing finding fixed and resolved
- Issue #20: closed/completed
- No production data used and no policy decisions invented
- No hosted Codacy status exists for this repository/PR; no Codacy result is claimed

W02–W10 must use the merged dataset-QA tooling before opening their generator PRs. W11 still owns final deduplication decisions, accepted family grouping, and leakage-safe splitting.


## W16 merge checkpoint

W16 deployment/supervisor preparation is complete. No production deployment was performed.

AI-Moderation-API:
- PR #21 merged at `768a86bf95fee16e0b2a88fa23a3fa7c9926c110`.
- PR #23 documentation follow-up rebased to current main and merged.
- Final PR #23 head: `7b4e6147754d4ce9126d1966a0ff12de6ba8869d`.
- PR #23 merge commit: `22123862c363ac90d631dfa00d51db1c9a261355`.
- Exact-head service-ci #16: success.
- Runtime secret guidance now explicitly requires Pterodactyl/process environment injection; dotenv files are not auto-loaded.

enthusia-support-bot:
- PR #6 supervisor companion is merged.
- Final PR #6 head: `a8a7eb53e8e5255063f8facae3a3d66ff7627c21`.
- Merge commit: `61e635f9147c11f0262ae157acb8b521582cc2c8`.
- Exact-head Check workflow #695: success.
- AI service is supervised as optional/non-critical with bounded backoff and health checks.
- Critical Ticket Bot exits preserve a non-zero supervisor/container exit code.
- AI liveness/readiness tests cover 200/200, 200/503, and failed liveness.

Issue #17 is closed/completed.

Production status:
- no Pterodactyl restart;
- no live package installation;
- no AI service deployment;
- no production-data mutation;
- no secrets committed.


## W00 / Policy v1 merge checkpoint

Policy v1 was coordinator-reviewed and merged via PR #24.

- Accepted W00 head: `082dba9c9e959af4abd119cd7542b1348f5edcfd`
- Merge commit: `4b101a687adb88317f0c1c09df5bc1c442be7f75`
- Exact-head service-ci #19: success
- 84 recorded interview decisions/notes after owner clarification W00-079
- Discord ticket channels: completely exempt
- Discord staff-only channels: completely exempt
- Direct targeted staff abuse: BLOCK + strike
- Remaining unresolved edges are tracked in `policy/UNRESOLVED-DECISIONS.md`

Immediate parallel work authorized:
- #19 runtime/API/storage/context reconciliation with Policy v1
- #25 dataset-QA vocabulary/schema reconciliation with Policy v1
- #26 owner-policy golden acceptance set

W02–W10 remain blocked until #25 is accepted and generator launch packets are refreshed against final Policy-v1 QA schema.


## Policy-v1 QA + golden-set checkpoint

W17 Policy-v1 QA reconciliation:
- PR #27 merged.
- Final head: `5ea5c23acf681108aaef3ec47eb04eb12639210f`
- Merge commit: `e7e567d32402d0e6fbf97a1f37ea0e3b840e1b89`
- Exact-head service-ci #21: success.
- 65 tests on that exact PR head.
- G01–G09 records now require Policy-v1 outcome dimensions and use centralized vocabulary.
- Issue #25 closed/completed.

W18 owner-policy golden acceptance set:
- PR #28 merged after coordinator reconciliation.
- Final accepted head: `589e8d539e3c7bf353370c72d6a5d2bacbbe8d89`
- Merge commit: `be1e614c086ec91021e85d4ed7fff95b2d9fc45c`
- Exact-head service-ci #26: success.
- Post-merge main service-ci #27: success.
- Full repository tests on accepted head: 74 passed.
- 52 direct owner-policy fixtures + 35 policy-engine assertions.
- All 84 W00 interview records have traceability coverage.
- All 9 unresolved Policy-v1 edges remain unresolved.
- W00-043 quoted/condemning-slur strike ambiguity is clarified by later W00-076; OPV1-0045 is BLOCK + strike.
- Three Policy-v1-only provenance gaps remain explicitly marked (mirror dedupe, fail-open/missing-memory, working ~24h recent-threat safety-check rule).
- Issue #26 closed/completed.

Dataset generation gate is now open for W02–W10. Generator workers must:
- use Policy v1 and merged dataset QA;
- treat the owner golden set as evaluation/acceptance, not training data;
- avoid exact/trivial golden-set leakage;
- preserve unresolved policy edges rather than inventing answers;
- submit 500-record domain PRs for later W11 cross-corpus dedupe/leakage integration.

Issue #19 runtime/API reconciliation remains independent and may continue in parallel.


## Synthetic generator wave released

W02–W10 are now authorized to start from live `main`.

Complete self-contained launch packets were added in commit `c0dbbb817a020ec86bbf08bde1bed0f099d7cde2`:

- W02 / G01: `workers/handoffs/W02-G01-synthetic-dataset-launch.md`
- W03 / G02: `workers/handoffs/W03-G02-synthetic-dataset-launch.md`
- W04 / G03: `workers/handoffs/W04-G03-synthetic-dataset-launch.md`
- W05 / G04: `workers/handoffs/W05-G04-synthetic-dataset-launch.md`
- W06 / G05: `workers/handoffs/W06-G05-synthetic-dataset-launch.md`
- W07 / G06: `workers/handoffs/W07-G06-synthetic-dataset-launch.md`
- W08 / G07: `workers/handoffs/W08-G07-synthetic-dataset-launch.md`
- W09 / G08: `workers/handoffs/W09-G08-synthetic-dataset-launch.md`
- W10 / G09: `workers/handoffs/W10-G09-synthetic-dataset-launch.md`

Each worker owns exactly 500 IDs, must use merged Policy-v1 QA, must avoid exact/trivial golden-set leakage, must not invent unresolved policy, and must open (not merge) one PR for coordinator/W11 review.

Issue #19 runtime/API reconciliation continues independently in parallel.


## Coordinator consolidation checkpoint — 2026-10-02

Accepted and merged generator PRs:
- G01 / PR #34 — merge `8d4df80b9513e42a0e0b690bb4cb79aebe2fac38`
- G02 / PR #31 — merge `5592c5c84d2a1efba41fcbdf72f8304ebdcbf0bc`
- G04 / PR #36 — merge `ccba2f3583419f0c35beb68e9e09e592f24c682d`
- G05 / PR #30 — merge `23341673cff72583b52c7ed53b10c5974f305176`
- G06 / PR #38 — merge `f7b3e49bd6c594c5ed82c5069e0b7db5a567bf33`
- G07 / PR #33 — merge `f021fe24e665049a9a9df70e2fcdc9d01c49ab9a`
- G09 / PR #35 — merge `38e4919ba199578853eaaee20a644ebec89942e4`

Latest main service-ci after these merges: #55 success.

Still blocked on revision:
- G03 / PR #32 — excessive identical message-text reuse across unrelated family IDs; 74 repeated text-sequence groups / 170 records, including 35 same-profile/same-outcome redundant groups.
- G08 / PR #37 — 28 repeated text-sequence groups / 63 records assigned to separate families; 5 redundant same-profile/same-outcome groups; two exact cross-worker duplicates against accepted G01 (G08-0441 vs G01-0281, G08-0459 vs G01-0321).
- Runtime Policy-v1 PR #29 — two PENDING-event recovery blockers:
  1. failed finalization/process crash can strand an idempotency key in PENDING indefinitely;
  2. a mirror arriving while canonical processing is PENDING is not registered as an alias, so fail-open mirror copies can become undeletable/unlinked.
  Coordinator comments on those PRs define the required regression fixes.

W11 must not start until G03 and G08 are corrected, accepted, and merged. W13/W14/W15 should not treat #29 as frozen until its recovery blockers are fixed and #29 is accepted.


## Consolidation correction / live gates

Runtime:
- PR #29 is now merged at `19f828fb10e7e2fd286161d11b230490bf0fbb5a`.
- Two PENDING-event recovery defects identified before merge are **not resolved by that merge**.
- Issue #39 / W19 is now the authoritative fix-forward task.
- W13/W14/W15 remain blocked from treating the runtime contract as frozen until #39 is reviewed and merged.
- No production deployment has occurred, so this is a pre-deployment correctness repair rather than a live rollback.

Accepted synthetic datasets already integrated into `main`:
- G01, G02, G04, G05, G06, G07, G09.
- Their redundant still-open generator PRs were closed after confirming their commits are already present on main.
- Original issues #3, #4, #6, #7, #8, #9, and #11 are closed/completed.

Still blocked:
- G03 / issue #5 / PR #32 — diversity/family cleanup required.
- G08 / issue #10 / PR #37 — family/cross-worker leakage cleanup required.

Fresh-runtime continuation packets:
- `workers/handoffs/W19-pending-runtime-recovery-launch.md`
- `workers/handoffs/W04-G03-diversity-cleanup-launch.md`
- `workers/handoffs/W09-G08-leakage-cleanup-launch.md`

W11 remains blocked until corrected G03 and G08 are accepted and integrated. Runtime client integration remains blocked until W19 is accepted.


## Dataset-wave completion + W11/W19 checkpoint — 2026-10-02

This section supersedes the earlier G03/G08/W11 gate text above.

Synthetic dataset completion:
- G03 / issue #5 / PR #32 accepted at final head `2b96f95850c2a339656c0c330fe5ba2b440075de`.
- G03 merge commit: `07cb2af21459983be036134a17a14b590fe8c56b`.
- G03 exact-head service-ci #59: success.
- G03 post-merge main service-ci #61: success.
- G03 final cleanup rewrote 53 redundant same-profile/same-outcome exact-sequence copies; 39 / 82 exact-wording contrast groups remain, all family-grouped; exact accepted-corpus and golden collisions were 0.
- G08 / issue #10 / PR #37 accepted at final head `638761d46bb8ada03f6023815743e7c35bdc8fdb`.
- G08 merge commit: `49dc7fb0e443351f346fb846c55fcaf6aea5c947`.
- G08 exact-head service-ci #60: success.
- G08 post-merge main service-ci #62: success.
- G08 final cleanup removed all 5 redundant exact groups and the two accepted-G01 collisions; 23 / 53 exact-wording contrast groups remain, all family-grouped; exact accepted-corpus and golden collisions were 0.
- Issues #5 and #10 are closed/completed.
- All G01–G09 datasets are now accepted and merged: exactly 4,500 synthetic records are available for W11.

W11:
- issue #12 is now unblocked.
- fresh self-contained packet: `workers/handoffs/W11-dataset-integration-launch.md`.
- packet commit on main: `d3b39682b090221a9f4b2c037c7f553a755fa19f`.
- W11 must still create `w11/dataset-integration` from live main, protect the owner golden set from training leakage, reconcile cross-worker families/near duplicates/contradictions, and produce deterministic family-safe train/validation/test plus frozen adversarial manifests.
- W12 / issue #13 remains downstream of accepted W11 integration artifacts.

W19 runtime recovery:
- issue #39 remains the authoritative pre-deployment runtime gate.
- branch `w19/pending-recovery` was created from the clean post-dataset main.
- PR #40 is open: `W19: recover stale PENDING moderation events safely`.
- last observed PR #40 head at this checkpoint: `05013eb4033f6202d1c5ede5187ea5ec83dd0cb0`.
- implementation direction is schema-v2 durable reservation token + lease timestamp, CAS stale takeover, token-guarded finalization, alias-first PENDING mirrors, bounded pending replay wait, and original-canonical-request recovery.
- focused recovery/mirror/migration tests are included.
- exact-head service-ci #63 was still in progress when this checkpoint was written; do not treat W19 as accepted until current-head CI and coordinator review are green.
- W13/W14/W15 remain blocked on accepted W19.

Production status is unchanged:
- no AI moderation service deployment;
- no Pterodactyl restart;
- no live package/config mutation;
- no production moderation-data mutation;
- no punishment enablement.


## W19 runtime recovery completion — 2026-10-02

W19 / issue #39 is complete.

- PR #40 final head: `2954bd53b04472537ddfef9622832882b2d8c348`
- Merge commit: `917aef4e97c539fea89d558f9e1be9d0d506b4a4`
- Exact-head service-ci #67: success
- Post-merge main service-ci #69: success
- Exact-head suite: 95 tests plus Ruff, strict mypy, complexity, dataset QA, and wheel build
- SQLite schema v2 adds durable PENDING reservation ownership/lease state.
- Stale retry takeover is atomic and token-guarded; superseded workers cannot finalize.
- PENDING mirror aliases are persisted and later replay resolves all known platform copies.
- Simultaneous first-arrival canonical/mirror reservations preserve one logical event.
- No production deployment, restart, live config change, or production-data mutation occurred.

The runtime/API/review contract is no longer blocked on PENDING-event recovery. W13/W14/W15 may use the merged contract as their source baseline.


## W11 dataset integration completion — 2026-10-02

W11 / issue #12 is complete.

- PR #41 final head: `3b71c0500c41f883fe6c5d462ce8732dfb185d91`
- Merge commit: `5c337488d3014aefda7ba29fc0883b2beaa5dc0d`
- Exact-head service-ci #83: success
- Post-merge main service-ci #84: success
- Exact-head suite: 98 tests plus deterministic W11 regeneration, Ruff, strict mypy, complexity, all G01–G09 validators, and wheel build
- Integrated synthetic source corpus: exactly 4,500 records / 500 per G01–G09
- W11 algorithm: `w11-v2`
- 83 text-only exact groups; 0 redundant same-decision/same-context exact groups; 0 cross-worker exact groups
- 2,722 lexical near candidates; all 27 cross-worker near pairs are integration-family linked
- 12 cross-worker differing-decision near pairs were reviewed against settled Policy-v1 §6/§11 boundaries; 0 unresolved cross-worker contradictions
- 1 synthetic↔golden lexical candidate at 0.760331; 0 golden-sensitive synthetic records at the 0.88 threshold
- 1,883 integration families; largest family 45 records
- Final frozen manifests:
  - train: 3,269
  - validation: 385
  - test: 410
  - frozen adversarial: 436
- Owner golden set remains separate from ordinary training.

Canonical W11 artifacts:
- `data/integration/W11-audit.json`
- `data/integration/W11-split-manifest.json`
- `data/integration/W11-adversarial-eval-manifest.json`
- `docs/W11-DATASET-INTEGRATION-REPORT.md`

W12 / issue #13 is now unblocked. It must consume these accepted manifests without reshuffling families or tuning on test/frozen/golden acceptance evidence.

## W12-W15 next-wave release checkpoint — 2026-10-02

This section supersedes earlier text that described W12 or client integrations as blocked.

Accepted upstream gates:
- W19 PENDING/mirror recovery is merged and post-merge green (`917aef4e97c539fea89d558f9e1be9d0d506b4a4`, main service-ci #69).
- W11 dataset integration is merged and post-merge green (`5c337488d3014aefda7ba29fc0883b2beaa5dc0d`, main service-ci #84).
- W11 frozen split algorithm is `w11-v2`: 3,269 train / 385 validation / 410 test / 436 frozen adversarial; owner golden remains separate.

W12 / issue #13:
- unblocked and released;
- fresh packet: `workers/handoffs/W12-model-training-launch.md`;
- packet added at `a1dae9849bf622b3f4c8502168bce27f6d90fddb` and clarified on main at `5f25155bd9ef34ac75a527736876dbf56afd9bc8`;
- target branch: `w12/model-training` in this repository from live main;
- train may use only W11 train; validation is the only tuning/calibration partition; test/frozen/golden remain acceptance-only;
- requires baseline + at least two small pretrained CPU/ONNX candidates, critical Policy-v1 slice metrics, calibration, quantized CPU benchmarks, artifact checksums, and a fail-open runtime adapter;
- no production deployment is authorized.

W13 / issue #14:
- unblocked and released;
- target repository: `wsg138/Enthusia-RoseChat`;
- fresh packet: `workers/handoffs/W13-rosechat-client-launch.md`;
- packet commit: `e7be369a62f4421f85f7b22a3ce423b75ca72804`;
- target branch: `w13/rosechat-client` from live RoseChat `master`;
- preserve bounded hold, late-delete, circuit, generation-fence, and fail-open lifecycle while replacing/bypassing legacy local OpenAI threshold/strike authority with the central service;
- do not remove DiscordSRV/chat transport or deploy.

W14 / issue #15:
- unblocked and released;
- target repository: `wsg138/enthusia-support-bot`;
- fresh packet: `workers/handoffs/W14-discord-client-launch.md`;
- packet commit: `c961655655d229cea92f1417e1a2b976c9806f36`;
- target branch: `w14/discord-client` from live support-bot main;
- use the existing Discord gateway only; ticket/staff/configured-exempt surfaces remain outside semantic moderation; Ticket Bot readiness remains independent of AI health;
- mirror canonical IDs must come from authoritative transport metadata, never text matching;
- no deployment or automatic punishment.

W15 / issue #16:
- unblocked and released;
- target repository: `wsg138/EnthusiaStaff`;
- fresh packet: `workers/handoffs/W15-staff-review-gui-launch.md`;
- packet commit: `d68cd57153e6bd645214a7724bf8712d8d89cc8c`;
- target branch: `w15/staff-review-gui` from live Staff main;
- reconcile live parallel moderation/reopening PRs, especially #302/#214 if still open, before editing;
- reuse Staff async report-GUI safety patterns, but central review/correction state remains authoritative;
- AI review/correction must not automatically create a punishment or revive the legacy RoseChat AI mute path.

Observed target heads when packets were prepared:
- RoseChat `master`: `0425b7d2c2252f8287af93c12d13e1e4c5e686f4`;
- support-bot `main`: `61e635f9147c11f0262ae157acb8b521582cc2c8`;
- EnthusiaStaff `main`: `24d2ab5f60c097ee303f5c9342a9503f44e8b821`.

Those observations were used to stage the initial launch branches. Workers must still re-read live GitHub before their first product commit and reconcile any upstream movement.

Launch branches staged:
- W12: `w12/model-training` in AI-Moderation-API at packet-amended base `5f25155bd9ef34ac75a527736876dbf56afd9bc8`;
- W13: `w13/rosechat-client` in Enthusia-RoseChat from `0425b7d2c2252f8287af93c12d13e1e4c5e686f4`;
- W14: `w14/discord-client` in enthusia-support-bot from `61e635f9147c11f0262ae157acb8b521582cc2c8`;
- W15: `w15/staff-review-gui` in EnthusiaStaff from `24d2ab5f60c097ee303f5c9342a9503f44e8b821`.

No product commits existed on W13-W15 at branch creation.

Production status remains unchanged:
- no AI moderation service deployment;
- no Paper/Ticket Bot/Staff restart;
- no live package/config/firewall mutation;
- no production moderation-data mutation;
- no automatic punishment enablement.


## Live coordinator checkpoint — 2026-10-05

This section supersedes older W12-W15 status text above. Live GitHub remains authoritative if any SHA/status below moves.

### Current critical path

1. **W20 / issue #43 — fresh unseen W12-v2 acceptance set**
   - Required because PR #42's original test/frozen-adversarial/owner-golden evidence was observed before a later material preprocessing correction.
   - W20 must be built independently from Policy v1/project requirements without inspecting W12 individual model failures or predictions.
   - Exact/trivial leakage against every W11 partition and owner golden must be zero/reviewed before freeze.
   - Once frozen, W12 v2 gets one acceptance run. Any later semantic model/preprocessing/threshold change burns that set and requires a new unseen set.

2. **W12 / issue #13 / PR #42 — model training/evaluation/runtime adapter**
   - Live branch: `w12/model-training`.
   - Current observed head: `3aac90ca8d0d57ca2174a852f961c6b753e7205d`.
   - PR remains **draft** and is **not merge-ready**.
   - A later audit corrected train/runtime serialization parity, canonical speaker ordering, target-relative timing, removal of post-target future messages, and empty/mis-keyed critical slices.
   - Using W11 train + validation only, v2 selection remains `baseline-tfidf`; BERT Mini and BERT Tiny were comparison candidates.
   - Previously opened W11 test/frozen-adversarial/owner-golden evidence is development/superseded evidence for the old preprocessing contract and must not accept v2.
   - Current hosted Codacy summary on PR #42 reports new findings and must be reviewed/cleared before acceptance/merge.
   - No production deployment has occurred.

3. **W15 / issue #16 / EnthusiaStaff PR #318 — Staff review queue/GUI**
   - Product PR remains open.
   - Current observed head: `e3d84f9bb861c04dfba543cd5eca66b52ce3dfaa`.
   - Earlier issue comments that called `1317e92...` the final reviewed head are superseded by later commits.
   - Current-head review/static-analysis reconciliation is still required before merge.
   - Central review/correction state remains authoritative; W15 must remain optional/fail-safe and must not dispatch automatic punishment.

4. **Final cross-platform integration seam**
   - W13 RoseChat and W14 Discord clients are merged.
   - The real Minecraft→Discord transport still must carry the authoritative W13 canonical-message metadata into W14's mirror registry.
   - W14 intentionally does not infer mirrors by matching message text.
   - Verify exact related-message deletion across Minecraft/Discord only after this metadata handoff is wired.

5. **Shadow deployment and acceptance**
   - After W12 + W15 + mirror handoff are accepted, deploy the central moderation service and clients in shadow/observability-first mode.
   - Preserve fail-open behavior for Minecraft/Discord chat.
   - Keep OpenAI optional/advisory and off the critical latency path.
   - Do not enable automatic punishment during initial shadow evaluation.
   - Review real disagreements/false positives/false negatives, promote only reviewed/redacted examples, then retrain/version deliberately.

### Completed downstream integrations

**W13 — RoseChat central moderation client: accepted/merged**
- Enthusia-RoseChat PR #18 accepted head: `1ba4a736290cd797a3f8d9ae385877b1982de46a`.
- Merge commit: `831aadda7e1de28c07ea2ad4e6a4b09ce2af24a2`.
- Follow-up async circuit-breaker test-race fix merged afterward; post-fix master build succeeded.
- Central service is the semantic authority in central mode; bounded hold, late-delete, generation fencing, circuit/fail-open behavior remain preserved.

**W14 — Discord central moderation client: accepted/merged**
- enthusia-support-bot PR #9 accepted head: `04c0900c44b824d02f2e0c0c25b0fd5fa1572ecd`.
- Squash merge: `a0d58937d34479b12dce77ebfd9e2e929fb8943a`.
- Ticket/staff/configured-exempt content is excluded before semantic moderation.
- BLOCK deletion is bounded to exact authoritative Discord message/version refs.
- Review/strike/containment/support output does not automatically punish.
- Ticket Bot readiness remains independent of moderation health.

### Relationship to wsg138/Enthusia-AI

Do **not** merge the moderation classifier/model into the general support LLM.

The Enthusia-AI master specification already defines moderation as a separate operational path and separate model/workload. Its `services/moderation-adapter` is specifically designed to call this external moderation service without coupling health.

Recommended production topology:
- same Bloom physical host is fine;
- shared overall machine resources are fine when explicitly capped/benchmarked;
- keep moderation and general support inference in separate processes, preferably separate Pterodactyl splits;
- a support-model crash/OOM/restart must not take moderation offline;
- moderation failure must not break chat;
- repositories may share contracts/integration documentation, but keeping independent release/model lineage is intentional.

### Production status

As of this checkpoint:
- no AI moderation service production deployment;
- no production model acceptance;
- no automatic punishment enablement;
- no production moderation-data mutation;
- no authorization to turn a support-model deployment/restart into a moderation restart;
- deployment should proceed only after W12 final acceptance, W15 current-head acceptance, mirror metadata handoff, and exact-head integration evidence.
