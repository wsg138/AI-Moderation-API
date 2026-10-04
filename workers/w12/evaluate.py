"""W12 evaluation: policy dimensions, critical slices, and calibration.

Validation is the only selection/calibration partition. Held-out helpers exist
for frozen acceptance reporting after a candidate and preprocessing contract are
frozen; callers must enforce that gate.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from .dataset import (
    ACTION_TO_ID,
    ACTIONS,
    CONTAINMENT_TO_ID,
    CONTAINMENTS,
    LABEL_TO_ID,
    LABELS,
    REVIEW_PRIORITIES,
    REVIEW_TO_ID,
    SUPPORT_FLOWS,
    SUPPORT_TO_ID,
    ModerationExample,
)

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def prf_per_class(gold: list[int], pred: list[int], n_classes: int) -> list[dict]:
    out = []
    for class_id in range(n_classes):
        tp = sum(g == class_id and p == class_id for g, p in zip(gold, pred, strict=True))
        fp = sum(g != class_id and p == class_id for g, p in zip(gold, pred, strict=True))
        fn = sum(g == class_id and p != class_id for g, p in zip(gold, pred, strict=True))
        tn = len(gold) - tp - fp - fn
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out.append(
            {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": tp + fn,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            }
        )
    return out


def confusion_matrix(gold: list[int], pred: list[int], n_classes: int) -> list[list[int]]:
    matrix = [[0] * n_classes for _ in range(n_classes)]
    for expected, actual in zip(gold, pred, strict=True):
        matrix[expected][actual] += 1
    return matrix


def macro_f1(per_class: list[dict]) -> float:
    return sum(item["f1"] for item in per_class) / len(per_class)


def weighted_f1(per_class: list[dict]) -> float:
    total = sum(item["support"] for item in per_class)
    if not total:
        return 0.0
    return sum(item["f1"] * item["support"] for item in per_class) / total


def _classification_report(
    gold: list[int],
    pred: list[int],
    names: list[str],
    name_key: str,
) -> dict:
    stats = prf_per_class(gold, pred, len(names))
    return {
        "per_class": [
            {name_key: name, **item} for name, item in zip(names, stats, strict=True)
        ],
        "macro_f1": macro_f1(stats),
        "weighted_f1": weighted_f1(stats),
        "accuracy": sum(g == p for g, p in zip(gold, pred, strict=True)) / len(gold),
        "confusion_matrix": confusion_matrix(gold, pred, len(names)),
    }


def _has_reason(example: ModerationExample, *codes: str) -> bool:
    return any(code in example.reason_codes for code in codes)


def _minecraft_gameplay(example: ModerationExample) -> bool:
    return example.channel_profile.startswith("minecraft_") and (
        example.label == "GAMEPLAY_VIOLENCE"
        or _has_reason(example, "minecraft_gameplay_explicit")
    )


def _benign_hard_negatives(example: ModerationExample) -> bool:
    return example.example_id.startswith("G09-")


def _generic_minecraft_violence(example: ModerationExample) -> bool:
    return (
        example.channel_profile.startswith("minecraft_")
        and example.label == "GAMEPLAY_VIOLENCE"
        and example.action == "ALLOW"
    )


def _explicit_real_world_cues(example: ModerationExample) -> bool:
    return _has_reason(
        example,
        "explicit_real_world_cue",
        "real_world_location",
        "real_world_time",
        "real_world_proximity",
        "real_world_address_cue",
        "real_world_delivery_cue",
    )


def _real_world_threat(example: ModerationExample) -> bool:
    return example.label == "REAL_WORLD_THREAT"


def _split_message_threat(example: ModerationExample) -> bool:
    return _has_reason(example, "split_message_context") and example.label == "REAL_WORLD_THREAT"


def _long_gap_non_linkage(example: ModerationExample) -> bool:
    return _has_reason(example, "long_gap_breaks_linkage")


def _self_harm_instruction(example: ModerationExample) -> bool:
    return example.label == "SELF_HARM_INSTRUCTION"


def _first_person_self_harm(example: ModerationExample) -> bool:
    return _has_reason(example, "self_harm_disclosure") and example.label == "SELF_HARM_INTENT"


def _slur_actual_use(example: ModerationExample) -> bool:
    return _has_reason(example, "actual_slur")


def _slur_reference_only(example: ModerationExample) -> bool:
    return _has_reason(example, "slur_reference_only")


def _public_flirting_or_sexual(example: ModerationExample) -> bool:
    return _has_reason(example, "public_flirting", "public_sexual_content")


def _private_flirting(example: ModerationExample) -> bool:
    return _has_reason(example, "private_flirting")


def _sexual_minor(example: ModerationExample) -> bool:
    return example.label in ("SEXUAL_MINOR", "GROOMING")


def _age_reliable_minor(example: ModerationExample) -> bool:
    return _has_reason(example, "age_reliable_minor")


def _age_self_report_only(example: ModerationExample) -> bool:
    return _has_reason(example, "age_self_report_clue")


def _minecraft_tnt(example: ModerationExample) -> bool:
    return (
        example.channel_profile.startswith("minecraft_")
        and example.action == "ALLOW"
        and "tnt" in example.serialized.lower()
    )


def _real_world_explosive_request(example: ModerationExample) -> bool:
    return (
        example.label == "DANGEROUS_REAL_WORLD_INSTRUCTIONS"
        and _has_reason(example, "dangerous_instruction_request")
    )


def _obfuscation_evasion(example: ModerationExample) -> bool:
    return _has_reason(example, "obfuscated_evasion")


SLICE_PREDICATES: dict[str, Callable[[ModerationExample], bool]] = {
    "minecraft_gameplay": _minecraft_gameplay,
    "benign_hard_negatives": _benign_hard_negatives,
    "generic_minecraft_violence": _generic_minecraft_violence,
    "explicit_real_world_cues": _explicit_real_world_cues,
    "real_world_threat": _real_world_threat,
    "split_message_threat": _split_message_threat,
    "long_gap_non_linkage": _long_gap_non_linkage,
    "self_harm_instruction": _self_harm_instruction,
    "first_person_self_harm_disclosure": _first_person_self_harm,
    "slur_actual_use": _slur_actual_use,
    "slur_reference_only": _slur_reference_only,
    "public_flirting_or_sexual": _public_flirting_or_sexual,
    "private_flirting": _private_flirting,
    "sexual_minor": _sexual_minor,
    "age_reliable_minor": _age_reliable_minor,
    "age_self_report_only": _age_self_report_only,
    "minecraft_tnt": _minecraft_tnt,
    "real_world_explosive_request": _real_world_explosive_request,
    "obfuscation_evasion": _obfuscation_evasion,
    "discord_general": lambda example: example.channel_profile == "discord_general",
    "minecraft_public": lambda example: example.channel_profile == "minecraft_public",
}
SLICES = list(SLICE_PREDICATES)


def slice_predicate(example: ModerationExample, slice_name: str) -> bool:
    predicate = SLICE_PREDICATES.get(slice_name)
    if predicate is None:
        return False
    return predicate(example)


def runtime_visibility(action: str) -> int:
    """Dataset BLOCK -> runtime BLOCK (1); ALLOW/REVIEW -> runtime ALLOW (0)."""
    return 1 if action == "BLOCK" else 0


def _slice_metrics(
    examples: list[ModerationExample],
    indices: list[int],
    gold_vis: list[int],
    pred_vis: list[int],
    gold_label: list[int],
    pred_label: list[int],
) -> dict:
    allow = [index for index in indices if gold_vis[index] == 0]
    block = [index for index in indices if gold_vis[index] == 1]
    false_positive = [index for index in allow if pred_vis[index] == 1]
    true_positive = [index for index in block if pred_vis[index] == 1]
    false_negative = [index for index in block if pred_vis[index] == 0]
    families = sorted(
        {examples[index].family_id for index in false_positive if examples[index].family_id}
    )
    return {
        "n": len(indices),
        "n_gold_allow": len(allow),
        "n_gold_block": len(block),
        "block_false_positive_rate": len(false_positive) / len(allow) if allow else None,
        "block_false_positives": len(false_positive),
        "block_recall": len(true_positive) / len(block) if block else None,
        "block_true_positives": len(true_positive),
        "block_false_negatives": len(false_negative),
        "label_accuracy": (
            sum(gold_label[index] == pred_label[index] for index in indices) / len(indices)
        ),
        "false_positive_example_ids": [
            examples[index].example_id for index in false_positive[:20]
        ],
        "false_positive_family_ids": families[:20],
        "false_negative_example_ids": [
            examples[index].example_id for index in false_negative[:20]
        ],
    }


def _critical_slices(
    examples: list[ModerationExample],
    gold_vis: list[int],
    pred_vis: list[int],
    gold_label: list[int],
    pred_label: list[int],
) -> dict:
    result = {}
    for name, predicate in SLICE_PREDICATES.items():
        indices = [index for index, example in enumerate(examples) if predicate(example)]
        result[name] = (
            {"n": 0}
            if not indices
            else _slice_metrics(examples, indices, gold_vis, pred_vis, gold_label, pred_label)
        )
    return result


def evaluate_predictions(
    examples: list[ModerationExample],
    pred_label: list[int],
    pred_action: list[int],
    pred_review: list[int],
    pred_strike: list[int],
    pred_containment: list[int],
    pred_support: list[int],
    proba_block: list[float] | None = None,
) -> dict:
    gold_label = [LABEL_TO_ID[example.label] for example in examples]
    gold_action = [ACTION_TO_ID[example.action] for example in examples]
    gold_review = [REVIEW_TO_ID[example.review_priority] for example in examples]
    gold_strike = [1 if example.strike else 0 for example in examples]
    gold_containment = [CONTAINMENT_TO_ID[example.containment] for example in examples]
    gold_support = [SUPPORT_TO_ID[example.support_flow] for example in examples]
    gold_visibility = [runtime_visibility(example.action) for example in examples]
    pred_visibility = [1 if ACTIONS[value] == "BLOCK" else 0 for value in pred_action]

    runtime_report = _classification_report(
        gold_visibility, pred_visibility, ["ALLOW", "BLOCK"], "visibility"
    )
    runtime_report.update(
        {
            "block_precision": runtime_report["per_class"][1]["precision"],
            "block_recall": runtime_report["per_class"][1]["recall"],
            "block_f1": runtime_report["per_class"][1]["f1"],
        }
    )
    report = {
        "n": len(examples),
        "semantic_label": _classification_report(gold_label, pred_label, LABELS, "label"),
        "dataset_action_3way": _classification_report(
            gold_action, pred_action, ACTIONS, "action"
        ),
        "runtime_visibility_binary": runtime_report,
        "review_priority": _classification_report(
            gold_review, pred_review, REVIEW_PRIORITIES, "priority"
        ),
        "strike": _classification_report(
            gold_strike, pred_strike, ["false", "true"], "strike"
        ),
        "containment": _classification_report(
            gold_containment, pred_containment, CONTAINMENTS, "containment"
        ),
        "support_flow": _classification_report(
            gold_support, pred_support, SUPPORT_FLOWS, "flow"
        ),
        "critical_slices": _critical_slices(
            examples, gold_visibility, pred_visibility, gold_label, pred_label
        ),
    }
    if proba_block is not None:
        report["calibration"] = calibration_report(gold_visibility, proba_block)
    return report


def calibration_report(y_true: list[int], y_prob: list[float], n_bins: int = 10) -> dict:
    bins: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for expected, probability in zip(y_true, y_prob, strict=True):
        bins[min(int(probability * n_bins), n_bins - 1)].append((expected, probability))
    table = []
    ece = 0.0
    for bin_id in range(n_bins):
        items = bins.get(bin_id, [])
        if not items:
            table.append({"bin": bin_id, "n": 0, "mean_pred": None, "frac_pos": None})
            continue
        mean_pred = sum(probability for _, probability in items) / len(items)
        fraction_positive = sum(expected for expected, _ in items) / len(items)
        table.append(
            {
                "bin": bin_id,
                "n": len(items),
                "mean_pred": mean_pred,
                "frac_pos": fraction_positive,
            }
        )
        ece += abs(mean_pred - fraction_positive) * len(items) / len(y_true)
    brier = sum(
        (probability - expected) ** 2
        for expected, probability in zip(y_true, y_prob, strict=True)
    ) / len(y_true)
    return {"ece": ece, "brier_score": brier, "n_bins": n_bins, "reliability_table": table}


def _acceptance_failures(
    examples: list[ModerationExample], predictions: dict[str, list[int]]
) -> dict:
    dimensions = (
        ("label", LABELS, lambda example: LABEL_TO_ID[example.label]),
        ("action", ACTIONS, lambda example: ACTION_TO_ID[example.action]),
        ("review_priority", REVIEW_PRIORITIES, lambda example: REVIEW_TO_ID[example.review_priority]),
        ("strike", ["false", "true"], lambda example: 1 if example.strike else 0),
        ("containment", CONTAINMENTS, lambda example: CONTAINMENT_TO_ID[example.containment]),
        ("support_flow", SUPPORT_FLOWS, lambda example: SUPPORT_TO_ID[example.support_flow]),
    )
    failures = []
    for index, example in enumerate(examples):
        mismatches = {}
        for name, values, expected_fn in dimensions:
            expected = expected_fn(example)
            actual = predictions[name][index]
            if expected != actual:
                mismatches[name] = {"expected": values[expected], "predicted": values[actual]}
        if mismatches:
            failures.append(
                {
                    "example_id": example.example_id,
                    "family_id": example.family_id,
                    "semantic_category": example.label,
                    "visibility_error": _visibility_error(example, predictions["action"][index]),
                    "dimensions": mismatches,
                }
            )
    return {
        "fully_labeled": len(examples),
        "passed_all_dimensions": len(examples) - len(failures),
        "failed_any_dimension": len(failures),
        "failures": failures,
    }


def _visibility_error(example: ModerationExample, predicted_action: int) -> str | None:
    expected = runtime_visibility(example.action)
    actual = 1 if ACTIONS[predicted_action] == "BLOCK" else 0
    if expected == actual:
        return None
    return "false_positive_block" if actual else "false_negative_block"


def evaluate_heldout(
    name: str,
    examples: list[ModerationExample],
    predictions: dict[str, list[int]],
    proba_block: list[float] | None = None,
) -> dict:
    """Evaluate a frozen held-out partition after the acceptance gate is frozen."""
    report = evaluate_predictions(
        examples,
        predictions["label"],
        predictions["action"],
        predictions["review_priority"],
        predictions["strike"],
        predictions["containment"],
        predictions["support_flow"],
        proba_block,
    )
    report["partition"] = name
    if name == "owner_golden":
        report["acceptance"] = _acceptance_failures(examples, predictions)
    if name == "frozen_adversarial":
        gold_visibility = [runtime_visibility(example.action) for example in examples]
        pred_visibility = [1 if ACTIONS[value] == "BLOCK" else 0 for value in predictions["action"]]
        gold_label = [LABEL_TO_ID[example.label] for example in examples]
        report["critical_slices"]["frozen_adversarial_partition"] = _slice_metrics(
            examples,
            list(range(len(examples))),
            gold_visibility,
            pred_visibility,
            gold_label,
            predictions["label"],
        )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"heldout-{name}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"[{name}] n={report['n']} label_macro_f1={report['semantic_label']['macro_f1']:.3f} "
        f"block_recall={report['runtime_visibility_binary']['block_recall']:.3f}",
        flush=True,
    )
    return report
