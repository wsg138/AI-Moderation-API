"""Propose a versioned next wave without changing any frozen Stage-1 packet.

The inputs are source-pinned public synthetic candidates, not training gold.
Only aggregate diagnostics are printed; no reviewer packet is created.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

from tools.dataset_qa.freshness import ROOT, batch_files, report_for

from .corpus_verification_stage1 import TARGET_QUOTA, _unique_key, outcome_conflicts, stage1
from .synthetic_family_audit import find_groups, load_candidates

FROZEN_WAVE1_SHA256 = (
    "bec3d820706c4b8e42c9e17ce1e8455bb38811d30c25d293c27e12a4f1350407"
)
SEED = b"enthusia-verification-stage2-experimental-v1"
BATCHES = tuple(f"G{i:02d}" for i in range(10, 28))
TIERS = tuple(TARGET_QUOTA)
PER_BATCH = 10


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _rank(row: dict[str, Any]) -> str:
    return hashlib.sha256(SEED + str(row["example_id"]).encode("ascii")).hexdigest()


def _target_counts(available: Counter[str]) -> dict[str, int]:
    """Reallocate slots fairly only when a tier lacks diverse target texts."""
    goals = {tier: min(TARGET_QUOTA[tier], available[tier]) for tier in TIERS}
    while sum(goals.values()) < PER_BATCH:
        choices = [tier for tier in TIERS if goals[tier] < available[tier]]
        _require(bool(choices), "insufficient novel target messages in batch")
        tier = min(choices, key=lambda k: (goals[k] / TARGET_QUOTA[k], TIERS.index(k)))
        goals[tier] += 1
    return goals


def _available_targets(pool: list[dict[str, Any]], used: set[str]) -> int:
    return len({_unique_key(row)[1] for row in pool if _unique_key(row)[1] not in used})


def _fresh_families(pool: list[dict[str, Any]], used: set[str]) -> int:
    return len({_unique_key(row)[0] for row in pool if _unique_key(row)[0] not in used})


def _tier_options(
    by_tier: dict[str, list[dict[str, Any]]],
    families: set[str], targets: set[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Keep one deterministic representative for each target and tier."""
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for tier in TIERS:
        options: dict[str, dict[str, Any]] = {}
        ordered = sorted(by_tier[tier], key=lambda row: (
            _unique_key(row)[0] in families, _rank(row)
        ))
        for row in ordered:
            target = _unique_key(row)[1]
            if target not in targets:
                options.setdefault(target, row)
        result[tier] = options
    return result


def _augment(
    slot: int, slots: list[str], targets_by_tier: dict[str, list[str]],
    assigned: dict[str, int], visited: set[str],
) -> bool:
    """Reassign earlier choices to preserve achievable tier quotas."""
    for target in targets_by_tier[slots[slot]]:
        if target in visited:
            continue
        visited.add(target)
        previous = assigned.get(target)
        if previous is None or _augment(previous, slots, targets_by_tier, assigned, visited):
            assigned[target] = slot
            return True
    return False


def _match_quotas(
    options: dict[str, dict[str, dict[str, Any]]], goals: dict[str, int],
    families: set[str],
) -> list[tuple[str, dict[str, Any]]]:
    """Maximum target-distinct assignment to quota slots, before fallback."""
    counts = Counter(target for tier in TIERS for target in options[tier])
    order = sorted(TIERS, key=lambda tier: (len(options[tier]), TIERS.index(tier)))
    slots = [tier for tier in order for _ in range(goals[tier])]
    ranked = {tier: sorted(options[tier], key=lambda target: (
        counts[target], _unique_key(options[tier][target])[0] in families,
        _rank(options[tier][target]),
    )) for tier in TIERS}
    assignment: dict[str, int] = {}
    for slot in range(len(slots)):
        _augment(slot, slots, ranked, assignment, set())
    return [(slots[slot], options[slots[slot]][target])
            for target, slot in sorted(assignment.items(), key=lambda pair: pair[1])]


def _pick_family_representative(
    rows: list[dict[str, Any]], target: str, used_families: set[str],
) -> dict[str, Any]:
    """Select the most family-diverse row for a matched target."""
    choices = [row for row in rows if _unique_key(row)[1] == target]
    return min(choices, key=lambda row: (
        _unique_key(row)[0] in used_families, _rank(row)
    ))


def _choose_tier(
    pool: list[dict[str, Any]], required: int, chosen: list[str],
    families: set[str], targets: set[str], selected_ids: set[str],
) -> None:
    """Prefer new families; never reuse target text from either wave."""
    for require_new_family in (True, False):
        for row in pool:
            if len(chosen) >= required:
                return
            identifier = str(row["example_id"])
            family, target = _unique_key(row)
            if identifier in selected_ids or target in targets:
                continue
            if require_new_family and family in families:
                continue
            chosen.append(identifier)
            selected_ids.add(identifier)
            families.add(family)
            targets.add(target)


