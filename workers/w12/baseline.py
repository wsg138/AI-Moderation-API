"""W12 baseline: TF-IDF + linear heads (multi-task).

Sanity-check baseline. Trains one linear classifier per policy dimension on
TF-IDF features of the leakage-safe serialization. Cheap, deterministic, and
fast — establishes the floor that encoder candidates must beat on critical
policy slices, not just aggregate F1.
"""

from __future__ import annotations

import json
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .dataset import (
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

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


@dataclass
class BaselineModel:
    vectorizer: TfidfVectorizer
    heads: dict[str, LogisticRegression]
    classes: dict[str, list[str]]
    trained_at: float = field(default_factory=time.time)
    seed: int = 0

    def __reduce__(self):
        # Make pickle robust regardless of whether this module was run as
        # __main__ or imported normally.
        from workers.w12 import baseline as _mod
        return (_mod._rebuild_baseline, (self.vectorizer, self.heads,
                                         self.classes, self.trained_at, self.seed))

    def predict_proba_all(self, texts: list[str]) -> dict[str, list[list[float]]]:
        X = self.vectorizer.transform(texts)
        out: dict[str, list[list[float]]] = {}
        for name, head in self.heads.items():
            out[name] = head.predict_proba(X).tolist()
        return out

    def predict_all(self, texts: list[str]) -> dict[str, list[int]]:
        X = self.vectorizer.transform(texts)
        return {name: head.predict(X).tolist() for name, head in self.heads.items()}


def _targets(examples: list[ModerationExample]) -> dict[str, list[int]]:
    return {
        "label": [LABEL_TO_ID[e.label] for e in examples],
        "action": [ACTION_TO_ID[e.action] for e in examples],
        "review_priority": [REVIEW_TO_ID[e.review_priority] for e in examples],
        "strike": [1 if e.strike else 0 for e in examples],
        "containment": [CONTAINMENT_TO_ID[e.containment] for e in examples],
        "support_flow": [SUPPORT_TO_ID[e.support_flow] for e in examples],
    }


def train_baseline(
    train_examples: list[ModerationExample],
    seed: int = 42,
    max_features: int = 30000,
) -> BaselineModel:
    texts = [e.serialized for e in train_examples]
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
    )
    X = vectorizer.fit_transform(texts)
    targets = _targets(train_examples)
    heads: dict[str, LogisticRegression] = {}
    for name, y in targets.items():
        head = LogisticRegression(
            max_iter=2000,
            C=1.0,
            class_weight="balanced",
            random_state=seed,
            n_jobs=1,
        )
        head.fit(X, y)
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


def _rebuild_baseline(vectorizer, heads, classes, trained_at, seed) -> BaselineModel:
    return BaselineModel(vectorizer=vectorizer, heads=heads, classes=classes,
                         trained_at=trained_at, seed=seed)


def save_baseline(model: BaselineModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_baseline(path: Path) -> BaselineModel:
    with open(path, "rb") as f:
        return pickle.load(f)


def main() -> None:
    from .dataset import load_partition

    train = load_partition("train")
    val = load_partition("validation")
    print(f"train={len(train)} val={len(val)}", flush=True)
    t0 = time.time()
    model = train_baseline(train)
    print(f"trained in {time.time() - t0:.1f}s", flush=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    save_baseline(model, ARTIFACT_DIR / "baseline-tfidf.pkl")

    # Quick validation sanity: label accuracy
    preds = model.predict_all([e.serialized for e in val])
    gold = [LABEL_TO_ID[e.label] for e in val]
    acc = sum(p == g for p, g in zip(preds["label"], gold, strict=True)) / len(gold)
    print(f"val label accuracy: {acc:.3f}", flush=True)
    with open(ARTIFACT_DIR / "baseline-val-sanity.json", "w") as f:
        json.dump({"val_label_accuracy": acc, "n_val": len(val)}, f, indent=2)


if __name__ == "__main__":
    main()
