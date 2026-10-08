"""Create an offline, action-only owner-review HTML page from blinded packets.

Never embed source labels, coordinator selection mappings or future messages.
"""
from __future__ import annotations

import argparse
import html
import os
import sys
from pathlib import Path

from tools.dataset_qa.blind_review import _outside_checkout
from tools.dataset_qa.review_assignments import _check_packet
from tools.dataset_qa.review_jsonl import read_jsonl

STYLE = """<style>
:root{font-family:system-ui,Segoe UI,sans-serif;color-scheme:dark}
body{max-width:800px;margin:auto;padding:24px 14px;background:#10151c;color:#ecf1fa}
header,.panel{background:#1a232e;padding:22px;border:1px solid #3b4a59;border-radius:16px}
h1{font-size:1.45rem;margin-top:0}h2{font-size:1.18rem}
p,.meta{line-height:1.5;color:#c8d3e1}.meta{font-size:.85rem}
label{display:block;margin:10px 0}input,textarea,button{font:inherit}
input[type=text],textarea{background:#10151c;border:1px solid #617286;color:#fff;
border-radius:7px;padding:10px;box-sizing:border-box;width:100%}
textarea{min-height:60px;resize:vertical}
.message{background:#111923;border-left:3px solid #6684b2;border-radius:5px;
padding:11px;white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0}
.message.target{border-left-color:#edbd70;background:#27251f}
.choices{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}
.choices label{background:#273445;border:1px solid #435468;padding:12px;
border-radius:10px;cursor:pointer;text-align:center}
.choices label:has(input:checked){outline:2px solid #9bc5ff}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
button{background:#466da0;color:white;border:0;padding:12px 18px;
border-radius:8px;cursor:pointer}
button.secondary{background:#354456}button:disabled{opacity:.4}
#output{min-height:180px;margin-top:12px}
#status{min-height:30px;color:#d6dbe4}
footer{font-size:.8rem;color:#aebccc;margin:20px 0}
@media(max-width:500px){.choices{grid-template-columns:1fr}}
</style>"""

SCRIPT = r"""<script>
'use strict';
const cards = Array.from(document.querySelectorAll('.case'));
const progress = document.getElementById('progress');
const status = document.getElementById('status');
let current = 0;
function answerFor(card) {
  return card.querySelector('input[type=radio]:checked')?.value || '';
}
function render() {
  cards.forEach((card, index) => { card.hidden = index !== current; });
  const done = cards.filter(answerFor).length;
  progress.textContent = 'Question ' + (current + 1) + ' of ' + cards.length
    + ' • ' + done + ' answered';
  document.getElementById('previous').disabled = current === 0;
  document.getElementById('next').disabled = current + 1 === cards.length;
}
function move(delta) { current = Math.max(0, Math.min(cards.length - 1, current + delta)); render(); }
function choose(value) {
  cards[current].querySelector('input[value="' + value + '"]').checked = true;
  render();
}
function singleLine(text) { return text.replace(/[\r\n|]+/g, ' ').trim(); }
function exportText() {
  const reviewer = singleLine(document.getElementById('reviewer').value);
  if (!reviewer) { status.textContent = 'Enter your reviewer name first.'; return null; }
  const missing = cards.findIndex(card => !answerFor(card));
  if (missing >= 0) {
    current = missing; render();
    status.textContent = 'Answer every case before copying. Missing Q'
      + String(missing + 1).padStart(2, '0');
    return null;
  }
  const label = document.body.dataset.roundLabel;
  const lines = cards.map((card, index) => {
    const note = singleLine(card.querySelector('textarea').value);
    return 'Q' + String(index + 1).padStart(2, '0') + ' | '
      + card.dataset.packetId + ' | ' + answerFor(card)
      + (note ? ' | Why: ' + note : '');
  });
  return ['ENTHUSIA AI MODERATION — QUICK REVIEW', 'Name: ' + reviewer,
    'Round: ' + label + ' (' + cards.length + ' new public synthetic cases)',
    '', ...lines, '', 'End of review'].join('\n');
}
async function copyAnswers() {
  const text = exportText();
  if (text === null) return;
  const area = document.getElementById('output');
  area.value = text;
  try { await navigator.clipboard.writeText(text); status.textContent = 'Answers copied.'; }
  catch (_) { area.focus(); area.select(); status.textContent = 'Select and copy the text below.'; }
}
document.getElementById('previous').addEventListener('click', () => move(-1));
document.getElementById('next').addEventListener('click', () => move(1));
document.getElementById('copy').addEventListener('click', copyAnswers);
cards.forEach(card => card.addEventListener('change', render));
document.addEventListener('keydown', event => {
  if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
  if (event.key === '1') choose('ALLOW');
  if (event.key === '2') choose('REVIEW');
  if (event.key === '3') choose('BLOCK');
  if (event.key === 'ArrowRight') move(1);
  if (event.key === 'ArrowLeft') move(-1);
});
render();
</script>"""