def _fill_remaining(
    by_tier: dict[str, list[dict[str, Any]]], chosen: list[str],
    selected_ids: set[str], families: set[str], targets: set[str],
) -> None:
    for tier in TIERS:
        if len(chosen) >= PER_BATCH:
            break
        extras: list[str] = []
        _choose_tier(sorted(by_tier[tier], key=_rank),
                     PER_BATCH - len(chosen), extras,
                     families, targets, selected_ids)
        chosen.extend(extras)


def _batch_diagnostic(
    by_tier: dict[str, list[dict[str, Any]]],
    chosen_ids: set[str], goals: dict[str, int],
) -> dict[str, dict[str, int]]:
    actual = {
        tier: sum(str(row["example_id"]) in chosen_ids for row in by_tier[tier])
        for tier in TIERS
    }
    return {
        "goals": goals,
        "actual": actual,
        "quota_shortfalls": {tier: max(0, goals[tier] - actual[tier]) for tier in TIERS},
    }


def _greedy_batch(
    by_tier: dict[str, list[dict[str, Any]]], goals: dict[str, int],
    families: set[str], targets: set[str],
) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Keep the original diversity-preferring choice if quotas are met."""
    order = sorted(TIERS, key=lambda tier: (
        _fresh_families(by_tier[tier], families), -goals[tier], TIERS.index(tier)
    ))
    chosen: list[str] = []
    selected_ids: set[str] = set()
    for tier in order:
        subset: list[str] = []
        _choose_tier(sorted(by_tier[tier], key=_rank), goals[tier],
                     subset, families, targets, selected_ids)
        chosen.extend(subset)
    _fill_remaining(by_tier, chosen, selected_ids, families, targets)
    _require(len(chosen) == PER_BATCH, "could not choose ten distinct targets")
    return chosen, _batch_diagnostic(by_tier, selected_ids, goals)


def _matched_batch(
    by_tier: dict[str, list[dict[str, Any]]], goals: dict[str, int],
    families: set[str], targets: set[str],
) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Reroute targets shared between priority tiers to preserve quotas."""
    options = _tier_options(by_tier, families, targets)
    matched = _match_quotas(options, goals, families)
    chosen: list[str] = []
    selected_ids: set[str] = set()
    for tier, assigned in matched:
        _, target = _unique_key(assigned)
        row = _pick_family_representative(by_tier[tier], target, families)
        identifier = str(row["example_id"])
        chosen.append(identifier)
        selected_ids.add(identifier)
        family, target = _unique_key(row)
        families.add(family)
        targets.add(target)
    _fill_remaining(by_tier, chosen, selected_ids, families, targets)
    _require(len(chosen) == PER_BATCH, "could not choose ten distinct targets")
    return chosen, _batch_diagnostic(by_tier, selected_ids, goals)


def _shortfall(report: dict[str, dict[str, int]]) -> int:
    return sum(report["quota_shortfalls"].values())


def _select_batch(
    by_tier: dict[str, list[dict[str, Any]]],
    families: set[str], targets: set[str],
) -> tuple[list[str], dict[str, dict[str, int]]]:
    available = Counter({
        tier: _available_targets(by_tier[tier], targets) for tier in TIERS
    })
    goals = _target_counts(available)
    greedy_families, greedy_targets = set(families), set(targets)
    first, diagnostic = _greedy_batch(by_tier, goals, greedy_families, greedy_targets)
    if _shortfall(diagnostic) == 0:
        families.update(greedy_families)
        targets.update(greedy_targets)
        return first, diagnostic
    matched_families, matched_targets = set(families), set(targets)
    second, matched = _matched_batch(by_tier, goals, matched_families, matched_targets)
    if _shortfall(matched) < _shortfall(diagnostic):
        families.update(matched_families)
        targets.update(matched_targets)
        return second, matched
    families.update(greedy_families)
    targets.update(greedy_targets)
    return first, diagnostic


def _build_pools(
    rows: list[dict[str, Any]], tiers: dict[str, str], previous: list[str],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    seen: set[str] = set()
    old = set(previous)
    by_batch: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {tier: [] for tier in TIERS}
    )
    for row in rows:
        identifier = str(row["example_id"])
        _require(identifier not in seen, "duplicate source ID")
        _require(identifier[:3] in BATCHES and tiers.get(identifier) in TIERS,
                 "unexpected batch or missing tier")
        seen.add(identifier)
        if identifier not in old:
            by_batch[identifier[:3]][tiers[identifier]].append(row)
    _require(seen == set(tiers), "extra or missing tier assignments")
    _require(set(by_batch) == set(BATCHES), "missing source batch")
    return by_batch


