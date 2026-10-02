from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

SYNTHETIC_GLOB = "data/synthetic/G??-*.jsonl"
GOLDEN_PATH = Path("data/eval/owner-policy-v1.jsonl")
OUTPUT_DIR = Path("data/integration")
REPORT_PATH = Path("docs/W11-DATASET-INTEGRATION-REPORT.md")
ALGORITHM_VERSION = "w11-v1"
NEAR_THRESHOLD = 0.75
FAMILY_NEAR_THRESHOLD = 0.90
GOLDEN_SENSITIVE_THRESHOLD = 0.88
MAX_BLOCK_SIZE = 80
ADVERSARIAL_HASH_PERCENT = 45
EXTRA_ADVERSARIAL_HASH_PERCENT = 8

OUTCOME_FIELDS = (
    "channel_profile",
    "label",
    "action",
    "review_priority",
    "strike",
    "containment",
    "containment_duration_seconds",
    "support_flow",
)
ADVERSARIAL_REASON_CODES = frozenset(
    {
        "split_message_context",
        "long_gap_breaks_linkage",
        "obfuscated_evasion",
        "reply_context",
        "multi_sender_dogpile",
        "coordinated_dogpile",
        "self_harm_instruction",
        "actual_slur",
        "slur_reference_only",
        "sexual_minor",
        "age_reliable_minor",
        "dangerous_instruction_request",
        "historical_or_high_level_context",
    }
)


@dataclass(frozen=True, slots=True)
class Example:
    example_id: str
    source_file: str
    source_prefix: str
    data: dict[str, Any]
    sequence_key: str
    comparison_text: str
    outcome_key: tuple[object, ...]

    @property
    def source_family(self) -> str:
        family = self.data.get("family_id")
        if isinstance(family, str) and family:
            return f"{self.source_prefix}:{family}"
        return f"{self.source_prefix}:singleton:{self.example_id}"


class UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self.parent = {item: item for item in ids}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            item, self.parent[item] = self.parent[item], root
        return root

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        keep, merge = sorted((left_root, right_root))
        self.parent[merge] = keep


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _speaker_text(message: object) -> str:
    if not isinstance(message, dict):
        return ""
    speaker = normalize_text(str(message.get("speaker", "")))
    text = normalize_text(str(message.get("text", "")))
    return f"{speaker}:{text}"


def sequence_key(data: dict[str, Any]) -> str:
    messages = data.get("messages")
    if not isinstance(messages, list):
        return ""
    return "\u241e".join(_speaker_text(message) for message in messages)


def comparison_text(data: dict[str, Any]) -> str:
    messages = data.get("messages")
    if not isinstance(messages, list):
        return ""
    parts = []
    for message in messages:
        if isinstance(message, dict):
            parts.append(normalize_text(str(message.get("text", ""))))
    return " \u241e ".join(parts)


def outcome_key(data: dict[str, Any]) -> tuple[object, ...]:
    return tuple(data.get(field) for field in OUTCOME_FIELDS)


def _prefix_from_id(example_id: str) -> str:
    return example_id.split("-", 1)[0]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"{path}: JSONL record is not an object")
            records.append(parsed)
    return records


def load_synthetic(root: Path) -> list[Example]:
    examples: list[Example] = []
    for path in sorted(root.glob(SYNTHETIC_GLOB)):
        for data in load_jsonl(path):
            example_id = str(data.get("example_id", ""))
            examples.append(
                Example(
                    example_id=example_id,
                    source_file=str(path.relative_to(root)),
                    source_prefix=_prefix_from_id(example_id),
                    data=data,
                    sequence_key=sequence_key(data),
                    comparison_text=comparison_text(data),
                    outcome_key=outcome_key(data),
                )
            )
    return sorted(examples, key=lambda item: item.example_id)


def _blocks(text: str) -> set[str]:
    tokens = re.findall(r"[\w']+", text)
    if len(tokens) < 2:
        return set(tokens)
    return {" ".join(pair) for pair in zip(tokens, tokens[1:], strict=False)}


