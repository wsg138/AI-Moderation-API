"""Cheap, optional role-admitted development-only lexical comparisons.

Default: W11 train/validation. Optional: approved W21/W26 train/development.
Never admits validation-only W27, W20, frozen tests, or owner golden records.
An ephemeral HMAC key joins models *within this one run* only.
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
from workers.w25.data import (
    TRAINING_ROLES,
    load_admissions,
    load_development_data,
)
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


def _one_model(
    train, development, output, secret, name, seed, train_fn, predict_fn, scope,
):
    started = time.perf_counter()
    model = train_fn(train, seed=seed)
    training_seconds = time.perf_counter() - started
    started = time.perf_counter()
    bundle = predict_fn(model, development)
    inference_seconds = time.perf_counter() - started
    path = capture(
        development, bundle, secret=secret, folder=output,
        run_id=scope + "-" + name + "-s" + str(seed),
        candidate=name, seed=seed,
        model_sha=fitted_weights_digest(model),
        config_sha=training_recipe_digest(name, seed, source=scope),
        policy="v1", suite_name="development",
    )
    return path, {
        "run": path.name, "model_weights_sha256": fitted_weights_digest(model),
        "training_seconds": round(training_seconds, 3),
        "inference_seconds": round(inference_seconds, 3),
    }


def _reserved_training_source_present() -> bool:
    return any(
        source.role in TRAINING_ROLES
        and any(marker in source.path.upper() for marker in ("W20", "W27"))
        for source in load_admissions()
    )


def _load_approved_partitions(include_admitted: bool):
    if include_admitted and _reserved_training_source_present():
        raise ValueError("Reserved acceptance source cannot be admitted for training")
    train, development = load_development_data(include_admitted=include_admitted)
    if not train or not development:
        raise ValueError("Train and development partitions must both exist")
    train_ids = {item.example_id for item in train}
    if train_ids & {item.example_id for item in development}:
        raise ValueError("Train and development example IDs overlap")
    return train, development


def run(
    private_dir: Path, *, seed: int = 42, include_admitted: bool = False,
) -> dict[str, object]:
    """Write exact evidence for two fitted architectures, then report comparisons."""
    output = _private_root(private_dir)
    train, development = _load_approved_partitions(include_admitted)
    scope = "w25-admitted" if include_admitted else "w11"
    ephemeral_secret = secrets.token_bytes(32)
    word, word_info = _one_model(
        train, development, output, ephemeral_secret,
        "word-tfidf", seed, train_baseline, _word_bundle, scope,
    )
    char, char_info = _one_model(
        train, development, output, ephemeral_secret,
        "char-tfidf", seed, train_character_baseline, bundle_from_fitted, scope,
    )
    diagnosis = diagnose([word, char])
    result = {
        "source": (
            "W11 plus verified role-admitted training/development, never W27"
            if include_admitted else
            "W11 train/validation only; development comparison, not acceptance"
        ),
        "train_count": len(train), "development_count": len(development),
        "runs": [word_info, char_info],
        "comparisons": diagnosis,
        "ephemeral_hmac_not_saved": True,
        "future_cross_session_joins_require_owner_managed_persistent_key": True,
        "not_proof_of_99pct_production_accuracy": True,
    }
    filename = scope + "-word-v-char-s" + str(seed) + "-comparison.json"
    with (output / filename).open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2, sort_keys=True, allow_nan=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Local-only word-vs-char development test")
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-admitted", action="store_true",
                        help="Explicitly include verified W21/W26 train/dev, never W27")
    args = parser.parse_args()
    outcome = run(args.private_dir, seed=args.seed,
                  include_admitted=args.include_admitted)
    # Never print pseudonymous case drill-down or model input in the console.
    run_infos = outcome["runs"]
    if not isinstance(run_infos, list):
        raise ValueError("Run evidence must contain a list of completed runs")
    print(json.dumps({
        "train_count": outcome["train_count"],
        "development_count": outcome["development_count"],
        "runs": run_infos,
        "ledger_count": len(run_infos),
        "comparison_report": (
            ("w25-admitted" if args.include_admitted else "w11")
            + "-word-v-char-s" + str(args.seed) + "-comparison.json"
        ),
        "status": "Development probe completed (not acceptance)",
    }, indent=2))


if __name__ == "__main__":
    main()
