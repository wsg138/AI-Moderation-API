"""Deterministic development attack mutations for W25 robustness testing."""

from __future__ import annotations

import hashlib
import itertools
import re
from collections.abc import Callable
from dataclasses import replace

from workers.w12.dataset import ModerationExample

_LEET = str.maketrans({"a": "4", "e": "3", "i": "1", "o": "0", "s": "5"})
_CONFUSABLES = str.maketrans({"a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х"})
_WORD = re.compile(r"[A-Za-z]{4,}")
_TARGET_MARKER = " [TARGET] "


def attack_variants(text: str) -> dict[str, str]:
    """Return one deterministic variant per attack family without editing the source."""
    return {family: transform(text) for family, transform in _ATTACK_TRANSFORMS.items()}


def attack_serialized_variants(serialized: str) -> dict[str, str]:
    """Mutate only the current target text while preserving serializer structure."""
    return {
        family: _rewrite_target_text(serialized, transform)
        for family, transform in _ATTACK_TRANSFORMS.items()
    }


def mutate_examples(
    examples: list[ModerationExample],
    family: str,
) -> list[ModerationExample]:
    transform = _ATTACK_TRANSFORMS.get(family)
    if transform is None:
        raise ValueError(f"unknown attack family: {family}")
    return [
        replace(
            example,
            serialized=_rewrite_target_text(example.serialized, transform),
        )
        for example in examples
    ]


def augment_training_examples(
    examples: list[ModerationExample],
) -> list[ModerationExample]:
    """Add one deterministic train-only corruption per example."""
    generated = [
        variant
        for example in examples
        if (variant := _training_variant(example)) is not None
    ]
    return [*examples, *generated]


def _training_variant(example: ModerationExample) -> ModerationExample | None:
    start = _family_index(example.example_id)
    for offset in range(len(ATTACK_FAMILIES)):
        family = ATTACK_FAMILIES[(start + offset) % len(ATTACK_FAMILIES)]
        serialized = _rewrite_target_text(
            example.serialized,
            _ATTACK_TRANSFORMS[family],
        )
        if serialized != example.serialized:
            return replace(
                example,
                example_id=f"{example.example_id}::w25-adv::{family}",
                serialized=serialized,
                family_id=example.family_id or example.example_id,
                reason_codes=(
                    *example.reason_codes,
                    "w25_generated_adversarial_training",
                ),
            )
    return None


def _family_index(example_id: str) -> int:
    digest = hashlib.sha256(example_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % len(ATTACK_FAMILIES)


def apply_family(texts: list[str], transform: Callable[[str], str]) -> list[str]:
    return [transform(text) for text in texts]


def _alternating_case(text: str) -> str:
    cycle = itertools.cycle((str.lower, str.upper))
    return "".join(next(cycle)(char) if char.isalpha() else char for char in text)


def _space_word(word: str) -> str:
    return " ".join(word)


def _punctuate_word(word: str) -> str:
    return ".".join(word)


def _repeat_word(word: str) -> str:
    return "".join(char * 2 for char in word)


def _zero_width_word(word: str) -> str:
    return "\u200b".join(word)


def _space_letters(text: str) -> str:
    return _rewrite_first_word(text, _space_word)


def _punctuate(text: str) -> str:
    return _rewrite_first_word(text, _punctuate_word)


def _repeat_letters(text: str) -> str:
    return _rewrite_first_word(text, _repeat_word)


def _single_typo(text: str) -> str:
    def mutate(word: str) -> str:
        if len(word) < 4:
            return word
        chars = list(word)
        chars[1], chars[2] = chars[2], chars[1]
        return "".join(chars)

    return _rewrite_first_word(text, mutate)


def _leetspeak(text: str) -> str:
    return text.translate(_LEET)


def _unicode_confusable(text: str) -> str:
    return text.translate(_CONFUSABLES)


def _zero_width(text: str) -> str:
    return _rewrite_first_word(text, _zero_width_word)


_ATTACK_TRANSFORMS: dict[str, Callable[[str], str]] = {
    "case": _alternating_case,
    "spacing": _space_letters,
    "punctuation": _punctuate,
    "repetition": _repeat_letters,
    "leetspeak": _leetspeak,
    "unicode_confusable": _unicode_confusable,
    "zero_width": _zero_width,
    "keyboard_typo": _single_typo,
}
ATTACK_FAMILIES = tuple(_ATTACK_TRANSFORMS)


def _rewrite_target_text(serialized: str, transform: Callable[[str], str]) -> str:
    lines = serialized.splitlines()
    target_indices = [
        index for index, line in enumerate(lines) if _TARGET_MARKER in line
    ]
    if len(target_indices) != 1:
        raise ValueError("serialized input must contain exactly one target marker")
    index = target_indices[0]
    prefix, text = lines[index].split(_TARGET_MARKER, 1)
    lines[index] = prefix + _TARGET_MARKER + transform(text)
    return "\n".join(lines)


def _rewrite_first_word(text: str, transform: Callable[[str], str]) -> str:
    match = _WORD.search(text)
    if match is None:
        return text
    return text[: match.start()] + transform(match.group()) + text[match.end() :]
