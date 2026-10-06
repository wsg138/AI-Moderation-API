"""Group W25 visibility failures without leaking evaluation metadata into models."""

from __future__ import annotations

from collections import Counter

from workers.w12.dataset import ACTION_TO_ID, ModerationExample
from workers.w25.contract import PredictionBundle


def grouped_visibility_failures(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
    *,
    include_text: bool = False,
) -> dict[str, object]:
    bundle.validate()
    failures = _visibility_failures(examples, bundle, include_text)
    groups = Counter(str(item["failure_mode"]) for item in failures)
    return {
        "total": len(failures),
        "group_counts": dict(sorted(groups.items())),
        "examples": failures,
    }


def _visibility_failures(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
    include_text: bool,
) -> list[dict[str, object]]:
    failures = []
    block_id = ACTION_TO_ID["BLOCK"]
    for index, example in enumerate(examples):
        expected = example.action == "BLOCK"
        actual = bundle.predictions["action"][index] == block_id
        if expected == actual:
            continue
        direction = "false_positive" if actual else "false_negative"
        failures.append(_failure_record(example, direction, include_text))
    return failures


def _failure_record(
    example: ModerationExample,
    direction: str,
    include_text: bool,
) -> dict[str, object]:
    record: dict[str, object] = {
        "example_id": example.example_id,
        "family_id": example.family_id,
        "direction": direction,
        "failure_mode": _failure_mode(example, direction),
        "semantic_label": example.label,
        "gold_action": example.action,
        "channel_profile": example.channel_profile,
        "domain": example.domain,
        "reason_codes": list(example.reason_codes),
    }
    if include_text:
        record["serialized"] = example.serialized
    return record


def _failure_mode(example: ModerationExample, direction: str) -> str:
    reasons = " ".join(example.reason_codes).lower()
    domain = example.domain.lower()
    if _has_evasion_reason(reasons):
        return f"{direction}:evasion"
    if _has_quote_reason(reasons):
        return f"{direction}:quotation_or_report"
    if _is_gameplay_domain(domain):
        return f"{direction}:minecraft_context"
    if _is_self_harm(example, domain):
        return f"{direction}:self_harm_context"
    return f"{direction}:{domain or example.label.lower()}"


def _has_evasion_reason(reasons: str) -> bool:
    return "evasion" in reasons or "obfuscat" in reasons


def _has_quote_reason(reasons: str) -> bool:
    return any(token in reasons for token in ("quote", "report", "counter"))


def _is_gameplay_domain(domain: str) -> bool:
    return "minecraft" in domain or "gameplay" in domain


def _is_self_harm(example: ModerationExample, domain: str) -> bool:
    return "self_harm" in domain or "self_harm" in example.label.lower()
