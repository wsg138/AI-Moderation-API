"""Public synthetic candidate triage; no automatic label changes or private data."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .freshness import ROOT, batch_files
from .model import RecordRef
from .normalize import normalize_text, normalized_context

OUTPUT = Path("docs/data-v2/PR52-QA-READINESS.md")
SENSITIVE = {
    "actual_slur", "targeted_violence", "grooming_pattern",
    "self_harm_intent", "blackmail", "apparent_doxxing",
}
GAME = re.compile(r"\b(?:pvp|tnt|respawn|minecraft|nether|creeper|bedwars)\b", re.I)
REAL = re.compile(r"\b(?:irl|in real life|at school|your address|your house)\b", re.I)
DIRECTIVE = re.compile(r"\b(?:kys|kill yourself)\b", re.I)
MINOR = re.compile(r"\b(?:minor|underage|kid|child|1[0-7][ -]?years?[ -]?old)\b", re.I)
DM_PIVOT = re.compile(r"\b(?:check (?:your|ur) dms?|dm me)\b", re.I)


def _context(record: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
    messages = record.get("messages", [])
    index = record.get("target_index", -1)
    target = messages[index].get("text", "") if 0 <= index < len(messages) else ""
    return target, " ".join(m.get("text", "") for m in messages), messages


def _safe_flags(item: dict[str, Any], label: str, action: str) -> set[str]:
    if label != "SAFE":
        return set()
    flags: set[str] = set()
    if action != "ALLOW":
        flags.add("safe_action_disagreement")
    if item.get("strike") or item.get("containment") != "NONE":
        flags.add("safe_with_punishment")
    if set(item.get("reason_codes", [])) & SENSITIVE:
        flags.add("safe_with_severe_reason_code")
    return flags


def _policy_flags(item: dict[str, Any], label: str, action: str) -> set[str]:
    flags = _safe_flags(item, label, action)
    if label == "AMBIGUOUS_REVIEW" and action != "REVIEW":
        flags.add("ambiguous_action_disagreement")
    if label == "SELF_HARM_INTENT" and (action == "BLOCK" or item.get("strike")):
        flags.add("self_harm_disclosure_punished")
    return flags


def _violence_flags(label: str, target: str, context: str) -> set[str]:
    flags: set[str] = set()
    if label == "REAL_WORLD_THREAT" and GAME.search(target) and not REAL.search(context):
        flags.add("real_world_label_with_game_cue")
    if label == "GAMEPLAY_VIOLENCE" and REAL.search(context):
        flags.add("gameplay_label_with_real_cue")
    return flags


def _text_flags(label: str, target: str, context: str) -> set[str]:
    flags = _violence_flags(label, target, context)
    if label == "SAFE" and DIRECTIVE.search(target):
        flags.add("safe_with_self_harm_directive")
    if label == "GROOMING" and not MINOR.search(context):
        flags.add("grooming_without_explicit_minor_cue")
    if DM_PIVOT.fullmatch(target.strip()) and label != "SAFE":
        flags.add("dm_pivot_is_target")
    return flags


def _reason_flags(label: str, reasons: set[str]) -> set[str]:
    flags: set[str] = set()
    if "actual_slur" in reasons and label not in {"HATE", "SLUR_USE"}:
        flags.add("actual_slur_reason_label_disagreement")
    if "staff_targeted_abuse" in reasons and label != "STAFF_TARGETED_ABUSE":
        flags.add("staff_targeted_reason_label_disagreement")
    return flags


def _chronology_flags(item: dict[str, Any], messages: list[dict[str, Any]]) -> set[str]:
    flags: set[str] = set()
    if item.get("target_index") != len(messages) - 1:
        flags.add("nonterminal_target_index_review")
    offsets = [message.get("offset_ms") for message in messages]
    if any(a > b for a, b in zip(offsets, offsets[1:], strict=False)):
        flags.add("nonchronological_message_offsets")
    if len(messages) >= 3 and len({m.get("speaker") for m in messages}) == 1:
        flags.add("single_speaker_multimessage_realism_review")
    return flags


def _flags(item: dict[str, Any]) -> set[str]:
    label, action = item.get("label"), item.get("action")
    target, context, messages = _context(item)
    return (
        _policy_flags(item, label, action)
        | _text_flags(label, target, context)
        | _reason_flags(label, set(item.get("reason_codes", [])))
        | _chronology_flags(item, messages)
    )


def _add_overlap(
    item: dict[str, Any], duplicates: dict[str, list[str]],
    targets: dict[str, list[str]], families: dict[str, list[str]],
) -> None:
    identifier = item["example_id"]
    context = normalized_context(RecordRef(Path("synthetic"), 0, item))
    if context is not None:
        signature = json.dumps(context, sort_keys=True, ensure_ascii=False)
        duplicates[signature].append(identifier)
    target, _, _ = _context(item)
    if len(target) >= 18:
        targets[normalize_text(target)].append(identifier)
    family = item.get("family_id")
    if isinstance(family, str):
        families[family].append(identifier)


def _cross_batch(groups: dict[str, list[str]]) -> list[list[str]]:
    return [
        sorted(set(ids)) for ids in groups.values()
        if len({identifier[:3] for identifier in ids}) > 1
    ]


def _batch_digest_table(files: list[Path]) -> list[str]:
    lines = ["## Final input SHA-256", "", "| Batch | Records | SHA-256 (JSONL bytes) |",
             "|---|---:|---|"]
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"| {path.name[:3]} | 500 | {digest} |")
    return lines


def _scan_files(
    files: list[Path],
) -> tuple[Counter[str], dict[str, list[str]], list[dict[str, list[str]]]]:
    labels: Counter[str] = Counter()
    flags: dict[str, list[str]] = defaultdict(list)
    duplicates: dict[str, list[str]] = defaultdict(list)
    targets: dict[str, list[str]] = defaultdict(list)
    families: dict[str, list[str]] = defaultdict(list)
    for path in files:
        for raw in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(raw)
            labels[item["label"]] += 1
            for rule in _flags(item):
                flags[rule].append(item["example_id"])
            _add_overlap(item, duplicates, targets, families)
    return labels, flags, [duplicates, targets, families]


def _flag_table(flags: dict[str, list[str]]) -> list[str]:
    lines = ["", "## Sanitized review queue", "",
             "| Rule | Count | First 12 synthetic example IDs |",
             "|---|---:|---|"]
    for rule, ids in sorted(flags.items()):
        lines.append(f"| {rule} | {len(ids)} | {', '.join(sorted(ids)[:12])} |")
    return lines


def _overlap_lines(groups: list[dict[str, list[str]]]) -> list[str]:
    lines = ["", "## Cross-batch structural family overlap", ""]
    for name, values in zip((
        "Exact normalized full contexts",
        "Identical target message (18+ chars)",
        "Shared explicit family ID",
    ), groups, strict=True):
        matches = _cross_batch(values)
        sample = "; ".join(", ".join(ids[:4]) for ids in matches[:12])
        lines.append(f"- {name}: **{len(matches)} groups**; sample: {sample or '(none)'}")
    return lines


def build_summary(directory: Path = ROOT) -> str:
    files = batch_files(directory)
    if len(files) != 18:
        raise ValueError("expected all 18 synthetic candidate batches")
    labels, flags, groups = _scan_files(files)
    lines = [
        "# DATA-V2-01 — final-byte QA and independent-review queue", "",
        "Source PR #52 / JSONL commit 53e34e52c6c9a42a8be2ab8f772156e89d31b7e9.",
        "G24 chronology offsets subsequently corrected without changing text or labels.",
        "Generated by python -m tools.dataset_qa.candidate_audit.",
        "Only public synthetic records; excludes W20, W27 and all real-chat logs.", "",
        f"Records: **{sum(labels.values())}** from **{len(files)}** batches.",
        "Rule flags are *review hypotheses*, not confirmed defects or relabels.", "",
    ] + _batch_digest_table(files)
    lines += ["", "## Final label distribution", "", "| Label | Count |", "|---|---:|"]
    lines += [f"| {label} | {count} |" for label, count in sorted(labels.items())]
    lines += _flag_table(flags)
    lines += _overlap_lines(groups)
    lines += [
        "", "Identical target messages are cheap candidate filters, not fuzzy scans.",
        "Review all cross-batch families before partitioning.", "",
        "## Admission decision: NOT TRAINING-READY", "",
        "Structural QA does not establish semantic truth. Independently review",
        "flagged IDs using owner Policy v1, including quoted slurs under §10.", "",
        "W11/W25 overlap requires approved development-only manifests, not W20/W27,",
        "private logs, or previously model-mined heldout material.", "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_summary(), encoding="utf-8")
    print(f"Wrote sanitized aggregate review queue: {OUTPUT}")


if __name__ == "__main__":
    main()
