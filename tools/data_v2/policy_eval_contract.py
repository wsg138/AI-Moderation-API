"""Offline Policy-v1 fact-to-decision sketch; never imported by the live service.

Only policy-settled fields are populated. None means NOT DECIDED, not "no".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Kind = Literal[
    "safe", "gameplay_violence", "threat", "blackmail", "actual_slur",
    "slur_reference", "directed_self_harm", "directed_death_wish",
    "self_harm_disclosure", "third_party_concern", "staff_abuse",
    "sexual_minor", "grooming",
]
Scope = Literal["game_only", "irl", "unclear"]
Channel = Literal["minecraft_public", "minecraft_private", "discord_general", "discord_gaming"]


@dataclass(frozen=True)
class SemanticFacts:
    kind: Kind
    scope: Scope
    channel: Channel
    reliable_minor_evidence: bool = False
    quoted_or_reported: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    semantic_label: str
    action: Literal["ALLOW", "REVIEW", "BLOCK"]
    review_priority: str | None
    strike: bool | None
    containment: str | None
    containment_duration_seconds: int | None
    support_flow: str | None
    status: Literal["RESOLVED", "PARTIAL", "UNRESOLVED"]
    policy_section: str
    unresolved: str | None = None


def _decision(
    label: str, action: Literal["ALLOW", "REVIEW", "BLOCK"],
    section: str, *, strike: bool | None = None,
    review: str | None = None, containment: str | None = None,
    support: str | None = None, status: Literal["RESOLVED", "PARTIAL"] = "PARTIAL",
    unresolved: str | None = None,
) -> PolicyDecision:
    return PolicyDecision(label, action, review, strike, containment, None,
                          support, status, section, unresolved)


def _allow(label: str, section: str) -> PolicyDecision:
    return _decision(label, "ALLOW", section, strike=False, review="NONE",
                     containment="NONE", support="NONE", status="RESOLVED")


def _unresolved(section: str, reason: str) -> PolicyDecision:
    return PolicyDecision("AMBIGUOUS_REVIEW", "REVIEW", "NORMAL", None,
                          None, None, None, "UNRESOLVED", section, reason)


def _threat(facts: SemanticFacts) -> PolicyDecision:
    if facts.scope == "irl":
        return _decision("REAL_WORLD_THREAT", "BLOCK", "§6",
                         unresolved="Strike/containment depend on credible severity and context")
    if facts.scope == "game_only" or facts.channel.startswith("minecraft_"):
        return _allow("GAMEPLAY_VIOLENCE", "§6")
    return _decision("REAL_WORLD_THREAT", "BLOCK", "§6", strike=False,
                     unresolved="Discord-general generic threat: no automatic strike")


def _blackmail(facts: SemanticFacts) -> PolicyDecision:
    if facts.scope == "game_only" and facts.channel.startswith("minecraft_"):
        return _allow("SAFE", "§12 + owner 2026-10-08 ruling")
    if facts.scope == "irl":
        return _decision("BLACKMAIL", "BLOCK", "§12", review="URGENT",
                         containment="MUTE",
                         unresolved="Mute duration and strike remain unspecified; appeal required")
    return _unresolved("§12", "Game-only vs IRL blackmail scope not established")


def resolve(facts: SemanticFacts) -> PolicyDecision:
    """Pure offline policy probe; not a complete enforcement resolver."""
    if facts.kind == "safe":
        return _allow("SAFE", "§2")
    if facts.kind == "gameplay_violence":
        return _allow("GAMEPLAY_VIOLENCE", "§6")
    if facts.kind == "threat":
        return _threat(facts)
    if facts.kind == "blackmail":
        return _blackmail(facts)
    if facts.kind == "slur_reference":
        return _allow("SAFE", "§10")
    if facts.kind == "actual_slur":
        return _decision("SLUR_USE", "BLOCK", "§10", strike=True,
                         unresolved="Review and containment depend on severity")
    if facts.kind in {"directed_self_harm", "staff_abuse"}:
        label = (
            "SELF_HARM_INSTRUCTION"
            if facts.kind == "directed_self_harm"
            else "STAFF_TARGETED_ABUSE"
        )
        return _decision(label, "BLOCK", "§9" if facts.kind == "directed_self_harm" else "§8",
                         strike=True)
    return _resolve_remaining(facts)


def _grooming(facts: SemanticFacts) -> PolicyDecision:
    if facts.reliable_minor_evidence:
        return _decision("GROOMING", "BLOCK", "§12", review="URGENT",
                         unresolved="Strike and mute duration are not frozen")
    return _unresolved("§11–12", "Minor reliability / grooming thresholds unresolved")


def _resolve_remaining(facts: SemanticFacts) -> PolicyDecision:
    if facts.kind == "directed_death_wish":
        if facts.scope == "game_only":
            return _allow("GAMEPLAY_VIOLENCE", "§9")
        return _decision("SELF_HARM_INSTRUCTION", "BLOCK", "§9",
                         strike=facts.scope == "irl",
                         review="NORMAL" if facts.scope == "unclear" else None)
    if facts.kind in {"self_harm_disclosure", "third_party_concern"}:
        label = ("SELF_HARM_INTENT" if facts.kind == "self_harm_disclosure"
                 else "THIRD_PARTY_SELF_HARM_CONCERN")
        return _decision(label, "ALLOW", "§9", strike=False,
                         support="SELF_HARM_CHECK",
                         unresolved="Staff urgency depends on subsequent safety response")
    if facts.kind == "sexual_minor":
        if not facts.reliable_minor_evidence:
            return _unresolved("§11", "Self-reported/uncertain age cannot establish minor status")
        return _decision("SEXUAL_MINOR", "BLOCK", "§11", strike=True)
    if facts.kind == "grooming":
        return _grooming(facts)
    raise ValueError(f"Unknown fact kind: {facts.kind!r}")
