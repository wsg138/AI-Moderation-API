"""Leakage-safe W25 data admission and deterministic group partitioning."""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workers.w12.dataset import ModerationExample, load_partition, serialize_messages
from workers.w25.attacks import augment_training_examples
from workers.w25.config import W20_MARKERS

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADMISSIONS = Path(__file__).resolve().parent / "admissions.json"
TRAINING_ROLES = {"training", "adversarial_training", "real_chat_training"}


@dataclass(frozen=True)
class AdmittedSource:
    path: str
    sha256: str
    role: str
    reviewed_by: str
    frozen_group_field: str
    storage: str = "repo"
    partition_manifest: str | None = None
    partition_manifest_sha256: str | None = None
    partition_manifest_storage: str | None = None


def normalize_text(text: str) -> str:
    """Normalize only for the parallel normalized view; raw text remains preserved."""
    normalized = unicodedata.normalize("NFKC", text)
    visible = "".join(char for char in normalized if unicodedata.category(char) != "Cf")
    return " ".join(visible.split())


def serialize_variant(serialized: str, variant: str) -> str:
    if variant == "raw":
        return serialized
    if variant == "raw+normalized":
        return f"RAW:\n{serialized}\nNORMALIZED:\n{normalize_text(serialized)}"
    raise ValueError(f"unknown serialization variant: {variant}")


def load_w11_development() -> tuple[list[ModerationExample], list[ModerationExample]]:
    """Return only W11 train + validation; never acceptance/test partitions."""
    return load_partition("train"), load_partition("validation")


def admissions_payload(path: Path = DEFAULT_ADMISSIONS) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported W25 admission manifest")
    return payload


def load_admissions(path: Path = DEFAULT_ADMISSIONS) -> tuple[AdmittedSource, ...]:
    payload = admissions_payload(path)
    return tuple(AdmittedSource(**item) for item in payload.get("sources", []))


def load_development_data(
    *,
    include_admitted: bool,
    adversarial_augment: bool = False,
) -> tuple[list[ModerationExample], list[ModerationExample]]:
    train, development = load_w11_development()
    if not include_admitted:
        return _maybe_augment_train(train, adversarial_augment), development
    payload = admissions_payload()
    if payload.get("status") != "ready":
        raise RuntimeError("W25 admitted development data is not frozen/ready")
    train.extend(load_admitted_partition("train"))
    development.extend(load_admitted_partition("development"))
    return _maybe_augment_train(train, adversarial_augment), development


def _maybe_augment_train(
    train: list[ModerationExample],
    enabled: bool,
) -> list[ModerationExample]:
    return augment_training_examples(train) if enabled else train


def load_admitted_partition(partition: str) -> list[ModerationExample]:
    examples = []
    for source in load_admissions():
        if source.role not in TRAINING_ROLES:
            continue
        examples.extend(load_source_partition(source.path, partition))
    return examples


def load_source_partition(source_path: str, partition: str) -> list[ModerationExample]:
    source = _find_admitted_source(source_path)
    records, manifest = _load_verified_source(source)
    return _examples_for_partition(records, manifest, partition, source)


def _find_admitted_source(source_path: str) -> AdmittedSource:
    matches = [source for source in load_admissions() if source.path == source_path]
    if len(matches) != 1:
        raise ValueError(f"expected one admitted source for {source_path}, found {len(matches)}")
    return matches[0]


def verify_admitted_source(source: AdmittedSource) -> Path:
    source_path = _verified_source_file(source.path, source.sha256, source.storage)
    if not source.reviewed_by.strip():
        raise ValueError("admitted source must name a reviewer")
    if not source.frozen_group_field.strip():
        raise ValueError("admitted source must define its frozen group field")
    if (
        source.role in TRAINING_ROLES
        or source.partition_manifest is not None
        or source.partition_manifest_sha256 is not None
    ):
        _verified_partition_manifest(source)
    return source_path


def verify_all_admissions(path: Path = DEFAULT_ADMISSIONS) -> tuple[Path, ...]:
    return tuple(verify_admitted_source(source) for source in load_admissions(path))


def freeze_group_partitions(
    records: Sequence[Mapping[str, object]],
    *,
    group_field: str,
    seed: str = "w25-group-freeze-v1",
) -> dict[str, list[str]]:
    groups = _group_records(records, group_field)
    partitions = {"train": [], "development": [], "test": []}
    for group, example_ids in sorted(groups.items()):
        bucket = _bucket(group, seed)
        partition = "train" if bucket < 0.70 else "development" if bucket < 0.85 else "test"
        partitions[partition].extend(example_ids)
    return {name: sorted(values) for name, values in partitions.items()}