def candidate_pairs(examples: list[Example]) -> set[tuple[str, str]]:
    by_block: dict[str, list[str]] = defaultdict(list)
    text_by_id = {item.example_id: item.comparison_text for item in examples}
    for item in examples:
        for block in sorted(_blocks(item.comparison_text)):
            by_block[block].append(item.example_id)
    shared: Counter[tuple[str, str]] = Counter()
    for ids in by_block.values():
        if len(ids) > MAX_BLOCK_SIZE:
            continue
        for left, right in combinations(sorted(set(ids)), 2):
            shared[(left, right)] += 1
    result: set[tuple[str, str]] = set()
    for pair, count in shared.items():
        short = min(len(text_by_id[pair[0]]), len(text_by_id[pair[1]])) < 40
        if count >= 2 or (short and count >= 1):
            result.add(pair)
    return result


def near_candidates(examples: list[Example]) -> list[dict[str, object]]:
    by_id = {item.example_id: item for item in examples}
    exact = exact_groups(examples)
    exact_pairs = {
        tuple(sorted(pair))
        for group in exact
        for pair in combinations(group["ids"], 2)
    }
    candidates: list[dict[str, object]] = []
    for left_id, right_id in sorted(candidate_pairs(examples)):
        if (left_id, right_id) in exact_pairs:
            continue
        left = by_id[left_id]
        right = by_id[right_id]
        ratio = text_similarity(left.comparison_text, right.comparison_text)
        if ratio < NEAR_THRESHOLD:
            continue
        candidates.append(_near_row(left, right, ratio))
    return candidates


def _char_trigrams(value: str) -> set[str]:
    padded = f"  {value}  "
    return {padded[index : index + 3] for index in range(max(1, len(padded) - 2))}


def text_similarity(left: str, right: str) -> float:
    left_grams = _char_trigrams(left)
    right_grams = _char_trigrams(right)
    if not left_grams and not right_grams:
        return 1.0
    if not left_grams or not right_grams:
        return 0.0
    shared = len(left_grams & right_grams)
    return 2 * shared / (len(left_grams) + len(right_grams))


def _near_row(left: Example, right: Example, ratio: float) -> dict[str, object]:
    return {
        "left": left.example_id,
        "right": right.example_id,
        "similarity": round(ratio, 6),
        "same_outcome": left.outcome_key == right.outcome_key,
        "same_source_family": left.source_family == right.source_family,
        "cross_source": left.source_prefix != right.source_prefix,
    }


def exact_groups(examples: list[Example]) -> list[dict[str, object]]:
    grouped: dict[str, list[Example]] = defaultdict(list)
    for item in examples:
        grouped[item.sequence_key].append(item)
    rows = []
    for items in grouped.values():
        if not items[0].sequence_key or len(items) < 2:
            continue
        outcomes = {item.outcome_key for item in items}
        rows.append(
            {
                "ids": sorted(item.example_id for item in items),
                "same_outcome": len(outcomes) == 1,
                "cross_source": len({item.source_prefix for item in items}) > 1,
            }
        )
    return sorted(rows, key=lambda row: row["ids"])


def golden_leakage(
    examples: list[Example], golden_records: list[dict[str, Any]]
) -> list[dict[str, object]]:
    golden = [
        (str(item.get("example_id", "")), sequence_key(item), comparison_text(item))
        for item in golden_records
    ]
    results: list[dict[str, object]] = []
    for example in examples:
        best = _best_golden_match(example, golden)
        if best is not None:
            results.append(best)
    return sorted(results, key=lambda row: (row["synthetic_id"], row["golden_id"]))


def _best_golden_match(
    example: Example, golden: list[tuple[str, str, str]]
) -> dict[str, object] | None:
    best_id = ""
    best_ratio = 0.0
    exact = False
    for golden_id, golden_key, golden_text in golden:
        is_exact = bool(example.sequence_key and example.sequence_key == golden_key)
        ratio = 1.0 if is_exact else text_similarity(
            example.comparison_text, golden_text
        )
        if ratio > best_ratio:
            best_id, best_ratio, exact = golden_id, ratio, is_exact
    if best_ratio < NEAR_THRESHOLD:
        return None
    return {
        "synthetic_id": example.example_id,
        "golden_id": best_id,
        "similarity": round(best_ratio, 6),
        "exact": exact,
        "training_sensitive": best_ratio >= GOLDEN_SENSITIVE_THRESHOLD,
    }


