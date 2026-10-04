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
        from src.shared.constants import ROUTING_KEY_PLAYER_JOINED, QUEUE_GATEWAY_PLAYER_EVENTS
        from src.shared.domain.events import PlayerJoinedEvent

        self.ensure_queue(QUEUE_GATEWAY_PLAYER_EVENTS, [ROUTING_KEY_PLAYER_JOINED])

        return self.publish_event(
            ROUTING_KEY_PLAYER_JOINED, PlayerJoinedEvent(payload=event_data)
        )

    def publish_player_guess(self, event_data: Dict[str, Any]) -> bool:
        """Publish player guess event"""
        from src.shared.constants import ROUTING_KEY_PLAYER_SUBMIT, QUEUE_GATEWAY_PLAYER_EVENTS
        from src.shared.domain.events import PlayerSubmitGuessEvent

        self.ensure_queue(QUEUE_GATEWAY_PLAYER_EVENTS, [ROUTING_KEY_PLAYER_SUBMIT])

        return self.publish_event(
            ROUTING_KEY_PLAYER_SUBMIT, PlayerSubmitGuessEvent(payload=event_data)
        )

    def ensure_queue(self, queue_name: str, routing_keys) -> None:
        """Make sure a queue exists and is bound before publishing to it.

        Without this, publishing to a routing key that has no bound queue is
        silently discarded by the broker and the request appears to hang.
        """
        try:
            if queue_name not in self.broker._declared_queues:
                self.broker.declare_queue(queue_name, routing_keys)
        except Exception as e:
            logger.error(f"Failed to declare queue {queue_name}: {e}")

    def publish_calculate_result(self, event_data: Dict[str, Any]) -> bool:
        """Publish calculate result request event"""
        from src.shared.constants import (
            ROUTING_KEY_ROUND_CALCULATE,
            QUEUE_WORKER_CALCULATE_RESULTS,
        )
        from src.shared.domain.events import CalculateRoundResultEvent

        self.ensure_queue(QUEUE_WORKER_CALCULATE_RESULTS, [ROUTING_KEY_ROUND_CALCULATE])

        return self.publish_event(
            ROUTING_KEY_ROUND_CALCULATE, CalculateRoundResultEvent(payload=event_data)
        )

    def publish_round_result_ready(self, event_data: Dict[str, Any]) -> bool:
        """Publish round result ready event"""
        from src.shared.constants import (
            ROUTING_KEY_ROUND_RESULT_READY,
            QUEUE_GATEWAY_ROUND_RESULTS,
        )
        from src.shared.domain.events import RoundResultReadyEvent

        self.ensure_queue(QUEUE_GATEWAY_ROUND_RESULTS, [ROUTING_KEY_ROUND_RESULT_READY])

        return self.publish_event(
            ROUTING_KEY_ROUND_RESULT_READY, RoundResultReadyEvent(payload=event_data)
        )

    def publish_round_result_failed(self, event_data: Dict[str, Any]) -> bool:
        """Publish round result failure event"""
        from src.shared.constants import (
            ROUTING_KEY_ROUND_RESULT_FAILED,
            QUEUE_GATEWAY_ROUND_RESULTS,
        )
        from src.shared.domain.events import RoundResultFailedEvent

        self.ensure_queue(
            QUEUE_GATEWAY_ROUND_RESULTS,
            [ROUTING_KEY_ROUND_RESULT_READY, ROUTING_KEY_ROUND_RESULT_FAILED],
        )

        return self.publish_event(
            ROUTING_KEY_ROUND_RESULT_FAILED, RoundResultFailedEvent(payload=event_data)
        )


message_publisher = MessagePublisher()
