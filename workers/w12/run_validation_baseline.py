"""Run validation-only evaluation for the W12 TF-IDF baseline."""

from __future__ import annotations

import json
import platform

import sklearn

from workers.w12.baseline import train_baseline
from workers.w12.dataset import load_partition
from workers.w12.evaluate import REPORTS_DIR, evaluate_predictions


def main() -> None:
    train = load_partition("train")
    validation = load_partition("validation")
    model = train_baseline(train, seed=42)
    texts = [example.serialized for example in validation]
    predictions = model.predict_all(texts)
    probabilities = model.predict_proba_all(texts)
    report = evaluate_predictions(
        validation,
        predictions["label"],
        predictions["action"],
        predictions["review_priority"],
        predictions["strike"],
        predictions["containment"],
        predictions["support_flow"],
        [row[1] for row in probabilities["action"]],
    )
    report["candidate"] = "baseline-tfidf"
    report["seed"] = 42
    report["environment"] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "scikit_learn": sklearn.__version__,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "val-baseline-tfidf.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(path),
                "label_accuracy": report["semantic_label"]["accuracy"],
                "label_macro_f1": report["semantic_label"]["macro_f1"],
                "gameplay_fp": report["critical_slices"]["minecraft_gameplay"][
                    "block_false_positive_rate"
                ],
                "threat_recall": report["critical_slices"]["real_world_threat"]["block_recall"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
