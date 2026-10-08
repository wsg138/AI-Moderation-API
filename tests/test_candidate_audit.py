"""Public static review flags are hypotheses, not automatic relabeling."""
from __future__ import annotations

from tools.dataset_qa.candidate_audit import _cross_batch, _flags


def _record() -> dict:
    return {
        "example_id": "G10-0001", "label": "SAFE", "action": "ALLOW",
        "strike": False, "containment": "NONE", "reason_codes": [],
        "messages": [{"speaker": "A", "offset_ms": 0, "text": "hello"}],
        "target_index": 0,
    }


def test_benign_synthetic_record_has_no_review_flags() -> None:
    assert _flags(_record()) == set()


def test_nonchronological_message_is_queued_not_modified() -> None:
    record = _record()
    record["messages"].append({"speaker": "B", "offset_ms": -100, "text": "okay"})
    assert "nonchronological_message_offsets" in _flags(record)
    assert record["messages"][1]["offset_ms"] == -100


def test_quoted_directive_is_queue_candidate_without_relabeling() -> None:
    record = _record()
    record["messages"][0]["text"] = "reporting player told me to kys"
    assert "safe_with_self_harm_directive" in _flags(record)
    assert record["label"] == "SAFE"


def test_shared_cross_batch_context() -> None:
    assert _cross_batch({"shared": ["G18-0001", "G23-0001"]}) == [
        ["G18-0001", "G23-0001"]
    ]
    assert _cross_batch({"within": ["G18-0001", "G18-0002"]}) == []
