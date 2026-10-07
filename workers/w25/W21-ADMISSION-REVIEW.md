# W25 review of W21 adversarial/evasion candidates

Source PR: #46  
Source head: `a90aa5835d2f25c4db7743e38cfbad7da3f211fe`

## Admission decision

W21 is approved for W25 development use with a W25-owned family split. It is
not promoted into W11/W12 or production data.

The source contains 500 records in 25 twenty-example families. W21's own QA
reports zero schema errors/warnings and zero exact duplicate groups. Its
accepted-data leakage audit reports zero exact collisions, zero >=0.92 near
collisions, and zero >=0.985 trivial-near collisions against the audited
accepted corpus. W20 was not inspected.

W25 freezes:

- 220 examples / 11 families for adversarial training;
- 100 examples / 5 families for iterative development;
- 180 examples / 9 families for the untouched W25 adversarial comparison suite.

No family crosses partitions.

## Test-family coverage

The frozen test families cover:

- hate/slur obfuscation mechanics;
- real-world threats;
- self-harm;
- sexual content;
- reliable-minor sexual content;
- doxxing;
- dangerous real-world instructions;
- harassment;
- benign hard negatives.

The W21 slur families intentionally use a placeholder token instead of a real
slur lexicon. Those records are therefore evidence for transformation and
context mechanics, not proof of robustness to every production slur spelling.
W25 must not claim otherwise.

## Boundaries

- This admission is W25-only.
- W20 remains forbidden during development and architecture selection.
- W21 test records must never be used for fitting, calibration, threshold
  selection, attack generation, or architecture selection.
- The same frozen W21 train/development/test memberships apply to all five W25
  candidates and baselines that consume admitted development data.
- New adversarial examples may be generated only from training-derived sources;
  final adversarial holdout families remain untouched.
