"""Synthetic policy-contract probes; not real classifier accuracy."""
import unittest

from tools.data_v2.target_message_lexical_probe import propose_target_visibility


class TargetLexicalProbeTests(unittest.TestCase):
    def test_direct_target_occurrence_proposes_block_without_punishment(self) -> None:
        result = propose_target_visibility(
            "minecraft_private", "wow, you b4dword", ["b4dword"]
        )
        self.assertEqual(result.outcome, "BLOCK")
        self.assertTrue(result.target_matched)
        self.assertFalse(result.reporter_culpability_inferred)
        self.assertFalse(result.strike_authorized)
        self.assertFalse(result.mute_authorized)
        self.assertFalse(result.staff_alert_authorized)
        self.assertFalse(result.runtime_enabled)
        self.assertFalse(result.training_eligible)

    def test_quote_also_proposes_only_message_visibility(self) -> None:
        result = propose_target_visibility(
            "discord_general", "reporting this: 'b4dword'", ["b4dword"]
        )
        self.assertEqual(result.outcome, "BLOCK")
        self.assertFalse(result.reporter_culpability_inferred)

    def test_context_cannot_leak_into_current_message(self) -> None:
        history = "someone wrote b4dword"
        target = "I reported it to the moderators"
        self.assertIn("b4dword", history)
        result = propose_target_visibility("minecraft_public", target, ["b4dword"])
        self.assertEqual(result.outcome, "ABSTAIN")
        self.assertFalse(result.target_matched)

    def test_non_matching_target_is_abstain_not_allow(self) -> None:
        result = propose_target_visibility(
            "minecraft_private", "send your real address right now", ["b4dword"]
        )
        self.assertEqual(result.outcome, "ABSTAIN")

    def test_obfuscation_requires_a_separately_reviewed_literal(self) -> None:
        ordinary = propose_target_visibility(
            "minecraft_private", "b4dword", ["badword"]
        )
        explicit = propose_target_visibility(
            "minecraft_private", "b4dword", ["badword", "b4dword"]
        )
        self.assertEqual(ordinary.outcome, "ABSTAIN")
        self.assertEqual(explicit.outcome, "BLOCK")

    def test_substrings_and_regex_metacharacters_not_interpreted(self) -> None:
        for message in ("preb4dword", "b4dword123", "xb4dwordy"):
            with self.subTest(message=message):
                result = propose_target_visibility(
                    "minecraft_public", message, ["b4dword"]
                )
                self.assertEqual(result.outcome, "ABSTAIN")
        self.assertEqual(
            propose_target_visibility(
                "minecraft_public", "a+b", ["a+b"]
            ).outcome,
            "BLOCK",
        )
        self.assertEqual(
            propose_target_visibility(
                "minecraft_public", "ab", ["a+b"]
            ).outcome,
            "ABSTAIN",
        )

    def test_unicode_normalization_and_case(self) -> None:
        result = propose_target_visibility(
            "discord_gaming", "B4DWORD", ["b4dword"]
        )
        self.assertEqual(result.outcome, "BLOCK")

    def test_all_exempt_and_unknown_profiles_abstain(self) -> None:
        for channel in (
            "discord_ticket_exempt",
            "discord_staff_exempt",
            "discord_configured_exempt",
            "discord_bot_dm",
            "unknown",
        ):
            with self.subTest(channel=channel):
                result = propose_target_visibility(channel, "b4dword", ["b4dword"])
                self.assertEqual(result.outcome, "ABSTAIN")

    def test_invalid_configuration_rejected(self) -> None:
        invalid = ([], ["word", "word"], [" "], ["x"], ["word "])
        for words in invalid:
            with self.subTest(words=words), self.assertRaises(ValueError):
                propose_target_visibility("minecraft_public", "word", words)
        with self.assertRaises(ValueError):
            propose_target_visibility("minecraft_public", "word", "word")
        with self.assertRaises(ValueError):
            propose_target_visibility("minecraft_public", "x" * 9000, ["word"])


if __name__ == "__main__":
    unittest.main()
