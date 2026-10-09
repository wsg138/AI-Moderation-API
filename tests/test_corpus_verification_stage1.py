"""Verification Stage 1: full 9,000-case audit stays candidate-only."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.corpus_verification_stage1 import (
    outcome_conflicts,
    private_review_outputs,
    sample_wave,
    stage1,
)
from tools.data_v2.synthetic_family_audit import Group, find_groups, load_candidates
from tools.dataset_qa.freshness import ROOT, batch_files


def _toy(identifier: str, target: str = "ordinary synthetic chat") -> dict[str, Any]:
    return {
        "example_id": identifier,
        "source": "synthetic",
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_public",
        "messages": [{"speaker": "A", "offset_ms": 0, "text": target}],
        "target_index": 0,
        "label": "SAFE",
        "action": "ALLOW",
        "review_priority": "NONE",
        "strike": False,
        "containment": "NONE",
        "containment_duration_seconds": None,
        "support_flow": "NONE",
        "reason_codes": [],
    }


def test_exact_same_input_different_outcomes_are_review_hypotheses() -> None:
    first = _toy("G10-0001")
    second = _toy("G10-0002")
    second["action"] = "BLOCK"
    second["strike"] = True
    second["reason_codes"] = ["targeted_violence"]
    flags = outcome_conflicts(
        [first, second], [Group("asof_exact", ("G10-0001", "G10-0002"))]
    )
    assert flags["G10-0001"] == {"action", "strike", "reason_codes"}
    assert flags["G10-0002"] == flags["G10-0001"]
    assert first["action"] == "ALLOW"


def test_different_visible_inputs_do_not_auto_create_conflict() -> None:
    rows = [_toy("G10-0001"), _toy("G10-0002", "different sample")]
    assert outcome_conflicts(rows, []) == {}


def test_balanced_sample_per_batch_unique_families_and_targets() -> None:
    records: list[dict[str, Any]] = []
    priorities: dict[str, str] = {}
    for batch in range(10, 28):
        for line in range(1, 16):
            identifier = f"G{batch:02d}-{line:04d}"
            row = _toy(identifier, f"unique message {identifier}")
            row["family_id"] = f"family.{identifier}"
            records.append(row)
            priorities[identifier] = list((
                "01_policy_conflict_candidate", "02_high_impact_candidate",
                "03_stratified_audit_candidate",
            ))[line % 3]
    chosen = sample_wave(records, priorities)
    assert len(chosen) == len(set(chosen)) == 180
    assert set(Counter(identifier[:3] for identifier in chosen).values()) == {10}
    assert sample_wave(records, priorities) == chosen


def test_private_packet_has_no_candidate_answers(tmp_path: Path) -> None:
    source = _toy("G10-0001")
    packet_path = tmp_path / "reviewers" / "blind.jsonl"
    mapping_path = tmp_path / "coordinators" / "source-map.jsonl"
    queue = {"G10-0001": {
        "source_commit": "toy", "source_sha256": "toy_digest",
        "source_line": 1, "candidate_semantic_label": "SAFE",
        "candidate_action": "ALLOW",
    }}
    private_review_outputs(
        ["G10-0001"], [source], queue,
        packet_path, mapping_path, b"not-a-real-review-secret-123",
    )
    blind = json.loads(packet_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert isinstance(blind, dict) and isinstance(mapping, dict)
    assert "example_id" not in blind
    assert "label" not in blind and "action" not in blind
    assert "reason_codes" not in blind and "strike" not in blind
    assert "source_sha256" not in blind
    assert mapping["training_eligible"] is False
    assert mapping["packet_id"] == blind["packet_id"]


def test_review_packet_paths_cannot_point_inside_checkout() -> None:
    with pytest.raises(ValueError, match="inside Git checkout"):
        private_review_outputs(
            [], [], {},
            Path("docs/should-not-write.jsonl"), Path("data/should-not-write.jsonl"),
            b"not-a-real-review-secret-123",
        )


def test_stage1_refuses_duplicate_source_ids() -> None:
    row = _toy("G10-0001")
    with pytest.raises(ValueError):
        stage1([row, row], [], {})


def test_full_source_pinned_9000_candidate_stage1(capsys: Any) -> None:
    if not batch_files(ROOT):
        pytest.skip("G10-G27 are draft-only, absent on main")
    files = batch_files(ROOT, require_complete=True)
    rows = load_candidates()
    selected, _, report = stage1(
        rows, find_groups(rows), {p.name[:3]: str(p) for p in files},
    )
    assert report["records_audited"] == 9000
    assert "all_source_hashes_verified" not in report  # untrusted caller boundary
    assert report["source_batches"] == 18
    assert report["first_blind_review_wave"] == 180
    # Packet review already began: these IDs/order and tier totals are frozen.
    assert report["selected_priority_counts"] == {
        "01_policy_conflict_candidate": 34,
        "02_high_impact_candidate": 72,
        "03_stratified_audit_candidate": 74,
    }
    assert hashlib.sha256(",".join(selected).encode("ascii")).hexdigest() == (
        "bec3d820706c4b8e42c9e17ce1e8455bb38811d30c25d293c27e12a4f1350407"
    )
    assert report["independent_reviews_completed"] == 0
    assert report["semantically_verified_records"] == 0
    assert report["training_eligible"] is False
    assert len(selected) == len(set(selected)) == 180
    assert set(Counter(i[:3] for i in selected).values()) == {10}
    print("STAGE1_AGGREGATE=" + json.dumps(report, sort_keys=True))


def test_cli_attests_only_after_pinned_source_ingestion(capsys: Any) -> None:
    if not batch_files(ROOT):
        pytest.skip("G10-G27 are draft-only, absent on main")
    from tools.data_v2.corpus_verification_stage1 import main

    assert main([]) == 0
    report = json.loads(capsys.readouterr().out.strip())
    assert report["all_source_hashes_verified"] is True
    assert report["records_audited"] == 9000
    assert report["training_eligible"] is False


def test_stage1_code_stays_within_complexity_budget() -> None:
    assert analyze(Path("tools/data_v2/corpus_verification_stage1.py")) == []
