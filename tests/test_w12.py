"""W12 tests: split safety, serialization, and the selected ONNX bundle adapter."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from moderation_api.app import _build_local_classifier
from moderation_api.models import (
    ChannelProfile,
    ClassificationInput,
    ContextMessage,
    MemorySnapshot,
    MessageAction,
    Platform,
)
from moderation_api.onnx_classifier import (
    OnnxClassifier,
    OnnxClassifierConfig,
    serialize_input,
)

from workers.w12.dataset import (
    LABELS,
    assert_no_leakage,
    load_adversarial_manifest,
    load_partition,
    load_records_by_id,
    load_split_manifest,
    serialize_messages,
)
from workers.w12.evaluate import SLICES, slice_predicate


def test_split_manifest_counts():
    manifest = load_split_manifest()
    assert manifest["algorithm_version"] == "w11-v2"
    assert len(manifest["partitions"]["train"]) == 3269
    assert len(manifest["partitions"]["validation"]) == 385
    assert len(manifest["partitions"]["test"]) == 410


def test_no_partition_overlap():
    manifest = load_split_manifest()
    adv = load_adversarial_manifest()
    train = set(manifest["partitions"]["train"])
    val = set(manifest["partitions"]["validation"])
    test = set(manifest["partitions"]["test"])
    adv_ids = set(adv.get("example_ids", adv.get("frozen_adversarial", [])))
    assert_no_leakage(train, val, test, adv_ids)


def test_serialization_excludes_answer_metadata():
    """The serializer must not leak labels, notes, reason codes, or IDs."""
    records = load_records_by_id()
    record = records["G01-0001"]
    text = serialize_messages(record["channel_profile"], record["messages"], record["target_index"])
    assert "[PROFILE=minecraft_public]" in text
    assert "[TARGET]" in text
    for forbidden in [
        record["label"],
        record["action"],
        record["domain"],
        record["difficulty"],
        record["example_id"],
        "GAMEPLAY_VIOLENCE",
    ]:
        assert f"[LABEL={forbidden}]" not in text
    assert "notes" not in text.lower() or "minecraft combat" not in text.lower()
    for code in record["reason_codes"]:
        assert code not in text


def test_label_vocabulary_matches_service():
    from moderation_api.models import Label

    service_labels = {label.value for label in Label}
    assert set(LABELS) == service_labels


def test_partitions_load():
    train = load_partition("train")
    val = load_partition("validation")
    assert len(train) == 3269
    assert len(val) == 385
    assert all(example.serialized for example in train)

def test_canonical_training_serialization_excludes_future_and_normalizes_speakers():
    messages = [
        {"speaker": "B", "offset_ms": -1200, "text": "prior"},
        {"speaker": "A", "offset_ms": 0, "text": "current"},
        {"speaker": "SYSTEM", "offset_ms": 500, "text": "future response"},
    ]
    serialized = serialize_messages("minecraft_public", messages, 1)
    assert serialized == (
        "[PROFILE=minecraft_public]\n"
        "[A@-1200ms] prior\n"
        "[B@+0ms] [TARGET] current"
    )
    assert "future response" not in serialized
    assert "SYSTEM" not in serialized


def test_train_records_do_not_serialize_post_target_future_messages():
    example = next(item for item in load_partition("train") if item.example_id == "G04-0461")
    assert "I've been having thoughts about not wanting to be alive" in example.serialized
    assert "Are you safe right now" not in example.serialized
    assert "no, I'm safe right now" not in example.serialized


def test_required_validation_slices_are_non_empty():
    validation = load_partition("validation")
    counts = {
        name: sum(slice_predicate(example, name) for example in validation)
        for name in SLICES
    }
    assert all(count > 0 for count in counts.values()), counts



def _message(
    *,
    event_id: str,
    external_message_id: str,
    sender_id: str,
    occurred_at: datetime,
    text: str,
) -> ContextMessage:
    return ContextMessage(
        event_id=event_id,
        platform=Platform.MINECRAFT,
        channel_profile=ChannelProfile.MINECRAFT_PUBLIC,
        scope_id="smp",
        channel_id=None,
        conversation_id=None,
        external_message_id=external_message_id,
        canonical_message_id=None,
        sender_id=sender_id,
        sender_identity_id=None,
        recipient_ids=(),
        recipient_identity_ids=(),
        target_ids=(),
        target_identity_ids=(),
        occurred_at=occurred_at,
        text=text,
        reply_to_message_id=None,
    )


def _make_input(text: str = "irl at your school tomorrow") -> ClassificationInput:
    start = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    prior = _message(
        event_id="evt-0",
        external_message_id="mc-0",
        sender_id="player-a",
        occurred_at=start,
        text="im gonna get you",
    )
    current = _message(
        event_id="evt-1",
        external_message_id="mc-1",
        sender_id="player-b",
        occurred_at=start + timedelta(milliseconds=800),
        text=text,
    )
    return ClassificationInput(current=current, context=(prior,), memory=MemorySnapshot())


def test_serialize_input_matches_training_shape():
    serialized = serialize_input(_make_input())
    assert serialized == (
        "[PROFILE=minecraft_public]\n"
        "[A@-800ms] im gonna get you\n"
        "[B@+0ms] [TARGET] irl at your school tomorrow"
    )
    assert "player-a" not in serialized
    assert "player-b" not in serialized

def test_runtime_and_training_serializers_match_same_logical_sequence():
    runtime = serialize_input(_make_input())
    training = serialize_messages(
        "minecraft_public",
        [
            {"speaker": "B", "offset_ms": -800, "text": "im gonna get you"},
            {"speaker": "A", "offset_ms": 0, "text": "irl at your school tomorrow"},
        ],
        1,
    )
    assert runtime == training



def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_constant_onnx(path: Path, probabilities: list[float]) -> None:
    import onnx
    from onnx import TensorProto, helper

    input_info = helper.make_tensor_value_info("features", TensorProto.FLOAT, [None, 1])
    output_info = helper.make_tensor_value_info(
        "probabilities", TensorProto.FLOAT, [1, len(probabilities)]
    )
    value = helper.make_tensor(
        "constant_probabilities",
        TensorProto.FLOAT,
        [1, len(probabilities)],
        probabilities,
    )
    node = helper.make_node("Constant", inputs=[], outputs=["probabilities"], value=value)
    graph = helper.make_graph(
        [node],
        f"fixture-{path.stem}",
        [input_info],
        [output_info],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_operatorsetid("", 17)])
    model.ir_version = 10
    onnx.checker.check_model(model)
    onnx.save(model, path)


_FIXTURE_HEADS = {
    "label": (["SAFE", "REAL_WORLD_THREAT"], [0.1, 0.9]),
    "action": (["ALLOW", "BLOCK", "REVIEW"], [0.05, 0.9, 0.05]),
    "review_priority": (["NONE", "NORMAL", "URGENT"], [0.05, 0.15, 0.8]),
    "strike": (["false", "true"], [0.1, 0.9]),
    "containment": (["NONE", "MUTE"], [0.95, 0.05]),
    "support_flow": (
        ["NONE", "SELF_HARM_CHECK", "TARGET_SAFETY_CHECK"],
        [0.9, 0.05, 0.05],
    ),
}


def _write_fixture_heads(tmp_path: Path) -> dict[str, object]:
    heads: dict[str, object] = {}
    for head, (classes, probabilities) in _FIXTURE_HEADS.items():
        model_path = tmp_path / f"baseline-tfidf-{head}.onnx"
        _write_constant_onnx(model_path, probabilities)
        heads[head] = {
            "path": model_path.name,
            "sha256": _sha256(model_path),
            "bytes": model_path.stat().st_size,
            "input_name": "features",
            "probabilities_output": "probabilities",
            "classes": classes,
            "class_ids": list(range(len(classes))),
        }
    return heads


def _write_fixture_vectorizer(tmp_path: Path) -> Path:
    path = tmp_path / "baseline-tfidf-vectorizer.json"
    payload = {
        "schema_version": 1,
        "terms": ["school"],
        "idf": [1.0],
        "lowercase": True,
        "ngram_range": [1, 2],
        "sublinear_tf": True,
        "norm": "l2",
        "token_pattern": r"(?u)\\b\\w\\w+\\b",
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _write_fixture_bundle(tmp_path: Path) -> OnnxClassifierConfig:
    vectorizer_path = _write_fixture_vectorizer(tmp_path)
    metadata = {
        "schema_version": 2,
        "candidate": "baseline-tfidf",
        "model_version": "w12-fixture-v2",
        "seed": 42,
        "serialization_version": "w12-v2",
        "serialization": "canonical W12 v2 fixture",
        "vectorizer": {
            "path": vectorizer_path.name,
            "sha256": _sha256(vectorizer_path),
            "bytes": vectorizer_path.stat().st_size,
            "feature_count": 1,
        },
        "target_opset": 17,
        "heads": _write_fixture_heads(tmp_path),
    }
    metadata_path = tmp_path / "baseline-tfidf-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return OnnxClassifierConfig(
        metadata_path=metadata_path,
        expected_metadata_sha256=_sha256(metadata_path),
        timeout_ms=500,
    )

def test_onnx_classifier_not_ready_without_metadata(tmp_path):
    cfg = OnnxClassifierConfig(
        metadata_path=tmp_path / "missing.json",
        expected_metadata_sha256="0" * 64,
    )
    classifier = OnnxClassifier(cfg)
    health = classifier.health()
    assert health["ready"] is False
    assert "metadata" in str(health.get("error", "")).lower()


def test_onnx_classifier_rejects_metadata_checksum_mismatch(tmp_path):
    cfg = _write_fixture_bundle(tmp_path)
    bad = OnnxClassifierConfig(
        metadata_path=cfg.metadata_path,
        expected_metadata_sha256="f" * 64,
    )
    classifier = OnnxClassifier(bad)
    health = classifier.health()
    assert health["ready"] is False
    assert "metadata checksum" in str(health.get("error", "")).lower()


def test_onnx_classifier_rejects_wrong_serialization_version(tmp_path):
    cfg = _write_fixture_bundle(tmp_path)
    metadata = json.loads(cfg.metadata_path.read_text(encoding="utf-8"))
    metadata["serialization_version"] = "w12-v1"
    cfg.metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    classifier = OnnxClassifier(
        OnnxClassifierConfig(
            metadata_path=cfg.metadata_path,
            expected_metadata_sha256=_sha256(cfg.metadata_path),
        )
    )
    health = classifier.health()
    assert health["ready"] is False
    assert "serialization version" in str(health.get("error", "")).lower()


def test_onnx_classifier_rejects_head_checksum_mismatch(tmp_path):
    cfg = _write_fixture_bundle(tmp_path)
    (tmp_path / "baseline-tfidf-label.onnx").write_bytes(b"tampered")
    classifier = OnnxClassifier(cfg)
    health = classifier.health()
    assert health["ready"] is False
    error = str(health.get("error", "")).lower()
    assert "label" in error
    assert "checksum mismatch" in error


def test_onnx_classifier_rejects_head_vectorizer_shape_mismatch(tmp_path):
    cfg = _write_fixture_bundle(tmp_path)
    vectorizer_path = tmp_path / "baseline-tfidf-vectorizer.json"
    vectorizer = json.loads(vectorizer_path.read_text(encoding="utf-8"))
    vectorizer["terms"] = ["school", "tomorrow"]
    vectorizer["idf"] = [1.0, 1.0]
    vectorizer_path.write_text(json.dumps(vectorizer) + "\n", encoding="utf-8")

    metadata = json.loads(cfg.metadata_path.read_text(encoding="utf-8"))
    metadata["vectorizer"]["sha256"] = _sha256(vectorizer_path)
    metadata["vectorizer"]["bytes"] = vectorizer_path.stat().st_size
    metadata["vectorizer"]["feature_count"] = 2
    cfg.metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    classifier = OnnxClassifier(
        OnnxClassifierConfig(
            metadata_path=cfg.metadata_path,
            expected_metadata_sha256=_sha256(cfg.metadata_path),
        )
    )
    health = classifier.health()
    assert health["ready"] is False
    assert "feature dimension" in str(health.get("error", "")).lower()


@pytest.mark.asyncio
async def test_selected_baseline_bundle_loads_and_infers(tmp_path):
    cfg = _write_fixture_bundle(tmp_path)
    classifier = OnnxClassifier(cfg)
    health = classifier.health()
    assert health["ready"] is True
    assert health["heads_loaded"] == 6
    assert health["feature_count"] == 1
    assert health["mode"] == "onnx-baseline-tfidf"

    result = await classifier.classify(_make_input())
    assert result.semantic_label.value == "REAL_WORLD_THREAT"
    assert result.message_action is MessageAction.BLOCK
    assert result.review_priority.value == "URGENT"
    assert result.strike_recommendation.value == "STRIKE"
    assert result.containment.value == "NONE"
    assert result.support_flow.value == "NONE"
    assert result.model_version.startswith("w12-fixture-v2+")
    assert result.scores["action:BLOCK"] == pytest.approx(0.9)
    assert result.confidence == pytest.approx(0.9)


def test_service_factory_uses_configured_bundle(tmp_path, monkeypatch):
    cfg = _write_fixture_bundle(tmp_path)
    monkeypatch.setenv("AI_MOD_ONNX_METADATA_PATH", str(cfg.metadata_path))
    monkeypatch.setenv("AI_MOD_ONNX_METADATA_SHA256", cfg.expected_metadata_sha256)
    classifier = _build_local_classifier()
    assert classifier.health()["ready"] is True


@pytest.mark.asyncio
async def test_onnx_classifier_not_ready_raises(tmp_path):
    cfg = OnnxClassifierConfig(
        metadata_path=tmp_path / "missing.json",
        expected_metadata_sha256="0" * 64,
    )
    classifier = OnnxClassifier(cfg)
    with pytest.raises(RuntimeError):
        await classifier.classify(_make_input())
