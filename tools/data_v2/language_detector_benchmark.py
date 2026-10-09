"""Aggregate-only offline evaluation of *externally supplied* language predictions.

Does not implement/invoke a language detector, read production chat, or enable
blocking. Requires independently human-reviewed private benchmark records.
Never prints texts, IDs, filenames, or case-by-case actions.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from tools.dataset_qa.blind_review import _outside_checkout

from .language_rule_probe import ASSESSMENTS, RULE_PATH, evaluate_rule, load_rule

FIELDS = frozenset({
    "case_id", "review_provenance", "human_reviewed",
    "channel_profile", "human_expected_action", "detector_assessment",
})
EXPECTED = frozenset({"ALLOW", "BLOCK"})


def _require(condition: bool, explanation: str) -> None:
    if not condition:
        raise ValueError(explanation)


def _record(row: object, included: set[str]) -> dict[str, Any]:
    _require(isinstance(row, dict) and set(row) == FIELDS,
             "unexpected private benchmark fields")
    _require(isinstance(row["case_id"], str) and
             row["case_id"].startswith("private-eval-"), "invalid private case ID")
    _require(row["review_provenance"] == "independent_human_review",
             "independent human label provenance required")
    _require(row["human_reviewed"] is True, "unreviewed expected result")
    _require(row["channel_profile"] in included, "evaluation scope not moderated")
    _require(row["human_expected_action"] in EXPECTED, "invalid human expected action")
    _require(row["detector_assessment"] in ASSESSMENTS | {"unavailable"},
             "invalid detector assessment")
    return row


def _count(counts: Counter[str], expected: str, observed: str) -> None:
    counts["total"] += 1
    counts[f"expected_{expected}"] += 1
    counts[f"observed_{observed}"] += 1
    if observed == "ABSTAIN":
        counts["abstained"] += 1
    elif expected == "ALLOW" and observed == "BLOCK":
        counts["false_blocks"] += 1
    elif expected == "BLOCK" and observed == "ALLOW":
        counts["false_allows"] += 1
    else:
        counts["correct_decisions"] += 1


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _summary(counts: Counter[str]) -> dict[str, object]:
    return {
        "reviewed_private_cases": counts["total"],
        "expected_allow": counts["expected_ALLOW"],
        "expected_block": counts["expected_BLOCK"],
        "false_blocks": counts["false_blocks"],
        "false_block_rate_expected_allow": _rate(
            counts["false_blocks"], counts["expected_ALLOW"]),
        "false_allows": counts["false_allows"],
        "false_allow_rate_expected_block": _rate(
            counts["false_allows"], counts["expected_BLOCK"]),
        "abstentions": counts["abstained"],
        "abstention_rate": _rate(counts["abstained"], counts["total"]),
        "correct_non_abstaining_decisions": counts["correct_decisions"],
        "independent_source_verified_by_tool": False,
        "claim_about_model_accuracy": False,
        "training_eligible": False,
        "runtime_enabled": False,
        "automated_release_approval": False,
    }


def evaluate_predictions(path: Path, rule: dict[str, Any]) -> dict[str, object]:
    """Fail closed on incorrect scope, incomplete provenance and duplicate cases."""
    private_path = _outside_checkout(path)
    included = set(rule["runtime_surface_profiles"]["moderated"])
    _require(private_path.is_file(), "private evaluation input unavailable")
    _require(private_path.stat().st_size <= 10_000_000, "private evaluation too large")
    lines = private_path.read_text(encoding="utf-8").splitlines()
    _require(0 < len(lines) <= 25000, "invalid private evaluation count")
    ids: set[str] = set()
    counts: Counter[str] = Counter()
    for line in lines:
        _require(len(line) <= 4096, "private evaluation row too large")
        row = _record(json.loads(line), included)
        _require(row["case_id"] not in ids, "duplicate private evaluation ID")
        ids.add(row["case_id"])
        signal = row["detector_assessment"]
        assessment = None if signal == "unavailable" else signal
        actual = evaluate_rule(rule, row["channel_profile"], assessment)
        _count(counts, row["human_expected_action"], actual)
    return _summary(counts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-predictions", required=True, type=Path)
    parser.add_argument("--rule", default=RULE_PATH, type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate_predictions(args.private_predictions, load_rule(args.rule))
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        print(f"Private offline language evaluation refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
