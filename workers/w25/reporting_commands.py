"""Selection, evidence, benchmark, and export commands for the W25 runner."""

from __future__ import annotations

import json
from pathlib import Path

from workers.w25.adversarial_benchmark import adversarial_bundle_report
from workers.w25.artifacts import write_report
from workers.w25.attacks import ATTACK_FAMILIES, mutate_examples
from workers.w25.comparison import rank_candidates
from workers.w25.config import MODEL_SPECS
from workers.w25.evidence import aggregate_evidence_manifest
from workers.w25.performance_evidence import benchmark_candidate
from workers.w25.selection import (
    DevelopmentScore,
    select_deberta_seed_aggregate,
    select_modernbert_seed_aggregate,
)
from workers.w25.suites import assert_required_suites_ready, load_frozen_suite


def _deberta_select(args) -> None:
    xsmall = [
        _score_from_report("deberta-v3-xsmall", path)
        for path in args.xsmall_report
    ]
    small = [
        _score_from_report("deberta-v3-small", path)
        for path in args.small_report
    ]
    selected = select_deberta_seed_aggregate(xsmall, small)
    write_report(
        args.output,
        {
            "selected": selected.name,
            "aggregate": _score_dict(selected),
            "xsmall_seeds": [_score_dict(score) for score in xsmall],
            "small_seeds": [_score_dict(score) for score in small],
        },
    )


def _modernbert_select(args) -> None:
    raw = [
        _score_from_report("modernbert-raw", path)
        for path in args.raw_report
    ]
    normalized = [
        _score_from_report("modernbert-normalized", path)
        for path in args.normalized_report
    ]
    selected = select_modernbert_seed_aggregate(raw, normalized)
    write_report(
        args.output,
        {
            "selected": selected.name,
            "aggregate": _score_dict(selected),
            "raw_seeds": [_score_dict(score) for score in raw],
            "normalized_seeds": [_score_dict(score) for score in normalized],
        },
    )


def _aggregate_evidence(args) -> None:
    write_report(args.output, aggregate_evidence_manifest(args.manifest))


def _attack_report(args) -> None:
    examples = load_frozen_suite(args.suite)
    attacked = _parse_attack_bundles(args.attack_bundle)
    report = adversarial_bundle_report(
        examples,
        args.clean_bundle,
        attacked,
    )
    write_report(args.output, report)


def _parse_attack_bundles(values: list[str]) -> dict[str, Path]:
    result = {}
    for value in values:
        family, separator, path = value.partition("=")
        if not separator or family not in ATTACK_FAMILIES:
            raise ValueError(f"invalid attack bundle specification: {value}")
        if family in result:
            raise ValueError(f"duplicate attack family: {family}")
        result[family] = Path(path)
    return result


def _suite_examples(args):
    examples = load_frozen_suite(args.suite)
    family = getattr(args, "attack_family", None)
    return mutate_examples(examples, family) if family else examples


def _neural_benchmark(args) -> None:
    from workers.w25.neural import load_encoder_checkpoint, predict

    examples = load_frozen_suite(args.suite)
    sample = [examples[0]]
    model, tokenizer = load_encoder_checkpoint(args.model_key, args.state)

    def operation():
        return predict(
            model,
            tokenizer,
            sample,
            serialization_variant=args.variant,
            max_length=args.max_length,
            batch_size=1,
        )

    def startup():
        return load_encoder_checkpoint(args.model_key, args.state)

    artifacts = _benchmark_artifacts(args, args.state)
    write_report(args.output, _benchmark_payload(operation, startup, artifacts, args))


def _onnx_benchmark(args) -> None:
    from workers.w25.export_onnx import load_onnx_session, predict_onnx_session
    from workers.w25.neural import load_tokenizer

    examples = load_frozen_suite(args.suite)
    sample = [examples[0]]
    tokenizer = load_tokenizer(args.model_key)
    session = load_onnx_session(args.model)

    def operation():
        return predict_onnx_session(
            session,
            tokenizer,
            sample,
            serialization_variant=args.variant,
            max_length=args.max_length,
        )

    def startup():
        return load_onnx_session(args.model)

    artifacts = _benchmark_artifacts(args, args.model)
    write_report(args.output, _benchmark_payload(operation, startup, artifacts, args))


