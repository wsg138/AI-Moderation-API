"""Offline-only two-cohort evidence gate; NEVER authorizes live moderation.

All labels, predictions, and evidence files remain private/offline. Metadata
assertions require external verification; this tool does not certify lineage.
Neither W20 nor W27 may be evaluated without their separate owner's consent.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tools.data_v2.policy_eval_metrics import evaluate, load_pairs

SCHEMA = "prospective-accuracy-evidence/1"
REQUIRED_ASSERTIONS = (
    "candidate_frozen_before_both_cohorts",
    "natural_prospective_never_scored",
    "challenge_fresh_and_predeclared",
    "sessions_and_families_disjoint_from_training",
    "cohorts_disjoint_from_each_other",
    "independently_double_adjudicated",
    "reviewers_blind_to_model_predictions",
    "neither_cohort_used_for_tuning",
    "privacy_and_source_rights_verified",
    "natural_sample_preserves_actual_prevalence",
)
CRITICAL_LABELS = (
    "REAL_WORLD_THREAT",
    "SELF_HARM_INSTRUCTION",
    "SLUR_USE",
    "SEXUAL_MINOR",
    "DOXXING",
    "GROOMING",
)
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _stat(report: dict[str, Any], name: str) -> dict[str, Any]:
    return report["total"][name]


def _bound(
    report: dict[str, Any], key: str, field: str, threshold: float,
    *, at_least: bool,
) -> bool:
    value = _stat(report, key).get(field)
    return isinstance(value, (float, int)) and (
        value >= threshold if at_least else value <= threshold
    )


def _digest_blockers(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ("model_sha256", "natural_cohort_sha256", "challenge_cohort_sha256"):
        value = meta.get(key)
        if not isinstance(value, str) or not HEX_SHA.fullmatch(value):
            issues.append("invalid_digest_" + key)
    if meta.get("natural_cohort_sha256") == meta.get("challenge_cohort_sha256"):
        issues.append("cohort_digests_not_distinct")
    return issues


def _size_blockers(meta: dict[str, Any], natural_n: int, challenge_n: int) -> list[str]:
    issues: list[str] = []
    if type(meta.get("natural_cases")) is not int or meta["natural_cases"] != natural_n:
        issues.append("natural_cohort_size_mismatch")
    if type(meta.get("challenge_cases")) is not int or meta["challenge_cases"] != challenge_n:
        issues.append("challenge_cohort_size_mismatch")
    return issues


def _assertion_blockers(meta: dict[str, Any]) -> list[str]:
    issues = ["unverified_" + key for key in REQUIRED_ASSERTIONS if meta.get(key) is not True]
    reference = meta.get("independent_audit_reference")
    if not isinstance(reference, str) or not reference.strip():
        issues.append("missing_independent_audit_reference")
    return issues


def _manifest_blockers(
    meta: dict[str, Any], natural_n: int, challenge_n: int,
) -> list[str]:
    issues = ["invalid_attestation_schema"] if meta.get("schema_version") != SCHEMA else []
    return (
        issues + _digest_blockers(meta)
        + _size_blockers(meta, natural_n, challenge_n)
        + _assertion_blockers(meta)
    )

def _natural_blockers(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report["total"]["n"] < 1000:
        failures.append("natural_sample_under_1000")
    if _stat(report, "false_blocks_per_1000_benign")["n"] < 3500:
        failures.append("benign_support_under_3500")
    for metric in ("full_decision_exact_match", "action_accuracy"):
        if not _bound(report, metric, "ci95_low", 0.99, at_least=True):
            failures.append(metric + "_lower95_below_99pct")
    if not _bound(report, "false_blocks_per_1000_benign",
                  "ci95_high", 1.0, at_least=False):
        failures.append("false_blocks_upper95_over_one_per_1000_benign")
    return failures


def _critical_blockers(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for label in CRITICAL_LABELS:
        rate = report["critical"][label]["required_block_recall"]
        if rate["n"] < 80:
            failures.append("critical_" + label + "_support_under_80")
        if rate["ci95_low"] is None or rate["ci95_low"] < 0.95:
            failures.append("critical_" + label + "_block_recall_lower95_below_95pct")
    return failures


def _challenge_blockers(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for metric in ("block_recall", "block_precision"):
        if _stat(report, metric)["n"] < 100:
            failures.append(metric + "_support_under_100")
    if not _bound(report, "block_recall", "ci95_low", 0.95, at_least=True):
        failures.append("block_recall_lower95_below_95pct")
    if not _bound(report, "block_precision", "ci95_low", 0.99, at_least=True):
        failures.append("block_precision_lower95_below_99pct")
    return failures + _critical_blockers(report)

def _punishment_blockers(report: dict[str, Any], cohort: str) -> list[str]:
    return [
        cohort + "_false_" + name
        for name in ("strikes", "mutes")
        if report["punishments"]["false_" + name] != 0
    ]


def assess(
    natural: dict[str, Any], challenge: dict[str, Any], metadata: dict[str, Any],
) -> dict[str, Any]:
    """Return a conservative informational result, never a go-live authorization."""
    if natural.get("schema_version") != "policy-eval-offline/1":
        raise ValueError("Unsupported natural cohort metrics")
    if challenge.get("schema_version") != "policy-eval-offline/1":
        raise ValueError("Unsupported challenge cohort metrics")
    if not isinstance(metadata, dict):
        raise ValueError("Evidence attestation must be an object")
    blockers = (
        _manifest_blockers(metadata, natural["total"]["n"], challenge["total"]["n"])
        + _natural_blockers(natural)
        + _challenge_blockers(challenge)
        + _punishment_blockers(natural, "natural")
        + _punishment_blockers(challenge, "challenge")
    )
    return {
        "schema_version": SCHEMA,
        "result": "NOT_ESTABLISHED" if blockers else "PROVISIONAL_EVIDENCE_THRESHOLDS_MET",
        "not_a_deployment_authorization": True,
        "never_authorizes_automatic_punishments": True,
        "attestation_is_self_declared_and_requires_independent_verification": True,
        "blockers": sorted(set(blockers)),
        "natural_n": natural["total"]["n"],
        "challenge_n": challenge["total"]["n"],
        "natural_whole_decision_lower95": _stat(
            natural, "full_decision_exact_match")["ci95_low"],
        "natural_false_blocks_per_1000_upper95": _stat(
            natural, "false_blocks_per_1000_benign")["ci95_high"],
        "challenge_block_recall_lower95": _stat(
            challenge, "block_recall")["ci95_low"],
        "challenge_block_precision_lower95": _stat(
            challenge, "block_precision")["ci95_low"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline 99%-claim evidence preflight")
    for name in ("natural_truth", "natural_predictions", "challenge_truth",
                 "challenge_predictions", "attestation"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    try:
        natural = evaluate(load_pairs(args.natural_truth, args.natural_predictions))
        challenge = evaluate(load_pairs(args.challenge_truth, args.challenge_predictions))
        meta = json.loads(args.attestation.read_text(encoding="utf-8"))
        result = assess(natural, challenge, meta)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error("Offline evidence cannot be evaluated: " + type(exc).__name__)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
