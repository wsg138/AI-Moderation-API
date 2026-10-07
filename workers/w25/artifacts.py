"""Machine-readable W25 artifact helpers."""

from __future__ import annotations

import json
from pathlib import Path

from workers.w25.contract import PredictionBundle


def save_bundle(path: Path, bundle: PredictionBundle) -> None:
    bundle.validate()
    payload = {
        "predictions": bundle.predictions,
        "probabilities": bundle.probabilities,
        "uncertainty": bundle.uncertainty,
    }
    _write_json(path, payload)


def load_bundle(path: Path) -> PredictionBundle:
    payload = json.loads(path.read_text(encoding="utf-8"))
    bundle = PredictionBundle(
        predictions=payload["predictions"],
        probabilities=payload["probabilities"],
        uncertainty=payload["uncertainty"],
    )
    bundle.validate()
    return bundle


def write_report(path: Path, payload: dict[str, object]) -> None:
    _write_json(path, payload)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
