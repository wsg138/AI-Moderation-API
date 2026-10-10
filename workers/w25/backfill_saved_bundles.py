"""Backfill private W25 development ledgers from existing A100 saved bundles.

No model loading, neural inference, training, dataset mutation or sealed holdouts.
Fail closed if any saved bundle differs from current admitted development truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from workers.w25.artifacts import load_bundle
from workers.w25.candidate_diagnostics import diagnose
from workers.w25.config import MODEL_SPECS
from workers.w25.data import load_development_data, verify_all_admissions
from workers.w25.decision_analytics import capture
from workers.w25.development_smoke import _key, _private_paths, _write_json_once
from workers.w25.evaluation import suite_fingerprint

MODELS = {
    "modernbert-normalized": ("modernbert-base/seed-138/raw-normalized", "modernbert-base"),
    "modernbert-raw": ("modernbert-base/seed-138/raw", "modernbert-base"),
    "deberta-xsmall": ("deberta-v3-xsmall/seed-138/raw", "deberta-v3-xsmall"),
    "deberta-small": ("deberta-v3-small/seed-138/raw", "deberta-v3-small"),
    "canine": ("canine-s/seed-138/raw", "canine-s"),
    "word-char": ("word-char-tfidf/seed-138/raw", None),
}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as data:
        for chunk in iter(lambda: data.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _configuration_hash(directory: Path, key: str | None, folder: str) -> str:
    spec = MODEL_SPECS[key] if key is not None else None
    calibration = directory / "calibration.json"
    payload = {
        "candidate_folder": folder,
        "seed": 138,
        "model_spec": vars(spec) if spec is not None else "word-char-baseline",
        "calibration_sha256": _hash_file(calibration) if calibration.exists() else None,
        "configuration_provenance": "existing_A100_bundle_not_retrained",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _source_evidence(folder: Path, size: int, fingerprint: str) -> dict[str, Any]:
    report = json.loads((folder / "dev-report.json").read_text(encoding="utf-8"))
    suite = report["suite"]
    if suite["n"] != size or suite["fingerprint"] != fingerprint:
        raise ValueError("Saved W25 report does not match verified current development data")
    bundle = load_bundle(folder / "dev-bundle.json")
    if len(bundle.uncertainty) != size:
        raise ValueError("Saved W25 bundle cardinality is different from development data")
    artifact = folder / "model-state.pt"
    source = artifact if artifact.exists() else folder / "dev-bundle.json"
    return {
        "folder": folder,
        "bundle": bundle,
        "model_sha": _hash_file(source),
        "artifact_kind": "model_checkpoint" if artifact.exists() else "saved_predictions_only",
        "block": {k: report["consequences"]["block"][k] for k in ("tp", "fn", "fp")},
    }


def _verified_inputs(artifact_root: Path):
    if not artifact_root.is_absolute() or not artifact_root.is_dir():
        raise ValueError("Existing absolute artifact root required")
    verify_all_admissions()  # W27 hashed, but never evaluated or trained.
    _train, dev = load_development_data(include_admitted=True)
    fingerprint = suite_fingerprint(dev)
    sources = {}
    for name, (folder_name, key) in MODELS.items():
        folder = artifact_root / folder_name
        source = _source_evidence(folder, len(dev), fingerprint)
        source["config_sha"] = _configuration_hash(folder, key, folder_name)
        sources[name] = source
    return dev, sources


def _archive(
    root: Path, prefix: str, examples, sources: dict[str, dict[str, Any]],
) -> dict[str, object]:
    private, key_path = _private_paths(root)
    key = _key(key_path).encode("utf-8")
    destination = private / prefix
    destination.mkdir(mode=0o700, exist_ok=False)
    paths: list[Path] = []
    for name, evidence in sources.items():
        path = capture(
            examples, evidence["bundle"],
            secret=key, folder=destination, run_id=prefix + "-" + name,
            candidate=name, seed=138, model_sha=evidence["model_sha"],
            config_sha=evidence["config_sha"], policy="v1", suite_name="development",
            artifact_kind=evidence["artifact_kind"],
            preprocessing_variant=(
                "raw+normalized" if name == "modernbert-normalized" else "raw"
            ),
        )
        paths.append(path)
    comparison = diagnose(paths)
    _write_json_once(destination / "comparison.json", comparison)
    return {
        "source": "existing_A100_saved_development_bundles",
        "case_count": len(examples),
        "backfilled": [path.stem for path in paths],
        "checkpoint_and_prediction_provenance": {
            name: {
                "artifact_kind": evidence["artifact_kind"],
                "block_counts": evidence["block"],
            }
            for name, evidence in sources.items()
        },
        "all_raw_messages_remain_private": True,
        "no_frozen_acceptance_read": True,
        "no_retraining_performed": True,
    }


def run(private_root: Path, artifact_root: Path, prefix: str) -> dict[str, object]:
    if not prefix.isascii() or not prefix.replace("-", "").isalnum():
        raise ValueError("Run prefix must be ASCII alphanumeric with hyphens")
    if len(prefix) > 30:
        raise ValueError("Run prefix too long")
    examples, sources = _verified_inputs(artifact_root)
    return _archive(private_root, prefix, examples, sources)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.private_root, args.artifact_root, args.run_prefix),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
