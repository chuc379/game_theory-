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

    def find_winner(self, guesses: List[PlayerGuess], target: float) -> Optional[dict]:
        """Find player closest to target"""
        if not guesses:
            return None

        winner_guess = min(guesses, key=lambda g: abs(g.guess_number - target))
        return {
            "player_id": winner_guess.player_id,
            "player_name": winner_guess.player_name,
            "guess_number": winner_guess.guess_number,
            "difference": abs(winner_guess.guess_number - target),
        }
