"""
Main application entry point - Socket.io gateway server (ASGI)
"""
import logging
import os
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
        self.player_controller = None
        self.round_controller = None
        self.room_controller = None
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize application"""
        if self.initialized:
            return
            
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
            self.initialized = True
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
                result = await self.player_controller.join_room(request)

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
                from src.modules.game_round.controller.round_controller import validate_submit_guess
                valid, error = validate_submit_guess(data)
                if not valid:
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return
                
                result = await self.round_controller.submit_guess(data)

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
                from src.modules.game_round.controller.round_controller import validate_calculate_result
                valid, error = validate_calculate_result(data)
                if not valid:
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return

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

    async def lifespan(self, scope, receive, send):
        """ASGI lifespan handler"""
        message = await receive()
        if message["type"] == "lifespan.startup":
            try:
                await self.initialize()
                await send({"type": "lifespan.startup.complete"})
            except Exception as e:
                logger.error(f"Startup error: {e}")
                await send({"type": "lifespan.startup.failed", "message": str(e)})
        elif message["type"] == "lifespan.shutdown":
            logger.info("Shutting down...")
            await redis_client.disconnect()
            rabbitmq_client.disconnect()
            await send({"type": "lifespan.shutdown.complete"})

    async def asgi_app(self, scope, receive, send):
        """Main ASGI app that handles both Socket.io and HTTP"""
        if scope["type"] == "lifespan":
            await self.lifespan(scope, receive, send)
        elif scope["type"] == "http":
            # Handle health check
            if scope.get("path") == "/health":
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"status":"ok"}',
                })
                return
            
            # Pass HTTP requests to Socket.io ASGI app
            await socket_gateway.asgi_app(scope, receive, send)
        elif scope["type"] == "websocket":
            # Pass WebSocket to Socket.io ASGI app
            await socket_gateway.asgi_app(scope, receive, send)


# Global app instance
app_instance = GameApplication()


async def app(scope, receive, send):
    """ASGI app entrypoint"""
    await app_instance.asgi_app(scope, receive, send)


def run_server(host: str = None, port: int = None) -> None:
    """Run application with Uvicorn"""
    import uvicorn
    
    host = host or "0.0.0.0"
    port = port or int(os.getenv("PORT", settings.SOCKET_IO_PORT))

    # Setup handlers before running
    app_instance.setup_socket_handlers()

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("src.app:app", host=host, port=port, log_level="info", reload=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_server()
