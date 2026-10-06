"""Development-only train-derived evasion probes for W23."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import replace

from workers.w12.dataset import ModerationExample
from workers.w23.config import EVASION_SAMPLE_SIZE

_MESSAGE = re.compile(r"^(\[[^\]]+ms\](?: \[TARGET\])? )(.*)$")
_WORD = re.compile(r"\b[A-Za-z]{5,}\b")
_LEET = str.maketrans({"a": "4", "e": "3", "i": "1", "o": "0", "s": "5"})


def deterministic_probe_sample(
    examples: list[ModerationExample],
    size: int = EVASION_SAMPLE_SIZE,
) -> list[ModerationExample]:
    ranked = sorted(
        examples,
        key=lambda item: hashlib.sha256(item.example_id.encode("utf-8")).digest(),
    )
    return ranked[: min(size, len(ranked))]


def _first_word(text: str, transform: Callable[[str], str]) -> str:
    return _WORD.sub(lambda match: transform(match.group(0)), text, count=1)


def _spacing(word: str) -> str:
    return " ".join(word)


def _punctuation(word: str) -> str:
    return ".".join(word)


def _alternating_case(word: str) -> str:
    return "".join(char.upper() if index % 2 else char.lower() for index, char in enumerate(word))


def _misspelling(word: str) -> str:
    chars = list(word)
    chars[1], chars[2] = chars[2], chars[1]
    return "".join(chars)


def _confusable(word: str) -> str:
    return word.lower().translate(_LEET)


def _repeat(word: str) -> str:
    return word[0] + word[1] * 3 + word[2:]


def _fullwidth(word: str) -> str:
    return "".join(chr(ord(char) + 0xFEE0) if "!" <= char <= "~" else char for char in word)


TRANSFORMS: dict[str, Callable[[str], str]] = {
    "spacing": _spacing,
    "punctuation_insertion": _punctuation,
    "casing": _alternating_case,
    "benign_misspelling": _misspelling,
    "visual_substitution": _confusable,
    "repeated_letters": _repeat,
    "unicode_width_variant": _fullwidth,
}


def perturb_serialized(serialized: str, transform_name: str) -> str:
    transform = TRANSFORMS[transform_name]
    output = []
    for line in serialized.splitlines():
        match = _MESSAGE.match(line)
        if match is None:
            output.append(line)
            continue
        prefix, message = match.groups()
        output.append(prefix + _first_word(message, transform))
    return "\n".join(output)


def build_probe_set(
    examples: list[ModerationExample],
    transform_name: str,
    *,
    size: int = EVASION_SAMPLE_SIZE,
) -> list[ModerationExample]:
    sampled = deterministic_probe_sample(examples, size)
    return [
        replace(item, serialized=perturb_serialized(item.serialized, transform_name))
        for item in sampled
    ]


def all_probe_sets(
    examples: list[ModerationExample],
    *,
    size: int = EVASION_SAMPLE_SIZE,
) -> dict[str, list[ModerationExample]]:
    return {name: build_probe_set(examples, name, size=size) for name in TRANSFORMS}
