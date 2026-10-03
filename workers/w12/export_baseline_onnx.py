"""W12: Convert TF-IDF baseline to ONNX (if baseline is selected).

Converts the sklearn TF-IDF + LogisticRegression pipeline to ONNX for
production CPU inference. Used only if the evidence selects the baseline
over encoder candidates.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

from .baseline import load_baseline

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
EXPORT_DIR = ARTIFACT_DIR / "onnx"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def export_baseline_onnx() -> dict:
    model = load_baseline(ARTIFACT_DIR / "baseline-tfidf.pkl")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Build a sklearn pipeline: TF-IDF is already fitted; we convert each head.
    # skl2onnx needs a single pipeline, so we wrap vectorizer + head.
    from sklearn.pipeline import make_pipeline

    outputs = {}
    for head_name, head in model.heads.items():
        pipe = make_pipeline(model.vectorizer, head)
        onnx_model = convert_sklearn(
            pipe,
            name=f"baseline-{head_name}",
            initial_types=[("input", StringTensorType([None, 1]))],
            options={"zipmap": False},
        )
        path = EXPORT_DIR / f"baseline-tfidf-{head_name}.onnx"
        with open(path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        outputs[head_name] = {
            "path": path.name,
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
        }
        print(f"exported {path.name}: {path.stat().st_size} bytes", flush=True)

    metadata = {
        "candidate": "baseline-tfidf",
        "seed": model.seed,
        "heads": outputs,
        "export_command": "python -m workers.w12.export_baseline_onnx",
        "exported_at": time.time(),
    }
    with open(EXPORT_DIR / "baseline-tfidf-metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    return metadata


if __name__ == "__main__":
    export_baseline_onnx()
