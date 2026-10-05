"""Deprecated W12 v1 held-out evaluator.

The original W11 test/frozen-adversarial/owner-golden partitions were opened
before a material W12 preprocessing correction. They are therefore development
evidence for the superseded v1 contract and MUST NOT be rerun or used to accept
w12-v2.

Final v2 acceptance is owned by issue #43 / PR #44 and requires a new,
independently built unseen W20 acceptance set.
"""

from __future__ import annotations


def run_heldout_evaluation(*_args: object, **_kwargs: object) -> None:
    """Refuse accidental reuse of contaminated v1 acceptance partitions."""
    raise RuntimeError(
        "W12 v1 held-out evaluation is superseded. "
        "Use the independently frozen W20 acceptance set for w12-v2."
    )


def main() -> None:
    run_heldout_evaluation()


if __name__ == "__main__":
    main()
