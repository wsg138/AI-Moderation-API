"""Regression tests: the freshness gate must reject stale final-byte reports."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.dataset_qa.freshness import batch_files, process, report_for, report_path


def _record() -> dict[str, object]:
    return {
        "example_id": "G10-0001",
        "policy_version": "v1",
        "source": "synthetic",
        "domain": "test",
        "difficulty": "hard",
        "platform_hint": "minecraft",
        "channel_profile": "minecraft_public",
        "messages": [{"speaker": "A", "offset_ms": 0, "text": "hello"}],
        "target_index": 0,
        "label": "SAFE",
        "action": "ALLOW",
        "review_priority": "NONE",
        "strike": False,
        "containment": "NONE",
        "containment_duration_seconds": None,
        "support_flow": "NONE",
        "reason_codes": ["insufficient_context"],
        "notes": "Synthetic regression fixture.",
    }


def test_render_is_repeatable(tmp_path: Path) -> None:
    path = tmp_path / "G10-test.jsonl"
    path.write_text(json.dumps(_record()) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected 500"):
        report_for(path)


def test_main_compatible_absent_batches(tmp_path: Path) -> None:
    assert process(tmp_path) == (0, 0)


def test_incomplete_batch_set_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "G10-only.jsonl").touch()
    with pytest.raises(ValueError, match="incomplete"):
        batch_files(tmp_path)


@pytest.mark.parametrize("change", ["label", "action", "reason_codes", "target_index"])
def test_changed_final_bytes_invalidate_report(
    tmp_path: Path, change: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "G10-fixture.jsonl"
    original = _record()
    modified = dict(original)
    modified[change] = {
        "label": "AMBIGUOUS_REVIEW",
        "action": "REVIEW",
        "reason_codes": ["reply_context"],
        "target_index": 1,
    }[change]
    data.write_text(json.dumps(original) + "\n", encoding="utf-8")
    from tools.dataset_qa import freshness

    monkeypatch.setattr(freshness, "EXPECTED", {"G10"})
    monkeypatch.setattr(freshness, "report_for", lambda path: json.loads(
        path.read_text(encoding="utf-8").splitlines()[0]
    ).get("label", "") + "|" + path.read_text(encoding="utf-8"))
    assert process(tmp_path, write=True) == (1, 1)
    assert process(tmp_path) == (0, 1)
    data.write_text(json.dumps(modified) + "\n", encoding="utf-8")
    assert process(tmp_path) == (1, 1)
    assert report_path(data).read_text(encoding="utf-8") != freshness.report_for(data)


def test_stale_report_is_rewritten_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.dataset_qa import freshness

    (tmp_path / "G10-fixture.jsonl").write_text("mock", encoding="utf-8")
    monkeypatch.setattr(freshness, "EXPECTED", {"G10"})
    monkeypatch.setattr(freshness, "report_for", lambda path: "fresh\n")
    report = tmp_path / "G10-report.md"
    report.write_text("old\n", encoding="utf-8")
    assert process(tmp_path) == (1, 1)
    assert report.read_text(encoding="utf-8") == "old\n"
    assert process(tmp_path, write=True) == (1, 1)
    assert process(tmp_path) == (0, 1)
