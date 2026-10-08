"""Deterministic QA report regeneration/freshness gate for candidate G10-G27."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyze import analyze_records
from .config import load_config
from .report import build_report, render_markdown_report
from .validate import load_and_validate

ROOT = Path("data/synthetic")
EXPECTED = {f"G{value:02d}" for value in range(10, 28)}


def report_for(path: Path) -> str:
    """Use exactly the same validation, analysis and rendering as dataset_qa report."""
    config = load_config()
    result = analyze_records(load_and_validate(path, config, "auto"), config)
    errors = result.errors()
    if errors:
        raise ValueError(f"{path}: {len(errors)} dataset QA errors")
    if len(result.records) != 500:
        raise ValueError(f"{path}: expected 500 records, found {len(result.records)}")
    return render_markdown_report(build_report(result))


def batch_files(directory: Path) -> list[Path]:
    files = sorted(directory.glob("G??-*.jsonl"))
    selected = [path for path in files if path.name[:3] in EXPECTED]
    found = {path.name[:3] for path in selected}
    if found and found != EXPECTED:
        raise ValueError(f"incomplete G10-G27 batches: missing {sorted(EXPECTED - found)}")
    return selected


def report_path(path: Path) -> Path:
    return path.with_name(f"{path.name[:3]}-report.md")


def process(directory: Path, write: bool = False) -> tuple[int, int]:
    """Compute every report before mutating anything, and fail on stale output."""
    updates: list[tuple[Path, str]] = []
    for dataset in batch_files(directory):
        rendered = report_for(dataset)
        destination = report_path(dataset)
        current = destination.read_text(encoding="utf-8") if destination.exists() else None
        if current != rendered:
            updates.append((destination, rendered))
    if write:
        for path, content in updates:
            path.write_text(content, encoding="utf-8")
    return len(updates), len(batch_files(directory))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        changed, checked = process(args.directory, args.write)
    except (OSError, ValueError) as exc:
        print(f"Report freshness error: {exc}", file=sys.stderr)
        return 2
    if checked == 0:
        print("G10-G27 absent: no candidate reports to check (main-compatible)")
        return 0
    status = "regenerated" if args.write else "stale"
    print(f"G10-G27: {checked} batches checked, {changed} {status} reports")
    return 0 if args.write or changed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
