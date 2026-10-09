"""Frozen, developer-authored candidate-corpus checks. Not training validation."""
from __future__ import annotations

import json
import unittest
from collections import Counter, defaultdict

from tools.data_v2.private_banter_candidates import (
    DATASET,
    PHASES,
    SLUR_TOKEN,
    build_candidates,
    summarize,
)
from tools.dataset_qa.asof_input import serialize_as_of_target


class PrivateBanterCandidatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = build_candidates()
        cls.by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in cls.records:
            cls.by_family[row["family_id"]].append(row)

    def test_cardinality_and_action_diversity(self) -> None:
        self.assertEqual(len(self.records), 96)
        self.assertEqual(len(self.by_family), 20)
        self.assertEqual(
            Counter(row["candidate_action"] for row in self.records),
            {"ALLOW": 52, "BLOCK": 28, "REVIEW": 16},
        )
        self.assertEqual(summarize(self.records)["training_eligible"], False)

    def test_all_development_candidates_remain_unverified(self) -> None:
        for row in self.records:
            self.assertIs(row["training_eligible"], False)
            self.assertIs(row["semantic_label_verified"], False)
            self.assertIs(row["owner_reviewed"], False)
            self.assertEqual(row["annotation_status"], "unverified_policy_candidate")
            self.assertEqual(row["source"], "synthetic_developer_authored")
            self.assertNotIn("strike", row)
            self.assertNotIn("mute", row)

    def test_five_counterfactual_phases_per_friendship(self) -> None:
        for number in range(1, 17):
            family = self.by_family[f"PMB-F{number:02d}"]
            actual = {row["contrast_phase"]: row["candidate_action"] for row in family}
            self.assertEqual(set(actual), set(PHASES))
            self.assertEqual(
                actual,
                {
                    "mutual_joking": "ALLOW",
                    "boundary_request": "ALLOW",
                    "ignored_boundary": "REVIEW",
                    "repeated_after_boundary": "BLOCK",
                    "respectful_compliance": "ALLOW",
                },
            )

    def test_unwanted_escalation_has_a_visible_prior_stop(self) -> None:
        for number in range(1, 17):
            family = self.by_family[f"PMB-F{number:02d}"]
            phases = {row["contrast_phase"]: row for row in family}
            initial = phases["mutual_joking"]["messages"]
            request = phases["boundary_request"]["messages"]
            ignored = phases["ignored_boundary"]["messages"]
            repeated = phases["repeated_after_boundary"]["messages"]
            compliance = phases["respectful_compliance"]["messages"]
            self.assertEqual(request[:-1], initial)
            self.assertEqual(ignored[:-1], request)
            self.assertEqual(repeated[:len(ignored)], ignored)
            self.assertEqual(compliance[:-1], request)
            self.assertEqual(request[-1]["speaker"], "Friend_B")
            self.assertEqual(ignored[-1]["speaker"], "Friend_A")
            self.assertEqual(repeated[-2]["speaker"], "Friend_B")
            self.assertEqual(repeated[-1]["speaker"], "Friend_A")

    def test_placeholder_slur_always_candidate_block_even_if_friends(self) -> None:
        for number in range(17, 21):
            by_phase = {
                row["contrast_phase"]: row
                for row in self.by_family[f"PMB-F{number:02d}"]
            }
            self.assertEqual(len(by_phase), 4)
            for phase in (
                "direct_placeholder", "reported_placeholder",
                "after_stop_placeholder",
            ):
                self.assertEqual(by_phase[phase]["candidate_action"], "BLOCK")
                self.assertIn(SLUR_TOKEN, by_phase[phase]["messages"][-1]["text"])
            self.assertEqual(
                by_phase["reference_without_slur"]["candidate_action"], "ALLOW"
            )
            self.assertNotIn(
                SLUR_TOKEN, by_phase["reference_without_slur"]["messages"][-1]["text"]
            )

    def test_reporter_not_assigned_culpability(self) -> None:
        for row in self.records:
            if row["contrast_phase"] == "reported_placeholder":
                self.assertIn("reporter_not_culpable", row["candidate_reason_flags"])
                self.assertNotIn("punishment", row)

    def test_only_private_surface_and_target_visible_context(self) -> None:
        for row in self.records:
            self.assertEqual(row["channel_profile"], "minecraft_private")
            self.assertEqual(row["platform_hint"], "minecraft")
            self.assertEqual(row["target_index"], len(row["messages"]) - 1)
            self.assertLessEqual(len(row["messages"]), 8)
            projection = serialize_as_of_target(row)
            self.assertEqual(projection["messages"], row["messages"])
            self.assertNotIn("candidate_action", projection)
            self.assertNotIn("candidate_reason_flags", projection)
            self.assertNotIn("family_id", projection)

    def test_session_family_isolation_and_unique_targets(self) -> None:
        self.assertEqual(
            len({row["example_id"] for row in self.records}), len(self.records)
        )
        for number in range(1, 17):
            fam = self.by_family[f"PMB-F{number:02d}"]
            self.assertEqual(len(fam), 5)
            def target(row: dict[str, object]) -> str:
                return row["messages"][row["target_index"]]["text"]
            self.assertEqual(target(fam[0]), target(fam[2]))
            self.assertEqual(target(fam[1]), fam[1]["messages"][-1]["text"])
        self.assertEqual({str(row["family_id"])[:5] for row in self.records}, {"PMB-F"})

    def test_generated_jsonl_is_byte_identical_to_checked_in_fixture(self) -> None:
        expected = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in self.records
        )
        self.assertEqual(DATASET.read_bytes(), expected.encode("utf-8"))

    def test_build_is_deterministic(self) -> None:
        self.assertEqual(build_candidates(), self.records)


if __name__ == "__main__":
    unittest.main()
