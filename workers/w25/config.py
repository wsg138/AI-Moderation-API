"""Frozen W25 experiment configuration.

Model revisions are immutable Hugging Face commit SHAs. W25 may compare these
architectures, but it must not inspect or consume W20 acceptance evidence while
developing or selecting a candidate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    key: str
    hf_id: str
    revision: str
    license: str
    max_length: int
    role: str


MODEL_SPECS = {
    "modernbert-base": ModelSpec(
        key="modernbert-base",
        hf_id="answerdotai/ModernBERT-base",
        revision="8949b909ec900327062f0ebf497f51aef5e6f0c8",
        license="Apache-2.0",
        max_length=8192,
        role="candidate-1-and-verifier",
    ),
    "deberta-v3-xsmall": ModelSpec(
        key="deberta-v3-xsmall",
        hf_id="microsoft/deberta-v3-xsmall",
        revision="79c19681226cddc96fe1d9625c8a3ed6dac79624",
        license="MIT",
        max_length=512,
        role="candidate-2-development-and-cascade-screen",
    ),
    "deberta-v3-small": ModelSpec(
        key="deberta-v3-small",
        hf_id="microsoft/deberta-v3-small",
        revision="b25b093541eedd589b3fd60c30142da149189960",
        license="MIT",
        max_length=512,
        role="candidate-2-development",
    ),
    "canine-s": ModelSpec(
        key="canine-s",
        hf_id="google/canine-s",
        revision="afe7189a311a3ba3601525f03a98bb9e3d8a357e",
        license="Apache-2.0",
        max_length=4096,
        role="candidate-3",
    ),
}

NEURAL_SEEDS = (42, 138, 2026)
SERIALIZATION_VARIANTS = ("raw", "raw+normalized")
SUITES = (
    "balanced_policy",
    "real_distribution",
    "adversarial_evasion",
    "context",
    "time_based_real_chat",
)

CONSEQUENCE_TARGETS = {
    "review": {"mode": "recall_first"},
    "block": {"precision": 0.99},
    "strike": {"precision": 0.995},
    "containment": {"precision": 0.999},
}

PREVALENCE_LEVELS = (0.0005, 0.001, 0.005, 0.01)

W12_BERT_MINI_RUN_ID = 37_225_843_627
W12_BERT_MINI_SOURCE_HEAD = "3aac90ca8d0d57ca2174a852f961c6b753e7205d"
W12_BERT_MINI_ARTIFACT = "w12-bert-mini-3aac90ca8d0d57ca2174a852f961c6b753e7205d"
W12_BERT_MINI_ARTIFACT_SHA256 = (
    "41eb6d4123b17e789bb1802e97138b8b55bca3829cefe4847ba1d6d9eb61e1e3"
)

W20_MARKERS = (
    "w20",
    "fresh-acceptance",
    "acceptance-set",
    "fresh_acceptance",
)
