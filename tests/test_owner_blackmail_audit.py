"""Owner's gameplay-only blackmail choice must not auto-certify G10 labels."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.dataset_qa.owner_blackmail_audit import G10, audit_file, game_only_candidate


def _record(*, irl: bool = False, label: str = "BLACKMAIL") -> dict[str, object]:
    reasons = ["blackmail", "minecraft_gameplay_explicit"]
    if irl:
        reasons.append("explicit_real_world_cue")
    return {
        "source": "synthetic", "label": label, "action": "BLOCK",
        "reason_codes": reasons,
    }


def test_gameplay_cue_only_is_a_review_candidate_not_a_label_edit() -> None:
    record = _record()
    original = json.dumps(record, sort_keys=True)
    assert game_only_candidate(record)
    assert json.dumps(record, sort_keys=True) == original


def test_explicit_real_world_cue_is_not_game_only() -> None:
    assert not game_only_candidate(_record(irl=True))


def test_non_blackmail_and_unflagged_cases_are_not_selected() -> None:
    assert not game_only_candidate(_record(label="SAFE"))
    row = _record()
    row["reason_codes"] = ["blackmail"]
    assert not game_only_candidate(row)


def test_audit_refuses_non_synthetic_input(tmp_path: Path) -> None:
    path = tmp_path / G10
    path.write_text(
        "\n".join(json.dumps({**_record(), "source": "private"}) for _ in range(500)),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="public synthetic"):
        audit_file(path)


def test_audit_fails_closed_on_truncated_batch(tmp_path: Path) -> None:
    path = tmp_path / G10
    path.write_text(json.dumps(_record()), encoding="utf-8")
    with pytest.raises(ValueError, match="500-record"):
        audit_file(path)


def test_audit_produces_counts_without_training_admission(tmp_path: Path) -> None:
    path = tmp_path / G10
    rows = [_record()] * 250 + [_record(irl=True)] * 250
    path.write_bytes(("\n".join(json.dumps(row) for row in rows) + "\n").encode())
    summary = audit_file(path)
    assert summary["records"] == 500
    assert summary["current_blackmail_block_count"] == 500
    assert summary["gameplay_tagged_no_irl_cue_review_candidates"] == 250
    assert summary["training_eligible"] is False
    assert summary["action"] == "review_only_no_auto_relabels"
