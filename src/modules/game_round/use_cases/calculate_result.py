"""
Calculate result use case - Business logic for calculating round result
"""
import logging
from typing import Any, Dict, List, Optional

from src.modules.game_round.domain.round_entity import RoundEntity
from src.modules.game_round.domain.round_repository import (
    IGuessRepository,
    IRoundResultRepository,
)
from src.shared.constants import CONVERGENCE_TARGET_THRESHOLD, STARTING_LIVES
from src.shared.domain.entities import PlayerGuess, RoundResult, Winner
from src.shared.domain.scoring import PlayerScore, apply_survival_round

logger = logging.getLogger(__name__)


class CalculateResultUseCase:
    """Use case for calculating round result and survival penalties"""

    def __init__(
        self,
        guess_repository: IGuessRepository,
        result_repository: IRoundResultRepository,
        score_repository=None,
        player_repository=None,
    ):
        self.guess_repo = guess_repository
        self.result_repo = result_repository
        self.score_repo = score_repository
        self.player_repo = player_repository

    async def execute(
        self, room_id: str, round_id: int, force_calculate: bool = False
    ) -> dict:
        """
        Execute calculate result logic

        Args:
            room_id: Room identifier
            round_id: Round number
            force_calculate: True if Skip button (partial data), False if all submitted

        Returns:
            dict with calculation result, survival scoreboard and eliminations
        """
        try:
            round_entity = RoundEntity(round_id=round_id, status="LOCKED", result=None)

            guesses = await self.guess_repo.find_all(room_id, round_id)

            if guesses:
                average = round_entity.calculate_average(guesses)
                target = round_entity.calculate_target(average)
                winner_data = round_entity.find_winner(guesses, target)
            else:
                # A survival round must still resolve (everyone alive loses a
                # life) instead of getting stuck because nobody submitted.
                average = 0.0
                target = 0.0
                winner_data = None

            winner = Winner(**winner_data) if winner_data else None
            convergence = bool(guesses) and target <= CONVERGENCE_TARGET_THRESHOLD

            # A converged round has no winner: picking 0 is a losing move.
            if convergence:
                winner = None

            result = RoundResult(
                total_players=len(guesses),
                average=round(average, 2),
                target=round(target, 2),
                winner=winner,
                force_calculate=force_calculate,
            )

            scoring = await self._apply_survival_scoring(
                room_id=room_id,
                guesses=guesses,
                winner=winner,
                convergence=convergence,
            )

            await self.result_repo.save(room_id, round_id, result)

            result_dict = result.to_dict()
            result_dict.update(
                {
                    "guesses": [guess.to_dict() for guess in guesses],
                    "rule": "survival",
                    "convergence": convergence,
                    "losers": scoring.get("loser_ids", []),
                    "correct": scoring.get("correct_ids", []),
                    "eliminated": scoring.get("eliminated", []),
                    "game_over": scoring.get("game_over", False),
                    "survivor": scoring.get("survivor"),
                    "scoreboard": scoring.get("scoreboard", []),
                }
            )

            logger.info(
                f"Round {round_id} result calculated (force={force_calculate}, "
                f"convergence={convergence}): {result_dict}"
            )

            return {
                "success": True,
                "result": result_dict,
                "message": f"Round {round_id} completed",
                "calculation_type": "skipped" if force_calculate else "normal",
            }

        except Exception as e:
            logger.error(f"Calculate result failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _apply_survival_scoring(
        self,
        room_id: str,
        guesses: List[PlayerGuess],
        winner: Optional[Winner],
        convergence: bool,
    ) -> Dict[str, Any]:
        """Load the scoreboard, apply penalties and persist the new lives"""
        if self.score_repo is None:
            return {}

        players = []
        if self.player_repo is not None:
            try:
                players = await self.player_repo.find_all_by_room(room_id)
            except Exception as e:
                logger.warning(f"Could not load players for room {room_id}: {e}")

        scores: List[PlayerScore] = await self.score_repo.ensure_players(room_id, players)

        # Safety net for data created before scores existed (or when the player
        # repository is unavailable): make sure every submitter has a score.
        known_ids = {score.player_id for score in scores}
        for guess in guesses:
            if guess.player_id not in known_ids:
                scores.append(
                    PlayerScore(
                        player_id=guess.player_id,
                        player_name=guess.player_name,
                        total_points=STARTING_LIVES,
                    )
                )
                known_ids.add(guess.player_id)

        guesses_by_player = {guess.player_id: guess.guess_number for guess in guesses}
        summary = apply_survival_round(
            scores=scores,
            guesses_by_player=guesses_by_player,
            winner_guess=winner.guess_number if winner else None,
            convergence=convergence,
        )

        await self.score_repo.save_many(room_id, scores)
        return summary
