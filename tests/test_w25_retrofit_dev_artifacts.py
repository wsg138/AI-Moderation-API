"""Only invented evaluation records: verify W25 saved-bundle provenance gates."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from workers.w12.dataset import ModerationExample
from workers.w25.artifacts import save_bundle
from workers.w25.contract import HEAD_VALUES, PredictionBundle
from workers.w25.evaluation import suite_fingerprint
from workers.w25.retrofit_dev_artifacts import Source, _preflight, retrofit


def _examples() -> list[ModerationExample]:
    return [
        ModerationExample(
            example_id=f"fictional-{i}", serialized=f"mock speech {i}",
            label="SAFE", action="ALLOW", review_priority="NONE",
            strike=False, containment="NONE", containment_duration_seconds=None,
            support_flow="NONE", channel_profile="minecraft_public",
            platform_hint="minecraft", domain="benign", difficulty="hard",
            reason_codes=(), family_id=f"fiction-{i}",
        )
        for i in range(30)
    ]


def _bundle(changed: bool) -> PredictionBundle:
    names = {
        "label": "SAFE", "action": "BLOCK" if changed else "ALLOW",
        "review_priority": "NONE", "strike": "false",
        "containment": "NONE", "support_flow": "NONE",
    }
    predictions = {
        head: [HEAD_VALUES[head].index(value)] * 30
        for head, value in names.items()
    }
    scores = {
        head: [[float(index == value) for index in range(len(HEAD_VALUES[head]))]
               for value in values]
        for head, values in predictions.items()
    }
    return PredictionBundle(predictions, scores, [0.1] * 30)


def _saved_source(tmp_path: Path, name: str, changed: bool) -> Source:
    directory = tmp_path / name
    directory.mkdir()
    save_bundle(directory / "dev-selective-bundle.json", _bundle(changed))
    (directory / "dev-report.json").write_text(json.dumps({
        "suite": {"n": 30, "fingerprint": suite_fingerprint(_examples())},
    }), encoding="utf-8")
    return Source(name, name)


def test_retrofit_rechecks_frozen_dev_fingerprint_before_writing(tmp_path, monkeypatch):
    archive = tmp_path / "archive"
    archive.mkdir()
    a = _saved_source(archive, "a", False)
    b = _saved_source(archive, "b", True)
    monkeypatch.setattr(
        "workers.w25.retrofit_dev_artifacts.SOURCES", (a, b),
    )
    monkeypatch.setattr(
        "workers.w25.retrofit_dev_artifacts.load_development_data",
        lambda include_admitted: ([], _examples()),
    )
    output = tmp_path / "private"
    output.mkdir()
    result = retrofit(archive, output)
    assert result["source_candidate_count"] == 2
    assert result["sample_count"] == 30
    assert result["neural_inference_or_training_performed"] is False
    assert result["model_weights_not_reauthenticated"]
    assert (output / "retrofitted-w25-development-comparison.json").is_file()
    names = ["retro-a-s138.jsonl", "retro-b-s138.jsonl"]
    for name in names:
        header = json.loads((output / name).read_text().splitlines()[0])
        assert header["model_artifact_kind"] == "saved_prediction_bundle"
        assert header["configuration_artifact_kind"] == "saved_evaluation_report"
    assert "mock speech" not in (output / names[0]).read_text()


def test_changed_gold_hash_refuses_retrofit_before_any_capture(tmp_path, monkeypatch):
    archive = tmp_path / "archive"
    archive.mkdir()
    a = _saved_source(archive, "a", False)
    monkeypatch.setattr(
        "workers.w25.retrofit_dev_artifacts.SOURCES", (a,),
    )
    report = archive / "a" / "dev-report.json"
    report.write_text(json.dumps({
        "suite": {"n": 30, "fingerprint": "f" * 64}
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        _preflight(archive.resolve(), _examples())
    assert len(list(archive.glob("**/*.jsonl"))) == 0
