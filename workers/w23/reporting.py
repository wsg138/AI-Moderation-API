"""Human-readable W23 experiment report rendering."""

from __future__ import annotations

from typing import Any


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def _model_rows(report: dict[str, Any]) -> list[str]:
    rows = []
    for name, metrics in report["models"].items():
        block = metrics["runtime_visibility_binary"]
        strike = metrics["strike"]["per_class"][1]
        mute = metrics["containment"]["per_class"][1]
        rows.append(
            "| "
            + " | ".join(
                (
                    name,
                    _pct(metrics["semantic_label"]["accuracy"]),
                    _pct(metrics["semantic_label"]["macro_f1"]),
                    _pct(block["block_precision"]),
                    _pct(block["block_recall"]),
                    _pct(strike["precision"]),
                    _pct(strike["recall"]),
                    _pct(mute["precision"]),
                    _pct(mute["recall"]),
                )
            )
            + " |"
        )
    return rows


def _auto_summary(label: str, result: dict[str, Any]) -> str:
    if "hypothetical_rule" in result:
        return (
            f"- Hypothetical auto {label}: \x60{result['hypothetical_rule']}\x60, "
            + f"precision {_pct(result['precision'])}, recall {_pct(result['recall'])}, "
            + f"recall sacrifice {_pct(result['recall_sacrifice_vs_baseline'])}; disabled."
        )
    return (
        f"- Hypothetical auto {label}: no rule reached the precision floor; "
        + f"best precision {_pct(result['best_observed_precision'])}, "
        + f"recall {_pct(result['best_observed_recall'])}, recall sacrifice "
        + f"{_pct(result['recall_sacrifice_vs_baseline'])}."
    )


def _decision_lines(report: dict[str, Any]) -> list[str]:
    tiers = report["decision_tiers"]
    recommended = report["recommended_architecture"]
    robustness = recommended["evasion_post_selection_gate"]
    return [
        f"- Screening/review: \x60{tiers['screening']['selection']['rule']}\x60.",
        f"- BLOCK: \x60{tiers['block']['selection']['rule']}\x60.",
        f"- STRIKE: \x60{tiers['strike']['selection']['rule']}\x60.",
        "- Automatic punishment: disabled; calculations are hypothetical only.",
        _auto_summary("STRIKE", tiers["strike"]["hypothetical_auto_punishment"]),
        _auto_summary("MUTE", tiers["containment_mute"]["hypothetical_auto_punishment"]),
        "- Replace current W12 candidate: "
        + f"\x60{recommended['justifies_replacing_current_w12_candidate']}\x60 "
        + f"(BLOCK precision delta {_pct(recommended['precision_gain_vs_w12_word'])}, "
        + f"validation recall ratio {_pct(recommended['recall_ratio_vs_w12_word'])}).",
        "- Post-selection evasion gate: "
        + f"\x60{robustness['passed']}\x60 "
        + f"(recall ratio {_pct(robustness['recall_ratio'])}, "
        + f"floor {_pct(robustness['recall_ratio_floor'])}).",
    ]


def _paired_table(report: dict[str, Any]) -> list[str]:
    paired = report["paired_word_bert"]
    intersection = paired["actual_intersection"]
    union = paired["actual_union"]
    return [
        "| Rule | BLOCK precision | BLOCK recall | BLOCK F1 |",
        "| --- | ---: | ---: | ---: |",
        f"| Word+BERT intersection | {_pct(intersection['precision'])} | "
        + f"{_pct(intersection['recall'])} | {_pct(intersection['f1'])} |",
        f"| Word+BERT union | {_pct(union['precision'])} | "
        + f"{_pct(union['recall'])} | {_pct(union['f1'])} |",
    ]


def _overlap_lines(report: dict[str, Any]) -> list[str]:
    overlap = report["paired_word_bert"]["error_overlap"]
    fp = overlap["false_positives"]
    fn = overlap["false_negatives"]
    return [
        f"- BLOCK prediction disagreements: {overlap['prediction_disagreements']}.",
        f"- False positives: word {fp['left']}, BERT {fp['right']}, "
        + f"shared {fp['intersection']}, union {fp['union']}.",
        f"- False negatives: word {fn['left']}, BERT {fn['right']}, "
        + f"shared {fn['intersection']}, union {fn['union']}.",
    ]


def _evasion_lines(report: dict[str, Any]) -> list[str]:
    probes = report["evasion_probes"]
    lines = [
        f"Train-derived deterministic probe sample: {probes['sample_size']} examples.",
        "",
        "| Model/rule | Original BLOCK recall | Worst transformed BLOCK recall |",
        "| --- | ---: | ---: |",
    ]
    for model, results in probes["models"].items():
        original = results["original"]["block"]["recall"]
        transformed = [results[name]["block"]["recall"] for name in probes["transforms"]]
        lines.append(f"| {model} | {_pct(original)} | {_pct(min(transformed))} |")
    selected = probes["selected_block_rule"]
    results = selected["results"]
    original = results["original"]["recall"]
    transformed = [results[name]["recall"] for name in probes["transforms"]]
    lines.append(f"| selected {selected['rule']} | {_pct(original)} | {_pct(min(transformed))} |")
    gate = selected["post_selection_gate"]
    lines.extend(
        [
            "",
            f"- Post-selection robustness gate passed: `{gate['passed']}`.",
            f"- Selected/W12 worst-transformed recall ratio: {_pct(gate['recall_ratio'])} "
            + f"(floor {_pct(gate['recall_ratio_floor'])}).",
        ]
    )
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# W23 Precision-First Ensemble Experiments",
        "",
        "Development experiment only. Fit data: W11 train. Comparison data: W11 validation.",
        "W11 test, frozen adversarial, owner golden, and W20 were not used for selection.",
        "",
        "## Model comparison",
        "",
        "| Model | Semantic accuracy | Macro F1 | BLOCK precision | BLOCK recall | "
        + "STRIKE precision | STRIKE recall | MUTE precision | MUTE recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *_model_rows(report),
        "",
        "## Actual paired Word TF-IDF + BERT behavior",
        "",
        *_paired_table(report),
        "",
        *_overlap_lines(report),
        "",
        "## Selected development operating points",
        "",
        *_decision_lines(report),
        "",
        "## Train-derived evasion probes",
        "",
        *_evasion_lines(report),
        "",
        "## Selection contract",
        "",
        "- Character and combined TF-IDF grids are selected on W11 validation only.",
        "- Meta-classifier training uses 3-fold W11-train OOF predictions only.",
        "- BLOCK requires the predeclared recall/slice-FPR guard when an eligible rule exists.",
        (
            "- Train-derived evasion probes are not selection data; they act only as a "
            + "post-selection deployment gate against severe robustness regressions."
        ),
        "- STRIKE is BLOCK-gated and selected with a stricter precision-first objective.",
        "- No production service, punishment behavior, or W20 acceptance evidence is changed.",
        "",
    ]
    return "\n".join(lines)
