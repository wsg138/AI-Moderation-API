"""Predeclared validation-only selection rules for W23."""

from __future__ import annotations

from workers.w23.config import (
    AUTO_PUNISHMENT_PRECISION_FLOOR,
    BLOCK_RECALL_RATIO_FLOOR,
    BLOCK_SLICE_FPR_TOLERANCE,
    IMPORTANT_BENIGN_SLICES,
    STRIKE_RECALL_RATIO_FLOOR,
)


def _slice_guard(candidate: dict, baseline: dict) -> bool:
    candidate_slices = candidate["important_benign_slices"]
    baseline_slices = baseline["important_benign_slices"]
    for name in IMPORTANT_BENIGN_SLICES:
        candidate_rate = candidate_slices[name]["false_positive_rate"]
        baseline_rate = baseline_slices[name]["false_positive_rate"]
        if candidate_rate is None or baseline_rate is None:
            continue
        if candidate_rate > baseline_rate + BLOCK_SLICE_FPR_TOLERANCE:
            return False
    return True


def select_precision_text_candidate(
    candidates: list[dict],
    baseline_decision: dict,
) -> dict:
    recall_floor = baseline_decision["recall"] * BLOCK_RECALL_RATIO_FLOOR
    eligible = [
        item
        for item in candidates
        if item["decision"]["recall"] >= recall_floor
        and _slice_guard(item["decision"], baseline_decision)
    ]
    fallback = False
    if not eligible:
        eligible = [item for item in candidates if item["decision"]["recall"] >= recall_floor]
        fallback = True
    if not eligible:
        eligible = list(candidates)
        fallback = True
    chosen = max(
        eligible,
        key=lambda item: (
            item["decision"]["precision"],
            item["semantic_macro_f1"],
            item["decision"]["recall"],
        ),
    )
    return {
        "candidate": chosen["name"],
        "recall_floor": recall_floor,
        "slice_guard_applied": not fallback,
        "selection_order": "BLOCK precision, semantic macro-F1, BLOCK recall",
    }


def select_screening_rule(rule_reports: list[dict]) -> dict:
    chosen = max(
        rule_reports,
        key=lambda item: (item["recall"], item["precision"], item["f1"]),
    )
    return {
        "rule": chosen["name"],
        "selection_order": "BLOCK recall, then precision, then F1",
    }


def select_block_rule(rule_reports: list[dict], baseline: dict) -> dict:
    recall_floor = baseline["recall"] * BLOCK_RECALL_RATIO_FLOOR
    eligible = [
        item
        for item in rule_reports
        if item["recall"] >= recall_floor and _slice_guard(item, baseline)
    ]
    fallback = False
    if not eligible:
        eligible = [item for item in rule_reports if item["recall"] >= recall_floor]
        fallback = True
    if not eligible:
        eligible = list(rule_reports)
        fallback = True
    chosen = max(eligible, key=lambda item: (item["precision"], item["recall"], item["f1"]))
    return {
        "rule": chosen["name"],
        "recall_floor": recall_floor,
        "slice_guard_applied": not fallback,
        "selection_order": "BLOCK precision, then recall, then F1",
    }


def select_strike_rule(rule_reports: list[dict], baseline: dict) -> dict:
    recall_floor = baseline["recall"] * STRIKE_RECALL_RATIO_FLOOR
    eligible = [item for item in rule_reports if item["recall"] >= recall_floor]
    fallback = False
    if not eligible:
        eligible = list(rule_reports)
        fallback = True
    chosen = max(eligible, key=lambda item: (item["precision"], item["recall"], item["f1"]))
    return {
        "rule": chosen["name"],
        "recall_floor": recall_floor,
        "fallback": fallback,
        "selection_order": "STRIKE precision, then recall, then F1",
    }


def select_hypothetical_auto_rule(rule_reports: list[dict]) -> dict:
    eligible = [
        item
        for item in rule_reports
        if item["precision"] >= AUTO_PUNISHMENT_PRECISION_FLOOR and item["tp"] > 0
    ]
    if not eligible:
        best = max(rule_reports, key=lambda item: (item["precision"], item["recall"]))
        return {
            "enabled": False,
            "reason": "No validation operating point reached the predeclared precision floor.",
            "best_observed_rule": best["name"],
            "best_observed_precision": best["precision"],
        }
    chosen = max(eligible, key=lambda item: (item["recall"], item["precision"]))
    return {
        "enabled": False,
        "hypothetical_rule": chosen["name"],
        "precision_floor": AUTO_PUNISHMENT_PRECISION_FLOOR,
        "precision": chosen["precision"],
        "recall": chosen["recall"],
        "reason": "Development calculation only; automatic punishment remains disabled.",
    }
