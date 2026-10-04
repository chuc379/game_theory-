"""
Game worker - Main entry point for async worker
"""
import asyncio
import logging
import signal
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.infrastructure.messaging.rabbitmq_client import rabbitmq_client
from src.shared.infrastructure.messaging.event_consumer import EventConsumer
from src.shared.constants import QUEUE_WORKER_CALCULATE_RESULTS, ROUTING_KEY_ROUND_CALCULATE
from src.worker.task_handlers import TaskHandler

logger = logging.getLogger(__name__)


class GameWorker:
    """Game worker for async task processing"""

    def __init__(self):
        self.task_handler = TaskHandler()
        self.event_consumer = EventConsumer()
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        """Start worker"""
        # Connect to Redis
        await redis_client.connect()
        logger.info("Worker connected to Redis")

        # Connect to RabbitMQ
        rabbitmq_client.connect()
        logger.info("Worker connected to RabbitMQ")

        # Start consuming tasks
        self.event_consumer.subscribe(
            QUEUE_WORKER_CALCULATE_RESULTS,
            ROUTING_KEY_ROUND_CALCULATE,
            self.task_handler.handle_calculate_result,
        )
        await self.event_consumer.start()
        logger.info("Worker is consuming calculate requests")

    def request_shutdown(self) -> None:
        """Signal the worker to stop"""
        logger.info("Shutdown requested")
        self._shutdown.set()

    async def stop(self) -> None:
        """Stop worker"""
        self.event_consumer.stop()
        rabbitmq_client.disconnect()
        await redis_client.disconnect()
        logger.info("Worker stopped")

    async def run(self) -> None:
        """Run until a shutdown is requested"""
        await self.start()
        await self._shutdown.wait()
        await self.stop()


async def run_worker():
    worker = GameWorker()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_shutdown)
        except NotImplementedError:  # pragma: no cover - Windows
            pass

    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run_worker())
