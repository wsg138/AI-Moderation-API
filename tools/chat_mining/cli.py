from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .ingest import ingest_paths
from .mining import (
    add_reviewed_false_positive_candidates,
    load_scores,
    load_slang_terms,
    mine_candidates,
)
from .review import export_reviewed, review_bucket_counts, write_review_queue
from .splitting import finalize_splits, split_manifest
from .store import MiningStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="W22 privacy-conscious real-chat mining pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_ingest(subparsers)
    _add_split(subparsers)
    _add_scores(subparsers)
    _add_mine(subparsers)
    _add_review(subparsers)
    _add_export(subparsers)
    return parser


def _add_db(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db", type=Path, required=True, help="private local SQLite state database"
    )


def _add_ingest(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "ingest", help="stream raw log files into private redacted state"
    )
    _add_db(parser)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--identity-map", type=Path)
    parser.add_argument("--progress-every", type=int, default=50_000)


def _add_split(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("split", help="freeze leakage-aware partitions before mining")
    _add_db(parser)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--manifest", type=Path, required=True)


def _add_scores(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("load-scores", help="load external model predictions")
    _add_db(parser)
    parser.add_argument("scores", type=Path)


def _add_mine(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("mine", help="mine review candidates from development partition")
    _add_db(parser)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--ordinary-sample", type=int, default=200)
    parser.add_argument("--adjudications", type=Path)
    parser.add_argument("--slang-file", type=Path)


def _add_review(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("review-queue", help="write redacted human-review JSONL")
    _add_db(parser)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-limit", type=int, default=5)
    parser.add_argument("--context-window-ms", type=int, default=120_000)


def _add_export(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("export-reviewed", help="export only completed adjudications")
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)


def _run_ingest(args: argparse.Namespace) -> dict[str, object]:
    with MiningStore(args.db) as store:
        stats = ingest_paths(store, args.inputs, args.identity_map, args.progress_every)
    return {
        "lines": stats.lines,
        "chat": stats.chat,
        "stored": stats.stored,
        "duplicates": stats.duplicates,
        "private_skipped": stats.private_skipped,
    }


def _run_split(args: argparse.Namespace) -> dict[str, object]:
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with MiningStore(args.db) as store:
        result = finalize_splits(store, args.seed)
        manifest = split_manifest(store, args.manifest)
    return {"split": result, "manifest": manifest}


def _run_scores(args: argparse.Namespace) -> dict[str, object]:
    with MiningStore(args.db) as store:
        loaded = load_scores(store, args.scores)
    return {"loaded_scores": loaded}


def _run_mine(args: argparse.Namespace) -> dict[str, object]:
    with MiningStore(args.db) as store:
        slang_terms = load_slang_terms(args.slang_file)
        count = mine_candidates(store, args.seed, args.ordinary_sample, slang_terms)
        reviewed = 0
        if args.adjudications is not None:
            reviewed = add_reviewed_false_positive_candidates(store, args.adjudications)
    return {"candidate_bucket_rows": count + reviewed, "reviewed_false_positive_rows": reviewed}


def _run_review(args: argparse.Namespace) -> dict[str, object]:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with MiningStore(args.db) as store:
        count = write_review_queue(store, args.output, args.context_limit, args.context_window_ms)
    return {"review_records": count, "bucket_counts": review_bucket_counts(args.output)}


def _run_export(args: argparse.Namespace) -> dict[str, object]:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    return {"exported_records": export_reviewed(args.reviews, args.output)}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    runners = {
        "ingest": _run_ingest,
        "split": _run_split,
        "load-scores": _run_scores,
        "mine": _run_mine,
        "review-queue": _run_review,
        "export-reviewed": _run_export,
    }
    result = runners[args.command](args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
