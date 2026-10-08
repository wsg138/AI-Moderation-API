"""Source-independent regressions for public synthetic context/family leakage."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.synthetic_family_audit import (
    Group,
    _is_near,
    find_groups,
    load_candidates,
    summarize,
)
from tools.dataset_qa.freshness import ROOT, batch_files


def _row(identifier: str, text: str = "tell everyone about my house build") -> dict[str, Any]:
    return {
        "example_id": identifier, "source": "synthetic", "family_id": "g10.base.001",
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "target_index": 1,
        "messages": [
            {"speaker": "A", "offset_ms": 0, "text": "hi there"},
            {"speaker": "B", "offset_ms": 10, "text": text},
        ],
    }


def _has(groups: list[Group], kind: str, *ids: str) -> bool:
    return any(group.kind == kind and set(ids) <= set(group.example_ids) for group in groups)


def test_future_messages_cannot_hide_same_asof_input() -> None:
    left = _row("G10-0001")
    right = deepcopy(left)
    right["example_id"] = "G11-0001"
    left["messages"].append({"speaker": "C", "offset_ms": 20, "text": "allowed"})
    right["messages"].append({"speaker": "C", "offset_ms": 20, "text": "blocked"})
    groups = find_groups([left, right])
    assert _has(groups, "asof_exact", "G10-0001", "G11-0001")
    assert _has(groups, "target_exact", "G10-0001", "G11-0001")


def test_identical_target_in_different_context_is_detected() -> None:
    left = _row("G10-0001")
    right = _row("G25-0001")
    right["family_id"] = "g25.different.001"
    right["messages"][0]["text"] = "different earlier context"
    groups = find_groups([left, right])
    assert _has(groups, "target_exact", "G10-0001", "G25-0001")
    assert not _has(groups, "asof_exact", "G10-0001", "G25-0001")


def test_family_stem_is_heuristic_not_explicit_family() -> None:
    left, right = _row("G10-0001"), _row("G10-0002")
    right["family_id"] = "g10.base.002"
    right["messages"][1]["text"] = "different topic entirely"
    groups = find_groups([left, right])
    assert _has(groups, "family_stem_candidate", "G10-0001", "G10-0002")
    assert not _has(groups, "family_id", "G10-0001", "G10-0002")


def test_token_near_duplicates_ignore_context_shape() -> None:
    first = "please keep these seven diamonds near my secret base coordinates tonight"
    second = "please keep these seven diamonds near my secret base coordinates tomorrow"
    left, right = _row("G10-0001", first), _row("G25-0001", second)
    right["family_id"] = "g25.other.001"
    right["messages"] = [right["messages"][1]]
    right["target_index"] = 0
    groups = find_groups([left, right])
    assert _has(groups, "near_target_candidate", "G10-0001", "G25-0001")


def test_near_threshold_rejects_unrelated_targets() -> None:
    assert not _is_near(
        {"one", "two", "three", "four", "five", "six"},
        {"seven", "eight", "nine", "ten", "eleven", "twelve"},
    )


def test_duplicate_ids_rejected() -> None:
    row = _row("G10-0001")
    with pytest.raises(ValueError, match="duplicate"):
        find_groups([row, deepcopy(row)])


def test_label_changes_do_not_affect_family_evidence() -> None:
    left, right = _row("G10-0001"), _row("G11-0001")
    before = find_groups([left, right])
    right.update({"label": "BLACKMAIL", "action": "BLOCK", "notes": "hidden"})
    assert find_groups([left, right]) == before
    assert summarize([left, right], before)["training_eligible"] is False


def test_real_candidate_corpus_is_source_pinned_and_candidate_only() -> None:
    if not batch_files(ROOT):
        pytest.skip("G10-G27 candidates not present on main")
    rows = load_candidates()
    report = summarize(rows, find_groups(rows))
    assert report["records"] == 9000
    assert report["nonterminal_targets"] == 1584
    assert report["status"] == "candidate"
    assert report["training_eligible"] is False
    assert report["overlap"]["asof_exact"]["groups"] >= 27


def test_changed_source_bytes_fail_closed(tmp_path: Any) -> None:
    for batch in range(10, 28):
        (tmp_path / f"G{batch:02d}-fixture.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed candidate source bytes"):
        load_candidates(tmp_path)


def test_family_modules_follow_complexity_limits() -> None:
    for module in (
        Path("tools/data_v2/synthetic_family_audit.py"),
        Path("tools/data_v2/synthetic_family_preflight.py"),
    ):
        assert analyze(module) == []