def _benchmark_payload(operation, startup, artifacts: list[Path], args) -> dict[str, object]:
    return benchmark_candidate(
        operation,
        startup,
        artifacts,
        iterations=args.iterations,
        concurrency=args.concurrency,
        queue_requests=args.queue_requests,
        timeout_ms=args.timeout_ms,
    )


def _benchmark_artifacts(args, primary: Path) -> list[Path]:
    extra = list(args.artifact_path or [])
    return [primary, *extra]


def _neural_export(args) -> None:
    from workers.w25.data import serialize_variant
    from workers.w25.export_onnx import (
        artifact_metadata,
        export_encoder_onnx,
        parity_report,
        predict_onnx,
    )
    from workers.w25.neural import load_encoder_checkpoint, predict

    examples = load_frozen_suite(args.suite)[: args.sample_count]
    if not examples:
        raise ValueError("ONNX parity sample is empty")
    model, tokenizer = load_encoder_checkpoint(args.model_key, args.state)
    export_encoder_onnx(
        model,
        tokenizer,
        output_path=args.model_output,
        sample_text=serialize_variant(examples[0].serialized, args.variant),
        max_length=args.max_length,
    )
    reference, _raw, _embeddings = predict(
        model,
        tokenizer,
        examples,
        serialization_variant=args.variant,
        max_length=args.max_length,
    )
    optimized = predict_onnx(
        args.model_output,
        tokenizer,
        examples,
        serialization_variant=args.variant,
        max_length=args.max_length,
    )
    parity = parity_report(reference, optimized)
    report = {
        "model_key": args.model_key,
        "base_revision": MODEL_SPECS[args.model_key].revision,
        "license": MODEL_SPECS[args.model_key].license,
        "serialization_variant": args.variant,
        "sample_count": len(examples),
        "artifact": artifact_metadata(args.model_output),
        "parity": parity,
    }
    write_report(args.report_output, report)
    if not parity["prediction_parity"]:
        raise SystemExit("ONNX export changed one or more W25 head decisions")


def _final_rank(args) -> None:
    assert_required_suites_ready()
    evidence = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.evidence
    ]
    ranked = rank_candidates(evidence)
    write_report(
        args.output,
        {
            "ranking": [
                {
                    "candidate": item.name,
                    "readiness": item.readiness,
                    "real_fpr": item.real_fpr,
                    "real_precision": item.real_precision,
                    "real_recall": item.real_recall,
                    "critical_recall": item.critical_recall,
                    "context_block_recall": item.context_block_recall,
                    "drift_fpr": item.drift_fpr,
                    "drift_recall": item.drift_recall,
                    "balanced_macro_f1": item.balanced_macro_f1,
                    "adversarial_recall": item.adversarial_recall,
                    "seed_flip_rate": item.seed_flip_rate,
                    "block_ece": item.block_ece,
                    "p95_ms": item.p95_ms,
                    "rss_bytes": item.rss_bytes,
                    "deployment_complexity": item.deployment_complexity,
                }
                for item in ranked
            ]
        },
    )


def _score_from_report(name: str, path: Path) -> DevelopmentScore:
    report = json.loads(path.read_text(encoding="utf-8"))
    block = report["consequences"]["block"]
    critical = _critical_recall(report.get("critical_slices", {}))
    return DevelopmentScore(
        name=name,
        block_precision=float(block["precision"]),
        block_recall=float(block["recall"]),
        critical_recall=critical,
        macro_f1=float(report["semantic_label"]["macro_f1"]),
        ece=float(block["calibration"]["ece"]),
    )


def _critical_recall(slices: dict[str, object]) -> float:
    recalls = []
    for payload in slices.values():
        if isinstance(payload, dict) and payload.get("block_recall") is not None:
            recalls.append(float(payload["block_recall"]))
    return min(recalls) if recalls else 0.0


def _score_dict(score: DevelopmentScore) -> dict[str, object]:
    return {
        "name": score.name,
        "block_precision": score.block_precision,
        "block_recall": score.block_recall,
        "critical_recall": score.critical_recall,
        "macro_f1": score.macro_f1,
        "ece": score.ece,
        "p95_ms": score.p95_ms,
    }


