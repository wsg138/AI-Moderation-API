"""Frozen comparison-suite registry for W25."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workers.w12.dataset import ModerationExample, load_partition
from workers.w25.data import load_source_partition

REGISTRY_PATH = Path(__file__).resolve().parent / "suite_registry.json"


def load_suite_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported W25 suite registry")
    suites = payload.get("suites")
    if not isinstance(suites, dict):
        raise ValueError("suite registry requires suites object")
    return payload


def load_frozen_suite(name: str) -> list[ModerationExample]:
    registry = load_suite_registry()
    suite = _suite_entry(registry, name)
    if suite.get("status") != "ready":
        raise RuntimeError(f"W25 suite is not ready: {name}")
    examples = [
        example
        for source in suite.get("sources", [])
        for example in _load_suite_source(name, source)
    ]
    examples = _apply_suite_selection(examples, suite.get("selection"))
    if not examples:
        raise ValueError(f"ready W25 suite is empty: {name}")
    return examples


def assert_required_suites_ready() -> None:
    registry = load_suite_registry()
    suites = registry["suites"]
    if not isinstance(suites, dict):
        raise ValueError("suite registry requires suites object")
    pending = [
        name
        for name, value in suites.items()
        if isinstance(value, dict)
        and bool(value.get("required"))
        and value.get("status") != "ready"
    ]
    if pending:
        raise RuntimeError(f"required W25 suites are not ready: {sorted(pending)}")


def _suite_entry(registry: dict[str, Any], name: str) -> dict[str, Any]:
    suites = registry["suites"]
    if not isinstance(suites, dict) or name not in suites:
        raise ValueError(f"unknown W25 suite: {name}")
    suite = suites[name]
    if not isinstance(suite, dict):
        raise ValueError(f"invalid W25 suite entry: {name}")
    return suite


def _load_suite_source(
    suite_name: str,
    source: Any,
) -> list[ModerationExample]:
    if not isinstance(source, dict):
        raise ValueError(f"invalid source entry for suite {suite_name}")
    kind = str(source.get("kind", "admitted"))
    partition = str(source["partition"])
    if kind == "w11":
        examples = load_partition(partition)
    elif kind == "admitted":
        examples = load_source_partition(str(source["path"]), partition)
    else:
        raise ValueError(f"unknown W25 suite source kind: {kind}")
    return _apply_filter(examples, source.get("filter"))


def _apply_suite_selection(
    examples: list[ModerationExample],
    selection: Any,
) -> list[ModerationExample]:
    if selection is None:
        return examples
    if not isinstance(selection, dict):
        raise ValueError("W25 suite selection must be an object")
    if selection.get("kind") != "label_cap":
        raise ValueError(f"unknown W25 suite selection: {selection.get('kind')}")
    maximum = int(selection.get("max_per_label", 0))
    if maximum < 1:
        raise ValueError("label_cap max_per_label must be positive")
    return _label_cap(examples, maximum)


def _label_cap(
    examples: list[ModerationExample],
    maximum: int,
) -> list[ModerationExample]:
    counts: dict[str, int] = {}
    selected = []
    for example in sorted(examples, key=lambda item: item.example_id):
        count = counts.get(example.label, 0)
        if count >= maximum:
            continue
        counts[example.label] = count + 1
        selected.append(example)
    return selected


def _apply_filter(
    examples: list[ModerationExample],
    filter_name: Any,
) -> list[ModerationExample]:
    if filter_name is None:
        return examples
    if filter_name == "visible_context":
        return [example for example in examples if example.serialized.count("\n") >= 2]
    raise ValueError(f"unknown W25 suite filter: {filter_name}")
