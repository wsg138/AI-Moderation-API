"""TF-IDF candidates and leakage-safe OOF prediction helpers for W23."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np  # pyright: ignore[reportMissingImports]
from sklearn.feature_extraction.text import TfidfVectorizer  # pyright: ignore[reportMissingImports]
from sklearn.linear_model import LogisticRegression  # pyright: ignore[reportMissingImports]
from sklearn.model_selection import StratifiedKFold  # pyright: ignore[reportMissingImports]
from sklearn.pipeline import FeatureUnion  # pyright: ignore[reportMissingImports]

from workers.w12.dataset import (
    ACTION_TO_ID,
    ACTIONS,
    CONTAINMENT_TO_ID,
    CONTAINMENTS,
    LABEL_TO_ID,
    LABELS,
    REVIEW_PRIORITIES,
    REVIEW_TO_ID,
    SUPPORT_FLOWS,
    SUPPORT_TO_ID,
    ModerationExample,
)
from workers.w23.config import OOF_FOLDS, SEED, WORD_MAX_FEATURES

HEAD_CLASS_COUNTS = {
    "label": len(LABELS),
    "action": len(ACTIONS),
    "review_priority": len(REVIEW_PRIORITIES),
    "strike": 2,
    "containment": len(CONTAINMENTS),
    "support_flow": len(SUPPORT_FLOWS),
}


@dataclass
class PredictionBundle:
    predictions: dict[str, list[int]]
    probabilities: dict[str, np.ndarray]


@dataclass
class TextPolicyModel:
    vectorizer: Any
    heads: dict[str, LogisticRegression]


def targets(examples: list[ModerationExample]) -> dict[str, list[int]]:
    return {
        "label": [LABEL_TO_ID[item.label] for item in examples],
        "action": [ACTION_TO_ID[item.action] for item in examples],
        "review_priority": [REVIEW_TO_ID[item.review_priority] for item in examples],
        "strike": [1 if item.strike else 0 for item in examples],
        "containment": [CONTAINMENT_TO_ID[item.containment] for item in examples],
        "support_flow": [SUPPORT_TO_ID[item.support_flow] for item in examples],
    }


def _word_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        max_features=WORD_MAX_FEATURES,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
    )


def _char_vectorizer(ngram_range: tuple[int, int], max_features: int) -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="char_wb",
        max_features=max_features,
        ngram_range=ngram_range,
        sublinear_tf=True,
        min_df=2,
    )


def build_vectorizer(
    kind: str,
    char_range: tuple[int, int] = (3, 5),
    char_features: int = 60_000,
) -> Any:
    if kind == "word":
        return _word_vectorizer()
    if kind == "char":
        return _char_vectorizer(char_range, char_features)
    if kind == "combined":
        return FeatureUnion(
            [
                ("word", _word_vectorizer()),
                ("char", _char_vectorizer(char_range, char_features)),
            ]
        )
    raise ValueError(f"unknown text model kind: {kind}")


def _fit_head(features: Any, target: list[int], seed: int) -> LogisticRegression:
    head = LogisticRegression(
        max_iter=2000,
        C=1.0,
        class_weight="balanced",
        random_state=seed,
    )
    head.fit(features, target)
    return head


def train_text_model(
    examples: list[ModerationExample],
    kind: str,
    char_range: tuple[int, int] = (3, 5),
    char_features: int = 60_000,
    seed: int = SEED,
) -> TextPolicyModel:
    vectorizer = build_vectorizer(kind, char_range, char_features)
    features = vectorizer.fit_transform([item.serialized for item in examples])
    heads = {name: _fit_head(features, target, seed) for name, target in targets(examples).items()}
    return TextPolicyModel(vectorizer=vectorizer, heads=heads)


def _aligned_probabilities(head: LogisticRegression, features: Any, class_count: int) -> np.ndarray:
    raw = head.predict_proba(features)
    aligned = np.zeros((raw.shape[0], class_count), dtype=np.float64)
    for source_index, class_id in enumerate(head.classes_):
        aligned[:, int(class_id)] = raw[:, source_index]
    return aligned


def predict_text_model(
    model: TextPolicyModel, examples: list[ModerationExample]
) -> PredictionBundle:
    features = model.vectorizer.transform([item.serialized for item in examples])
    probabilities = {
        name: _aligned_probabilities(head, features, HEAD_CLASS_COUNTS[name])
        for name, head in model.heads.items()
    }
    predictions = {
        name: matrix.argmax(axis=1).astype(int).tolist() for name, matrix in probabilities.items()
    }
    return PredictionBundle(predictions=predictions, probabilities=probabilities)


def existing_word_baseline_bundle(
    train_examples: list[ModerationExample],
    examples: list[ModerationExample],
) -> PredictionBundle:
    from workers.w12.baseline import train_baseline

    model = train_baseline(train_examples, seed=SEED)
    texts = [item.serialized for item in examples]
    features = model.vectorizer.transform(texts)
    probabilities = {
        name: _aligned_probabilities(head, features, HEAD_CLASS_COUNTS[name])
        for name, head in model.heads.items()
    }
    predictions = model.predict_all(texts)
    return PredictionBundle(predictions=predictions, probabilities=probabilities)


def _folds(examples: list[ModerationExample]) -> list[tuple[np.ndarray, np.ndarray]]:
    labels = [LABEL_TO_ID[item.label] for item in examples]
    splitter = StratifiedKFold(n_splits=OOF_FOLDS, shuffle=True, random_state=SEED)
    indices = np.arange(len(examples))
    return list(splitter.split(indices, labels))


def oof_text_bundle(
    examples: list[ModerationExample],
    kind: str,
    char_range: tuple[int, int] = (3, 5),
    char_features: int = 60_000,
) -> PredictionBundle:
    probabilities = {
        name: np.zeros((len(examples), count), dtype=np.float64)
        for name, count in HEAD_CLASS_COUNTS.items()
    }
    for fold, (fit_indices, hold_indices) in enumerate(_folds(examples)):
        fit = [examples[int(index)] for index in fit_indices]
        hold = [examples[int(index)] for index in hold_indices]
        model = train_text_model(
            fit,
            kind,
            char_range=char_range,
            char_features=char_features,
            seed=SEED + fold,
        )
        fold_bundle = predict_text_model(model, hold)
        for name, matrix in fold_bundle.probabilities.items():
            probabilities[name][hold_indices] = matrix
    predictions = {
        name: matrix.argmax(axis=1).astype(int).tolist() for name, matrix in probabilities.items()
    }
    return PredictionBundle(predictions=predictions, probabilities=probabilities)


def char_spec_name(ngram_range: tuple[int, int], max_features: int) -> str:
    return f"char-{ngram_range[0]}-{ngram_range[1]}-{max_features // 1000}k"
