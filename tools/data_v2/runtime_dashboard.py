"""Offline private HTML dashboard from read-only aggregate moderation evidence.

This tool never loads message text, usernames, raw scores, or decision IDs.
No web service is exposed. An explicit private output path is required.
"""
from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
from typing import Any

from tools.data_v2.runtime_analytics import report

REPO = Path(__file__).resolve().parents[2]
GROUPS = (
    ("per_model_policy", "Model and policy versions"),
    ("per_channel", "Channels"),
    ("per_day", "UTC trend"),
    ("per_semantic_label", "Semantic labels"),
)
COLUMNS = (
    ("finalized", "Decisions"),
    ("blocked", "Blocks"),
    ("review", "Review"),
    ("fail_open", "Fail-open"),
    ("accepted_corrections", "Corrections"),
    ("correction_changed_message_action", "Action changed"),
)
STYLE = """
:root{color-scheme:light dark;font-family:system-ui,Arial,sans-serif}
body{max-width:1200px;margin:2rem auto;padding:0 1rem;line-height:1.5}
h1,h2{line-height:1.2}header p,.notice{color:inherit;opacity:.86}
article{border:1px solid #8893;padding:1rem;border-radius:.75rem;margin:1rem 0}
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{padding:.45rem .65rem;text-align:right;border-bottom:1px solid #8893}
th:first-child,td:first-child{text-align:left}
div.table-wrap{overflow-x:auto}caption{text-align:left;margin:.5rem 0}
p.notice{border-left:4px solid currentColor;padding:.5rem 1rem}
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:.7rem}
.summary div{border:1px solid #8893;border-radius:.5rem;padding:.5rem}
.summary strong{display:block;font-size:1.6rem}
small{font-size:.8rem}
"""


def _cell(value: object) -> str:
    return html.escape(str(value), quote=True)


def _number(value: object) -> int:
    return int(value) if type(value) is int and value >= 0 else 0


def _percentage(count: int, total: int) -> str:
    if not total:
        return "n/a"
    return f"{100 * count / total:.2f}%"


def _metric_card(name: str, count: int, denominator: int) -> str:
    return (
        f"<div><small>{_cell(name)}</small><strong>{count:,}</strong>"
        f"<small>{_percentage(count, denominator)} of persisted FINAL</small></div>"
    )


def _summary(payload: dict[str, Any]) -> str:
    totals = payload["total"]
    population = _number(totals.get("finalized"))
    cards = "".join(
        _metric_card(name, _number(totals.get(field)), population)
        for field, name in COLUMNS
    )
    return f'<article class="summary">{cards}</article>'


def _table_row(name: str, values: dict[str, Any]) -> str:
    cells = "".join(
        f"<td>{_number(values.get(field)):,}</td>"
        for field, _ in COLUMNS
    )
    return f"<tr><th scope='row'>{_cell(name)}</th>{cells}</tr>"


def _table_section(payload: dict[str, Any], field: str, title: str) -> str:
    groups = payload[field]
    heads = "".join(f"<th scope='col'>{_cell(name)}</th>" for _, name in COLUMNS)
    rows = "".join(_table_row(name, values) for name, values in groups.items())
    if not rows:
        return f"<article><h2>{_cell(title)}</h2><p>Insufficient group evidence.</p></article>"
    return (
        f"<article><h2>{_cell(title)}</h2><div class='table-wrap'><table>"
        f"<thead><tr><th scope='col'>Group</th>{heads}</tr></thead>"
        f"<tbody>{rows}</tbody></table></div></article>"
    )


def render(payload: dict[str, Any]) -> str:
    """Render a private, non-interactive, script-free offline dashboard."""
    if payload.get("schema_version") != "private-runtime-aggregates/1":
        raise ValueError("Unsupported aggregate schema")
    start = _cell(payload["date_start_inclusive"])
    end = _cell(payload["date_end_exclusive"])
    sample = payload["latency_ms"]
    latency = (
        f"Latency p50 {_cell(sample['p50'])} ms, "
        f"p95 {_cell(sample['p95'])} ms, p99 {_cell(sample['p99'])} ms."
    )
    sections = "".join(_table_section(payload, key, name) for key, name in GROUPS)
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Enthusia moderation analytics</title><style>{STYLE}</style>"
        "<body><header><h1>Enthusia moderation analytics</h1>"
        f"<p>UTC window: {start} through {end} (exclusive)</p>"
        "<p class='notice'>PRIVATE: local report only. These are persisted "
        "decision counts, not independently adjudicated model accuracy. "
        "Uncorrected decisions are not established correct; client events lost "
        "before API persistence cannot be included.</p></header>"
        f"{_summary(payload)}<p>{latency}</p>{sections}"
        "<p class='notice'>Small reporting groups are suppressed. "
        "No player IDs, raw messages, model prompts or individual case records "
        "are included. Access and retention still require local controls.</p>"
        "</body></html>"
    )


def _private_output(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("Absolute private dashboard output path required")
    destination = path.resolve()
    if REPO == destination or REPO in destination.parents:
        raise ValueError("Dashboard output must remain outside Git")
    if not destination.parent.is_dir():
        raise ValueError("Pre-create the restricted private dashboard directory")
    return destination


def write_dashboard(path: Path, payload: dict[str, Any]) -> Path:
    destination = _private_output(path)
    contents = render(payload).encode("utf-8")
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError("Dashboard already exists; no overwrite permitted") from exc
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(contents)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Private read-only moderation dashboard")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--from-day", required=True)
    parser.add_argument("--until-day", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    values = report(args.database, args.from_day, args.until_day)
    destination = write_dashboard(args.output, values)
    print(f"Private offline dashboard generated: {destination.name}")


if __name__ == "__main__":
    main()
