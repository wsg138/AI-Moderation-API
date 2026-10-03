"""Export the selected W12 TF-IDF baseline as a six-head ONNX bundle."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import skl2onnx
import sklearn
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

from .baseline import load_baseline

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
EXPORT_DIR = ARTIFACT_DIR / "onnx"
MODEL_VERSION = "w12-baseline-tfidf-v1"
METADATA_SCHEMA_VERSION = 1


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_baseline_onnx() -> dict[str, object]:
    model = load_baseline(ARTIFACT_DIR / "baseline-tfidf.pkl")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    from sklearn.pipeline import make_pipeline

    outputs: dict[str, object] = {}
    for head_name, head in model.heads.items():
        pipe = make_pipeline(model.vectorizer, head)
        # Force the ONNX StringNormalizer to use the portable C locale instead of
        # the backend-dependent en_US.UTF-8 default that failed on the training host.
        # zipmap=False keeps probabilities as a dense tensor with stable class order.
        options = {
            id(model.vectorizer): {"locale": "C"},
            id(head): {"zipmap": False},
        }
        onnx_model = convert_sklearn(
            pipe,
            name=f"baseline-{head_name}",
            initial_types=[("input", StringTensorType([None, 1]))],
            options=options,
            target_opset=17,
        )
        output_names = [value.name for value in onnx_model.graph.output]
        if len(output_names) < 2:
            raise RuntimeError(
                f"unexpected ONNX outputs for {head_name}: {output_names}"
            )

        path = EXPORT_DIR / f"baseline-tfidf-{head_name}.onnx"
        path.write_bytes(onnx_model.SerializeToString())

        class_ids = [int(value) for value in head.classes_.tolist()]
        class_names = [model.classes[head_name][class_id] for class_id in class_ids]
        outputs[head_name] = {
            "path": path.name,
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
            "input_name": onnx_model.graph.input[0].name,
            "probabilities_output": output_names[-1],
            "classes": class_names,
            "class_ids": class_ids,
        }
        print(f"exported {path.name}: {path.stat().st_size} bytes", flush=True)

    metadata: dict[str, object] = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "candidate": "baseline-tfidf",
        "model_version": MODEL_VERSION,
        "seed": model.seed,
        "serialization": (
            "w12-v1: [PROFILE=profile] + [A@+offsetms] speaker markers + [TARGET]"
        ),
        "locale": "C",
        "target_opset": 17,
        "sklearn_version": sklearn.__version__,
        "skl2onnx_version": skl2onnx.__version__,
        "heads": outputs,
        "export_command": "python -m workers.w12.export_baseline_onnx",
        "exported_at_unix": time.time(),
    }
    metadata_path = EXPORT_DIR / "baseline-tfidf-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(
        f"metadata {metadata_path.name}: sha256={sha256_of(metadata_path)}",
        flush=True,
    )
    return metadata


if __name__ == "__main__":
    export_baseline_onnx()
