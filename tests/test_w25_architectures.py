from __future__ import annotations

import pytest
from moderation_api.model_serialization import ModelMessage, serialize_model_input

from workers.w12.dataset import ModerationExample
from workers.w25.attacks import (
    attack_serialized_variants,
    attack_variants,
    augment_training_examples,
)
from workers.w25.calibration import apply_bundle_temperatures, calibrate_bundle
from workers.w25.cascade import (
    CascadeThresholds,
    combine_cascade,
    finalize_cascade,
    fit_cascade_thresholds,
)
from workers.w25.contract import HEAD_NAMES, HEAD_VALUES, PredictionBundle
from workers.w25.selection import (
    DevelopmentScore,
    select_deberta_seed_aggregate,
    select_deberta_size,
    select_modernbert_seed_aggregate,
)
from workers.w25.selective import (
    SelectiveThresholds,
    apply_selective_policy,
    fit_selective_thresholds,
)


def _example(example_id: str, *, action: str = "ALLOW", strike: bool = False) -> ModerationExample:
    return ModerationExample(
        example_id=example_id,
        serialized="[0ms] A: test",
        label="SAFE",
        action=action,
        review_priority="NONE",
        strike=strike,
        containment="NONE",
        containment_duration_seconds=None,
        support_flow="NONE",
        channel_profile="minecraft_public",
        platform_hint="minecraft",
        domain="gameplay",
        difficulty="normal",
        reason_codes=(),
        family_id=None,
    )


def _bundle(action_rows: list[list[float]], strike_rows: list[list[float]]) -> PredictionBundle:
    probabilities = {}
    for head in HEAD_NAMES:
        width = len(HEAD_VALUES[head])
        probabilities[head] = [[1.0] + [0.0] * (width - 1) for _ in action_rows]
    probabilities["action"] = action_rows
    probabilities["strike"] = strike_rows
    predictions = {
        head: [max(range(len(row)), key=row.__getitem__) for row in rows]
        for head, rows in probabilities.items()
    }
    uncertainty = [1.0 - max(row) for row in action_rows]
    return PredictionBundle(predictions, probabilities, uncertainty)


def test_calibration_preserves_contract_and_returns_all_temperatures() -> None:
    bundle = _bundle([[0.8, 0.1, 0.1], [0.1, 0.8, 0.1]], [[0.9, 0.1], [0.2, 0.8]])
    examples = [_example("A"), _example("B", action="BLOCK", strike=True)]
    calibrated, temperatures = calibrate_bundle(bundle, examples)
    calibrated.validate()
    assert set(temperatures) == set(HEAD_NAMES)
    assert all(value > 0 for value in temperatures.values())


def test_cascade_verifier_can_block_without_stage_a_consensus() -> None:
    stage_a = _bundle([[0.60, 0.30, 0.10]], [[0.99, 0.01]])
    stage_b = _bundle([[0.02, 0.97, 0.01]], [[0.99, 0.01]])
    result, routed = combine_cascade(stage_a, stage_b, CascadeThresholds())
    assert routed == [True]
    assert HEAD_VALUES["action"][result.predictions["action"][0]] == "BLOCK"


def test_cascade_disagreement_defaults_to_review() -> None:
    stage_a = _bundle([[0.30, 0.60, 0.10]], [[0.99, 0.01]])
    stage_b = _bundle([[0.70, 0.20, 0.10]], [[0.99, 0.01]])
    result, routed = combine_cascade(stage_a, stage_b, CascadeThresholds())
    assert routed == [True]
    assert HEAD_VALUES["action"][result.predictions["action"][0]] == "REVIEW"
    assert result.predictions["strike"][0] == 0


def test_cascade_requires_both_stages_for_strike() -> None:
    stage_a = _bundle([[0.02, 0.97, 0.01]], [[0.01, 0.99]])
    stage_b = _bundle([[0.02, 0.97, 0.01]], [[0.20, 0.80]])
    result, _ = combine_cascade(stage_a, stage_b, CascadeThresholds())
    assert result.predictions["strike"][0] == 0


