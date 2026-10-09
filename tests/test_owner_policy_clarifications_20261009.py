"""Structural checks for developer-only policy probes; not model accuracy."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OwnerClarificationTests(unittest.TestCase):
    def test_toy_cases_never_claim_gold(self) -> None:
        record = json.loads(
            (ROOT / "policy/owner-offline-probes-v1.1.json").read_text()
        )
        self.assertFalse(record["training_eligible"])
        self.assertFalse(record["model_validation_claim"])
        self.assertEqual(record["source"], "invented_toy_inputs_only")
        self.assertEqual(len(record["cases"]), 13)
        for case in record["cases"]:
            self.assertIn(case["expected_action"], {"ALLOW", "BLOCK", "REVIEW"})
            self.assertFalse(case["training_eligible"])
            self.assertTrue(case["review_only"])

    def test_private_escalation_is_distinct_from_ordinary_chat(self) -> None:
        cases = json.loads(
            (ROOT / "policy/owner-offline-probes-v1.1.json").read_text()
        )["cases"]
        by_id = {case["id"]: case for case in cases}
        self.assertEqual(
            by_id["ordinary_private_flirt"]["expected_action"], "ALLOW"
        )
        self.assertEqual(
            by_id["escalating_pressure_with_age_clue"]["expected_action"], "BLOCK"
        )


if __name__ == "__main__":
    unittest.main()
