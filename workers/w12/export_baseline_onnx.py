"""Export the selected W12 TF-IDF baseline as safe metadata + standard-op ONNX heads."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import onnx
import sklearn
from onnx import TensorProto, helper, numpy_helper

from .baseline import load_baseline

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
EXPORT_DIR = ARTIFACT_DIR / "onnx"
MODEL_VERSION = "w12-baseline-tfidf-v1"
METADATA_SCHEMA_VERSION = 2
TARGET_OPSET = 17


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _export_vectorizer(model) -> dict[str, object]:
    vectorizer = model.vectorizer
    if (
        vectorizer.ngram_range != (1, 2)
        or vectorizer.norm != "l2"
        or not vectorizer.sublinear_tf
        or not vectorizer.lowercase
    ):
        raise RuntimeError("selected baseline vectorizer no longer matches W12 runtime contract")

    payload = {
        "schema_version": 1,
        "terms": vectorizer.get_feature_names_out().tolist(),
        "idf": vectorizer.idf_.tolist(),
        "lowercase": True,
        "ngram_range": [1, 2],
        "sublinear_tf": True,
        "norm": "l2",
        "token_pattern": vectorizer.token_pattern,
    }
    path = EXPORT_DIR / "baseline-tfidf-vectorizer.json"
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    return {
        "path": path.name,
        "sha256": sha256_of(path),
        "bytes": path.stat().st_size,
        "feature_count": len(payload["terms"]),
    }


def _binary_probability_nodes(logits_name: str) -> list[onnx.NodeProto]:
    return [
        helper.make_node("Sigmoid", [logits_name], ["positive_probability"]),
        helper.make_node(
            "Sub",
            ["one", "positive_probability"],
            ["negative_probability"],
        ),
        helper.make_node(
            "Concat",
            ["negative_probability", "positive_probability"],
            ["probabilities"],
            axis=1,
        ),
    ]


def _multiclass_probability_nodes(logits_name: str) -> list[onnx.NodeProto]:
    return [helper.make_node("Softmax", [logits_name], ["probabilities"], axis=1)]


def _standard_logistic_graph(head_name: str, head, feature_count: int) -> onnx.ModelProto:
    coefficients = np.asarray(head.coef_, dtype=np.float32)
    intercept = np.asarray(head.intercept_, dtype=np.float32)
    if coefficients.ndim != 2 or coefficients.shape[1] != feature_count:
        raise RuntimeError(f"unexpected coefficient shape for {head_name}: {coefficients.shape}")

    class_count = len(head.classes_)
    expected_rows = 1 if class_count == 2 else class_count
    if coefficients.shape[0] != expected_rows or intercept.shape != (expected_rows,):
        raise RuntimeError(
            f"unexpected logistic shape for {head_name}: "
            f"coef={coefficients.shape} intercept={intercept.shape} classes={class_count}"
        )

    input_info = helper.make_tensor_value_info(
        "features",
        TensorProto.FLOAT,
        [None, feature_count],
    )
    output_info = helper.make_tensor_value_info(
        "probabilities",
        TensorProto.FLOAT,
        [None, class_count],
    )
    weights = numpy_helper.from_array(coefficients.T.copy(), name="weights")
    bias = numpy_helper.from_array(intercept.copy(), name="bias")
    nodes = [
        helper.make_node("MatMul", ["features", "weights"], ["linear"]),
        helper.make_node("Add", ["linear", "bias"], ["logits"]),
    ]
    initializers = [weights, bias]
    if class_count == 2:
        initializers.append(
            numpy_helper.from_array(np.asarray([1.0], dtype=np.float32), name="one")
        )
        nodes.extend(_binary_probability_nodes("logits"))
    else:
        nodes.extend(_multiclass_probability_nodes("logits"))

    graph = helper.make_graph(
        nodes,
        f"baseline-{head_name}",
        [input_info],
        [output_info],
        initializer=initializers,
    )
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_operatorsetid("", TARGET_OPSET)],
        producer_name="enthusia-w12-standard-logistic-export",
    )
    onnx.checker.check_model(model)
    return model


def _export_head(
    head_name: str,
    head,
    classes: list[str],
    feature_count: int,
) -> dict[str, object]:
    onnx_model = _standard_logistic_graph(head_name, head, feature_count)
    path = EXPORT_DIR / f"baseline-tfidf-{head_name}.onnx"
    onnx.save(onnx_model, path)
    class_ids = [int(value) for value in head.classes_.tolist()]
    class_names = [classes[class_id] for class_id in class_ids]
    return {
        "path": path.name,
        "sha256": sha256_of(path),
        "bytes": path.stat().st_size,
        "input_name": "features",
        "probabilities_output": "probabilities",
        "classes": class_names,
        "class_ids": class_ids,
    }


def export_baseline_onnx() -> dict[str, object]:
    model = load_baseline(ARTIFACT_DIR / "baseline-tfidf.pkl")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    vectorizer = _export_vectorizer(model)
    feature_count = int(vectorizer["feature_count"])
    outputs: dict[str, object] = {}
    for head_name, head in model.heads.items():
        exported = _export_head(
            head_name,
            head,
            model.classes[head_name],
            feature_count,
        )
        outputs[head_name] = exported
        print(f"exported {exported['path']}: {exported['bytes']} bytes", flush=True)

    metadata: dict[str, object] = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "candidate": "baseline-tfidf",
        "model_version": MODEL_VERSION,
        "seed": model.seed,
        "serialization": (
            "w12-v1: [PROFILE=profile] + [A@+offsetms] speaker markers + [TARGET]"
        ),
        "vectorizer": vectorizer,
        "target_opset": TARGET_OPSET,
        "export_backend": "standard-onnx-logistic-regression",
        "sklearn_version": sklearn.__version__,
        "onnx_version": onnx.__version__,
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
