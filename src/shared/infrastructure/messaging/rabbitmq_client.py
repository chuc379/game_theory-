"""
RabbitMQ client - Message broker for async operations
"""
import json
import logging
import threading
import pika
from typing import Callable, Optional
from config.settings import settings
from src.shared.constants import (
    RABBITMQ_EXCHANGE,
    RABBITMQ_EXCHANGE_TYPE,
    RABBITMQ_PREFETCH_COUNT,
)

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """RabbitMQ client wrapper.

    Publishing and consuming use separate AMQP connections on purpose: a pika
    channel blocked in ``start_consuming()`` cannot be used by another thread,
    and the gateway publishes from inside the asyncio event loop.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.connection = None
        self.channel = None
        self._consumer_connection: Optional[pika.BlockingConnection] = None
        self._consumer_channel = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._declared_queues = set()

    def _build_parameters(self) -> pika.ConnectionParameters:
        if settings.RABBITMQ_URL:
            return pika.URLParameters(settings.RABBITMQ_URL)

        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD
        )
        return pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
        )

    def _declare_exchange(self, channel) -> None:
        channel.exchange_declare(
            exchange=RABBITMQ_EXCHANGE,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
            durable=True,
        )

    def connect(self):
        """Open the publisher connection"""
        try:
            self.connection = pika.BlockingConnection(self._build_parameters())
            self.channel = self.connection.channel()
            self._declare_exchange(self.channel)
            logger.info("RabbitMQ publisher connected")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def _ensure_publisher_channel(self):
        """Reopen the publisher channel if the broker or channel dropped it"""
        if self.connection is not None and self.connection.is_open and self.channel is not None \
                and self.channel.is_open:
            return self.channel

        logger.warning("Publisher channel unavailable, reconnecting")
        self.connection = pika.BlockingConnection(self._build_parameters())
        self.channel = self.connection.channel()
        self._declare_exchange(self.channel)
        return self.channel

    def declare_queue(self, queue_name: str, routing_keys) -> None:
        """Declare a durable queue and bind it to routing keys.

        Publishers call this so events are buffered durably while a consumer
        service is down, instead of being dropped by the exchange.
        """
        channel = self._ensure_publisher_channel()
        channel.queue_declare(queue=queue_name, durable=True)
        for routing_key in routing_keys:
            channel.queue_bind(
                exchange=RABBITMQ_EXCHANGE, queue=queue_name, routing_key=routing_key
            )
        self._declared_queues.add(queue_name)
        logger.info(f"Declared queue {queue_name} for {list(routing_keys)}")

    def queue_status(self, queue_name: str) -> dict:
        """Return message and consumer counts for a queue without consuming it"""
        status = {"queue": queue_name, "messages": None, "consumers": None}
        try:
            channel = self._ensure_publisher_channel()
            info = channel.queue_declare(queue=queue_name, durable=True, passive=True)
            status["messages"] = info.method.message_count
            status["consumers"] = info.method.consumer_count
        except Exception as e:
            status["error"] = str(e)
            self.channel = None
        return status

    def disconnect(self):
        """Close all connections"""
        self.stop_consuming()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ disconnected")

    def publish(self, routing_key: str, message: dict) -> None:
        """Publish message to exchange"""
        try:
            channel = self._ensure_publisher_channel()
            channel.basic_publish(
                exchange=RABBITMQ_EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type="application/json",
                ),
            )
            logger.debug(f"Published message to {routing_key}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    def add_consumer(self, queue_name: str, routing_key: str, callback: Callable) -> None:
        """Declare a queue, bind it to the exchange and register a callback"""
        if self._consumer_channel is None:
            raise RuntimeError("Consumer connection is not established")

        channel = self._consumer_channel
        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(
            exchange=RABBITMQ_EXCHANGE, queue=queue_name, routing_key=routing_key
        )
        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        self._declared_queues.add(queue_name)
        logger.info(f"Subscribed {queue_name} -> {routing_key}")

    def connect_consumer(self) -> None:
        """Open the consumer connection used by the background consuming thread"""
        if self._consumer_connection is not None and not self._consumer_connection.is_closed:
            return

        self._consumer_connection = pika.BlockingConnection(self._build_parameters())
        self._consumer_channel = self._consumer_connection.channel()
        self._declare_exchange(self._consumer_channel)
        self._consumer_channel.basic_qos(prefetch_count=RABBITMQ_PREFETCH_COUNT)
        logger.info("RabbitMQ consumer connected")

    def start_consuming_in_background(self) -> None:
        """Run the blocking consumer loop on a daemon thread"""
        if self._consumer_thread and self._consumer_thread.is_alive():
            return

        if self._consumer_channel is None:
            raise RuntimeError("connect_consumer() must be called before consuming")

        self._consumer_thread = threading.Thread(
            target=self._consumer_channel.start_consuming,
            name="rabbitmq-consumer",
            daemon=True,
        )
        self._consumer_thread.start()

    def stop_consuming(self) -> None:
        """Stop the background consumer loop"""
        connection = self._consumer_connection
        if connection is None:
            return

        try:
            connection.add_callback_threadsafe(connection.stop_ioloop)
        except Exception as e:
            logger.warning(f"Failed to stop consumer cleanly: {e}")

    @property
    def consumer_alive(self) -> bool:
        return bool(self._consumer_thread and self._consumer_thread.is_alive())


rabbitmq_client = RabbitMQClient()
