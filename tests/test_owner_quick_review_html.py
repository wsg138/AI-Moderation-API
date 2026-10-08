"""Offline self-contained HTML review page: no gold or future message leakage."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tools.check_complexity import analyze
from tools.data_v2.owner_quick_review_html import render_review_page


def _packet(identifier: str, target: str = "ordinary question") -> dict[str, Any]:
    return {
        "packet_id": identifier, "platform_hint": "minecraft",
        "channel_profile": "minecraft_public",
        "target_index": 1,
        "messages": [
            {"speaker": "A", "offset_ms": 0, "text": "earlier chat"},
            {"speaker": "B", "offset_ms": 5, "text": target},
        ],
    }


def test_review_html_is_offline_blinded_and_shows_action_legend() -> None:
    packet = _packet("R-" + "a" * 24)
    html = render_review_page([packet], "Targeted Round 4")
    assert '<meta charset="utf-8">' in html
    assert "ALLOW keeps it visible" in html
    assert "REVIEW flags for staff" in html
    assert "BLOCK removes it" in html
    assert "Q" in html
    assert packet["packet_id"] in html
    assert "data-round-label=" in html
    assert 'value="ALLOW"' in html
    assert 'value="REVIEW"' in html
    assert 'value="BLOCK"' in html
    assert "https://" not in html
    assert "candidate_action" not in html
    assert "training_eligible" not in html
    assert "source_file" not in html


def test_untrusted_text_is_html_escaped_and_cannot_close_script() -> None:
    text = '</script><img src=x onerror="alert(1)"> & end'
    packet = _packet("R-" + "b" * 24, text)
    result = render_review_page([packet], "Next </body><script>alert(1)</script>")
    assert "&lt;/script&gt;&lt;img" in result
    assert "&lt;/body&gt;&lt;script&gt;" in result
    assert text not in result
    assert result.count("<script>") == 1
    assert "<img src=x onerror=" not in result


def test_html_does_not_render_future_text_or_source_fields() -> None:
    packet = _packet("R-" + "c" * 24)
    source = {
        "source_file": "G10-hidden.jsonl", "label": "BLACKMAIL",
        "messages": packet["messages"] + [
            {"speaker": "C", "offset_ms": 10, "text": "FUTURE_SECRET"},
        ],
    }
    assert source["source_file"] not in render_review_page([packet], "Round 4")
    assert source["label"] not in render_review_page([packet], "Round 4")
    assert "FUTURE_SECRET" not in render_review_page([packet], "Round 4")


def test_repeated_or_malformed_packet_rejected() -> None:
    packet = _packet("R-" + "d" * 24)
    with pytest.raises(ValueError, match="duplicate"):
        render_review_page([packet, deepcopy(packet)], "Round 4")
    tampered = deepcopy(packet)
    tampered["gold_action"] = "BLOCK"
    with pytest.raises(ValueError, match="invalid blind packet"):
        render_review_page([tampered], "Round 4")


@pytest.mark.parametrize("count", [0, 121])
def test_review_size_bounds(count: int) -> None:
    packets = [_packet(f"R-{i:024x}") for i in range(count)]
    with pytest.raises(ValueError, match="1–120"):
        render_review_page(packets, "Round 4")


def test_embedded_script_preserves_copy_and_note_sanitization() -> None:
    result = render_review_page([_packet("R-" + "e" * 24)], "Round 4")
    assert "navigator.clipboard.writeText" in result
    assert "Q' + String(index + 1).padStart" in result
    assert "singleLine" in result
    assert r"/[\r\n|]+/g" in result


def test_review_page_implementation_respects_complexity_gate() -> None:
    assert analyze(Path("tools/data_v2/owner_quick_review_html.py")) == []
