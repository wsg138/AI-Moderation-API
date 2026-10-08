"""G10 owner's game-only allowance: queue, never automatically admit labels."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from tools.dataset_qa.freshness import ROOT
from tools.dataset_qa.gameplay_blackmail_triage import build_queue, scope_bucket
from tools.dataset_qa.owner_blackmail_audit import G10


def _row(
    text: str, *, number: int = 1, after_target: str | None = None,
) -> dict[str, object]:
    messages = [{"speaker": "A", "offset_ms": 0, "text": text}]
    if after_target is not None:
        messages.append({
            "speaker": "A", "offset_ms": 9999, "text": after_target,
        })
    return {
        "example_id": f"G10-{number:04d}", "source": "synthetic",
        "label": "BLACKMAIL", "action": "BLOCK",
        "reason_codes": ["blackmail", "minecraft_gameplay_explicit"],
        "platform_hint": "minecraft", "channel_profile": "minecraft_public",
        "messages": messages, "target_index": 0,
    }


def test_clear_game_only_candidate_is_not_certified_truth() -> None:
    row = _row("give me diamonds or I reveal your Minecraft base coords")
    assert scope_bucket(row) == "gameplay_scope_confirmation"


def test_real_money_even_when_minecraft_words_appear_is_not_game_only() -> None:
    row = _row("pay $20 real money or I reveal your Minecraft base coords")
    assert scope_bucket(row) == "mixed_or_realworld_risk"


def test_store_rank_purchase_is_not_assumed_free_game_currency() -> None:
    row = _row("gift me VIP from the store or I leak your base coords")
    assert scope_bucket(row) == "mixed_or_realworld_risk"


def test_personal_disclosure_risk_is_prioritized_even_with_diamonds() -> None:
    row = _row("give me 20 diamonds or I leak your private screenshots")
    assert scope_bucket(row) == "mixed_or_realworld_risk"


def test_vague_stakes_are_not_inferred_game_only() -> None:
    row = _row("give me diamonds or I'll tell everyone your secret")
    assert scope_bucket(row) == "insufficient_scope_evidence"


def test_post_target_real_world_words_never_enter_triage() -> None:
    row = _row("give me diamonds or I reveal your base coords",
               after_target="my home address IRL is next")
    assert scope_bucket(row) == "gameplay_scope_confirmation"


def test_queue_preserves_original_and_requires_human_semantic_review() -> None:
    records = [_row("give me diamonds or your base coords go public", number=i)
               for i in range(1, 501)]
    records[1]["reason_codes"] = ["blackmail", "explicit_real_world_cue"]
    records[2]["label"] = "SAFE"
    records[3]["messages"][0]["text"] = "gift me VIP from store or base coords"
    original = json.dumps(records, sort_keys=True)
    raw = ("\n".join(json.dumps(record) for record in records) + "\n").encode()
    manifest, summary = build_queue(raw)
    assert summary["records"] == 500
    assert summary["review_queue_total"] == 498
    assert summary["priority_bucket_counts"] == {
        "gameplay_scope_confirmation": 497,
        "mixed_or_realworld_risk": 1,
    }
    assert len(manifest) == 498
    assert all(row["status"] == "pending_semantic_review" for row in manifest)
    assert all(row["training_eligible"] is False for row in manifest)
    assert summary["training_eligible"] is False
    assert all(len(str(row["source_sha256"])) == 64 for row in manifest)
    assert all("messages" not in row and "gold" not in row for row in manifest)
    assert json.dumps(records, sort_keys=True) == original
    assert manifest[0]["source_line"] == 1


def test_triage_is_independent_of_post_target_notes_and_answer_fields() -> None:
    row = _row("64 diamonds or your base coords go public")
    before = scope_bucket(row)
    changed = deepcopy(row)
    changed["notes"] = "IRL doxxing after the target event"
    changed["label"] = "SAFE"
    changed["messages"].append({
        "speaker": "B", "offset_ms": 1000, "text": "I will leak your phone",
    })
    assert scope_bucket(changed) == before


def test_queue_does_not_auto_change_games_or_real_world_outcomes() -> None:
    records = [_row("16 diamonds or your base coords go public", number=i)
               for i in range(1, 501)]
    records[10]["messages"][0]["text"] = "pay real money or I share your home address"
    raw = ("\n".join(json.dumps(record) for record in records) + "\n").encode()
    manifest, summary = build_queue(raw)
    assert summary["review_queue_total"] == 500
    assert summary["priority_bucket_counts"]["mixed_or_realworld_risk"] == 1
    risk = next(row for row in manifest if row["example_id"] == "G10-0011")
    assert risk["status"] == "pending_semantic_review"
    assert risk["training_eligible"] is False


def test_complete_source_queues_all_341_original_tagged_candidates() -> None:
    source = ROOT / G10
    if not source.exists():
        pytest.skip("G10 not present on this checkout")
    manifest, summary = build_queue(source.read_bytes())
    assert summary["records"] == 500
    assert summary["review_queue_total"] == 341
    assert sum(summary["priority_bucket_counts"].values()) == 341
    assert len({row["example_id"] for row in manifest}) == 341
    assert {row["source_sha256"] for row in manifest} == {
        summary["source_sha256"],
    }
