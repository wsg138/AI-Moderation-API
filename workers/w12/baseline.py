"""W12 baseline: deterministic TF-IDF + linear policy heads.

The baseline is trained from the frozen W11 train partition whenever evidence
is produced. It is intentionally not persisted as a pickle/joblib artifact:
review and production artifacts use JSON + ONNX instead.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

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

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


@dataclass
class BaselineModel:
    vectorizer: TfidfVectorizer
    heads: dict[str, LogisticRegression]
    classes: dict[str, list[str]]
    trained_at: float = field(default_factory=time.time)
    seed: int = 0

    def predict_proba_all(self, texts: list[str]) -> dict[str, list[list[float]]]:
        features = self.vectorizer.transform(texts)
        return {
            name: head.predict_proba(features).tolist()
            for name, head in self.heads.items()
        }

    def predict_all(self, texts: list[str]) -> dict[str, list[int]]:
        features = self.vectorizer.transform(texts)
        return {
            name: head.predict(features).tolist()
            for name, head in self.heads.items()
        }


def _targets(examples: list[ModerationExample]) -> dict[str, list[int]]:
    return {
        "label": [LABEL_TO_ID[item.label] for item in examples],
        "action": [ACTION_TO_ID[item.action] for item in examples],
        "review_priority": [REVIEW_TO_ID[item.review_priority] for item in examples],
        "strike": [1 if item.strike else 0 for item in examples],
        "containment": [CONTAINMENT_TO_ID[item.containment] for item in examples],
        "support_flow": [SUPPORT_TO_ID[item.support_flow] for item in examples],
    }


def train_baseline(
    train_examples: list[ModerationExample],
    seed: int = 42,
    max_features: int = 30000,
) -> BaselineModel:
    texts = [item.serialized for item in train_examples]
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
    )
    features = vectorizer.fit_transform(texts)
    heads: dict[str, LogisticRegression] = {}
    for name, target in _targets(train_examples).items():
        head = LogisticRegression(
            max_iter=2000,
            C=1.0,
            class_weight="balanced",
            random_state=seed,
            n_jobs=1,
        )
        head.fit(features, target)
        heads[name] = head

    return BaselineModel(
        vectorizer=vectorizer,
        heads=heads,
        classes={
            "label": LABELS,
            "action": ACTIONS,
            "review_priority": REVIEW_PRIORITIES,
            "strike": ["false", "true"],
            "containment": CONTAINMENTS,
            "support_flow": SUPPORT_FLOWS,
        },
        seed=seed,
    )


def main() -> None:
    from workers.w12.dataset import load_partition

    train = load_partition("train")
    validation = load_partition("validation")
    started = time.time()
    model = train_baseline(train)
    predictions = model.predict_all([item.serialized for item in validation])
    gold = [LABEL_TO_ID[item.label] for item in validation]
    accuracy = sum(
        predicted == expected
        for predicted, expected in zip(predictions["label"], gold, strict=True)
    ) / len(gold)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "baseline-val-sanity.json"
    path.write_text(
        json.dumps(
            {
                "train": len(train),
                "validation": len(validation),
                "seed": model.seed,
                "elapsed_seconds": time.time() - started,
                "val_label_accuracy": accuracy,
                "persistence": "none; retrain deterministically and export JSON+ONNX",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"val label accuracy: {accuracy:.3f}", flush=True)


if __name__ == "__main__":
    main()
