import unittest

from src.shared.constants import STARTING_LIVES
from src.shared.domain.scoring import PlayerScore, apply_survival_round


class SurvivalScoringTests(unittest.TestCase):
    def test_players_start_with_ten_lives_and_non_winners_lose_one(self):
        winner = PlayerScore(player_id="winner", player_name="Winner")
        missed = PlayerScore(player_id="missed", player_name="Missed")

        result = apply_survival_round(
            scores=[winner, missed],
            guesses_by_player={"winner": 25},
            winner_guess=25,
            convergence=False,
        )

        self.assertEqual(STARTING_LIVES, 10)
        self.assertEqual(winner.total_points, 10)
        self.assertEqual(missed.total_points, 9)
        self.assertEqual(missed.last_delta, -1)
        self.assertEqual(missed.rounds_played, 1)
        self.assertIn("missed", result["loser_ids"])

    def test_player_is_eliminated_when_the_tenth_life_is_lost(self):
        player = PlayerScore(
            player_id="player",
            player_name="Player",
            total_points=1,
        )
        winner = PlayerScore(
            player_id="winner",
            player_name="Winner",
            total_points=STARTING_LIVES,
        )

        result = apply_survival_round(
            scores=[player, winner],
            guesses_by_player={"player": 0, "winner": 1},
            winner_guess=1,
            convergence=False,
        )

        self.assertEqual(player.total_points, 0)
        self.assertTrue(player.eliminated)
        self.assertEqual([player.to_dict()], result["eliminated"])


if __name__ == "__main__":
    unittest.main()