def test_attack_harness_is_deterministic_and_covers_required_character_families() -> None:
    first = attack_variants("sample message")
    second = attack_variants("sample message")
    assert first == second
    assert {
        "case",
        "spacing",
        "punctuation",
        "repetition",
        "leetspeak",
        "unicode_confusable",
        "zero_width",
        "keyboard_typo",
    } <= set(first)
    assert first["zero_width"] != "sample message"


def test_deberta_size_selection_uses_development_quality_only() -> None:
    xsmall = DevelopmentScore("deberta-v3-xsmall", 0.995, 0.91, 0.90, 0.88, 0.02, 8.0)
    small = DevelopmentScore("deberta-v3-small", 0.996, 0.89, 0.94, 0.90, 0.03, 13.0)
    assert select_deberta_size([xsmall, small]).name == "deberta-v3-small"


def test_frozen_temperature_application_reuses_development_fit() -> None:
    bundle = _bundle([[0.8, 0.1, 0.1]], [[0.9, 0.1]])
    calibrated, temperatures = calibrate_bundle(bundle, [_example("A")])
    reapplied = apply_bundle_temperatures(bundle, temperatures)
    assert reapplied.predictions == calibrated.predictions
    for head in HEAD_NAMES:
        for actual, expected in zip(
            reapplied.probabilities[head],
            calibrated.probabilities[head],
            strict=True,
        ):
            assert actual == pytest.approx(expected)


def test_deberta_selection_uses_seed_aggregate_not_best_single_run() -> None:
    xsmall = [
        DevelopmentScore("deberta-v3-xsmall", 1.0, 0.99, 0.99, 0.95, 0.01, 8.0),
        DevelopmentScore("deberta-v3-xsmall", 0.96, 0.90, 0.90, 0.88, 0.03, 8.0),
        DevelopmentScore("deberta-v3-xsmall", 0.96, 0.90, 0.90, 0.88, 0.03, 8.0),
    ]
    small = [
        DevelopmentScore("deberta-v3-small", 0.985, 0.94, 0.94, 0.91, 0.02, 13.0),
        DevelopmentScore("deberta-v3-small", 0.985, 0.94, 0.94, 0.91, 0.02, 13.0),
        DevelopmentScore("deberta-v3-small", 0.985, 0.94, 0.94, 0.91, 0.02, 13.0),
    ]
    selected = select_deberta_seed_aggregate(xsmall, small)
    assert selected.name == "deberta-v3-small"


def test_modernbert_serialization_selection_uses_seed_aggregate() -> None:
    raw = [
        DevelopmentScore("modernbert-raw", 0.99, 0.94, 0.94, 0.91, 0.02, 10.0)
        for _ in range(3)
    ]
    normalized = [
        DevelopmentScore(
            "modernbert-normalized",
            0.995,
            0.93,
            0.95,
            0.92,
            0.018,
            11.0,
        )
        for _ in range(3)
    ]
    selected = select_modernbert_seed_aggregate(raw, normalized)
    assert selected.name == "modernbert-normalized"


def test_selective_policy_routes_uncertain_block_to_review() -> None:
    bundle = _bundle([[0.15, 0.55, 0.30]], [[0.01, 0.99]])
    thresholds = SelectiveThresholds(
        block=0.90,
        strike=0.995,
        containment=0.999,
        uncertainty_review=0.40,
    )
    selected, abstained = apply_selective_policy(bundle, thresholds)
    assert abstained == [True]
    assert HEAD_VALUES["action"][selected.predictions["action"][0]] == "REVIEW"
    assert selected.predictions["strike"][0] == 0


def test_selective_policy_requires_block_before_strike() -> None:
    bundle = _bundle([[0.95, 0.03, 0.02]], [[0.001, 0.999]])
    thresholds = SelectiveThresholds(0.90, 0.995, 0.999, 0.50)
    selected, _ = apply_selective_policy(bundle, thresholds)
    assert HEAD_VALUES["action"][selected.predictions["action"][0]] == "ALLOW"
    assert selected.predictions["strike"][0] == 0


