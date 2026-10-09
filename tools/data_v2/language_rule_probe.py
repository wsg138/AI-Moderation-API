"""Offline-only English-primary policy gate; NOT a language detector or runtime hook.

A future independently validated detector may submit a *verified assessment*.
This module maps that assessment and exact API channel profile to owner policy.
It never infers language from message text, scripts, G21 batches, or keywords.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RULE_PATH = Path("policy/english-primary-message-action-v1.json")
PROBES_PATH = Path("data/policy-probes/english-primary-v1.jsonl")
RESULTS = frozenset({"ALLOW", "BLOCK", "ABSTAIN", "SKIP_EXEMPT", "OUT_OF_SCOPE"})
ASSESSMENTS = frozenset({
    "primarily_non_english", "primarily_english",
    "occasional_foreign_words_or_short_greetings",
    "player_names_and_recognized_game_terms",
    "unreliably_assessed_or_ambiguous",
})
NO_PENALTY_KEYS = (
    "strike", "mute", "staff_escalation", "repeat_violation_escalation",
    "other_punishment",
)


def _require(condition: bool, explanation: str) -> None:
    if not condition:
        raise ValueError(explanation)


def load_rule(path: Path = RULE_PATH) -> dict[str, Any]:
    """Refuse an unexpected policy or accidentally enabled live runtime."""
    rule = json.loads(path.read_text(encoding="utf-8"))
    _require(rule["schema_version"] == "enthusia.owner_language_message_action.v1",
             "unexpected language policy version")
    _require(rule["runtime_enabled"] is False, "live runtime not authorized")
    _require(rule["gold_training_eligible"] is False, "synthetic gold not authorized")
    _require(set(rule["message_action_by_verified_assessment"]) == ASSESSMENTS,
             "unexpected language assessment vocabulary")
    _require(rule["message_action_by_verified_assessment"][
        "unreliably_assessed_or_ambiguous"] == "UNDECIDED", "ambiguity must abstain")
    _require(all(rule["language_only_consequences"][k] == "NONE"
                 for k in NO_PENALTY_KEYS), "language-only penalty not authorized")
    _require(rule["language_only_consequences"]["message_action"] == "BLOCK",
             "wrong owner message consequence")
    surface = rule["runtime_surface_profiles"]
    included = surface["moderated"]
    exempt = surface["exempt"]
    _require(set(included) == {
        "minecraft_public", "minecraft_private", "discord_general", "discord_gaming",
    }, "unexpected moderated channel profiles")
    _require(set(exempt) == {
        "discord_staff_exempt", "discord_ticket_exempt", "discord_configured_exempt",
    }, "unexpected exempt channel profiles")
    _require(set(included).isdisjoint(exempt), "overlapping channel profiles")
    _require(surface["out_of_scope_on_unrecognized_profile"] is True,
             "unknown channel must not trigger a block")
    return rule


def evaluate_rule(
    rule: dict[str, Any], channel_profile: str, assessment: str | None,
) -> str:
    """Map a trusted external assessment; never attempt language inference."""
    surface = rule["runtime_surface_profiles"]
    if channel_profile in surface["exempt"]:
        return "SKIP_EXEMPT"
    if channel_profile not in surface["moderated"]:
        return "OUT_OF_SCOPE"
    if assessment not in ASSESSMENTS:
        return "ABSTAIN"
    action = rule["message_action_by_verified_assessment"][assessment]
    if action == "UNDECIDED":
        return "ABSTAIN"
    _require(action in {"ALLOW", "BLOCK"}, "unexpected policy action")
    return str(action)


def language_only_effects(rule: dict[str, Any], action: str) -> dict[str, str]:
    """Explicitly model what language-only policy cannot do."""
    _require(action in RESULTS, "invalid action")
    return {
        "message_action": action,
        "strike": "NONE", "mute": "NONE",
        "staff_escalation": "NONE", "repeat_violation_escalation": "NONE",
        "other_punishment": "NONE",
    }


def validate_probe(row: object) -> dict[str, str]:
    """Accept only tiny developer probes; no private chat payloads."""
    _require(isinstance(row, dict), "invalid probe row")
    _require(set(row) == {
        "probe_id", "channel_profile", "assessment", "expected_action",
    }, "unexpected probe fields, potential private data")
    _require(all(isinstance(value, str) for value in row.values()),
             "invalid probe fields")
    _require(row["probe_id"].startswith("dev-probe-"), "not a developer probe")
    _require(row["expected_action"] in RESULTS, "unknown expected action")
    _require(row["assessment"] in ASSESSMENTS | {"unavailable"},
             "unknown assessment")
    return row


def run_probes(rule: dict[str, Any], path: Path) -> dict[str, object]:
    """Evaluate a finite, deliberately non-gold developer smoke-test matrix."""
    _require(path.resolve().is_relative_to(Path.cwd().resolve()),
             "developer probes must reside inside checkout")
    lines = path.read_text(encoding="utf-8").splitlines()
    _require(0 < len(lines) <= 1000, "invalid developer probe count")
    seen: set[str] = set()
    actual: Counter[str] = Counter()
    for raw in lines:
        row = validate_probe(json.loads(raw))
        _require(row["probe_id"] not in seen, "duplicate probe ID")
        seen.add(row["probe_id"])
        assessment = None if row["assessment"] == "unavailable" else row["assessment"]
        outcome = evaluate_rule(rule, row["channel_profile"], assessment)
        _require(outcome == row["expected_action"], "developer probe failed")
        _require(all(value == "NONE" for key, value in
                     language_only_effects(rule, outcome).items()
                     if key != "message_action"), "unexpected language penalty")
        actual[outcome] += 1
    return {
        "developer_probes_passed": len(seen),
        "outcomes": dict(sorted(actual.items())),
        "language_detector_evaluated": False,
        "independent_holdout_evaluated": False,
        "training_eligible": False,
        "runtime_enabled": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rule", type=Path, default=RULE_PATH)
    parser.add_argument("--probes", type=Path, default=PROBES_PATH)
    args = parser.parse_args(argv)
    try:
        result = run_probes(load_rule(args.rule), args.probes)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print(f"Offline language-rule probes refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
