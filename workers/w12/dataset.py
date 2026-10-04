"""W12 dataset loading and leakage-safe input serialization.

Consumes the accepted W11 integration manifests. Training may use only W11
train IDs. Validation is the only tuning partition. Test / frozen adversarial /
owner golden are acceptance-only and must never be used for fitting,
calibration, threshold selection, or candidate choice.

Only runtime-realizable fields are serialized. Evaluation metadata such as
reason codes, difficulty, example IDs, and family IDs is retained separately
for slice reporting and never enters model input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from moderation_api.model_serialization import ModelMessage, serialize_model_input

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
INTEGRATION_DIR = DATA_DIR / "integration"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
EVAL_DIR = DATA_DIR / "eval"

LABELS = [
    "SAFE",
    "GAMEPLAY_VIOLENCE",
    "LOW_LEVEL_HARASSMENT",
    "SEVERE_HARASSMENT",
    "STAFF_TARGETED_ABUSE",
    "REAL_WORLD_THREAT",
    "SELF_HARM_INSTRUCTION",
    "SELF_HARM_INTENT",
    "THIRD_PARTY_SELF_HARM_CONCERN",
    "HATE",
    "SLUR_USE",
    "SEXUAL_CONTENT",
    "SEXUAL_MINOR",
    "DOXXING",
    "BLACKMAIL",
    "GROOMING",
    "DANGEROUS_REAL_WORLD_INSTRUCTIONS",
    "AMBIGUOUS_REVIEW",
]
LABEL_TO_ID = {name: i for i, name in enumerate(LABELS)}

ACTIONS = ["ALLOW", "BLOCK", "REVIEW"]
ACTION_TO_ID = {name: i for i, name in enumerate(ACTIONS)}

REVIEW_PRIORITIES = ["NONE", "NORMAL", "URGENT"]
REVIEW_TO_ID = {name: i for i, name in enumerate(REVIEW_PRIORITIES)}

CONTAINMENTS = ["NONE", "MUTE"]
CONTAINMENT_TO_ID = {name: i for i, name in enumerate(CONTAINMENTS)}

SUPPORT_FLOWS = ["NONE", "SELF_HARM_CHECK", "TARGET_SAFETY_CHECK"]
SUPPORT_TO_ID = {name: i for i, name in enumerate(SUPPORT_FLOWS)}

RUNTIME_BLOCK_ID = 1
RUNTIME_ALLOW_ID = 0


@dataclass(frozen=True)
class ModerationExample:
    example_id: str
    serialized: str
    label: str
    action: str
    review_priority: str
    strike: bool
    containment: str
    containment_duration_seconds: int | None
    support_flow: str
    channel_profile: str
    platform_hint: str
    domain: str
    difficulty: str
    reason_codes: tuple[str, ...]
    family_id: str | None


def serialize_messages(channel_profile: str, messages: list[dict], target_index: int) -> str:
    """Serialize runtime fields only, using the shared canonical W12 contract."""
    model_messages = [
        ModelMessage(
            speaker_key=str(message.get("speaker", "?")),
            offset_ms=int(message.get("offset_ms", 0)),
            text=str(message.get("text", "")),
        )
        for message in messages
    ]
    return serialize_model_input(channel_profile, model_messages, target_index)


def _record_to_example(record: dict, family_id: str | None = None) -> ModerationExample:
    return ModerationExample(
        example_id=record["example_id"],
        serialized=serialize_messages(
            record["channel_profile"], record["messages"], int(record["target_index"])
        ),
        label=record["label"],
        action=record["action"],
        review_priority=record["review_priority"],
        strike=bool(record["strike"]),
        containment=record["containment"],
        containment_duration_seconds=record.get("containment_duration_seconds"),
        support_flow=record["support_flow"],
        channel_profile=record["channel_profile"],
        platform_hint=record.get("platform_hint", ""),
        domain=record.get("domain", ""),
        difficulty=record.get("difficulty", ""),
        reason_codes=tuple(record.get("reason_codes", ())),
        family_id=family_id or record.get("family_id"),
    )


def is_fully_labeled(record: dict) -> bool:
    """Check whether all classifier dimensions have owner/source labels."""
    return all(
        record.get(key) is not None
        for key in ("label", "action", "review_priority", "containment", "support_flow", "strike")
    )


def load_split_manifest() -> dict:
    with open(INTEGRATION_DIR / "W11-split-manifest.json") as handle:
        return json.load(handle)


def load_adversarial_manifest() -> dict:
    with open(INTEGRATION_DIR / "W11-adversarial-eval-manifest.json") as handle:
        return json.load(handle)


def _family_map(manifest: dict) -> dict[str, str]:
    return {
        example_id: group["group_id"]
        for group in manifest.get("groups", [])
        for example_id in group["example_ids"]
    }


def load_records_by_id() -> dict[str, dict]:
    """Load all accepted synthetic records indexed by example_id."""
    records: dict[str, dict] = {}
    for path in sorted(SYNTHETIC_DIR.glob("*.jsonl")):
        with open(path) as handle:
            for line in handle:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    records[record["example_id"]] = record
    return records


def _partition_ids(partition: str, manifest: dict) -> list[str]:
    if partition == "frozen_adversarial":
        adversarial = load_adversarial_manifest()
        return list(adversarial.get("example_ids", adversarial.get("frozen_adversarial", [])))
    partitions = manifest.get("partitions", {})
    if partition not in partitions:
        raise ValueError(f"unknown W11 partition: {partition}")
    return list(partitions[partition])


def load_partition(
    partition: str, records_by_id: dict[str, dict] | None = None
) -> list[ModerationExample]:
    """Load one accepted W11 partition without changing membership or families."""
    manifest = load_split_manifest()
    ids = _partition_ids(partition, manifest)
    if records_by_id is None:
        records_by_id = load_records_by_id()
    families = _family_map(manifest)
    examples = []
    for example_id in ids:
        record = records_by_id.get(example_id)
        if record is None:
            raise KeyError(f"W11 manifest references unknown example {example_id}")
        examples.append(_record_to_example(record, families.get(example_id)))
    return examples


def load_owner_golden() -> list[dict]:
    """Load owner golden fixtures (acceptance only — never train on these)."""
    path = EVAL_DIR / "owner-policy-v1.jsonl"
    records = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def assert_no_leakage(train_ids: set[str], *other_id_sets: set[str]) -> None:
    for other in other_id_sets:
        overlap = train_ids & other
        if overlap:
            raise AssertionError(
                f"Leakage: {len(overlap)} IDs shared between train and held-out "
                f"(e.g. {sorted(overlap)[:5]})"
            )
