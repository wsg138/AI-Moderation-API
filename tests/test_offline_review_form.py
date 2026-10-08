"""Static safety/field contract for the offline blind-review HTML form."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

FORM = Path("docs/data-v2/BLIND-REVIEW-OFFLINE.html")
FIELDS = {
    "alias", "file", "status", "counter", "prev", "next", "export",
    "facts", "evidence", "semantic_label", "action", "review_priority",
    "strike", "containment", "containment_duration_seconds",
    "support_flow", "uncertainty", "save", "chat",
}


class FormTags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.externals: list[str] = []
        self.policies: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        props = dict(attrs)
        if props.get("id"):
            self.ids.add(str(props["id"]))
        for field in ("src", "href", "action"):
            value = props.get(field)
            if value and (value.startswith("http") or value.startswith("//")):
                self.externals.append(value)
        if tag == "meta" and props.get("http-equiv") == "Content-Security-Policy":
            self.policies.append(str(props.get("content", "")))


def test_offline_form_has_all_review_decision_fields() -> None:
    parser = FormTags()
    parser.feed(FORM.read_text(encoding="utf-8"))
    assert parser.ids >= FIELDS
    assert not parser.externals


def test_form_is_restricted_to_local_file_and_no_remote_connection() -> None:
    parser = FormTags()
    html = FORM.read_text(encoding="utf-8")
    parser.feed(html)
    assert len(parser.policies) == 1
    assert "default-src 'none'" in parser.policies[0]
    assert "connect-src 'none'" in parser.policies[0]
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "localStorage" not in html
    assert "training_eligible" not in html


def test_offline_form_rejects_more_facts_than_python_intake() -> None:
    html = FORM.read_text(encoding="utf-8")
    assert "facts.length>32" in html
    assert "facts.some(x=>x.length>200)" in html
    assert "if(!indices.length)" in html
