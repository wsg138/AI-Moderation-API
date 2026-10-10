"""Only invented messages/labels; never use sealed or real moderation evidence."""
from __future__ import annotations

import json
import os
import stat

import pytest

from workers.w12.dataset import ModerationExample
from workers.w25.contract import HEAD_VALUES, PredictionBundle
from workers.w25.decision_analytics import (
    REPO,
    _secret,
    audit_coverage,
    capture,
    capture_if_required,
    compare,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def _example(suffix: str = "1") -> ModerationExample:
    return ModerationExample(
        example_id="fake-case-" + suffix,
        serialized="fake harmless synthetic chat only",
        label="SAFE",
        action="ALLOW",
        review_priority="NONE",
        strike=False,
        containment="NONE",
        containment_duration_seconds=None,
        support_flow="NONE",
        channel_profile="minecraft_public",
        platform_hint="minecraft",
        domain="benign_chat",
        difficulty="hard",
        reason_codes=("benign_pvp",),
        family_id="synthetic-family-1",
    )


def _bundle(*, action: str = "ALLOW", count: int = 2) -> PredictionBundle:
    defaults = {
        "label": "SAFE",
        "action": action,
        "review_priority": "NONE",
        "strike": "false",
        "containment": "NONE",
        "support_flow": "NONE",
    }
    indices = {key: HEAD_VALUES[key].index(value) for key, value in defaults.items()}
    predictions = {key: [indices[key]] * count for key in HEAD_VALUES}
    probabilities = {
        key: [
            [float(index == indices[key]) for index in range(len(HEAD_VALUES[key]))]
            for _ in range(count)
        ]
        for key in HEAD_VALUES
    }
    return PredictionBundle(predictions, probabilities, [0.02] * count)


def _capture(tmp_path, run: str, action: str = "ALLOW"):
    return capture(
        [_example("1"), _example("2")], _bundle(action=action),
        secret=b"fake-secret-do-not-use-in-prod-1234567890",
        folder=tmp_path,
        run_id=run, candidate="fake-architecture", seed=42,
        model_sha=SHA_A, config_sha=SHA_B, policy="v1",
    )


def test_records_every_head_score_and_error_without_raw_chats(tmp_path) -> None:
    path = _capture(tmp_path, "run1", action="BLOCK")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 3
    assert rows[0]["count"] == 2
    assert rows[0]["model_artifact_sha256"] == SHA_A
    assert rows[1]["gold"]["action"] == "ALLOW"
    assert rows[1]["predicted"]["action"] == "BLOCK"
    assert rows[1]["head_errors"] == ["action"]
    assert "action" in rows[1]["probabilities"]
    assert len(rows[1]["probabilities"]["label"]) == len(HEAD_VALUES["label"])
    assert rows[1]["uncertainty"] == 0.02
    assert rows[1]["latency_ms"] is None
    assert rows[1]["gold_containment_duration_seconds"] is None
    assert rows[1]["predicted_containment_duration_seconds"] is None
    content = path.read_text(encoding="utf-8")
    assert "fake harmless synthetic chat" not in content
    assert "fake-case-1" not in content
    assert "synthetic-family-1" not in content
    assert rows[1]["case_key"] != rows[2]["case_key"]
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_separate_candidate_ledgers_support_cross_model_disagreements(tmp_path) -> None:
    first = _capture(tmp_path, "modelA")
    second = _capture(tmp_path, "modelB", action="BLOCK")
    report = compare([first, second])
    pair = report["pairwise"]["modelA_vs_modelB"]
    assert report["compared_cases"] == 2
    assert pair["action"]["disagreements"] == 2
    assert pair["label"]["disagreements"] == 0
    assert report["per_run"]["modelB"]["supervised_head_errors"]["action"] == 2
    assert report["not_an_accuracy_or_deployment_certificate"]


def test_existing_run_cannot_be_rewritten_or_silently_overwritten(tmp_path) -> None:
    path = _capture(tmp_path, "immutable")
    old = path.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        _capture(tmp_path, "immutable", action="BLOCK")
    assert path.read_bytes() == old


def test_no_raw_ids_even_when_two_models_share_pseudonym_key(tmp_path) -> None:
    a = _capture(tmp_path, "one")
    b = _capture(tmp_path, "two")
    a_rows = a.read_text(encoding="utf-8").splitlines()
    b_rows = b.read_text(encoding="utf-8").splitlines()
    assert json.loads(a_rows[1])["case_key"] == json.loads(b_rows[1])["case_key"]
    assert json.loads(a_rows[1])["family_key"] == json.loads(b_rows[1])["family_key"]


def test_differing_suite_or_mismatched_truth_is_rejected(tmp_path) -> None:
    a = _capture(tmp_path, "a")
    b = _capture(tmp_path, "b")
    rows = [json.loads(line) for line in b.read_text(encoding="utf-8").splitlines()]
    rows[0]["suite_fingerprint"] = "f" * 64
    b.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="distinct evaluation suites"):
        compare([a, b])
    rows[0]["suite_fingerprint"] = json.loads(a.read_text().splitlines()[0])[
        "suite_fingerprint"
    ]
    rows[1]["gold"]["action"] = "BLOCK"
    b.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Gold decisions differ"):
        compare([a, b])


def test_missing_examples_duplicate_examples_and_invalid_bundle_rejected(tmp_path) -> None:
    bad = [_example("1"), _example("1")]
    with pytest.raises(ValueError, match="Duplicate example"):
        capture(
            bad, _bundle(), secret=b"hello" * 10, folder=tmp_path,
            run_id="duplicate", candidate="test", seed=1,
            model_sha=SHA_A, config_sha=SHA_B, policy="v1",
        )
    with pytest.raises(ValueError, match="cardinality"):
        capture(
            [_example("1")], _bundle(), secret=b"hello" * 10, folder=tmp_path,
            run_id="length", candidate="test", seed=1,
            model_sha=SHA_A, config_sha=SHA_B, policy="v1",
        )


