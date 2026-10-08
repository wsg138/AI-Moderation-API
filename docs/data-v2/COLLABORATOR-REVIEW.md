# Data/Model v2 — collaboration review brief

This is a **public-safe discussion brief** for people who offered advice on dataset organization and training order. It is not an invitation to share raw logs, private evidence, or player identities.

## What help is most useful right now

We need a **dataset and experimental-design reviewer**, not 50 workers writing consecutive offensive examples. The real difficulty is distinguishing ordinary Minecraft/Discord language from policy violations when context, speaker, target, time, channel, and prior messages change the meaning.

### Questions for an experienced training/data collaborator

1. **Data organization:** Would you maintain separate, immutable sources for real unlabeled chat, verified real labeled windows, approved synthetic hard pairs, weak/pseudo-labels, and frozen evaluations? What manifest fields and lineage rules do you consider essential?
2. **Training order:** What would you train first: a pretrained encoder fine-tuned on verified moderation labels, continued domain-language pretraining on eligible unlabeled Minecraft chat, then hard-negative/contrastive retraining? What *evidence* would cause you to change that order?
3. **Real conversation context:** How should one target message use earlier chat without treating all nearby messages as the same violation? How many preceding turns or seconds would you start with? How do you avoid incorrect speaker matching and bridging AFK gaps or separate servers?
4. **Split leakage:** How would you group entire chat sessions, calendar periods, servers, and synthetic paraphrase families so near-identical messages cannot make a held-out score look artificially good? What are the best approaches to cross-source near-duplicate detection?
5. **Label reliability:** What would your rubric and independent-review/adjudication process look like for disputed grooming, doxxing, self-harm, threats, slur quotation, age context, and ordinary PvP banter? Would you use one strong annotator plus manual spot checks, or double-review critical labels?
6. **Natural SAFE prevalence:** How should benign samples be included so the model does not over-block ordinary chat? Would you preserve a traffic-representative SAFE test distribution alongside separately balanced critical-class challenge sets?
7. **Synthetic examples:** How would you generate real-feeling hard pairs without making fake conversations that are all threats/slurs in a row? How would you measure diversity, contextual realism, and accidental label contradictions?
8. **99% evaluation:** Which metrics, per-class sample sizes, uncertainty routing and false-block-per-1,000-SAFE criteria would convince you an auto-block system is truly ready? How would you measure abstention/review cost?
9. **Training resource decisions:** What small controlled ablations would you run before paying for a large GPU? What reproducible settings, seed count, early-stopping conditions, and profiling data would you require?

### Useful artifacts a collaborator can contribute safely

- A reviewed **manifest/registry schema** proposal, with synthetic placeholder records only.
- A **split/contamination audit checklist** and small tests using synthetic fixtures.
- A **blind label-review rubric** and examples constructed or licensed for sharing.
- A **training-order memo** with explicit comparison experiments and proposed metrics.
- A **natural-context quality rubric**: ordinary chat interleaved with hard cases, channel and target indices valid, no future messages, realistic time gaps.

Do not request original Minecraft logs or claim their owners agreed to donate them. Player logs may contain third-party identifiers and sensitive material. Obtain specific permission and use a privacy-reviewed local extraction/redaction process before discussing transfer. An anonymized speaker column alone is insufficient.

## Proposed conversation / VC agenda (30–45 minutes)

- 5 min: project objective, Policy v1, 94% action / ~79% full-decision historical baseline, and why this is insufficient.
- 10 min: show the schema and *synthetic* sample examples; discuss realistic context and labeled-vs-unlabeled source separation.
- 10 min: split strategy, dedupe, human review and policy disagreement.
- 10 min: choose cheap first training experiments and explicit compute budget gates.
- 5 min: name one deliverable each, assign a GitHub tracking issue, agree on review criteria.

A collaborator's opinions are input to the coordinator/owner. Nothing enters training solely because it was suggested in chat or passed structural JSONL validation.
