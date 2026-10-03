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
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("vectorizer metadata must be an object")
        raw_terms = parsed.get("terms")
        raw_idf = parsed.get("idf")
        raw_ngram = parsed.get("ngram_range")
        if not isinstance(raw_terms, list) or not raw_terms:
            raise ValueError("vectorizer terms are missing")
        if not all(isinstance(term, str) and term for term in raw_terms):
            raise ValueError("vectorizer terms are invalid")
        if not isinstance(raw_idf, list) or len(raw_idf) != len(raw_terms):
            raise ValueError("vectorizer idf is invalid")
        if not all(isinstance(value, (int, float)) for value in raw_idf):
            raise ValueError("vectorizer idf values are invalid")
        if (
            not isinstance(raw_ngram, list)
            or len(raw_ngram) != 2
            or not all(isinstance(value, int) for value in raw_ngram)
        ):
            raise ValueError("vectorizer ngram_range is invalid")
        ngram_min, ngram_max = raw_ngram
        if ngram_min < 1 or ngram_max < ngram_min:
            raise ValueError("vectorizer ngram_range is invalid")
        norm = parsed.get("norm")
        if norm != "l2":
            raise ValueError("only l2 TF-IDF normalization is supported")
        terms = tuple(raw_terms)
        return cls(
            terms=terms,
            idf=tuple(float(value) for value in raw_idf),
            lowercase=parsed.get("lowercase") is True,
            ngram_min=ngram_min,
            ngram_max=ngram_max,
            sublinear_tf=parsed.get("sublinear_tf") is True,
            norm=norm,
            _vocabulary={term: index for index, term in enumerate(terms)},
        )

    @property
    def feature_count(self) -> int:
        return len(self.terms)

    def transform(self, text: str, np: Any) -> Any:
        normalized = text.lower() if self.lowercase else text
        tokens = _TOKEN_PATTERN.findall(normalized)
        counts: Counter[str] = Counter()
        for size in range(self.ngram_min, self.ngram_max + 1):
            if size > len(tokens):
                break
            for start in range(0, len(tokens) - size + 1):
                counts[" ".join(tokens[start : start + size])] += 1

        row = np.zeros((1, self.feature_count), dtype=np.float32)
        squared_sum = 0.0
        for term, count in counts.items():
            index = self._vocabulary.get(term)
            if index is None:
                continue
            tf = 1.0 + math.log(count) if self.sublinear_tf else float(count)
            value = tf * self.idf[index]
            row[0, index] = value
            squared_sum += value * value

        if squared_sum > 0.0:
            row /= math.sqrt(squared_sum)
        return row