def build_union(
    examples: list[Example],
    exact: list[dict[str, object]],
    near: list[dict[str, object]],
) -> UnionFind:
    union = UnionFind([item.example_id for item in examples])
    by_family: dict[str, list[str]] = defaultdict(list)
    for item in examples:
        by_family[item.source_family].append(item.example_id)
    for ids in by_family.values():
        _union_group(union, ids)
    for row in exact:
        _union_group(union, list(row["ids"]))
    for row in near:
        if float(row["similarity"]) >= FAMILY_NEAR_THRESHOLD:
            union.union(str(row["left"]), str(row["right"]))
    return union


def _union_group(union: UnionFind, ids: list[str]) -> None:
    if not ids:
        return
    first = ids[0]
    for item in ids[1:]:
        union.union(first, item)


def integration_groups(
    examples: list[Example], union: UnionFind
) -> dict[str, list[Example]]:
    groups: dict[str, list[Example]] = defaultdict(list)
    for item in examples:
        groups[union.find(item.example_id)].append(item)
    return {
        root: sorted(items, key=lambda item: item.example_id)
        for root, items in sorted(groups.items())
    }


def _stable_hash(value: str) -> int:
    result = 2_166_136_261
    for byte in value.encode("utf-8"):
        result ^= byte
        result = (result * 16_777_619) & 0xFFFF_FFFF
    return result


def _hash_percent(key: str, salt: str) -> int:
    return _stable_hash(f"{ALGORITHM_VERSION}:{salt}:{key}") % 100


def _is_adversarial_group(items: list[Example]) -> bool:
    if any(item.source_prefix == "G08" for item in items):
        return True
    for item in items:
        reasons = item.data.get("reason_codes")
        if isinstance(reasons, list) and ADVERSARIAL_REASON_CODES.intersection(reasons):
            return True
    return any(item.data.get("difficulty") == "adversarial" for item in items)


def assign_partitions(
    groups: dict[str, list[Example]], sensitive_ids: set[str]
) -> dict[str, list[str]]:
    partitions = {"train": [], "validation": [], "test": [], "frozen_adversarial": []}
    for root, items in groups.items():
        ids = [item.example_id for item in items]
        if any(item in sensitive_ids for item in ids) or _frozen_by_hash(root, items):
            partition = "frozen_adversarial"
        else:
            partition = _ordinary_partition(root)
        partitions[partition].extend(ids)
    for ids in partitions.values():
        ids.sort()
    return partitions


def _frozen_by_hash(root: str, items: list[Example]) -> bool:
    slot = _hash_percent(root, "adversarial")
    if any(item.source_prefix == "G08" for item in items):
        return slot < ADVERSARIAL_HASH_PERCENT
    return _is_adversarial_group(items) and slot < EXTRA_ADVERSARIAL_HASH_PERCENT


def _ordinary_partition(root: str) -> str:
    slot = _hash_percent(root, "ordinary")
    if slot < 80:
        return "train"
    if slot < 90:
        return "validation"
    return "test"


def group_manifest(
    groups: dict[str, list[Example]], partitions: dict[str, list[str]]
) -> dict[str, object]:
    partition_by_id = {
        example_id: partition
        for partition, ids in partitions.items()
        for example_id in ids
    }
    rows = []
    for root, items in groups.items():
        ids = [item.example_id for item in items]
        parts = {partition_by_id[item] for item in ids}
        if len(parts) != 1:
            raise ValueError(f"integration family crossed partitions: {root}")
        rows.append(
            {
                "group_id": _group_id(ids),
                "partition": next(iter(parts)),
                "example_ids": ids,
            }
        )
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "records": sum(len(items) for items in groups.values()),
        "partitions": partitions,
        "groups": rows,
    }


def _group_id(ids: list[str]) -> str:
    joined = "\n".join(sorted(ids))
    return f"IF-{_stable_hash(joined):08x}-{len(ids):04d}"


