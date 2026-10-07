"""Argument parser construction for the W25 experiment runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from workers.w25.attacks import ATTACK_FAMILIES
from workers.w25.config import MODEL_SPECS, SERIALIZATION_VARIANTS


def build_parser() -> argparse.ArgumentParser:
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


