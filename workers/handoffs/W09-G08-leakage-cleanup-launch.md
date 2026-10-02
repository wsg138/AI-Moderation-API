# G08 cleanup launch packet — Adversarial corpus family/leakage repair

## Identity

You are a **fresh cleanup worker** for W09 / G08.

Existing issue: **#10**.
Existing PR: **#37 — Add G08 evasion and adversarial-context synthetic dataset**.
Existing branch: `w09/dataset-evasion-context`.
Current reviewed head before your changes: `0add0950a656ef7f9821d6997ccda79735e9e028`.

Continue the existing branch/PR. Do not open a second G08 PR.

## Why revision is required

The adversarial coverage is useful and CI is green, but coordinator leakage audit found family/duplicate problems.

Reviewed-head findings:

- 28 identical normalized message-text sequence groups;
- 63 / 500 records participate;
- all 28 groups currently have different family IDs;
- 23 groups vary channel/profile and may be useful contrasts, but exact wording must be grouped together;
- 5 groups are redundant same-profile/same-outcome repeats and must be rewritten;
- two exact normalized cross-worker duplicates exist against already accepted G01:
  - G08-0441 duplicates G01-0281;
  - G08-0459 duplicates G01-0321.

## Mandatory reading

Read:

- PR #37 conversation and coordinator revision comment;
- issue #10;
- existing G08 JSONL/report;
- accepted `data/synthetic/G01-gameplay.jsonl` on current main;
- Policy v1;
- Dataset schema/QA docs;
- owner golden-set docs/data;
- current `COORDINATOR-STATE.md`.

## Preserve exactly

Keep:

- exactly 500 IDs `G08-0001..G08-0500`;
- original eight coverage buckets:
  - 100 split-message threat/context reversal;
  - 80 directed self-harm evasion;
  - 80 slur obfuscation/masking/reference;
  - 70 harassment/dogpile adversarial;
  - 60 sexual/minor resolved-policy context;
  - 50 explosive-request context;
  - 40 platform/channel flips;
  - 20 quote/report/reply-vs-endorsement;
- Policy-v1 outcomes;
- unresolved Policy-v1 edges omitted;
- no production data;
- no runtime/client changes.

## Required cleanup

### 1. Re-family intentional exact-wording contrasts

Where the same message sequence is intentionally shown under different channel/profile/context conditions, give every exact-wording variant one shared `family_id`.

Examples include profile flips for Minecraft vs Discord/general/gaming.

### 2. Rewrite redundant repeats

The 5 same-profile/same-outcome identical sequence groups add no adversarial value. Rewrite the redundant copies with genuinely different language/structure.

### 3. Remove cross-worker exact duplicates

Rewrite at minimum:

- G08-0441 so it is not the same normalized sequence as accepted G01-0281;
- G08-0459 so it is not the same normalized sequence as accepted G01-0321.

Also run a full G08-vs-current-main G01–G09 exact text-sequence check, because seven other generator sets are now accepted on main.

Do not copy wording from another worker merely to make a contrast.

### 4. Maintain adversarial diversity

The point of G08 is mechanism diversity:

- split messages;
- obfuscation;
- spacing;
- masking;
- euphemism;
- reply dependence;
- speaker changes;
- context reversal;
- platform/profile flips.

Do not let the cleanup turn G08 into simple single-message paraphrases.

## Required audits

Before finalizing:

1. canonical Dataset QA;
2. message-text-only exact duplicate audit within G08;
3. exact message-text sequence audit against all accepted synthetic files on current main;
4. golden exact/trivial leakage review;
5. family audit proving identical-wording intentional contrasts share one family.

Target:

- zero redundant same-profile/same-outcome exact text-sequence groups;
- zero exact cross-worker sequence duplicates unless coordinator-approved and family-linked by an explicit integration mechanism (prefer rewriting here);
- intentional within-G08 exact wording contrasts all share family IDs.

## Canonical commands

```bash
python -m tools.dataset_qa validate data/synthetic/G08-evasion-context.jsonl --range G08:1-500
python -m tools.dataset_qa report data/synthetic/G08-evasion-context.jsonl --range G08:1-500 --format markdown --output data/synthetic/G08-report.md
```

Run full repository CI on final exact head.

Update PR #37 with:

- exact final head;
- canonical QA result;
- final text-sequence duplicate counts;
- cross-worker exact duplicate count;
- family audit result;
- action/label/channel distributions;
- multi-message/family counts;
- exact-head CI result;
- confirmation no policy/unresolved edge was invented.

Do not self-merge.
