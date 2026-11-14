"""
Game round domain entity
"""
from typing import Optional, List
from src.shared.domain.entities import GameRound, PlayerGuess, RoundResult
from src.shared.constants import RoundStatus


class RoundEntity(GameRound):
    """Extended round entity with domain logic"""

    def can_accept_guesses(self) -> bool:
        """Check if round accepts guesses"""
        return self.status == RoundStatus.WAITING

    def lock(self) -> None:
        """Lock round - stop accepting guesses"""
        self.status = RoundStatus.LOCKED

    def end(self, result: RoundResult) -> None:
        """End round with result"""
        self.status = RoundStatus.ENDED
        self.result = result

    def calculate_average(self, guesses: List[PlayerGuess]) -> float:
        """Calculate average of guesses"""
        if not guesses:
            return 0.0
        total = sum(g.guess_number for g in guesses)
        return total / len(guesses)

    def calculate_target(self, average: float) -> float:
        """Calculate 2/3 of average"""
        return average * (2 / 3)

    def find_winners(self, guesses: List[PlayerGuess], target: float) -> List[dict]:
        """Find every player tied for the closest guess.

        Two players that pick the same winning number are both winners: the
        round is decided by the *number*, not by which player submitted first.
        """
        if not guesses:
            return []

        best_difference = min(
            abs(g.guess_number - target) for g in guesses
        )
        return [
            {
                "player_id": guess.player_id,
                "player_name": guess.player_name,
                "guess_number": guess.guess_number,
                "difference": abs(guess.guess_number - target),
            }
            for guess in guesses
            if abs(abs(guess.guess_number - target) - best_difference) < 1e-9
        ]

    def find_winner(self, guesses: List[PlayerGuess], target: float) -> Optional[dict]:
        """Find the first player closest to target (kept for compatibility)"""
        winners = self.find_winners(guesses, target)
        return winners[0] if winners else None
