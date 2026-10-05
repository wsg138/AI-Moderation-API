from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SEEDS_PATH = ROOT / "data/candidates/W21-seeds.json"
OUTPUT_PATH = ROOT / "data/candidates/W21-adversarial-evasion.jsonl"
LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "g": "9", "l": "1"}
CONFUSABLE = {"a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х", "y": "у", "i": "і"}


def _repeat_middle(token: str) -> str:
    index = max(0, len(token) // 2)
    return token[:index] + token[index] + token[index:]


def _confusable(token: str) -> str:
    for index, char in enumerate(token):
        replacement = CONFUSABLE.get(char.lower())
        if replacement:
            return token[:index] + replacement + token[index + 1 :]
    return token[0] + "\u200b" + token[1:]


def _typo_or_symbol(token: str, seed_id: int) -> str:
    if seed_id % 2 == 0 and len(token) > 3:
        return token[0] + token[2:]
    index = max(1, len(token) // 2)
    return token[:index] + "⚔" + token[index:]


def _mutate(token: str, variant: int, seed_id: int) -> str:
    if variant == 0:
        return token
    if variant == 1:
        return " ".join(token)
    if variant == 2:
        return ("." if seed_id % 2 == 0 else "-").join(token)
    if variant == 3:
        return _repeat_middle(token)
    if variant == 4:
        return "".join(LEET.get(char.lower(), char) for char in token)
    if variant == 5:
        return "/".join(
            char.upper() if index % 2 else char.lower()
            for index, char in enumerate(token)
        )
    if variant == 6:
        return "\u200b".join(token)
    if variant == 7:
        return _confusable(token)
    return _typo_or_symbol(token, seed_id)


def _replace_once(text: str, token: str, replacement: str) -> str:
    index = text.index(token)
    return text[:index] + replacement + text[index + len(token):]


def _blocked_retry(
    seed: dict[str, Any],
    phrase: str,
    messages: list[dict[str, Any]],
    reasons: list[str],
) -> tuple[list[dict[str, Any]], int, list[str]]:
    messages.append({"speaker": "A", "offset_ms": -6000, "text": phrase})
    replacement = _mutate(seed["token"], 6, seed["seed_id"])
    changed = _replace_once(phrase, seed["token"], replacement)
    messages.append({"speaker": "A", "offset_ms": 0, "text": changed})
    if "obfuscated_evasion" not in reasons:
        reasons.append("obfuscated_evasion")
    return messages, len(messages) - 1, reasons


def _allowed_split(
    seed: dict[str, Any],
    phrase: str,
    messages: list[dict[str, Any]],
    reasons: list[str],
) -> tuple[list[dict[str, Any]], int, list[str]]:
    replacement = _mutate(seed["token"], 1, seed["seed_id"])
    changed = _replace_once(phrase, seed["token"], replacement)
    position = changed.index(replacement)
    cut = position + max(1, len(replacement) // 2)
    messages.extend([
        {"speaker": "A", "offset_ms": -450, "text": changed[:cut]},
        {"speaker": "A", "offset_ms": 0, "text": changed[cut:]},
    ])
    reasons.append("split_message_context")
    return messages, len(messages) - 1, reasons


def _single_message(
    seed: dict[str, Any],
    phrase: str,
    variant: int,
    messages: list[dict[str, Any]],
    reasons: list[str],
) -> tuple[list[dict[str, Any]], int, list[str]]:
    replacement = _mutate(seed["token"], variant, seed["seed_id"])
    changed = _replace_once(phrase, seed["token"], replacement)
    messages.append({"speaker": "A", "offset_ms": 0, "text": changed})
    return messages, len(messages) - 1, reasons


def _messages(
    seed: dict[str, Any],
    slot: int,
) -> tuple[list[dict[str, Any]], int, list[str]]:
    phrase = seed["base"] if slot < 10 else seed["alt"]
    variant = slot % 10
    messages = [dict(item) for item in seed["prior"]]
    reasons = list(seed["outcome"]["reason_codes"])
    if variant == 9 and seed["outcome"]["action"] == "BLOCK":
        return _blocked_retry(seed, phrase, messages, reasons)
    if variant == 9:
        return _allowed_split(seed, phrase, messages, reasons)
    return _single_message(seed, phrase, variant, messages, reasons)


def _record(seed: dict[str, Any], slot: int, index: int) -> dict[str, Any]:
    messages, target_index, reasons = _messages(seed, slot)
    outcome = seed["outcome"]
    return {
        "example_id": f"G21-{index:04d}",
        "policy_version": "v1",
        "source": "w21_synthetic_candidate",
        "domain": seed["domain"],
        "difficulty": "adversarial",
        "platform_hint": seed["platform_hint"],
        "channel_profile": seed["channel_profile"],
        "messages": messages,
        "target_index": target_index,
        "label": outcome["label"],
        "action": outcome["action"],
        "review_priority": outcome["review_priority"],
        "strike": outcome["strike"],
        "containment": outcome["containment"],
        "containment_duration_seconds": outcome["containment_duration_seconds"],
        "support_flow": outcome["support_flow"],
        "reason_codes": reasons,
        "notes": (
            f"W21 candidate seed {seed['seed_id']}; slot {slot}. "
            "Candidate-only, not admitted to frozen training."
        ),
        "family_id": f"w21.{seed['domain']}.{seed['seed_id']:03d}",
    }


def build_records() -> list[dict[str, Any]]:
    seeds = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))["seeds"]
    records: list[dict[str, Any]] = []
    index = 1
    for seed in seeds:
        for slot in range(20):
            records.append(_record(seed, slot, index))
            index += 1
    return records


def render_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    )


def main() -> int:
    records = build_records()
    if len(records) != 500:
        raise ValueError(f"expected 500 records, found {len(records)}")
    OUTPUT_PATH.write_text(render_jsonl(records), encoding="utf-8")
    print(f"wrote {len(records)} records to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
