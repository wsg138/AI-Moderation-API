"""W12 dataset loading and leakage-safe input serialization.

Consumes the accepted W11 integration manifests. Training may use only W11
train IDs. Validation is the only tuning partition. Test / frozen adversarial /
owner golden are acceptance-only and must never be used for fitting,
calibration, threshold selection, or candidate choice.

The serializer exposes ONLY legitimate runtime information:
- channel profile
- ordered message sequence with speaker boundaries
- target (current) message marker
- relative timing offsets

It MUST NOT expose answer/editorial metadata (labels, actions, notes,
reason codes, domain, difficulty, example IDs, family IDs, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
INTEGRATION_DIR = DATA_DIR / "integration"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
EVAL_DIR = DATA_DIR / "eval"

# ---------------------------------------------------------------------------
# Label vocabularies (must match service/moderation_api/models.py Label enum)
# ---------------------------------------------------------------------------

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

# Runtime binary visibility: dataset BLOCK -> runtime BLOCK,
# dataset ALLOW/REVIEW -> runtime ALLOW.
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
    # Slice metadata (NOT serialized to model input; used for evaluation only)
    channel_profile: str
    platform_hint: str
    domain: str


def serialize_messages(channel_profile: str, messages: list[dict], target_index: int) -> str:
    """Leakage-safe serialization of a message sequence.

    Only structural/runtime information is emitted. Never call this with
    label/action/notes/reason/domain/difficulty/example_id fields.
    """
    parts = [f"[PROFILE={channel_profile}]"]
    for i, msg in enumerate(messages):
        speaker = str(msg.get("speaker", "?"))
        offset = int(msg.get("offset_ms", 0))
        text = str(msg.get("text", ""))
        marker = " [TARGET]" if i == target_index else ""
        parts.append(f"[{speaker}@+{offset}ms]{marker} {text}")
    return "\n".join(parts)


def _record_to_example(record: dict) -> ModerationExample:
    messages = record["messages"]
    target_index = int(record["target_index"])
    return ModerationExample(
        example_id=record["example_id"],
        serialized=serialize_messages(
            record["channel_profile"], messages, target_index
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
    )


def is_fully_labeled(record: dict) -> bool:
    """Check if a record has all classifier dimensions specified."""
    return all(
        record.get(k) is not None
        for k in ("label", "action", "review_priority", "containment", "support_flow")
    )


def load_split_manifest() -> dict:
    with open(INTEGRATION_DIR / "W11-split-manifest.json") as f:
        return json.load(f)


def load_adversarial_manifest() -> dict:
    with open(INTEGRATION_DIR / "W11-adversarial-eval-manifest.json") as f:
        return json.load(f)


def load_records_by_id() -> dict[str, dict]:
    """Load all synthetic records indexed by example_id."""
    records: dict[str, dict] = {}
    for path in sorted(SYNTHETIC_DIR.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                records[record["example_id"]] = record
    return records


def load_partition(
    partition: str, records_by_id: dict[str, dict] | None = None
) -> list[ModerationExample]:
    """Load one W11 partition. partition in {train, validation, test, frozen_adversarial}."""
    manifest = load_split_manifest()
    if partition == "frozen_adversarial":
        manifest = load_adversarial_manifest()
        ids = manifest.get("example_ids", manifest.get("frozen_adversarial", []))
    else:
        ids = manifest["partitions"][partition]
    if records_by_id is None:
        records_by_id = load_records_by_id()
    examples = []
    for example_id in ids:
        record = records_by_id.get(example_id)
        if record is None:
            raise KeyError(f"W11 manifest references unknown example {example_id}")
        examples.append(_record_to_example(record))
    return examples


def load_owner_golden() -> list[dict]:
    """Load owner golden fixtures (acceptance only — never train on these)."""
    path = EVAL_DIR / "owner-policy-v1.jsonl"
    records = []
    with open(path) as f:
        for line in f:
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
