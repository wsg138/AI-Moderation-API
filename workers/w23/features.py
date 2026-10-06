"""Runtime-realizable meta features for W23.

No example IDs, family IDs, reason codes, difficulty labels, or editorial fields
are admitted here.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np  # pyright: ignore[reportMissingImports]

from workers.w12.dataset import ModerationExample

_REPEATED = re.compile(r"(.)\1{2,}")
_TOKEN = re.compile(r"\w+")


@dataclass(frozen=True)
class RuntimeFeatureEncoder:
    channels: tuple[str, ...]

    @classmethod
    def fit(cls, examples: list[ModerationExample]) -> RuntimeFeatureEncoder:
        return cls(channels=tuple(sorted({item.channel_profile for item in examples})))

    def transform(self, examples: list[ModerationExample]) -> np.ndarray:
        rows = [self._row(item) for item in examples]
        return np.asarray(rows, dtype=np.float64)

    def _row(self, item: ModerationExample) -> list[float]:
        scalar = _text_features(item.serialized)
        channel = [1.0 if item.channel_profile == name else 0.0 for name in self.channels]
        unknown = float(item.channel_profile not in self.channels)
        return scalar + channel + [unknown]


def _text_features(text: str) -> list[float]:
    length = max(len(text), 1)
    tokens = _TOKEN.findall(text)
    messages = text.count("ms]")
    uppercase = sum(char.isupper() for char in text)
    digits = sum(char.isdigit() for char in text)
    punctuation = sum(not char.isalnum() and not char.isspace() for char in text)
    non_ascii = sum(ord(char) > 127 for char in text)
    whitespace = sum(char.isspace() for char in text)
    return [
        math.log1p(length),
        math.log1p(len(tokens)),
        float(messages),
        float(max(messages - 1, 0)),
        uppercase / length,
        digits / length,
        punctuation / length,
        non_ascii / length,
        whitespace / length,
        float(bool(_REPEATED.search(text))),
        float(max((len(token) for token in tokens), default=0)),
    ]