def _quota_shortfalls(
    diagnostics: dict[str, dict[str, dict[str, int]]],
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    missing = Counter()
    for diagnostic in diagnostics.values():
        missing.update(diagnostic["quota_shortfalls"])
    affected = {
        batch: diagnostic["quota_shortfalls"]
        for batch, diagnostic in diagnostics.items()
        if any(diagnostic["quota_shortfalls"].values())
    }
    return dict(sorted(missing.items())), affected


def _target_repeat_count(
    new_keys: list[tuple[str, str]], old_keys: list[tuple[str, str]],
) -> int:
    current = [target for _, target in new_keys]
    return len(current) - len(set(current)) + len(
        set(current) & {target for _, target in old_keys}
    )


def _summary(
    rows: list[dict[str, Any]], chosen: list[str], tiers: dict[str, str],
    previous: list[str],
    diagnostics: dict[str, dict[str, dict[str, int]]],
) -> dict[str, object]:
    by_id = {str(row["example_id"]): row for row in rows}
    keys = [_unique_key(by_id[i]) for i in chosen]
    older = [_unique_key(by_id[i]) for i in previous]
    family_set = {family for family, _ in keys}
    repeats = _target_repeat_count(keys, older)
    _require(repeats == 0, "repeated target in reviewed or proposed wave")
    missing, affected = _quota_shortfalls(diagnostics)
    return {
        "version": "experimental_stage2_v1",
        "source_records": len(rows),
        "first_wave_identity_verified": True,
        "first_wave_modified": False,
        "new_cases": len(chosen),
        "batches": len(BATCHES),
        "overlap_with_frozen_wave1_ids": len(set(chosen) & set(previous)),
        "target_repetitions_across_both_waves": repeats,
        "new_wave_declared_family_repetitions": len(keys) - len(family_set),
        "new_wave_families_shared_with_wave1": len(
            family_set & {family for family, _ in older}
        ),
        "priority_counts": dict(sorted(Counter(tiers[i] for i in chosen).items())),
        "unmet_target_quota_slots": missing,
        "batches_with_target_quota_shortfalls": affected,
        "new_wave_selection_sha256": hashlib.sha256(
            ",".join(chosen).encode("ascii")
        ).hexdigest(),
        "review_packets_generated": False,
        "training_eligible": False,
    }


def select_next_wave(
    rows: list[dict[str, Any]], tiers: dict[str, str], previous: list[str],
) -> tuple[list[str], dict[str, object]]:
    """Select ten per batch, excluding every reviewed first-wave source ID."""
    _require(len(previous) == 180 and len(set(previous)) == 180,
             "frozen first wave must contain 180 distinct cases")
    digest = hashlib.sha256(",".join(previous).encode("ascii")).hexdigest()
    _require(digest == FROZEN_WAVE1_SHA256, "frozen first wave identity changed")
    by_id = {str(row["example_id"]): row for row in rows}
    _require(set(previous) <= set(by_id), "first wave missing from corpus")
    families = {_unique_key(by_id[i])[0] for i in previous}
    targets = {_unique_key(by_id[i])[1] for i in previous}
    pools = _build_pools(rows, tiers, previous)
    chosen: list[str] = []
    diagnostics: dict[str, dict[str, dict[str, int]]] = {}
    for batch in BATCHES:
        selection, diagnostic = _select_batch(pools[batch], families, targets)
        chosen.extend(selection)
        diagnostics[batch] = diagnostic
    _require(len(chosen) == 180 and len(set(chosen)) == 180,
             "next wave must contain 180 distinct source IDs")
    _require(not set(previous).intersection(chosen), "reused first-wave ID")
    return chosen, _summary(rows, chosen, tiers, previous, diagnostics)


def main() -> int:
    """Read source-pinned candidates; print no individual case or label."""
    files = batch_files(ROOT, require_complete=True)
    _require(len(files) == len(BATCHES), "expected 18 source batches")
    for path in files:
        report_for(path)
    rows = load_candidates()
    groups = find_groups(rows)
    previous, queue, _ = stage1(rows, groups, {
        path.name[:3]: str(path) for path in files
    })
    conflicts = outcome_conflicts(rows, groups)
    tiers = {
        identifier: TIERS[0] if identifier in conflicts else str(record["triage_priority"])
        for identifier, record in queue.items()
    }
    _, report = select_next_wave(rows, tiers, previous)
    report["source_hashes_verified_at_cli"] = True
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
