"""Development candidate diagnostics smoke tests, using invented aggregate records."""
from __future__ import annotations

import pytest

from workers.w25.candidate_diagnostics import (
    _pair_report,
    _slice_result,
    load_registry,
    validate_registry,
)


def _row(expected: str, predicted: str) -> dict:
    return {
        "gold": {"action": expected},
        "predicted": {"action": predicted},
        "head_errors": [] if expected == predicted else ["action"],
        "risk_tags": ["wrongful_blocks"] if expected == "ALLOW" and predicted == "BLOCK" else [],
        "all_supervised_heads_correct": expected == predicted,
    }


def test_registry_is_open_and_unapproved() -> None:
    registry = load_registry()
    ids = {model["id"] for model in registry["experimental_candidates"]}
    assert {"xlm-roberta-base", "byt5-small", "char-tfidf-linear"} <= ids
    assert len(registry["experimental_combinations"]) >= 3
    assert all(item["status"] == "proposal" for item in registry["experimental_candidates"])
    registry["requirements"]["locked_acceptance_never_used_for_selection"] = False
    with pytest.raises(ValueError, match="Acceptance"):
        validate_registry(registry)


def test_disjoint_errors_create_only_hypothetical_oracle_potential() -> None:
    left = {"a": _row("ALLOW", "BLOCK"), "b": _row("ALLOW", "ALLOW")}
    right = {"a": _row("ALLOW", "ALLOW"), "b": _row("ALLOW", "BLOCK")}
    counts = _pair_report(left, right)
    assert counts["left_unique_correct_actions"] == 1
    assert counts["right_unique_correct_actions"] == 1
    assert counts["both_wrong_action"] == 0
    assert counts["action_disagreements"] == 2


def test_sparse_slices_refuse_accuracy_claims() -> None:
    assert _slice_result([_row("ALLOW", "BLOCK")], 20) == {
        "n": 1, "status": "INSUFFICIENT_SUPPORT"
    }
    assert _slice_result([_row("ALLOW", "BLOCK")] * 20, 20)["risk_errors"] == {
        "wrongful_blocks": 20
    }


def test_small_model_slice_does_not_claim_low_false_block_rate() -> None:
    from workers.w25.candidate_diagnostics import _slice_result

    rows = [_row("ALLOW", "ALLOW")] * 19 + [_row("ALLOW", "BLOCK")]
    report = _slice_result(rows, 20)
    assert report["action_matches"] == 19
    assert report["gold_allow_support"] == 20
    assert 0 < report["action_accuracy_wilson_lower95"] < 0.95
    assert report["false_block_fpr_wilson_upper95_per_1000"] is None
