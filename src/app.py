"""
Main application entry point - Socket.io gateway server
"""
import logging
import asyncio
from aiohttp import web
from config.settings import settings
from src.shared.infrastructure.socket_io.socket_gateway import socket_gateway
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.infrastructure.messaging.rabbitmq_client import rabbitmq_client

# Initialize repositories
from src.modules.player.adapter.player_cache_repository import PlayerCacheRepository
from src.modules.game_round.adapter.round_cache_repository import (
    GuessCacheRepository,
    RoundResultCacheRepository,
)
from src.modules.room.adapter.room_cache_repository import RoomCacheRepository

# Initialize use cases
from src.modules.player.use_cases.join_room import JoinRoomUseCase
from src.modules.game_round.use_cases.submit_guess import SubmitGuessUseCase
from src.modules.game_round.use_cases.calculate_result import CalculateResultUseCase

# Initialize controllers
from src.modules.player.controller.player_controller import PlayerController
from src.modules.game_round.controller.round_controller import RoundController
from src.modules.room.controller.room_controller import RoomController

# Message publisher
from src.shared.infrastructure.messaging.message_publisher import message_publisher

logger = logging.getLogger(__name__)


class GameApplication:
    """Main game application"""

    def __init__(self):
        self.app = None
        self.player_controller = None
        self.round_controller = None
        self.room_controller = None

    async def initialize(self) -> None:
        """Initialize application"""
        try:
            # Connect to Redis
            await redis_client.connect()
            logger.info("Connected to Redis")

            # Connect to RabbitMQ
            rabbitmq_client.connect()
            logger.info("Connected to RabbitMQ")

            # Setup controllers with repositories and use cases
            self._setup_controllers()

            logger.info("Application initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise

    def _setup_controllers(self) -> None:
        """Setup controllers"""
        # Player
        player_repo = PlayerCacheRepository()
        join_room_use_case = JoinRoomUseCase(player_repo)
        self.player_controller = PlayerController(join_room_use_case)

        # Game Round
        guess_repo = GuessCacheRepository()
        result_repo = RoundResultCacheRepository()
        submit_guess_use_case = SubmitGuessUseCase(guess_repo)
        calculate_result_use_case = CalculateResultUseCase(guess_repo, result_repo)
        self.round_controller = RoundController(submit_guess_use_case, calculate_result_use_case)

        # Room
        room_repo = RoomCacheRepository()
        self.room_controller = RoomController(room_repo)

    def setup_socket_handlers(self) -> None:
        """Setup Socket.io event handlers"""

        @socket_gateway.sio.on("connect")
        async def on_connect(sid, environ):
            logger.info(f"Client connected: {sid}")
            await socket_gateway.emit_async("connection_response", {"data": "Connected"}, to=sid)

        @socket_gateway.sio.on("disconnect")
        async def on_disconnect(sid):
            logger.info(f"Client disconnected: {sid}")

        @socket_gateway.sio.on("join_room")
        async def on_join_room(sid, data):
            logger.info(f"Join room event from {sid}: {data}")
            try:
                request = {
                    "room_id": data.get("room_id"),
                    "player_name": data.get("player_name"),
                    "socket_id": sid,
                }
                # Validate request
                from src.modules.player.controller.player_controller import JoinRoomRequest
                req = JoinRoomRequest(**request)
                result = await self.player_controller.join_room(req)

                if result.get("success"):
                    # Publish event to message broker
                    message_publisher.publish_player_guess(
                        {
                            "room_id": data.get("room_id"),
                            "event": "PLAYER_JOINED",
                            "player": result.get("player"),
                        }
                    )
                    # Broadcast to room
                    await socket_gateway.broadcast(
                        "player_joined", result.get("player"), skip_sid=sid
                    )

                await socket_gateway.emit_async("join_room_response", result, to=sid)
            except Exception as e:
                logger.error(f"Error in join_room: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("submit_guess")
        async def on_submit_guess(sid, data):
            logger.info(f"Submit guess event from {sid}: {data}")
            try:
                # Validate request
                from src.modules.game_round.controller.round_controller import SubmitGuessRequest
                req = SubmitGuessRequest(**data)
                result = await self.round_controller.submit_guess(req)

                if result.get("success"):
                    # Publish to message broker for worker
                    message_publisher.publish_player_guess(
                        {
                            "room_id": data.get("room_id"),
                            "round_id": data.get("round_id"),
                            "playerId": data.get("player_id"),
                            "playerName": data.get("player_name"),
                            "guessNumber": data.get("guess_number"),
                        }
                    )
                    # Broadcast to room
                    await socket_gateway.broadcast("player_submitted", result.get("guess"))

                await socket_gateway.emit_async("submit_guess_response", result, to=sid)
            except Exception as e:
                logger.error(f"Error in submit_guess: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("calculate_result")
        async def on_calculate_result(sid, data):
            logger.info(f"Calculate result event from {sid}: {data}")
            try:
                # Validate request
                from src.modules.game_round.controller.round_controller import CalculateResultRequest
                req = CalculateResultRequest(**data)

                # Publish to worker queue
                message_publisher.publish_calculate_result(
                    {
                        "room_id": data.get("room_id"),
                        "round_id": data.get("round_id"),
                    }
                )

                await socket_gateway.emit_async(
                    "calculate_result_response",
                    {"success": True, "message": "Calculating result..."},
                    to=sid,
                )
            except Exception as e:
                logger.error(f"Error in calculate_result: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

    async def startup(self, app: web.Application) -> None:
        """Startup event handler"""
        logger.info("Application starting...")

    async def shutdown(self, app: web.Application) -> None:
        """Shutdown event handler"""
        logger.info("Application shutting down...")
        await redis_client.disconnect()
        rabbitmq_client.disconnect()

    async def run(self, host: str = None, port: int = None) -> None:
        """Run application"""
        host = host or settings.SOCKET_IO_PORT
        port = port or settings.SOCKET_IO_PORT

        # Create app
        self.app = socket_gateway.create_app()
        socket_gateway.setup(self.app)

        # Setup handlers
        self.setup_socket_handlers()

        # Setup startup/shutdown
        self.app.on_startup.append(self.startup)
        self.app.on_shutdown.append(self.shutdown)

        # Initialize
        await self.initialize()

        # Run
        logger.info(f"Starting server on {host}:{port}")
        web.run_app(self.app, host=host, port=port)


def create_app() -> GameApplication:
    """Factory function to create application"""
    return GameApplication()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app = create_app()
    asyncio.run(app.run())
