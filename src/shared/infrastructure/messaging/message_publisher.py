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

    @property
    def available(self) -> bool:
        """Whether the publisher connection is usable"""
        return self.broker.channel is not None and self.broker.connection is not None \
            and not self.broker.connection.is_closed

    def publish_event(self, routing_key: str, event: DomainEvent) -> bool:
        """Publish domain event to message broker"""
        try:
            message = event.to_dict()
            self.broker.publish(routing_key, message)
            logger.info(f"Event published: {event.event_type} to {routing_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event to {routing_key}: {e}")
            return False

    def publish_player_joined(self, event_data: Dict[str, Any]) -> bool:
        """Publish player joined event"""
        from src.shared.constants import ROUTING_KEY_PLAYER_JOINED
        from src.shared.domain.events import PlayerJoinedEvent

        return self.publish_event(
            ROUTING_KEY_PLAYER_JOINED, PlayerJoinedEvent(payload=event_data)
        )

    def publish_player_guess(self, event_data: Dict[str, Any]) -> bool:
        """Publish player guess event"""
        from src.shared.constants import ROUTING_KEY_PLAYER_SUBMIT
        from src.shared.domain.events import PlayerSubmitGuessEvent

        return self.publish_event(
            ROUTING_KEY_PLAYER_SUBMIT, PlayerSubmitGuessEvent(payload=event_data)
        )

    def publish_calculate_result(self, event_data: Dict[str, Any]) -> bool:
        """Publish calculate result request event"""
        from src.shared.constants import ROUTING_KEY_ROUND_CALCULATE
        from src.shared.domain.events import CalculateRoundResultEvent

        return self.publish_event(
            ROUTING_KEY_ROUND_CALCULATE, CalculateRoundResultEvent(payload=event_data)
        )

    def publish_round_result_ready(self, event_data: Dict[str, Any]) -> bool:
        """Publish round result ready event"""
        from src.shared.constants import ROUTING_KEY_ROUND_RESULT_READY
        from src.shared.domain.events import RoundResultReadyEvent

        return self.publish_event(
            ROUTING_KEY_ROUND_RESULT_READY, RoundResultReadyEvent(payload=event_data)
        )

    def publish_round_result_failed(self, event_data: Dict[str, Any]) -> bool:
        """Publish round result failure event"""
        from src.shared.constants import ROUTING_KEY_ROUND_RESULT_FAILED
        from src.shared.domain.events import RoundResultFailedEvent

        return self.publish_event(
            ROUTING_KEY_ROUND_RESULT_FAILED, RoundResultFailedEvent(payload=event_data)
        )


message_publisher = MessagePublisher()
