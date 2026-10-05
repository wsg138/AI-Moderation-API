"""Leakage-safe learned meta ensemble for W23."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from workers.w12.dataset import ModerationExample
from workers.w23.features import RuntimeFeatureEncoder
from workers.w23.modeling import HEAD_CLASS_COUNTS, PredictionBundle, targets

BASE_ORDER = ("word", "char", "combined", "bert")
DISAGREEMENT_HEADS = ("label", "action", "strike", "containment")
DISAGREEMENT_PAIRS = (
    ("word", "char"),
    ("word", "bert"),
    ("char", "bert"),
    ("combined", "bert"),
)

META_FEATURE_CONTRACT = (
    "base-model policy-head probabilities",
    "base-model disagreement indicators",
    "channel profile",
    "serialized context length",
    "serialized text shape/evasion indicators",
)


@dataclass
class MetaEnsemble:
    encoder: RuntimeFeatureEncoder
    heads: dict[str, Pipeline]


def _probability_features(bundles: dict[str, PredictionBundle]) -> list[np.ndarray]:
    matrices = []
    for model_name in BASE_ORDER:
        bundle = bundles[model_name]
        for head_name in HEAD_CLASS_COUNTS:
            matrices.append(bundle.probabilities[head_name])
    return matrices


def _disagreement_features(bundles: dict[str, PredictionBundle]) -> np.ndarray:
    rows = len(next(iter(bundles.values())).predictions["action"])
    columns: list[np.ndarray] = []
    for head_name in DISAGREEMENT_HEADS:
        for left, right in DISAGREEMENT_PAIRS:
            lhs = np.asarray(bundles[left].predictions[head_name])
            rhs = np.asarray(bundles[right].predictions[head_name])
            columns.append((lhs != rhs).astype(np.float64).reshape(rows, 1))
    return np.concatenate(columns, axis=1)


def build_meta_features(
    bundles: dict[str, PredictionBundle],
    examples: list[ModerationExample],
    encoder: RuntimeFeatureEncoder,
) -> np.ndarray:
    pieces = _probability_features(bundles)
    pieces.append(_disagreement_features(bundles))
    pieces.append(encoder.transform(examples))
    return np.concatenate(pieces, axis=1)


def _new_meta_head(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=3000,
                    C=0.5,
                    class_weight="balanced",
                    random_state=seed,
                ),
            ),
        ]
    )


def train_meta_ensemble(
    oof_bundles: dict[str, PredictionBundle],
    train_examples: list[ModerationExample],
    *,
    seed: int = 42,
) -> MetaEnsemble:
    encoder = RuntimeFeatureEncoder.fit(train_examples)
    features = build_meta_features(oof_bundles, train_examples, encoder)
    heads = {}
    for offset, (name, target) in enumerate(targets(train_examples).items()):
        head = _new_meta_head(seed + offset)
        head.fit(features, target)
        heads[name] = head
    return MetaEnsemble(encoder=encoder, heads=heads)


def _aligned_meta_probabilities(
    head: Pipeline,
    features: np.ndarray,
    class_count: int,
) -> np.ndarray:
    raw = head.predict_proba(features)
    classes = head.named_steps["model"].classes_
    aligned = np.zeros((raw.shape[0], class_count), dtype=np.float64)
    for source_index, class_id in enumerate(classes):
        aligned[:, int(class_id)] = raw[:, source_index]
    return aligned


def predict_meta_ensemble(
    meta: MetaEnsemble,
    bundles: dict[str, PredictionBundle],
    examples: list[ModerationExample],
) -> PredictionBundle:
    features = build_meta_features(bundles, examples, meta.encoder)
    probabilities = {
        name: _aligned_meta_probabilities(head, features, HEAD_CLASS_COUNTS[name])
        for name, head in meta.heads.items()
    }
    predictions = {
        name: matrix.argmax(axis=1).astype(int).tolist() for name, matrix in probabilities.items()
    }
    return PredictionBundle(predictions=predictions, probabilities=probabilities)