def cross_source_review(
    examples: list[Example],
    near: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_id = {item.example_id: item for item in examples}
    rows: list[dict[str, object]] = []
    for row in near:
        if not bool(row["cross_source"]) or bool(row["same_outcome"]):
            continue
        if float(row["similarity"]) < FAMILY_NEAR_THRESHOLD:
            continue
        left = by_id[str(row["left"])]
        right = by_id[str(row["right"])]
        rows.append(_cross_source_disposition(left, right, row))
    return rows


def _cross_source_disposition(
    left: Example,
    right: Example,
    row: dict[str, object],
) -> dict[str, object]:
    reasons = set(left.data.get("reason_codes", [])) | set(right.data.get("reason_codes", []))
    flirting = bool({"public_flirting", "private_flirting"} & reasons)
    disposition = "intentional_policy_contrast" if flirting else "requires_policy_review"
    policy_source = "policy/POLICY-v1.md §11" if flirting else None
    return {
        **row,
        "disposition": disposition,
        "policy_source": policy_source,
    }


def contradiction_rows(
    exact: list[dict[str, object]],
    near: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for group in exact:
        if not bool(group["same_outcome"]):
            rows.append({"kind": "exact_contrast", **group})
    for row in near:
        if not bool(row["same_outcome"]) and float(row["similarity"]) >= 0.88:
            rows.append({"kind": "near_decision_contrast", **row})
    return rows


def distributions(examples: list[Example]) -> dict[str, object]:
    fields = (
        "domain",
        "label",
        "action",
        "review_priority",
        "strike",
        "containment",
        "support_flow",
        "channel_profile",
        "platform_hint",
        "difficulty",
    )
    result: dict[str, object] = {}
    for field in fields:
        counts = Counter(str(item.data.get(field)) for item in examples)
        result[field] = dict(sorted(counts.items()))
    result["message_count"] = dict(
        sorted(Counter(str(len(item.data.get("messages", []))) for item in examples).items())
    )
    return result


def audit_payload(
    examples: list[Example],
    exact: list[dict[str, object]],
    near: list[dict[str, object]],
    leakage: list[dict[str, object]],
    groups: dict[str, list[Example]],
) -> dict[str, object]:
    redundant_exact = [row for row in exact if bool(row["same_outcome"])]
    cross_near = [row for row in near if bool(row["cross_source"])]
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "records": len(examples),
        "source_counts": dict(sorted(Counter(item.source_prefix for item in examples).items())),
        "exact_groups": exact,
        "redundant_exact_groups": redundant_exact,
        "near_candidates": near,
        "cross_source_near_candidates": cross_near,
        "cross_source_review": cross_source_review(examples, near),
        "contradictions": contradiction_rows(exact, near),
        "golden_leakage_candidates": leakage,
        "integration_group_count": len(groups),
        "largest_group_size": max((len(items) for items in groups.values()), default=0),
        "distributions": distributions(examples),
    }


def render_report(
    audit: dict[str, object],
    manifest: dict[str, object],
    leakage: list[dict[str, object]],
) -> str:
    parts = manifest["partitions"]
    if not isinstance(parts, dict):
        raise ValueError("partition manifest is malformed")
    sensitive = [row for row in leakage if bool(row["training_sensitive"])]
    exact = audit["exact_groups"]
    near = audit["near_candidates"]
    cross_near = audit["cross_source_near_candidates"]
    contradictions = audit["contradictions"]
    cross_review = audit["cross_source_review"]
    unresolved_cross = [
        row for row in cross_review if row["disposition"] == "requires_policy_review"
    ]
    lines = [
        "# W11 dataset integration report",
        "",
        f"- Algorithm: `{ALGORITHM_VERSION}`",
        f"- Synthetic records: **{audit['records']}**",
        f"- Integration families: **{audit['integration_group_count']}**",
        f"- Largest integration family: **{audit['largest_group_size']}** records",
        f"- Text-only exact groups: **{len(exact)}**",
        f"- Near candidates (>= {NEAR_THRESHOLD:.2f}): **{len(near)}**",
        f"- Cross-source near candidates: **{len(cross_near)}**",
        f"- Decision-contrast lexical candidates: **{len(contradictions)}**",
        f"- High-similarity cross-worker contrasts reviewed: **{len(cross_review)}**",
        f"- Unresolved cross-worker contradictions: **{len(unresolved_cross)}**",
        f"- Golden near/exact candidates: **{len(leakage)}**",
        f"- Golden-sensitive (>= {GOLDEN_SENSITIVE_THRESHOLD:.2f}): **{len(sensitive)}**",
        "",
        "## Frozen split counts",
        "",
    ]
    for name in ("train", "validation", "test", "frozen_adversarial"):
        lines.append(f"- {name}: **{len(parts[name])}**")
    lines.extend(_report_sections(audit, sensitive))
    return "\n".join(lines) + "\n"


def _report_sections(
    audit: dict[str, object], sensitive: list[dict[str, object]]
) -> list[str]:
    redundant = audit["redundant_exact_groups"]
    return [
        "",
        "## Leakage and family safety",
        "",
        f"- Redundant same-outcome text-only exact groups: **{len(redundant)}**.",
        "- Every source `family_id`, text-only exact group, and >=0.90 near group is kept",
        "  in one integration family before splitting.",
        "- Owner golden fixtures are never copied into these manifests. Synthetic records",
        f"  with >={GOLDEN_SENSITIVE_THRESHOLD:.2f} similarity to a golden fixture are forced",
        "  into frozen evaluation.",
        f"- Golden-sensitive synthetic records forced out of training: **{len(sensitive)}**.",
        "",
        "## Decision contrasts",
        "",
        "The machine-readable audit records exact and >=0.88 near pairs whose Policy-v1",
        "outcome dimensions differ. These are candidates for intentional minimal pairs or",
        "data defects; W11 does not silently relabel them.",
        "",
        "## Known limitation",
        "",
        "Near-duplicate detection is deterministic lexical candidate finding, not semantic",
        "embedding similarity. It uses shared normalized token bigrams followed by",
        "normalized character-trigram Dice similarity. Human review remains required.",
        "",
        "## Files",
        "",
        "- `data/integration/W11-audit.json`",
        "- `data/integration/W11-split-manifest.json`",
        "- `data/integration/W11-adversarial-eval-manifest.json`",
    ]


def build_outputs(root: Path) -> dict[Path, str]:
    examples = load_synthetic(root)
    if len(examples) != 4500:
        raise ValueError(f"expected 4500 synthetic records, found {len(examples)}")
    golden = load_jsonl(root / GOLDEN_PATH)
    exact = exact_groups(examples)
    near = near_candidates(examples)
    leakage = golden_leakage(examples, golden)
    union = build_union(examples, exact, near)
    groups = integration_groups(examples, union)
    sensitive = {
        str(row["synthetic_id"]) for row in leakage if bool(row["training_sensitive"])
    }
    partitions = assign_partitions(groups, sensitive)
    manifest = group_manifest(groups, partitions)
    audit = audit_payload(examples, exact, near, leakage, groups)
    adversarial = {
        "algorithm_version": ALGORITHM_VERSION,
        "example_ids": partitions["frozen_adversarial"],
    }
    return {
        OUTPUT_DIR / "W11-audit.json": _json_text(audit),
        OUTPUT_DIR / "W11-split-manifest.json": _json_text(manifest),
        OUTPUT_DIR / "W11-adversarial-eval-manifest.json": _json_text(adversarial),
        REPORT_PATH: render_report(audit, manifest, leakage),
    }


def _json_text(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def write_outputs(root: Path, outputs: dict[Path, str]) -> None:
    for relative, content in outputs.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_outputs(root: Path, outputs: dict[Path, str]) -> list[str]:
    failures = []
    for relative, expected in outputs.items():
        path = root / relative
        if not path.exists():
            failures.append(f"missing generated output: {relative}")
        elif path.read_text(encoding="utf-8") != expected:
            failures.append(f"stale generated output: {relative}")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build W11 dataset integration artifacts.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    outputs = build_outputs(root)
    if args.check:
        failures = check_outputs(root, outputs)
        if failures:
            print("\n".join(failures))
            return 1
        print("W11 integration artifacts are deterministic and up to date.")
        return 0
    write_outputs(root, outputs)
    print("W11 integration artifacts written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