def assert_group_isolation(
    records: Sequence[Mapping[str, object]],
    manifest: dict[str, list[str]],
    *,
    group_field: str,
) -> None:
    owner = {example_id: name for name, ids in manifest.items() for example_id in ids}
    group_partitions: dict[str, set[str]] = {}
    for record in records:
        group = str(record[group_field])
        partition = owner.get(str(record["example_id"]))
        if partition is None:
            raise ValueError("partition manifest omitted an example")
        group_partitions.setdefault(group, set()).add(partition)
    leaked = [group for group, names in group_partitions.items() if len(names) != 1]
    if leaked:
        raise AssertionError(f"group leakage across partitions: {sorted(leaked)[:5]}")


def _load_verified_source(
    source: AdmittedSource,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    source_path = verify_admitted_source(source)
    records = _read_jsonl(source_path)
    manifest_path = _verified_partition_manifest(source)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    partitions = payload.get("partitions")
    if not isinstance(partitions, dict):
        raise ValueError("partition manifest requires partitions object")
    typed = {name: [str(value) for value in values] for name, values in partitions.items()}
    assert_group_isolation(records, typed, group_field=source.frozen_group_field)
    return records, typed


def _examples_for_partition(
    records: list[dict[str, object]],
    manifest: dict[str, list[str]],
    partition: str,
    source: AdmittedSource,
) -> list[ModerationExample]:
    ids = set(manifest.get(partition, []))
    records_by_id = {str(record["example_id"]): record for record in records}
    missing = ids - records_by_id.keys()
    if missing:
        raise ValueError(f"partition references missing records: {sorted(missing)[:5]}")
    return [_record_to_example(records_by_id[example_id], source) for example_id in sorted(ids)]


def _record_to_example(record: dict[str, Any], source: AdmittedSource) -> ModerationExample:
    messages = list(record["messages"])
    duration = record.get("containment_duration_seconds")
    serialized = serialize_messages(
        str(record["channel_profile"]),
        messages,
        int(record["target_index"]),
    )
    return ModerationExample(
        example_id=str(record["example_id"]),
        serialized=serialized,
        label=str(record["label"]),
        action=str(record["action"]),
        review_priority=str(record["review_priority"]),
        strike=bool(record["strike"]),
        containment=str(record["containment"]),
        containment_duration_seconds=int(duration) if duration is not None else None,
        support_flow=str(record["support_flow"]),
        channel_profile=str(record["channel_profile"]),
        platform_hint=str(record.get("platform_hint", "")),
        domain=str(record.get("domain", "")),
        difficulty=str(record.get("difficulty", "")),
        reason_codes=tuple(str(value) for value in record.get("reason_codes", [])),
        family_id=str(record[source.frozen_group_field]),
    )


def _verified_partition_manifest(source: AdmittedSource) -> Path:
    if not source.partition_manifest or not source.partition_manifest_sha256:
        raise ValueError("partitioned sources require a hash-pinned partition manifest")
    storage = source.partition_manifest_storage or source.storage
    return _verified_source_file(
        source.partition_manifest,
        source.partition_manifest_sha256,
        storage,
    )


def _verified_source_file(relative: str, expected_sha256: str, storage: str) -> Path:
    if storage == "repo":
        return _verified_repo_file(relative, expected_sha256)
    if storage == "private":
        return _verified_private_file(relative, expected_sha256)
    raise ValueError(f"unsupported W25 source storage: {storage}")


def _verified_private_file(relative: str, expected_sha256: str) -> Path:
    _reject_acceptance_path(relative)
    root_value = os.environ.get("W25_PRIVATE_DATA_ROOT")
    if not root_value:
        raise RuntimeError("W25_PRIVATE_DATA_ROOT is required for private admitted data")
    root = Path(root_value).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("private admitted source escapes W25_PRIVATE_DATA_ROOT")
    return _verified_file_hash(path, expected_sha256, relative)


def _verified_repo_file(relative: str, expected_sha256: str) -> Path:
    _reject_acceptance_path(relative)
    path = (REPO_ROOT / relative).resolve()
    if not path.is_relative_to(REPO_ROOT):
        raise ValueError("admitted source escapes repository")
    return _verified_file_hash(path, expected_sha256, relative)


def _verified_file_hash(path: Path, expected_sha256: str, label: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError(f"admitted source hash mismatch: {label}")
    return path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _group_records(
    records: Sequence[Mapping[str, object]], group_field: str
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for record in records:
        example_id = str(record.get("example_id", "")).strip()
        group = str(record.get(group_field, "")).strip()
        if not example_id or not group:
            raise ValueError(f"records require example_id and {group_field}")
        groups.setdefault(group, []).append(example_id)
    return groups


def _bucket(group: str, seed: str) -> float:
    digest = hashlib.sha256(f"{seed}|{group}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _reject_acceptance_path(path: str) -> None:
    lowered = path.lower().replace("_", "-")
    if any(marker.replace("_", "-") in lowered for marker in W20_MARKERS):
        raise ValueError("W20/acceptance data is forbidden during W25 development")
