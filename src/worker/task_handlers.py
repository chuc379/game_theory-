"""
Task handlers - Handle tasks from message queue
"""
import logging
from src.modules.game_round.adapter.round_cache_repository import (
    GuessCacheRepository,
    RoundResultCacheRepository,
)
from src.modules.game_round.use_cases.calculate_result import CalculateResultUseCase
from src.shared.infrastructure.messaging.message_publisher import message_publisher

logger = logging.getLogger(__name__)


class TaskHandler:
    """Handle tasks from RabbitMQ"""

    def __init__(self):
        self.guess_repo = GuessCacheRepository()
        self.result_repo = RoundResultCacheRepository()
        self.calculate_use_case = CalculateResultUseCase(self.guess_repo, self.result_repo)

    async def handle_calculate_result(self, event_data: dict) -> None:
        """
        Handle calculate result task

        Args:
            event_data: Event payload with room_id, round_id and force_calculate
        """
        room_id = event_data.get("room_id")
        round_id = event_data.get("round_id")
        force_calculate = bool(event_data.get("force_calculate", False))

        if not room_id or round_id is None:
            logger.error(f"Malformed calculate result event: {event_data}")
            return

        logger.info(
            f"Processing calculation for room {room_id}, round {round_id} "
            f"(force={force_calculate})"
        )

        result = await self.calculate_use_case.execute(
            room_id, int(round_id), force_calculate=force_calculate
        )

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            logger.error(f"Calculation failed for room {room_id}: {error}")
            message_publisher.publish_round_result_failed(
                {"room_id": room_id, "round_id": int(round_id), "error": error}
            )
            return

        published = message_publisher.publish_round_result_ready(
            {
                "room_id": room_id,
                "round_id": int(round_id),
                "result": result.get("result"),
            }
        )

        if not published:
            logger.error(
                f"Result for room {room_id} round {round_id} could not be returned to gateway"
            )
            return

        logger.info(f"Result published for room {room_id}, round {round_id}")
