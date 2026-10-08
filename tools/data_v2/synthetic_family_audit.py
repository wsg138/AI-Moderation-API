"""Read-only, source-pinned G10-G27 candidate-family leakage audit.

No private source access, model inference, label admission, or split creation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from tools.dataset_qa.asof_input import serialize_as_of_target
from tools.dataset_qa.freshness import ROOT, batch_files
from tools.dataset_qa.normalize import normalize_text

SOURCE_COMMIT = "a77fdaf15a90123225311ebc4c8823191655bc69"
SOURCE_DIGESTS = {
    "G10": "4d62fe8dc1acd402b19bead5fa8ffd6652fc017a71b4b030a66f71a308e4df83",
    "G11": "17d9769d22dcd8c2cacf8b0fd92ea3c923b7003df0338d10d4e12ee05049c382",
    "G12": "fcc6f3b074013eed6f053d9ed88480f0c76df9435072b8a8cd8af6e0922084fd",
    "G13": "7a44d370d2ebd37a9d556894d36035e57c86f13875d0f3dae5ffeffb173268cd",
    "G14": "e3c9369a30ba0dc49469f77163d24520bb3a507ea08fd75bf6b3125ffb3713f1",
    "G15": "4e7ec5dca2eae97dc3b9cd807eb1005177ac84842d1d41280a3baca58502aa8b",
    "G16": "8f62d09e6ac324d55f0c21bd6bc8d9ee44a25dee1956d5c51a4a5cb42677acd3",
    "G17": "a3d5d94fb2583068811c64efbb60315954ec363dae572cc2e972d8d20527916c",
    "G18": "e419bb49788b149f5c9501d813e4496259917af7b563531be73a54a948f034c5",
    "G19": "a0f9b0c9e091ec0a9d5c7a2ce52dfe0d36745d4862ddf64154ab95ffc92f6597",
    "G20": "3730793c44af6b2fafa17fb51e737876e8b5a79978bb3ef1f47b31f012e78e48",
    "G21": "ff04f45497a9368224f8f1455f1e325f4a4850dfdd713fcef332308019884bb9",
    "G22": "a5c54c51cdcc6e12115dac66182258bacc4138e402095fd5f96ce9a104963a6d",
    "G23": "f821e3c163e9ae5fd3d173cbf41f084205550e311ccfa3b391038c5435f457ce",
    "G24": "06caf466122e3eebfd23013800075274cdda96d1584620d179b1be6230828007",
    "G25": "4d69a1884fe00845f4e9e5622ec5ea20608f2e4ce1a7149b5d52c3717b90c8b7",
    "G26": "9e5df11ad9426551e75d53260d1e09776fe71c71b824d410f18f7dcf87992e18",
    "G27": "2744c432e978a4cee945aac0d694ea06a166c777f37f5f064351a321705cd6d6",
}
EVIDENCE_KINDS = (
    "asof_exact", "target_exact", "family_id",
    "family_stem_candidate", "near_target_candidate",
)
HEURISTIC_KINDS = frozenset({"family_stem_candidate", "near_target_candidate"})
IDENTIFIER = re.compile(r"^G(?:1\d|2[0-7])-\d{4}$")
TOKENS = re.compile(r"\w+", flags=re.UNICODE)


@dataclass(frozen=True)
class Group:
    kind: str
    example_ids: tuple[str, ...]

    @property
    def cross_batch(self) -> bool:
        return len({identifier[:3] for identifier in self.example_ids}) > 1


def _decode_batch(path: Path) -> list[object]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_DIGESTS[path.name[:3]]:
        raise ValueError(f"changed candidate source bytes: {path.name}")
    lines = raw.decode("utf-8").splitlines()
    if len(lines) != 500:
        raise ValueError(f"expected 500 cases in {path.name}")
    return [json.loads(line) for line in lines]


def _check_row(row: object, path: Path, seen: set[str]) -> dict[str, Any]:
    if not isinstance(row, dict) or row.get("source") != "synthetic":
        raise ValueError(f"non-public-synthetic source: {path.name}")
    identifier = row.get("example_id")
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        raise ValueError("invalid synthetic example ID")
    if identifier in seen or not identifier.startswith(path.name[:3] + "-"):
        raise ValueError("duplicate or misfiled synthetic example ID")
    seen.add(identifier)
    return row


def load_candidates(directory: Path = ROOT) -> list[dict[str, Any]]:
    """Allowlist all 18 public synthetic files, checking final-byte hashes."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in batch_files(directory, require_complete=True):
        for item in _decode_batch(path):
            rows.append(_check_row(item, path, seen))
    if len(rows) != 9000:
        raise ValueError("expected exactly 9,000 synthetic candidate cases")
    return rows