def test_private_destination_cannot_live_inside_public_repository(tmp_path) -> None:
    with pytest.raises(ValueError, match="cannot be inside"):
        capture(
            [_example("1"), _example("2")], _bundle(),
            secret=b"hello" * 10, folder=REPO,
            run_id="unsafe", candidate="test", seed=1,
            model_sha=SHA_A, config_sha=SHA_B, policy="v1",
        )
    with pytest.raises(ValueError, match="absolute"):
        _capture(tmp_path.relative_to(tmp_path.parent), "notabsolute")


def test_hmac_key_is_mandatory_and_never_in_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENTHUSIA_TEST_HMAC", "short")
    with pytest.raises(ValueError, match="at least 32"):
        _secret("ENTHUSIA_TEST_HMAC")
    monkeypatch.setenv("ENTHUSIA_TEST_HMAC", "s" * 40)
    key = _secret("ENTHUSIA_TEST_HMAC")
    path = capture(
        [_example("1"), _example("2")], _bundle(),
        secret=key, folder=tmp_path, run_id="secure",
        candidate="c", seed=1, model_sha=SHA_A, config_sha=SHA_B, policy="v1",
    )
    assert "s" * 40 not in path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="explicit ENTHUSIA"):
        _secret("AWS_SECRET_ACCESS_KEY")


def test_coverage_audit_detects_missing_unexpected_and_corrupted_runs(tmp_path) -> None:
    _capture(tmp_path, "expected1")
    missing = audit_coverage(tmp_path, ["expected1", "expected2"])
    assert not missing["complete"]
    assert missing["missing_runs"] == ["expected2"]
    second = _capture(tmp_path, "expected2")
    assert audit_coverage(tmp_path, ["expected1", "expected2"])["complete"]
    _capture(tmp_path, "unexpected")
    extras = audit_coverage(tmp_path, ["expected1", "expected2"])
    assert not extras["complete"]
    assert extras["unexpected_runs"] == ["unexpected"]
    second.write_text('{"bad":"ledger"}\n', encoding="utf-8")
    invalid = audit_coverage(tmp_path, ["expected1", "expected2", "unexpected"])
    assert invalid["invalid_runs"] == ["expected2"]
    assert not invalid["complete"]


def test_comparison_reports_harm_counts_and_channel_error_rates(tmp_path) -> None:
    good = _capture(tmp_path, "baseline")
    worse = _capture(tmp_path, "worse", action="BLOCK")
    report = compare([good, worse])
    assert report["per_run"]["worse"]["harmful_errors"]["wrongful_blocks"] == 2
    assert report["per_run"]["worse"]["harmful_errors"]["false_strikes"] == 0
    assert report["per_run"]["worse"]["channel_issues"]["minecraft_public"]["wrong"] == 2
    assert report["per_run"]["baseline"]["harmful_errors"]["wrongful_blocks"] == 0


def _required_environment(monkeypatch, private_dir) -> None:
    values = {
        "ENTHUSIA_ANALYTICS_MODE": "required",
        "ENTHUSIA_ANALYTICS_PRIVATE_DIR": str(private_dir),
        "ENTHUSIA_ANALYTICS_RUN_ID": "modelA-dev-42",
        "ENTHUSIA_ANALYTICS_CANDIDATE": "modelA",
        "ENTHUSIA_ANALYTICS_SEED": "42",
        "ENTHUSIA_ANALYTICS_MODEL_SHA256": SHA_A,
        "ENTHUSIA_ANALYTICS_CONFIG_SHA256": SHA_B,
        "ENTHUSIA_ANALYTICS_POLICY": "v1",
        "ENTHUSIA_ANALYTICS_SUITE": "development",
        "ENTHUSIA_ANALYTICS_HMAC_KEY": "s" * 40,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_required_shared_evaluator_archives_every_decision(tmp_path, monkeypatch) -> None:
    from workers.w25.evaluation import evaluate_candidate

    _required_environment(monkeypatch, tmp_path)
    examples = [_example("1"), _example("2")]
    report = evaluate_candidate(examples, _bundle())
    assert report["suite"]["n"] == 2
    path = tmp_path / "modelA-dev-42.jsonl"
    assert path.exists()
    assert len(path.read_text().splitlines()) == 3
    with pytest.raises(ValueError, match="already exists"):
        evaluate_candidate(examples, _bundle())


def test_required_mode_fails_incomplete_config_and_rejects_acceptance(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENTHUSIA_ANALYTICS_MODE", "required")
    with pytest.raises(ValueError, match="incomplete"):
        capture_if_required([_example("1"), _example("2")], _bundle())
    _required_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("ENTHUSIA_ANALYTICS_SUITE", "w20-acceptance")
    with pytest.raises(ValueError, match="declared"):
        capture_if_required([_example("1"), _example("2")], _bundle())
    assert list(tmp_path.glob("*.jsonl")) == []


def test_disabled_mode_does_not_consume_private_sources(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ENTHUSIA_ANALYTICS_MODE", raising=False)
    assert capture_if_required([_example("1"), _example("2")], _bundle()) is None
    assert list(tmp_path.iterdir()) == []


def test_incomplete_or_corrupted_ledgers_are_rejected(tmp_path) -> None:
    first = _capture(tmp_path, "first")
    second = _capture(tmp_path, "second")
    rows = second.read_text(encoding="utf-8").splitlines()
    second.write_text("\n".join(rows[:2]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="count mismatch"):
        compare([first, second])
