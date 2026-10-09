"""Offline visibility proposal must never authorize punishments."""
import unittest

from tools.data_v2.owner_visibility_probe import propose_visibility


class OwnerVisibilityTests(unittest.TestCase):
    def test_reported_token_blocks_message_only(self) -> None:
        result = propose_visibility(
            "discord_general", "I reported the message saying 'badword'",
            "ALLOW", "badword",
        )
        self.assertEqual(result.proposed_action, "BLOCK")
        self.assertTrue(result.visibility_override)
        self.assertFalse(result.punitive_action_authorized)
        self.assertFalse(result.live_enforcement_authorized)

    def test_other_reports_remain_allowed(self) -> None:
        result = propose_visibility(
            "minecraft_private", "I reported someone's threat.", "ALLOW", "badword"
        )
        self.assertEqual(result.proposed_action, "ALLOW")

    def test_similar_words_not_substring_matched(self) -> None:
        for sentence in ("notbadword", "badwording", "badword42"):
            with self.subTest(sentence=sentence):
                result = propose_visibility(
                    "minecraft_public", sentence, "ALLOW", "badword"
                )
                self.assertEqual(result.proposed_action, "ALLOW")

    def test_exempt_profiles_remain_untouched(self) -> None:
        for scope in ("discord_ticket_exempt", "discord_staff_exempt", "unknown"):
            with self.subTest(scope=scope):
                result = propose_visibility(scope, "badword", "ALLOW", "badword")
                self.assertEqual(result.proposed_action, "ALLOW")
                self.assertFalse(result.visibility_override)

    def test_no_new_punishment_for_preexisting_block(self) -> None:
        result = propose_visibility(
            "discord_gaming", "badword", "BLOCK", "badword"
        )
        self.assertEqual(result.proposed_action, "BLOCK")
        self.assertFalse(result.visibility_override)
        self.assertFalse(result.punitive_action_authorized)

    def test_invalid_inputs_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "policy token"):
            propose_visibility("minecraft_public", "hello", "ALLOW", "*")
        with self.assertRaisesRegex(ValueError, "offline action"):
            propose_visibility("minecraft_public", "hello", "BAN", "badword")


if __name__ == "__main__":
    unittest.main()
