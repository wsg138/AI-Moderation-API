"""CPU-only W11 development comparison with mandatory private decision ledgers.

Does not touch W20/W27, train neural models, download weights, or deploy.
Requires an existing owner-authorized private root; never prints the HMAC key.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from workers.w12.baseline import train_baseline
from workers.w25.candidate_diagnostics import diagnose
from workers.w25.data import load_development_data, verify_all_admissions
from workers.w25.decision_analytics import CAPTURE_ENV, audit_coverage
from workers.w25.evaluation import evaluate_candidate
from workers.w25.open_baselines import (
    bundle_from_fitted,
    fitted_weights_digest,
    train_character_baseline,
    training_recipe_digest,
)

REPO = Path(__file__).resolve().parents[2]


def _private_paths(root: Path) -> tuple[Path, Path]:
    directory = root.resolve()
    if not root.is_absolute() or not directory.is_dir():
        raise ValueError("Existing absolute private root required")
    if directory == REPO or REPO in directory.parents:
        raise ValueError("Development evidence must not live in Git")
    output = directory / "w25-development-analytics"
    output.mkdir(mode=0o700, exist_ok=True)
    return output, output / ".hmac-key"


def _key(path: Path) -> str:
    if not path.exists():
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "w", encoding="ascii") as file:
                file.write(secrets.token_hex(32))
    value = path.read_text(encoding="ascii").strip()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("Invalid existing private HMAC key; do not overwrite it")
    return value


def _capture_settings(
    directory: Path, key: str, run_id: str, candidate: str, seed: int,
    model_hash: str, recipe_hash: str,
) -> None:
    settings = {
        "private_dir": str(directory),
        "run_id": run_id,
        "candidate": candidate,
        "seed": str(seed),
        "model_sha": model_hash,
        "config_sha": recipe_hash,
        "policy": "v1",
        "suite": "development",
    }
    os.environ["ENTHUSIA_ANALYTICS_MODE"] = "required"
    os.environ["ENTHUSIA_ANALYTICS_HMAC_KEY"] = key
    for field, name in CAPTURE_ENV.items():
        os.environ[name] = settings[field]


def _write_json_once(path: Path, payload: dict[str, object]) -> None:
    data = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(data)


def _development_examples(admitted: bool, limit: int):
    if admitted:
        verify_all_admissions()  # W27 verified but never selected as training.
    train, dev = load_development_data(include_admitted=admitted)
    examples = dev[:limit]
    if not examples or len({item.example_id for item in examples}) != len(examples):
        raise ValueError("Nonempty unique development examples required")
    return train, examples


def _run(
    root: Path, prefix: str, seed: int, limit: int, admitted: bool,
) -> dict[str, object]:
    output, secret_path = _private_paths(root)
    key = _key(secret_path)
    train, examples = _development_examples(admitted, limit)
    paths: list[Path] = []
    for candidate, trainer in (("word", train_baseline), ("character", train_character_baseline)):
        identifier = prefix + "-" + candidate
        if (output / (identifier + ".jsonl")).exists():
            raise ValueError("Run already exists; use a distinct --run-prefix")
        model = trainer(train, seed=seed)
        bundle = bundle_from_fitted(model, examples)
        _capture_settings(
            output, key, identifier, candidate, seed,
            fitted_weights_digest(model), training_recipe_digest(candidate, seed),
        )
        report = evaluate_candidate(examples, bundle)  # required ledger or fail
        _write_json_once(output / (identifier + "-metrics.json"), report)
        paths.append(output / (identifier + ".jsonl"))
    comparison = diagnose(paths)
    _write_json_once(output / (prefix + "-comparison.json"), comparison)
    checked = audit_coverage(output, [path.stem for path in paths])
    return {
        "source": (
            "W11 plus admitted W26 train/development"
            if admitted else "W11 train/development"
        ),
        "case_count": len(examples),
        "run_ids": [path.stem for path in paths],
        "private_evidence_written": True,
        "run_files_present": checked["present_count"],
        "joint_wrong_action_count": comparison[
            "pairwise_action_complementarity"
        ][paths[0].stem + "_vs_" + paths[1].stem]["both_wrong_action"],
        "not_independent_accuracy_or_release_evidence": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=128)
    parser.add_argument("--include-admitted", action="store_true")
    args = parser.parse_args()
    if not 20 <= args.limit <= 10000:
        parser.error("Development sample limit must be in [20, 10000]")
    if not args.run_prefix.isascii() or not args.run_prefix.replace("-", "").isalnum():
        parser.error("Run prefix must be ASCII alphanumeric with optional hyphens")
    print(json.dumps(_run(args.private_root, args.run_prefix, args.seed,
                          args.limit, args.include_admitted), indent=2))


if __name__ == "__main__":
    main()
