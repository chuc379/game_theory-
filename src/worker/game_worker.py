"""
Game worker - Main entry point for async worker
"""
import logging
import asyncio
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.infrastructure.messaging.rabbitmq_client import rabbitmq_client
from src.worker.task_handlers import TaskHandler

logger = logging.getLogger(__name__)


class GameWorker:
    """Game worker for async task processing"""

    def __init__(self):
        self.task_handler = TaskHandler()

    async def start(self) -> None:
        """Start worker"""
        try:
            # Connect to Redis
            await redis_client.connect()
            logger.info("Worker connected to Redis")

            # Connect to RabbitMQ
            rabbitmq_client.connect()
            logger.info("Worker connected to RabbitMQ")

            # Start consuming tasks
            self.task_handler.start_consuming()

        except Exception as e:
            logger.error(f"Failed to start worker: {e}")
            raise

    async def stop(self) -> None:
        """Stop worker"""
        try:
            await redis_client.disconnect()
            rabbitmq_client.disconnect()
            logger.info("Worker stopped")
        except Exception as e:
            logger.error(f"Error stopping worker: {e}")


async def run_worker():
    """Run worker in asyncio loop"""
    worker = GameWorker()
    await worker.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
