"""
Submit guess use case - Business logic for player submitting guess
"""
import logging
from src.modules.game_round.domain.round_repository import IGuessRepository
from src.shared.domain.entities import PlayerGuess

logger = logging.getLogger(__name__)


class SubmitGuessUseCase:
    """Use case for player submitting guess"""

    def __init__(self, guess_repository: IGuessRepository):
        self.guess_repo = guess_repository

    async def execute(
        self, room_id: str, round_id: int, player_id: str, player_name: str, guess_number: float
    ) -> dict:
        """
        Execute submit guess logic
        
        Args:
            room_id: Room identifier
            round_id: Round number
            player_id: Player ID
            player_name: Player name
            guess_number: Guessed number
            
        Returns:
            dict with status and message
        """
        try:
            # Validate guess range
            if not (0 <= guess_number <= 100):
                return {"success": False, "error": "Guess must be between 0-100"}

            # Create and save guess
            guess = PlayerGuess(
                player_id=player_id,
                player_name=player_name,
                guess_number=guess_number,
            )

            await self.guess_repo.save(room_id, round_id, guess)

            logger.info(f"Player {player_id} submitted guess {guess_number} in round {round_id}")

            return {
                "success": True,
                "message": "Guess submitted successfully",
                "guess": guess.to_dict(),
            }
        except Exception as e:
            logger.error(f"Submit guess failed: {e}")
            return {"success": False, "error": str(e)}
