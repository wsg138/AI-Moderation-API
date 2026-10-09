"""Offline exact-token visibility proposal; not a production hook.

A coordinator explicitly supplies the narrowly scoped policy token. This
utility cannot issue moderation sanctions or operate a deployed service.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MODERATED = frozenset({
    "minecraft_public", "minecraft_private", "discord_general", "discord_gaming"
})


@dataclass(frozen=True)
class VisibilityProbe:
    original_action: str
    proposed_action: str
    visibility_override: bool
    punitive_action_authorized: bool = False
    live_enforcement_authorized: bool = False


def propose_visibility(
    channel_profile: str, target_text: str, model_action: str,
    policy_token: str,
) -> VisibilityProbe:
    """Propose message visibility only for an exact supplied policy token."""
    if model_action not in {"ALLOW", "BLOCK", "REVIEW"}:
        raise ValueError("unsupported offline action")
    if not re.fullmatch(r"[a-z]{2,16}", policy_token):
        raise ValueError("invalid coordinator policy token")
    if channel_profile not in MODERATED:
        return VisibilityProbe(model_action, model_action, False)
    if not isinstance(target_text, str) or len(target_text) > 8192:
        raise ValueError("invalid bounded target text")
    exact_token = re.compile(
        r"(?<!\w)" + re.escape(policy_token) + r"(?!\w)", re.IGNORECASE
    )
    if exact_token.search(target_text):
        return VisibilityProbe(model_action, "BLOCK", model_action != "BLOCK")
    return VisibilityProbe(model_action, model_action, False)