def _visible(row: dict[str, Any]) -> dict[str, object]:
    return serialize_as_of_target(row)


def _asof_key(visible: dict[str, object]) -> str:
    """Match visible input, not retrospective post-target context."""
    messages = visible["messages"]
    assert isinstance(messages, list)
    compact = [
        (normalize_text(message["speaker"]), message["offset_ms"],
         normalize_text(message["text"]))
        for message in messages
    ]
    fields = (
        normalize_text(visible["platform_hint"]),
        normalize_text(visible["channel_profile"]),
        visible["target_index"], compact,
    )
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))


def _target(visible: dict[str, object]) -> str:
    messages = visible["messages"]
    index = visible["target_index"]
    assert isinstance(messages, list) and isinstance(index, int)
    return normalize_text(messages[index]["text"])


def _stem(row: dict[str, Any]) -> str | None:
    family = row.get("family_id")
    if not isinstance(family, str):
        return None
    stem = re.sub(r"\.\d+$", "", family)
    return stem if stem != family else None


def _buckets(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in rows:
        identifier = row["example_id"]
        visible = _visible(row)
        buckets[("asof_exact", _asof_key(visible))].append(identifier)
        target = _target(visible)
        if len(target) >= 18:
            buckets[("target_exact", target)].append(identifier)
        family = row.get("family_id")
        if isinstance(family, str):
            buckets[("family_id", family)].append(identifier)
        stem = _stem(row)
        if stem is not None:
            buckets[("family_stem_candidate", stem)].append(identifier)
    return buckets


def _near_tokens(rows: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, set[str]]]:
    texts: dict[str, str] = {}
    tokens: dict[str, set[str]] = {}
    for row in rows:
        identifier = row["example_id"]
        target = _target(_visible(row))
        unique = set(TOKENS.findall(target))
        if len(target) >= 30 and len(unique) >= 6:
            texts[identifier] = target
            tokens[identifier] = unique
    return texts, tokens


def _anchors(words: set[str], frequency: Counter[str]) -> list[str]:
    return sorted(
        (word for word in words if len(word) >= 4 and frequency[word] <= 64),
        key=lambda word: (frequency[word], word),
    )[:6]


def _near_pairs(tokens: dict[str, set[str]]) -> list[tuple[str, str]]:
    frequency = Counter(word for words in tokens.values() for word in words)
    index: dict[str, list[str]] = defaultdict(list)
    for identifier, words in sorted(tokens.items()):
        for word in _anchors(words, frequency):
            index[word].append(identifier)
    candidates: set[tuple[str, str]] = set()
    for identifiers in index.values():
        candidates.update(combinations(identifiers, 2))
    return sorted(candidates)


def _is_near(left: set[str], right: set[str]) -> bool:
    shared = len(left & right)
    union = len(left | right)
    return (
        shared >= 5
        and shared / union >= 0.8
        and min(len(left), len(right)) / max(len(left), len(right)) >= 0.8
    )


def _near_groups(rows: list[dict[str, Any]]) -> list[Group]:
    texts, tokens = _near_tokens(rows)
    output: list[Group] = []
    for left, right in _near_pairs(tokens):
        if texts[left] != texts[right] and _is_near(tokens[left], tokens[right]):
            output.append(Group("near_target_candidate", (left, right)))
    return output


def find_groups(rows: list[dict[str, Any]]) -> list[Group]:
    """Distinct evidence kinds; heuristics never become certified lineage."""
    ids = [row["example_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate synthetic IDs")
    buckets = _buckets(rows)
    groups = [
        Group(kind, tuple(sorted(set(identifiers))))
        for (kind, _), identifiers in buckets.items()
        if len(set(identifiers)) > 1
    ]
    groups.extend(_near_groups(rows))
    return sorted(groups, key=lambda item: (item.kind, item.example_ids))


def summarize(rows: list[dict[str, Any]], groups: list[Group]) -> dict[str, object]:
    kinds: dict[str, dict[str, int]] = {}
    for kind in EVIDENCE_KINDS:
        matched = [group for group in groups if group.kind == kind]
        kinds[kind] = {
            "groups": len(matched),
            "cases": len({i for group in matched for i in group.example_ids}),
            "cross_batch_groups": sum(group.cross_batch for group in matched),
        }
    return {
        "source_commit": SOURCE_COMMIT, "status": "candidate",
        "training_eligible": False, "batches": 18, "records": len(rows),
        "nonterminal_targets": sum(
            row["target_index"] < len(row["messages"]) - 1 for row in rows
        ),
        "overlap": kinds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        rows = load_candidates(args.directory)
        print(json.dumps(summarize(rows, find_groups(rows)), indent=2, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Synthetic family audit blocked: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