def test_threshold_fitting_fails_closed_when_precision_floor_is_unmet() -> None:
    examples = [
        _example("A"),
        _example("B"),
        _example("C", action="BLOCK", strike=True),
    ]
    bundle = _bundle(
        [[0.10, 0.85, 0.05], [0.10, 0.85, 0.05], [0.10, 0.85, 0.05]],
        [[0.01, 0.99], [0.01, 0.99], [0.01, 0.99]],
    )
    thresholds = fit_selective_thresholds(examples, bundle)
    assert thresholds.block == 1.0
    assert thresholds.strike == 1.0


def test_cascade_safety_override_survives_probability_recalibration() -> None:
    stage_a = _bundle([[0.30, 0.60, 0.10]], [[0.99, 0.01]])
    stage_b = _bundle([[0.70, 0.20, 0.10]], [[0.99, 0.01]])
    thresholds = CascadeThresholds()
    combined, routed = combine_cascade(stage_a, stage_b, thresholds)
    calibrated, _ = calibrate_bundle(combined, [_example("A")])
    final = finalize_cascade(
        calibrated.probabilities,
        stage_a,
        stage_b,
        routed,
        thresholds,
    )
    assert HEAD_VALUES["action"][final.predictions["action"][0]] == "REVIEW"
    assert final.predictions["strike"][0] == 0


def test_cascade_threshold_fitting_fails_closed_on_false_positive_pressure() -> None:
    examples = [
        _example("A"),
        _example("B"),
        _example("C", action="BLOCK", strike=True),
    ]
    stage_a = _bundle(
        [[0.05, 0.90, 0.05], [0.05, 0.90, 0.05], [0.05, 0.90, 0.05]],
        [[0.01, 0.99], [0.01, 0.99], [0.01, 0.99]],
    )
    stage_b = _bundle(
        [[0.05, 0.90, 0.05], [0.05, 0.90, 0.05], [0.05, 0.90, 0.05]],
        [[0.01, 0.99], [0.01, 0.99], [0.01, 0.99]],
    )
    thresholds = fit_cascade_thresholds(examples, stage_a, stage_b)
    assert thresholds.block == 1.0
    assert thresholds.strike == 1.0


def test_serialized_attacks_preserve_profile_and_context_markers() -> None:
    serialized = (
        "[PROFILE=minecraft_public]\n"
        "[A@-1000ms] hello there\n"
        "[B@+0ms] [TARGET] sample message"
    )
    variants = attack_serialized_variants(serialized)
    for mutated in variants.values():
        assert mutated.startswith(
            "[PROFILE=minecraft_public]\n[A@-1000ms] hello there\n"
            "[B@+0ms] [TARGET] "
        )
        assert mutated != serialized


def test_serialized_attacks_accept_canonical_runtime_serialization() -> None:
    serialized = serialize_model_input(
        "minecraft_public",
        [
            ModelMessage("player-a", -1000, "hello there"),
            ModelMessage("player-b", 0, "sample message"),
        ],
        1,
    )
    variants = attack_serialized_variants(serialized)
    assert variants
    assert all("[PROFILE=minecraft_public]" in value for value in variants.values())
    assert all("hello there" in value for value in variants.values())
    assert all("[TARGET]" in value for value in variants.values())


def test_train_only_augmentation_is_deterministic_and_label_preserving() -> None:
    serialized = serialize_model_input(
        "minecraft_public",
        [ModelMessage("player-a", 0, "sample message")],
        0,
    )
    example = ModerationExample(
        example_id="train-1",
        serialized=serialized,
        label="LOW_LEVEL_HARASSMENT",
        action="BLOCK",
        review_priority="NORMAL",
        strike=True,
        containment="NONE",
        containment_duration_seconds=None,
        support_flow="NONE",
        channel_profile="minecraft_public",
        platform_hint="minecraft",
        domain="harassment",
        difficulty="normal",
        reason_codes=("reviewed",),
        family_id="family-1",
    )
    first = augment_training_examples([example])
    second = augment_training_examples([example])
    assert first == second
    assert len(first) == 2
    generated = first[1]
    assert generated.example_id.startswith("train-1::w25-adv::")
    assert generated.family_id == "family-1"
    assert generated.serialized != example.serialized
    assert generated.label == example.label
    assert generated.action == example.action
    assert generated.strike == example.strike
