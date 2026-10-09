"""Experimental next-wave selection is candidate-only and version isolated."""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.corpus_verification_stage1 import outcome_conflicts, stage1
from tools.data_v2.corpus_verification_stage2 import (
    FROZEN_WAVE1_SHA256,
    _greedy_batch,
    _select_batch,
    _target_counts,
    select_next_wave,
)
from tools.data_v2.synthetic_family_audit import find_groups, load_candidates
from tools.dataset_qa.freshness import ROOT, batch_files


def _toy(identifier: str, target: str, family: str) -> dict[str, Any]:
    return {
        "example_id": identifier,
        "family_id": family,
        "messages": [{"speaker": "Player", "offset_ms": 0, "text": target}],
        "target_index": 0,
    }


def _pool() -> dict[str, list[dict[str, Any]]]:
    return {"01_policy_conflict_candidate": [],
            "02_high_impact_candidate": [],
            "03_stratified_audit_candidate": []}


def test_absent_policy_tier_redistributes_slots_evenly() -> None:
    goals = _target_counts(Counter({
        "01_policy_conflict_candidate": 0,
        "02_high_impact_candidate": 15,
        "03_stratified_audit_candidate": 15,
    }))
    assert goals == {
        "01_policy_conflict_candidate": 0,
        "02_high_impact_candidate": 5,
        "03_stratified_audit_candidate": 5,
    }


def test_distinct_target_quota_trumps_duplicate_rows() -> None:
    data = _pool()
    for idx in range(5):
        data["01_policy_conflict_candidate"].append(
            _toy(f"G10-{idx+1:04d}", f"policy {idx}", "same.family")
        )
    for idx in range(12):
        data["02_high_impact_candidate"].append(
            _toy(f"G10-{idx+10:04d}", f"high {idx}", f"high.{idx}")
        )
        data["03_stratified_audit_candidate"].append(
            _toy(f"G10-{idx+30:04d}", f"routine {idx}", f"routine.{idx}")
        )
    data["01_policy_conflict_candidate"].append(
        _toy("G10-0099", "policy 1", "other.family")
    )
    used_targets = {"policy 0"}
    ids, report = _select_batch(data, set(), used_targets)
    chosen = {row["example_id"]: row for group in data.values() for row in group}
    assert len(ids) == len(set(ids)) == 10
    assert len({chosen[i]["messages"][0]["text"] for i in ids}) == 10
    assert report["goals"] == {
        "01_policy_conflict_candidate": 4,
        "02_high_impact_candidate": 3,
        "03_stratified_audit_candidate": 3,
    }
    assert all(value == 0 for value in report["quota_shortfalls"].values())


def test_shared_target_can_move_to_scarce_tier_without_quota_loss() -> None:
    """A greedily taking 'a' would starve B; a matching preserves 4/3/3."""
    data = _pool()
    groups = (
        ("01_policy_conflict_candidate", ("a", "b", "c", "d", "k")),
        ("02_high_impact_candidate", ("a", "e", "i")),
        ("03_stratified_audit_candidate", ("f", "g", "h")),
    )
    counter = 13
    for tier_number, (tier, messages) in enumerate(groups):
        for target in messages:
            identifier = f"G10-{counter:04d}"
            counter += 1
            data[tier].append(_toy(identifier, target, f"family.tier{tier_number}"))
    baseline, before = _greedy_batch(
        data, {"01_policy_conflict_candidate": 4,
               "02_high_impact_candidate": 3,
               "03_stratified_audit_candidate": 3}, set(), set()
    )
    assert len(baseline) == 10
    assert any(before["quota_shortfalls"].values())
    selected, result = _select_batch(data, set(), set())
    indexed = {row["example_id"]: row for rows in data.values() for row in rows}
    assert len(selected) == 10
    assert len({indexed[i]["messages"][0]["text"] for i in selected}) == 10
    assert result["actual"] == {
        "01_policy_conflict_candidate": 4,
        "02_high_impact_candidate": 3,
        "03_stratified_audit_candidate": 3,
    }
    assert not any(result["quota_shortfalls"].values())


def test_absent_tier_batch_does_not_invent_high_risk_examples() -> None:
    data = _pool()
    for idx in range(20):
        data["03_stratified_audit_candidate"].append(
            _toy(f"G18-{idx+1:04d}", f"routine {idx}", f"routine.{idx}")
        )
    ids, report = _select_batch(data, set(), set())
    assert len(ids) == 10
    assert report["actual"]["03_stratified_audit_candidate"] == 10
    assert report["actual"]["01_policy_conflict_candidate"] == 0


def test_refuses_ten_records_with_only_one_unique_target() -> None:
    data = _pool()
    for idx in range(15):
        data["03_stratified_audit_candidate"].append(
            _toy(f"G18-{idx+1:04d}", "one repeated target", f"family.{idx}")
        )
    with pytest.raises(ValueError, match="novel target"):
        _select_batch(data, set(), set())


def test_frozen_prior_wave_cannot_be_substituted() -> None:
    assert len(FROZEN_WAVE1_SHA256) == 64
    with pytest.raises(ValueError, match="identity changed"):
        select_next_wave([], {}, ["G10-0001"] * 0 + [
            f"G10-{i:04d}" for i in range(1, 181)
        ])


def test_full_pinned_source_next_wave_is_distinct_and_nonadmitting() -> None:
    if not batch_files(ROOT):
        pytest.skip("G10-G27 are draft-only, absent on main")
    files = batch_files(ROOT, require_complete=True)
    rows = load_candidates()
    groups = find_groups(rows)
    prior, queue, _ = stage1(
        rows, groups, {path.name[:3]: str(path) for path in files},
    )
    assert hashlib.sha256(",".join(prior).encode("ascii")).hexdigest() == (
        FROZEN_WAVE1_SHA256
    )
    conflicts = outcome_conflicts(rows, groups)
    tiers = {
        identifier: ("01_policy_conflict_candidate" if identifier in conflicts
                     else str(row["triage_priority"]))
        for identifier, row in queue.items()
    }
    new, report = select_next_wave(rows, tiers, prior)
    assert len(new) == len(set(new)) == 180
    assert len(set(new).intersection(prior)) == 0
    assert set(Counter(identifier[:3] for identifier in new).values()) == {10}
    assert report["priority_counts"] == {
        "01_policy_conflict_candidate": 32,
        "02_high_impact_candidate": 62,
        "03_stratified_audit_candidate": 86,
    }
    assert report["batches_with_target_quota_shortfalls"] == {}
    assert report["new_wave_selection_sha256"] == (
        "bdfcd6392a024db3a525b2abed224447936bd4c2fed6381d82e4fd3e3eacbeb1"
    )
    assert report["overlap_with_frozen_wave1_ids"] == 0
    assert report["target_repetitions_across_both_waves"] == 0
    assert report["training_eligible"] is False
    assert report["review_packets_generated"] is False
    assert select_next_wave(rows, tiers, prior)[0] == new


def test_stage2_respects_complexity_limits() -> None:
    assert analyze(Path("tools/data_v2/corpus_verification_stage2.py")) == []
