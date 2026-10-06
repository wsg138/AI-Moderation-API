"""Development-only architecture and operating-point selection helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DevelopmentScore:
    name: str
    block_precision: float
    block_recall: float
    critical_recall: float
    macro_f1: float
    ece: float
    p95_ms: float | None = None


def select_deberta_size(scores: list[DevelopmentScore]) -> DevelopmentScore:
    eligible = [
        score
        for score in scores
        if score.name in {"deberta-v3-xsmall", "deberta-v3-small"}
    ]
    if len(eligible) != 2:
        raise ValueError("DeBERTa selection requires xsmall and small development scores")
    return max(eligible, key=_quality_key)


def aggregate_development_scores(
    name: str,
    scores: list[DevelopmentScore],
) -> DevelopmentScore:
    _require_named_scores(name, scores)
    return DevelopmentScore(
        name=name,
        block_precision=_mean_attribute(scores, "block_precision"),
        block_recall=_mean_attribute(scores, "block_recall"),
        critical_recall=_mean_attribute(scores, "critical_recall"),
        macro_f1=_mean_attribute(scores, "macro_f1"),
        ece=_mean_attribute(scores, "ece"),
        p95_ms=_mean_latency(scores),
    )


def _require_named_scores(name: str, scores: list[DevelopmentScore]) -> None:
    if not scores:
        raise ValueError(f"cannot aggregate empty development scores for {name}")
    if any(score.name != name for score in scores):
        raise ValueError(f"cannot aggregate mismatched development scores for {name}")


def _mean_attribute(scores: list[DevelopmentScore], attribute: str) -> float:
    return _mean([float(getattr(score, attribute)) for score in scores])


def _mean_latency(scores: list[DevelopmentScore]) -> float | None:
    values = [score.p95_ms for score in scores if score.p95_ms is not None]
    return _mean(values) if values else None


def select_deberta_seed_aggregate(
    xsmall: list[DevelopmentScore],
    small: list[DevelopmentScore],
) -> DevelopmentScore:
    return select_deberta_size(
        [
            aggregate_development_scores("deberta-v3-xsmall", xsmall),
            aggregate_development_scores("deberta-v3-small", small),
        ]
    )


def select_modernbert_seed_aggregate(
    raw: list[DevelopmentScore],
    normalized: list[DevelopmentScore],
) -> DevelopmentScore:
    scores = [
        aggregate_development_scores("modernbert-raw", raw),
        aggregate_development_scores("modernbert-normalized", normalized),
    ]
    return max(scores, key=_quality_key)


def rank_finalists(scores: list[DevelopmentScore]) -> list[DevelopmentScore]:
    """Development ranking only; frozen-suite winner selection happens later."""
    return sorted(scores, key=_quality_key, reverse=True)


def _quality_key(score: DevelopmentScore) -> tuple[float, ...]:
    latency = score.p95_ms if score.p95_ms is not None else float("inf")
    return (
        score.block_precision,
        score.block_recall,
        score.critical_recall,
        score.macro_f1,
        -score.ece,
        -latency,
    )


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty development score")
    return sum(values) / len(values)
