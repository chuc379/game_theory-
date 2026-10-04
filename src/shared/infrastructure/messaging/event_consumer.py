"""
Event consumer - Bridges RabbitMQ deliveries into the local asyncio event loop
"""
import asyncio
import json
import logging
from typing import Awaitable, Callable, List, Optional, Tuple
from src.shared.infrastructure.messaging.rabbitmq_client import rabbitmq_client

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], Awaitable[None]]
HANDLER_TIMEOUT_SECONDS = 30.0


class EventConsumer:
    """Consumes domain events from the broker and dispatches them to async handlers.

    pika delivers messages on its own thread. Handlers here are coroutines bound
    to the application's event loop, so every delivery is scheduled back onto
    that loop with ``run_coroutine_threadsafe``.
    """

    def __init__(self, broker_client=rabbitmq_client):
        self.broker = broker_client
        self._subscriptions: List[Tuple[str, str, EventHandler]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def subscribe(self, queue_name: str, routing_key: str, handler: EventHandler) -> None:
        """Register an async handler for a routing key on a queue"""
        self._subscriptions.append((queue_name, routing_key, handler))

    def _build_callback(self, routing_key: str, handler: EventHandler) -> Callable:
        def callback(ch, method, properties, body):
            try:
                event = json.loads(body) if body else {}
            except json.JSONDecodeError:
                logger.error(f"Malformed event on {routing_key}, dropping")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            payload = event.get("payload", event)
            try:
                future = asyncio.run_coroutine_threadsafe(
                    handler(payload), self._loop
                )
                future.result(timeout=HANDLER_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                logger.error(f"Handler timed out for {routing_key}")
            except Exception:
                logger.exception(f"Handler failed for {routing_key}")
            finally:
                ch.basic_ack(delivery_tag=method.delivery_tag)

        return callback

    async def start(self) -> None:
        """Declare queues/bindings and run the consumer loop on a background thread"""
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.broker.connect_consumer)

        for queue_name, routing_key, handler in self._subscriptions:
            self.broker.add_consumer(
                queue_name, routing_key, self._build_callback(routing_key, handler)
            )

        self.broker.start_consuming_in_background()
        logger.info(
            f"Event consumer started with {len(self._subscriptions)} subscription(s)"
        )

    def stop(self) -> None:
        """Stop the background consumer loop"""
        self.broker.stop_consuming()
        self._loop = None
