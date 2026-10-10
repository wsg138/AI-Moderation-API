"""Conservative, player-safe reasons for *persisted* moderation blocks.

Only the semantic category determines the short notice. No raw text, model
scores, incident details, private context, or internal rule codes are exposed.
A client must still verify the response is BLOCK before sending a notice.
"""
from __future__ import annotations

CATEGORY = {
    "LOW_LEVEL_HARASSMENT": "possible harassment",
    "SEVERE_HARASSMENT": "harassment",
    "STAFF_TARGETED_ABUSE": "harassment",
    "SLUR_USE": "prohibited language",
    "HATE": "hateful language",
    "REAL_WORLD_THREAT": "a possible real-world threat",
    "DOXXING": "sharing private information",
    "BLACKMAIL": "possible blackmail",
    "GROOMING": "a chat safety concern",
    "SEXUAL_MINOR": "a chat safety concern",
    "SEXUAL_CONTENT": "sexual content",
    "DANGEROUS_REAL_WORLD_INSTRUCTIONS": "a chat safety concern",
    "SELF_HARM_INSTRUCTION": "a chat safety concern",
}


def player_block_notice(
    action: str,
    label: str,
    ingestion_status: str,
    degraded: bool,
) -> str | None:
    """No notice on ALLOW, exempt, fallback, or storage-failure decisions."""
    if action != "BLOCK" or ingestion_status != "INGESTED" or degraded:
        return None
    category = CATEGORY.get(label)
    if category is None:
        return "Your message was blocked by chat moderation. If this seems wrong, contact staff."
    return (
        f"Your message was blocked because it may contain {category}. "
        "If this seems wrong, contact staff."
    )
