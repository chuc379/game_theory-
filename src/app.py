"""
Main application entry point - Socket.io gateway server (Starlette)
"""
import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
from socketio import ASGIApp
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
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
from src.shared.infrastructure.messaging.event_consumer import EventConsumer
from src.shared.constants import (
    QUEUE_GATEWAY_PLAYER_EVENTS,
    QUEUE_GATEWAY_ROUND_RESULTS,
    QUEUE_WORKER_CALCULATE_RESULTS,
    ROUND_DURATION_SECONDS,
    ROUTING_KEY_PLAYER_JOINED,
    ROUTING_KEY_PLAYER_SUBMIT,
    ROUTING_KEY_ROUND_CALCULATE,
    ROUTING_KEY_ROUND_RESULT_FAILED,
    ROUTING_KEY_ROUND_RESULT_READY,
    RoundStatus,
)

logger = logging.getLogger(__name__)


class GameApplication:
    """Main game application"""

    def __init__(self):
        self.player_controller = None
        self.round_controller = None
        self.room_controller = None
        self.event_consumer = None
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

            # Setup Socket.io handlers
            self.setup_socket_handlers()

            # Setup broker subscriptions
            await self._setup_event_consumer()

            # Buffer calculate requests even when the worker service is down so
            # they are replayed instead of dropped.
            message_publisher.ensure_queue(
                QUEUE_WORKER_CALCULATE_RESULTS, [ROUTING_KEY_ROUND_CALCULATE]
            )

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

        # Room
        room_repo = RoomCacheRepository()
        self.room_controller = RoomController(room_repo)

        # Game Round
        guess_repo = GuessCacheRepository()
        result_repo = RoundResultCacheRepository()
        submit_guess_use_case = SubmitGuessUseCase(guess_repo)
        calculate_result_use_case = CalculateResultUseCase(guess_repo, result_repo)
        self.round_controller = RoundController(
            submit_guess_use_case, calculate_result_use_case, room_repo
        )

    async def _setup_event_consumer(self) -> None:
        """Subscribe the gateway to the events it owns"""
        self.event_consumer = EventConsumer()

        self.event_consumer.subscribe(
            QUEUE_GATEWAY_PLAYER_EVENTS,
            ROUTING_KEY_PLAYER_JOINED,
            self.on_player_joined_event,
        )
        self.event_consumer.subscribe(
            QUEUE_GATEWAY_PLAYER_EVENTS,
            ROUTING_KEY_PLAYER_SUBMIT,
            self.on_player_submit_event,
        )
        self.event_consumer.subscribe(
            QUEUE_GATEWAY_ROUND_RESULTS,
            ROUTING_KEY_ROUND_RESULT_READY,
            self.on_round_result_ready_event,
        )
        self.event_consumer.subscribe(
            QUEUE_GATEWAY_ROUND_RESULTS,
            ROUTING_KEY_ROUND_RESULT_FAILED,
            self.on_round_result_failed_event,
        )

        await self.event_consumer.start()

    async def on_player_joined_event(self, event: dict) -> None:
        """Handle player joined event coming from the broker"""
        room_id = event.get("room_id")
        player = event.get("player")
        if not room_id or not player:
            logger.error(f"Malformed player joined event: {event}")
            return

        await self.room_controller.update_player_count(room_id)
        await socket_gateway.emit_async(
            "player_joined", player, to=f"room_{room_id}"
        )

    async def on_player_submit_event(self, event: dict) -> None:
        """Handle player submitted event coming from the broker"""
        room_id = event.get("room_id")
        if not room_id:
            logger.error(f"Malformed player submit event: {event}")
            return

        await socket_gateway.emit_async(
            "player_submitted", event.get("guess"), to=f"room_{room_id}"
        )

    async def on_round_result_ready_event(self, event: dict) -> None:
        """Handle computed round result coming back from the worker"""
        room_id = event.get("room_id")
        round_id = event.get("round_id")
        if not room_id or round_id is None:
            logger.error(f"Malformed round result event: {event}")
            return

        await self.room_controller.end_round(room_id)
        await socket_gateway.emit_async(
            "round_result_ready",
            {
                "room_id": room_id,
                "round_id": round_id,
                "result": event.get("result"),
            },
            to=f"room_{room_id}",
        )
        logger.info(f"Broadcast round {round_id} result for room {room_id}")

    async def _calculate_inline(
        self, room_id: str, round_id: int, force_calculate: bool
    ) -> dict:
        """Calculate a round inside the gateway when no worker is available"""
        try:
            result = await self.round_controller.calculate_result_use_case.execute(
                room_id, round_id, force_calculate=force_calculate
            )
        except Exception as e:
            logger.error(f"Inline calculation failed for room {room_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

        if not result.get("success"):
            logger.warning(
                f"Inline calculation rejected for room {room_id} round {round_id}: "
                f"{result.get('error')}"
            )
            return result

        await self.room_controller.end_round(room_id)
        await socket_gateway.emit_async(
            "round_result_ready",
            {
                "room_id": room_id,
                "round_id": round_id,
                "result": result.get("result"),
            },
            to=f"room_{room_id}",
        )
        logger.info(
            f"Broadcast round {round_id} result for room {room_id} (inline)"
        )
        return result

    async def on_round_result_failed_event(self, event: dict) -> None:
        """Handle round result failure coming back from the worker"""
        room_id = event.get("room_id")
        round_id = event.get("round_id")
        if not room_id:
            logger.error(f"Malformed round result failure event: {event}")
            return

        error = event.get("error") or "Failed to calculate result"
        logger.warning(f"Round {round_id} failed for room {room_id}: {error}")
        await socket_gateway.emit_async(
            "error",
            {"error": f"Round {round_id}: {error}", "room_id": room_id, "round_id": round_id},
            to=f"room_{room_id}",
        )

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
                room_id = data.get("room_id")
                is_mc = data.get("is_mc", False)
                
                request = {
                    "room_id": room_id,
                    "player_name": data.get("player_name"),
                    "socket_id": sid,
                    "player_id": data.get("player_id"),
                }
                result = await self.player_controller.join_room(request)

                if result.get("success"):
                    # Room membership is critical: without it this client receives
                    # no round_started / round_result broadcasts.
                    await socket_gateway.enter_room(sid, f"room_{room_id}")

                    try:
                        if is_mc:
                            # MC creating/joining - save room info
                            await self.room_controller.save_room_info(room_id, {
                                "room_id": room_id,
                                "created_at": datetime.now().isoformat(),
                                "player_count": 1,
                                "mc_name": data.get("player_name"),
                            })
                        else:
                            # Player joining - announce through the broker
                            message_publisher.publish_player_joined(
                                {
                                    "room_id": room_id,
                                    "player": result.get("player"),
                                }
                            )

                            # Late joiner: replay the current round state so the
                            # player UI does not wait for the next round.
                            current_round = await self.room_controller.get_current_round(room_id)
                            round_status = await self.room_controller.get_round_status(room_id)
                            if current_round > 0 and round_status == RoundStatus.LOCKED:
                                await socket_gateway.emit_async(
                                    "round_started",
                                    {
                                        "room_id": room_id,
                                        "round_id": current_round,
                                        "duration": ROUND_DURATION_SECONDS,
                                    },
                                    to=sid,
                                )
                                logger.info(
                                    f"Replayed round {current_round} to late joiner {sid}"
                                )
                    except Exception as setup_error:
                        # Side effects are best-effort: never block the join
                        # acknowledgement, but tell the client about it.
                        logger.error(
                            f"Post-join setup failed for room {room_id}: {setup_error}",
                            exc_info=True,
                        )
                        await socket_gateway.emit_async(
                            "warning",
                            {
                                "message": (
                                    f"Joined room {room_id} but some setup failed: "
                                    f"{setup_error}"
                                )
                            },
                            to=sid,
                        )

                await socket_gateway.emit_async("join_room_response", result, to=sid)
            except Exception as e:
                logger.error(f"Error in join_room: {e}", exc_info=True)
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("submit_guess")
        async def on_submit_guess(sid, data):
            logger.info(f"Submit guess event from {sid}: {data}")
            try:
                # Validate request
                from src.modules.game_round.controller.round_controller import validate_submit_guess
                valid, error = validate_submit_guess(data)
                if not valid:
                    logger.warning(f"Invalid submit_guess: {error}")
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return
                
                room_id = data.get("room_id")
                logger.info(f"Processing submit_guess for player {data.get('player_id')} in room {room_id}")
                result = await self.round_controller.submit_guess(data)
                logger.info(f"Submit guess result: {result}")

                if result.get("success"):
                    message_publisher.publish_player_guess(
                        {
                            "room_id": room_id,
                            "round_id": data.get("round_id"),
                            "guess": result.get("guess"),
                        }
                    )
                else:
                    logger.warning(f"submit_guess rejected: {result.get('error')}")

                await socket_gateway.emit_async("submit_guess_response", result, to=sid)

            except Exception as e:
                logger.error(f"Error in submit_guess: {e}", exc_info=True)
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)


        @socket_gateway.sio.on("calculate_result")
        async def on_calculate_result(sid, data):
            logger.info(f"Calculate result event from {sid}: {data}")
            try:
                # Validate request
                from src.modules.game_round.controller.round_controller import (
                    get_force_calculate,
                    validate_calculate_result,
                )
                valid, error = validate_calculate_result(data)
                if not valid:
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return

                room_id = data.get("room_id")
                round_id = data.get("round_id")

                valid, error = await self.round_controller.validate_round(
                    room_id, round_id
                )
                if not valid:
                    logger.warning(
                        f"calculate_result rejected for room {room_id} round {round_id}: {error}"
                    )
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return

                force_calculate = get_force_calculate(data)

                # If no worker is consuming, run the calculation inline so the
                # round still completes instead of timing out.
                worker_status = rabbitmq_client.queue_status(QUEUE_WORKER_CALCULATE_RESULTS)
                worker_consumers = worker_status.get("consumers") or 0

                if worker_consumers == 0:
                    logger.warning(
                        f"No worker consuming {QUEUE_WORKER_CALCULATE_RESULTS}; "
                        f"calculating room {room_id} round {round_id} inline"
                    )
                    calculated = await self._calculate_inline(
                        room_id, int(round_id), force_calculate
                    )
                    if not calculated.get("success"):
                        await socket_gateway.emit_async(
                            "error",
                            {
                                "error": calculated.get("error", "Calculation failed"),
                                "room_id": room_id,
                                "round_id": int(round_id),
                            },
                            to=sid,
                        )
                        return

                    await socket_gateway.emit_async(
                        "calculate_result_response",
                        {
                            "success": True,
                            "status": "completed",
                            "message": "Calculation completed inline (no worker available)",
                            "room_id": room_id,
                            "round_id": int(round_id),
                        },
                        to=sid,
                    )
                    return

                # Hand the calculation to the worker
                published = message_publisher.publish_calculate_result(
                    {
                        "room_id": room_id,
                        "round_id": int(round_id),
                        "force_calculate": force_calculate,
                    }
                )

                if not published:
                    await socket_gateway.emit_async(
                        "error",
                        {"error": "Message broker unavailable, cannot calculate result"},
                        to=sid,
                    )
                    return

                await socket_gateway.emit_async(
                    "calculate_result_response",
                    {
                        "success": True,
                        "status": "queued",
                        "message": "Calculation queued",
                        "room_id": room_id,
                        "round_id": int(round_id),
                    },
                    to=sid,
                )
            except Exception as e:
                logger.error(f"Error in calculate_result: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("start_round")
        async def on_start_round(sid, data):
            logger.info(f"Start round event from {sid}: {data}")
            try:
                room_id = data.get("room_id")
                if not room_id:
                    await socket_gateway.emit_async(
                        "error", {"error": "room_id is required"}, to=sid
                    )
                    return

                round_id = await self.room_controller.start_round(room_id)
                logger.info(f"Room {room_id} started round {round_id}")

                # Broadcast round_started to all players in room
                try:
                    await socket_gateway.emit_to_room(
                        "round_started",
                        {
                            "room_id": room_id,
                            "round_id": round_id,
                            "duration": ROUND_DURATION_SECONDS,
                        },
                        room=f"room_{room_id}",
                        skip_sid=sid,
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast round_started: {e}")
                
                # Confirm to MC
                await socket_gateway.emit_async(
                    "start_round_response",
                    {
                        "success": True,
                        "message": "Round started",
                        "room_id": room_id,
                        "round_id": round_id,
                        "duration": ROUND_DURATION_SECONDS,
                    },
                    to=sid,
                )
            except Exception as e:
                logger.error(f"Error in start_round: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("list_rooms")
        async def on_list_rooms(sid, data):
            logger.info(f"List rooms request from {sid}")
            try:
                # Get all active rooms from Redis
                rooms = await self.room_controller.list_rooms()
                await socket_gateway.emit_async(
                    "rooms_list",
                    {"success": True, "rooms": rooms},
                    to=sid,
                )
            except Exception as e:
                logger.error(f"Error in list_rooms: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

    async def shutdown(self) -> None:
        """Shutdown handler"""
        logger.info("Application shutting down...")
        if self.event_consumer:
            self.event_consumer.stop()
        rabbitmq_client.disconnect()
        await redis_client.disconnect()


# Global app instance
app_instance = GameApplication()


# HTTP endpoints
async def health(request):
    """Health check endpoint"""
    worker_queue = rabbitmq_client.queue_status(QUEUE_WORKER_CALCULATE_RESULTS)
    worker_consumers = worker_queue.get("consumers") or 0
    return JSONResponse(
        {
            "status": "ok",
            "broker": "connected" if rabbitmq_client.consumer_alive else "disconnected",
            "worker": {
                "queue": worker_queue.get("queue"),
                "consumers": worker_queue.get("consumers"),
                "pending_messages": worker_queue.get("messages"),
                "alive": worker_consumers > 0,
                "error": worker_queue.get("error"),
            },
        }
    )


@asynccontextmanager
async def lifespan(app):
    await app_instance.initialize()
    try:
        yield
    finally:
        await app_instance.shutdown()


# Starlette app
starlette_app = Starlette(
    debug=settings.DEBUG,
    routes=[
        Route("/health", health),
    ],
    lifespan=lifespan,
)

# CORS middleware
starlette_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Socket.IO handles polling and WebSocket traffic; Starlette handles other routes.
app = ASGIApp(socket_gateway.sio, other_asgi_app=starlette_app)


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    host = "0.0.0.0"
    port = int(os.getenv("PORT", settings.SOCKET_IO_PORT))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("src.app:app", host=host, port=port, log_level="info", reload=False)
