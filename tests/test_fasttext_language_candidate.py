"""Regression tests for the optional real fastText candidate, no runtime hook."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2 import fasttext_language_candidate as candidate


class FakeModel:
    def __init__(self, label: str, first: float = 0.96, second: float = 0.02) -> None:
        self.label = label
        self.first = first
        self.second = second

    def predict(self, text: str, k: int) -> tuple[tuple[str, str], tuple[float, float]]:
        assert k == 2
        assert "\n" not in text
        return (f"__label__{self.label}", "__label__other"), (self.first, self.second)


@pytest.mark.parametrize(("text", "expected"), [
    ("hola", "occasional_foreign_words_or_short_greetings"),
    ("bonjour!", "occasional_foreign_words_or_short_greetings"),
    ("gg wp", "unreliably_assessed_or_ambiguous"),
    ("/warp spawn and go find diamonds", "unreliably_assessed_or_ambiguous"),
    ("@someone can you help my base", "unreliably_assessed_or_ambiguous"),
    ("", "unreliably_assessed_or_ambiguous"),
    ("my username is SeñorLobo", "primarily_english"),
])
def test_english_examples_are_never_classified_foreign_by_word_guess(
    text: str, expected: str,
) -> None:
    assert candidate.candidate_assessment(FakeModel("en"), text) == expected


def test_clear_long_foreign_candidate_requires_model_evidence() -> None:
    spanish = "Estoy buscando diamantes en la mina ahora mismo"
    assert candidate.candidate_assessment(FakeModel("es"), spanish) == (
        "primarily_non_english"
    )


@pytest.mark.parametrize(("text", "label", "first", "second"), [
    ("Estoy buscando diamantes en la mina", "es", 0.80, 0.10),
    ("Estoy buscando diamantes en la mina", "es", 0.92, 0.70),
    ("bonjour je suis", "fr", 0.99, 0.001),
])
def test_low_confidence_low_margin_or_short_foreign_abstains(
    text: str, label: str, first: float, second: float,
) -> None:
    assert candidate.candidate_assessment(FakeModel(label, first, second), text) == (
        "unreliably_assessed_or_ambiguous"
    )


def test_large_or_malformed_input_cannot_block() -> None:
    assert candidate.candidate_assessment(FakeModel("es"), "abc " * 130) == (
        "unreliably_assessed_or_ambiguous"
    )
    assert candidate.candidate_assessment(FakeModel("es"), "bonjour\x00bad phrase") == (
        "unreliably_assessed_or_ambiguous"
    )


def test_invalid_model_prediction_cannot_trigger_block() -> None:
    assert candidate.candidate_assessment(
        FakeModel("es", float("nan"), 0.01),
        "Estoy buscando diamantes en la mina ahora mismo",
    ) == "unreliably_assessed_or_ambiguous"


def test_model_hash_and_size_must_both_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"tiny-test-model"
    file = tmp_path / "candidate.ftz"
    file.write_bytes(payload)
    monkeypatch.setattr(candidate, "MODEL_BYTES", len(payload))
    monkeypatch.setattr(candidate, "MODEL_SHA256", hashlib.sha256(payload).hexdigest())
    assert candidate.verified_model_file(file) == file.resolve()
    file.write_bytes(b"x" + payload)
    with pytest.raises(ValueError, match="size"):
        candidate.verified_model_file(file)
    file.write_bytes(b"X" + payload[1:])
    with pytest.raises(ValueError, match="SHA-256"):
        candidate.verified_model_file(file)


def test_public_toy_pilot_stays_aggregate_and_never_approves_runtime() -> None:
    class ConstantEnglish(FakeModel):
        pass

    result = candidate.run_pilot(ConstantEnglish("en"))
    assert result["probes"] == 34
    assert result["toy_examples_only"] is True
    assert result["independent_human_gold_evaluated"] is False
    assert result["accuracy_validated"] is False
    assert result["thresholds_validated"] is False
    assert result["approved_to_block_live_chat"] is False
    assert result["training_eligible"] is False
    assert set(result) == {
        "trial_model", "probes", "outcomes", "toy_examples_only",
        "independent_human_gold_evaluated", "accuracy_validated",
        "thresholds_validated", "approved_to_block_live_chat", "training_eligible",
    }


def test_candidate_import_is_optional_and_offline_only() -> None:
    assert analyze(Path("tools/data_v2/fasttext_language_candidate.py")) == []
