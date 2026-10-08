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


def _flags(record: dict[str, Any]) -> set[str]:
    label, action = record.get("label"), record.get("action")
    reasons = set(record.get("reason_codes", []))
    target, context, messages = _context(record)
    flags: set[str] = set()
    if label == "SAFE" and action != "ALLOW":
        flags.add("safe_action_disagreement")
    if label == "AMBIGUOUS_REVIEW" and action != "REVIEW":
        flags.add("ambiguous_action_disagreement")
    if label == "SAFE" and (record.get("strike") or record.get("containment") != "NONE"):
        flags.add("safe_with_punishment")
    if label == "SAFE" and reasons & SENSITIVE:
        flags.add("safe_with_severe_reason_code")
    if label == "SAFE" and DIRECTIVE.search(target):
        flags.add("safe_with_self_harm_directive")
    if label == "SELF_HARM_INTENT" and (action == "BLOCK" or record.get("strike")):
        flags.add("self_harm_disclosure_punished")
    if label == "REAL_WORLD_THREAT" and GAME.search(target) and not REAL.search(context):
        flags.add("real_world_label_with_game_cue")
    if label == "GAMEPLAY_VIOLENCE" and REAL.search(context):
        flags.add("gameplay_label_with_real_cue")
    if label == "GROOMING" and not MINOR.search(context):
        flags.add("grooming_without_explicit_minor_cue")
    if "actual_slur" in reasons and label not in {"HATE", "SLUR_USE"}:
        flags.add("actual_slur_reason_label_disagreement")
    if "staff_targeted_abuse" in reasons and label != "STAFF_TARGETED_ABUSE":
        flags.add("staff_targeted_reason_label_disagreement")
    if DM_PIVOT.fullmatch(target.strip()) and label != "SAFE":
        flags.add("dm_pivot_is_target")
    if record.get("target_index") != len(messages) - 1:
        flags.add("nonterminal_target_index_review")
    offsets = [m.get("offset_ms") for m in messages]
    if any(a > b for a, b in zip(offsets, offsets[1:])):
        flags.add("nonchronological_message_offsets")
    if len(messages) >= 3 and len({m.get("speaker") for m in messages}) == 1:
        flags.add("single_speaker_multimessage_realism_review")
    return flags


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


def build_summary(directory: Path = ROOT) -> str:
    files = batch_files(directory)
    if len(files) != 18:
        raise ValueError("expected all 18 synthetic candidate batches")
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
    lines = [
        "# DATA-V2-01 — final-byte QA and independent-review queue", "",
        "Source PR #52 / JSONL commit 53e34e52c6c9a42a8be2ab8f772156e89d31b7e9.",
        "Generated by python -m tools.dataset_qa.candidate_audit.",
        "Only public synthetic records; excludes W20, W27 and all real-chat logs.", "",
        f"Records: **{sum(labels.values())}** from **{len(files)}** batches.",
        "Rule flags are *review hypotheses*, not confirmed defects or relabels.", "",
    ] + _batch_digest_table(files)
    lines += ["", "## Final label distribution", "", "| Label | Count |", "|---|---:|"]
    lines += [f"| {label} | {count} |" for label, count in sorted(labels.items())]
    lines += ["", "## Sanitized review queue", "",
              "| Rule | Count | First 12 synthetic example IDs |",
              "|---|---:|---|"]
    for rule, ids in sorted(flags.items()):
        lines.append(f"| {rule} | {len(ids)} | {', '.join(sorted(ids)[:12])} |")
    lines += ["", "## Cross-batch structural family overlap", ""]
    groups = [
        ("Exact normalized full contexts", _cross_batch(duplicates)),
        ("Identical target message (18+ chars)", _cross_batch(targets)),
        ("Shared explicit family ID", _cross_batch(families)),
    ]
    for name, matches in groups:
        sample = "; ".join(", ".join(ids[:4]) for ids in matches[:12])
        lines.append(f"- {name}: **{len(matches)} groups**; sample: {sample or '(none)'}")
    lines += [
        "", "Target-message equality is a cheap candidate filter, not a fuzzy-neighbor",
        "exhaustive scan. Review cross-batch families prior to partitioning.", "",
        "## Admission decision: NOT TRAINING-READY", "",
        "Existing QA validates structure, not semantic truth. An independent reviewer",
        "must adjudicate flagged IDs against owner Policy v1, including actual",
        "quoted slurs under §10, before admitting examples.", "",
        "For W11/W25 overlap, obtain an approved development-only manifest",
        "and compare family/normalized context without accessing W20, W27,",
        "private logs, or previously model-mined heldout evidence.", "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_summary(), encoding="utf-8")
    print(f"Wrote sanitized aggregate review queue: {OUTPUT}")


if __name__ == "__main__":
    main()
