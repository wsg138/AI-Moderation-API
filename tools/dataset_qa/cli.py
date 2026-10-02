from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyze import analyze_records
from .config import load_config
from .model import DatasetResult
from .report import build_report, render_markdown_report
from .validate import load_and_validate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.dataset_qa")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "report"):
        command = subparsers.add_parser(name)
        command.add_argument("path", type=Path)
        command.add_argument("--range", default="auto", help="auto, none, or PREFIX:start-end")
        command.add_argument("--config", type=Path)
    validate = subparsers.choices["validate"]
    validate.add_argument("--format", choices=("text", "json"), default="text")
    report = subparsers.choices["report"]
    report.add_argument("--format", choices=("json", "markdown"), default="markdown")
    report.add_argument("--output", type=Path)
    return parser


def _run(path: Path, config_path: Path | None, range_spec: str) -> DatasetResult:
    config = load_config(config_path)
    result = load_and_validate(path, config, range_spec)
    return analyze_records(result, config)


def _diagnostics_text(result: DatasetResult) -> str:
    lines = []
    for item in result.diagnostics:
        location = f"{item.path}:{item.line}" if item.line is not None else item.path
        lines.append(f"{location}: {item.severity} {item.code}: {item.message}")
    lines.append(
        f"summary: records={len(result.records)} errors={len(result.errors())} "
        f"warnings={len(result.warnings())} "
        f"exact_duplicate_groups={len(result.exact_duplicate_groups)} "
        f"near_candidates={len(result.near_duplicate_candidates)}"
    )
    return "\n".join(lines)


def _validate_command(args: argparse.Namespace) -> int:
    result = _run(args.path, args.config, args.range)
    if args.format == "json":
        payload = {
            "diagnostics": [item.to_dict() for item in result.diagnostics],
            "summary": build_report(result)["diagnostics"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(_diagnostics_text(result))
    return 1 if result.errors() else 0


def _report_command(args: argparse.Namespace) -> int:
    result = _run(args.path, args.config, args.range)
    report = build_report(result)
    content = (
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if args.format == "json"
        else render_markdown_report(report)
    )
    if args.output is None:
        print(content, end="")
    else:
        args.output.write_text(content, encoding="utf-8")
    return 1 if result.errors() else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "validate":
        return _validate_command(args)
    return _report_command(args)
