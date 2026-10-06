"""Sharded W25 experiment runner.

Development admissions may include hash-pinned private real-chat data. Final
architecture ranking remains gated on the required frozen comparison suites.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workers.w25.adversarial_benchmark import adversarial_bundle_report
from workers.w25.artifacts import load_bundle, save_bundle, write_report
from workers.w25.attacks import ATTACK_FAMILIES, mutate_examples
from workers.w25.calibration import apply_bundle_temperatures, calibrate_bundle
from workers.w25.cascade import (
    CascadeThresholds,
    combine_cascade,
    finalize_cascade,
    fit_cascade_thresholds,
)
from workers.w25.comparison import rank_candidates
from workers.w25.config import MODEL_SPECS, SERIALIZATION_VARIANTS
from workers.w25.contract import PredictionBundle
from workers.w25.data import (
    admissions_payload,
    load_development_data,
    verify_all_admissions,
)
from workers.w25.evaluation import evaluate_candidate
from workers.w25.evidence import aggregate_evidence_manifest
from workers.w25.performance_evidence import benchmark_candidate
from workers.w25.selection import (
    DevelopmentScore,
    select_deberta_seed_aggregate,
    select_modernbert_seed_aggregate,
)
from workers.w25.selective import (
    SelectiveThresholds,
    apply_selective_policy,
    fit_selective_thresholds,
)
from workers.w25.suites import assert_required_suites_ready, load_frozen_suite

OUTPUT_ROOT = Path(__file__).resolve().parent / "artifacts"


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    handlers = {
        "preflight": _preflight,
        "baseline": _baseline,
        "baseline-suite": _baseline_suite,
        "neural": _neural,
        "neural-suite": _neural_suite,
        "lexical": _lexical,
        "lexical-suite": _lexical_suite,
        "fusion": _fusion,
        "fusion-suite": _fusion_suite,
        "cascade": _cascade,
        "cascade-suite": _cascade_suite,
        "deberta-select": _deberta_select,
        "modernbert-select": _modernbert_select,
        "aggregate-evidence": _aggregate_evidence,
        "attack-report": _attack_report,
        "neural-benchmark": _neural_benchmark,
        "onnx-benchmark": _onnx_benchmark,
        "neural-export": _neural_export,
        "final-rank": _final_rank,
    }
    handlers[args.command](args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--require-ready", action="store_true")
    _add_baseline_parser(sub)
    _add_baseline_suite_parser(sub)
    _add_neural_parser(sub)
    _add_neural_suite_parser(sub)
    _add_lexical_parser(sub, "lexical")
    _add_lexical_suite_parser(sub, "lexical-suite")
    _add_lexical_parser(sub, "fusion")
    _add_lexical_suite_parser(sub, "fusion-suite", fusion=True)
    _add_cascade_parser(sub)
    _add_cascade_suite_parser(sub)
    _add_deberta_select_parser(sub)
    _add_modernbert_select_parser(sub)
    _add_aggregate_evidence_parser(sub)
    _add_attack_report_parser(sub)
    _add_neural_benchmark_parser(sub)
    _add_onnx_benchmark_parser(sub)
    _add_neural_export_parser(sub)
    _add_final_rank_parser(sub)
    return parser


def _add_common_data_flag(parser) -> None:
    parser.add_argument(
        "--include-admitted",
        action="store_true",
        help="Require and include reviewed group-frozen W25 admissions.",
    )
    parser.add_argument(
        "--clean-training-only",
        action="store_true",
        help="Development ablation: disable generated train-only attack mutations.",
    )


def _add_baseline_parser(sub) -> None:
    parser = sub.add_parser("baseline")
    parser.add_argument(
        "--candidate",
        choices=("w12-word-tfidf", "w12-bert-mini"),
        required=True,
    )
    parser.add_argument("--checkpoint", type=Path)
    _add_common_data_flag(parser)


def _add_baseline_suite_parser(sub) -> None:
    parser = sub.add_parser("baseline-suite")
    parser.add_argument(
        "--candidate",
        choices=("w12-word-tfidf", "w12-bert-mini"),
        required=True,
    )
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bundle-output", type=Path)
    parser.add_argument("--attack-family", choices=ATTACK_FAMILIES)


def _add_neural_parser(sub) -> None:
    parser = sub.add_parser("neural")
    parser.add_argument("--model-key", choices=tuple(MODEL_SPECS), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--variant", choices=SERIALIZATION_VARIANTS, required=True)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int)
    _add_common_data_flag(parser)


def _add_neural_suite_parser(sub) -> None:
    parser = sub.add_parser("neural-suite")
    parser.add_argument("--model-key", choices=tuple(MODEL_SPECS), required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--variant", choices=SERIALIZATION_VARIANTS, required=True)
    parser.add_argument("--max-length", type=int, required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-bundle-output", type=Path)
    parser.add_argument("--final-bundle-output", type=Path)
    parser.add_argument("--embeddings-output", type=Path)
    parser.add_argument("--attack-family", choices=ATTACK_FAMILIES)


def _add_lexical_parser(sub, name: str) -> None:
    parser = sub.add_parser(name)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--variant", choices=SERIALIZATION_VARIANTS, required=True)
    if name == "fusion":
        parser.add_argument("--train-embeddings", type=Path, required=True)
        parser.add_argument("--dev-embeddings", type=Path, required=True)
    _add_common_data_flag(parser)


def _add_lexical_suite_parser(sub, name: str, *, fusion: bool = False) -> None:
    parser = sub.add_parser(name)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--variant", choices=SERIALIZATION_VARIANTS, required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bundle-output", type=Path)
    parser.add_argument("--attack-family", choices=ATTACK_FAMILIES)
    if fusion:
        parser.add_argument("--train-embeddings", type=Path, required=True)
        parser.add_argument("--suite-embeddings", type=Path, required=True)
    _add_common_data_flag(parser)


def _add_cascade_parser(sub) -> None:
    parser = sub.add_parser("cascade")
    parser.add_argument("--stage-a", type=Path, required=True)
    parser.add_argument("--stage-b", type=Path, required=True)
    parser.add_argument("--name", default="cascade")
    _add_common_data_flag(parser)


def _add_cascade_suite_parser(sub) -> None:
    parser = sub.add_parser("cascade-suite")
    parser.add_argument("--stage-a", type=Path, required=True)
    parser.add_argument("--stage-b", type=Path, required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bundle-output", type=Path)


def _add_deberta_select_parser(sub) -> None:
    parser = sub.add_parser("deberta-select")
    parser.add_argument("--xsmall-report", type=Path, action="append", required=True)
    parser.add_argument("--small-report", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)


def _add_modernbert_select_parser(sub) -> None:
    parser = sub.add_parser("modernbert-select")
    parser.add_argument("--raw-report", type=Path, action="append", required=True)
    parser.add_argument("--normalized-report", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)


def _add_aggregate_evidence_parser(sub) -> None:
    parser = sub.add_parser("aggregate-evidence")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)


def _add_attack_report_parser(sub) -> None:
    parser = sub.add_parser("attack-report")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--clean-bundle", type=Path, required=True)
    parser.add_argument("--attack-bundle", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)


def _add_benchmark_args(parser) -> None:
    parser.add_argument("--suite", default="balanced_policy")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--queue-requests", type=int, default=100)
    parser.add_argument("--timeout-ms", type=float, default=100.0)
    parser.add_argument("--artifact-path", type=Path, action="append")
    parser.add_argument("--output", type=Path, required=True)


def _add_neural_benchmark_parser(sub) -> None:
    parser = sub.add_parser("neural-benchmark")
    parser.add_argument("--model-key", choices=tuple(MODEL_SPECS), required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--variant", choices=SERIALIZATION_VARIANTS, required=True)
    parser.add_argument("--max-length", type=int, required=True)
    _add_benchmark_args(parser)


def _add_onnx_benchmark_parser(sub) -> None:
    parser = sub.add_parser("onnx-benchmark")
    parser.add_argument("--model-key", choices=tuple(MODEL_SPECS), required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--variant", choices=SERIALIZATION_VARIANTS, required=True)
    parser.add_argument("--max-length", type=int, required=True)
    _add_benchmark_args(parser)


def _add_neural_export_parser(sub) -> None:
    parser = sub.add_parser("neural-export")
    parser.add_argument("--model-key", choices=tuple(MODEL_SPECS), required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--variant", choices=SERIALIZATION_VARIANTS, required=True)
    parser.add_argument("--max-length", type=int, required=True)
    parser.add_argument("--suite", default="balanced_policy")
    parser.add_argument("--sample-count", type=int, default=32)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)


def _add_final_rank_parser(sub) -> None:
    parser = sub.add_parser("final-rank")
    parser.add_argument("--evidence", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)


def _preflight(args) -> None:
    payload = admissions_payload()
    ready = payload.get("status") == "ready"
    result = {
        "status": payload.get("status"),
        "admitted_sources": len(payload.get("sources", [])),
        "ready": ready,
    }
    if args.require_ready and not ready:
        raise SystemExit("W25 admissions are not ready")
    if args.require_ready:
        result["verified_sources"] = len(verify_all_admissions())
    print(json.dumps(result, indent=2))


def _baseline(args) -> None:
    from workers.w25.baselines import predict_w12_bert_mini, predict_w12_word_baseline

    _train, dev = _development_data(args)
    if args.candidate == "w12-word-tfidf":
        bundle = predict_w12_word_baseline(dev)
    else:
        if args.checkpoint is None:
            raise SystemExit("--checkpoint is required for w12-bert-mini")
        bundle = predict_w12_bert_mini(dev, args.checkpoint)
    bundle, temperatures = calibrate_bundle(bundle, dev)
    root = OUTPUT_ROOT / args.candidate
    save_bundle(root / "dev-bundle.json", bundle)
    write_report(root / "dev-report.json", evaluate_candidate(dev, bundle))
    write_report(root / "calibration.json", {"temperatures": temperatures})


def _baseline_suite(args) -> None:
    from workers.w25.baselines import predict_w12_bert_mini, predict_w12_word_baseline

    examples = _suite_examples(args)
    if args.candidate == "w12-word-tfidf":
        bundle = predict_w12_word_baseline(examples)
    else:
        if args.checkpoint is None:
            raise SystemExit("--checkpoint is required for w12-bert-mini")
        bundle = predict_w12_bert_mini(examples, args.checkpoint)
    calibrated = apply_bundle_temperatures(
        bundle,
        _load_temperatures(args.calibration),
    )
    if args.bundle_output is not None:
        save_bundle(args.bundle_output, calibrated)
    write_report(args.output, evaluate_candidate(examples, calibrated))


def _neural(args) -> None:
    import numpy as np  # pyright: ignore[reportMissingImports]
    import torch  # pyright: ignore[reportMissingImports]

    from workers.w25.neural import predict, train_encoder

    train, dev = _development_data(args)
    result = train_encoder(
        args.model_key,
        train,
        dev,
        seed=args.seed,
        serialization_variant=args.variant,
        epochs=args.epochs,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
    max_length = min(
        args.max_length or MODEL_SPECS[args.model_key].max_length,
        MODEL_SPECS[args.model_key].max_length,
    )
    train_bundle, _, train_embeddings = predict(
        result.model,
        result.tokenizer,
        train,
        serialization_variant=args.variant,
        max_length=max_length,
    )
    dev_bundle, _, dev_embeddings = predict(
        result.model,
        result.tokenizer,
        dev,
        serialization_variant=args.variant,
        max_length=max_length,
    )
    dev_bundle, temperatures = calibrate_bundle(dev_bundle, dev)
    root = _shard_root(args.model_key, args.seed, args.variant)
    save_bundle(root / "train-bundle.json", train_bundle)
    save_bundle(root / "dev-bundle.json", dev_bundle)
    np.save(root / "train-embeddings.npy", train_embeddings)
    np.save(root / "dev-embeddings.npy", dev_embeddings)
    torch.save(result.model.state_dict(), root / "model-state.pt")
    write_report(root / "calibration.json", {"temperatures": temperatures})
    write_report(root / "history.json", {"history": list(result.history)})
    _write_selective_development(root, dev, dev_bundle)


def _neural_suite(args) -> None:
    import numpy as np  # pyright: ignore[reportMissingImports]

    from workers.w25.neural import load_encoder_checkpoint, predict

    examples = _suite_examples(args)
    model, tokenizer = load_encoder_checkpoint(args.model_key, args.state)
    bundle, _raw, embeddings = predict(
        model,
        tokenizer,
        examples,
        serialization_variant=args.variant,
        max_length=args.max_length,
    )
    calibrated = apply_bundle_temperatures(
        bundle,
        _load_temperatures(args.calibration),
    )
    if args.raw_bundle_output is not None:
        save_bundle(args.raw_bundle_output, calibrated)
    if args.embeddings_output is not None:
        args.embeddings_output.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.embeddings_output, embeddings)
    _evaluate_selective_suite(
        examples,
        calibrated,
        args.thresholds,
        args.output,
        bundle_output=args.final_bundle_output,
    )


def _write_selective_development(root, examples, bundle: PredictionBundle) -> None:
    thresholds = fit_selective_thresholds(examples, bundle)
    selective, abstained = apply_selective_policy(bundle, thresholds)
    save_bundle(root / "dev-selective-bundle.json", selective)
    write_report(
        root / "selective-thresholds.json",
        {
            "thresholds": thresholds.as_dict(),
            "abstained": sum(abstained),
            "total": len(abstained),
        },
    )
    report = evaluate_candidate(examples, selective)
    report["selective"] = {
        "abstained": sum(abstained),
        "coverage": 1.0 - (sum(abstained) / max(len(abstained), 1)),
        "thresholds": thresholds.as_dict(),
    }
    write_report(root / "dev-report.json", report)


def _load_temperatures(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("temperatures")
    if not isinstance(values, dict):
        raise ValueError("calibration file requires temperatures object")
    return {str(key): float(value) for key, value in values.items()}


def _load_selective_thresholds(path: Path) -> SelectiveThresholds:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("thresholds")
    if not isinstance(values, dict):
        raise ValueError("threshold file requires thresholds object")
    return SelectiveThresholds(
        block=float(values["block"]),
        strike=float(values["strike"]),
        containment=float(values["containment"]),
        uncertainty_review=float(values["uncertainty_review"]),
    )


def _lexical(args) -> None:
    from workers.w25.lexical import fit_lexical_fusion, predict_lexical

    train, dev = _development_data(args)
    model = fit_lexical_fusion(
        train,
        serialization_variant=args.variant,
        seed=args.seed,
    )
    bundle = predict_lexical(model, dev)
    bundle, temperatures = calibrate_bundle(bundle, dev)
    root = _shard_root("word-char-tfidf", args.seed, args.variant)
    save_bundle(root / "dev-bundle.json", bundle)
    write_report(root / "calibration.json", {"temperatures": temperatures})
    _write_selective_development(root, dev, bundle)


def _lexical_suite(args) -> None:
    from workers.w25.lexical import fit_lexical_fusion, predict_lexical

    train, _dev = _development_data(args)
    examples = _suite_examples(args)
    model = fit_lexical_fusion(
        train,
        serialization_variant=args.variant,
        seed=args.seed,
    )
    bundle = predict_lexical(model, examples)
    calibrated = apply_bundle_temperatures(
        bundle,
        _load_temperatures(args.calibration),
    )
    _evaluate_selective_suite(
        examples,
        calibrated,
        args.thresholds,
        args.output,
        bundle_output=args.bundle_output,
    )


def _fusion_suite(args) -> None:
    import numpy as np  # pyright: ignore[reportMissingImports]

    from workers.w25.lexical import fit_lexical_fusion, predict_lexical

    train, _dev = _development_data(args)
    examples = _suite_examples(args)
    model = fit_lexical_fusion(
        train,
        serialization_variant=args.variant,
        embeddings=np.load(args.train_embeddings),
        seed=args.seed,
    )
    bundle = predict_lexical(
        model,
        examples,
        embeddings=np.load(args.suite_embeddings),
    )
    calibrated = apply_bundle_temperatures(
        bundle,
        _load_temperatures(args.calibration),
    )
    _evaluate_selective_suite(
        examples,
        calibrated,
        args.thresholds,
        args.output,
        bundle_output=args.bundle_output,
    )


def _evaluate_selective_suite(
    examples,
    calibrated: PredictionBundle,
    thresholds_path: Path,
    output: Path,
    *,
    bundle_output: Path | None = None,
) -> None:
    thresholds = _load_selective_thresholds(thresholds_path)
    selective, abstained = apply_selective_policy(calibrated, thresholds)
    if bundle_output is not None:
        save_bundle(bundle_output, selective)
    report = evaluate_candidate(examples, selective)
    report["selective"] = {
        "abstained": sum(abstained),
        "coverage": 1.0 - (sum(abstained) / max(len(abstained), 1)),
        "thresholds": thresholds.as_dict(),
    }
    write_report(output, report)


def _fusion(args) -> None:
    import numpy as np  # pyright: ignore[reportMissingImports]

    from workers.w25.lexical import fit_lexical_fusion, predict_lexical

    train, dev = _development_data(args)
    train_embeddings = np.load(args.train_embeddings)
    dev_embeddings = np.load(args.dev_embeddings)
    model = fit_lexical_fusion(
        train,
        serialization_variant=args.variant,
        embeddings=train_embeddings,
        seed=args.seed,
    )
    bundle = predict_lexical(model, dev, embeddings=dev_embeddings)
    bundle, temperatures = calibrate_bundle(bundle, dev)
    root = _shard_root("modernbert-lexical-fusion", args.seed, args.variant)
    save_bundle(root / "dev-bundle.json", bundle)
    write_report(root / "calibration.json", {"temperatures": temperatures})
    _write_selective_development(root, dev, bundle)


def _cascade(args) -> None:
    _train, dev = _development_data(args)
    stage_a = load_bundle(args.stage_a)
    stage_b = load_bundle(args.stage_b)
    thresholds = fit_cascade_thresholds(dev, stage_a, stage_b)
    combined, routed = combine_cascade(stage_a, stage_b, thresholds)
    calibrated, temperatures = calibrate_bundle(combined, dev)
    bundle = finalize_cascade(
        calibrated.probabilities,
        stage_a,
        stage_b,
        routed,
        thresholds,
    )
    root = OUTPUT_ROOT / args.name
    save_bundle(root / "dev-bundle.json", bundle)
    report = evaluate_candidate(dev, bundle)
    report["routing"] = {"routed": sum(routed), "total": len(routed)}
    write_report(root / "dev-report.json", report)
    write_report(root / "calibration.json", {"temperatures": temperatures})
    write_report(root / "cascade-thresholds.json", {"thresholds": thresholds.__dict__})


def _cascade_suite(args) -> None:
    examples = load_frozen_suite(args.suite)
    stage_a = load_bundle(args.stage_a)
    stage_b = load_bundle(args.stage_b)
    thresholds = _load_cascade_thresholds(args.thresholds)
    combined, routed = combine_cascade(stage_a, stage_b, thresholds)
    calibrated = apply_bundle_temperatures(
        combined,
        _load_temperatures(args.calibration),
    )
    bundle = finalize_cascade(
        calibrated.probabilities,
        stage_a,
        stage_b,
        routed,
        thresholds,
    )
    report = evaluate_candidate(examples, bundle)
    report["routing"] = {
        "routed": sum(routed),
        "total": len(routed),
        "rate": sum(routed) / max(len(routed), 1),
    }
    report["thresholds"] = thresholds.__dict__
    if args.bundle_output is not None:
        save_bundle(args.bundle_output, bundle)
    write_report(args.output, report)


def _load_cascade_thresholds(path: Path) -> CascadeThresholds:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("thresholds")
    if not isinstance(values, dict):
        raise ValueError("cascade threshold file requires thresholds object")
    return CascadeThresholds(
        screen_block=float(values["screen_block"]),
        screen_strike=float(values["screen_strike"]),
        screen_containment=float(values["screen_containment"]),
        uncertainty=float(values["uncertainty"]),
        block=float(values["block"]),
        strike=float(values["strike"]),
        containment=float(values["containment"]),
    )


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


def _development_data(args):
    return load_development_data(
        include_admitted=bool(args.include_admitted),
        adversarial_augment=not bool(args.clean_training_only),
    )


def _shard_root(candidate: str, seed: int, variant: str) -> Path:
    root = OUTPUT_ROOT / candidate / f"seed-{seed}" / variant.replace("+", "-")
    root.mkdir(parents=True, exist_ok=True)
    return root


if __name__ == "__main__":
    main()
