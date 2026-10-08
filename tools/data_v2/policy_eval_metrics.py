"""Aggregate-only offline Policy-v1 benchmark for an independently adjudicated truth set.

No model inference, source ingestion, or data admission. Never run on unreviewed
candidate labels or a sealed suite without the suite owner's separate permission.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ACTIONS = frozenset({"ALLOW", "REVIEW", "BLOCK"})
REVIEWS = frozenset({"NONE", "NORMAL", "URGENT"})
CONTAINMENTS = frozenset({"NONE", "MUTE"})
SUPPORTS = frozenset({"NONE", "SELF_HARM_CHECK", "TARGET_SAFETY_CHECK"})
CRITICAL = (
    "REAL_WORLD_THREAT", "SELF_HARM_INSTRUCTION", "SELF_HARM_INTENT",
    "THIRD_PARTY_SELF_HARM_CONCERN", "SLUR_USE", "SEXUAL_MINOR",
    "DOXXING", "BLACKMAIL", "GROOMING", "DANGEROUS_REAL_WORLD_INSTRUCTIONS",
)
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
FIELDS = frozenset({
    "semantic_label", "action", "review_priority", "strike",
    "containment", "containment_duration_seconds", "support_flow",
})
LABELS = frozenset({
    "SAFE", "GAMEPLAY_VIOLENCE", "LOW_LEVEL_HARASSMENT", "SEVERE_HARASSMENT",
    "STAFF_TARGETED_ABUSE", "REAL_WORLD_THREAT", "SELF_HARM_INSTRUCTION",
    "SELF_HARM_INTENT", "THIRD_PARTY_SELF_HARM_CONCERN", "HATE", "SLUR_USE",
    "SEXUAL_CONTENT", "SEXUAL_MINOR", "DOXXING", "BLACKMAIL", "GROOMING",
    "DANGEROUS_REAL_WORLD_INSTRUCTIONS", "AMBIGUOUS_REVIEW",
})
SLICES = frozenset({
    "artificial", "safe", "minecraft", "threat", "staff", "care", "critical",
    "minecraft_gameplay", "minecraft_public", "minecraft_private",
    "discord_general", "discord_gaming", "game_only_blackmail",
    "real_world_threats", "abuse", "slur_quote", "minor_safety",
    "self_harm_support", "doxxing", "blackmail", "grooming",
    "dangerous_instructions", "novel_session", "novel_text", "traffic",
    "prevalence_sample", "hard_negative", "rare_safety",
})
MAX_ROWS = 100_000
MAX_LINE = 16_384


@dataclass(frozen=True)
class Decision:
    semantic_label: str
    action: str
    review_priority: str
    strike: bool
    containment: str
    containment_duration_seconds: int | None
    support_flow: str


@dataclass(frozen=True)
class Example:
    case_id: str
    slice_name: str
    truth: Decision
    predicted: Decision


def _validate_category(raw: dict[str, Any]) -> None:
    label = raw["semantic_label"]
    if not isinstance(label, str) or label not in LABELS:
        raise ValueError("invalid semantic label")


def _validate_action(raw: dict[str, Any]) -> None:
    if (not isinstance(raw["action"], str) or raw["action"] not in ACTIONS
            or not isinstance(raw["review_priority"], str)
            or raw["review_priority"] not in REVIEWS):
        raise ValueError("invalid action/review enum")


def _validate_consequence(raw: dict[str, Any]) -> None:
    if type(raw["strike"]) is not bool:
        raise ValueError("invalid strike")
    if (not isinstance(raw["containment"], str)
            or raw["containment"] not in CONTAINMENTS):
        raise ValueError("invalid containment")
    if not isinstance(raw["support_flow"], str) or raw["support_flow"] not in SUPPORTS:
        raise ValueError("invalid support flow")


def _validate_duration(raw: dict[str, Any]) -> None:
    duration = raw["containment_duration_seconds"]
    if duration is not None and (type(duration) is not int or duration < 1):
        raise ValueError("invalid duration")
    if raw["containment"] == "NONE" and duration is not None:
        raise ValueError("duration without containment")


def _validate_decision(raw: Any) -> Decision:
    if not isinstance(raw, dict) or set(raw) != FIELDS:
        raise ValueError("decision must contain exactly the seven permitted fields")
    _validate_category(raw)
    _validate_action(raw)
    _validate_consequence(raw)
    _validate_duration(raw)
    return Decision(**raw)

def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, entry in pairs:
        if key in value:
            raise ValueError("Repeated JSON field")
        value[key] = entry
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for index, line in enumerate(stream, 1):
            if index > MAX_ROWS or len(line) > MAX_LINE or not line.strip():
                raise ValueError(f"Invalid or oversized row {index}")
            try:
                item = json.loads(line, object_pairs_hook=_strict_json_object)
            except (json.JSONDecodeError, ValueError):
                raise ValueError(f"Invalid JSON at row {index}") from None
            if not isinstance(item, dict):
                raise ValueError(f"Expected object at row {index}")
            rows.append(item)
    if not rows:
        raise ValueError("Empty input is not evaluable")
    return rows


def _check_id(value: Any) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ValueError("Invalid case_id or slice")
    return value


def _complete_truth(decision: Decision) -> Decision:
    if decision.containment == "MUTE" and decision.containment_duration_seconds is None:
        raise ValueError("Unresolved mute duration cannot be full-decision truth")
    return decision


def _truth_rows(path: Path) -> dict[str, tuple[str, Decision]]:
    rows: dict[str, tuple[str, Decision]] = {}
    for item in _load_jsonl(path):
        if set(item) != {"case_id", "slice", "truth_source", "policy_version", "split", "decision"}:
            raise ValueError("Truth row has missing or unapproved fields")
        if (item["truth_source"] != "independently_adjudicated"
                or item["split"] != "heldout" or item["policy_version"] != "v1"):
            raise ValueError("Truth must be independently adjudicated Policy-v1 heldout")
        key, slice_name = _check_id(item["case_id"]), _check_id(item["slice"])
        if slice_name not in SLICES:
            raise ValueError("Slice must use the approved non-identifying taxonomy")
        if key in rows:
            raise ValueError("Duplicate truth case_id")
        rows[key] = (slice_name, _complete_truth(_validate_decision(item["decision"])))
    return rows


def _prediction_rows(path: Path) -> dict[str, Decision]:
    rows: dict[str, Decision] = {}
    for item in _load_jsonl(path):
        if set(item) != {"case_id", "decision"}:
            raise ValueError("Prediction row has missing or unapproved fields")
        key = _check_id(item["case_id"])
        if key in rows:
            raise ValueError("Duplicate prediction case_id")
        rows[key] = _validate_decision(item["decision"])
    return rows


def load_pairs(truth_path: Path, prediction_path: Path) -> list[Example]:
    truth = _truth_rows(truth_path)
    predicted = _prediction_rows(prediction_path)
    if truth.keys() != predicted.keys():
        raise ValueError("Truth and prediction case IDs differ (no partial scoring)")
    return [Example(key, group, expected, predicted[key])
            for key, (group, expected) in truth.items()]


def _rate(hits: int, total: int, scale: float = 1.0) -> dict[str, float | int | None]:
    if total == 0:
        return {"hits": hits, "n": total, "rate": None, "ci95_low": None, "ci95_high": None}
    z = 1.959963984540054
    p = hits / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    half /= denominator
    return {"hits": hits, "n": total, "rate": scale * p,
            "ci95_low": scale * max(0.0, center - half),
            "ci95_high": scale * min(1.0, center + half)}


def _count(rows: list[Example], predicate: Any) -> int:
    return sum(1 for item in rows if predicate(item))


def _core_metrics(rows: list[Example]) -> dict[str, Any]:
    benign = [item for item in rows if item.truth.action == "ALLOW"]
    true_block = [item for item in rows if item.truth.action == "BLOCK"]
    predicted_block = [item for item in rows if item.predicted.action == "BLOCK"]
    result: dict[str, Any] = {
        "n": len(rows),
        "action_accuracy": _rate(
            _count(rows, lambda x: x.truth.action == x.predicted.action), len(rows)
        ),
        "semantic_accuracy": _rate(
            _count(rows, lambda x: x.truth.semantic_label == x.predicted.semantic_label), len(rows)
        ),
        "full_decision_exact_match": _rate(
            _count(rows, lambda x: x.truth == x.predicted), len(rows)
        ),
        "block_precision": _rate(
            _count(predicted_block, lambda x: x.truth.action == "BLOCK"), len(predicted_block)
        ),
        "block_recall": _rate(
            _count(true_block, lambda x: x.predicted.action == "BLOCK"), len(true_block)
        ),
        "false_blocks_per_1000_benign": _rate(
            _count(benign, lambda x: x.predicted.action == "BLOCK"), len(benign), 1000
        ),
        "review_abstention_rate": _rate(
            _count(rows, lambda x: x.predicted.action == "REVIEW"), len(rows)
        ),
    }
    return result


def _punishment_key(value: Decision) -> tuple[bool, str, int | None]:
    return value.strike, value.containment, value.containment_duration_seconds


def _punishment_metrics(rows: list[Example]) -> dict[str, int]:
    return {
        "false_strikes": _count(
            rows, lambda x: x.predicted.strike and not x.truth.strike
        ),
        "false_mutes": _count(
            rows, lambda x: x.predicted.containment == "MUTE" and x.truth.containment != "MUTE"
        ),
        "incorrect_punishment_field_sets": _count(
            rows, lambda x: _punishment_key(x.truth) != _punishment_key(x.predicted),
        ),
    }


def _category_recall(rows: list[Example]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label in CRITICAL:
        matching = [x for x in rows if x.truth.semantic_label == label]
        result[label] = {
            "semantic_recall": _rate(
                sum(x.predicted.semantic_label == label for x in matching), len(matching)
            ),
            "required_block_recall": _rate(
                _count(
                    matching,
                    lambda x: x.truth.action == "BLOCK" and x.predicted.action == "BLOCK",
                ),
                _count(matching, lambda x: x.truth.action == "BLOCK"),
            ),
        }
    return result


def _action_confusion(rows: list[Example]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for actual in sorted(ACTIONS):
        counts = Counter(x.predicted.action for x in rows if x.truth.action == actual)
        result[actual] = dict(sorted(counts.items()))
    return result


def _slice_metrics(rows: list[Example]) -> dict[str, Any]:
    slices = sorted({item.slice_name for item in rows})
    if len(slices) > 128:
        raise ValueError("Too many distinct slices")
    return {
        group: _core_metrics([x for x in rows if x.slice_name == group])
        for group in slices
    }


def evaluate(rows: list[Example]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Cannot evaluate zero cases")
    return {
        "schema_version": "policy-eval-offline/1",
        "performance_claim": "unverified_provenance; not a model acceptance certificate",
        "truth_requirements": "independently_adjudicated+heldout+policy_v1; metadata is not proof",
        "total": _core_metrics(rows),
        "punishments": _punishment_metrics(rows),
        "action_confusion": _action_confusion(rows),
        "critical": _category_recall(rows),
        "slices": _slice_metrics(rows),
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Offline, adjudicated-only aggregate evaluation")
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(load_pairs(args.truth, args.predictions))
    except (ValueError, OSError) as exc:
        parser.error(f"Cannot score provided inputs: {type(exc).__name__}")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
