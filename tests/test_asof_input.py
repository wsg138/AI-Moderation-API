"""Regression: no future message, label or retrospective metadata reaches model input."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from tools.dataset_qa.asof_input import serialize_as_of_target


def _record() -> dict[str, object]:
    return {
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "messages": [
            {"speaker": "A", "offset_ms": -1000, "text": "I saw a warning"},
            {"speaker": "B", "offset_ms": 0, "text": "I will report this"},
            {"speaker": "A", "offset_ms": 2000, "text": "FUTURE_ONLY_ANSWER: joking"},
        ],
        "target_index": 1,
        "label": "SAFE", "action": "ALLOW",
        "notes": "FUTURE_ONLY_ANSWER: exonerating later evidence",
        "reason_codes": ["FUTURE_ONLY_ANSWER"],
        "family_id": "FUTURE_ONLY_ANSWER",
        "difficulty": "FUTURE_ONLY_ANSWER",
        "source": "FUTURE_ONLY_ANSWER",
    }


def test_future_only_answer_and_metadata_never_enter_features() -> None:
    item = serialize_as_of_target(_record())
    assert item["target_index"] == 1
    assert len(item["messages"]) == 2
    assert set(item) == {
        "platform_hint", "channel_profile", "messages", "target_index"
    }
    assert set(item["messages"][0]) == {"speaker", "offset_ms", "text"}
    assert "FUTURE_ONLY_ANSWER" not in json.dumps(item)


def test_retroactive_changes_do_not_change_as_of_time_input() -> None:
    original = _record()
    changed = deepcopy(original)
    changed["messages"][2]["text"] = "FUTURE_ONLY_ANSWER: actually serious"
    changed["messages"][2]["offset_ms"] = 999999
    changed["notes"] = "different explanation"
    changed["label"] = "REAL_WORLD_THREAT"
    changed["reason_codes"] = ["targeted_violence"]
    assert serialize_as_of_target(original) == serialize_as_of_target(changed)


def test_current_target_must_be_present() -> None:
    record = _record()
    record["target_index"] = 0
    item = serialize_as_of_target(record)
    assert len(item["messages"]) == 1
    assert item["messages"][0]["text"] == "I saw a warning"


@pytest.mark.parametrize("target", [-1, 3, True, "1"])
def test_invalid_target_is_rejected(target: object) -> None:
    record = _record()
    record["target_index"] = target
    with pytest.raises(ValueError):
        serialize_as_of_target(record)


def test_pre_target_message_from_future_is_rejected() -> None:
    record = _record()
    record["messages"][0]["offset_ms"] = 500
    with pytest.raises(ValueError, match="after target"):
        serialize_as_of_target(record)


def test_untrusted_metadata_is_rejected_not_serialized() -> None:
    record = _record()
    record["channel_profile"] = None
    with pytest.raises(ValueError, match="static scope"):
        serialize_as_of_target(record)


def test_future_message_metadata_is_not_forwarded() -> None:
    record = _record()
    record["messages"][1]["model_answer"] = "FUTURE_ONLY_ANSWER"
    record["messages"][0]["moderation_outcome"] = "FUTURE_ONLY_ANSWER"
    item = serialize_as_of_target(record)
    assert "FUTURE_ONLY_ANSWER" not in json.dumps(item)
