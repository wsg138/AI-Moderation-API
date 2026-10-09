"""Action-only intake checks locked packets; cannot admit any training gold."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.owner_blind_action_intake import reconcile
from tools.data_v2.synthetic_family_audit import SOURCE_COMMIT
from tools.dataset_qa.asof_input import serialize_as_of_target


def _toy(identifier: str) -> dict[str, Any]:
    return {
        "example_id": identifier,
        "source": "synthetic",
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_public",
        "messages": [
            {"speaker": "A", "offset_ms": 0, "text": f"synthetic message {identifier}"}
        ],
        "target_index": 0,
        "label": "SAFE",
        "action": "ALLOW",
    }


def _fixture() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, Any],
    list[str], dict[str, dict[str, Any]], dict[str, dict[str, object]],
]:
    packets: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    selected: list[str] = []
    source: dict[str, dict[str, Any]] = {}
    queue: dict[str, dict[str, object]] = {}
    for n in range(180):
        identifier = f"G10-{n + 1:04d}"
        pid = f"R-{n + 1:024x}"
        row = _toy(identifier)
        source[identifier] = row
        selected.append(identifier)
        digest = f"{n + 1:064x}"
        queue[identifier] = {"source_sha256": digest, "source_line": n + 1}
        packets.append({"packet_id": pid, **serialize_as_of_target(row)})
        mapping.append({
            "packet_id": pid, "example_id": identifier,
            "source_commit": SOURCE_COMMIT,
            "source_sha256": digest, "source_line": n + 1,
            "candidate_label_for_comparison_only": "SAFE",
            "candidate_action_for_comparison_only": "ALLOW",
            "training_eligible": False,
        })
    decisions = [
        {"packet_id": f"R-{n + 1:024x}",
         "owner_action": "ALLOW" if n < 2 else "REVIEW", "owner_reason": ""}
        for n in range(5)
    ]
    owner = {"type": "blinded_owner_action_review", "training_eligible": False,
             "decisions": decisions}
    return packets, mapping, owner, selected, source, queue


def _run(args: tuple[Any, ...]) -> tuple[list[dict[str, object]], dict[str, object]]:
    return reconcile(*args)


def test_action_only_owner_intake_keeps_training_blocked() -> None:
    rows, summary = _run(_fixture())
    assert len(rows) == 5
    assert summary["actions"] == {"ALLOW": 2, "REVIEW": 3}
    assert summary["disagrees_with_candidate_action"] == 3
    assert summary["owner_review_unresolved"] == 3
    assert summary["opaque_crosswalk_key_authenticated"] is False
    assert all(row["training_eligible"] is False for row in rows)
    assert all(row["semantic_label_verified"] is False for row in rows)
    assert all(row["punishment_fields_verified"] is False for row in rows)


def test_rejects_post_target_or_target_context_tampering() -> None:
    args = list(_fixture())
    args[0][0]["messages"][0]["text"] = "modified after assignment"
    with pytest.raises(ValueError, match="target context"):
        _run(tuple(args))


def test_rejects_changed_source_metadata_or_candidate_label() -> None:
    args = list(_fixture())
    args[1][0]["source_sha256"] = "another hash"
    with pytest.raises(ValueError, match="source digest"):
        _run(tuple(args))
    args = list(_fixture())
    args[1][0]["candidate_label_for_comparison_only"] = "HATE"
    with pytest.raises(ValueError, match="candidate label"):
        _run(tuple(args))


def test_rejects_crosswalk_reordering_or_missing_packet() -> None:
    args = list(_fixture())
    args[1][0], args[1][1] = args[1][1], args[1][0]
    with pytest.raises(ValueError, match="frozen ordered first wave"):
        _run(tuple(args))
    args = list(_fixture())
    args[0].pop()
    with pytest.raises(ValueError, match="exactly the frozen"):
        _run(tuple(args))


def test_rejects_unknown_duplicate_and_unanswered_owner_packets() -> None:
    args = list(_fixture())
    args[2]["decisions"][0]["packet_id"] = "R-" + "f" * 24
    with pytest.raises(ValueError, match="unknown or duplicate"):
        _run(tuple(args))
    args = list(_fixture())
    args[2]["decisions"][1]["packet_id"] = args[2]["decisions"][0]["packet_id"]
    with pytest.raises(ValueError, match="unknown or duplicate"):
        _run(tuple(args))
    args = list(_fixture())
    args[2]["decisions"][0]["owner_action"] = "UNANSWERED"
    with pytest.raises(ValueError, match="unknown owner action"):
        _run(tuple(args))


def test_rejects_attempted_training_gold_or_extra_fields() -> None:
    args = list(_fixture())
    args[2]["training_eligible"] = True
    with pytest.raises(ValueError, match="invalid action-only"):
        _run(tuple(args))
    args = list(_fixture())
    args[2]["decisions"][0]["semantic_label"] = "SAFE"
    with pytest.raises(ValueError, match="invalid owner decision"):
        _run(tuple(args))
    args = list(_fixture())
    args[1][0]["training_eligible"] = True
    with pytest.raises(ValueError, match="training admission"):
        _run(tuple(args))


def test_rejects_crosswalk_packet_id_substitution() -> None:
    args = list(_fixture())
    args[0][0]["packet_id"] = "R-" + "a" * 24
    with pytest.raises(ValueError, match="target context"):
        _run(tuple(args))


def test_does_not_mutate_source_packets_or_crosswalk() -> None:
    args = _fixture()
    snapshot = copy.deepcopy(args)
    _run(args)
    assert args == snapshot


def test_intake_code_within_complexity_limits() -> None:
    assert analyze(Path("tools/data_v2/owner_blind_action_intake.py")) == []
