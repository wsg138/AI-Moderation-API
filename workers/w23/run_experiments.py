"""Run the complete W23 precision-first ensemble experiment.

This module fits only W11 train, uses W11 validation for development comparison,
and never reads test, frozen-adversarial, owner-golden, or W20 data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workers.w12.dataset import LABEL_TO_ID, ModerationExample, load_partition
from workers.w23.bert_support import load_bert_oof, predict_bert_checkpoint
from workers.w23.config import (
    BLOCK_RECALL_RATIO_FLOOR,
    BLOCK_SLICE_FPR_TOLERANCE,
    CHAR_GRID,
    MATERIAL_BLOCK_PRECISION_GAIN,
    W12_BERT_MODEL_HEAD,
)
from workers.w23.evasion import all_probe_sets, deterministic_probe_sample
from workers.w23.meta import META_FEATURE_CONTRACT, predict_meta_ensemble, train_meta_ensemble
from workers.w23.metrics import (
    binary_metrics,
    block_from_bundle,
    decision_rule_report,
    full_bundle_report,
    gold_block,
    mute_rule_report,
    paired_error_overlap,
    screening_rule_report,
    strike_rule_report,
)
from workers.w23.modeling import (
    PredictionBundle,
    TextPolicyModel,
    char_spec_name,
    existing_word_baseline_bundle,
    oof_text_bundle,
    predict_text_model,
    train_text_model,
)
from workers.w23.reporting import render_markdown
from workers.w23.rules import block_rules, mute_rules, screening_rules, strike_rules
from workers.w23.selection import (
    select_block_rule,
    select_hypothetical_auto_rule,
    select_precision_text_candidate,
    select_screening_rule,
    select_strike_rule,
)

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
OOF_DIR = ROOT / "artifacts" / "oof"
BERT_CHECKPOINT = ROOT.parents[0] / "w12" / "artifacts" / "bert-mini-seed42.pt"


def _candidate_record(
    name: str,
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict[str, Any]:
    full = full_bundle_report(examples, bundle)
    decision = decision_rule_report(name, examples, block_from_bundle(bundle))
    return {
        "name": name,
        "semantic_macro_f1": full["semantic_label"]["macro_f1"],
        "semantic_accuracy": full["semantic_label"]["accuracy"],
        "decision": decision,
        "full_report": full,
    }


def _fit_grid(
    train: list[ModerationExample],
    validation: list[ModerationExample],
    kind: str,
    baseline_decision: dict,
) -> tuple[TextPolicyModel, PredictionBundle, list[dict], dict]:
    models: dict[str, TextPolicyModel] = {}
    bundles: dict[str, PredictionBundle] = {}
    records: list[dict] = []
    for char_range, max_features in CHAR_GRID:
        name = f"{kind}+{char_spec_name(char_range, max_features)}"
        model = train_text_model(train, kind, char_range, max_features)
        bundle = predict_text_model(model, validation)
        record = _candidate_record(name, validation, bundle)
        record["char_range"] = list(char_range)
        record["char_features"] = max_features
        models[name] = model
        bundles[name] = bundle
        records.append(record)
    selection = select_precision_text_candidate(records, baseline_decision)
    chosen = selection["candidate"]
    return models[chosen], bundles[chosen], records, selection


def _base_models(
    train: list[ModerationExample],
    validation: list[ModerationExample],
) -> tuple[dict[str, PredictionBundle], dict[str, TextPolicyModel], dict]:
    word_bundle = existing_word_baseline_bundle(train, validation)
    baseline_decision = decision_rule_report(
        "word-argmax",
        validation,
        block_from_bundle(word_bundle),
    )
    word_model = train_text_model(train, "word")
    equivalent = predict_text_model(word_model, validation)
    if equivalent.predictions != word_bundle.predictions:
        raise RuntimeError("W23 word implementation diverged from the existing W12 baseline")
    char_model, char_bundle, char_grid, char_selection = _fit_grid(
        train, validation, "char", baseline_decision
    )
    combined_model, combined_bundle, combined_grid, combined_selection = _fit_grid(
        train, validation, "combined", baseline_decision
    )
    bert_bundle = predict_bert_checkpoint(validation, BERT_CHECKPOINT)
    bundles = {
        "word": word_bundle,
        "char": char_bundle,
        "combined": combined_bundle,
        "bert": bert_bundle,
    }
    models = {"word": word_model, "char": char_model, "combined": combined_model}
    grid_report = {
        "char": {"selection": char_selection, "candidates": char_grid},
        "combined": {"selection": combined_selection, "candidates": combined_grid},
    }
    return bundles, models, grid_report


def _oof_bundles(
    train: list[ModerationExample],
    grid_report: dict,
) -> dict[str, PredictionBundle]:
    char = grid_report["char"]["selection"]["candidate"]
    combined = grid_report["combined"]["selection"]["candidate"]
    char_record = next(item for item in grid_report["char"]["candidates"] if item["name"] == char)
    combined_record = next(
        item for item in grid_report["combined"]["candidates"] if item["name"] == combined
    )
    return {
        "word": oof_text_bundle(train, "word"),
        "char": oof_text_bundle(
            train,
            "char",
            tuple(char_record["char_range"]),
            char_record["char_features"],
        ),
        "combined": oof_text_bundle(
            train,
            "combined",
            tuple(combined_record["char_range"]),
            combined_record["char_features"],
        ),
        "bert": load_bert_oof(OOF_DIR, len(train)),
    }


def _screening_reports(
    validation: list[ModerationExample],
    rules: dict[str, list[int]],
) -> list[dict]:
    return [screening_rule_report(name, validation, predicted) for name, predicted in rules.items()]


def _decision_reports(
    validation: list[ModerationExample],
    rules: dict[str, list[int]],
) -> list[dict]:
    return [decision_rule_report(name, validation, predicted) for name, predicted in rules.items()]


def _strike_reports(
    validation: list[ModerationExample],
    rules: dict[str, list[int]],
) -> list[dict]:
    return [strike_rule_report(name, validation, predicted) for name, predicted in rules.items()]


def _mute_reports(
    validation: list[ModerationExample],
    rules: dict[str, list[int]],
) -> list[dict]:
    return [mute_rule_report(name, validation, predicted) for name, predicted in rules.items()]


def _rule_reports(
    validation: list[ModerationExample],
    bundles: dict[str, PredictionBundle],
) -> tuple[dict, dict[str, list[int]]]:
    screening = screening_rules(bundles)
    screening_reports = _screening_reports(validation, screening)
    blocks = block_rules(bundles)
    block_reports = _decision_reports(validation, blocks)
    baseline = next(item for item in block_reports if item["name"] == "word-argmax")
    block_selection = select_block_rule(block_reports, baseline)
    selected_block = blocks[block_selection["rule"]]
    strikes = strike_rules(bundles, selected_block)
    strike_reports = _strike_reports(validation, strikes)
    baseline_strike = next(
        item for item in strike_reports if item["name"] == "word-strike@0.500+block-gate"
    )
    mutes = mute_rules(bundles)
    mute_reports = _mute_reports(validation, mutes)
    baseline_mute = next(item for item in mute_reports if item["name"] == "word-argmax")
    return {
        "screening": {
            "selection": select_screening_rule(screening_reports),
            "candidates": screening_reports,
        },
        "block": {"selection": block_selection, "candidates": block_reports},
        "strike": {
            "selection": select_strike_rule(strike_reports, baseline_strike),
            "candidates": strike_reports,
            "hypothetical_auto_punishment": select_hypothetical_auto_rule(
                strike_reports, baseline_strike
            ),
        },
        "containment_mute": {
            "candidates": mute_reports,
            "hypothetical_auto_punishment": select_hypothetical_auto_rule(
                mute_reports, baseline_mute
            ),
        },
    }, blocks


def _slice_bundle(bundle: PredictionBundle, start: int, end: int) -> PredictionBundle:
    probabilities = {name: matrix[start:end] for name, matrix in bundle.probabilities.items()}
    predictions = {name: values[start:end] for name, values in bundle.predictions.items()}
    return PredictionBundle(predictions=predictions, probabilities=probabilities)


def _probe_metrics(
    examples: list[ModerationExample],
    bundle: PredictionBundle,
) -> dict:
    block = binary_metrics(gold_block(examples), block_from_bundle(bundle))
    gold_labels = [LABEL_TO_ID[item.label] for item in examples]
    accuracy = sum(
        expected == actual
        for expected, actual in zip(gold_labels, bundle.predictions["label"], strict=True)
    ) / len(examples)
    return {"block": block, "semantic_accuracy": accuracy}


def _evasion_report(
    train: list[ModerationExample],
    text_models: dict[str, TextPolicyModel],
) -> dict:
    original = deterministic_probe_sample(train)
    probe_sets = {"original": original, **all_probe_sets(train)}
    names = list(probe_sets)
    flattened = [item for name in names for item in probe_sets[name]]
    bundles = {name: predict_text_model(model, flattened) for name, model in text_models.items()}
    bundles["bert"] = predict_bert_checkpoint(flattened, BERT_CHECKPOINT, batch_size=64)
    size = len(original)
    report: dict[str, dict] = {name: {} for name in bundles}
    for model_name, bundle in bundles.items():
        for index, probe_name in enumerate(names):
            start = index * size
            end = start + size
            report[model_name][probe_name] = _probe_metrics(
                probe_sets[probe_name],
                _slice_bundle(bundle, start, end),
            )
    return {
        "source_partition": "W11 train only",
        "sample_size": size,
        "transforms": names[1:],
        "models": report,
    }


def _recommendation(report: dict) -> dict:
    block = report["decision_tiers"]["block"]
    baseline = next(item for item in block["candidates"] if item["name"] == "word-argmax")
    selected = next(
        item for item in block["candidates"] if item["name"] == block["selection"]["rule"]
    )
    precision_gain = selected["precision"] - baseline["precision"]
    recall_ratio = selected["recall"] / baseline["recall"] if baseline["recall"] else 0.0
    replace = (
        precision_gain >= MATERIAL_BLOCK_PRECISION_GAIN
        and recall_ratio >= BLOCK_RECALL_RATIO_FLOOR
        and block["selection"]["slice_guard_applied"]
    )
    return {
        "screening_rule": report["decision_tiers"]["screening"]["selection"]["rule"],
        "block_rule": block["selection"]["rule"],
        "strike_rule": report["decision_tiers"]["strike"]["selection"]["rule"],
        "precision_gain_vs_w12_word": precision_gain,
        "recall_ratio_vs_w12_word": recall_ratio,
        "material_precision_gain_threshold": MATERIAL_BLOCK_PRECISION_GAIN,
        "slice_fpr_tolerance": BLOCK_SLICE_FPR_TOLERANCE,
        "justifies_replacing_current_w12_candidate": replace,
        "replacement_scope": (
            "Development recommendation only; any W12 candidate change must be "
            "deliberate before W20."
        ),
        "automatic_punishment_enabled": False,
    }


def run() -> dict:
    if not BERT_CHECKPOINT.is_file():
        raise FileNotFoundError(f"missing exact W12 BERT Mini checkpoint: {BERT_CHECKPOINT}")
    train = load_partition("train")
    validation = load_partition("validation")
    bundles, text_models, grid_report = _base_models(train, validation)
    oof = _oof_bundles(train, grid_report)
    meta = train_meta_ensemble(oof, train)
    bundles["meta"] = predict_meta_ensemble(meta, bundles, validation)
    model_reports = {
        name: full_bundle_report(validation, bundle) for name, bundle in bundles.items()
    }
    decision_tiers, block_predictions = _rule_reports(validation, bundles)
    word_block = block_from_bundle(bundles["word"])
    bert_block = block_from_bundle(bundles["bert"])
    report = {
        "experiment": "W23 precision-first ensemble experiments",
        "development_only": True,
        "data_contract": {
            "fit": "W11 train only",
            "comparison": "W11 validation only",
            "forbidden_for_selection": ["W11 test", "frozen adversarial", "owner golden", "W20"],
            "bert_checkpoint_source_head": W12_BERT_MODEL_HEAD,
            "meta_training": "3-fold W11-train OOF predictions only",
            "meta_feature_contract": list(META_FEATURE_CONTRACT),
        },
        "grid": grid_report,
        "models": model_reports,
        "decision_tiers": decision_tiers,
        "paired_word_bert": {
            "error_overlap": paired_error_overlap(validation, word_block, bert_block),
            "actual_intersection": next(
                item
                for item in decision_tiers["block"]["candidates"]
                if item["name"] == "word+bert-intersection"
            ),
            "actual_union": next(
                item
                for item in decision_tiers["block"]["candidates"]
                if item["name"] == "word+bert-union"
            ),
        },
        "evasion_probes": _evasion_report(train, text_models),
    }
    report["recommended_architecture"] = _recommendation(report)
    report["selected_block_prediction_count"] = sum(
        block_predictions[decision_tiers["block"]["selection"]["rule"]]
    )
    return report


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = run()
    json_path = REPORTS_DIR / "comparison.json"
    markdown_path = REPORTS_DIR / "comparison.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["recommended_architecture"], indent=2), flush=True)


if __name__ == "__main__":
    main()
