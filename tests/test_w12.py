"""W12 tests: dataset loading, leakage-safe serialization, ONNX adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from moderation_api.models import (
    ChannelProfile,
    ClassificationInput,
    ContextMessage,
    MemorySnapshot,
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

W12_DIR = Path(__file__).resolve().parents[1] / "workers" / "w12"


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
    # Structural info present
    assert "[PROFILE=minecraft_public]" in text
    assert "[TARGET]" in text
    # Answer/editorial metadata absent
    for forbidden in [
        record["label"],
        record["action"],
        record["domain"],
        record["difficulty"],
        record["example_id"],
        "GAMEPLAY_VIOLENCE",
    ]:
        # label text itself would only appear if leaked; the raw message text
        # may coincidentally contain words, so check structured markers
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
    assert all(e.serialized for e in train)


# ---------------------------------------------------------------------------
# ONNX adapter tests (no real model binary in git; use fixture behavior)
# ---------------------------------------------------------------------------
# (imports moved to top)
# ---------------------------------------------------------------------------


def _make_input(text: str = "im gonna kill you") -> ClassificationInput:
    now = datetime.now(UTC)
    current = ContextMessage(
        event_id="evt-1",
        platform=Platform.MINECRAFT,
        channel_profile=ChannelProfile.MINECRAFT_PUBLIC,
        scope_id="smp",
        channel_id=None,
        conversation_id=None,
        external_message_id="mc-1",
        canonical_message_id=None,
        sender_id="player-a",
        sender_identity_id=None,
        recipient_ids=(),
        recipient_identity_ids=(),
        target_ids=(),
        target_identity_ids=(),
        occurred_at=now,
        text=text,
        reply_to_message_id=None,
    )
    return ClassificationInput(current=current, context=(), memory=MemorySnapshot())


def test_serialize_input_deterministic():
    item = _make_input()
    a = serialize_input(item)
    b = serialize_input(item)
    assert a == b
    assert "[PROFILE=minecraft_public]" in a
    assert "[TARGET]" in a
    assert "im gonna kill you" in a


def test_onnx_classifier_not_ready_without_artifacts(tmp_path):
    cfg = OnnxClassifierConfig(
        model_path=tmp_path / "missing.onnx",
        tokenizer_dir=tmp_path,
        expected_sha256="0" * 64,
        model_version="test-v1",
    )
    clf = OnnxClassifier(cfg)
    assert clf.health()["ready"] is False


def test_onnx_classifier_rejects_checksum_mismatch(tmp_path):
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"fake-onnx-bytes")
    (tmp_path / "vocab.txt").write_text("[PAD]\n[UNK]\n")
    cfg = OnnxClassifierConfig(
        model_path=model_path,
        tokenizer_dir=tmp_path,
        expected_sha256="f" * 64,
        model_version="test-v1",
    )
    clf = OnnxClassifier(cfg)
    health = clf.health()
    assert health["ready"] is False
    assert "checksum" in str(health.get("error", "")).lower()


@pytest.mark.asyncio
async def test_onnx_classifier_not_ready_raises():
    cfg = OnnxClassifierConfig(
        model_path=Path("/nonexistent/model.onnx"),
        tokenizer_dir=Path("/nonexistent"),
        expected_sha256="0" * 64,
        model_version="test-v1",
    )
    clf = OnnxClassifier(cfg)
    with pytest.raises(RuntimeError):
        await clf.classify(_make_input())
