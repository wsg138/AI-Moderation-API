# Worker launch standard

Every future worker handoff must be delivered to the owner in one of two forms:

1. a **downloadable handoff file**, or
2. a **single self-contained copy/paste message**.

Do not send a short pointer that assumes the worker will infer missing context from the coordinator chat.

## Required contents of every handoff

Each worker launch packet must include all information necessary to start correctly:

- project goal and why the work matters;
- exact repository/repositories involved;
- authoritative GitHub issue number and branch;
- current architecture and relevant already-merged work;
- dependencies and upstream/downstream workers;
- scope boundaries and explicit non-goals;
- required source documents/files/URLs to inspect before coding or interviewing;
- existing production behavior that must be preserved;
- failure-safety rules;
- data/privacy/security rules;
- acceptance criteria;
- required tests/evidence;
- expected deliverables/PR behavior;
- deployment prohibition or authorization status;
- known edge cases and contradictions the worker must think about.

The handoff should still tell the worker to read live GitHub because live state is authoritative, but it must not rely on that sentence as a substitute for context.

## Research-before-action rule

Workers must inspect the current sources that govern their task before proposing a design.

Examples for moderation work:

- current public Enthusia rules: `wsg138/enthusia-site/public/rules.html`;
- current RoseChat AI moderation configuration and implementation;
- current EnthusiaStaff moderation/punishment contracts;
- current Discord/Ticket Bot runtime if the task touches Discord;
- existing policy/interview documents in this repository.

If sources conflict, the worker must surface the conflict and ask/resolve it; do not silently choose one.

## Interview-worker standard

Policy interviews must not be generic questionnaires.

Before asking the owner for decisions, the worker must:
1. read the current public rules;
2. read the existing RoseChat moderation behavior;
3. identify policy ambiguities/conflicts;
4. build **minimal contrasting pairs/sets** designed to discover boundaries.

Good contrast families include:

```text
im gonna kill you
im gonna kill you next round
im gonna kill you irl
im gonna kill you when i see you at school

im gonna blow up your house
im gonna blow up your Minecraft house with TNT
im gonna send a bomb to your house

fuck
fuck this game
fuck you
youre a fucking idiot

kys
go kill yourself
kill me bro
i want to die

<slur>
quoted <slur>
someone called me <slur>
dont call people <slur>
```

The goal is not merely to collect labels. The worker should discover **what exact change in context changes the owner's answer**.

For each family, probe:
- single message vs split messages;
- same sender vs different speakers;
- immediate follow-up vs delayed follow-up;
- Minecraft-specific cue vs real-world cue;
- quote/report/counterspeech vs endorsement;
- direct target vs general statement;
- repetition/escalation;
- obvious evasion/obfuscation.

## Dataset-worker standard

Dataset workers must generate examples to challenge the policy, not just paraphrase easy cases.

Every 500-example package should include:
- obvious positive examples;
- obvious negative examples;
- boundary examples;
- minimal pairs;
- multi-message examples;
- misleading/ambiguous context;
- false-positive traps;
- false-negative traps;
- evasions;
- quotes/reports/counterspeech;
- cases modeled after known production failures.

Reports must explain coverage and notable hard families.

## Coordinator responsibility

Before giving any future worker script to the owner, the coordinator should review the packet as if the worker had no access to this chat. If an important assumption lives only in coordinator memory, the handoff is incomplete.
