import unittest

from src.modules.room.session_policy import (
    DEFAULT_ROOM_CONFIG,
    SESSION_MODE_MULTI_LINK,
    SESSION_MODE_SINGLE_LINK,
    SessionContext,
    SessionPolicyFactory,
    normalize_room_config,
)


class SessionPolicyTests(unittest.TestCase):
    def test_default_config_is_multi_link(self):
        config = normalize_room_config(None)
        self.assertEqual(config["session_mode"], SESSION_MODE_MULTI_LINK)
        self.assertEqual(
            config["max_player_links"], DEFAULT_ROOM_CONFIG["max_player_links"]
        )
        self.assertTrue(config["lock_on_round_start"])

    def test_legacy_allow_multi_link_flag_is_migrated(self):
        self.assertEqual(
            normalize_room_config({"allow_multi_link": False})["session_mode"],
            SESSION_MODE_SINGLE_LINK,
        )
        self.assertEqual(
            normalize_room_config({"allow_multi_link": True})["session_mode"],
            SESSION_MODE_MULTI_LINK,
        )

    def test_max_player_links_is_clamped(self):
        self.assertEqual(
            normalize_room_config({"max_player_links": 0})["max_player_links"], 1
        )
        self.assertEqual(
            normalize_room_config({"max_player_links": 999})["max_player_links"], 20
        )
        self.assertEqual(
            normalize_room_config({"max_player_links": "not-a-number"})[
                "max_player_links"
            ],
            6,
        )

    def test_multi_link_allows_links_until_limit(self):
        policy = SessionPolicyFactory.create(
            {"session_mode": SESSION_MODE_MULTI_LINK, "max_player_links": 2}
        )

        self.assertTrue(
            policy.decide(
                SessionContext(device_id="dev", existing_sids=["a"], round_active=False)
            ).allowed
        )
        rejected = policy.decide(
            SessionContext(
                device_id="dev",
                existing_sids=["a", "b"],
                round_active=False,
            )
        )
        self.assertFalse(rejected.allowed)
        self.assertEqual(rejected.code, "device_link_limit")

    def test_multi_link_locks_to_one_when_round_is_active(self):
        policy = SessionPolicyFactory.create(
            {
                "session_mode": SESSION_MODE_MULTI_LINK,
                "max_player_links": 6,
                "lock_on_round_start": True,
            }
        )
        rejected = policy.decide(
            SessionContext(device_id="dev", existing_sids=["a"], round_active=True)
        )
        self.assertFalse(rejected.allowed)
        self.assertEqual(rejected.code, "device_link_limit_round")

    def test_single_link_rejects_second_link_even_before_the_round(self):
        policy = SessionPolicyFactory.create(
            {"session_mode": SESSION_MODE_SINGLE_LINK}
        )
        self.assertTrue(
            policy.decide(SessionContext(device_id="dev", existing_sids=[])).allowed
        )
        rejected = policy.decide(
            SessionContext(device_id="dev", existing_sids=["a"])
        )
        self.assertFalse(rejected.allowed)
        self.assertEqual(rejected.code, "device_link_limit")

    def test_mc_is_exempt_from_the_player_link_policy(self):
        policy = SessionPolicyFactory.create(
            {"session_mode": SESSION_MODE_SINGLE_LINK}
        )
        self.assertTrue(
            policy.decide(
                SessionContext(
                    role="mc", device_id="dev", existing_sids=["player-tab"]
                )
            ).allowed
        )


if __name__ == "__main__":
    unittest.main()
