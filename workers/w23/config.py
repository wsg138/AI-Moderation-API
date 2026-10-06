"""W23 experiment constants.

Everything in this module is declared before validation evaluation so operating
point selection is explicit and reproducible.
"""

from __future__ import annotations

SEED = 42
OOF_FOLDS = 3
BERT_OOF_EPOCHS = 5
BERT_BATCH_SIZE = 16
BERT_LR = 3e-5

WORD_MAX_FEATURES = 30_000
CHAR_GRID: tuple[tuple[tuple[int, int], int], ...] = (
    ((3, 5), 30_000),
    ((3, 5), 60_000),
    ((3, 6), 30_000),
    ((3, 6), 60_000),
    ((4, 6), 30_000),
    ((4, 6), 60_000),
)

IMPORTANT_BENIGN_SLICES = (
    "minecraft_gameplay",
    "benign_hard_negatives",
    "generic_minecraft_violence",
    "long_gap_non_linkage",
    "slur_reference_only",
    "private_flirting",
    "age_self_report_only",
    "minecraft_tnt",
)

BLOCK_RECALL_RATIO_FLOOR = 0.97
BLOCK_SLICE_FPR_TOLERANCE = 0.01
MATERIAL_BLOCK_PRECISION_GAIN = 0.01
STRIKE_RECALL_RATIO_FLOOR = 0.80
AUTO_PUNISHMENT_PRECISION_FLOOR = 0.99

SCREENING_THRESHOLDS = tuple(i / 100 for i in range(5, 81, 5))
BLOCK_THRESHOLDS = tuple(i / 100 for i in range(35, 96, 5))
STRIKE_THRESHOLDS = (
    0.50,
    0.60,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.925,
    0.95,
    0.975,
    0.99,
)

EVASION_SAMPLE_SIZE = 512
W12_BERT_ARTIFACT_RUN = 37_225_843_627
W12_BERT_ARTIFACT_NAME = "w12-bert-mini-3aac90ca8d0d57ca2174a852f961c6b753e7205d"
W12_BERT_MODEL_HEAD = "3aac90ca8d0d57ca2174a852f961c6b753e7205d"
