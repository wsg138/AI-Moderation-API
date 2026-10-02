# Coordinator state

Last updated: 2026-10-01

## Current phase

**Phase 0 — owner policy interview; API foundation merged**

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

1. Continue W00 until Policy v1 is complete and reviewed.
2. Review/merge Policy v1.
3. Run #19 to reconcile the runtime contract with Policy v1.
4. Release W02–W10 simultaneously once policy/schema are stable.
5. Review dataset PRs for scope, quality, duplication, and policy consistency.


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
