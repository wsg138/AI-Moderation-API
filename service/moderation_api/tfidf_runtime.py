"""Minimal safe runtime implementation of the frozen W12 TF-IDF transform."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")


def _read_object(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("vectorizer metadata must be an object")
    return parsed


def _terms(parsed: dict[str, Any]) -> tuple[str, ...]:
    raw = parsed.get("terms")
    if not isinstance(raw, list) or not raw:
        raise ValueError("vectorizer terms are missing")
    if not all(isinstance(term, str) and term for term in raw):
        raise ValueError("vectorizer terms are invalid")
    return tuple(raw)


def _idf(parsed: dict[str, Any], size: int) -> tuple[float, ...]:
    raw = parsed.get("idf")
    if not isinstance(raw, list) or len(raw) != size:
        raise ValueError("vectorizer idf is invalid")
    if not all(isinstance(value, (int, float)) for value in raw):
        raise ValueError("vectorizer idf values are invalid")
    return tuple(float(value) for value in raw)


def _ngram_range(parsed: dict[str, Any]) -> tuple[int, int]:
    raw = parsed.get("ngram_range")
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError("vectorizer ngram_range is invalid")
    if not all(isinstance(value, int) for value in raw):
        raise ValueError("vectorizer ngram_range is invalid")
    minimum, maximum = raw
    if minimum < 1 or maximum < minimum:
        raise ValueError("vectorizer ngram_range is invalid")
    return minimum, maximum


def _require_l2(parsed: dict[str, Any]) -> str:
    norm = parsed.get("norm")
    if norm != "l2":
        raise ValueError("only l2 TF-IDF normalization is supported")
    return norm


@dataclass(frozen=True, slots=True)
class TfidfRuntimeVectorizer:
    """Reproduces the selected sklearn TfidfVectorizer without sklearn/pickle."""

    terms: tuple[str, ...]
    idf: tuple[float, ...]
    lowercase: bool
    ngram_min: int
    ngram_max: int
    sublinear_tf: bool
    norm: str
    _vocabulary: dict[str, int]

    @classmethod
    def from_file(cls, path: Path) -> TfidfRuntimeVectorizer:
        parsed = _read_object(path)
        terms = _terms(parsed)
        ngram_min, ngram_max = _ngram_range(parsed)
        return cls(
            terms=terms,
            idf=_idf(parsed, len(terms)),
            lowercase=parsed.get("lowercase") is True,
            ngram_min=ngram_min,
            ngram_max=ngram_max,
            sublinear_tf=parsed.get("sublinear_tf") is True,
            norm=_require_l2(parsed),
            _vocabulary={term: index for index, term in enumerate(terms)},
        )

    @property
    def feature_count(self) -> int:
        return len(self.terms)

    def transform(self, text: str, np: Any) -> Any:
        tokens = _TOKEN_PATTERN.findall(text.lower() if self.lowercase else text)
        counts = self._count_ngrams(tokens)
        row = np.zeros((1, self.feature_count), dtype=np.float32)
        squared_sum = self._fill_row(row, counts)
        if squared_sum > 0.0:
            row /= math.sqrt(squared_sum)
        return row

    def _count_ngrams(self, tokens: list[str]) -> Counter[str]:
        counts: Counter[str] = Counter()
        for size in range(self.ngram_min, self.ngram_max + 1):
            for start in range(0, max(0, len(tokens) - size + 1)):
                counts[" ".join(tokens[start : start + size])] += 1
        return counts

    def _fill_row(self, row: Any, counts: Counter[str]) -> float:
        squared_sum = 0.0
        for term, count in counts.items():
            index = self._vocabulary.get(term)
            if index is None:
                continue
            tf = 1.0 + math.log(count) if self.sublinear_tf else float(count)
            value = tf * self.idf[index]
            row[0, index] = value
            squared_sum += value * value
        return squared_sum
