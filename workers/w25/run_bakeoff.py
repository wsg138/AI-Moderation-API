"""Sharded W25 experiment runner.

Development admissions may include hash-pinned private real-chat data. Final
architecture ranking remains gated on the required frozen comparison suites.
"""

from __future__ import annotations

import json
from pathlib import Path

from workers.w25.artifacts import load_bundle, save_bundle, write_report
from workers.w25.calibration import apply_bundle_temperatures, calibrate_bundle
from workers.w25.cascade import (
    CascadeThresholds,
    combine_cascade,
    finalize_cascade,
    fit_cascade_thresholds,
)
from workers.w25.cli import build_parser
from workers.w25.config import MODEL_SPECS
from workers.w25.contract import PredictionBundle
from workers.w25.data import (
    admissions_payload,
    load_development_data,
    verify_all_admissions,
)
from workers.w25.evaluation import evaluate_candidate
from workers.w25.reporting_commands import (
    _aggregate_evidence,
    _attack_report,
    _deberta_select,
    _final_rank,
    _modernbert_select,
    _neural_benchmark,
    _neural_export,
    _onnx_benchmark,
    _suite_examples,
)
from workers.w25.selective import (
    SelectiveThresholds,
    apply_selective_policy,
    fit_selective_thresholds,
)
from workers.w25.suites import load_frozen_suite

OUTPUT_ROOT = Path(__file__).resolve().parent / "artifacts"


def main() -> None:
    parser = build_parser()
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

    from workers.w25.neural import TrainingConfig, predict, train_encoder

    train, dev = _development_data(args)
    result = train_encoder(
        args.model_key,
        train,
        dev,
        TrainingConfig(
            seed=args.seed,
            serialization_variant=args.variant,
            epochs=args.epochs,
            batch_size=args.batch_size,
            max_length=args.max_length,
        ),
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
