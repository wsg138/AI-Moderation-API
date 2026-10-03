"""W12 evaluation: metrics, critical policy slices, calibration.

Evaluates any candidate (baseline or encoder) on validation. Test/frozen
adversarial/golden are evaluated ONLY via evaluate_heldout() after the final
candidate is frozen.
"""

from __future__ import annotations

import json
from collections import defaultdict
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
    for c in range(n_classes):
        tp = sum(1 for g, p in zip(gold, pred, strict=False) if g == c and p == c)
        fp = sum(1 for g, p in zip(gold, pred, strict=False) if g != c and p == c)
        fn = sum(1 for g, p in zip(gold, pred, strict=False) if g == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out.append(
            {
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "support": tp + fn,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )
    return out


def confusion_matrix(gold: list[int], pred: list[int], n_classes: int) -> list[list[int]]:
    m = [[0] * n_classes for _ in range(n_classes)]
    for g, p in zip(gold, pred, strict=False):
        m[g][p] += 1
    return m


def macro_f1(per_class: list[dict]) -> float:
    return sum(c["f1"] for c in per_class) / len(per_class)


def weighted_f1(per_class: list[dict]) -> float:
    total = sum(c["support"] for c in per_class)
    if not total:
        return 0.0
    return sum(c["f1"] * c["support"] for c in per_class) / total


# ---------------------------------------------------------------------------
# Critical policy slices (evaluation-only metadata, never model input)
# ---------------------------------------------------------------------------


def slice_predicate(example: ModerationExample, slice_name: str) -> bool:
    d = example.domain
    label = example.label
    profile = example.channel_profile
    if slice_name == "minecraft_gameplay":
        return label == "GAMEPLAY_VIOLENCE" or d == "gameplay_violence"
    if slice_name == "benign_hard_negatives":
        return d in ("benign_hard_negatives",) or (label == "SAFE" and "hard" in d)
    if slice_name == "real_world_threat":
        return label == "REAL_WORLD_THREAT"
    if slice_name == "split_message_threat":
        return d in ("evasion_context",) and label in ("REAL_WORLD_THREAT", "AMBIGUOUS_REVIEW")
    if slice_name == "kys_self_harm_instruction":
        return label == "SELF_HARM_INSTRUCTION"
    if slice_name == "self_harm_disclosure":
        return label in ("SELF_HARM_INTENT", "THIRD_PARTY_SELF_HARM_CONCERN")
    if slice_name == "slur":
        return label in ("SLUR_USE", "HATE")
    if slice_name == "sexual_minor":
        return label in ("SEXUAL_CONTENT", "SEXUAL_MINOR", "GROOMING")
    if slice_name == "tnt_vs_explosive":
        return label == "DANGEROUS_REAL_WORLD_INSTRUCTIONS" or "tnt" in example.serialized.lower()
    if slice_name == "obfuscation_evasion":
        return d in ("evasion_context",)
    if slice_name == "discord_general":
        return profile == "discord_general"
    if slice_name == "minecraft_public":
        return profile == "minecraft_public"
    return False


SLICES = [
    "minecraft_gameplay",
    "benign_hard_negatives",
    "real_world_threat",
    "split_message_threat",
    "kys_self_harm_instruction",
    "self_harm_disclosure",
    "slur",
    "sexual_minor",
    "tnt_vs_explosive",
    "obfuscation_evasion",
    "discord_general",
    "minecraft_public",
]


def runtime_visibility(action: str) -> int:
    """Dataset BLOCK -> runtime BLOCK (1); ALLOW/REVIEW -> runtime ALLOW (0)."""
    return 1 if action == "BLOCK" else 0


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
    gold_label = [LABEL_TO_ID[e.label] for e in examples]
    gold_action = [ACTION_TO_ID[e.action] for e in examples]
    gold_review = [REVIEW_TO_ID[e.review_priority] for e in examples]
    gold_strike = [1 if e.strike else 0 for e in examples]
    gold_cont = [CONTAINMENT_TO_ID[e.containment] for e in examples]
    gold_support = [SUPPORT_TO_ID[e.support_flow] for e in examples]

    label_prf = prf_per_class(gold_label, pred_label, len(LABELS))
    action_prf = prf_per_class(gold_action, pred_action, len(ACTIONS))

    # Derived runtime binary visibility
    gold_vis = [runtime_visibility(e.action) for e in examples]
    pred_vis = [1 if ACTIONS[p] == "BLOCK" else 0 for p in pred_action]
    vis_prf = prf_per_class(gold_vis, pred_vis, 2)

    report: dict = {
        "n": len(examples),
        "semantic_label": {
            "per_class": [
                {"label": name, **stats} for name, stats in zip(LABELS, label_prf, strict=False)
            ],
            "macro_f1": macro_f1(label_prf),
            "weighted_f1": weighted_f1(label_prf),
            "accuracy": sum(g == p for g, p in zip(gold_label, pred_label, strict=False))
            / len(examples),
            "confusion_matrix": confusion_matrix(gold_label, pred_label, len(LABELS)),
        },
        "dataset_action_3way": {
            "per_class": [
                {"action": name, **stats} for name, stats in zip(ACTIONS, action_prf, strict=False)
            ],
            "macro_f1": macro_f1(action_prf),
            "accuracy": sum(g == p for g, p in zip(gold_action, pred_action, strict=False))
            / len(examples),
        },
        "runtime_visibility_binary": {
            "per_class": [
                {"visibility": name, **stats}
                for name, stats in zip(["ALLOW", "BLOCK"], vis_prf, strict=False)
            ],
            "block_precision": vis_prf[1]["precision"],
            "block_recall": vis_prf[1]["recall"],
            "block_f1": vis_prf[1]["f1"],
        },
        "review_priority": {
            "per_class": [
                {"priority": name, **stats}
                for name, stats in zip(
                    REVIEW_PRIORITIES, prf_per_class(gold_review, pred_review, 3), strict=False
                )
            ],
        },
        "strike": {
            "per_class": [
                {"strike": name, **stats}
                for name, stats in zip(
                    ["false", "true"], prf_per_class(gold_strike, pred_strike, 2), strict=False
                )
            ],
        },
        "containment": {
            "per_class": [
                {"containment": name, **stats}
                for name, stats in zip(
                    CONTAINMENTS, prf_per_class(gold_cont, pred_containment, 2), strict=False
                )
            ],
        },
        "support_flow": {
            "per_class": [
                {"flow": name, **stats}
                for name, stats in zip(
                    SUPPORT_FLOWS, prf_per_class(gold_support, pred_support, 3), strict=False
                )
            ],
        },
    }

    # Critical policy slices
    slices: dict = {}
    for s in SLICES:
        idx = [i for i, e in enumerate(examples) if slice_predicate(e, s)]
        if not idx:
            slices[s] = {"n": 0}
            continue
        s_gold_vis = [gold_vis[i] for i in idx]
        s_pred_vis = [pred_vis[i] for i in idx]
        s_gold_label = [gold_label[i] for i in idx]
        s_pred_label = [pred_label[i] for i in idx]
        # BLOCK false-positive rate on this slice
        allow_idx = (
            [i for i in idx if gold_vis[examples.index(examples[i])] == 0]
            if False
            else [k for k, i in enumerate(idx) if s_gold_vis[k] == 0]
        )
        fp = sum(1 for k in allow_idx if s_pred_vis[k] == 1)
        # Threat recall on this slice (for threat-relevant slices)
        block_idx = [k for k, i in enumerate(idx) if s_gold_vis[k] == 1]
        tp = sum(1 for k in block_idx if s_pred_vis[k] == 1)
        slices[s] = {
            "n": len(idx),
            "n_gold_allow": len(allow_idx),
            "n_gold_block": len(block_idx),
            "block_false_positive_rate": fp / len(allow_idx) if allow_idx else None,
            "block_false_positives": fp,
            "block_recall": tp / len(block_idx) if block_idx else None,
            "block_true_positives": tp,
            "label_accuracy": sum(1 for k in range(len(idx)) if s_gold_label[k] == s_pred_label[k])
            / len(idx),
        }
        # For gameplay slice, list worst false-positive families (by example id prefix)
        if s == "minecraft_gameplay" and fp:
            fp_ids = [examples[idx[k]].example_id for k in allow_idx if s_pred_vis[k] == 1]
            slices[s]["false_positive_example_ids"] = fp_ids[:20]
    report["critical_slices"] = slices

    # Calibration (if block probabilities provided)
    if proba_block is not None:
        report["calibration"] = calibration_report(
            [runtime_visibility(e.action) for e in examples], proba_block
        )
    return report


def calibration_report(y_true: list[int], y_prob: list[float], n_bins: int = 10) -> dict:
    bins: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for t, p in zip(y_true, y_prob, strict=False):
        b = min(int(p * n_bins), n_bins - 1)
        bins[b].append((t, p))
    table = []
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        items = bins.get(b, [])
        if not items:
            table.append({"bin": b, "n": 0, "mean_pred": None, "frac_pos": None})
            continue
        mean_pred = sum(p for _, p in items) / len(items)
        frac_pos = sum(t for t, _ in items) / len(items)
        table.append({"bin": b, "n": len(items), "mean_pred": mean_pred, "frac_pos": frac_pos})
        ece += abs(mean_pred - frac_pos) * len(items) / n
    brier = sum((p - t) ** 2 for t, p in zip(y_true, y_prob, strict=False)) / n
    return {"ece": ece, "brier_score": brier, "n_bins": n_bins, "reliability_table": table}


def evaluate_heldout(
    name: str,
    examples: list[ModerationExample],
    predictions: dict[str, list[int]],
    proba_block: list[float] | None = None,
) -> dict:
    """Evaluate a frozen held-out partition. Call exactly once per partition."""
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
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"heldout-{name}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(
        f"[{name}] n={report['n']} label_macro_f1={report['semantic_label']['macro_f1']:.3f} "
        f"block_recall={report['runtime_visibility_binary']['block_recall']:.3f} "
        f"gameplay_fp_rate={report['critical_slices']['minecraft_gameplay'].get('block_false_positive_rate')}",
        flush=True,
    )
    return report
