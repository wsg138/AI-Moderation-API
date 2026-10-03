"""Run validation-only evaluation for one W12 pretrained encoder candidate."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import sklearn
import torch
import transformers

from .dataset import load_partition
from .evaluate import REPORTS_DIR, evaluate_predictions
from .predict import predict_encoder
from .train_encoder import CANDIDATES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=list(CANDIDATES), required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    examples = load_partition("validation")
    predictions, proba_block = predict_encoder(args.candidate, args.seed, examples)
    report = evaluate_predictions(
        examples,
        predictions["label"],
        predictions["action"],
        predictions["review_priority"],
        predictions["strike"],
        predictions["containment"],
        predictions["support_flow"],
        proba_block,
    )
    cfg = CANDIDATES[args.candidate]
    report["candidate"] = args.candidate
    report["seed"] = args.seed
    report["model_source"] = {
        "hf_id": cfg["hf_id"],
        "revision": cfg["revision"],
        "license": cfg["license"],
    }
    report["environment"] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "scikit_learn": sklearn.__version__,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(REPORTS_DIR) / f"val-{args.candidate}-seed{args.seed}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(path),
                "candidate": args.candidate,
                "label_accuracy": report["semantic_label"]["accuracy"],
                "label_macro_f1": report["semantic_label"]["macro_f1"],
                "gameplay_fp": report["critical_slices"]["minecraft_gameplay"].get(
                    "block_false_positive_rate"
                ),
                "threat_recall": report["critical_slices"]["real_world_threat"].get(
                    "block_recall"
                ),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
