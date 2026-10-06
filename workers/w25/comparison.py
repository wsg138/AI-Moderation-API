"""Evidence validation, ranking, and conservative readiness tiers for W25."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REQUIRED_FINAL_SUITES = (
    "balanced_policy",
    "real_distribution",
    "adversarial_evasion",
    "context",
    "time_based_real_chat",
)


@dataclass(frozen=True)
class CandidateSummary:
    name: str
    real_fpr: float
    real_precision: float
    real_recall: float
    critical_recall: float
    context_block_recall: float
    drift_fpr: float
    drift_recall: float
    balanced_macro_f1: float
    adversarial_recall: float
    seed_flip_rate: float
    block_ece: float
    p95_ms: float
    rss_bytes: int
    deployment_complexity: int
    readiness: str


def rank_candidates(evidence: list[dict[str, Any]]) -> list[CandidateSummary]:
    if not evidence:
        raise ValueError("candidate evidence is empty")
    validate_suite_fingerprints(evidence)
    summaries = [_summarize(item) for item in evidence]
    return sorted(summaries, key=_ranking_key, reverse=True)


def validate_suite_fingerprints(evidence: list[dict[str, Any]]) -> None:
    for suite in REQUIRED_FINAL_SUITES:
        fingerprints = {_suite_fingerprint(item, suite) for item in evidence}
        if None in fingerprints:
            raise ValueError(f"missing required final suite: {suite}")
        if len(fingerprints) != 1:
            raise ValueError(f"candidate suite mismatch for {suite}")


def _summarize(evidence: dict[str, Any]) -> CandidateSummary:
    suites = _mapping(evidence, "suites")
    balanced = _mapping(suites, "balanced_policy")
    real = _mapping(suites, "real_distribution")
    adversarial = _mapping(suites, "adversarial_evasion")
    context = _mapping(suites, "context")
    drift = _mapping(suites, "time_based_real_chat")
    block = _consequence(real, "block")
    drift_block = _consequence(drift, "block")
    stability = _mapping(evidence, "stability")
    performance = _mapping(evidence, "performance")
    return CandidateSummary(
        name=str(evidence["candidate"]),
        real_fpr=float(block["false_positive_rate"]),
        real_precision=float(block["precision"]),
        real_recall=float(block["recall"]),
        critical_recall=_critical_recall(real),
        context_block_recall=float(_consequence(context, "block")["recall"]),
        drift_fpr=float(drift_block["false_positive_rate"]),
        drift_recall=float(drift_block["recall"]),
        balanced_macro_f1=float(_mapping(balanced, "semantic_label")["macro_f1"]),
        adversarial_recall=float(_consequence(adversarial, "block")["recall"]),
        seed_flip_rate=float(stability["prediction_flip_rate"]),
        block_ece=float(_mapping(block, "calibration")["ece"]),
        p95_ms=float(performance["p95_ms"]),
        rss_bytes=int(performance["steady_rss_bytes"]),
        deployment_complexity=int(evidence.get("deployment_complexity", 99)),
        readiness=_readiness(real, drift),
    )


def _ranking_key(summary: CandidateSummary) -> tuple[float, ...]:
    return (
        -summary.real_fpr,
        summary.real_precision,
        summary.real_recall,
        summary.critical_recall,
        -summary.drift_fpr,
        summary.drift_recall,
        summary.context_block_recall,
        summary.balanced_macro_f1,
        summary.adversarial_recall,
        -summary.seed_flip_rate,
        -summary.block_ece,
        -summary.p95_ms,
        -float(summary.rss_bytes),
        -float(summary.deployment_complexity),
    )


def _readiness(
    real_report: dict[str, object],
    drift_report: dict[str, object],
) -> str:
    block_ok = _both_supported(real_report, drift_report, "block", 0.99)
    strike_ok = block_ok and _both_supported(
        real_report, drift_report, "strike", 0.995
    )
    containment_ok = strike_ok and _both_supported(
        real_report, drift_report, "containment", 0.999
    )
    if containment_ok:
        return "CONTAINMENT_CONSIDERATION"
    if strike_ok:
        return "STRIKE_CONSIDERATION"
    if block_ok:
        return "BLOCK_CONSIDERATION"
    return "SHADOW_ONLY"


def _both_supported(
    real_report: dict[str, object],
    drift_report: dict[str, object],
    consequence: str,
    threshold: float,
) -> bool:
    return _precision_supported(
        _consequence(real_report, consequence), threshold
    ) and _precision_supported(
        _consequence(drift_report, consequence), threshold
    )


def _precision_supported(report: dict[str, Any], threshold: float) -> bool:
    observed = float(report["precision"])
    lower = float(report.get("precision_wilson_lower_95", 0.0))
    return observed >= threshold and lower >= threshold


def _critical_recall(report: dict[str, Any]) -> float:
    slices = _mapping(report, "critical_slices")
    recalls = []
    for payload in slices.values():
        if not isinstance(payload, dict):
            continue
        if int(payload.get("n_gold_block", 0)) <= 0:
            continue
        value = payload.get("block_recall")
        if value is not None:
            recalls.append(float(value))
    return min(recalls) if recalls else 0.0


def _consequence(report: dict[str, Any], name: str) -> dict[str, Any]:
    return _mapping(_mapping(report, "consequences"), name)


def _suite_fingerprint(evidence: dict[str, Any], suite: str) -> str | None:
    suites = _mapping(evidence, "suites")
    report = suites.get(suite)
    if not isinstance(report, dict):
        return None
    suite_meta = report.get("suite")
    if not isinstance(suite_meta, dict):
        return None
    value = suite_meta.get("fingerprint")
    return str(value) if value else None


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value
