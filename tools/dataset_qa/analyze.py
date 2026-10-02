from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher

from .config import QaConfig
from .model import DatasetResult, Diagnostic, RecordRef
from .normalize import comparison_text, exact_fingerprint, structural_key


def _diag(
    result: DatasetResult,
    record: RecordRef,
    severity: str,
    code: str,
    message: str,
) -> None:
    level = "error" if severity == "error" else "warning"
    result.diagnostics.append(
        Diagnostic(str(result.path), record.line, level, code, message)
    )


def _exact_groups(records: list[RecordRef]) -> list[list[RecordRef]]:
    groups: dict[str, list[RecordRef]] = defaultdict(list)
    for record in records:
        fingerprint = exact_fingerprint(record)
        if fingerprint is not None:
            groups[fingerprint].append(record)
    output = [group for group in groups.values() if len(group) > 1]
    return [sorted(group, key=lambda item: item.example_id) for group in output]


def _reason_set(record: RecordRef) -> tuple[str, ...]:
    values = record.data.get("reason_codes")
    if not isinstance(values, list):
        return ()
    return tuple(sorted(item for item in values if isinstance(item, str)))


def _decision_sets(
    group: list[RecordRef],
) -> tuple[set[object], set[object], set[tuple[str, ...]]]:
    labels = {record.data.get("label") for record in group}
    actions = {record.data.get("action") for record in group}
    reason_sets = {_reason_set(record) for record in group}
    return labels, actions, reason_sets


def _analyze_exact_group(result: DatasetResult, group: list[RecordRef]) -> None:
    ids = [record.example_id for record in group]
    message = f"normalized input duplicates: {', '.join(ids)}"
    for record in group:
        _diag(result, record, "error", "exact_duplicate", message)
    labels, actions, reason_sets = _decision_sets(group)
    joined = ", ".join(ids)
    if len(labels) > 1 or len(actions) > 1:
        message = f"same normalized input has conflicting label/action across {joined}"
        _diag(result, group[0], "error", "exact_contradiction", message)
        return
    if len(reason_sets) > 1:
        message = f"same normalized input has differing reason codes across {joined}"
        _diag(result, group[0], "warning", "reason_code_conflict", message)


def _group_for_near(
    records: list[RecordRef],
) -> dict[tuple[object, ...], list[RecordRef]]:
    groups: dict[tuple[object, ...], list[RecordRef]] = defaultdict(list)
    for record in records:
        key = structural_key(record)
        if key is not None:
            groups[key].append(record)
    return groups


def _similarity(left: RecordRef, right: RecordRef) -> float:
    left_text = comparison_text(left)
    right_text = comparison_text(right)
    if left_text is None or right_text is None:
        return 0.0
    longer = max(len(left_text), len(right_text))
    if longer == 0:
        return 1.0
    if min(len(left_text), len(right_text)) / longer < 0.8:
        return 0.0
    return SequenceMatcher(None, left_text, right_text, autojunk=False).ratio()


def _candidate(
    left: RecordRef,
    right: RecordRef,
    score: float,
) -> dict[str, object]:
    same_label = left.data.get("label") == right.data.get("label")
    same_action = left.data.get("action") == right.data.get("action")
    kind = (
        "near_duplicate_candidate"
        if same_label and same_action
        else "minimal_pair_candidate"
    )
    return {
        "left": left.example_id,
        "right": right.example_id,
        "similarity": round(score, 6),
        "kind": kind,
    }


def _warn_near_conflicts(
    result: DatasetResult,
    config: QaConfig,
    left: RecordRef,
    right: RecordRef,
    candidate: dict[str, object],
    score: float,
) -> None:
    if score < config.near_contradiction_threshold:
        return
    if candidate["kind"] == "minimal_pair_candidate":
        message = f"very-close input differs in label/action from {right.example_id}"
        _diag(result, left, "warning", "near_contradiction_candidate", message)
    if _reason_set(left) != _reason_set(right):
        message = f"very-close input has differing reason codes from {right.example_id}"
        _diag(result, left, "warning", "near_reason_code_conflict", message)


def _near_candidates(
    result: DatasetResult,
    config: QaConfig,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for group in _group_for_near(result.records).values():
        ordered = sorted(group, key=lambda item: item.example_id)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if exact_fingerprint(left) == exact_fingerprint(right):
                    continue
                score = _similarity(left, right)
                if score < config.near_duplicate_threshold:
                    continue
                item = _candidate(left, right, score)
                candidates.append(item)
                _warn_near_conflicts(result, config, left, right, item, score)
    return sorted(
        candidates,
        key=lambda item: (str(item["left"]), str(item["right"])),
    )


def _family_suggestions(
    exact_groups: list[list[str]],
    candidates: list[dict[str, object]],
) -> list[dict[str, object]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for group in exact_groups:
        for item in group[1:]:
            adjacency[group[0]].add(item)
            adjacency[item].add(group[0])
    for candidate in candidates:
        left = str(candidate["left"])
        right = str(candidate["right"])
        adjacency[left].add(right)
        adjacency[right].add(left)
    return _connected_components(adjacency)


def _connected_components(
    adjacency: dict[str, set[str]],
) -> list[dict[str, object]]:
    seen: set[str] = set()
    groups: list[list[str]] = []
    for start in sorted(adjacency):
        if start in seen:
            continue
        stack = [start]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - seen, reverse=True))
        if len(component) > 1:
            groups.append(sorted(component))
    return [
        {
            "suggested_family_id": f"SUGGESTED-{index:04d}",
            "example_ids": group,
        }
        for index, group in enumerate(groups, start=1)
    ]


def analyze_records(result: DatasetResult, config: QaConfig) -> DatasetResult:
    exact_record_groups = _exact_groups(result.records)
    result.exact_duplicate_groups = [
        [record.example_id for record in group]
        for group in exact_record_groups
    ]
    for group in exact_record_groups:
        _analyze_exact_group(result, group)
    result.near_duplicate_candidates = _near_candidates(result, config)
    result.family_suggestions = _family_suggestions(
        result.exact_duplicate_groups,
        result.near_duplicate_candidates,
    )
    result.diagnostics.sort(key=Diagnostic.sort_key)
    return result
