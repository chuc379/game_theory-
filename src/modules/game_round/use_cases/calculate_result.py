"""
Calculate result use case - Business logic for calculating round result
"""
import logging
from src.modules.game_round.domain.round_entity import RoundEntity
from src.modules.game_round.domain.round_repository import (
    IGuessRepository,
    IRoundResultRepository,
)
from src.shared.domain.entities import RoundResult, Winner

logger = logging.getLogger(__name__)


class CalculateResultUseCase:
    """Use case for calculating round result"""

    def __init__(
        self,
        guess_repository: IGuessRepository,
        result_repository: IRoundResultRepository,
    ):
        self.guess_repo = guess_repository
        self.result_repo = result_repository

    async def execute(self, room_id: str, round_id: int, force_calculate: bool = False) -> dict:
        """
        Execute calculate result logic
        
        Args:
            room_id: Room identifier
            round_id: Round number
            force_calculate: True if Skip button (partial data), False if all submitted
            
        Returns:
            dict with calculation result
        """
        try:
            # Create round entity
            round_entity = RoundEntity(round_id=round_id, status="LOCKED", result=None)

            # Get all guesses
            guesses = await self.guess_repo.find_all(room_id, round_id)

            if not guesses:
                return {
                    "success": False,
                    "error": "No submissions for this round",
                }

            # Calculate average
            average = round_entity.calculate_average(guesses)

            # Calculate target (2/3 of average)
            target = round_entity.calculate_target(average)

            # Find winner
            winner_data = round_entity.find_winner(guesses, target)

            if not winner_data:
                return {"success": False, "error": "Could not determine winner"}

            # Create result entity
            winner = Winner(**winner_data)
            result = RoundResult(
                total_players=len(guesses),
                average=round(average, 2),
                target=round(target, 2),
                winner=winner,
                force_calculate=force_calculate,  # Track how result was calculated
            )

            # Save result
            await self.result_repo.save(room_id, round_id, result)

            logger.info(f"Round {round_id} result calculated (force={force_calculate}): {result.to_dict()}")

            return {
                "success": True,
                "result": result.to_dict(),
                "message": f"Round {round_id} completed",
                "calculation_type": "skipped" if force_calculate else "normal",
            }

        except Exception as e:
            logger.error(f"Calculate result failed: {e}")
            return {"success": False, "error": str(e)}
