"""
Task handlers - Handle tasks from message queue
"""
import logging
import json
from src.modules.game_round.adapter.round_cache_repository import (
    GuessCacheRepository,
    RoundResultCacheRepository,
)
from src.modules.game_round.use_cases.calculate_result import CalculateResultUseCase
from src.shared.infrastructure.messaging.rabbitmq_client import rabbitmq_client
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
            event_data: Event payload with room_id and round_id
        """
        try:
            room_id = event_data.get("room_id")
            round_id = event_data.get("round_id")

            logger.info(f"Processing calculation for room {room_id}, round {round_id}")

            # Calculate result
            result = await self.calculate_use_case.execute(room_id, round_id)

            if result["success"]:
                # Publish result ready event to notify gateway
                message_publisher.publish_event(
                    "game.round.result.ready",
                    {
                        "room_id": room_id,
                        "round_id": round_id,
                        "result": result["result"],
                    },
                )
                logger.info(f"Result published for room {room_id}, round {round_id}")
            else:
                logger.error(f"Calculation failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error handling calculate result: {e}")
            raise

    def start_consuming(self) -> None:
        """Start consuming tasks from queue"""
        from src.shared.constants import QUEUE_CALCULATE_RESULTS, ROUTING_KEY_CALCULATE_RESULT

        def callback(ch, method, properties, message):
            try:
                logger.info(f"Received message: {message}")
                # Run async handler
                import asyncio

                asyncio.run(self.handle_calculate_result(message.get("payload", {})))
            except Exception as e:
                logger.error(f"Error in callback: {e}")

        try:
            rabbitmq_client.consume(
                QUEUE_CALCULATE_RESULTS, ROUTING_KEY_CALCULATE_RESULT, callback
            )
        except Exception as e:
            logger.error(f"Error starting consumer: {e}")
            raise
