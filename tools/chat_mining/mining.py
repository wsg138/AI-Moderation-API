from __future__ import annotations

import heapq
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .privacy import normalized_text, stable_hash
from .store import MiningStore

_SPACED_LETTERS = re.compile(r"\b(?:[a-z]\s+){2,}[a-z]\b", re.IGNORECASE)
_VIOLENCE = re.compile(
    r"\b(?:kill|stab|shoot|bomb|tnt|sword|mace|explode)\w*\b",
    re.IGNORECASE,
)
_SELF_HARM = re.compile(r"\b(?:kys|kill yourself)\b", re.IGNORECASE)


def _load_score_rows(store: MiningStore, path: Path) -> int:
    loaded = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            _validate_score(value, line_no)
            partition = _message_partition(store, str(value["message_id"]))
            if partition == "holdout":
                raise ValueError(f"line {line_no}: refusing model scores for protected holdout")
            store.add_score(
                str(value["message_id"]),
                str(value["model"]),
                str(value["action"]),
                float(value["block_confidence"]),
            )
            loaded += 1
    return loaded


def load_scores(store: MiningStore, path: Path) -> int:
    store.connection.execute("SAVEPOINT score_load")
    try:
        loaded = _load_score_rows(store, path)
    except Exception:
        store.connection.execute("ROLLBACK TO score_load")
        store.connection.execute("RELEASE score_load")
        raise
    store.connection.execute("RELEASE score_load")
    store.commit()
    return loaded


