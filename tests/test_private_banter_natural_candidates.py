"""Developer-only checks for unadmitted private-banter contrast candidates."""
import json
import unittest
from collections import Counter

from tools.data_v2.private_banter_natural_candidates import OUT, build_candidates
from tools.dataset_qa.asof_input import serialize_as_of_target


class NaturalBanterCandidatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = build_candidates()

    def test_count_and_action_diversity(self) -> None:
        self.assertEqual(len(self.rows), 52)
        self.assertEqual(
            Counter(r["candidate_action"] for r in self.rows),
            {"ALLOW": 40, "BLOCK": 11, "REVIEW": 1},
        )
        self.assertEqual(len({r["family_id"] for r in self.rows}), 20)

    def test_unadmitted_no_punishment_data(self) -> None:
        for row in self.rows:
            self.assertFalse(row["training_eligible"])
            self.assertFalse(row["semantic_label_verified"])
            self.assertFalse(row["owner_reviewed"])
            self.assertNotIn("strike", row)
            self.assertNotIn("mute", row)

    def test_as_of_target_projection(self) -> None:
        for row in self.rows:
            packet = serialize_as_of_target(row)
            self.assertEqual(packet["messages"], row["messages"])
            self.assertEqual(row["target_index"], len(row["messages"]) - 1)
            self.assertNotIn("candidate_action", packet)
            self.assertNotIn("family_id", packet)

    def test_owner_calibrated_contrasts(self) -> None:
        expected = {
            "reciprocal": "ALLOW",
            "short_stop": "ALLOW",
            "first_continuation": "ALLOW",
            "repeated_unwanted": "BLOCK",
            "apology": "ALLOW",
        }
        for n in range(1, 9):
            family = [r for r in self.rows if r["family_id"] == f"PMN-{n}"]
            self.assertEqual(
                {r["contrast_phase"]: r["candidate_action"] for r in family},
                expected,
            )

    def test_realistic_short_stop_and_no_contact_examples(self) -> None:
        by_id = {r["example_id"]: r for r in self.rows}
        self.assertEqual(
            by_id["PMN-no_contact_ignored-context_target"]["candidate_action"],
            "BLOCK",
        )
        self.assertEqual(
            by_id["PMN-no_contact_respected-context_target"]["candidate_action"],
            "ALLOW",
        )
        self.assertEqual(
            by_id["PMN-single_no_contact_reply-context_target"]["candidate_action"],
            "REVIEW",
        )

    def test_regenerates_immutable_fixture(self) -> None:
        canonical = "".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
            for r in self.rows
        )
        self.assertEqual(OUT.read_bytes(), canonical.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
