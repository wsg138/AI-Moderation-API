"""Isolated, optional fastText LID-176 model pilot; no production import.

The official lid.176.ftz model is CC-BY-SA-3.0. Fetch separately and
SHA-256-pin before loading. This is a heuristic research adapter: scores
and thresholds are NOT validated for automatic moderation decisions.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .language_rule_probe import evaluate_rule, language_only_effects, load_rule

MODEL_SHA256 = "8f3472cfe8738a7b6099e8e999c3cbfae0dcd15696aac7d7738a8039db603e83"
MODEL_BYTES = 938013
MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
FIXTURES = Path("data/policy-probes/fasttext-language-pilot-v1.jsonl")
PROBES_MAX = 100
GREETING_EXCEPTIONS = frozenset({"hola", "bonjour", "ciao", "gracias", "buenas", "salut"})
LABEL_PREFIX = "__label__"
MIN_BLOCK_WORDS = 5
CANDIDATE_SCORE = 0.90
CANDIDATE_MARGIN = 0.30


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verified_model_file(path: Path) -> Path:
    """Require exact known upstream bytes, not arbitrary or unchecked weights."""
    resolved = path.resolve(strict=True)
    _require(resolved.is_file() and resolved.stat().st_size == MODEL_BYTES,
             "invalid fastText LID model size")
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    _require(digest == MODEL_SHA256, "fastText LID model SHA-256 mismatch")
    return resolved


def load_fasttext(path: Path) -> Any:
    """Import optional package only for a separately invoked pilot."""
    checked = verified_model_file(path)
    module = importlib.import_module("fasttext")
    return module.load_model(str(checked))


def _prepared_text(text: str) -> str | None:
    if not isinstance(text, str) or len(text) > 500:
        return None
    clean = " ".join(text.split())
    if not clean or "\x00" in text:
        return None
    return clean


def _valid_scores(top: float, second: float) -> bool:
    return (
        math.isfinite(top) and math.isfinite(second)
        and 0 <= second <= top <= 1
        and top - second >= CANDIDATE_MARGIN
    )


def _predict(model: Any, text: str) -> tuple[str, float, float] | None:
    raw_labels, raw_scores = model.predict(text, k=2)
    if len(raw_labels) != 2 or len(raw_scores) != 2:
        return None
    top, second = float(raw_scores[0]), float(raw_scores[1])
    if not _valid_scores(top, second):
        return None
    label = raw_labels[0]
    if not isinstance(label, str) or not label.startswith(LABEL_PREFIX):
        return None
    code = label[len(LABEL_PREFIX):]
    if re.fullmatch(r"[a-z]{2,3}", code) is None:
        return None
    return code, top, second


def _unsafe_for_language_block(words: list[str], text: str) -> bool:
    return len(words) < 3 or "/" in text or "@" in text or "§" in text


def _assessment_from_prediction(
    prediction: tuple[str, float, float] | None, word_count: int,
) -> str:
    if prediction is None or prediction[1] < CANDIDATE_SCORE:
        return "unreliably_assessed_or_ambiguous"
    if prediction[0] == "en":
        return "primarily_english"
    if word_count < MIN_BLOCK_WORDS:
        return "unreliably_assessed_or_ambiguous"
    return "primarily_non_english"


def candidate_assessment(model: Any, text: str) -> str:
    """Deliberately conservative, *unvalidated* candidate, never live blocking."""
    clean = _prepared_text(text)
    if clean is None:
        return "unreliably_assessed_or_ambiguous"
    if clean.casefold().strip("!?., ") in GREETING_EXCEPTIONS:
        return "occasional_foreign_words_or_short_greetings"
    words = [word for word in re.findall(r"\b\w+\b", clean) if word.isalpha()]
    if _unsafe_for_language_block(words, clean):
        return "unreliably_assessed_or_ambiguous"
    return _assessment_from_prediction(_predict(model, clean), len(words))


def _fixture(row: object) -> dict[str, str]:
    _require(isinstance(row, dict) and set(row) == {
        "probe_id", "channel_profile", "text", "illustrative_expected_action",
    }, "unrecognized pilot probe schema")
    _require(all(isinstance(v, str) for v in row.values()), "invalid pilot probe")
    _require(row["probe_id"].startswith("pilot-"), "not a public developer pilot")
    _require(row["illustrative_expected_action"] in {"ALLOW", "BLOCK"},
             "pilot expected action must be allowed or blocked")
    _require(len(row["text"]) <= 500, "pilot text too long")
    return row


def run_pilot(model: Any, samples: Path = FIXTURES) -> dict[str, object]:
    _require(samples.resolve().is_relative_to(Path.cwd().resolve()),
             "only public in-repository pilot probes allowed")
    raw = samples.read_text(encoding="utf-8").splitlines()
    _require(0 < len(raw) <= PROBES_MAX, "unexpected public probe count")
    rule = load_rule()
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    for line in raw:
        row = _fixture(json.loads(line))
        _require(row["probe_id"] not in seen, "duplicate public pilot ID")
        seen.add(row["probe_id"])
        assessment = candidate_assessment(model, row["text"])
        action = evaluate_rule(rule, row["channel_profile"], assessment)
        _require(all(v == "NONE" for k, v in
                     language_only_effects(rule, action).items()
                     if k != "message_action"), "language-only penalty")
        counts[f"action_{action}"] += 1
        if action == "BLOCK" and row["illustrative_expected_action"] == "ALLOW":
            counts["illustrative_false_blocks"] += 1
        if action == "ALLOW" and row["illustrative_expected_action"] == "BLOCK":
            counts["illustrative_false_allows"] += 1
    return {
        "trial_model": "fasttext_lid_176_ftz_sha256_pinned",
        "probes": len(seen),
        "outcomes": dict(sorted(counts.items())),
        "toy_examples_only": True,
        "independent_human_gold_evaluated": False,
        "accuracy_validated": False,
        "thresholds_validated": False,
        "approved_to_block_live_chat": False,
        "training_eligible": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--samples", type=Path, default=FIXTURES)
    args = parser.parse_args(argv)
    try:
        result = run_pilot(load_fasttext(args.model), args.samples)
    except (OSError, ImportError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        print(f"Offline fastText candidate pilot unavailable: {type(exc).__name__}",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
