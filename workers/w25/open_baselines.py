"""Cheap, reproducible six-head W25 lexical development baselines.

This module neither fetches remote weights nor reads sealed acceptance suites.
Model fingerprints hash fitted weights, not raw private message text.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from workers.w12.baseline import BaselineModel, _targets
from workers.w12.dataset import ModerationExample
from workers.w25.baselines import _expand_w12_probabilities
from workers.w25.contract import PredictionBundle, HEAD_NAMES


def train_character_baseline(
    examples: list[ModerationExample], *, seed: int = 42,
) -> BaselineModel:
    if not examples:
        raise ValueError("Training requires nonempty approved examples")
    vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(3, 5),
        max_features=12000, min_df=2, sublinear_tf=True,
    )
    features = vectorizer.fit_transform(item.serialized for item in examples)
    heads: dict[str, LogisticRegression] = {}
    for name, targets in _targets(examples).items():
        model = LogisticRegression(
            max_iter=1200, C=1.0, class_weight="balanced",
            random_state=seed, n_jobs=1,
        )
        model.fit(features, targets)
        heads[name] = model
    return BaselineModel(vectorizer=vectorizer, heads=heads,
                         classes={}, seed=seed)


def bundle_from_fitted(
    model: BaselineModel, examples: list[ModerationExample],
) -> PredictionBundle:
    texts = [item.serialized for item in examples]
    predictions = model.predict_all(texts)
    probabilities = _expand_w12_probabilities(model, model.predict_proba_all(texts))
    bundle = PredictionBundle(
        predictions=predictions,
        probabilities=probabilities,
        uncertainty=[1.0 - max(row) for row in probabilities["action"]],
    )
    bundle.validate()
    return bundle


def fitted_weights_digest(model: BaselineModel) -> str:
    """Digest fitted TF-IDF and all six linear weights, with fixed ordering."""
    digest = hashlib.sha256()
    vocabulary = sorted(model.vectorizer.vocabulary_.items())
    digest.update(json.dumps(vocabulary, separators=(",", ":")).encode("utf-8"))
    digest.update(model.vectorizer.idf_.tobytes())
    for head in HEAD_NAMES:
        fitted = model.heads[head]
        digest.update(head.encode("utf-8"))
        digest.update(fitted.coef_.tobytes())
        digest.update(fitted.intercept_.tobytes())
        digest.update(fitted.classes_.tobytes())
    return digest.hexdigest()


def training_recipe_digest(name: str, seed: int) -> str:
    from workers.w12 import baseline as word
    from workers.w25 import open_baselines as lexical

    data = {
        "candidate": name, "seed": seed,
        "sklearn": sklearn.__version__,
        "training_source": "W11 train and W26 admitted train if authorized",
        "word_sha": hashlib.sha256(
            Path(word.__file__).read_bytes()
        ).hexdigest(),
        "char_sha": hashlib.sha256(
            Path(lexical.__file__).read_bytes()
        ).hexdigest(),
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
