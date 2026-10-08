from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
CANDIDATE_PATH = ROOT / "data/candidates/W21-adversarial-evasion.jsonl"
ACCEPTED_PATHS = tuple(sorted((ROOT / "data/synthetic").glob("G*.jsonl"))) + (
    ROOT / "data/eval/owner-policy-v1.jsonl",
)
NEAR_THRESHOLD = 0.92
TRIVIAL_THRESHOLD = 0.985
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Prepared:
    example_id: str
    path: Path
    text: str
    trigrams: frozenset[str]


def _load(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return SPACE_RE.sub(" ", normalized).strip()


def _text(record: dict[str, Any]) -> str:
    return " ⟂ ".join(_normalize(message["text"]) for message in record["messages"])


def _trigrams(text: str) -> frozenset[str]:
    padded = f"  {text}  "
    return frozenset(padded[index : index + 3] for index in range(len(padded) - 2))


def _prepare(path: Path, record: dict[str, Any]) -> Prepared:
    text = _text(record)
    return Prepared(record["example_id"], path, text, _trigrams(text))


def _exact_key(record: dict[str, Any]) -> tuple[object, ...]:
    messages = tuple(
        (message["speaker"], message["offset_ms"], _normalize(message["text"]))
        for message in record["messages"]
    )
    return (
        record.get("platform_hint"),
        record.get("channel_profile"),
        record["target_index"],
        messages,
    )


def _candidate_similarity(left: Prepared, right: Prepared) -> float:
    length_ratio = min(len(left.text), len(right.text)) / max(
        len(left.text), len(right.text), 1
    )
    if length_ratio < 0.70:
        return 0.0
    union = left.trigrams | right.trigrams
    jaccard = len(left.trigrams & right.trigrams) / max(len(union), 1)
    if jaccard < 0.25:
        return 0.0
    return SequenceMatcher(None, left.text, right.text, autojunk=False).ratio()


def _accepted() -> tuple[list[tuple[Path, dict[str, Any]]], list[Prepared]]:
    raw = [
        (path, record)
        for path in ACCEPTED_PATHS
        for record in _load(path)
    ]
    prepared = [_prepare(path, record) for path, record in raw]
    return raw, prepared


def _best_near(candidate: Prepared, accepted: list[Prepared]) -> tuple[float, Prepared | None]:
    best_score = 0.0
    best: Prepared | None = None
    for item in accepted:
        score = _candidate_similarity(candidate, item)
        if score > best_score:
            best_score, best = score, item
    return best_score, best


def _near_row(candidate: Prepared, score: float, accepted: Prepared) -> dict[str, object]:
    return {
        "candidate": candidate.example_id,
        "accepted": accepted.example_id,
        "path": str(accepted.path.relative_to(ROOT)),
        "similarity": round(score, 6),
    }


def audit() -> dict[str, Any]:
    candidates = _load(CANDIDATE_PATH)
    accepted_raw, accepted = _accepted()
    exact_index = {
        _exact_key(record): (path, record["example_id"])
        for path, record in accepted_raw
    }
    exact: list[dict[str, object]] = []
    near: list[dict[str, object]] = []
    for record in candidates:
        collision = exact_index.get(_exact_key(record))
        if collision:
            exact.append({
                "candidate": record["example_id"],
                "accepted": collision[1],
                "path": str(collision[0].relative_to(ROOT)),
            })
        prepared = _prepare(CANDIDATE_PATH, record)
        score, best = _best_near(prepared, accepted)
        if best and score >= NEAR_THRESHOLD:
            near.append(_near_row(prepared, score, best))
    trivial = [row for row in near if row["similarity"] >= TRIVIAL_THRESHOLD]
    return {
        "candidate_records": len(candidates),
        "accepted_records": len(accepted),
        "exact_collisions": exact,
        "near_candidates": near,
        "trivial_near_collisions": trivial,
        "near_threshold": NEAR_THRESHOLD,
        "trivial_threshold": TRIVIAL_THRESHOLD,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit()
    print(json.dumps(result, indent=2 if args.json else None, sort_keys=True))
    blocked = result["exact_collisions"] or result["trivial_near_collisions"]
    return 1 if args.check and blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
