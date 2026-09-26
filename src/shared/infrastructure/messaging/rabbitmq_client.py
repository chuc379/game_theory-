"""
RabbitMQ client - Message broker for async operations
"""
import json
import logging
import pika
from typing import Callable
from config.settings import settings
from src.shared.constants import RABBITMQ_EXCHANGE, RABBITMQ_EXCHANGE_TYPE

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """RabbitMQ async client wrapper"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.connection = None
        self.channel = None

    def connect(self):
        """Initialize RabbitMQ connection"""
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD
        )
        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        # Declare exchange
        self.channel.exchange_declare(
            exchange=RABBITMQ_EXCHANGE,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
            durable=True,
        )
        logger.info("RabbitMQ connected")

    def disconnect(self):
        """Close RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ disconnected")

    def publish(self, routing_key: str, message: dict) -> None:
        """Publish message to exchange"""
        try:
            self.channel.basic_publish(
                exchange=RABBITMQ_EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),  # Persistent
            )
            logger.debug(f"Published message to {routing_key}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    def consume(
        self,
        queue_name: str,
        routing_key: str,
        callback: Callable,
    ) -> None:
        """Consume messages from queue"""
        try:
            # Declare queue
            self.channel.queue_declare(queue=queue_name, durable=True)

            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=RABBITMQ_EXCHANGE, queue=queue_name, routing_key=routing_key
            )

            # Set prefetch count for fairness
            self.channel.basic_qos(prefetch_count=1)

            # Wrap callback to handle JSON parsing
            def wrapped_callback(ch, method, properties, body):
                try:
                    message = json.loads(body)
                    callback(ch, method, properties, message)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            self.channel.basic_consume(queue=queue_name, on_message_callback=wrapped_callback)

            logger.info(f"Listening on queue: {queue_name}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
            raise


rabbitmq_client = RabbitMQClient()
