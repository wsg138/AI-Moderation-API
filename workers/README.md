# Worker packages

GitHub issues are the authoritative task cards. This folder contains durable handoff templates when a worker chat needs to be recycled.

Planned ownership:

| Worker | Scope | Output |
|---|---|---|
| W00 | Owner policy interview | Policy v1 + interview JSONL |
| W01 | API/runtime foundation | Service/API/context/storage |
| W02 | Gameplay dataset | 500 examples, prefix G01 |
| W03 | Real-world threat dataset | 500 examples, prefix G02 |
| W04 | Harassment dataset | 500 examples, prefix G03 |
| W05 | Self-harm dataset | 500 examples, prefix G04 |
| W06 | Hate/identity dataset | 500 examples, prefix G05 |
| W07 | Sexual/minor dataset | 500 examples, prefix G06 |
| W08 | Dangerous instructions dataset | 500 examples, prefix G07 |
| W09 | Evasion/context dataset | 500 examples, prefix G08 |
| W10 | Benign/hard-negative dataset | 500 examples, prefix G09 |
| W11 | Dataset integration/QA | dedupe + splits + audit |
| W12 | Model training/evaluation | trained/exported ONNX + metrics |
| W13 | RoseChat integration | API client + fail-open + context actions |
| W14 | Discord integration | Ticket Bot client + Discord message actions |
| W15 | EnthusiaStaff review workflow | login reminder + GUI + evidence/review |
| W16 | Deployment/operations | Ticket Bot supervisor + health/rollback |

Dataset workers wait for W00/Policy v1.
