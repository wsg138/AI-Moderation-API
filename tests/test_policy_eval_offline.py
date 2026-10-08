"""Tiny invented cases only; do not report these as model performance."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.data_v2.policy_eval_contract import SemanticFacts, resolve
from tools.data_v2.policy_eval_metrics import (
    Decision,
    Example,
    evaluate,
    load_pairs,
)

SAFE = Decision("SAFE", "ALLOW", "NONE", False, "NONE", None, "NONE")
THREAT = Decision("REAL_WORLD_THREAT", "BLOCK", "URGENT", True, "NONE", None, "NONE")
STAFF = Decision("STAFF_TARGETED_ABUSE", "BLOCK", "NONE", True, "NONE", None, "NONE")
CARE = Decision("SELF_HARM_INTENT", "ALLOW", "NORMAL", False, "NONE", None, "SELF_HARM_CHECK")


@pytest.mark.parametrize(
    ("kind", "scope", "channel", "action", "strike", "status"),
    [
        ("blackmail", "game_only", "minecraft_public", "ALLOW", False, "RESOLVED"),
        ("blackmail", "game_only", "minecraft_private", "ALLOW", False, "RESOLVED"),
        ("blackmail", "game_only", "discord_gaming", "ALLOW", False, "RESOLVED"),
        ("blackmail", "game_only", "discord_general", "ALLOW", False, "RESOLVED"),
        ("blackmail", "irl", "minecraft_public", "BLOCK", None, "PARTIAL"),
        ("blackmail", "unclear", "discord_general", "REVIEW", None, "UNRESOLVED"),
        ("threat", "unclear", "minecraft_public", "ALLOW", False, "RESOLVED"),
        ("threat", "irl", "minecraft_public", "BLOCK", None, "PARTIAL"),
        ("threat", "unclear", "discord_general", "BLOCK", False, "PARTIAL"),
        ("directed_death_wish", "game_only", "minecraft_public", "ALLOW", False, "RESOLVED"),
        ("directed_death_wish", "unclear", "minecraft_public", "BLOCK", False, "PARTIAL"),
        ("directed_death_wish", "irl", "discord_general", "BLOCK", True, "PARTIAL"),
        ("directed_self_harm", "irl", "minecraft_private", "BLOCK", True, "PARTIAL"),
        ("staff_abuse", "unclear", "minecraft_public", "BLOCK", True, "PARTIAL"),
        ("self_harm_disclosure", "irl", "minecraft_public", "ALLOW", False, "PARTIAL"),
        ("third_party_concern", "irl", "minecraft_public", "ALLOW", False, "PARTIAL"),
        ("actual_slur", "unclear", "minecraft_public", "BLOCK", True, "PARTIAL"),
        ("slur_reference", "unclear", "minecraft_public", "ALLOW", False, "RESOLVED"),
        ("sexual_minor", "irl", "minecraft_private", "REVIEW", None, "UNRESOLVED"),
        ("grooming", "unclear", "minecraft_private", "REVIEW", None, "UNRESOLVED"),
    ],
)
def test_policy_probes(kind: str, scope: str, channel: str,
                       action: str, strike: bool | None, status: str) -> None:
    facts = SemanticFacts(kind, scope, channel)  # type: ignore[arg-type]
    decision = resolve(facts)
    assert (decision.action, decision.strike, decision.status) == (action, strike, status)


def test_quoted_slur_still_block_and_strike() -> None:
    direct = resolve(SemanticFacts("actual_slur", "unclear", "minecraft_public"))
    quoted = resolve(SemanticFacts("actual_slur", "unclear", "minecraft_public",
                                   quoted_or_reported=True))
    assert direct == quoted
    assert quoted.action == "BLOCK" and quoted.strike is True


def test_reliable_minor_evidence_changes_policy_route() -> None:
    candidate = SemanticFacts("sexual_minor", "irl", "minecraft_private")
    assert resolve(candidate).status == "UNRESOLVED"
    confirmed = resolve(replace(candidate, reliable_minor_evidence=True))
    assert confirmed.action == "BLOCK" and confirmed.strike is True


def test_no_unknown_scope_autofills_blackmail_or_mute_duration() -> None:
    uncertain = resolve(SemanticFacts("blackmail", "unclear", "minecraft_private"))
    serious = resolve(SemanticFacts("blackmail", "irl", "minecraft_private"))
    assert uncertain.action == "REVIEW" and uncertain.containment is None
    assert serious.action == "BLOCK" and serious.containment == "MUTE"
    assert serious.strike is None and serious.unresolved is not None


def test_artificial_metrics_with_wrongful_punishments() -> None:
    rows = [
        Example("toy_1", "minecraft", SAFE, replace(SAFE, action="BLOCK", strike=True)),
        Example("toy_2", "minecraft", SAFE, SAFE),
        Example("toy_3", "threat", THREAT, THREAT),
        Example("toy_4", "staff", STAFF, replace(STAFF, strike=False)),
        Example("toy_5", "care", CARE, replace(CARE, action="REVIEW")),
    ]
    report = evaluate(rows)
    assert report["total"]["n"] == 5
    assert report["total"]["action_accuracy"]["hits"] == 3
    assert report["total"]["full_decision_exact_match"]["hits"] == 2
    assert report["total"]["block_precision"]["hits"] == 2
    assert report["total"]["block_precision"]["n"] == 3
    assert report["total"]["false_blocks_per_1000_benign"]["n"] == 3
    assert report["total"]["false_blocks_per_1000_benign"]["hits"] == 1
    assert report["punishments"]["false_strikes"] == 1
    assert report["punishments"]["incorrect_punishment_field_sets"] == 2
    assert report["total"]["review_abstention_rate"]["hits"] == 1
    assert report["critical"]["GROOMING"]["semantic_recall"]["rate"] is None


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _truth(case_id: str = "toy1") -> dict[str, object]:
    return {
        "case_id": case_id, "slice": "artificial", "truth_source": "independently_adjudicated",
        "policy_version": "v1", "split": "heldout", "decision": vars(SAFE),
    }


def _pred(case_id: str = "toy1") -> dict[str, object]:
    return {"case_id": case_id, "decision": vars(SAFE)}


def test_loader_is_strict_and_matches_ids(tmp_path: Path) -> None:
    truth, pred = tmp_path / "truth.jsonl", tmp_path / "pred.jsonl"
    _write(truth, [_truth()])
    _write(pred, [_pred()])
    assert evaluate(load_pairs(truth, pred))["total"]["action_accuracy"]["hits"] == 1
    _write(pred, [_pred("other")])
    with pytest.raises(ValueError, match="case IDs differ"):
        load_pairs(truth, pred)


def test_candidate_labels_and_extra_text_are_rejected(tmp_path: Path) -> None:
    truth, pred = tmp_path / "truth.jsonl", tmp_path / "pred.jsonl"
    candidate = _truth()
    candidate["truth_source"] = "synthetic_candidate"
    _write(truth, [candidate])
    _write(pred, [_pred()])
    with pytest.raises(ValueError, match="independently adjudicated"):
        load_pairs(truth, pred)
    candidate["truth_source"] = "independently_adjudicated"
    candidate["raw_text"] = "must never be printed"
    _write(truth, [candidate])
    with pytest.raises(ValueError, match="unapproved fields"):
        load_pairs(truth, pred)


def test_duplicate_and_invalid_decision_rejected(tmp_path: Path) -> None:
    truth, pred = tmp_path / "truth.jsonl", tmp_path / "pred.jsonl"
    _write(truth, [_truth(), _truth()])
    _write(pred, [_pred()])
    with pytest.raises(ValueError, match="Duplicate"):
        load_pairs(truth, pred)
    bad = _truth()
    bad["decision"] = dict(vars(SAFE), strike=1)
    _write(truth, [bad])
    with pytest.raises(ValueError, match="strike"):
        load_pairs(truth, pred)


def test_zero_denominator_does_not_become_zero_rate() -> None:
    report = evaluate([Example("toy", "critical", THREAT, THREAT)])
    assert report["total"]["false_blocks_per_1000_benign"]["rate"] is None
    assert report["total"]["block_precision"]["rate"] == 1
    assert report["critical"]["BLACKMAIL"]["required_block_recall"]["n"] == 0


def test_confidence_intervals_cover_endpoints() -> None:
    report = evaluate([Example("toy", "safe", SAFE, SAFE)])
    stat = report["total"]["action_accuracy"]
    assert stat["rate"] == 1.0
    assert 0 < stat["ci95_low"] < stat["ci95_high"] == 1.0

def test_json_duplicate_fields_fail_closed(tmp_path: Path) -> None:
    truth, pred = tmp_path / "truth.jsonl", tmp_path / "pred.jsonl"
    truth.write_text('{"case_id":"toy1","case_id":"other"}\n', encoding="utf-8")
    _write(pred, [_pred()])
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_pairs(truth, pred)


def test_confirmed_minor_grooming_blocks_but_does_not_invent_punishment() -> None:
    facts = SemanticFacts("grooming", "irl", "minecraft_private", reliable_minor_evidence=True)
    decision = resolve(facts)
    assert decision.action == "BLOCK"
    assert decision.review_priority == "URGENT"
    assert decision.strike is None
    assert decision.status == "PARTIAL"


def test_false_mute_count_and_rate_scale() -> None:
    muted = replace(SAFE, containment="MUTE", containment_duration_seconds=60)
    report = evaluate([
        Example("safe1", "minecraft", SAFE, muted),
        Example("safe2", "minecraft", SAFE, SAFE),
    ])
    assert report["punishments"]["false_mutes"] == 1
    assert report["total"]["false_blocks_per_1000_benign"]["rate"] == 0.0


def test_truth_with_undecided_mute_duration_is_not_full_gold(tmp_path: Path) -> None:
    truth, pred = tmp_path / "truth.jsonl", tmp_path / "pred.jsonl"
    candidate = _truth()
    candidate["decision"] = vars(replace(SAFE, containment="MUTE"))
    _write(truth, [candidate])
    _write(pred, [_pred()])
    with pytest.raises(ValueError, match="Unresolved mute duration"):
        load_pairs(truth, pred)



def test_game_only_discord_blackmail_is_allowed_but_real_stakes_never_are() -> None:
    game = resolve(SemanticFacts("blackmail", "game_only", "discord_gaming"))
    real = resolve(SemanticFacts("blackmail", "irl", "discord_gaming"))
    assert game.action == "ALLOW" and game.strike is False
    assert game.review_priority == "NONE" and game.containment == "NONE"
    assert real.action == "BLOCK" and real.review_priority == "URGENT"
    assert real.status == "PARTIAL"
