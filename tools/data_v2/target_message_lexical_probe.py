"""Offline, target-only lexical message-visibility contract.

Requires a caller-provided, separately reviewed literal vocabulary. No
restricted vocabulary, real player messages, model weights, or production
moderation hooks are committed here. Exact matches do not authorize blame.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import islice

MODERATED = frozenset({
    "minecraft_public", "minecraft_private", "discord_general", "discord_gaming",
})
MAX_TARGET = 8192
MAX_TERMS = 128


@dataclass(frozen=True)
class LexicalProbe:
    outcome: str
    target_matched: bool
    reporter_culpability_inferred: bool = False
    strike_authorized: bool = False
    mute_authorized: bool = False
    staff_alert_authorized: bool = False
    runtime_enabled: bool = False
    training_eligible: bool = False


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def _validate_term(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError("invalid term type")
    if not 2 <= len(raw) <= 64 or raw.strip() != raw:
        raise ValueError("invalid literal term length")
    return _normalize(raw)


def _checked_terms(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValueError("terms must be an iterable of literal strings")
    result = tuple(islice(values, MAX_TERMS + 1))
    if not 1 <= len(result) <= MAX_TERMS:
        raise ValueError("unbounded or empty term list")
    normalized = tuple(_validate_term(term) for term in result)
    if len(normalized) != len(set(normalized)):
        raise ValueError("duplicate normalized term")
    return normalized


def propose_target_visibility(
    channel_profile: str, target_text: str, literal_terms: Iterable[str],
) -> LexicalProbe:
    """BLOCK proposal on a current-target lexical hit; otherwise ABSTAIN.

    The method does NOT search previous messages, issue punishments, or
    decide whether the user reporting an expression was the original author.
    """
    tokens = _checked_terms(literal_terms)
    if not isinstance(target_text, str) or len(target_text) > MAX_TARGET:
        raise ValueError("invalid bounded target message")
    if channel_profile not in MODERATED:
        return LexicalProbe("ABSTAIN", False)
    target = _normalize(target_text)
    for token in tokens:
        pattern = r"(?<!\w)" + re.escape(token) + r"(?!\w)"
        if re.search(pattern, target):
            return LexicalProbe("BLOCK", True)
    return LexicalProbe("ABSTAIN", False)