def _validate_packets(packets: list[dict[str, object]]) -> None:
    if not 1 <= len(packets) <= 120:
        raise ValueError("offline owner review requires 1–120 blinded cases")
    identifiers = [_check_packet(packet) for packet in packets]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate blinded packet IDs")


def _conversation(packet: dict[str, object]) -> str:
    messages = packet["messages"]
    assert isinstance(messages, list)
    blocks: list[str] = []
    for index, message in enumerate(messages):
        css = "message target" if index == packet["target_index"] else "message"
        speaker = html.escape(str(message["speaker"]))
        text = html.escape(str(message["text"]))
        blocks.append(f'<div class="{css}"><b>{speaker}:</b> {text}</div>')
    return "\n".join(blocks)


def _case(packet: dict[str, object], index: int) -> str:
    identifier = html.escape(str(packet["packet_id"]), quote=True)
    scope = html.escape(str(packet["channel_profile"]))
    conversation = _conversation(packet)
    options = "\n".join(
        f'<label><input type="radio" name="a{index}" value="{value}"> {value}</label>'
        for value in ("ALLOW", "REVIEW", "BLOCK")
    )
    return (
        f'<section class="case panel" data-packet-id="{identifier}" hidden>'
        f'<h2>Question {index + 1}</h2><p class="meta">Channel: {scope}</p>'
        f'{conversation}<div class="choices">{options}</div>'
        '<label>Optional explanation<textarea maxlength="220" '
        'placeholder="Why? (optional)"></textarea></label></section>'
    )


def render_review_page(packets: list[dict[str, object]], round_label: str) -> str:
    """Render only vetted packet fields as escaped static HTML; no network calls."""
    _validate_packets(packets)
    if not 1 <= len(round_label) <= 60:
        raise ValueError("invalid round label")
    label = html.escape(round_label, quote=True)
    cases = "\n".join(_case(packet, number) for number, packet in enumerate(packets))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Enthusia AI Moderation — Blind Review</title>'
        + STYLE + '</head><body data-round-label="' + label + '">'
        '<header><h1>Enthusia AI Moderation — Blind Review</h1>'
        '<p>Review the message with earlier conversation only. '
        'ALLOW keeps it visible; REVIEW flags for staff; BLOCK removes it.</p>'
        '<label>Reviewer name<input id="reviewer" type="text" maxlength="50" '
        'placeholder="Your name" autocomplete="off"></label>'
        '<p id="progress" role="status"></p></header>'
        + cases + '<div class="actions">'
        '<button type="button" id="previous" class="secondary">Previous</button>'
        '<button type="button" id="next">Next</button>'
        '<button type="button" id="copy">Copy answers</button></div>'
        '<p id="status" aria-live="polite"></p><textarea id="output" readonly '
        'aria-label="Answers to copy"></textarea>'
        '<footer>Offline page. Your answers stay in this browser until copied. '
        'Keys: 1 ALLOW, 2 REVIEW, 3 BLOCK, arrows navigate. '
        'No information is submitted over the network.</footer>'
        + SCRIPT + '</body></html>'
    )


def _write_html(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-input", type=Path, required=True)
    parser.add_argument("--html-out", type=Path, required=True)
    parser.add_argument("--round-label", default="Targeted Round 4")
    args = parser.parse_args(argv)
    try:
        source = _outside_checkout(args.packet_input)
        destination = _outside_checkout(args.html_out)
        if source == destination or destination.exists():
            raise ValueError("review page output exists or aliases packets")
        page = render_review_page(read_jsonl(source), args.round_label)
        _write_html(destination, page)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Owner review page refused: {exc}", file=sys.stderr)
        return 2
    print("Prepared offline blinded action-only review page; no labels admitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
