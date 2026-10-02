# Worker system

The project uses independent workers with narrow ownership. GitHub is the coordination ledger.

## Rules for every worker

1. Read the canonical policy/schema docs before doing work.
2. Re-read the assigned GitHub issue immediately; live GitHub is authoritative.
3. Work only on the branch named in the issue.
4. Do not silently broaden scope.
5. Do not deploy or modify production unless the issue explicitly authorizes it.
6. Do not commit secrets or raw production chat.
7. Record assumptions and unresolved questions in the PR/issue.
8. Open one PR back to `main`.
9. Do not merge your own PR unless the coordinator explicitly instructs it.
10. Generated dataset records must validate against the canonical schema and ID range.

## Phases

### Phase 0 — Policy interview
One worker interviews the owner in short batches, focusing on ambiguous/hard cases. It produces:
- `policy/POLICY-v1.md`
- `policy/interviews/<date>-owner-interview.jsonl`
- seed labeled examples;
- unresolved edge cases.

Dataset generator workers must wait for Policy v1.

### Phase 1 — Dataset generation
Nine workers each generate 500 examples in a distinct semantic domain. This is intentionally not alphabetical: semantic partitioning gives more even useful coverage and avoids wasting workers on letters with poor phrase distributions.

Planned domains:
1. Minecraft gameplay/PvP/property/roleplay.
2. Real-world threats/stalking/doxxing/offline harm.
3. Harassment/profanity/bullying/social exclusion.
4. Self-harm instructions vs self-disclosure vs game language.
5. Hate/identity attacks/slurs/quoted or counterspeech context.
6. Sexual/minor/grooming/age ambiguity.
7. Dangerous real-world instructions/explosives/weapons/illicit harm.
8. Evasion/obfuscation/split messages/multi-message context/adversarial phrasing.
9. Benign everyday chat/arguments/jokes/quotes/normal Discord+Minecraft hard negatives.

Each worker gets a fixed ID prefix and 500-record quota.

### Phase 2 — Dataset integration
A dedicated integrator:
- schema-validates;
- exact-deduplicates;
- near-deduplicates;
- detects contradictory labels;
- checks class/action/domain balance;
- groups paraphrase families;
- creates leakage-safe train/validation/eval sets;
- produces statistics and audit report.

### Phase 3 — Model
Model worker:
- selects small pretrained encoder;
- fine-tunes on owner-approved dataset;
- benchmarks precision/recall/confusion by policy class;
- exports ONNX;
- benchmarks CPU latency/memory;
- does not declare production-ready from aggregate accuracy alone.

### Phase 4 — Runtime/integrations
Separate workers own:
- central API/context/storage/OpenAI advisory path;
- RoseChat client/fail-open/retroactive deletion;
- Discord Ticket Bot client;
- EnthusiaStaff review queue/login reminder/GUI/evidence bridge.

## Coordinator

The coordinator:
- protects canonical policy;
- resolves worker conflicts;
- reviews PRs;
- prevents duplicate scope;
- controls merge order;
- keeps handoffs concise so worker chats can be recycled safely.
