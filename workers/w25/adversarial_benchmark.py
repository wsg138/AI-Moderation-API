"""Bundle-based adversarial benchmark aggregation for W25."""

from __future__ import annotations

from pathlib import Path

from workers.w12.dataset import ACTION_TO_ID, ModerationExample
from workers.w25.adversarial_metrics import paired_attack_report
from workers.w25.artifacts import load_bundle
from workers.w25.attacks import ATTACK_FAMILIES
from workers.w25.contract import PredictionBundle


def adversarial_bundle_report(
    examples: list[ModerationExample],
    clean_bundle_path: Path,
    attacked_bundle_paths: dict[str, Path],
) -> dict[str, object]:
    missing = set(ATTACK_FAMILIES) - attacked_bundle_paths.keys()
    if missing:
        raise ValueError(f"missing attack families: {sorted(missing)}")
    clean = load_bundle(clean_bundle_path)
    _require_bundle_length(clean, examples)
    gold = [1 if example.action == "BLOCK" else 0 for example in examples]
    clean_block = _block_predictions(clean)
    families = {
        family: _family_report(
            gold,
            clean_block,
            attacked_bundle_paths[family],
            examples,
        )
        for family in ATTACK_FAMILIES
    }
    return {
        "n": len(examples),
        "families": families,
        "worst_attack_success_rate": max(
            float(report["attack_success_rate"]) for report in families.values()
        ),
        "worst_benign_corruption_false_positive_rate": max(
            float(report["benign_corruption_false_positive_rate"])
            for report in families.values()
        ),
    }


def _family_report(
    gold: list[int],
    clean_block: list[int],
    path: Path,
    examples: list[ModerationExample],
) -> dict[str, object]:
    bundle = load_bundle(path)
    _require_bundle_length(bundle, examples)
    return paired_attack_report(gold, clean_block, _block_predictions(bundle))


def _block_predictions(bundle: PredictionBundle) -> list[int]:
    block_id = ACTION_TO_ID["BLOCK"]
    return [1 if value == block_id else 0 for value in bundle.predictions["action"]]


def _require_bundle_length(
    bundle: PredictionBundle,
    examples: list[ModerationExample],
) -> None:
    bundle.validate()
    if len(bundle.uncertainty) != len(examples):
        raise ValueError("adversarial prediction bundle length mismatch")
