"""Synthetic-W11 only: verify CPU baseline evidence recording end to end."""
from __future__ import annotations

import json

from workers.w25.development_probe import run


def test_w11_word_vs_character_probe_saves_complete_private_evidence(tmp_path) -> None:
    result = run(tmp_path, seed=17)
    assert result["source"].startswith("W11 train/validation only")
    assert result["train_count"] > 100
    assert result["development_count"] > 100
    assert result["ephemeral_hmac_not_saved"]
    assert result["not_proof_of_99pct_production_accuracy"]
    output = tmp_path / "w11-word-v-char-s17-comparison.json"
    assert output.is_file()
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["development_count"] == result["development_count"]
    assert saved["comparisons"]["oracle_action_ceiling"]["not_a_real_ensemble"]
    paths = [
        tmp_path / "w11-word-tfidf-s17.jsonl",
        tmp_path / "w11-char-tfidf-s17.jsonl",
    ]
    for path in paths:
        manifest, *records = (
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        )
        assert manifest["suite_name"] == "development"
        assert manifest["count"] == len(records) == result["development_count"]
        assert len(manifest["model_artifact_sha256"]) == 64
        assert len(manifest["input_hmac_fingerprint"]) == 64
        assert "serialized" not in records[0]
    headers = [
        json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        for path in paths
    ]
    assert headers[0]["input_hmac_fingerprint"] == headers[1]["input_hmac_fingerprint"]
