"""Cheap W11 train/validation-only lexical architecture comparison.

No private W26/27 admission, model download, sealed test, or API calls.
A fresh ephemeral HMAC key joins the two models *within this one run* only.
"""
from __future__ import annotations

import argparse
import json
import secrets
import time
from pathlib import Path

from workers.w12.baseline import train_baseline
from workers.w25.baselines import _expand_w12_probabilities
from workers.w25.candidate_diagnostics import diagnose
from workers.w25.contract import PredictionBundle
from workers.w25.data import load_w11_development
from workers.w25.decision_analytics import _private_root, capture
from workers.w25.open_baselines import (
    bundle_from_fitted,
    fitted_weights_digest,
    train_character_baseline,
    training_recipe_digest,
)


def _word_bundle(model, examples) -> PredictionBundle:
    texts = [item.serialized for item in examples]
    probabilities = _expand_w12_probabilities(
        model, model.predict_proba_all(texts),
    )
    bundle = PredictionBundle(
        predictions=model.predict_all(texts),
        probabilities=probabilities,
        uncertainty=[1.0 - max(row) for row in probabilities["action"]],
    )
    bundle.validate()
    return bundle


def _one_model(train, development, output, secret, name, seed, train_fn, predict_fn):
    started = time.perf_counter()
    model = train_fn(train, seed=seed)
    training_seconds = time.perf_counter() - started
    started = time.perf_counter()
    bundle = predict_fn(model, development)
    inference_seconds = time.perf_counter() - started
    path = capture(
        development, bundle, secret=secret, folder=output,
        run_id="w11-" + name + "-s" + str(seed),
        candidate=name, seed=seed,
        model_sha=fitted_weights_digest(model),
        config_sha=training_recipe_digest(name, seed, source="w11_only"),
        policy="v1", suite_name="development",
    )
    return path, {
        "run": path.name, "model_weights_sha256": fitted_weights_digest(model),
        "training_seconds": round(training_seconds, 3),
        "inference_seconds": round(inference_seconds, 3),
    }


def run(private_dir: Path, *, seed: int = 42) -> dict[str, object]:
    """Write exact evidence for two fitted architectures, then report comparisons."""
    output = _private_root(private_dir)
    train, development = load_w11_development()
    if not train or not development:
        raise ValueError("W11 train and development partitions must both exist")
    train_ids = {item.example_id for item in train}
    if train_ids & {item.example_id for item in development}:
        raise ValueError("W11 train and development example IDs overlap")
    ephemeral_secret = secrets.token_bytes(32)
    word, word_info = _one_model(
        train, development, output, ephemeral_secret,
        "word-tfidf", seed, train_baseline, _word_bundle,
    )
    char, char_info = _one_model(
        train, development, output, ephemeral_secret,
        "char-tfidf", seed, train_character_baseline, bundle_from_fitted,
    )
    diagnosis = diagnose([word, char])
    return {
        "source": "W11 train/validation only; development comparison, not acceptance",
        "train_count": len(train), "development_count": len(development),
        "runs": [word_info, char_info],
        "comparisons": diagnosis,
        "ephemeral_hmac_not_saved": True,
        "future_cross_session_joins_require_owner_managed_persistent_key": True,
        "not_proof_of_99pct_production_accuracy": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="No-download W11 word vs char smoke run")
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    outcome = run(args.private_dir, seed=args.seed)
    # Never print pseudonymous case drill-down or model input in the console.
    print(json.dumps({
        "train_count": outcome["train_count"],
        "development_count": outcome["development_count"],
        "runs": outcome["runs"],
        "ledger_count": len(outcome["runs"]),
        "status": "W11 development probe completed (not acceptance)",
    }, indent=2))


if __name__ == "__main__":
    main()
