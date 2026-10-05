"""One-shot evaluator for an independently frozen W12-v2 acceptance corpus.

This tool never opens the superseded W11 held-outs. It evaluates an explicitly
provided JSONL acceptance set against an explicitly checksum-pinned ONNX bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from moderation_api.model_serialization import SERIALIZATION_VERSION
from moderation_api.onnx_classifier import OnnxClassifier, OnnxClassifierConfig
from moderation_api.tfidf_runtime import TfidfRuntimeVectorizer

from .dataset import ACTION_TO_ID, LABEL_TO_ID, ModerationExample, _record_to_example
from .dataset import is_fully_labeled
from .evaluate import _slice_metrics, evaluate_predictions, runtime_visibility, slice_predicate

HEAD_NAMES = ("label", "action", "review_priority", "strike", "containment", "support_flow")

COVERAGE_MINIMA = {
    "minecraft_gameplay": 25,
    "generic_minecraft_violence": 20,
    "benign_hard_negatives": 30,
    "real_world_threat": 25,
    "split_message_threat": 20,
    "long_gap_non_linkage": 15,
    "self_harm_instruction": 15,
    "first_person_self_harm_disclosure": 15,
    "slur_actual_use": 15,
    "slur_reference_only": 15,
    "sexual_minor": 20,
    "age_self_report_only": 20,
    "real_world_explosive_request": 15,
    "obfuscation_evasion": 20,
    "private_flirting": 20,
    "discord_general": 25,
    "minecraft_public": 25,
}

MAX_SLICE_GATES = {
    "benign_hard_negatives": 0.05,
    "minecraft_gameplay": 0.05,
    "generic_minecraft_violence": 0.05,
    "minecraft_public": 0.05,
    "discord_general": 0.08,
    "private_flirting": 0.10,
    "age_self_report_only": 0.10,
    "long_gap_non_linkage": 0.05,
}

MIN_SLICE_GATES = {
    "real_world_threat": 0.90,
    "split_message_threat": 0.90,
    "self_harm_instruction": 0.90,
    "sexual_minor": 0.95,
    "real_world_explosive_request": 0.95,
    "slur_actual_use": 0.90,
    "obfuscation_evasion": 0.85,
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_acceptance(path: Path) -> list[ModerationExample]:
    records = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        record = json.loads(raw)
        if not is_fully_labeled(record):
            raise ValueError(f"acceptance record on line {line_number} is not fully labeled")
        records.append(record)
    ids = [str(record["example_id"]) for record in records]
    if not records or len(ids) != len(set(ids)):
        raise ValueError("acceptance set must be non-empty with unique example IDs")
    return [_record_to_example(record) for record in records]


def validate_acceptance_manifest(
    manifest_path: Path,
    acceptance_path: Path,
    examples: list[ModerationExample],
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_flags = {
        "contract": "w12-v2-fresh-acceptance-v1",
        "acceptance_only": True,
        "forbidden_for_training": True,
        "built_without_w12_predictions": True,
    }
    for key, expected in required_flags.items():
        if manifest.get(key) != expected:
            raise ValueError(f"invalid acceptance manifest field {key}")
    if manifest.get("dataset_sha256") != sha256_of(acceptance_path):
        raise ValueError("acceptance manifest dataset SHA-256 mismatch")
    if manifest.get("record_count") != len(examples):
        raise ValueError("acceptance manifest record count mismatch")
    family_count = len({example.family_id for example in examples if example.family_id})
    if manifest.get("family_count") != family_count:
        raise ValueError("acceptance manifest family count mismatch")
    return manifest

def load_bundle(metadata_path: Path, expected_sha256: str) -> dict[str, Any]:
    actual = sha256_of(metadata_path)
    if actual.lower() != expected_sha256.lower():
        raise ValueError("selected model metadata checksum mismatch")
    classifier = OnnxClassifier(
        OnnxClassifierConfig(
            metadata_path=metadata_path,
            expected_metadata_sha256=expected_sha256,
        )
    )
    if classifier.health().get("ready") is not True:
        raise ValueError(f"selected model bundle is not ready: {classifier.health()}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("serialization_version") != SERIALIZATION_VERSION:
        raise ValueError("acceptance bundle does not use current W12 serialization")
    return metadata


def _feature_tensor(metadata: dict[str, Any], root: Path, texts: list[str]) -> Any:
    vectorizer_info = metadata["vectorizer"]
    vectorizer = TfidfRuntimeVectorizer.from_file(root / vectorizer_info["path"])
    return np.vstack([vectorizer.transform(text, np) for text in texts])


def _predict_head(root: Path, info: dict[str, Any], tensor: Any) -> tuple[list[int], Any]:
    session = ort.InferenceSession(str(root / info["path"]), providers=["CPUExecutionProvider"])
    probabilities = np.asarray(
        session.run(
            [info["probabilities_output"]],
            {info["input_name"]: tensor},
        )[0],
        dtype=float,
    )
    class_ids = [int(value) for value in info["class_ids"]]
    predictions = [class_ids[int(index)] for index in np.argmax(probabilities, axis=1)]
    return predictions, probabilities


def predict_bundle(
    metadata: dict[str, Any],
    root: Path,
    examples: list[ModerationExample],
) -> tuple[dict[str, list[int]], list[float]]:
    tensor = _feature_tensor(metadata, root, [example.serialized for example in examples])
    predictions: dict[str, list[int]] = {}
    action_probabilities: Any = None
    for name in HEAD_NAMES:
        predicted, probabilities = _predict_head(root, metadata["heads"][name], tensor)
        predictions[name] = predicted
        if name == "action":
            action_probabilities = probabilities
    if action_probabilities is None:
        raise ValueError("selected bundle is missing action probabilities")
    action_classes = [int(value) for value in metadata["heads"]["action"]["class_ids"]]
    block_column = action_classes.index(ACTION_TO_ID["BLOCK"])
    return predictions, action_probabilities[:, block_column].tolist()


def _augment_w20_hard_negative_slice(
    report: dict[str, Any],
    examples: list[ModerationExample],
    predictions: dict[str, list[int]],
) -> None:
    indices = [
        index
        for index, example in enumerate(examples)
        if example.domain == "benign_hard_negative"
        or slice_predicate(example, "benign_hard_negatives")
    ]
    if not indices:
        report["critical_slices"]["benign_hard_negatives"] = {"n": 0}
        return
    gold_visibility = [runtime_visibility(example.action) for example in examples]
    predicted_visibility = [
        1 if value == ACTION_TO_ID["BLOCK"] else 0 for value in predictions["action"]
    ]
    gold_label = [LABEL_TO_ID[example.label] for example in examples]
    report["critical_slices"]["benign_hard_negatives"] = _slice_metrics(
        examples,
        indices,
        gold_visibility,
        predicted_visibility,
        gold_label,
        predictions["label"],
    )


def _urgent_recall(report: dict[str, Any]) -> float:
    for item in report["review_priority"]["per_class"]:
        if item["priority"] == "URGENT":
            return float(item["recall"])
    return 0.0


def _gate(failures: list[dict[str, Any]], name: str, value: float, limit: float, op: str) -> None:
    passed = value >= limit if op == "min" else value <= limit
    if not passed:
        failures.append({"gate": name, "value": value, "required": f"{op} {limit}"})


def evaluate_gates(report: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    runtime = report["runtime_visibility_binary"]
    _gate(failures, "runtime_block_precision", float(runtime["block_precision"]), 0.90, "min")
    _gate(failures, "runtime_block_recall", float(runtime["block_recall"]), 0.90, "min")
    _gate(failures, "semantic_macro_f1", float(report["semantic_label"]["macro_f1"]), 0.75, "min")
    _gate(failures, "review_macro_f1", float(report["review_priority"]["macro_f1"]), 0.80, "min")
    _gate(failures, "urgent_review_recall", _urgent_recall(report), 0.85, "min")
    _slice_gates(report, failures)
    _class_collapse_gates(report, failures)
    return failures


def _slice_gates(report: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    slices = report["critical_slices"]
    for name, minimum in COVERAGE_MINIMA.items():
        count = int(slices.get(name, {}).get("n", 0))
        if count < minimum:
            failures.append({"gate": f"coverage:{name}", "value": count, "required": f"min {minimum}"})
    for name, maximum in MAX_SLICE_GATES.items():
        value = slices.get(name, {}).get("block_false_positive_rate")
        if value is None:
            failures.append({"gate": f"fp:{name}", "value": None, "required": f"max {maximum}"})
        else:
            _gate(failures, f"fp:{name}", float(value), maximum, "max")
    for name, minimum in MIN_SLICE_GATES.items():
        value = slices.get(name, {}).get("block_recall")
        if value is None:
            failures.append({"gate": f"recall:{name}", "value": None, "required": f"min {minimum}"})
        else:
            _gate(failures, f"recall:{name}", float(value), minimum, "min")


def _class_collapse_gates(report: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    for item in report["semantic_label"]["per_class"]:
        if int(item["support"]) >= 10 and float(item["f1"]) < 0.50:
            failures.append(
                {
                    "gate": f"class_f1:{item['label']}",
                    "value": float(item["f1"]),
                    "required": "min 0.5 when support >= 10",
                }
            )


def run(
    acceptance_path: Path,
    manifest_path: Path,
    metadata_path: Path,
    metadata_sha256: str,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError("refusing to overwrite an existing one-shot acceptance report")
    examples = load_acceptance(acceptance_path)
    manifest = validate_acceptance_manifest(manifest_path, acceptance_path, examples)
    metadata = load_bundle(metadata_path, metadata_sha256)
    predictions, block_probabilities = predict_bundle(metadata, metadata_path.parent, examples)
    report = evaluate_predictions(
        examples,
        predictions["label"],
        predictions["action"],
        predictions["review_priority"],
        predictions["strike"],
        predictions["containment"],
        predictions["support_flow"],
        block_probabilities,
    )
    _augment_w20_hard_negative_slice(report, examples, predictions)
    failures = evaluate_gates(report)
    result = {
        "contract": "w12-v2-fresh-acceptance-v1",
        "acceptance_jsonl_sha256": sha256_of(acceptance_path),
        "acceptance_manifest_sha256": sha256_of(manifest_path),
        "acceptance_contract": manifest["contract"],
        "model_metadata_sha256": sha256_of(metadata_path),
        "model_version": metadata["model_version"],
        "n": len(examples),
        "passed": not failures,
        "gate_failures": failures,
        "metrics": report,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-jsonl", type=Path, required=True)
    parser.add_argument("--acceptance-manifest", type=Path, required=True)
    parser.add_argument("--metadata-path", type=Path, required=True)
    parser.add_argument("--metadata-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.acceptance_jsonl,
        args.acceptance_manifest,
        args.metadata_path,
        args.metadata_sha256,
        args.output,
    )
    print(json.dumps({"passed": result["passed"], "gate_failures": result["gate_failures"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 2)


if __name__ == "__main__":
    main()
