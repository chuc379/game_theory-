"""
Message publisher - Wrapper for publishing domain events
"""
import logging
from typing import Dict, Any
from src.shared.infrastructure.messaging.rabbitmq_client import rabbitmq_client
from src.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class MessagePublisher:
    """Publisher for domain events to message broker"""

    def __init__(self, broker_client=rabbitmq_client):
        self.broker = broker_client

    def publish_event(self, routing_key: str, event: DomainEvent) -> None:
        """Publish domain event to message broker"""
        try:
            message = event.to_dict()
            self.broker.publish(routing_key, message)
            logger.info(f"Event published: {event.event_type} to {routing_key}")
        except Exception as e:
            logger.warning(f"RabbitMQ publish skipped because broker is unavailable: {e}")
            return

    def publish_player_guess(self, event_data: Dict[str, Any]) -> None:
        """Publish player guess event"""
        from src.shared.constants import ROUTING_KEY_PLAYER_SUBMIT
        from src.shared.domain.events import PlayerSubmitGuessEvent

        event = PlayerSubmitGuessEvent(payload=event_data)
        self.publish_event(ROUTING_KEY_PLAYER_SUBMIT, event)

    def publish_calculate_result(self, event_data: Dict[str, Any]) -> None:
        """Publish calculate result event"""
        from src.shared.constants import ROUTING_KEY_CALCULATE_RESULT
        from src.shared.domain.events import CalculateRoundResultEvent

        event = CalculateRoundResultEvent(payload=event_data)
        self.publish_event(ROUTING_KEY_CALCULATE_RESULT, event)


message_publisher = MessagePublisher()