def _validate_score(value: Any, line_no: int) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"line {line_no}: score must be an object")
    required = {"message_id", "model", "action", "block_confidence"}
    if not required.issubset(value):
        raise ValueError(f"line {line_no}: score is missing required fields")
    if value["action"] not in {"ALLOW", "REVIEW", "BLOCK"}:
        raise ValueError(f"line {line_no}: invalid action")
    confidence = value["block_confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError(f"line {line_no}: block_confidence must be numeric")
    if not 0 <= float(confidence) <= 1:
        raise ValueError(f"line {line_no}: block_confidence must be in [0,1]")


def _message_partition(store: MiningStore, message_id: str) -> str:
    row = store.connection.execute(
        "SELECT partition_name FROM messages WHERE message_id=?",
        (message_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown message_id {message_id}")
    partition = row["partition_name"]
    if partition is None:
        raise ValueError("splits must be finalized before model scores are loaded")
    return str(partition)


def _has_unicode_letters(text: str) -> bool:
    return any(ord(char) > 127 and char.isalnum() for char in text)


def _has_slang(text: str, slang_terms: set[str]) -> bool:
    lowered = normalized_text(text)
    return bool(slang_terms) and any(term in lowered for term in slang_terms)


def _rule_hits(text: str, slang_terms: set[str]) -> list[str]:
    hits: list[str] = []
    if _SPACED_LETTERS.search(text):
        hits.append("spaced_letters")
    if _VIOLENCE.search(text):
        hits.append("violence_lexical")
    if _SELF_HARM.search(text):
        hits.append("self_harm_lexical")
    if _has_unicode_letters(text):
        hits.append("unicode_letters")
    if _has_slang(text, slang_terms):
        hits.append("server_slang")
    return hits


def _action_for_model(scores: list[sqlite3.Row], needle: str) -> str | None:
    for row in scores:
        if needle in str(row["model"]).casefold():
            return str(row["action"])
    return None


def _named_model_buckets(scores: list[sqlite3.Row]) -> list[tuple[str, float]]:
    tfidf = _action_for_model(scores, "tfidf")
    bert = _action_for_model(scores, "bert")
    if tfidf == "BLOCK" and bert == "ALLOW":
        return [("tfidf_block_bert_allow", 1.0)]
    if bert == "BLOCK" and tfidf == "ALLOW":
        return [("bert_block_tfidf_allow", 1.0)]
    return []


def _decision_buckets(
    actions: set[str],
    confidences: list[float],
    score_count: int,
) -> list[tuple[str, float]]:
    result: list[tuple[str, float]] = []
    if len(actions) > 1:
        result.append(("model_disagreement", 0.95))
    if actions == {"BLOCK"} and score_count >= 2:
        result.append(("both_block", max(confidences)))
    elif "BLOCK" in actions:
        result.append(("model_suspicious", max(confidences)))
    return result


def _threshold_buckets(
    actions: set[str], confidences: list[float], rule_hits: list[str]
) -> list[tuple[str, float]]:
    result: list[tuple[str, float]] = []
    near_threshold = any(0.4 <= value <= 0.6 for value in confidences)
    if near_threshold:
        result.append(("near_threshold", 0.8))
    if actions == {"ALLOW"} and rule_hits:
        result.append(("lexical_model_disagreement", 0.85))
    return result


def _score_buckets(
    scores: list[sqlite3.Row], rule_hits: list[str]
) -> list[tuple[str, float]]:
    if not scores:
        return [("lexical_rule_hit", 0.55)] if rule_hits else []
    actions = {str(row["action"]) for row in scores}
    confidences = [float(row["block_confidence"]) for row in scores]
    result = _named_model_buckets(scores)
    result.extend(_decision_buckets(actions, confidences, len(scores)))
    result.extend(_threshold_buckets(actions, confidences, rule_hits))
    return result


def _message_buckets(
    row: sqlite3.Row,
    scores: list[sqlite3.Row],
    slang_terms: set[str],
) -> list[tuple[str, float]]:
    text = str(row["text"])
    hits = _rule_hits(text, slang_terms)
    result = _score_buckets(scores, hits)
    if int(row["reformulation"]):
        result.append(("repeated_reformulation", 0.75))
    if row["platform"] == "minecraft" and _VIOLENCE.search(text):
        result.append(("gameplay_lexical_hard_negative", 0.7))
    if "server_slang" in hits:
        result.append(("server_slang", 0.65))
    return result


def _ordinary_sample_key(seed: str, message_id: str) -> int:
    return int(stable_hash(seed, message_id)[:16], 16)


def mine_candidates(
    store: MiningStore,
    seed: str,
    ordinary_sample: int = 200,
    slang_terms: set[str] | None = None,
) -> int:
    store.connection.execute("DELETE FROM candidates")
    ordinary: list[tuple[int, str]] = []
    count = 0
    terms = slang_terms or set()
    for row in store.iter_messages(partition="development"):
        scores = store.scores(str(row["message_id"]))
        buckets = _message_buckets(row, scores, terms)
        if buckets:
            values = (
                (str(row["message_id"]), bucket, priority)
                for bucket, priority in buckets
            )
            store.add_candidates(values)
            count += len(buckets)
        elif ordinary_sample > 0:
            _reservoir_push(ordinary, seed, str(row["message_id"]), ordinary_sample)
    store.add_candidates((message_id, "random_ordinary", 0.2) for _, message_id in ordinary)
    store.commit()
    return count + len(ordinary)


def _reservoir_push(
    heap: list[tuple[int, str]], seed: str, message_id: str, limit: int
) -> None:
    key = _ordinary_sample_key(seed, message_id)
    item = (-key, message_id)
    if len(heap) < limit:
        heapq.heappush(heap, item)
        return
    if item > heap[0]:
        heapq.heapreplace(heap, item)


def _reviewed_false_positive(
    store: MiningStore, value: object
) -> tuple[str, str, float] | None:
    if not isinstance(value, dict):
        return None
    adjudication = value.get("adjudication")
    action = adjudication.get("action") if isinstance(adjudication, dict) else value.get("action")
    if action != "ALLOW":
        return None
    message_id = str(value.get("message_id", ""))
    confidence = max(
        (float(row["block_confidence"]) for row in store.scores(message_id)),
        default=0.0,
    )
    if confidence < 0.9 or _message_partition(store, message_id) != "development":
        return None
    return message_id, "reviewed_high_confidence_false_positive", confidence


def add_reviewed_false_positive_candidates(
    store: MiningStore, adjudications: Path
) -> int:
    added = 0
    with adjudications.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            candidate = _reviewed_false_positive(store, json.loads(line))
            if candidate is None:
                continue
            store.add_candidates([candidate])
            added += 1
    store.commit()
    return added


def load_slang_terms(path: Path | None) -> set[str]:
    if path is None:
        return set()
    return {
        normalized_text(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if normalized_text(line)
    }
