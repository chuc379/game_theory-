import unittest

from src.modules.game_round.domain.round_entity import RoundEntity
from src.shared.domain.entities import PlayerGuess


class RoundWinnerTests(unittest.TestCase):
    def test_two_players_with_the_same_winning_guess_are_both_winners(self):
        round_entity = RoundEntity(round_id=1, status="LOCKED")
        guesses = [
            PlayerGuess(player_id="a", player_name="Alice", guess_number=10),
            PlayerGuess(player_id="b", player_name="Bob", guess_number=10),
            PlayerGuess(player_id="c", player_name="Carol", guess_number=50),
        ]

        winners = round_entity.find_winners(guesses, target=10)

        self.assertEqual([winner["player_id"] for winner in winners], ["a", "b"])
        self.assertTrue(all(winner["difference"] == 0 for winner in winners))

    def test_only_the_closest_players_are_winners(self):
        round_entity = RoundEntity(round_id=1, status="LOCKED")
        guesses = [
            PlayerGuess(player_id="a", player_name="Alice", guess_number=9),
            PlayerGuess(player_id="b", player_name="Bob", guess_number=11),
            PlayerGuess(player_id="c", player_name="Carol", guess_number=50),
        ]

        winners = round_entity.find_winners(guesses, target=10)

        self.assertEqual(
            sorted(winner["player_id"] for winner in winners), ["a", "b"]
        )

    def test_no_guesses_means_no_winners(self):
        round_entity = RoundEntity(round_id=1, status="LOCKED")
        self.assertEqual(round_entity.find_winners([], target=0), [])


if __name__ == "__main__":
    unittest.main()
