"""Re-evaluate saved W25 development predictions without renting a GPU.

Only the hash-pinned W11/W21/W26 training/development partitions are loaded.
W20 and W27 are never read. Original saved model decisions are preserved,
not regenerated, and all detailed comparisons stay in private local files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workers.w25.artifacts import load_bundle
from workers.w25.candidate_diagnostics import diagnose
from workers.w25.data import load_development_data
from workers.w25.decision_analytics import _private_root, capture
from workers.w25.evaluation import suite_fingerprint


@dataclass(frozen=True)
class Source:
    name: str
    directory: str
    variant: str = "raw"
    stage: str = "selective"


# Explicit known local copy-back artifacts, not a wildcard or remote search.
SOURCES = (
    Source("w25-wordchar", "W25_A100_Offload_5vdymryahpn1hf/word-char-tfidf/seed-138/raw"),
    Source("modernbert-raw", "W25_A100_Offload_5vdymryahpn1hf/modernbert-base/seed-138/raw"),
    Source(
        "modernbert-normalized",
        "W25_A100_Offload_5vdymryahpn1hf/modernbert-base/seed-138/raw-normalized",
        "raw+normalized",
    ),
    Source("deberta-xsmall", "W25_A100_Offload_5vdymryahpn1hf/deberta-v3-xsmall/seed-138/raw"),
    Source("deberta-small", "W25_A100_Offload_5vdymryahpn1hf/deberta-v3-small/seed-138/raw"),
    Source("canine-s", "W25_A100_Offload_5vdymryahpn1hf/canine-s/seed-138/raw"),
    Source("xsmall-balanced", "W25_A100_Offload_5vdymryahpn1hf/deberta-v3-xsmall-balanced-v1"),
    Source("xsmall-stacked-router", "W25_XSMALL_STACKED_ROUTER", stage="stacked_router"),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paths(root: Path, spec: Source) -> tuple[Path, Path]:
    directory = (root / spec.directory).resolve()
    if not directory.is_relative_to(root):
        raise ValueError("Saved W25 artifact path escapes selected archive")
    bundle = directory / (
        "dev-bundle.json" if spec.stage == "stacked_router" else "dev-selective-bundle.json"
    )
    report = directory / "dev-report.json"
    if not bundle.is_file() or not report.is_file():
        raise FileNotFoundError("Required saved development bundle/report absent")
    return bundle, report


def _preflight(
    root: Path, examples: list[Any],
) -> list[tuple[Source, Path, Path]]:
    expected = suite_fingerprint(examples)
    inputs: list[tuple[Source, Path, Path]] = []
    for spec in SOURCES:
        bundle, report = _paths(root, spec)
        payload = json.loads(report.read_text(encoding="utf-8"))
        suite = payload["suite"]
        if suite["fingerprint"] != expected or suite["n"] != len(examples):
            raise ValueError("Saved candidate development suite fingerprint mismatch: " + spec.name)
        predictions = load_bundle(bundle)
        if len(predictions.uncertainty) != len(examples):
            raise ValueError("Saved candidate prediction cardinality mismatch: " + spec.name)
        inputs.append((spec, bundle, report))
    return inputs


def _archive_one(
    source: tuple[Source, Path, Path], examples: list[Any],
    secret: bytes, folder: Path,
) -> tuple[Path, dict[str, object]]:
    spec, bundle_path, report_path = source
    bundle_sha, report_sha = _sha(bundle_path), _sha(report_path)
    path = capture(
        examples, load_bundle(bundle_path), secret=secret, folder=folder,
        run_id="retro-" + spec.name + "-s138",
        candidate=spec.name, seed=138,
        model_sha=bundle_sha, config_sha=report_sha,
        policy="v1", suite_name="development",
        artifact_kind="saved_prediction_bundle",
        config_kind="saved_evaluation_report",
        preprocessing_variant=spec.variant,
        decision_stage=spec.stage,
    )
    return path, {
        "candidate": spec.name,
        "saved_prediction_bundle_sha256": bundle_sha,
        "saved_evaluation_report_sha256": report_sha,
        "actual_trained_weight_sha256": None,
        "preprocessing": spec.variant,
        "stage": spec.stage,
    }


def retrofit(archive_root: Path, output_dir: Path) -> dict[str, Any]:
    root = archive_root.resolve()
    destination = _private_root(output_dir)
    if not root.is_dir():
        raise ValueError("The reviewed saved-artifact archive must exist")
    _train, development = load_development_data(include_admitted=True)
    sources = _preflight(root, development)
    # One fresh key joins all candidates *inside this one offline analysis*.
    secret = secrets.token_bytes(32)
    paths: list[Path] = []
    manifest: list[dict[str, object]] = []
    for item in sources:
        saved, info = _archive_one(item, development, secret, destination)
        paths.append(saved)
        manifest.append(info)
    comparison = diagnose(paths)
    result = {
        "schema_version": "w25-saved-bundle-retrofit/1",
        "source_suite": "hash-verified W11/W21/W26 development only",
        "sample_count": len(development),
        "source_candidate_count": len(sources),
        "archive_lineage": manifest,
        "comparison": comparison,
        "neural_inference_or_training_performed": False,
        "model_weights_not_reauthenticated": True,
        "future_model_runs_require_new_privately_managed_hmac": True,
        "not_99pct_or_deployment_evidence": True,
    }
    target = destination / "retrofitted-w25-development-comparison.json"
    with target.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, sort_keys=True, allow_nan=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze saved W25 prediction bundles")
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = retrofit(args.archive_root, args.private_dir)
    print(json.dumps({
        "status": "Saved W25 development predictions compared offline",
        "candidates": summary["source_candidate_count"],
        "cases": summary["sample_count"],
        "model_inference_performed": False,
        "report": "retrofitted-w25-development-comparison.json",
    }, indent=2))


if __name__ == "__main__":
    main()
