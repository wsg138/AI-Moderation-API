"""Word/character TF-IDF ablation and ModernBERT lexical fusion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np  # pyright: ignore[reportMissingImports]
from scipy import sparse  # pyright: ignore[reportMissingImports]
from sklearn.feature_extraction.text import TfidfVectorizer  # pyright: ignore[reportMissingImports]
from sklearn.linear_model import LogisticRegression  # pyright: ignore[reportMissingImports]

from workers.w12.dataset import (
    ACTION_TO_ID,
    CONTAINMENT_TO_ID,
    LABEL_TO_ID,
    REVIEW_TO_ID,
    SUPPORT_TO_ID,
    ModerationExample,
)
from workers.w25.contract import HEAD_NAMES, HEAD_VALUES, PredictionBundle
from workers.w25.data import serialize_variant


@dataclass
class LexicalFusionModel:
    word: TfidfVectorizer
    char: TfidfVectorizer
    heads: dict[str, LogisticRegression]
    use_embeddings: bool
    serialization_variant: str

    def transform(
        self,
        examples: list[ModerationExample],
        embeddings: np.ndarray | None = None,
    ):
        texts = [
            serialize_variant(item.serialized, self.serialization_variant) for item in examples
        ]
        pieces = [
            self.word.transform(texts),
            self.char.transform(texts),
            _evasion_features(texts),
        ]
        if self.use_embeddings:
            if embeddings is None or len(embeddings) != len(examples):
                raise ValueError("fusion model requires aligned ModernBERT embeddings")
            pieces.append(sparse.csr_matrix(embeddings))
        return sparse.hstack(pieces, format="csr")


def fit_lexical_fusion(
    examples: list[ModerationExample],
    *,
    serialization_variant: str,
    embeddings: np.ndarray | None = None,
    seed: int = 42,
) -> LexicalFusionModel:
    texts = [serialize_variant(item.serialized, serialization_variant) for item in examples]
    word = TfidfVectorizer(
        ngram_range=(1, 2), min_df=1, max_features=50_000, sublinear_tf=True
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 6),
        min_df=1,
        max_features=75_000,
        sublinear_tf=True,
    )
    pieces = [
        word.fit_transform(texts),
        char.fit_transform(texts),
        _evasion_features(texts),
    ]
    use_embeddings = embeddings is not None
    if embeddings is not None:
        if len(embeddings) != len(examples):
            raise ValueError("embedding rows must align with training examples")
        pieces.append(sparse.csr_matrix(embeddings))
    matrix = sparse.hstack(pieces, format="csr")
    heads = {
        name: _fit_head(matrix, _targets(examples, name), seed)
        for name in HEAD_NAMES
    }
    return LexicalFusionModel(word, char, heads, use_embeddings, serialization_variant)


def predict_lexical(
    model: LexicalFusionModel,
    examples: list[ModerationExample],
    *,
    embeddings: np.ndarray | None = None,
) -> PredictionBundle:
    matrix = model.transform(examples, embeddings)
    predictions = {}
    probabilities = {}
    for name, classifier in model.heads.items():
        probabilities[name] = _aligned_probabilities(
            classifier, matrix, len(HEAD_VALUES[name])
        )
        predictions[name] = [
            max(range(len(row)), key=row.__getitem__) for row in probabilities[name]
        ]
    uncertainty = [1.0 - max(row) for row in probabilities["action"]]
    bundle = PredictionBundle(predictions, probabilities, uncertainty)
    bundle.validate()
    return bundle


def _fit_head(matrix, target: list[int], seed: int) -> LogisticRegression:
    model = LogisticRegression(
        max_iter=2_000,
        class_weight="balanced",
        solver="liblinear" if len(set(target)) == 2 else "lbfgs",
        random_state=seed,
    )
    model.fit(matrix, target)
    return model


def _aligned_probabilities(classifier: LogisticRegression, matrix, width: int) -> list[list[float]]:
    raw = classifier.predict_proba(matrix)
    rows = []
    for probabilities in raw:
        row = [0.0] * width
        for class_id, probability in zip(classifier.classes_, probabilities, strict=True):
            row[int(class_id)] = float(probability)
        rows.append(row)
    return rows


def _targets(examples: list[ModerationExample], head: str) -> list[int]:
    mappings = {
        "label": lambda item: LABEL_TO_ID[item.label],
        "action": lambda item: ACTION_TO_ID[item.action],
        "review_priority": lambda item: REVIEW_TO_ID[item.review_priority],
        "strike": lambda item: 1 if item.strike else 0,
        "containment": lambda item: CONTAINMENT_TO_ID[item.containment],
        "support_flow": lambda item: SUPPORT_TO_ID[item.support_flow],
    }
    return [mappings[head](item) for item in examples]


def _evasion_features(texts: list[str]):
    rows = [_text_features(text) for text in texts]
    return sparse.csr_matrix(np.asarray(rows, dtype=np.float64))


def _text_features(text: str) -> list[float]:
    length = max(len(text), 1)
    return [
        float(length),
        _ascii_count(text) / length,
        _alpha_count(text) / length,
        _digit_count(text) / length,
        _punctuation_count(text) / length,
        _upper_count(text) / length,
        _repeated_count(text) / length,
        float(text.count("\u200b")),
        _non_ascii_count(text) / length,
    ]


def _ascii_count(text: str) -> int:
    return sum(ord(char) < 128 for char in text)


def _alpha_count(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _digit_count(text: str) -> int:
    return sum(char.isdigit() for char in text)


def _punctuation_count(text: str) -> int:
    return sum(not char.isalnum() and not char.isspace() for char in text)


def _upper_count(text: str) -> int:
    return sum(char.isupper() for char in text)


def _repeated_count(text: str) -> int:
    return sum(text[index] == text[index - 1] for index in range(1, len(text)))


def _non_ascii_count(text: str) -> int:
    return sum(ord(char) > 127 for char in text)
