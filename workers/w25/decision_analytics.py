"""Private, per-decision W25 evidence ledger and comparable model disagreement reports.

Never collects raw chat, prompts, embeddings, names or external IDs. No model
inference, private-suite discovery, training or production moderation occurs here.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from workers.w12.dataset import ModerationExample
from workers.w25.artifacts import load_bundle
from workers.w25.contract import HEAD_NAMES, HEAD_VALUES, PredictionBundle
from workers.w25.evaluation import suite_fingerprint
from workers.w25.suites import load_frozen_suite

SCHEMA = "w25-private-decision-ledger/1"
REPO = Path(__file__).resolve().parents[2]
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
BANNED_SUITES = ("w20", "w27", "acceptance", "owner_golden")


def _validated_token(value: str) -> str:
    if not TOKEN.fullmatch(value):
        raise ValueError("Invalid run, model or suite identifier")
    return value


def _validated_sha(value: str) -> str:
    if not DIGEST.fullmatch(value):
        raise ValueError("Expected a lowercase SHA-256 digest")
    return value


def _private_root(folder: Path) -> Path:
    if not folder.is_absolute():
        raise ValueError("Private ledger folder must be an absolute path")
    location = folder.resolve()
    if location == REPO or REPO in location.parents:
        raise ValueError("Private ledger output cannot be inside the Git repository")
    if not location.is_dir():
        raise ValueError("Private ledger directory must exist and be access controlled")
    return location


def _secret(environment_key: str) -> bytes:
    if not environment_key.startswith("ENTHUSIA_"):
        raise ValueError("Use an explicit ENTHUSIA_ environment key")
    value = os.environ.get(environment_key)
    if value is None or len(value) < 32:
        raise ValueError("Private pseudonym secret must be at least 32 characters")
    return value.encode("utf-8")


def _opaque(secret: bytes, identifier: str) -> str:
    return hmac.new(secret, identifier.encode("utf-8"), hashlib.sha256).hexdigest()


def _decision_truth(example: ModerationExample) -> dict[str, object]:
    return {
        "label": example.label,
        "action": example.action,
        "review_priority": example.review_priority,
        "strike": example.strike,
        "containment": example.containment,
        "support_flow": example.support_flow,
    }


def _prediction(bundle: PredictionBundle, index: int) -> dict[str, object]:
    result: dict[str, object] = {}
    for head in HEAD_NAMES:
        name = HEAD_VALUES[head][bundle.predictions[head][index]]
        result[head] = (name == "true") if head == "strike" else name
    return result


def _case_record(
    example: ModerationExample, bundle: PredictionBundle, index: int, secret: bytes,
) -> dict[str, object]:
    truth = _decision_truth(example)
    predicted = _prediction(bundle, index)
    incorrect = [head for head in HEAD_NAMES if truth[head] != predicted[head]]
    return {
        "record_type": "decision",
        "case_key": _opaque(secret, example.example_id),
        "family_key": _opaque(secret, example.family_id) if example.family_id else None,
        "gold": truth,
        "predicted": predicted,
        "probabilities": {
            head: list(bundle.probabilities[head][index]) for head in HEAD_NAMES
        },
        "uncertainty": bundle.uncertainty[index],
        "confidence": max(bundle.probabilities["action"][index]),
        "head_errors": incorrect,
        "all_supervised_heads_correct": not incorrect,
        "channel_profile": example.channel_profile,
        "platform_hint": example.platform_hint,
        "domain": example.domain,
        "difficulty": example.difficulty,
        "gold_reason_codes": list(example.reason_codes),
        "gold_containment_duration_seconds": example.containment_duration_seconds,
        "predicted_containment_duration_seconds": None,
        "latency_ms": None,
        "logits": None,
        "explanation_trace": None,
        "error_kind": "HEAD_DISAGREEMENT" if incorrect else "MATCH",
    }


def _manifest(
    examples: list[ModerationExample], candidate: str, run_id: str,
    seed: int, model_sha: str, config_sha: str, policy: str,
) -> dict[str, object]:
    return {
        "record_type": "manifest",
        "schema_version": SCHEMA,
        "run_id": _validated_token(run_id),
        "candidate": _validated_token(candidate),
        "seed": seed,
        "policy_version": _validated_token(policy),
        "model_artifact_sha256": _validated_sha(model_sha),
        "configuration_sha256": _validated_sha(config_sha),
        "suite_fingerprint": suite_fingerprint(examples),
        "count": len(examples),
        "probability_head_value_order": HEAD_VALUES,
        "privacy": "private_only_hmac_case_and_family_keys_no_chat_text",
        "ground_truth_status": "SOURCE_LABELS_UNVERIFIED_UNLESS_ADJUDICATED_SEPARATELY",
        "automatic_punishments_enabled": False,
        "complete_seven_field_evaluation": False,
        "missing": "latency/logits/rule_trace/learned_mute_duration_not_in_W25_bundle",
    }


def _write_once(path: Path, lines: list[dict[str, object]]) -> None:
    # Exclusive create prevents overwriting results from earlier model runs.
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError("Run ledger already exists; use a new run ID") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            for item in lines:
                file.write(json.dumps(item, sort_keys=True, allow_nan=False) + "\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def capture(
    examples: list[ModerationExample], bundle: PredictionBundle,
    *, secret: bytes, folder: Path, run_id: str, candidate: str,
    seed: int, model_sha: str, config_sha: str, policy: str,
) -> Path:
    bundle.validate()
    if len(examples) != len(bundle.uncertainty) or not examples:
        raise ValueError("Exact nonempty example/prediction cardinality required")
    if len({item.example_id for item in examples}) != len(examples):
        raise ValueError("Duplicate example IDs in comparison suite")
    root = _private_root(folder)
    manifest = _manifest(examples, candidate, run_id, seed, model_sha, config_sha, policy)
    lines = [manifest] + [
        _case_record(example, bundle, index, secret)
        for index, example in enumerate(examples)
    ]
    destination = root / (_validated_token(run_id) + ".jsonl")
    _write_once(destination, lines)
    return destination


def _read_ledger(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if path.stat().st_size > 200_000_000:
        raise ValueError("Ledger too large")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or rows[0].get("schema_version") != SCHEMA:
        raise ValueError("Unsupported ledger schema")
    header = rows[0]
    records = rows[1:]
    if header["count"] != len(records):
        raise ValueError("Ledger count mismatch")
    if any(item.get("record_type") != "decision" for item in records):
        raise ValueError("Unexpected ledger record type")
    keys = [item["case_key"] for item in records]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate pseudonymous cases")
    return header, dict(zip(keys, records, strict=True))


def _compare_head(
    left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]], head: str,
) -> dict[str, object]:
    disagreements = [
        key for key in left
        if left[key]["predicted"][head] != right[key]["predicted"][head]
    ]
    both_wrong = sum(
        head in left[key]["head_errors"] and head in right[key]["head_errors"]
        for key in left
    )
    return {
        "disagreements": len(disagreements),
        "both_wrong": both_wrong,
        "first_25_disagreement_case_keys": disagreements[:25],
    }


def compare(paths: list[Path]) -> dict[str, object]:
    if len(paths) < 2:
        raise ValueError("Compare at least two independent model ledgers")
    loaded = [_read_ledger(path) for path in paths]
    headers = [pair[0] for pair in loaded]
    records = [pair[1] for pair in loaded]
    if len({h["run_id"] for h in headers}) != len(headers):
        raise ValueError("Duplicate run IDs")
    if len({h["suite_fingerprint"] for h in headers}) != 1:
        raise ValueError("Cannot compare distinct evaluation suites")
    first = records[0]
    if any(set(other) != set(first) for other in records[1:]):
        raise ValueError("Pseudonym keys differ; use the same private HMAC key")
    if any(other[key]["gold"] != first[key]["gold"]
           for other in records[1:] for key in first):
        raise ValueError("Gold decisions differ between candidate ledgers")
    pairs: dict[str, object] = {}
    for index in range(len(records)):
        for other in range(index + 1, len(records)):
            name = headers[index]["run_id"] + "_vs_" + headers[other]["run_id"]
            pairs[name] = {
                head: _compare_head(records[index], records[other], head)
                for head in HEAD_NAMES
            }
    return {
        "schema_version": "w25-private-comparison/1",
        "no_raw_message_content": True,
        "not_an_accuracy_or_deployment_certificate": True,
        "suite_fingerprint": headers[0]["suite_fingerprint"],
        "compared_cases": len(first),
        "per_run": {
            h["run_id"]: {
                "candidate": h["candidate"],
                "supervised_head_errors": dict(Counter(
                    head for row in values.values() for head in row["head_errors"]
                )),
            }
            for h, values in loaded
        },
        "pairwise": pairs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Private W25 per-decision model analytics")
    sub = parser.add_subparsers(dest="command", required=True)
    take = sub.add_parser("capture")
    for name in ("run-id", "candidate", "suite", "model-sha256",
                 "config-sha256", "policy"):
        take.add_argument("--" + name, required=True)
    take.add_argument("--seed", type=int, required=True)
    take.add_argument("--bundle", type=Path, required=True)
    take.add_argument("--private-dir", type=Path, required=True)
    take.add_argument("--secret-env", default="ENTHUSIA_ANALYTICS_HMAC_KEY")
    diff = sub.add_parser("compare")
    diff.add_argument("ledgers", type=Path, nargs="+")
    args = parser.parse_args()
    if args.command == "compare":
        print(json.dumps(compare(args.ledgers), indent=2, sort_keys=True))
        return
    suite = _validated_token(args.suite)
    if any(word in suite.lower() for word in BANNED_SUITES):
        raise SystemExit("Acceptance and sealed suites cannot be captured by this tool")
    output = capture(
        load_frozen_suite(suite), load_bundle(args.bundle),
        secret=_secret(args.secret_env), folder=args.private_dir,
        run_id=args.run_id, candidate=args.candidate, seed=args.seed,
        model_sha=args.model_sha256, config_sha=args.config_sha256,
        policy=args.policy,
    )
    print(json.dumps({"saved_private_ledger": output.name, "status": "capture_complete"}))


if __name__ == "__main__":
    main()
